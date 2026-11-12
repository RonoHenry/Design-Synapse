"""
Service Integration Tests (TDD)

Following TDD methodology - these tests define expected behavior
for cross-service communication and workflows.
"""
import asyncio
from typing import Any, Dict

import pytest
from httpx import AsyncClient


class TestAuthenticationFlow:
    """Test authentication flow across services."""

    async def test_user_authentication_creates_valid_token(self, service_clients):
        """
        Test that user authentication creates a valid token that works across services.

        Expected behavior:
        - User can authenticate with user-service
        - Token can be used to access protected endpoints in other services
        - Token contains proper user information
        """
        # This test will fail initially - we need authentication flow
        user_client = service_clients["user-service"]
        project_client = service_clients["project-service"]

        # Create a test user
        user_data = {
            "email": "test@example.com",
            "password": "testpassword123",
            "first_name": "Test",
            "last_name": "User",
        }

        created_user = await user_client.post("/api/v1/users", json=user_data)
        assert created_user["email"] == user_data["email"]

        # Authenticate user
        auth_response = await user_client.post(
            "/api/v1/auth/login",
            json={"email": user_data["email"], "password": user_data["password"]},
        )

        assert "access_token" in auth_response
        assert "token_type" in auth_response
        token = auth_response["access_token"]

        # Use token to access project service
        headers = {"Authorization": f"Bearer {token}"}
        projects_response = await project_client.get(
            "/api/v1/projects", headers=headers
        )

        # Should return projects list (empty is fine)
        assert isinstance(projects_response, list)

    async def test_invalid_token_rejected_by_all_services(self, service_clients):
        """
        Test that invalid tokens are rejected by all services.

        Expected behavior:
        - Invalid token should return 401 Unauthorized
        - Error response should be consistent across services
        """
        # This test will fail initially - we need token validation
        invalid_token = "invalid.jwt.token"
        headers = {"Authorization": f"Bearer {invalid_token}"}

        for service_name, client in service_clients.items():
            if service_name == "user-service":
                endpoint = "/api/v1/users"
            elif service_name == "project-service":
                endpoint = "/api/v1/projects"
            elif service_name == "knowledge-service":
                endpoint = "/api/v1/resources"
            else:
                continue

            response = await client.get(endpoint, headers=headers)

            # Should return 401 for invalid token
            assert response.status_code == 401

            # Error response should be consistent
            error_data = response.json()
            assert "error_code" in error_data
            assert error_data["error_code"] == "AUTHENTICATION_ERROR"

    async def test_expired_token_handling(self, service_clients):
        """
        Test that expired tokens are handled consistently.

        Expected behavior:
        - Expired token should return 401 Unauthorized
        - Error message should indicate token expiration
        """
        # This test will fail initially - we need token expiration handling
        pass  # Implementation needed


