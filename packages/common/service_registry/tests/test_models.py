"""Tests for Service Registry models."""

from datetime import datetime

import pytest
from pydantic import ValidationError

from ..models import (HealthCheck, HealthStatus, ServiceDiscoveryFilter,
                      ServiceEndpoint, ServiceInfo, ServiceRegistrationRequest,
                      SystemHealthStatus)


class TestHealthStatus:
    """Test HealthStatus enum."""

    def test_health_status_values(self):
        """Test that health status has correct values."""
        assert HealthStatus.HEALTHY == "healthy"
        assert HealthStatus.UNHEALTHY == "unhealthy"
        assert HealthStatus.UNKNOWN == "unknown"


class TestServiceInfo:
    """Test ServiceInfo model."""

    def test_service_info_creation(self):
        """Test creating a ServiceInfo instance."""
        service = ServiceInfo(
            name="test-service",
            version="1.0.0",
            host="localhost",
            port=8000,
            health_check_url="/health",
            metadata={"env": "test"},
            tags=["api", "web"],
        )

        assert service.name == "test-service"
        assert service.version == "1.0.0"
        assert service.host == "localhost"
        assert service.port == 8000
        assert service.health_check_url == "/health"
        assert service.metadata == {"env": "test"}
        assert service.tags == ["api", "web"]

    def test_service_info_defaults(self):
        """Test ServiceInfo with default values."""
        service = ServiceInfo(
            name="test-service",
            version="1.0.0",
            host="localhost",
            port=8000,
            health_check_url="/health",
        )

        assert service.metadata == {}
        assert service.tags == []

    def test_service_info_validation(self):
        """Test ServiceInfo validation."""
        with pytest.raises(ValidationError):
            ServiceInfo(
                name="",  # Empty name should fail
                version="1.0.0",
                host="localhost",
                port=-1,  # Invalid port should fail
                health_check_url="/health",
            )


class TestServiceEndpoint:
    """Test ServiceEndpoint model."""

    def test_service_endpoint_creation(self):
        """Test creating a ServiceEndpoint instance."""
        endpoint = ServiceEndpoint(
            service_name="test-service",
            instance_id="instance-1",
            url="http://localhost:8000",
            health_status=HealthStatus.HEALTHY,
            response_time_ms=50.0,
            metadata={"version": "1.0.0"},
            tags=["api"],
        )

        assert endpoint.service_name == "test-service"
        assert endpoint.instance_id == "instance-1"
        assert endpoint.url == "http://localhost:8000"
        assert endpoint.health_status == HealthStatus.HEALTHY
        assert endpoint.response_time_ms == 50.0
        assert endpoint.consecutive_failures == 0
        assert endpoint.metadata == {"version": "1.0.0"}
        assert endpoint.tags == ["api"]
        assert isinstance(endpoint.registered_at, datetime)

    def test_service_endpoint_defaults(self):
        """Test ServiceEndpoint with default values."""
        endpoint = ServiceEndpoint(
            service_name="test-service",
            instance_id="instance-1",
            url="http://localhost:8000",
        )

        assert endpoint.health_status == HealthStatus.UNKNOWN
        assert endpoint.last_health_check is None
        assert endpoint.response_time_ms is None
        assert endpoint.consecutive_failures == 0
        assert endpoint.metadata == {}
        assert endpoint.tags == []


class TestHealthCheck:
    """Test HealthCheck model."""

    def test_health_check_creation(self):
        """Test creating a HealthCheck instance."""
        check = HealthCheck(
            name="service_health",
            status=HealthStatus.HEALTHY,
            message="Service is running",
            response_time_ms=25.0,
        )

        assert check.name == "service_health"
        assert check.status == HealthStatus.HEALTHY
        assert check.message == "Service is running"
        assert check.response_time_ms == 25.0
        assert isinstance(check.timestamp, datetime)


class TestSystemHealthStatus:
    """Test SystemHealthStatus model."""

    def test_system_health_status_creation(self):
        """Test creating a SystemHealthStatus instance."""
        endpoints = [
            ServiceEndpoint(
                service_name="service-1",
                instance_id="instance-1",
                url="http://localhost:8000",
                health_status=HealthStatus.HEALTHY,
            ),
            ServiceEndpoint(
                service_name="service-2",
                instance_id="instance-2",
                url="http://localhost:8001",
                health_status=HealthStatus.UNHEALTHY,
            ),
        ]

        health_status = SystemHealthStatus(
            status=HealthStatus.UNKNOWN,
            services=endpoints,
            total_services=2,
            healthy_services=1,
            unhealthy_services=1,
            unknown_services=0,
        )

        assert health_status.status == HealthStatus.UNKNOWN
        assert len(health_status.services) == 2
        assert health_status.total_services == 2
        assert health_status.healthy_services == 1
        assert health_status.unhealthy_services == 1
        assert health_status.unknown_services == 0
        assert isinstance(health_status.timestamp, datetime)


class TestServiceRegistrationRequest:
    """Test ServiceRegistrationRequest model."""

    def test_registration_request_creation(self):
        """Test creating a ServiceRegistrationRequest instance."""
        service = ServiceInfo(
            name="test-service",
            version="1.0.0",
            host="localhost",
            port=8000,
            health_check_url="/health",
        )

        request = ServiceRegistrationRequest(
            service=service, health_check_interval=60, failure_threshold=5
        )

        assert request.service == service
        assert request.health_check_interval == 60
        assert request.failure_threshold == 5

    def test_registration_request_defaults(self):
        """Test ServiceRegistrationRequest with default values."""
        service = ServiceInfo(
            name="test-service",
            version="1.0.0",
            host="localhost",
            port=8000,
            health_check_url="/health",
        )

        request = ServiceRegistrationRequest(service=service)

        assert request.health_check_interval == 30
        assert request.failure_threshold == 3


class TestServiceDiscoveryFilter:
    """Test ServiceDiscoveryFilter model."""

    def test_discovery_filter_creation(self):
        """Test creating a ServiceDiscoveryFilter instance."""
        filter_criteria = ServiceDiscoveryFilter(
            service_name="test-service",
            tags=["api", "web"],
            health_status=HealthStatus.HEALTHY,
            min_response_time=10.0,
            max_response_time=100.0,
        )

        assert filter_criteria.service_name == "test-service"
        assert filter_criteria.tags == ["api", "web"]
        assert filter_criteria.health_status == HealthStatus.HEALTHY
        assert filter_criteria.min_response_time == 10.0
        assert filter_criteria.max_response_time == 100.0

    def test_discovery_filter_defaults(self):
        """Test ServiceDiscoveryFilter with default values."""
        filter_criteria = ServiceDiscoveryFilter()

        assert filter_criteria.service_name is None
        assert filter_criteria.tags == []
        assert filter_criteria.health_status is None
        assert filter_criteria.min_response_time is None
        assert filter_criteria.max_response_time is None
