"""
Tests for health check aggregation functionality.
"""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest

from ..health import HealthAggregator, get_health_aggregator
from ..models import ServiceHealth, SystemHealthStatus

try:
    from packages.common.service_registry.models import (HealthCheck,
                                                         HealthStatus,
                                                         ServiceEndpoint)
except ImportError:
    # Fallback for when running tests
    from ....service_registry.models import (HealthCheck, HealthStatus,
                                             ServiceEndpoint)


class TestHealthAggregator:
    """Test health aggregation functionality."""

    @pytest.mark.asyncio
    async def test_check_service_health_success(self, health_aggregator):
        """Test successful service health check."""
        # Mock successful health check
        mock_health_result = MagicMock()
        mock_health_result.status = HealthStatus.HEALTHY
        mock_health_result.message = "Service is healthy"
        mock_health_result.checks = [{"database": "connected"}]

        health_aggregator.health_checker.check_endpoint_health.return_value = (
            mock_health_result
        )

        service_health = await health_aggregator.check_service_health(
            "test-service", "http://localhost:8000/health"
        )

        assert service_health.service_name == "test-service"
        assert service_health.status == HealthStatus.HEALTHY
        assert service_health.message == "Service is healthy"
        assert service_health.response_time_ms is not None
        assert service_health.response_time_ms >= 0

    @pytest.mark.asyncio
    async def test_check_service_health_failure(self, health_aggregator):
        """Test service health check failure."""
        # Mock health check exception
        health_aggregator.health_checker.check_endpoint_health.side_effect = Exception(
            "Connection failed"
        )

        service_health = await health_aggregator.check_service_health(
            "test-service", "http://localhost:8000/health"
        )

        assert service_health.service_name == "test-service"
        assert service_health.status == HealthStatus.UNHEALTHY
        assert "Health check failed" in service_health.message
        assert service_health.response_time_ms is None
        assert "error" in service_health.metadata

    @pytest.mark.asyncio
    async def test_check_all_services_health(self, health_aggregator):
        """Test checking health of multiple services."""
        services = [
            {"name": "service-1", "health_endpoint": "http://service1:8000/health"},
            {"name": "service-2", "health_endpoint": "http://service2:8000/health"},
            {"name": "service-3", "health_endpoint": "http://service3:8000/health"},
        ]

        # Mock health check results
        mock_results = [
            MagicMock(
                status=HealthStatus.HEALTHY, message="Healthy", response_time_ms=100.0
            ),
            MagicMock(
                status=HealthStatus.UNHEALTHY,
                message="Database down",
                response_time_ms=200.0,
            ),
            MagicMock(
                status=HealthStatus.HEALTHY, message="Healthy", response_time_ms=150.0
            ),
        ]

        health_aggregator.health_checker.check_endpoint_health.side_effect = (
            mock_results
        )

        system_health = await health_aggregator.check_all_services_health(services)

        assert isinstance(system_health, SystemHealthStatus)
        assert len(system_health.services) == 3
        assert system_health.healthy_count == 2
        assert system_health.unhealthy_count == 1
        assert system_health.unknown_count == 0
        # System should be unhealthy because one service is unhealthy
        assert system_health.overall_status == HealthStatus.UNHEALTHY

    @pytest.mark.asyncio
    async def test_check_all_services_with_exceptions(self, health_aggregator):
        """Test handling exceptions during health checks."""
        services = [
            {"name": "service-1", "health_endpoint": "http://service1:8000/health"},
            {"name": "service-2", "health_endpoint": "http://service2:8000/health"},
        ]

        # Mock one success and one exception
        health_aggregator.health_checker.check_endpoint_health.side_effect = [
            MagicMock(
                status=HealthStatus.HEALTHY, message="Healthy", response_time_ms=100.0
            ),
            Exception("Network error"),
        ]

        system_health = await health_aggregator.check_all_services_health(services)

        assert len(system_health.services) == 2
        assert system_health.healthy_count == 1
        assert system_health.unhealthy_count == 1

        # Check that exception was handled properly
        unhealthy_service = next(
            s for s in system_health.services if s.status == HealthStatus.UNHEALTHY
        )
        assert "Health check exception" in unhealthy_service.message
        assert "exception" in unhealthy_service.metadata

    def test_calculate_overall_status_all_healthy(self, health_aggregator):
        """Test overall status calculation when all services are healthy."""
        service_healths = [
            ServiceHealth("service-1", HealthStatus.HEALTHY, "OK", datetime.utcnow()),
            ServiceHealth("service-2", HealthStatus.HEALTHY, "OK", datetime.utcnow()),
            ServiceHealth("service-3", HealthStatus.HEALTHY, "OK", datetime.utcnow()),
        ]

        overall_status = health_aggregator._calculate_overall_status(service_healths)
        assert overall_status == HealthStatus.HEALTHY

    def test_calculate_overall_status_some_unhealthy(self, health_aggregator):
        """Test overall status calculation with some unhealthy services."""
        service_healths = [
            ServiceHealth("service-1", HealthStatus.HEALTHY, "OK", datetime.utcnow()),
            ServiceHealth(
                "service-2", HealthStatus.UNHEALTHY, "Error", datetime.utcnow()
            ),
            ServiceHealth("service-3", HealthStatus.HEALTHY, "OK", datetime.utcnow()),
        ]

        overall_status = health_aggregator._calculate_overall_status(service_healths)
        assert overall_status == HealthStatus.UNHEALTHY

    def test_calculate_overall_status_majority_unhealthy(self, health_aggregator):
        """Test overall status calculation when majority are unhealthy."""
        service_healths = [
            ServiceHealth(
                "service-1", HealthStatus.UNHEALTHY, "Error", datetime.utcnow()
            ),
            ServiceHealth(
                "service-2", HealthStatus.UNHEALTHY, "Error", datetime.utcnow()
            ),
            ServiceHealth("service-3", HealthStatus.HEALTHY, "OK", datetime.utcnow()),
        ]

        overall_status = health_aggregator._calculate_overall_status(service_healths)
        assert overall_status == HealthStatus.UNHEALTHY

    def test_calculate_overall_status_with_unknown(self, health_aggregator):
        """Test overall status calculation with unknown services."""
        service_healths = [
            ServiceHealth("service-1", HealthStatus.HEALTHY, "OK", datetime.utcnow()),
            ServiceHealth(
                "service-2", HealthStatus.UNKNOWN, "No response", datetime.utcnow()
            ),
            ServiceHealth("service-3", HealthStatus.HEALTHY, "OK", datetime.utcnow()),
        ]

        overall_status = health_aggregator._calculate_overall_status(service_healths)
        assert overall_status == HealthStatus.UNKNOWN

    def test_calculate_overall_status_empty(self, health_aggregator):
        """Test overall status calculation with no services."""
        overall_status = health_aggregator._calculate_overall_status([])
        assert overall_status == HealthStatus.UNKNOWN

    def test_get_current_health(self, health_aggregator):
        """Test getting current health status."""
        # Initially no health status
        assert health_aggregator.get_current_health() is None

        # Add a health status to history
        system_health = SystemHealthStatus(
            overall_status=HealthStatus.HEALTHY,
            services=[],
            timestamp=datetime.utcnow(),
        )
        health_aggregator._add_to_history(system_health)

        current_health = health_aggregator.get_current_health()
        assert current_health is not None
        assert current_health.overall_status == HealthStatus.HEALTHY

    def test_get_service_health(self, health_aggregator):
        """Test getting health for specific service."""
        service_health = ServiceHealth(
            service_name="test-service",
            status=HealthStatus.HEALTHY,
            message="OK",
            timestamp=datetime.utcnow(),
        )

        health_aggregator._service_health["test-service"] = service_health

        retrieved_health = health_aggregator.get_service_health("test-service")
        assert retrieved_health == service_health

        # Non-existent service should return None
        assert health_aggregator.get_service_health("non-existent") is None

    def test_get_health_history(self, health_aggregator):
        """Test getting health history."""
        now = datetime.utcnow()
        past = now - timedelta(hours=2)

        # Add health statuses at different times
        old_health = SystemHealthStatus(
            overall_status=HealthStatus.HEALTHY, services=[], timestamp=past
        )
        recent_health = SystemHealthStatus(
            overall_status=HealthStatus.UNHEALTHY, services=[], timestamp=now
        )

        health_aggregator._add_to_history(old_health)
        health_aggregator._add_to_history(recent_health)

        # Get history for last 1 hour (should only include recent)
        history = health_aggregator.get_health_history(hours=1)
        assert len(history) == 1
        assert history[0].overall_status == HealthStatus.UNHEALTHY

        # Get history for last 3 hours (should include both)
        history = health_aggregator.get_health_history(hours=3)
        assert len(history) == 2

    def test_get_unhealthy_services(self, health_aggregator):
        """Test getting list of unhealthy services."""
        # Add services with different health statuses
        health_aggregator._service_health["healthy-service"] = ServiceHealth(
            service_name="healthy-service",
            status=HealthStatus.HEALTHY,
            message="OK",
            timestamp=datetime.utcnow(),
        )
        health_aggregator._service_health["unhealthy-service"] = ServiceHealth(
            service_name="unhealthy-service",
            status=HealthStatus.UNHEALTHY,
            message="Error",
            timestamp=datetime.utcnow(),
        )
        health_aggregator._service_health["unknown-service"] = ServiceHealth(
            service_name="unknown-service",
            status=HealthStatus.UNKNOWN,
            message="No response",
            timestamp=datetime.utcnow(),
        )

        unhealthy_services = health_aggregator.get_unhealthy_services()
        assert len(unhealthy_services) == 1
        assert unhealthy_services[0].service_name == "unhealthy-service"

    def test_get_health_summary(self, health_aggregator):
        """Test getting health summary counts."""
        # Add services with different health statuses
        health_aggregator._service_health["healthy-1"] = ServiceHealth(
            service_name="healthy-1",
            status=HealthStatus.HEALTHY,
            message="OK",
            timestamp=datetime.utcnow(),
        )
        health_aggregator._service_health["healthy-2"] = ServiceHealth(
            service_name="healthy-2",
            status=HealthStatus.HEALTHY,
            message="OK",
            timestamp=datetime.utcnow(),
        )
        health_aggregator._service_health["unhealthy-1"] = ServiceHealth(
            service_name="unhealthy-1",
            status=HealthStatus.UNHEALTHY,
            message="Error",
            timestamp=datetime.utcnow(),
        )
        health_aggregator._service_health["unknown-1"] = ServiceHealth(
            service_name="unknown-1",
            status=HealthStatus.UNKNOWN,
            message="No response",
            timestamp=datetime.utcnow(),
        )

        summary = health_aggregator.get_health_summary()
        assert summary["healthy"] == 2
        assert summary["unhealthy"] == 1
        assert summary["unknown"] == 1

    def test_health_history_rotation(self, health_aggregator):
        """Test health history rotation."""
        # Set a small max for testing
        health_aggregator._max_history = 3

        # Add more health statuses than max
        for i in range(5):
            system_health = SystemHealthStatus(
                overall_status=HealthStatus.HEALTHY,
                services=[],
                timestamp=datetime.utcnow(),
            )
            health_aggregator._add_to_history(system_health)

        # Should only keep the last 3 health statuses
        assert len(health_aggregator._health_history) == 3

    @pytest.mark.asyncio
    async def test_create_basic_health_endpoint_response(self, health_aggregator):
        """Test creating basic health endpoint response."""
        services = [
            {"name": "service-1", "health_endpoint": "http://service1:8000/health"},
            {"name": "service-2", "health_endpoint": "http://service2:8000/health"},
        ]

        # Mock health check results
        mock_results = [
            MagicMock(
                status=HealthStatus.HEALTHY, message="Healthy", response_time_ms=100.0
            ),
            MagicMock(
                status=HealthStatus.UNHEALTHY,
                message="Database down",
                response_time_ms=200.0,
            ),
        ]

        health_aggregator.health_checker.check_endpoint_health.side_effect = (
            mock_results
        )

        response = await health_aggregator.create_basic_health_endpoint_response(
            services
        )

        assert "status" in response
        assert "timestamp" in response
        assert "services" in response
        assert "summary" in response

        assert len(response["services"]) == 2
        assert response["summary"]["total"] == 2
        assert response["summary"]["healthy"] == 1
        assert response["summary"]["unhealthy"] == 1
        assert response["summary"]["unknown"] == 0


class TestGlobalHealthAggregator:
    """Test global health aggregator instance."""

    def test_get_global_instance(self):
        """Test getting global health aggregator instance."""
        aggregator1 = get_health_aggregator()
        aggregator2 = get_health_aggregator()

        # Should return the same instance
        assert aggregator1 is aggregator2
        assert isinstance(aggregator1, HealthAggregator)