class TestCrossServiceWorkflows:
    """Test workflows that span multiple services."""

    async def test_project_creation_with_resource_addition(
        self, service_clients, test_data_factory
    ):
        """
        Test complete workflow: create project → add resources → create citations.

        Expected behavior:
        - User can create project in project-service
        - User can upload resource to knowledge-service
        - User can create citation linking resource to project
        - All operations should be atomic and consistent
        """
        # This test will fail initially - we need cross-service workflow
        user_client = service_clients["user-service"]
        project_client = service_clients["project-service"]
        knowledge_client = service_clients["knowledge-service"]

        # Create and authenticate user
        user_data = await test_data_factory.create_user()
        token = await test_data_factory.authenticate_user(
            user_data["email"], "testpassword123"
        )
        headers = {"Authorization": f"Bearer {token}"}

        # Create project
        project_data = {
            "name": "Test Project",
            "description": "A test project for integration testing",
            "status": "active",
        }

        project_response = await project_client.post(
            "/api/v1/projects", json=project_data, headers=headers
        )
        assert project_response["name"] == project_data["name"]
        project_id = project_response["id"]

        # Upload resource to knowledge service
        resource_data = {
            "title": "Test Resource",
            "description": "A test resource for the project",
            "content_type": "pdf",
            "source_url": "https://example.com/test.pdf",
        }

        resource_response = await knowledge_client.post(
            "/api/v1/resources", json=resource_data, headers=headers
        )
        assert resource_response["title"] == resource_data["title"]
        resource_id = resource_response["id"]

        # Create citation linking resource to project
        citation_data = {
            "resource_id": resource_id,
            "project_id": project_id,
            "context": "This resource is relevant to the project requirements",
        }

        citation_response = await knowledge_client.post(
            "/api/v1/citations", json=citation_data, headers=headers
        )
        assert citation_response["resource_id"] == resource_id
        assert citation_response["project_id"] == project_id

        # Verify project shows linked resources
        project_resources = await knowledge_client.get(
            f"/api/v1/projects/{project_id}/resources", headers=headers
        )
        assert len(project_resources) == 1
        assert project_resources[0]["id"] == resource_id

    async def test_user_role_based_access_across_services(
        self, service_clients, test_data_factory
    ):
        """
        Test that user roles are respected across all services.

        Expected behavior:
        - Admin users can access all resources
        - Regular users can only access their own resources
        - Role-based permissions are consistent across services
        """
        # This test will fail initially - we need role-based access control
        user_client = service_clients["user-service"]
        project_client = service_clients["project-service"]

        # Create admin user
        admin_data = await test_data_factory.create_admin_user()
        admin_token = await test_data_factory.authenticate_user(
            admin_data["email"], "adminpassword123"
        )
        admin_headers = {"Authorization": f"Bearer {admin_token}"}

        # Create regular user
        user_data = await test_data_factory.create_user()
        user_token = await test_data_factory.authenticate_user(
            user_data["email"], "testpassword123"
        )
        user_headers = {"Authorization": f"Bearer {user_token}"}

        # Create project as regular user
        project_data = {
            "name": "User Project",
            "description": "A project created by regular user",
        }

        user_project = await project_client.post(
            "/api/v1/projects", json=project_data, headers=user_headers
        )
        project_id = user_project["id"]

        # Admin should be able to access user's project
        admin_access = await project_client.get(
            f"/api/v1/projects/{project_id}", headers=admin_headers
        )
        assert admin_access["id"] == project_id

        # Regular user should only see their own projects
        user_projects = await project_client.get(
            "/api/v1/projects", headers=user_headers
        )
        user_project_ids = [p["id"] for p in user_projects]
        assert project_id in user_project_ids


