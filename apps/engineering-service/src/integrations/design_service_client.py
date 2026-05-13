"""Design Service Client for updating technical requirements."""

import logging
from typing import Any, Dict, List, Optional
from uuid import UUID

import httpx
import redis.asyncio as redis

from ..core.config import settings

logger = logging.getLogger(__name__)


class DesignServiceClient:
    """Client for interacting with Design Service.

    Provides methods to update technical requirements and
    retrieve technical drawings.
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        timeout: float = 30.0,
        max_retries: int = 3,
        redis_client: Optional[redis.Redis] = None,
    ):
        """Initialize Design Service client.

        Args:
            base_url: Base URL of Design Service
            timeout: Request timeout in seconds
            max_retries: Maximum number of retry attempts
            redis_client: Optional Redis client for caching
        """
        self.base_url = (base_url or settings.design_service_url).rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries
        self.redis_client = redis_client
        self.cache_ttl = settings.redis_cache_ttl
        self._client: Optional[httpx.AsyncClient] = None

    async def __aenter__(self):
        """Async context manager entry."""
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=self.timeout,
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self._client:
            await self._client.aclose()

    def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=self.timeout,
            )
        return self._client

    async def _get_cached(self, key: str) -> Optional[Dict[str, Any]]:
        """Get cached response from Redis."""
        if not self.redis_client:
            return None

        try:
            cached = await self.redis_client.get(key)
            if cached:
                import json

                return json.loads(cached)
        except Exception as e:
            logger.warning(f"Cache retrieval failed: {e}")

        return None

    async def _set_cache(
        self, key: str, value: Dict[str, Any], ttl: Optional[int] = None
    ):
        """Set cached response in Redis."""
        if not self.redis_client:
            return

        try:
            import json

            await self.redis_client.setex(key, ttl or self.cache_ttl, json.dumps(value))
        except Exception as e:
            logger.warning(f"Cache storage failed: {e}")

    async def _invalidate_cache(self, pattern: str):
        """Invalidate cache entries matching pattern."""
        if not self.redis_client:
            return

        try:
            keys = []
            async for key in self.redis_client.scan_iter(match=pattern):
                keys.append(key)

            if keys:
                await self.redis_client.delete(*keys)
                logger.debug(f"Invalidated {len(keys)} cache entries")
        except Exception as e:
            logger.warning(f"Cache invalidation failed: {e}")

    async def update_technical_requirements(
        self,
        design_id: UUID,
        requirements: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Update technical drawing requirements.

        Args:
            design_id: Design UUID
            requirements: Technical requirements data

        Returns:
            Dictionary containing updated design data

        Raises:
            httpx.HTTPError: If request fails
        """
        logger.info(f"Updating technical requirements for design: {design_id}")

        client = self._get_client()

        try:
            response = await client.put(
                f"/api/v1/designs/{design_id}/requirements",
                json=requirements,
            )
            response.raise_for_status()

            data = response.json()
            logger.debug(f"Updated requirements for design: {design_id}")

            # Invalidate cache for this design
            await self._invalidate_cache(f"design:{design_id}*")

            return data

        except httpx.HTTPError as e:
            logger.error(f"Failed to update requirements for {design_id}: {e}")
            raise

    async def get_drawings(
        self, project_id: UUID, use_cache: bool = True
    ) -> List[Dict[str, Any]]:
        """Retrieve technical drawings for a project.

        Args:
            project_id: Project UUID
            use_cache: Whether to use cached response

        Returns:
            List of drawing data

        Raises:
            httpx.HTTPError: If request fails
        """
        logger.info(f"Fetching drawings for project: {project_id}")

        cache_key = f"design_drawings:{project_id}"

        # Check cache first
        if use_cache:
            cached = await self._get_cached(cache_key)
            if cached:
                logger.debug(f"Cache hit for drawings {project_id}")
                return cached

        client = self._get_client()

        try:
            response = await client.get(f"/api/v1/projects/{project_id}/drawings")
            response.raise_for_status()

            data = response.json()
            logger.debug(f"Retrieved {len(data)} drawings")

            # Cache the response
            await self._set_cache(cache_key, data)

            return data

        except httpx.HTTPError as e:
            logger.error(f"Failed to fetch drawings for {project_id}: {e}")
            raise

    async def get_design(
        self, design_id: UUID, use_cache: bool = True
    ) -> Dict[str, Any]:
        """Retrieve design by ID.

        Args:
            design_id: Design UUID
            use_cache: Whether to use cached response

        Returns:
            Dictionary containing design data

        Raises:
            httpx.HTTPError: If request fails
        """
        logger.info(f"Fetching design: {design_id}")

        cache_key = f"design:{design_id}"

        # Check cache first
        if use_cache:
            cached = await self._get_cached(cache_key)
            if cached:
                logger.debug(f"Cache hit for design {design_id}")
                return cached

        client = self._get_client()

        try:
            response = await client.get(f"/api/v1/designs/{design_id}")
            response.raise_for_status()

            data = response.json()
            logger.debug(f"Retrieved design: {design_id}")

            # Cache the response
            await self._set_cache(cache_key, data)

            return data

        except httpx.HTTPError as e:
            logger.error(f"Failed to fetch design {design_id}: {e}")
            raise

    async def create_technical_specification(
        self,
        design_id: UUID,
        specification_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Create technical specification for a design.

        Args:
            design_id: Design UUID
            specification_data: Specification data

        Returns:
            Dictionary containing created specification

        Raises:
            httpx.HTTPError: If request fails
        """
        logger.info(f"Creating technical specification for design: {design_id}")

        client = self._get_client()

        try:
            response = await client.post(
                f"/api/v1/designs/{design_id}/specifications",
                json=specification_data,
            )
            response.raise_for_status()

            data = response.json()
            logger.debug(f"Created specification for design: {design_id}")

            return data

        except httpx.HTTPError as e:
            logger.error(f"Failed to create specification for {design_id}: {e}")
            raise

    async def close(self):
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None
