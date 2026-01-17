"""
Knowledge Service client for building codes and standards.
"""

import logging
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx
from pydantic import BaseModel

# Add workspace root to path for common packages
workspace_root = Path(__file__).parent.parent.parent.parent.parent
if str(workspace_root) not in sys.path:
    sys.path.insert(0, str(workspace_root))

from packages.common.resilience.circuit_breaker import (CircuitBreaker,
                                                        CircuitBreakerConfig)
from packages.common.resilience.retry import RetryConfig, retry_async_call

logger = logging.getLogger(__name__)


class CodeSection(BaseModel):
    """Building code section."""

    code_id: str
    section: str
    title: str
    content: str
    edition: str
    effective_date: Optional[datetime] = None


class CodeStandard(BaseModel):
    """Building code standard."""

    code_id: str
    name: str
    edition: str
    jurisdiction: Optional[str] = None
    applicable_building_types: List[str] = []


class CodeSectionDetail(BaseModel):
    """Detailed code section information."""

    code_id: str
    section: str
    title: str
    content: str
    edition: str
    subsections: List[Dict[str, Any]] = []
    references: List[str] = []
    effective_date: Optional[datetime] = None


class CodeFilters(BaseModel):
    """Filters for code search."""

    jurisdiction: Optional[str] = None
    building_type: Optional[str] = None
    edition: Optional[str] = None
    effective_after: Optional[datetime] = None


class KnowledgeServiceClient:
    """Client for interacting with Knowledge Service."""

    def __init__(
        self,
        base_url: str,
        timeout: float = 30.0,
        cache_ttl: int = 3600,
        circuit_breaker_config: Optional[CircuitBreakerConfig] = None,
        retry_config: Optional[RetryConfig] = None,
    ):
        """Initialize Knowledge Service client."""
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.cache_ttl = cache_ttl

        # Simple in-memory cache for frequently accessed codes
        self._cache: Dict[str, tuple[Any, datetime]] = {}

        # Initialize circuit breaker
        if circuit_breaker_config is None:
            circuit_breaker_config = CircuitBreakerConfig(
                failure_threshold=5, recovery_timeout=60, success_threshold=3
            )
        self.circuit_breaker = CircuitBreaker(
            "knowledge-service", circuit_breaker_config
        )

        # Initialize retry config
        if retry_config is None:
            retry_config = RetryConfig(
                max_attempts=3,
                base_delay=1.0,
                max_delay=10.0,
                exponential_base=2.0,
                retryable_exceptions=[httpx.TimeoutException, httpx.ConnectError],
                retryable_status_codes=[502, 503, 504],
            )
        self.retry_config = retry_config

        # HTTP client
        self._client = httpx.AsyncClient(timeout=timeout)

        logger.info(f"KnowledgeServiceClient initialized with base_url={base_url}")

    async def close(self):
        """Close the HTTP client."""
        await self._client.aclose()

    def _get_from_cache(self, key: str) -> Optional[Any]:
        """Get value from cache if not expired."""
        if key in self._cache:
            value, timestamp = self._cache[key]
            if datetime.utcnow() - timestamp < timedelta(seconds=self.cache_ttl):
                logger.debug(f"Cache hit for key: {key}")
                return value
            else:
                # Expired, remove from cache
                del self._cache[key]
                logger.debug(f"Cache expired for key: {key}")
        return None

    def _set_in_cache(self, key: str, value: Any):
        """Set value in cache with current timestamp."""
        self._cache[key] = (value, datetime.utcnow())
        logger.debug(f"Cached value for key: {key}")

    def invalidate_cache(self, key: Optional[str] = None):
        """Invalidate cache entry or entire cache."""
        if key:
            if key in self._cache:
                del self._cache[key]
                logger.info(f"Invalidated cache for key: {key}")
        else:
            self._cache.clear()
            logger.info("Invalidated entire cache")

    async def _make_request(self, method: str, path: str, **kwargs) -> httpx.Response:
        """Make HTTP request with circuit breaker and retry logic."""
        url = f"{self.base_url}{path}"

        async def _request():
            response = await self._client.request(method, url, **kwargs)
            response.raise_for_status()
            return response

        # Execute with circuit breaker and retry
        return await self.circuit_breaker.call_async(
            retry_async_call, _request, config=self.retry_config
        )

    async def search_codes(
        self, query: str, filters: Optional[CodeFilters] = None
    ) -> List[CodeSection]:
        """
        Search for building code sections.

        Args:
            query: Search query string
            filters: Optional filters for search

        Returns:
            List of matching code sections

        Raises:
            httpx.HTTPStatusError: If request fails
        """
        # Build cache key
        cache_key = f"search:{query}:{filters.model_dump_json() if filters else 'none'}"

        # Check cache
        cached = self._get_from_cache(cache_key)
        if cached is not None:
            return cached

        try:
            params = {"q": query}
            if filters:
                filter_dict = filters.model_dump(exclude_none=True)
                params.update(filter_dict)

            response = await self._make_request(
                "GET", "/api/v1/codes/search", params=params
            )

            data = response.json()
            results = [CodeSection(**item) for item in data.get("results", [])]

            # Cache results
            self._set_in_cache(cache_key, results)

            return results

        except Exception as e:
            logger.error(f"Failed to search codes with query '{query}': {e}")
            raise

    async def get_applicable_codes(
        self, location: str, building_type: str
    ) -> List[CodeStandard]:
        """
        Get applicable building codes for location and building type.

        Args:
            location: Location/jurisdiction
            building_type: Type of building

        Returns:
            List of applicable code standards

        Raises:
            httpx.HTTPStatusError: If request fails
        """
        # Build cache key
        cache_key = f"applicable:{location}:{building_type}"

        # Check cache
        cached = self._get_from_cache(cache_key)
        if cached is not None:
            return cached

        try:
            response = await self._make_request(
                "GET",
                "/api/v1/codes/applicable",
                params={"location": location, "building_type": building_type},
            )

            data = response.json()
            results = [CodeStandard(**item) for item in data.get("codes", [])]

            # Cache results
            self._set_in_cache(cache_key, results)

            return results

        except Exception as e:
            logger.error(
                f"Failed to get applicable codes for location='{location}', "
                f"building_type='{building_type}': {e}"
            )
            raise

    async def get_code_section(self, code_id: str, section: str) -> CodeSectionDetail:
        """
        Retrieve specific code section with details.

        Args:
            code_id: Code standard identifier
            section: Section number

        Returns:
            Detailed code section information

        Raises:
            httpx.HTTPStatusError: If code section not found or request fails
        """
        # Build cache key
        cache_key = f"section:{code_id}:{section}"

        # Check cache
        cached = self._get_from_cache(cache_key)
        if cached is not None:
            return cached

        try:
            response = await self._make_request(
                "GET", f"/api/v1/codes/{code_id}/sections/{section}"
            )

            data = response.json()
            result = CodeSectionDetail(**data)

            # Cache result
            self._set_in_cache(cache_key, result)

            return result

        except Exception as e:
            logger.error(f"Failed to get code section {code_id}/{section}: {e}")
            raise
