"""Architectural Service Client for retrieving designs and changes."""

import logging
from typing import Any, Callable, Dict, List, Optional
from uuid import UUID

import httpx
import redis.asyncio as redis

from ..core.config import settings

logger = logging.getLogger(__name__)


class ArchitecturalServiceClient:
    """Client for interacting with Architectural Service.

    Provides methods to retrieve architectural designs and
    subscribe to design change notifications.
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        timeout: float = 30.0,
        max_retries: int = 3,
        redis_client: Optional[redis.Redis] = None,
    ):
        """Initialize Architectural Service client.

        Args:
            base_url: Base URL of Architectural Service
            timeout: Request timeout in seconds
            max_retries: Maximum number of retry attempts
            redis_client: Optional Redis client for caching
        """
        self.base_url = (base_url or settings.architectural_service_url).rstrip("/")
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

    async def get_design(
        self, design_id: UUID, use_cache: bool = True
    ) -> Dict[str, Any]:
        """Retrieve architectural design by ID.

        Args:
            design_id: Design UUID
            use_cache: Whether to use cached response

        Returns:
            Dictionary containing design data

        Raises:
            httpx.HTTPError: If request fails
        """
        logger.info(f"Fetching architectural design: {design_id}")

        cache_key = f"arch_design:{design_id}"

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

    async def get_space_requirements(
        self, project_id: UUID, use_cache: bool = True
    ) -> List[Dict[str, Any]]:
        """Get space requirements for MEP sizing.

        Args:
            project_id: Project UUID
            use_cache: Whether to use cached response

        Returns:
            List of space requirements

        Raises:
            httpx.HTTPError: If request fails
        """
        logger.info(f"Fetching space requirements for project: {project_id}")

        cache_key = f"arch_spaces:{project_id}"

        # Check cache first
        if use_cache:
            cached = await self._get_cached(cache_key)
            if cached:
                logger.debug(f"Cache hit for spaces {project_id}")
                return cached

        client = self._get_client()

        try:
            response = await client.get(f"/api/v1/projects/{project_id}/spaces")
            response.raise_for_status()

            data = response.json()
            logger.debug(f"Retrieved {len(data)} space requirements")

            # Cache the response
            await self._set_cache(cache_key, data)

            return data

        except httpx.HTTPError as e:
            logger.error(f"Failed to fetch space requirements for {project_id}: {e}")
            raise

    async def subscribe_to_design_changes(
        self,
        design_id: UUID,
        callback: Callable[[Dict[str, Any]], None],
    ) -> None:
        """Subscribe to design change notifications.

        Args:
            design_id: Design UUID to monitor
            callback: Function to call when design changes

        Note:
            This is a placeholder for webhook/websocket implementation.
            In production, this would establish a persistent connection
            or register a webhook endpoint.
        """
        logger.info(f"Subscribing to design changes: {design_id}")

        # Invalidate cache when design changes
        await self._invalidate_cache(f"arch_design:{design_id}*")

        # TODO: Implement actual subscription mechanism
        # This could be:
        # - WebSocket connection
        # - Webhook registration
        # - Message queue subscription
        logger.warning(
            "Design change subscription not fully implemented. "
            "Cache invalidation performed."
        )

    async def get_design_version(self, design_id: UUID, version: int) -> Dict[str, Any]:
        """Retrieve specific version of architectural design.

        Args:
            design_id: Design UUID
            version: Version number

        Returns:
            Dictionary containing design data for specific version

        Raises:
            httpx.HTTPError: If request fails
        """
        logger.info(f"Fetching design {design_id} version {version}")

        client = self._get_client()

        try:
            response = await client.get(
                f"/api/v1/designs/{design_id}/versions/{version}"
            )
            response.raise_for_status()

            data = response.json()
            logger.debug(f"Retrieved design version: {design_id} v{version}")

            return data

        except httpx.HTTPError as e:
            logger.error(f"Failed to fetch design {design_id} v{version}: {e}")
            raise

    async def close(self):
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None
