"""Project service client for verifying project access and retrieving project details."""

import asyncio
import logging
from typing import Any, Dict

import httpx

from common.http.base_client import BaseHTTPClient


logger = logging.getLogger(__name__)


class ProjectAccessDeniedError(Exception):
    """Raised when user does not have access to a project."""
    pass


class ProjectClient(BaseHTTPClient):
    """HTTP client for Project Service with design-specific methods."""

    def __init__(
        self,
        base_url: str = None,
        timeout: float = 30.0,
        max_retries: int = 3,
        circuit_breaker_threshold: int = 5,
        circuit_breaker_timeout: int = 60,
    ):
        """Initialize Project Service client.
        
        Args:
            base_url: Base URL for the project service (defaults to env config)
            timeout: Request timeout in seconds
            max_retries: Maximum number of retry attempts
            circuit_breaker_threshold: Number of failures before opening circuit
            circuit_breaker_timeout: Seconds to wait before trying half-open state
        """
        # If no base_url provided, use default from environment
        if base_url is None:
            from ..core.config import get_settings
            settings = get_settings()
            base_url = settings.project_service_url
        
        super().__init__(
            base_url=base_url,
            timeout=timeout,
            max_retries=max_retries,
            circuit_breaker_threshold=circuit_breaker_threshold,
            circuit_breaker_timeout=circuit_breaker_timeout,
        )

    async def verify_project_access(self, project_id: int, user_id: int) -> bool:
        """Verify that a user has access to a project.
        
        This method checks if the user is a member of the project by calling
        the project service's member verification endpoint.
        
        Args:
            project_id: ID of the project to check
            user_id: ID of the user to verify
            
        Returns:
            True if user has access to the project
            
        Raises:
            ProjectAccessDeniedError: If user is not a member or access is denied
            httpx.HTTPStatusError: For other HTTP errors (500, etc.)
        """
        try:
            # Call the project service to verify membership
            path = f"/projects/{project_id}/members/{user_id}"
            logger.info(f"Verifying project access: user {user_id} for project {project_id}")
            
            # Make the request - will raise HTTPStatusError for 4xx/5xx
            await self.get(path)
            
            logger.info(f"Access verified: user {user_id} is a member of project {project_id}")
            return True
            
        except httpx.HTTPStatusError as e:
            # Handle specific HTTP errors
            if e.response.status_code == 404:
                # User is not a member or project doesn't exist
                logger.warning(
                    f"Access denied: user {user_id} is not a member of project {project_id}"
                )
                raise ProjectAccessDeniedError(
                    f"User {user_id} is not a member of project {project_id}"
                )
            elif e.response.status_code == 403:
                # User is forbidden from accessing the project
                logger.warning(
                    f"Access denied: user {user_id} forbidden from project {project_id}"
                )
                raise ProjectAccessDeniedError(
                    f"Access denied to project {project_id} for user {user_id}"
                )
            else:
                # Other HTTP errors (500, etc.) - re-raise
                logger.error(
                    f"HTTP error verifying project access: {e.response.status_code}"
                )
                raise

    async def get_project_details(self, project_id: int) -> Dict[str, Any]:
        """Get project details from the project service.
        
        Args:
            project_id: ID of the project to retrieve
            
        Returns:
            Dictionary containing project details
            
        Raises:
            httpx.HTTPStatusError: If project not found or other HTTP errors
        """
        try:
            path = f"/projects/{project_id}"
            logger.info(f"Fetching project details for project {project_id}")
            
            # Make the request
            project_data = await self.get(path)
            
            logger.info(f"Successfully retrieved project {project_id}")
            return project_data
            
        except httpx.HTTPStatusError as e:
            logger.error(
                f"Error fetching project {project_id}: {e.response.status_code}"
            )
            raise
