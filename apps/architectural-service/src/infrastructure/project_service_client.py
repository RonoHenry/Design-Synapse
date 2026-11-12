"""
Project Service client for architectural service integration.
"""

import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional
from uuid import UUID

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


class ProjectValidation(BaseModel):
    """Project validation response."""

    project_id: UUID
    exists: bool
    user_has_access: bool
    project_name: Optional[str] = None
    project_status: Optional[str] = None


class ProjectStatus(BaseModel):
    """Project status response."""

    project_id: UUID
    status: str
    name: str
    created_at: datetime
    updated_at: datetime


class ActivityLog(BaseModel):
    """Activity log entry."""

    project_id: UUID
    user_id: UUID
    activity_type: str
    description: str
    metadata: Dict[str, Any] = {}
    timestamp: datetime


class ProjectServiceClient:
    """Client for interacting with Project Service."""

    def __init__(
        self,
        base_url: str,
        timeout: float = 30.0,
        circuit_breaker_config: Optional[CircuitBreakerConfig] = None,
        retry_config: Optional[RetryConfig] = None,
    ):
        """Initialize Project Service client."""
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

        # Initialize circuit breaker
        if circuit_breaker_config is None:
            circuit_breaker_config = CircuitBreakerConfig(
                failure_threshold=5, recovery_timeout=60, success_threshold=3
            )
        self.circuit_breaker = CircuitBreaker("project-service", circuit_breaker_config)

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

        logger.info(f"ProjectServiceClient initialized with base_url={base_url}")

    async def close(self):
        """Close the HTTP client."""
        await self._client.aclose()

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

    async def validate_project(
        self, project_id: UUID, user_id: UUID
    ) -> ProjectValidation:
        """
        Validate that project exists and user has access.

        Args:
            project_id: Project ID to validate
            user_id: User ID to check access for

        Returns:
            ProjectValidation with validation results

        Raises:
            httpx.HTTPStatusError: If request fails
        """
        try:
            response = await self._make_request(
                "GET",
                f"/api/v1/projects/{project_id}/validate",
                params={"user_id": str(user_id)},
            )

            data = response.json()
            return ProjectValidation(**data)

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                # Project not found
                return ProjectValidation(
                    project_id=project_id, exists=False, user_has_access=False
                )
            elif e.response.status_code == 403:
                # User doesn't have access
                return ProjectValidation(
                    project_id=project_id, exists=True, user_has_access=False
                )
            raise
        except Exception as e:
            logger.error(f"Failed to validate project {project_id}: {e}")
            raise

    async def log_activity(self, project_id: UUID, activity: ActivityLog) -> None:
        """
        Log activity to project timeline.

        Args:
            project_id: Project ID
            activity: Activity log entry

        Note:
            This is a fire-and-forget operation. Failures are logged but not raised.
        """
        try:
            await self._make_request(
                "POST",
                f"/api/v1/projects/{project_id}/activities",
                json=activity.model_dump(mode="json"),
            )
            logger.debug(
                f"Logged activity for project {project_id}: {activity.activity_type}"
            )

        except Exception as e:
            # Log but don't raise - activity logging is non-critical
            logger.warning(f"Failed to log activity for project {project_id}: {e}")

    async def get_project_status(self, project_id: UUID) -> ProjectStatus:
        """
        Get current project status.

        Args:
            project_id: Project ID

        Returns:
            ProjectStatus with project information

        Raises:
            httpx.HTTPStatusError: If project not found or request fails
        """
        try:
            response = await self._make_request("GET", f"/api/v1/projects/{project_id}")

            data = response.json()
            return ProjectStatus(**data)

        except Exception as e:
            logger.error(f"Failed to get project status for {project_id}: {e}")
            raise
