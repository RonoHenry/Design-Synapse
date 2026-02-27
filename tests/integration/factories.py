"""
Integration test data factory for cross-service testing.

This factory creates test data that spans multiple services
and handles the complexity of cross-service relationships.
"""
import asyncio
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional


class IntegrationTestFactory:
    """Factory for creating test data across services."""

    def __init__(self):
        """Initialize the factory."""
        self.created_users: List[Dict[str, Any]] = []
        self.created_projects: List[Dict[str, Any]] = []
        self.created_resources: List[Dict[str, Any]] = []
        self.created_citations: List[Dict[str, Any]] = []
        self.auth_tokens: Dict[str, str] = {}

    async def create_user(self, **kwargs) -> Dict[str, Any]:
        """
        Create a test user.

        Args:
            **kwargs: User data overrides

        Returns:
            Created user data
        """
        # This will fail initially - we need user creation implementation
        unique_id = str(uuid.uuid4())[:8]

        default_data = {
            "email": f"test-user-{unique_id}@example.com",
            "password": "testpassword123",
            "first_name": "Test",
            "last_name": f"User{unique_id}",
            "is_active": True,
        }

        user_data = {**default_data, **kwargs}

        # This would make HTTP request to user service
        # For now, return mock data that tests expect
        created_user = {
            "id": len(self.created_users) + 1,
            "email": user_data["email"],
            "first_name": user_data["first_name"],
            "last_name": user_data["last_name"],
            "is_active": user_data["is_active"],
            "created_at": datetime.utcnow().isoformat(),
            "roles": ["user"],
        }

        self.created_users.append(created_user)
        return created_user

    async def create_admin_user(self, **kwargs) -> Dict[str, Any]:
        """
        Create a test admin user.

        Args:
            **kwargs: User data overrides

        Returns:
            Created admin user data
        """
        # This will fail initially - we need admin user creation
        unique_id = str(uuid.uuid4())[:8]

        default_data = {
            "email": f"admin-{unique_id}@example.com",
            "password": "adminpassword123",
            "first_name": "Admin",
            "last_name": f"User{unique_id}",
            "is_active": True,
            "roles": ["admin", "user"],
        }

        user_data = {**default_data, **kwargs}

        created_user = {
            "id": len(self.created_users) + 1000,  # Different ID range for admins
            "email": user_data["email"],
            "first_name": user_data["first_name"],
            "last_name": user_data["last_name"],
            "is_active": user_data["is_active"],
            "created_at": datetime.utcnow().isoformat(),
            "roles": user_data["roles"],
        }

        self.created_users.append(created_user)
        return created_user

    async def authenticate_user(self, email: str, password: str) -> str:
        """
        Authenticate a user and return access token.

        Args:
            email: User email
            password: User password

        Returns:
            Access token
        """
        # This will fail initially - we need authentication implementation
        if email in self.auth_tokens:
            return self.auth_tokens[email]

        # Mock token generation
        token = f"mock-jwt-token-{str(uuid.uuid4())}"
        self.auth_tokens[email] = token

        return token

    async def create_project(self, user_id: int, **kwargs) -> Dict[str, Any]:
        """
        Create a test project.

        Args:
            user_id: ID of the user creating the project
            **kwargs: Project data overrides

        Returns:
            Created project data
        """
        # This will fail initially - we need project creation implementation
        unique_id = str(uuid.uuid4())[:8]

        default_data = {
            "name": f"Test Project {unique_id}",
            "description": f"A test project created for integration testing - {unique_id}",
            "status": "active",
            "owner_id": user_id,
        }

        project_data = {**default_data, **kwargs}

        created_project = {
            "id": len(self.created_projects) + 1,
            "name": project_data["name"],
            "description": project_data["description"],
            "status": project_data["status"],
            "owner_id": project_data["owner_id"],
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
        }

        self.created_projects.append(created_project)
        return created_project

    async def create_resource(self, **kwargs) -> Dict[str, Any]:
        """
        Create a test resource.

        Args:
            **kwargs: Resource data overrides

        Returns:
            Created resource data
        """
        # This will fail initially - we need resource creation implementation
        unique_id = str(uuid.uuid4())[:8]

        default_data = {
            "title": f"Test Resource {unique_id}",
            "description": f"A test resource for integration testing - {unique_id}",
            "content_type": "pdf",
            "source_url": f"https://example.com/test-resource-{unique_id}.pdf",
            "storage_path": f"/storage/test-resource-{unique_id}.pdf",
        }

        resource_data = {**default_data, **kwargs}

        created_resource = {
            "id": len(self.created_resources) + 1,
            "title": resource_data["title"],
            "description": resource_data["description"],
            "content_type": resource_data["content_type"],
            "source_url": resource_data["source_url"],
            "storage_path": resource_data["storage_path"],
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
        }

        self.created_resources.append(created_resource)
        return created_resource

    async def create_citation(
        self, resource_id: int, project_id: int, **kwargs
    ) -> Dict[str, Any]:
        """
        Create a test citation linking a resource to a project.

        Args:
            resource_id: ID of the resource
            project_id: ID of the project
            **kwargs: Citation data overrides

        Returns:
            Created citation data
        """
        # This will fail initially - we need citation creation implementation
        default_data = {
            "resource_id": resource_id,
            "project_id": project_id,
            "context": "This resource is relevant to the project for testing purposes",
            "created_by": 1,  # Default user ID
        }

        citation_data = {**default_data, **kwargs}

        created_citation = {
            "id": len(self.created_citations) + 1,
            "resource_id": citation_data["resource_id"],
            "project_id": citation_data["project_id"],
            "context": citation_data["context"],
            "created_by": citation_data["created_by"],
            "created_at": datetime.utcnow().isoformat(),
        }

        self.created_citations.append(created_citation)
        return created_citation

    async def create_complete_workflow_data(self) -> Dict[str, Any]:
        """
        Create a complete set of test data for workflow testing.

        Returns:
            Dictionary containing user, project, resource, and citation data
        """
        # This will fail initially - we need complete workflow implementation

        # Create user
        user = await self.create_user()

        # Authenticate user
        token = await self.authenticate_user(user["email"], "testpassword123")

        # Create project
        project = await self.create_project(user["id"])

        # Create resource
        resource = await self.create_resource()

        # Create citation
        citation = await self.create_citation(resource["id"], project["id"])

        return {
            "user": user,
            "token": token,
            "project": project,
            "resource": resource,
            "citation": citation,
        }

    def cleanup(self):
        """
        Clean up all created test data.

        This method should be called after tests complete
        to ensure no test data persists.
        """
        # This will fail initially - we need cleanup implementation

        # In a real implementation, this would:
        # 1. Delete all created citations
        # 2. Delete all created resources
        # 3. Delete all created projects
        # 4. Delete all created users
        # 5. Clear any cached tokens

        # For now, just clear the local tracking
        self.created_users.clear()
        self.created_projects.clear()
        self.created_resources.clear()
        self.created_citations.clear()
        self.auth_tokens.clear()

    async def wait_for_services_ready(
        self, service_clients: Dict[str, Any], timeout: int = 60
    ):
        """
        Wait for all services to be ready before running tests.

        Args:
            service_clients: Dictionary of service clients
            timeout: Maximum time to wait in seconds
        """
        # This will fail initially - we need service readiness checking
        start_time = asyncio.get_event_loop().time()

        while True:
            all_ready = True

            for service_name, client in service_clients.items():
                try:
                    response = await client.get("/api/v1/ready")
                    if response.status_code != 200:
                        all_ready = False
                        break
                except Exception:
                    all_ready = False
                    break

            if all_ready:
                return

            if asyncio.get_event_loop().time() - start_time > timeout:
                raise TimeoutError(f"Services not ready after {timeout} seconds")

            await asyncio.sleep(1)
