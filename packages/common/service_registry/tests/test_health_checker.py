"""Tests for HealthChecker."""

import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
import pytest_asyncio

from ..health_checker import HealthChecker
from ..models import HealthCheck, HealthStatus, ServiceEndpoint


@pytest_asyncio.fixture
async def health_checker():
    """Create a HealthChecker instance for testing."""
    checker = HealthChecker(check_interval=1, timeout=1.0, failure_threshold=2)
    async with checker:
        yield checker


@pytest.fixture
def sample_endpoint():
    """Create a sample service endpoint."""
    return ServiceEndpoint(
        service_name="test-service",
        instance_id="instance-1",
        url="http://localhost:8000",
    )


class TestHealthChecker:
    """Test HealthChecker functionality."""

    @pytest.mark.asyncio
    async def test_health_checker_initialization(self):
        """Test HealthChecker initialization."""
        checker = HealthChecker(
            check_interval=30, timeout=10.0, failure_threshold=3, recovery_threshold=2
        )

        assert checker.check_interval == 30
        assert checker.timeout == 10.0
        assert checker.failure_threshold == 3
        assert checker.recovery_threshold == 2
        assert not checker._running

    @pytest.mark.asyncio
    async def test_add_endpoint(self, health_checker, sample_endpoint):
        """Test adding an endpoint for monitoring."""
        await health_checker.add_endpoint(sample_endpoint)

        endpoint_id = f"{sample_endpoint.service_name}:{sample_endpoint.instance_id}"
        assert endpoint_id in health_checker._endpoints
        assert endpoint_id in health_checker._endpoint_configs

        config = health_checker._endpoint_configs[endpoint_id]
        assert config["check_interval"] == health_checker.check_interval
        assert config["failure_threshold"] == health_checker.failure_threshold

    @pytest.mark.asyncio
    async def test_add_endpoint_with_custom_config(
        self, health_checker, sample_endpoint
    ):
        """Test adding an endpoint with custom configuration."""
        await health_checker.add_endpoint(
            sample_endpoint, check_interval=60, failure_threshold=5
        )

        endpoint_id = f"{sample_endpoint.service_name}:{sample_endpoint.instance_id}"
        config = health_checker._endpoint_configs[endpoint_id]
        assert config["check_interval"] == 60
        assert config["failure_threshold"] == 5

    @pytest.mark.asyncio
    async def test_remove_endpoint(self, health_checker, sample_endpoint):
        """Test removing an endpoint from monitoring."""
        await health_checker.add_endpoint(sample_endpoint)

        endpoint_id = f"{sample_endpoint.service_name}:{sample_endpoint.instance_id}"
        assert endpoint_id in health_checker._endpoints

        await health_checker.remove_endpoint(
            sample_endpoint.service_name, sample_endpoint.instance_id
        )

        assert endpoint_id not in health_checker._endpoints
        assert endpoint_id not in health_checker._endpoint_configs

    @pytest.mark.asyncio
    async def test_check_endpoint_health_success(self, health_checker, sample_endpoint):
        """Test successful health check."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "healthy", "message": "All good"}

        with patch.object(
            health_checker._http_client, "get", return_value=mock_response
        ) as mock_get:
            health_check = await health_checker.check_endpoint_health(sample_endpoint)

            assert health_check.status == HealthStatus.HEALTHY
            assert health_check.name == "test-service_health"
            assert "All good" in health_check.message
            assert health_check.response_time_ms is not None
            assert health_check.response_time_ms > 0

            mock_get.assert_called_once_with("http://localhost:8000/health")

    @pytest.mark.asyncio
    async def test_check_endpoint_health_failure(self, health_checker, sample_endpoint):
        """Test failed health check."""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"

        with patch.object(
            health_checker._http_client, "get", return_value=mock_response
        ):
            health_check = await health_checker.check_endpoint_health(sample_endpoint)

            assert health_check.status == HealthStatus.UNHEALTHY
            assert health_check.name == "test-service_health"
            assert "HTTP 500" in health_check.message
            assert health_check.response_time_ms is not None

    @pytest.mark.asyncio
    async def test_check_endpoint_health_timeout(self, health_checker, sample_endpoint):
        """Test health check timeout."""
        with patch.object(
            health_checker._http_client, "get", side_effect=asyncio.TimeoutError()
        ):
            health_check = await health_checker.check_endpoint_health(sample_endpoint)

            assert health_check.status == HealthStatus.UNHEALTHY
            assert health_check.name == "test-service_health"
            assert "timeout" in health_check.message.lower()
            assert health_check.response_time_ms is None

    @pytest.mark.asyncio
    async def test_check_endpoint_health_exception(
        self, health_checker, sample_endpoint
    ):
        """Test health check with connection exception."""
        with patch.object(
            health_checker._http_client,
            "get",
            side_effect=httpx.ConnectError("Connection failed"),
        ):
            health_check = await health_checker.check_endpoint_health(sample_endpoint)

            assert health_check.status == HealthStatus.UNHEALTHY
            assert health_check.name == "test-service_health"
            assert "failed" in health_check.message.lower()
            assert health_check.response_time_ms is None

    @pytest.mark.asyncio
    async def test_get_aggregated_health_empty(self, health_checker):
        """Test getting aggregated health with no endpoints."""
        health_checks = await health_checker.get_aggregated_health()
        assert health_checks == []

    @pytest.mark.asyncio
    async def test_get_aggregated_health_with_endpoints(
        self, health_checker, sample_endpoint
    ):
        """Test getting aggregated health with endpoints."""
        await health_checker.add_endpoint(sample_endpoint)

        # Simulate a health check
        sample_endpoint.health_status = HealthStatus.HEALTHY
        sample_endpoint.last_health_check = datetime.utcnow()
        sample_endpoint.response_time_ms = 50.0

        health_checks = await health_checker.get_aggregated_health()

        assert len(health_checks) == 1
        assert health_checks[0].name == "test-service_health"
        assert health_checks[0].status == HealthStatus.HEALTHY
        assert health_checks[0].response_time_ms == 50.0

    @pytest.mark.asyncio
    async def test_health_callback(self, health_checker, sample_endpoint):
        """Test health status change callbacks."""
        callback_calls = []

        def test_callback(endpoint, health_check):
            callback_calls.append((endpoint, health_check))

        health_checker.add_health_callback(test_callback)
        await health_checker.add_endpoint(sample_endpoint)

        # Simulate health check that changes status
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "healthy"}

        with patch.object(
            health_checker._http_client, "get", return_value=mock_response
        ):
            await health_checker._check_and_update_endpoint(
                f"{sample_endpoint.service_name}:{sample_endpoint.instance_id}",
                sample_endpoint,
                health_checker._endpoint_configs[
                    f"{sample_endpoint.service_name}:{sample_endpoint.instance_id}"
                ],
            )

        # Callback should be called when status changes from UNKNOWN to HEALTHY
        assert len(callback_calls) == 1
        assert callback_calls[0][0] == sample_endpoint
        assert callback_calls[0][1].status == HealthStatus.HEALTHY

    @pytest.mark.asyncio
    async def test_remove_health_callback(self, health_checker):
        """Test removing health callbacks."""

        def test_callback(endpoint, health_check):
            pass

        health_checker.add_health_callback(test_callback)
        assert test_callback in health_checker._callbacks

        health_checker.remove_health_callback(test_callback)
        assert test_callback not in health_checker._callbacks

    @pytest.mark.asyncio
    async def test_consecutive_failures_tracking(self, health_checker, sample_endpoint):
        """Test tracking of consecutive failures."""
        await health_checker.add_endpoint(sample_endpoint)

        endpoint_id = f"{sample_endpoint.service_name}:{sample_endpoint.instance_id}"
        config = health_checker._endpoint_configs[endpoint_id]

        # Simulate multiple failed health checks
        with patch.object(
            health_checker._http_client,
            "get",
            side_effect=httpx.ConnectError("Connection failed"),
        ):
            # First failure
            await health_checker._check_and_update_endpoint(
                endpoint_id, sample_endpoint, config
            )
            assert sample_endpoint.consecutive_failures == 1
            assert (
                sample_endpoint.health_status == HealthStatus.UNKNOWN
            )  # Not enough failures yet

            # Second failure (reaches threshold)
            await health_checker._check_and_update_endpoint(
                endpoint_id, sample_endpoint, config
            )
            assert sample_endpoint.consecutive_failures == 2
            assert sample_endpoint.health_status == HealthStatus.UNHEALTHY

    @pytest.mark.asyncio
    async def test_recovery_after_failures(self, health_checker, sample_endpoint):
        """Test service recovery after failures."""
        await health_checker.add_endpoint(sample_endpoint)

        endpoint_id = f"{sample_endpoint.service_name}:{sample_endpoint.instance_id}"
        config = health_checker._endpoint_configs[endpoint_id]

        # Mark as unhealthy first
        sample_endpoint.health_status = HealthStatus.UNHEALTHY
        sample_endpoint.consecutive_failures = 3

        # Simulate successful health check
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "healthy"}

        with patch.object(
            health_checker._http_client, "get", return_value=mock_response
        ):
            # First success
            await health_checker._check_and_update_endpoint(
                endpoint_id, sample_endpoint, config
            )
            assert sample_endpoint.consecutive_failures == 0
            assert config["consecutive_successes"] == 1
            assert (
                sample_endpoint.health_status == HealthStatus.UNHEALTHY
            )  # Not enough successes yet

            # Second success (reaches recovery threshold)
            await health_checker._check_and_update_endpoint(
                endpoint_id, sample_endpoint, config
            )
            assert config["consecutive_successes"] == 2
            assert sample_endpoint.health_status == HealthStatus.HEALTHY

    @pytest.mark.asyncio
    async def test_start_stop_health_checker(self):
        """Test starting and stopping the health checker."""
        checker = HealthChecker(check_interval=0.1)  # Very short interval for testing

        async with checker:
            assert not checker._running

            await checker.start()
            assert checker._running
            assert checker._check_task is not None

            await checker.stop()
            assert not checker._running
