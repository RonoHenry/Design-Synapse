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

from ..core.cache import get_cache

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
        circuit_breaker_config: Optional[CircuitBreakerConfig] = None,
        retry_config: Optional[RetryConfig] = None,
    ):
        """Initialize Knowledge Service client."""
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

        # Get Redis cache instance
        self.cache = get_cache()

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

    def invalidate_cache(self, key: Optional[str] = None):
        """Invalidate cache entry or entire cache."""
        # This method is kept for backward compatibility but now delegates to Redis cache
        logger.info("Cache invalidation requested - will be handled by Redis cache")

    async def invalidate_knowledge_cache(self):
        """Invalidate all knowledge service cache entries."""
        return await self.cache.invalidate_knowledge_cache()

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
        return await self._search_codes_impl(query, filters)

    @get_cache().cached("knowledge:search", ttl=3600)  # Cache for 1 hour
    async def _search_codes_impl(
        self, query: str, filters: Optional[CodeFilters] = None
    ) -> List[CodeSection]:
        """Implementation of search_codes with caching."""
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

            logger.info(f"Retrieved {len(results)} code sections for query: {query}")
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
        return await self._get_applicable_codes_impl(location, building_type)

    @get_cache().cached("knowledge:applicable", ttl=7200)  # Cache for 2 hours
    async def _get_applicable_codes_impl(
        self, location: str, building_type: str
    ) -> List[CodeStandard]:
        """Implementation of get_applicable_codes with caching."""
        try:
            response = await self._make_request(
                "GET",
                "/api/v1/codes/applicable",
                params={"location": location, "building_type": building_type},
            )

            data = response.json()
            results = [CodeStandard(**item) for item in data.get("codes", [])]

            logger.info(
                f"Retrieved {len(results)} applicable codes for "
                f"location='{location}', building_type='{building_type}'"
            )
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
        return await self._get_code_section_impl(code_id, section)

    @get_cache().cached("knowledge:section", ttl=14400)  # Cache for 4 hours
    async def _get_code_section_impl(
        self, code_id: str, section: str
    ) -> CodeSectionDetail:
        """Implementation of get_code_section with caching."""
        try:
            response = await self._make_request(
                "GET", f"/api/v1/codes/{code_id}/sections/{section}"
            )

            data = response.json()
            result = CodeSectionDetail(**data)

            logger.info(f"Retrieved code section {code_id}/{section}")
            return result

        except Exception as e:
            logger.error(f"Failed to get code section {code_id}/{section}: {e}")
            raise
