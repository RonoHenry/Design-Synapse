"""Tests for ServiceRegistry."""

import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio

from ..models import (HealthStatus, ServiceDiscoveryFilter, ServiceEndpoint,
                      ServiceInfo, ServiceRegistrationRequest)
from ..registry import ServiceRegistry


@pytest_asyncio.fixture
async def service_registry():
    """Create a ServiceRegistry instance for testing."""
    registry = ServiceRegistry(
        default_health_check_interval=1, cleanup_interval=1, stale_service_timeout=2
    )
    async with registry:
        yield registry


@pytest.fixture
def sample_service_info():
    """Create a sample ServiceInfo."""
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
    """Create a sample ServiceRegistrationRequest."""
    return ServiceRegistrationRequest(
        service=sample_service_info, health_check_interval=30, failure_threshold=3
    )


class TestServiceRegistry:
    """Test ServiceRegistry functionality."""

    @pytest.mark.asyncio
    async def test_registry_initialization(self):
        """Test ServiceRegistry initialization."""
        registry = ServiceRegistry(
            default_health_check_interval=60,
            default_failure_threshold=5,
            cleanup_interval=300,
            stale_service_timeout=600,
        )

        assert registry.default_health_check_interval == 60
        assert registry.default_failure_threshold == 5
        assert registry.cleanup_interval == 300
        assert registry.stale_service_timeout == 600
        assert not registry._running

    @pytest.mark.asyncio
    async def test_start_stop_registry(self):
        """Test starting and stopping the registry."""
        registry = ServiceRegistry()

        assert not registry._running

        await registry.start()
        assert registry._running
        assert registry._health_checker is not None
        assert registry._cleanup_task is not None

        await registry.stop()
        assert not registry._running

    @pytest.mark.asyncio
    async def test_register_service(
        self, service_registry, sample_registration_request
    ):
        """Test service registration."""
        instance_id = await service_registry.register_service(
            sample_registration_request
        )

        assert instance_id is not None
        assert len(instance_id) > 0

        # Check that service is stored
        assert "test-service" in service_registry._services
        assert instance_id in service_registry._services["test-service"]

        endpoint = service_registry._services["test-service"][instance_id]
        assert endpoint.service_name == "test-service"
        assert endpoint.instance_id == instance_id
        assert endpoint.url == "http://localhost:8000"
        assert endpoint.health_status == HealthStatus.UNKNOWN
        assert endpoint.metadata == {"env": "test"}
        assert endpoint.tags == ["api", "web"]

        # Check configuration is stored
        assert instance_id in service_registry._service_configs
        config = service_registry._service_configs[instance_id]
        assert config["health_check_interval"] == 30
        assert config["failure_threshold"] == 3

    @pytest.mark.asyncio
    async def test_register_multiple_instances(
        self, service_registry, sample_service_info
    ):
        """Test registering multiple instances of the same service."""
        # Register first instance
        request1 = ServiceRegistrationRequest(service=sample_service_info)
        instance_id1 = await service_registry.register_service(request1)

        # Register second instance with different port
        service_info2 = ServiceInfo(
            name="test-service",
            version="1.0.0",
            host="localhost",
            port=8001,
            health_check_url="/health",
        )
        request2 = ServiceRegistrationRequest(service=service_info2)
        instance_id2 = await service_registry.register_service(request2)

        assert instance_id1 != instance_id2
        assert len(service_registry._services["test-service"]) == 2
        assert instance_id1 in service_registry._services["test-service"]
        assert instance_id2 in service_registry._services["test-service"]

    @pytest.mark.asyncio
    async def test_deregister_service_by_instance(
        self, service_registry, sample_registration_request
    ):
        """Test deregistering a specific service instance."""
        instance_id = await service_registry.register_service(
            sample_registration_request
        )

        # Verify service is registered
        assert "test-service" in service_registry._services
        assert instance_id in service_registry._services["test-service"]

        # Deregister specific instance
        success = await service_registry.deregister_service("test-service", instance_id)
        assert success

        # Verify service is removed
        assert "test-service" not in service_registry._services
        assert instance_id not in service_registry._service_configs

    @pytest.mark.asyncio
    async def test_deregister_all_service_instances(
        self, service_registry, sample_service_info
    ):
        """Test deregistering all instances of a service."""
        # Register multiple instances
        request1 = ServiceRegistrationRequest(service=sample_service_info)
        instance_id1 = await service_registry.register_service(request1)

        service_info2 = ServiceInfo(
            name="test-service",
            version="1.0.0",
            host="localhost",
            port=8001,
            health_check_url="/health",
        )
        request2 = ServiceRegistrationRequest(service=service_info2)
        instance_id2 = await service_registry.register_service(request2)

        # Verify both instances are registered
        assert len(service_registry._services["test-service"]) == 2

        # Deregister all instances
        success = await service_registry.deregister_service("test-service")
        assert success

        # Verify all instances are removed
        assert "test-service" not in service_registry._services
        assert instance_id1 not in service_registry._service_configs
        assert instance_id2 not in service_registry._service_configs

    @pytest.mark.asyncio
    async def test_deregister_nonexistent_service(self, service_registry):
        """Test deregistering a service that doesn't exist."""
        success = await service_registry.deregister_service("nonexistent-service")
        assert not success

    @pytest.mark.asyncio
    async def test_discover_services_no_filter(
        self, service_registry, sample_registration_request
    ):
        """Test discovering services without filters."""
        instance_id = await service_registry.register_service(
            sample_registration_request
        )

        endpoints = await service_registry.discover_services()

        assert len(endpoints) == 1
        assert endpoints[0].service_name == "test-service"
        assert endpoints[0].instance_id == instance_id

    @pytest.mark.asyncio
    async def test_discover_services_with_name_filter(
        self, service_registry, sample_service_info
    ):
        """Test discovering services with name filter."""
        # Register two different services
        request1 = ServiceRegistrationRequest(service=sample_service_info)
        await service_registry.register_service(request1)

        service_info2 = ServiceInfo(
            name="other-service",
            version="1.0.0",
            host="localhost",
            port=8001,
            health_check_url="/health",
        )
        request2 = ServiceRegistrationRequest(service=service_info2)
        await service_registry.register_service(request2)

        # Filter by service name
        filter_criteria = ServiceDiscoveryFilter(service_name="test-service")
        endpoints = await service_registry.discover_services(filter_criteria)

        assert len(endpoints) == 1
        assert endpoints[0].service_name == "test-service"

    @pytest.mark.asyncio
    async def test_discover_services_with_health_filter(
        self, service_registry, sample_registration_request
    ):
        """Test discovering services with health status filter."""
        instance_id = await service_registry.register_service(
            sample_registration_request
        )

        # Manually set health status
        endpoint = service_registry._services["test-service"][instance_id]
        endpoint.health_status = HealthStatus.HEALTHY

        # Filter by health status
        filter_criteria = ServiceDiscoveryFilter(health_status=HealthStatus.HEALTHY)
        endpoints = await service_registry.discover_services(filter_criteria)

        assert len(endpoints) == 1
        assert endpoints[0].health_status == HealthStatus.HEALTHY

        # Filter by different health status
        filter_criteria = ServiceDiscoveryFilter(health_status=HealthStatus.UNHEALTHY)
        endpoints = await service_registry.discover_services(filter_criteria)

        assert len(endpoints) == 0

    @pytest.mark.asyncio
    async def test_discover_services_with_tags_filter(
        self, service_registry, sample_registration_request
    ):
        """Test discovering services with tags filter."""
        instance_id = await service_registry.register_service(
            sample_registration_request
        )

        # Filter by tags (all must match)
        filter_criteria = ServiceDiscoveryFilter(tags=["api"])
        endpoints = await service_registry.discover_services(filter_criteria)

        assert len(endpoints) == 1
        assert "api" in endpoints[0].tags

        # Filter by tags that don't match
        filter_criteria = ServiceDiscoveryFilter(tags=["database"])
        endpoints = await service_registry.discover_services(filter_criteria)

        assert len(endpoints) == 0

    @pytest.mark.asyncio
    async def test_discover_services_with_response_time_filter(
        self, service_registry, sample_registration_request
    ):
        """Test discovering services with response time filter."""
        instance_id = await service_registry.register_service(
            sample_registration_request
        )

        # Set response time
        endpoint = service_registry._services["test-service"][instance_id]
        endpoint.response_time_ms = 50.0

        # Filter by response time range
        filter_criteria = ServiceDiscoveryFilter(
            min_response_time=10.0, max_response_time=100.0
        )
        endpoints = await service_registry.discover_services(filter_criteria)

        assert len(endpoints) == 1
        assert endpoints[0].response_time_ms == 50.0

        # Filter by response time range that excludes the service
        filter_criteria = ServiceDiscoveryFilter(
            min_response_time=100.0, max_response_time=200.0
        )
        endpoints = await service_registry.discover_services(filter_criteria)

        assert len(endpoints) == 0

    @pytest.mark.asyncio
    async def test_get_healthy_endpoint(self, service_registry, sample_service_info):
        """Test getting a healthy endpoint."""
        # Register service
        request = ServiceRegistrationRequest(service=sample_service_info)
        instance_id = await service_registry.register_service(request)

        # Initially no healthy endpoint (status is UNKNOWN)
        endpoint = await service_registry.get_healthy_endpoint("test-service")
        assert endpoint is not None  # Should return UNKNOWN status endpoint
        assert endpoint.health_status == HealthStatus.UNKNOWN

        # Mark as healthy
        service_registry._services["test-service"][
            instance_id
        ].health_status = HealthStatus.HEALTHY

        endpoint = await service_registry.get_healthy_endpoint("test-service")
        assert endpoint is not None
        assert endpoint.health_status == HealthStatus.HEALTHY
        assert endpoint.service_name == "test-service"

    @pytest.mark.asyncio
    async def test_get_healthy_endpoint_nonexistent_service(self, service_registry):
        """Test getting healthy endpoint for nonexistent service."""
        endpoint = await service_registry.get_healthy_endpoint("nonexistent-service")
        assert endpoint is None

    @pytest.mark.asyncio
    async def test_get_healthy_endpoint_no_healthy_services(
        self, service_registry, sample_registration_request
    ):
        """Test getting healthy endpoint when all services are unhealthy."""
        instance_id = await service_registry.register_service(
            sample_registration_request
        )

        # Mark as unhealthy
        service_registry._services["test-service"][
            instance_id
        ].health_status = HealthStatus.UNHEALTHY

        endpoint = await service_registry.get_healthy_endpoint("test-service")
        assert endpoint is None

    @pytest.mark.asyncio
    async def test_get_system_health_empty(self, service_registry):
        """Test getting system health with no services."""
        health_status = await service_registry.get_system_health()

        assert health_status.status == HealthStatus.UNKNOWN
        assert len(health_status.services) == 0
        assert health_status.total_services == 0
        assert health_status.healthy_services == 0
        assert health_status.unhealthy_services == 0
        assert health_status.unknown_services == 0

    @pytest.mark.asyncio
    async def test_get_system_health_mixed_status(
        self, service_registry, sample_service_info
    ):
        """Test getting system health with mixed service statuses."""
        # Register multiple services with different statuses
        request1 = ServiceRegistrationRequest(service=sample_service_info)
        instance_id1 = await service_registry.register_service(request1)

        service_info2 = ServiceInfo(
            name="service-2",
            version="1.0.0",
            host="localhost",
            port=8001,
            health_check_url="/health",
        )
        request2 = ServiceRegistrationRequest(service=service_info2)
        instance_id2 = await service_registry.register_service(request2)

        # Set different health statuses
        service_registry._services["test-service"][
            instance_id1
        ].health_status = HealthStatus.HEALTHY
        service_registry._services["service-2"][
            instance_id2
        ].health_status = HealthStatus.UNHEALTHY

        health_status = await service_registry.get_system_health()

        assert health_status.status == HealthStatus.UNKNOWN  # Mixed status
        assert len(health_status.services) == 2
        assert health_status.total_services == 2
        assert health_status.healthy_services == 1
        assert health_status.unhealthy_services == 1
        assert health_status.unknown_services == 0

    @pytest.mark.asyncio
    async def test_get_service_instances(self, service_registry, sample_service_info):
        """Test getting all instances of a specific service."""
        # Register multiple instances
        request1 = ServiceRegistrationRequest(service=sample_service_info)
        instance_id1 = await service_registry.register_service(request1)

        service_info2 = ServiceInfo(
            name="test-service",
            version="1.0.0",
            host="localhost",
            port=8001,
            health_check_url="/health",
        )
        request2 = ServiceRegistrationRequest(service=service_info2)
        instance_id2 = await service_registry.register_service(request2)

        instances = await service_registry.get_service_instances("test-service")

        assert len(instances) == 2
        instance_ids = [inst.instance_id for inst in instances]
        assert instance_id1 in instance_ids
        assert instance_id2 in instance_ids

    @pytest.mark.asyncio
    async def test_get_service_instances_nonexistent(self, service_registry):
        """Test getting instances of nonexistent service."""
        instances = await service_registry.get_service_instances("nonexistent-service")
        assert instances == []

    @pytest.mark.asyncio
    async def test_get_all_services(self, service_registry, sample_service_info):
        """Test getting all registered services."""
        # Register services
        request1 = ServiceRegistrationRequest(service=sample_service_info)
        await service_registry.register_service(request1)

        service_info2 = ServiceInfo(
            name="service-2",
            version="1.0.0",
            host="localhost",
            port=8001,
            health_check_url="/health",
        )
        request2 = ServiceRegistrationRequest(service=service_info2)
        await service_registry.register_service(request2)

        all_services = await service_registry.get_all_services()

        assert len(all_services) == 2
        assert "test-service" in all_services
        assert "service-2" in all_services
        assert len(all_services["test-service"]) == 1
        assert len(all_services["service-2"]) == 1

    @pytest.mark.asyncio
    async def test_cleanup_stale_services(
        self, service_registry, sample_registration_request
    ):
        """Test cleanup of stale services."""
        instance_id = await service_registry.register_service(
            sample_registration_request
        )

        # Mark service as unhealthy and old
        endpoint = service_registry._services["test-service"][instance_id]
        endpoint.health_status = HealthStatus.UNHEALTHY
        endpoint.last_health_check = datetime.utcnow() - timedelta(
            seconds=10
        )  # Old timestamp

        # Trigger cleanup
        await service_registry._cleanup_stale_services()

        # Service should be removed
        assert "test-service" not in service_registry._services
        assert instance_id not in service_registry._service_configs

    @pytest.mark.asyncio
    async def test_cleanup_does_not_remove_healthy_services(
        self, service_registry, sample_registration_request
    ):
        """Test that cleanup doesn't remove healthy services."""
        instance_id = await service_registry.register_service(
            sample_registration_request
        )

        # Mark service as healthy
        endpoint = service_registry._services["test-service"][instance_id]
        endpoint.health_status = HealthStatus.HEALTHY
        endpoint.last_health_check = datetime.utcnow() - timedelta(seconds=10)

        # Trigger cleanup
        await service_registry._cleanup_stale_services()

        # Service should not be removed
        assert "test-service" in service_registry._services
        assert instance_id in service_registry._service_configs

    @pytest.mark.asyncio
    async def test_concurrent_operations(self, service_registry, sample_service_info):
        """Test concurrent service operations."""
        # Create multiple registration tasks
        tasks = []
        for i in range(10):
            service_info = ServiceInfo(
                name=f"service-{i}",
                version="1.0.0",
                host="localhost",
                port=8000 + i,
                health_check_url="/health",
            )
            request = ServiceRegistrationRequest(service=service_info)
            task = asyncio.create_task(service_registry.register_service(request))
            tasks.append(task)

        # Wait for all registrations to complete
        instance_ids = await asyncio.gather(*tasks)

        # Verify all services are registered
        assert len(instance_ids) == 10
        assert len(service_registry._services) == 10

        # Test concurrent discovery
        discovery_tasks = []
        for i in range(5):
            task = asyncio.create_task(service_registry.discover_services())
            discovery_tasks.append(task)

        results = await asyncio.gather(*discovery_tasks)

        # All discovery calls should return the same results
        for result in results:
            assert len(result) == 10
