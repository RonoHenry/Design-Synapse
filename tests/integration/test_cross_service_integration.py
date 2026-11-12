"""Integration tests for cross-service workflows and communication.

These tests follow TDD approach - written first to fail, then infrastructure implemented to pass.
"""

import asyncio
from typing import Any, Dict
from unittest.mock import Mock, patch

import pytest
from fastapi.testclient import TestClient

from .conftest import IntegrationTestHelper, ServiceManager


class TestCrossServiceIntegration:
    """Test cross-service integration workflows."""

    @pytest.mark.asyncio
    @pytest.mark.cross_service
    async def test_user_authentication_across_services(
        self,
        service_manager: ServiceManager,
        user_service_client: TestClient,
        project_service_client: TestClient,
        knowledge_service_client: TestClient,
    ):
        """Test user authentication flow across all services.

        This test should FAIL initially - authentication flow not implemented.
        """
        # Create user in user service
        user_data = {
            "email": "integration@example.com",
            "username": "integrationuser",
            "password": "password123",
            "first_name": "Integration",
            "last_name": "Test",
        }

        # This should fail - endpoint doesn't exist yet
        response = user_service_client.post("/api/v1/users", json=user_data)
        assert response.status_code == 201
        user = response.json()

        # Login to get token
        login_data = {"username": "integrationuser", "password": "password123"}
        response = user_service_client.post("/api/v1/auth/login", json=login_data)
        assert response.status_code == 200
        token = response.json()["access_token"]

        # Use token to access project service
        headers = {"Authorization": f"Bearer {token}"}
        response = project_service_client.get("/api/v1/projects", headers=headers)
        assert response.status_code == 200

        # Use token to access knowledge service
        response = knowledge_service_client.get("/api/v1/resources", headers=headers)
        assert response.status_code == 200

    @pytest.mark.asyncio
    @pytest.mark.cross_service
    async def test_project_creation_with_resource_addition(
        self,
        service_manager: ServiceManager,
        user_service_client: TestClient,
        project_service_client: TestClient,
        knowledge_service_client: TestClient,
    ):
        """Test creating project and adding resources across services.

        This test should FAIL initially - cross-service workflow not implemented.
        """
        # Authenticate user
        token = await self._authenticate_test_user(user_service_client)
        headers = {"Authorization": f"Bearer {token}"}

        # Create project
        project_data = {
            "name": "Integration Test Project",
            "description": "Test project for integration testing",
            "status": "active",
        }

        response = project_service_client.post(
            "/api/v1/projects", json=project_data, headers=headers
        )
        assert response.status_code == 201
        project = response.json()
        project_id = project["id"]

        # Create resource in knowledge service
        resource_data = {
            "title": "Integration Test Resource",
            "description": "Test resource for integration",
            "content_type": "pdf",
            "source_url": "https://example.com/test.pdf",
        }

        response = knowledge_service_client.post(
            "/api/v1/resources", json=resource_data, headers=headers
        )
        assert response.status_code == 201
        resource = response.json()
        resource_id = resource["id"]

        # Add resource to project (cross-service operation)
        citation_data = {
            "resource_id": resource_id,
            "project_id": project_id,
            "context": "Integration test citation",
        }

        response = knowledge_service_client.post(
            "/api/v1/citations", json=citation_data, headers=headers
        )
        assert response.status_code == 201

        # Verify citation exists
        response = knowledge_service_client.get(
            f"/api/v1/projects/{project_id}/citations", headers=headers
        )
        assert response.status_code == 200
        citations = response.json()
        assert len(citations) == 1
        assert citations[0]["resource_id"] == resource_id

    @pytest.mark.asyncio
    @pytest.mark.cross_service
    async def test_service_to_service_communication_using_http_clients(
        self,
        service_manager: ServiceManager,
        user_service_client: TestClient,
        project_service_client: TestClient,
        knowledge_service_client: TestClient,
    ):
        """Test service-to-service communication using HTTP clients.

        This test should FAIL initially - HTTP client communication not implemented.
        """
        # Start all services
        assert service_manager.is_service_running("user-service")
        assert service_manager.is_service_running("project-service")
        assert service_manager.is_service_running("knowledge-service")

        # Test project service calling user service to validate user
        user_id = 1
        response = project_service_client.get(
            f"/api/v1/internal/users/{user_id}/validate"
        )
        assert response.status_code == 200
        user_validation = response.json()
        assert "valid" in user_validation
        assert "user_id" in user_validation

        # Test knowledge service calling project service to validate project
        project_id = 1
        response = knowledge_service_client.get(
            f"/api/v1/internal/projects/{project_id}/validate"
        )
        assert response.status_code == 200
        project_validation = response.json()
        assert "valid" in project_validation
        assert "project_id" in project_validation

    @pytest.mark.asyncio
    @pytest.mark.cross_service
    async def test_consistent_error_response_formats_across_services(
        self,
        service_manager: ServiceManager,
        user_service_client: TestClient,
        project_service_client: TestClient,
        knowledge_service_client: TestClient,
    ):
        """Test that all services return consistent error response formats.

        This test should FAIL initially - consistent error formats not implemented.
        """
        services = [
            ("user-service", user_service_client),
            ("project-service", project_service_client),
            ("knowledge-service", knowledge_service_client),
        ]

        for service_name, client in services:
            # Test 404 error format
            response = client.get("/api/v1/nonexistent")
            assert response.status_code == 404

            error_data = response.json()
            self._assert_standard_error_format(error_data, "not_found")

            # Test validation error format (if applicable)
            if service_name == "user-service":
                invalid_user_data = {"email": "invalid-email"}
                response = client.post("/api/v1/users", json=invalid_user_data)
                assert response.status_code == 422

                error_data = response.json()
                self._assert_standard_error_format(error_data, "validation_error")

    @pytest.mark.asyncio
    @pytest.mark.cross_service
    async def test_service_health_check_coordination(
        self,
        service_manager: ServiceManager,
        user_service_client: TestClient,
        project_service_client: TestClient,
        knowledge_service_client: TestClient,
        integration_helper: IntegrationTestHelper,
    ):
        """Test health check coordination across services.

        This test should FAIL initially - health check coordination not implemented.
        """
        services = [
            ("user-service", user_service_client),
            ("project-service", project_service_client),
            ("knowledge-service", knowledge_service_client),
        ]

        # All services should be healthy
        for service_name, client in services:
            response = client.get("/api/v1/health")
            assert response.status_code == 200

            health_data = response.json()
            integration_helper.assert_health_response_format(health_data, service_name)
            assert health_data["status"] == "healthy"

        # Test aggregate health endpoint (should be implemented)
        response = user_service_client.get("/api/v1/health/aggregate")
        assert response.status_code == 200

        aggregate_health = response.json()
        assert "services" in aggregate_health
        assert "overall_status" in aggregate_health
        assert aggregate_health["overall_status"] == "healthy"

        # Should include health of all services
        assert len(aggregate_health["services"]) == 3

    @pytest.mark.asyncio
    @pytest.mark.cross_service
    async def test_database_transaction_coordination(
        self,
        service_manager: ServiceManager,
        user_service_client: TestClient,
        project_service_client: TestClient,
        knowledge_service_client: TestClient,
    ):
        """Test database transaction coordination across services.

        This test should FAIL initially - transaction coordination not implemented.
        """
        # Authenticate user
        token = await self._authenticate_test_user(user_service_client)
        headers = {"Authorization": f"Bearer {token}"}

        # Start distributed transaction
        transaction_data = {"services": ["project-service", "knowledge-service"]}
        response = user_service_client.post(
            "/api/v1/transactions/begin", json=transaction_data, headers=headers
        )
        assert response.status_code == 201
        transaction_id = response.json()["transaction_id"]

        # Create project within transaction
        project_data = {
            "name": "Transaction Test Project",
            "description": "Test project for transaction coordination",
            "status": "active",
            "transaction_id": transaction_id,
        }

        response = project_service_client.post(
            "/api/v1/projects", json=project_data, headers=headers
        )
        assert response.status_code == 201
        project = response.json()

        # Create resource within same transaction
        resource_data = {
            "title": "Transaction Test Resource",
            "description": "Test resource for transaction",
            "content_type": "pdf",
            "source_url": "https://example.com/transaction-test.pdf",
            "transaction_id": transaction_id,
        }

        response = knowledge_service_client.post(
            "/api/v1/resources", json=resource_data, headers=headers
        )
        assert response.status_code == 201
        resource = response.json()

        # Commit transaction
        response = user_service_client.post(
            f"/api/v1/transactions/{transaction_id}/commit", headers=headers
        )
        assert response.status_code == 200

        # Verify both resources exist
        response = project_service_client.get(
            f"/api/v1/projects/{project['id']}", headers=headers
        )
        assert response.status_code == 200

        response = knowledge_service_client.get(
            f"/api/v1/resources/{resource['id']}", headers=headers
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    @pytest.mark.cross_service
    async def test_service_failure_cascade_prevention(
        self,
        service_manager: ServiceManager,
        user_service_client: TestClient,
        project_service_client: TestClient,
        knowledge_service_client: TestClient,
    ):
        """Test that service failures don't cascade to other services.

        This test should FAIL initially - failure isolation not implemented.
        """
        # Simulate knowledge service failure
        await service_manager.stop_service("knowledge-service")

        # User service should still work
        response = user_service_client.get("/api/v1/health")
        assert response.status_code == 200

        # Project service should still work
        response = project_service_client.get("/api/v1/health")
        assert response.status_code == 200

        # Project service should handle knowledge service unavailability gracefully
        token = await self._authenticate_test_user(user_service_client)
        headers = {"Authorization": f"Bearer {token}"}

        project_data = {
            "name": "Failure Test Project",
            "description": "Test project during service failure",
            "status": "active",
        }

        response = project_service_client.post(
            "/api/v1/projects", json=project_data, headers=headers
        )
        assert response.status_code == 201

        # Should indicate degraded functionality
        response = project_service_client.get("/api/v1/health")
        health_data = response.json()
        assert health_data["status"] in ["healthy", "degraded"]

    async def _authenticate_test_user(self, user_service_client: TestClient) -> str:
        """Helper to authenticate a test user and return token."""
        # Create test user
        user_data = {
            "email": "testuser@example.com",
            "username": "testuser",
            "password": "password123",
            "first_name": "Test",
            "last_name": "User",
        }

        response = user_service_client.post("/api/v1/users", json=user_data)
        if response.status_code != 201:
            # User might already exist, try to login
            pass

        # Login to get token
        login_data = {"username": "testuser", "password": "password123"}
        response = user_service_client.post("/api/v1/auth/login", json=login_data)
        assert response.status_code == 200
        return response.json()["access_token"]

    def _assert_standard_error_format(
        self, error_data: Dict[str, Any], expected_error_type: str
    ):
        """Assert error response has standard format."""
        assert "error_type" in error_data
        assert "message" in error_data
        assert "timestamp" in error_data
        assert error_data["error_type"] == expected_error_type

        if expected_error_type == "validation_error":
            assert "details" in error_data
            assert isinstance(error_data["details"], list)
