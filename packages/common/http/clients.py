"""Typed HTTP clients for each service."""

from typing import Any, Dict, List, Optional

from .base_client import BaseHTTPClient
from .service_registry import get_service_registry, ServiceName


class UserServiceClient(BaseHTTPClient):
    """HTTP client for User Service."""
    
    def __init__(self, **kwargs):
        """Initialize User Service client."""
        registry = get_service_registry()
        base_url = registry.get_base_url(ServiceName.USER_SERVICE.value)
        super().__init__(base_url=base_url, **kwargs)
    
    async def get_user(self, user_id: int) -> Dict[str, Any]:
        """Get user by ID.
        
        Args:
            user_id: User ID
            
        Returns:
            User data
        """
        return await self.get(f"/users/{user_id}")
    
    async def create_user(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new user.
        
        Args:
            user_data: User data
            
        Returns:
            Created user data
        """
        return await self.post("/users", json=user_data)
    
    async def update_user(self, user_id: int, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update user.
        
        Args:
            user_id: User ID
            user_data: Updated user data
            
        Returns:
            Updated user data
        """
        return await self.put(f"/users/{user_id}", json=user_data)
    
    async def delete_user(self, user_id: int) -> None:
        """Delete user.
        
        Args:
            user_id: User ID
        """
        await self.delete(f"/users/{user_id}")
    
    async def authenticate(self, email: str, password: str) -> Dict[str, Any]:
        """Authenticate user.
        
        Args:
            email: User email
            password: User password
            
        Returns:
            Authentication token data
        """
        return await self.post("/auth/login", json={"email": email, "password": password})
    
    async def get_user_roles(self, user_id: int) -> List[Dict[str, Any]]:
        """Get user roles.
        
        Args:
            user_id: User ID
            
        Returns:
            List of user roles
        """
        return await self.get(f"/users/{user_id}/roles")


class ProjectServiceClient(BaseHTTPClient):
    """HTTP client for Project Service."""
    
    def __init__(self, **kwargs):
        """Initialize Project Service client."""
        registry = get_service_registry()
        base_url = registry.get_base_url(ServiceName.PROJECT_SERVICE.value)
        super().__init__(base_url=base_url, **kwargs)
    
    async def get_project(self, project_id: int) -> Dict[str, Any]:
        """Get project by ID.
        
        Args:
            project_id: Project ID
            
        Returns:
            Project data
        """
        return await self.get(f"/projects/{project_id}")
    
    async def create_project(self, project_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new project.
        
        Args:
            project_data: Project data
            
        Returns:
            Created project data
        """
        return await self.post("/projects", json=project_data)
    
    async def update_project(self, project_id: int, project_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update project.
        
        Args:
            project_id: Project ID
            project_data: Updated project data
            
        Returns:
            Updated project data
        """
        return await self.put(f"/projects/{project_id}", json=project_data)
    
    async def delete_project(self, project_id: int) -> None:
        """Delete project.
        
        Args:
            project_id: Project ID
        """
        await self.delete(f"/projects/{project_id}")
    
    async def list_projects(self, skip: int = 0, limit: int = 100) -> List[Dict[str, Any]]:
        """List projects.
        
        Args:
            skip: Number of projects to skip
            limit: Maximum number of projects to return
            
        Returns:
            List of projects
        """
        return await self.get(f"/projects?skip={skip}&limit={limit}")
    
    async def get_project_comments(self, project_id: int) -> List[Dict[str, Any]]:
        """Get project comments.
        
        Args:
            project_id: Project ID
            
        Returns:
            List of comments
        """
        return await self.get(f"/projects/{project_id}/comments")
    
    async def create_comment(self, project_id: int, comment_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a comment on a project.
        
        Args:
            project_id: Project ID
            comment_data: Comment data
            
        Returns:
            Created comment data
        """
        return await self.post(f"/projects/{project_id}/comments", json=comment_data)


class KnowledgeServiceClient(BaseHTTPClient):
    """HTTP client for Knowledge Service."""
    
    def __init__(self, **kwargs):
        """Initialize Knowledge Service client."""
        registry = get_service_registry()
        base_url = registry.get_base_url(ServiceName.KNOWLEDGE_SERVICE.value)
        super().__init__(base_url=base_url, **kwargs)
    
    async def get_resource(self, resource_id: int) -> Dict[str, Any]:
        """Get resource by ID.
        
        Args:
            resource_id: Resource ID
            
        Returns:
            Resource data
        """
        return await self.get(f"/resources/{resource_id}")
    
    async def create_resource(self, resource_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new resource.
        
        Args:
            resource_data: Resource data
            
        Returns:
            Created resource data
        """
        return await self.post("/resources", json=resource_data)
    
    async def search_resources(
        self,
        query: str,
        resource_type: Optional[str] = None,
        limit: int = 20
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
        return await self.get(f"/search?{query_string}")
    
    async def get_project_resources(self, project_id: int) -> List[Dict[str, Any]]:
        """Get resources linked to a project.
        
        Args:
            project_id: Project ID
            
        Returns:
            List of resources
        """
        return await self.get(f"/projects/{project_id}/resources")
    
    async def create_citation(
        self,
        resource_id: int,
        project_id: int,
        context: str
    ) -> Dict[str, Any]:
        """Create a citation linking a resource to a project.
        
        Args:
            resource_id: Resource ID
            project_id: Project ID
            context: Citation context
            
        Returns:
            Created citation data
        """
        return await self.post(
            "/citations",
            json={
                "resource_id": resource_id,
                "project_id": project_id,
                "context": context
            }
        )
    
    async def get_recommendations(self, project_id: int) -> List[Dict[str, Any]]:
        """Get resource recommendations for a project.
        
        Args:
            project_id: Project ID
            
        Returns:
            List of recommended resources
        """
        return await self.get(f"/projects/{project_id}/recommendations")
