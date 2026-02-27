"""Typed HTTP clients for each service."""

from typing import Any, Dict, List, Optional

from .base_client import BaseHTTPClient
from .service_registry import ServiceName, get_service_registry


class UserServiceClient(BaseHTTPClient):
    """HTTP client for User Service."""

    def __init__(self, base_url: Optional[str] = None, **kwargs):
        """Initialize User Service client.

        Args:
            base_url: Optional base URL override. If not provided, uses service registry.
        """
        if base_url is None:
            registry = get_service_registry()
            base_url = registry.get_base_url(ServiceName.USER_SERVICE.value)
        super().__init__(base_url=base_url, **kwargs)

    def set_auth_token(self, token: str) -> None:
        """Set authentication token for requests."""
        self.headers["Authorization"] = f"Bearer {token}"

    async def get_user(self, user_id: int) -> Dict[str, Any]:
        """Get user by ID.

        Args:
            user_id: User ID

        Returns:
            User data
        """
        response = await self.get(f"/api/v1/users/{user_id}")
        response.raise_for_status()
        return response.json()

    async def create_user(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new user.

        Args:
            user_data: User data

        Returns:
            Created user data
        """
        response = await self.post("/api/v1/users", json=user_data)
        response.raise_for_status()
        return response.json()

    async def update_user(
        self, user_id: int, user_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update user.

        Args:
            user_id: User ID
            user_data: Updated user data

        Returns:
            Updated user data
        """
        response = await self.put(f"/api/v1/users/{user_id}", json=user_data)
        response.raise_for_status()
        return response.json()

    async def delete_user(self, user_id: int) -> None:
        """Delete user.

        Args:
            user_id: User ID
        """
        response = await self.delete(f"/api/v1/users/{user_id}")
        response.raise_for_status()

    async def authenticate(self, email: str, password: str) -> Dict[str, Any]:
        """Authenticate user.

        Args:
            email: User email
            password: User password

        Returns:
            Authentication token data
        """
        response = await self.post(
            "/api/v1/auth/login", json={"email": email, "password": password}
        )
        response.raise_for_status()
        return response.json()

    async def get_user_roles(self, user_id: int) -> List[Dict[str, Any]]:
        """Get user roles.

        Args:
            user_id: User ID

        Returns:
            List of user roles
        """
        response = await self.get(f"/api/v1/users/{user_id}/roles")
        response.raise_for_status()
        return response.json()


class ProjectServiceClient(BaseHTTPClient):
    """HTTP client for Project Service."""

    def __init__(self, base_url: Optional[str] = None, **kwargs):
        """Initialize Project Service client.

        Args:
            base_url: Optional base URL override. If not provided, uses service registry.
        """
        if base_url is None:
            registry = get_service_registry()
            base_url = registry.get_base_url(ServiceName.PROJECT_SERVICE.value)
        super().__init__(base_url=base_url, **kwargs)

    def set_auth_token(self, token: str) -> None:
        """Set authentication token for requests."""
        self.headers["Authorization"] = f"Bearer {token}"

    async def get_project(self, project_id: int) -> Dict[str, Any]:
        """Get project by ID.

        Args:
            project_id: Project ID

        Returns:
            Project data
        """
        response = await self.get(f"/api/v1/projects/{project_id}")
        response.raise_for_status()
        return response.json()

    async def create_project(self, project_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new project.

        Args:
            project_data: Project data

        Returns:
            Created project data
        """
        response = await self.post("/api/v1/projects", json=project_data)
        response.raise_for_status()
        return response.json()

    async def update_project(
        self, project_id: int, project_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update project.

        Args:
            project_id: Project ID
            project_data: Updated project data

        Returns:
            Updated project data
        """
        response = await self.put(f"/api/v1/projects/{project_id}", json=project_data)
        response.raise_for_status()
        return response.json()

    async def delete_project(self, project_id: int) -> None:
        """Delete project.

        Args:
            project_id: Project ID
        """
        response = await self.delete(f"/api/v1/projects/{project_id}")
        response.raise_for_status()

    async def list_projects(
        self, skip: int = 0, limit: int = 100
    ) -> List[Dict[str, Any]]:
        """List projects.

        Args:
            skip: Number of projects to skip
            limit: Maximum number of projects to return

        Returns:
            List of projects
        """
        response = await self.get(f"/api/v1/projects?skip={skip}&limit={limit}")
        response.raise_for_status()
        return response.json()

    async def get_project_comments(self, project_id: int) -> List[Dict[str, Any]]:
        """Get project comments.

        Args:
            project_id: Project ID

        Returns:
            List of comments
        """
        response = await self.get(f"/api/v1/projects/{project_id}/comments")
        response.raise_for_status()
        return response.json()

    async def create_comment(
        self, project_id: int, comment_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create a comment on a project.

        Args:
            project_id: Project ID
            comment_data: Comment data

        Returns:
            Created comment data
        """
        response = await self.post(
            f"/api/v1/projects/{project_id}/comments", json=comment_data
        )
        response.raise_for_status()
        return response.json()


class KnowledgeServiceClient(BaseHTTPClient):
    """HTTP client for Knowledge Service."""

    def __init__(self, base_url: Optional[str] = None, **kwargs):
        """Initialize Knowledge Service client.

        Args:
            base_url: Optional base URL override. If not provided, uses service registry.
        """
        if base_url is None:
            registry = get_service_registry()
            base_url = registry.get_base_url(ServiceName.KNOWLEDGE_SERVICE.value)
        super().__init__(base_url=base_url, **kwargs)

    def set_auth_token(self, token: str) -> None:
        """Set authentication token for requests."""
        self.headers["Authorization"] = f"Bearer {token}"

    async def get_resource(self, resource_id: int) -> Dict[str, Any]:
        """Get resource by ID.

        Args:
            resource_id: Resource ID

        Returns:
            Resource data
        """
        response = await self.get(f"/api/v1/resources/{resource_id}")
        response.raise_for_status()
        return response.json()

    async def create_resource(self, resource_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new resource.

        Args:
            resource_data: Resource data

        Returns:
            Created resource data
        """
        response = await self.post("/api/v1/resources", json=resource_data)
        response.raise_for_status()
        return response.json()

    async def search_resources(
        self, query: str, resource_type: Optional[str] = None, limit: int = 20
    ) -> Dict[str, Any]:
        """Search resources.

        Args:
            query: Search query
            resource_type: Optional resource type filter
            limit: Maximum number of results

        Returns:
            Search results
        """
        params = {"query": query, "limit": limit}
        if resource_type:
            params["resource_type"] = resource_type

        query_string = "&".join(f"{k}={v}" for k, v in params.items())
        response = await self.get(f"/api/v1/search?{query_string}")
        response.raise_for_status()
        return response.json()

    async def get_project_resources(self, project_id: int) -> List[Dict[str, Any]]:
        """Get resources linked to a project.

        Args:
            project_id: Project ID

        Returns:
            List of resources
        """
        response = await self.get(f"/api/v1/projects/{project_id}/resources")
        response.raise_for_status()
        return response.json()

    async def create_citation(
        self, resource_id: int, project_id: int, context: str
    ) -> Dict[str, Any]:
        """Create a citation linking a resource to a project.

        Args:
            resource_id: Resource ID
            project_id: Project ID
            context: Citation context

        Returns:
            Created citation data
        """
        response = await self.post(
            "/api/v1/citations",
            json={
                "resource_id": resource_id,
                "project_id": project_id,
                "context": context,
            },
        )
        response.raise_for_status()
        return response.json()

    async def get_recommendations(self, project_id: int) -> List[Dict[str, Any]]:
        """Get resource recommendations for a project.

        Args:
            project_id: Project ID

        Returns:
            List of recommended resources
        """
        response = await self.get(f"/api/v1/projects/{project_id}/recommendations")
        response.raise_for_status()
        return response.json()