class TestServiceCommunication:
    """Test service-to-service communication using HTTP clients."""

    async def test_user_service_client_operations(self, service_clients):
        """
        Test UserServiceClient operations work correctly.

        Expected behavior:
        - Client can perform CRUD operations
        - Proper error handling for invalid requests
        - Consistent response formats
        """
        # This test will fail initially - we need client implementation
        from packages.common.http.clients import UserServiceClient

        client = UserServiceClient()

        # Test user creation
        user_data = {
            "email": "client-test@example.com",
            "password": "testpassword123",
            "first_name": "Client",
            "last_name": "Test",
        }

        created_user = await client.create_user(user_data)
        assert created_user["email"] == user_data["email"]
        user_id = created_user["id"]

        # Test user retrieval
        retrieved_user = await client.get_user(user_id)
        assert retrieved_user["id"] == user_id
        assert retrieved_user["email"] == user_data["email"]

        # Test user update
        update_data = {"first_name": "Updated"}
        updated_user = await client.update_user(user_id, update_data)
        assert updated_user["first_name"] == "Updated"

        # Test authentication
        auth_result = await client.authenticate(
            user_data["email"], user_data["password"]
        )
        assert "access_token" in auth_result

        # Test user deletion
        await client.delete_user(user_id)

        # Verify user is deleted
        with pytest.raises(Exception):  # Should raise 404 or similar
            await client.get_user(user_id)

    async def test_project_service_client_operations(
        self, service_clients, test_data_factory
    ):
        """
        Test ProjectServiceClient operations work correctly.

        Expected behavior:
        - Client can manage projects and comments
        - Proper authentication handling
        - Error handling for invalid operations
        """
        # This test will fail initially - we need client implementation
        from packages.common.http.clients import ProjectServiceClient

        client = ProjectServiceClient()

        # Create authenticated user
        user_data = await test_data_factory.create_user()
        token = await test_data_factory.authenticate_user(
            user_data["email"], "testpassword123"
        )

        # Test project creation
        project_data = {
            "name": "Client Test Project",
            "description": "Testing project client operations",
        }

        created_project = await client.create_project(project_data)
        assert created_project["name"] == project_data["name"]
        project_id = created_project["id"]

        # Test project retrieval
        retrieved_project = await client.get_project(project_id)
        assert retrieved_project["id"] == project_id

        # Test project listing
        projects = await client.list_projects()
        project_ids = [p["id"] for p in projects]
        assert project_id in project_ids

        # Test comment creation
        comment_data = {
            "content": "This is a test comment",
            "author_id": user_data["id"],
        }

        created_comment = await client.create_comment(project_id, comment_data)
        assert created_comment["content"] == comment_data["content"]

        # Test getting project comments
        comments = await client.get_project_comments(project_id)
        assert len(comments) == 1
        assert comments[0]["content"] == comment_data["content"]

    async def test_knowledge_service_client_operations(
        self, service_clients, test_data_factory
    ):
        """
        Test KnowledgeServiceClient operations work correctly.

        Expected behavior:
        - Client can manage resources and citations
        - Search functionality works properly
        - Recommendations are generated correctly
        """
        # This test will fail initially - we need client implementation
        from packages.common.http.clients import KnowledgeServiceClient

        client = KnowledgeServiceClient()

        # Create authenticated user and project
        user_data = await test_data_factory.create_user()
        token = await test_data_factory.authenticate_user(
            user_data["email"], "testpassword123"
        )
        project_data = await test_data_factory.create_project(user_data["id"])

        # Test resource creation
        resource_data = {
            "title": "Client Test Resource",
            "description": "Testing knowledge client operations",
            "content_type": "pdf",
            "source_url": "https://example.com/client-test.pdf",
        }

        created_resource = await client.create_resource(resource_data)
        assert created_resource["title"] == resource_data["title"]
        resource_id = created_resource["id"]

        # Test resource retrieval
        retrieved_resource = await client.get_resource(resource_id)
        assert retrieved_resource["id"] == resource_id

        # Test resource search
        search_results = await client.search_resources("Client Test")
        assert len(search_results["results"]) > 0

        # Test citation creation
        citation = await client.create_citation(
            resource_id=resource_id,
            project_id=project_data["id"],
            context="Testing citation creation",
        )
        assert citation["resource_id"] == resource_id
        assert citation["project_id"] == project_data["id"]

        # Test getting project resources
        project_resources = await client.get_project_resources(project_data["id"])
        assert len(project_resources) == 1
        assert project_resources[0]["id"] == resource_id

        # Test recommendations
        recommendations = await client.get_recommendations(project_data["id"])
        assert isinstance(recommendations, list)


