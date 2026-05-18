"""Project Service Client for updating milestones and project info."""

import logging
from typing import Any, Dict, List, Optional
from uuid import UUID

import httpx
import redis.asyncio as redis

from ..core.config import settings

logger = logging.getLogger(__name__)


class ProjectServiceClient:
    """Client for interacting with Project Service.

    Provides methods to update engineering milestones and
    retrieve project information.
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        timeout: float = 30.0,
        max_retries: int = 3,
        redis_client: Optional[redis.Redis] = None,
    ):
        """Initialize Project Service client.

        Args:
            base_url: Base URL of Project Service
            timeout: Request timeout in seconds
            max_retries: Maximum number of retry attempts
            redis_client: Optional Redis client for caching
        """
        self.base_url = (base_url or settings.project_service_url).rstrip("/")
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

    async def get_project_info(
        self, project_id: UUID, use_cache: bool = True
    ) -> Dict[str, Any]:
        """Retrieve project information.

        Args:
            project_id: Project UUID
            use_cache: Whether to use cached response

        Returns:
            Dictionary containing project data

        Raises:
            httpx.HTTPError: If request fails
        """
        logger.info(f"Fetching project info: {project_id}")

        cache_key = f"project:{project_id}"

        # Check cache first
        if use_cache:
            cached = await self._get_cached(cache_key)
            if cached:
                logger.debug(f"Cache hit for project {project_id}")
                return cached

        client = self._get_client()

        try:
            response = await client.get(f"/api/v1/projects/{project_id}")
            response.raise_for_status()

            data = response.json()
            logger.debug(f"Retrieved project: {project_id}")

            # Cache the response
            await self._set_cache(cache_key, data)

            return data

        except httpx.HTTPError as e:
            logger.error(f"Failed to fetch project {project_id}: {e}")
            raise

    async def update_milestone(
        self,
        project_id: UUID,
        milestone_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Update engineering milestone status.

        Args:
            project_id: Project UUID
            milestone_data: Milestone update data including:
                - milestone_id: UUID of milestone
                - status: New status (e.g., "completed", "in_progress")
                - completion_date: Optional completion date
                - notes: Optional notes

        Returns:
            Dictionary containing updated milestone data

        Raises:
            httpx.HTTPError: If request fails
        """
        logger.info(f"Updating milestone for project: {project_id}")

        client = self._get_client()

        try:
            response = await client.put(
                f"/api/v1/projects/{project_id}/milestones",
                json=milestone_data,
            )
            response.raise_for_status()

            data = response.json()
            logger.debug(f"Updated milestone for project: {project_id}")

            # Invalidate project cache
            await self._invalidate_cache(f"project:{project_id}*")

            return data

        except httpx.HTTPError as e:
            logger.error(f"Failed to update milestone for {project_id}: {e}")
            raise

    async def get_milestones(
        self, project_id: UUID, use_cache: bool = True
    ) -> List[Dict[str, Any]]:
        """Get all milestones for a project.

        Args:
            project_id: Project UUID
            use_cache: Whether to use cached response

        Returns:
            List of milestone data

        Raises:
            httpx.HTTPError: If request fails
        """
        logger.info(f"Fetching milestones for project: {project_id}")

        cache_key = f"project_milestones:{project_id}"

        # Check cache first
        if use_cache:
            cached = await self._get_cached(cache_key)
            if cached:
                logger.debug(f"Cache hit for milestones {project_id}")
                return cached

        client = self._get_client()

        try:
            response = await client.get(f"/api/v1/projects/{project_id}/milestones")
            response.raise_for_status()

            data = response.json()
            logger.debug(f"Retrieved {len(data)} milestones")

            # Cache the response
            await self._set_cache(cache_key, data)

            return data

        except httpx.HTTPError as e:
            logger.error(f"Failed to fetch milestones for {project_id}: {e}")
            raise

    async def create_milestone(
        self,
        project_id: UUID,
        milestone_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Create a new engineering milestone.

        Args:
            project_id: Project UUID
            milestone_data: Milestone data including:
                - name: Milestone name
                - description: Description
                - due_date: Due date
                - milestone_type: Type (e.g., "engineering")

        Returns:
            Dictionary containing created milestone

        Raises:
            httpx.HTTPError: If request fails
        """
        logger.info(f"Creating milestone for project: {project_id}")

        client = self._get_client()

        try:
            response = await client.post(
                f"/api/v1/projects/{project_id}/milestones",
                json=milestone_data,
            )
            response.raise_for_status()

            data = response.json()
            logger.debug(f"Created milestone for project: {project_id}")

            # Invalidate milestones cache
            await self._invalidate_cache(f"project_milestones:{project_id}*")

            return data

        except httpx.HTTPError as e:
            logger.error(f"Failed to create milestone for {project_id}: {e}")
            raise

    async def get_project_team(
        self, project_id: UUID, use_cache: bool = True
    ) -> List[Dict[str, Any]]:
        """Get project team members.

        Args:
            project_id: Project UUID
            use_cache: Whether to use cached response

        Returns:
            List of team member data

        Raises:
            httpx.HTTPError: If request fails
        """
        logger.info(f"Fetching team for project: {project_id}")

        cache_key = f"project_team:{project_id}"

        # Check cache first
        if use_cache:
            cached = await self._get_cached(cache_key)
            if cached:
                logger.debug(f"Cache hit for team {project_id}")
                return cached

        client = self._get_client()

        try:
            response = await client.get(f"/api/v1/projects/{project_id}/team")
            response.raise_for_status()

            data = response.json()
            logger.debug(f"Retrieved {len(data)} team members")

            # Cache the response
            await self._set_cache(cache_key, data)

            return data

        except httpx.HTTPError as e:
            logger.error(f"Failed to fetch team for {project_id}: {e}")
            raise

    async def verify_project_membership(
        self, project_id: UUID, user_id: UUID, use_cache: bool = True
    ) -> bool:
        """Verify if a user is a member of a project.

        Args:
            project_id: Project UUID
            user_id: User UUID
            use_cache: Whether to use cached response

        Returns:
            True if user is a project member, False otherwise
        """
        logger.info(f"Verifying membership for user {user_id} in project {project_id}")

        cache_key = f"project_membership:{project_id}:{user_id}"

        # Check cache first
        if use_cache:
            cached = await self._get_cached(cache_key)
            if cached is not None:
                logger.debug("Cache hit for membership check")
                return cached.get("is_member", False)

        client = self._get_client()

        try:
            response = await client.get(
                f"/api/v1/projects/{project_id}/members/{user_id}"
            )

            # If we get a 200, user is a member
            if response.status_code == 200:
                result = {"is_member": True}
                await self._set_cache(cache_key, result, ttl=300)  # Cache for 5 min
                return True

            # If we get a 404, user is not a member
            if response.status_code == 404:
                result = {"is_member": False}
                await self._set_cache(cache_key, result, ttl=60)  # Cache for 1 min
                return False

            # For other status codes, raise an error
            response.raise_for_status()
            return False

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return False
            logger.error(f"Failed to verify membership: {e}")
            raise
        except httpx.HTTPError as e:
            logger.error(f"Failed to verify membership: {e}")
            # On error, default to False for security
            return False

    async def close(self):
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None
