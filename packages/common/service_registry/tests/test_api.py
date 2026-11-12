"""Tests for Service Registry API endpoints."""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from ..api import router
from ..models import (HealthStatus, ServiceEndpoint, ServiceInfo,
                      ServiceRegistrationRequest, SystemHealthStatus)


@pytest.fixture
def app():
    """Create FastAPI app with service registry router."""
    app = FastAPI()
    app.include_router(router)
    return app


@pytest.fixture
def client(app):
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def sample_service_info():
    """Create sample service info."""
    return ServiceInfo(
        name="test-service",
        version="1.0.0",
        host="localhost",
        port=8000,
        health_check_url="/health",
        metadata={"env": "test"},
        tags=["api", "web"],
    )


@pytest.fixture
def sample_registration_request(sample_service_info):
    """Create sample registration request."""
    return ServiceRegistrationRequest(
        service=sample_service_info, health_check_interval=30, failure_threshold=3
    )


class TestServiceRegistryAPI:
    """Test Service Registry API endpoints."""

    def test_register_service_success(self, client, sample_registration_request):
        """Test successful service registration."""
        mock_registry = AsyncMock()
        mock_registry.register_service.return_value = "instance-123"

        with patch(
            "packages.common.service_registry.api.get_service_registry",
            return_value=mock_registry,
        ):
            response = client.post(
                "/registry/register", json=sample_registration_request.model_dump()
            )

            assert response.status_code == 200
            data = response.json()
            assert data["instance_id"] == "instance-123"
            assert "registered successfully" in data["message"]

    def test_register_service_failure(self, client, sample_registration_request):
        """Test service registration failure."""
        mock_registry = AsyncMock()
        mock_registry.register_service.side_effect = Exception("Registration failed")

        with patch(
            "packages.common.service_registry.api.get_service_registry",
            return_value=mock_registry,
        ):
            response = client.post(
                "/registry/register", json=sample_registration_request.model_dump()
            )

            assert response.status_code == 500
            assert "Failed to register service" in response.json()["detail"]

    def test_register_service_invalid_data(self, client):
        """Test service registration with invalid data."""
        invalid_data = {
            "service": {
                "name": "",  # Invalid empty name
                "version": "1.0.0",
                "host": "localhost",
                "port": 8000,
                "health_check_url": "/health",
            }
        }

        response = client.post("/registry/register", json=invalid_data)
        assert response.status_code == 422  # Validation error

    def test_deregister_service_success(self, client):
        """Test successful service deregistration."""
        with patch(
            "packages.common.service_registry.api.get_service_registry"
        ) as mock_get_registry:
            mock_registry = AsyncMock()
            mock_registry.deregister_service.return_value = True
            mock_get_registry.return_value = mock_registry

            deregister_data = {
                "service_name": "test-service",
                "instance_id": "instance-123",
            }

            response = client.post("/registry/deregister", json=deregister_data)

            assert response.status_code == 200
            data = response.json()
            assert "deregistered successfully" in data["message"]

            mock_registry.deregister_service.assert_called_once_with(
                "test-service", "instance-123"
            )

    def test_deregister_service_not_found(self, client):
        """Test deregistering nonexistent service."""
        with patch(
            "packages.common.service_registry.api.get_service_registry"
        ) as mock_get_registry:
            mock_registry = AsyncMock()
            mock_registry.deregister_service.return_value = False
            mock_get_registry.return_value = mock_registry

            deregister_data = {"service_name": "nonexistent-service"}

            response = client.post("/registry/deregister", json=deregister_data)

            assert response.status_code == 404
            assert "not found" in response.json()["detail"]

    def test_deregister_service_failure(self, client):
        """Test service deregistration failure."""
        with patch(
            "packages.common.service_registry.api.get_service_registry"
        ) as mock_get_registry:
            mock_registry = AsyncMock()
            mock_registry.deregister_service.side_effect = Exception(
                "Deregistration failed"
            )
            mock_get_registry.return_value = mock_registry

            deregister_data = {"service_name": "test-service"}

            response = client.post("/registry/deregister", json=deregister_data)

            assert response.status_code == 500
            assert "Failed to deregister service" in response.json()["detail"]

    def test_discover_services_no_filters(self, client):
        """Test service discovery without filters."""
        sample_endpoint = ServiceEndpoint(
            service_name="test-service",
            instance_id="instance-123",
            url="http://localhost:8000",
            health_status=HealthStatus.HEALTHY,
        )

        with patch(
            "packages.common.service_registry.api.get_service_registry"
        ) as mock_get_registry:
            mock_registry = AsyncMock()
            mock_registry.discover_services.return_value = [sample_endpoint]
            mock_get_registry.return_value = mock_registry

            response = client.get("/registry/discover")

            assert response.status_code == 200
            data = response.json()
            assert len(data) == 1
            assert data[0]["service_name"] == "test-service"
            assert data[0]["instance_id"] == "instance-123"

    def test_discover_services_with_filters(self, client):
        """Test service discovery with filters."""
        with patch(
            "packages.common.service_registry.api.get_service_registry"
        ) as mock_get_registry:
            mock_registry = AsyncMock()
            mock_registry.discover_services.return_value = []
            mock_get_registry.return_value = mock_registry

            response = client.get(
                "/registry/discover",
                params={
                    "service_name": "test-service",
                    "health_status": "healthy",
                    "tags": "api,web",
                    "min_response_time": 10.0,
                    "max_response_time": 100.0,
                },
            )

            assert response.status_code == 200

            # Verify the filter criteria was built correctly
            mock_registry.discover_services.assert_called_once()
            call_args = mock_registry.discover_services.call_args[0][0]
            assert call_args.service_name == "test-service"
            assert call_args.health_status == HealthStatus.HEALTHY
            assert call_args.tags == ["api", "web"]
            assert call_args.min_response_time == 10.0
            assert call_args.max_response_time == 100.0

    def test_discover_services_failure(self, client):
        """Test service discovery failure."""
        with patch(
            "packages.common.service_registry.api.get_service_registry"
        ) as mock_get_registry:
            mock_registry = AsyncMock()
            mock_registry.discover_services.side_effect = Exception("Discovery failed")
            mock_get_registry.return_value = mock_registry

            response = client.get("/registry/discover")

            assert response.status_code == 500
            assert "Failed to discover services" in response.json()["detail"]

    def test_get_healthy_endpoint_success(self, client):
        """Test getting healthy endpoint successfully."""
        sample_endpoint = ServiceEndpoint(
            service_name="test-service",
            instance_id="instance-123",
            url="http://localhost:8000",
            health_status=HealthStatus.HEALTHY,
        )

        with patch(
            "packages.common.service_registry.api.get_service_registry"
        ) as mock_get_registry:
            mock_registry = AsyncMock()
            mock_registry.get_healthy_endpoint.return_value = sample_endpoint
            mock_get_registry.return_value = mock_registry

            response = client.get("/registry/services/test-service/healthy")

            assert response.status_code == 200
            data = response.json()
            assert data["service_name"] == "test-service"
            assert data["health_status"] == "healthy"

    def test_get_healthy_endpoint_none(self, client):
        """Test getting healthy endpoint when none available."""
        with patch(
            "packages.common.service_registry.api.get_service_registry"
        ) as mock_get_registry:
            mock_registry = AsyncMock()
            mock_registry.get_healthy_endpoint.return_value = None
            mock_get_registry.return_value = mock_registry

            response = client.get("/registry/services/test-service/healthy")

            assert response.status_code == 200
            assert response.json() is None

    def test_get_healthy_endpoint_failure(self, client):
        """Test getting healthy endpoint failure."""
        with patch(
            "packages.common.service_registry.api.get_service_registry"
        ) as mock_get_registry:
            mock_registry = AsyncMock()
            mock_registry.get_healthy_endpoint.side_effect = Exception(
                "Endpoint lookup failed"
            )
            mock_get_registry.return_value = mock_registry

            response = client.get("/registry/services/test-service/healthy")

            assert response.status_code == 500
            assert "Failed to get healthy endpoint" in response.json()["detail"]

    def test_get_service_instances(self, client):
        """Test getting service instances."""
        sample_endpoints = [
            ServiceEndpoint(
                service_name="test-service",
                instance_id="instance-1",
                url="http://localhost:8000",
                health_status=HealthStatus.HEALTHY,
            ),
            ServiceEndpoint(
                service_name="test-service",
                instance_id="instance-2",
                url="http://localhost:8001",
                health_status=HealthStatus.UNHEALTHY,
            ),
        ]

        with patch(
            "packages.common.service_registry.api.get_service_registry"
        ) as mock_get_registry:
            mock_registry = AsyncMock()
            mock_registry.get_service_instances.return_value = sample_endpoints
            mock_get_registry.return_value = mock_registry

            response = client.get("/registry/services/test-service/instances")

            assert response.status_code == 200
            data = response.json()
            assert len(data) == 2
            assert data[0]["instance_id"] == "instance-1"
            assert data[1]["instance_id"] == "instance-2"

    def test_get_service_instances_failure(self, client):
        """Test getting service instances failure."""
        with patch(
            "packages.common.service_registry.api.get_service_registry"
        ) as mock_get_registry:
            mock_registry = AsyncMock()
            mock_registry.get_service_instances.side_effect = Exception(
                "Instance lookup failed"
            )
            mock_get_registry.return_value = mock_registry

            response = client.get("/registry/services/test-service/instances")

            assert response.status_code == 500
            assert "Failed to get service instances" in response.json()["detail"]

    def test_get_system_health(self, client):
        """Test getting system health."""
        sample_health = SystemHealthStatus(
            status=HealthStatus.HEALTHY,
            services=[],
            total_services=2,
            healthy_services=2,
            unhealthy_services=0,
            unknown_services=0,
        )

        with patch(
            "packages.common.service_registry.api.get_service_registry"
        ) as mock_get_registry:
            mock_registry = AsyncMock()
            mock_registry.get_system_health.return_value = sample_health
            mock_get_registry.return_value = mock_registry

            response = client.get("/registry/health")

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"
            assert data["total_services"] == 2
            assert data["healthy_services"] == 2

    def test_get_system_health_failure(self, client):
        """Test getting system health failure."""
        with patch(
            "packages.common.service_registry.api.get_service_registry"
        ) as mock_get_registry:
            mock_registry = AsyncMock()
            mock_registry.get_system_health.side_effect = Exception(
                "Health check failed"
            )
            mock_get_registry.return_value = mock_registry

            response = client.get("/registry/health")

            assert response.status_code == 500
            assert "Failed to get system health" in response.json()["detail"]

    def test_get_all_services(self, client):
        """Test getting all services."""
        sample_services = {
            "service-1": [
                ServiceEndpoint(
                    service_name="service-1",
                    instance_id="instance-1",
                    url="http://localhost:8000",
                )
            ],
            "service-2": [
                ServiceEndpoint(
                    service_name="service-2",
                    instance_id="instance-2",
                    url="http://localhost:8001",
                )
            ],
        }

        with patch(
            "packages.common.service_registry.api.get_service_registry"
        ) as mock_get_registry:
            mock_registry = AsyncMock()
            mock_registry.get_all_services.return_value = sample_services
            mock_get_registry.return_value = mock_registry

            response = client.get("/registry/services")

            assert response.status_code == 200
            data = response.json()
            assert "service-1" in data
            assert "service-2" in data
            assert len(data["service-1"]) == 1
            assert len(data["service-2"]) == 1

    def test_get_all_services_failure(self, client):
        """Test getting all services failure."""
        with patch(
            "packages.common.service_registry.api.get_service_registry"
        ) as mock_get_registry:
            mock_registry = AsyncMock()
            mock_registry.get_all_services.side_effect = Exception(
                "Service lookup failed"
            )
            mock_get_registry.return_value = mock_registry

            response = client.get("/registry/services")

            assert response.status_code == 500
            assert "Failed to get all services" in response.json()["detail"]