class TestErrorResponseConsistency:
    """Test that error responses are consistent across services."""

    async def test_validation_error_format_consistency(self, service_clients):
        """
        Test that validation errors have consistent format across services.

        Expected behavior:
        - All services return same error structure for validation failures
        - Error codes are consistent
        - Field-level validation details are provided
        """
        # This test will fail initially - we need consistent error handling
        validation_test_cases = [
            {
                "service": "user-service",
                "endpoint": "/api/v1/users",
                "invalid_data": {"email": "invalid-email", "password": ""},
            },
            {
                "service": "project-service",
                "endpoint": "/api/v1/projects",
                "invalid_data": {"name": "", "description": "x" * 2000},  # Too long
            },
            {
                "service": "knowledge-service",
                "endpoint": "/api/v1/resources",
                "invalid_data": {"title": "", "source_url": "not-a-url"},
            },
        ]

        for test_case in validation_test_cases:
            client = service_clients[test_case["service"]]

            response = await client.post(
                test_case["endpoint"], json=test_case["invalid_data"]
            )

            # Should return 422 for validation errors
            assert response.status_code == 422

            error_data = response.json()

            # Check consistent error structure
            assert "error_code" in error_data
            assert error_data["error_code"] == "VALIDATION_ERROR"
            assert "message" in error_data
            assert "details" in error_data
            assert isinstance(error_data["details"], list)

            # Check field-level details
            for detail in error_data["details"]:
                assert "field" in detail
                assert "message" in detail

    async def test_not_found_error_consistency(self, service_clients):
        """
        Test that 404 errors are consistent across services.

        Expected behavior:
        - All services return same error structure for not found
        - Error codes are consistent
        - Helpful error messages are provided
        """
        # This test will fail initially - we need consistent 404 handling
        not_found_test_cases = [
            {"service": "user-service", "endpoint": "/api/v1/users/99999"},
            {"service": "project-service", "endpoint": "/api/v1/projects/99999"},
            {"service": "knowledge-service", "endpoint": "/api/v1/resources/99999"},
        ]

        for test_case in not_found_test_cases:
            client = service_clients[test_case["service"]]

            response = await client.get(test_case["endpoint"])

            # Should return 404
            assert response.status_code == 404

            error_data = response.json()

            # Check consistent error structure
            assert "error_code" in error_data
            assert error_data["error_code"] == "NOT_FOUND"
            assert "message" in error_data
            assert "service" in error_data
            assert error_data["service"] == test_case["service"]

    async def test_server_error_consistency(self, service_clients):
        """
        Test that server errors are handled consistently.

        Expected behavior:
        - 500 errors have consistent format
        - Error tracking information is included
        - Sensitive information is not exposed
        """
        # This test will fail initially - we need consistent 500 handling
        pass  # Implementation needed


class TestServiceHealthChecks:
    """Test service health check endpoints."""

    async def test_all_services_have_health_endpoints(self, service_clients):
        """
        Test that all services have working health endpoints.

        Expected behavior:
        - /health endpoint returns 200 OK
        - Response includes service name and status
        - Response format is consistent
        """
        # This test should pass - health endpoints exist
        for service_name, client in service_clients.items():
            response = await client.get("/api/v1/health")

            assert response.status_code == 200

            health_data = response.json()
            assert "status" in health_data
            assert health_data["status"] == "healthy"
            assert "service" in health_data
            assert health_data["service"] == service_name
            assert "timestamp" in health_data

    async def test_all_services_have_ready_endpoints(self, service_clients):
        """
        Test that all services have working readiness endpoints.

        Expected behavior:
        - /ready endpoint returns 200 OK when ready
        - Response includes dependency status
        - Database connectivity is verified
        """
        # This test should pass - ready endpoints exist
        for service_name, client in service_clients.items():
            response = await client.get("/api/v1/ready")

            assert response.status_code == 200

            ready_data = response.json()
            assert "status" in ready_data
            assert ready_data["status"] == "ready"
            assert "checks" in ready_data
            assert "database" in ready_data["checks"]
            assert ready_data["checks"]["database"]["status"] in ["healthy", "ready"]

    async def test_health_check_includes_dependencies(self, service_clients):
        """
        Test that detailed health checks include dependency status.

        Expected behavior:
        - /health/detailed includes dependency checks
        - External service dependencies are verified
        - Overall health reflects all dependencies
        """
        # This test will partially pass - some endpoints exist
        for service_name, client in service_clients.items():
            response = await client.get("/api/v1/health/detailed")

            if response.status_code == 200:
                health_data = response.json()
                assert "checks" in health_data
                assert "database" in health_data["checks"]

                # Knowledge service should check external dependencies
                if service_name == "knowledge-service":
                    checks = health_data["checks"]
                    # Should have vector search and LLM service checks
                    assert any(
                        "vector" in key or "pinecone" in key for key in checks.keys()
                    )
                    assert any("llm" in key or "openai" in key for key in checks.keys())

    async def test_service_startup_health_progression(self, service_containers):
        """
        Test that services progress through health states during startup.

        Expected behavior:
        - Services start in "starting" state
        - Progress to "ready" when dependencies available
        - Maintain "healthy" during normal operation
        """
        # This test will fail initially - we need startup state tracking
        pass  # Implementation needed
