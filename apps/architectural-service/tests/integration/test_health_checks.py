"""Integration tests for health check endpoints."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
class TestHealthCheckEndpoints:
    """Test health check endpoints."""

    async def test_health_check_all_healthy(self, client: AsyncClient):
        """Test health check when all components are healthy."""
        # Mock all health check functions
        with patch("src.api.v1.routes.health.check_database_health") as mock_db:
            mock_db.return_value = {
                "status": "healthy",
                "message": "Database connection successful",
                "response_time_ms": 10.0,
            }

            with patch("src.api.v1.routes.health.check_redis_health") as mock_redis:
                mock_redis.return_value = {
                    "status": "healthy",
                    "message": "Redis connection successful",
                    "response_time_ms": 5.0,
                }

                with patch(
                    "src.api.v1.routes.health.check_external_service_health"
                ) as mock_external:
                    mock_external.return_value = {
                        "status": "healthy",
                        "message": "Service is available",
                        "response_time_ms": 50.0,
                    }

                    response = await client.get("/api/v1/health")

                    assert response.status_code == 200
                    data = response.json()

                    assert data["status"] == "healthy"
                    assert data["service"] == "Architectural Service"
                    assert "version" in data
                    assert "timestamp" in data
                    assert "components" in data
                    assert "summary" in data

                    # Check components
                    components = data["components"]
                    assert "database" in components
                    assert "redis" in components
                    assert "external_services" in components

                    # Check summary
                    summary = data["summary"]
                    assert summary["total_components"] == 6
                    assert summary["unhealthy_components"] == 0

    async def test_health_check_database_unhealthy(self, client: AsyncClient):
        """Test health check when database is unhealthy."""
        # Mock database health check to fail
        with patch("src.api.v1.routes.health.check_database_health") as mock_db:
            mock_db.return_value = {
                "status": "unhealthy",
                "message": "Database connection failed",
                "error": "Connection timeout",
            }

            # Mock external services as healthy
            with patch(
                "src.api.v1.routes.health.check_external_service_health"
            ) as mock_external:
                mock_external.return_value = {
                    "status": "healthy",
                    "message": "Service is available",
                    "response_time_ms": 50.0,
                }

                response = await client.get("/api/v1/health")

                assert response.status_code == 503
                data = response.json()

                assert data["status"] == "unhealthy"
                assert data["components"]["database"]["status"] == "unhealthy"
                assert "error" in data["components"]["database"]

                # Check summary shows unhealthy component
                summary = data["summary"]
                assert summary["unhealthy_components"] >= 1

    async def test_health_check_redis_unhealthy(self, client: AsyncClient):
        """Test health check when Redis is unhealthy."""
        # Mock Redis health check to fail
        with patch("src.api.v1.routes.health.check_redis_health") as mock_redis:
            mock_redis.return_value = {
                "status": "unhealthy",
                "message": "Redis connection failed",
                "error": "Connection refused",
            }

            # Mock external services as healthy
            with patch(
                "src.api.v1.routes.health.check_external_service_health"
            ) as mock_external:
                mock_external.return_value = {
                    "status": "healthy",
                    "message": "Service is available",
                    "response_time_ms": 50.0,
                }

                response = await client.get("/api/v1/health")

                assert response.status_code == 503
                data = response.json()

                assert data["status"] == "unhealthy"
                assert data["components"]["redis"]["status"] == "unhealthy"
                assert "error" in data["components"]["redis"]

    async def test_health_check_external_service_unhealthy(self, client: AsyncClient):
        """Test health check when external service is unhealthy."""

        async def mock_external_health(service_name, service_url, timeout=5):
            if "Design Service" in service_name:
                return {
                    "status": "unhealthy",
                    "message": f"{service_name} is unavailable",
                    "error": "Connection timeout",
                }
            return {
                "status": "healthy",
                "message": f"{service_name} is available",
                "response_time_ms": 50.0,
            }

        with patch(
            "src.api.v1.routes.health.check_external_service_health",
            side_effect=mock_external_health,
        ):
            response = await client.get("/api/v1/health")

            assert response.status_code == 503
            data = response.json()

            assert data["status"] == "unhealthy"
            external_services = data["components"]["external_services"]
            assert external_services["design_service"]["status"] == "unhealthy"

    async def test_liveness_check(self, client: AsyncClient):
        """Test liveness probe endpoint."""
        response = await client.get("/api/v1/health/live")

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "alive"
        assert data["service"] == "Architectural Service"
        assert "timestamp" in data

    async def test_readiness_check_ready(self, client: AsyncClient):
        """Test readiness probe when service is ready."""
        # Mock database and Redis as healthy
        with patch("src.api.v1.routes.health.check_database_health") as mock_db:
            mock_db.return_value = {
                "status": "healthy",
                "message": "Database connection successful",
                "response_time_ms": 10.0,
            }

            with patch("src.api.v1.routes.health.check_redis_health") as mock_redis:
                mock_redis.return_value = {
                    "status": "healthy",
                    "message": "Redis connection successful",
                    "response_time_ms": 5.0,
                }

                response = await client.get("/api/v1/health/ready")

                assert response.status_code == 200
                data = response.json()

                assert data["status"] == "ready"
                assert data["components"]["database"]["status"] == "healthy"
                assert data["components"]["redis"]["status"] == "healthy"

    async def test_readiness_check_not_ready(self, client: AsyncClient):
        """Test readiness probe when service is not ready."""
        # Mock database as unhealthy
        with patch("src.api.v1.routes.health.check_database_health") as mock_db:
            mock_db.return_value = {
                "status": "unhealthy",
                "message": "Database connection failed",
                "error": "Connection timeout",
            }

            with patch("src.api.v1.routes.health.check_redis_health") as mock_redis:
                mock_redis.return_value = {
                    "status": "healthy",
                    "message": "Redis connection successful",
                    "response_time_ms": 5.0,
                }

                response = await client.get("/api/v1/health/ready")

                assert response.status_code == 503
                data = response.json()

                assert data["status"] == "not_ready"
                assert data["components"]["database"]["status"] == "unhealthy"


@pytest.mark.asyncio
class TestMetricsEndpoints:
    """Test metrics collection endpoints."""

    async def test_get_metrics(self, client: AsyncClient):
        """Test metrics endpoint returns comprehensive metrics."""
        # Make some requests to generate metrics
        await client.get("/api/v1/health/live")
        await client.get("/api/v1/health/live")

        response = await client.get("/api/v1/metrics")

        assert response.status_code == 200
        data = response.json()

        assert data["service"] == "Architectural Service"
        assert "version" in data
        assert "timestamp" in data
        assert "metrics" in data

        metrics = data["metrics"]
        assert "uptime_seconds" in metrics
        assert "requests" in metrics
        assert "external_services" in metrics
        assert "cache" in metrics

        # Check request metrics structure
        request_metrics = metrics["requests"]
        assert "total" in request_metrics
        assert "by_endpoint" in request_metrics
        assert "error_count" in request_metrics
        assert "error_rate_percent" in request_metrics
        assert "latency_percentiles" in request_metrics

        # Check latency percentiles
        latency = request_metrics["latency_percentiles"]
        assert "p50" in latency
        assert "p95" in latency
        assert "p99" in latency

    async def test_get_endpoint_metrics(self, client: AsyncClient):
        """Test endpoint-specific metrics."""
        # Make some requests to the endpoint
        await client.get("/api/v1/health/live")
        await client.get("/api/v1/health/live")

        response = await client.get("/api/v1/metrics/endpoints/api/v1/health/live")

        assert response.status_code == 200
        data = response.json()

        assert "metrics" in data
        metrics = data["metrics"]

        assert "endpoint" in metrics
        assert metrics["endpoint"] == "/api/v1/health/live"
        assert "request_count" in metrics
        assert "error_count" in metrics
        assert "error_rate_percent" in metrics
        assert "latency_percentiles" in metrics

    async def test_get_service_metrics(self, client: AsyncClient):
        """Test external service-specific metrics."""
        response = await client.get("/api/v1/metrics/services/Design Service")

        assert response.status_code == 200
        data = response.json()

        assert "metrics" in data
        metrics = data["metrics"]

        assert "service_name" in metrics
        assert metrics["service_name"] == "Design Service"
        assert "call_count" in metrics
        assert "error_count" in metrics
        assert "error_rate_percent" in metrics
        assert "latency_percentiles" in metrics

    async def test_metrics_accumulation(self, client: AsyncClient):
        """Test that metrics accumulate over multiple requests."""
        # Get initial metrics
        response1 = await client.get("/api/v1/metrics")
        data1 = response1.json()
        initial_count = data1["metrics"]["requests"]["total"]

        # Make some requests
        await client.get("/api/v1/health/live")
        await client.get("/api/v1/health/live")
        await client.get("/api/v1/health/live")

        # Get updated metrics
        response2 = await client.get("/api/v1/metrics")
        data2 = response2.json()
        updated_count = data2["metrics"]["requests"]["total"]

        # Verify metrics increased (at least by 3 for the health checks)
        assert updated_count >= initial_count + 3


@pytest.mark.asyncio
class TestHealthCheckComponents:
    """Test individual health check component functions."""

    async def test_database_health_check_success(self):
        """Test database health check with successful connection."""
        from src.api.v1.routes.health import check_database_health

        # Mock the entire get_db function to return a working session
        with patch("src.api.v1.routes.health.get_db") as mock_get_db:
            # Create a mock session
            mock_session = AsyncMock()
            mock_result = MagicMock()
            mock_result.fetchone.return_value = (1,)
            mock_session.execute.return_value = mock_result
            mock_session.close = AsyncMock()

            async def mock_db_generator():
                yield mock_session

            mock_get_db.return_value = mock_db_generator()

            result = await check_database_health()

            assert result["status"] == "healthy"
            assert "response_time_ms" in result

    async def test_redis_health_check_failure(self):
        """Test Redis health check with connection failure."""
        from src.api.v1.routes.health import check_redis_health

        # Mock Redis client to fail
        with patch("src.api.v1.routes.health.get_redis_client") as mock_redis:
            mock_redis.side_effect = Exception("Connection refused")

            result = await check_redis_health()

            assert result["status"] == "unhealthy"
            assert "error" in result
            assert "Connection refused" in result["error"]

    async def test_external_service_health_check_timeout(self):
        """Test external service health check with timeout."""
        from src.api.v1.routes.health import check_external_service_health

        # Use a non-existent service URL
        result = await check_external_service_health(
            "Test Service", "http://localhost:99999", timeout=1
        )

        assert result["status"] == "unhealthy"
        assert "error" in result or "message" in result

    async def test_external_service_health_check_success(self):
        """Test external service health check with successful response."""
        from src.api.v1.routes.health import check_external_service_health

        # Mock httpx client
        with patch("httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"status": "healthy"}

            mock_client_instance = AsyncMock()
            mock_client_instance.__aenter__.return_value = mock_client_instance
            mock_client_instance.__aexit__.return_value = None
            mock_client_instance.get.return_value = mock_response
            mock_client.return_value = mock_client_instance

            result = await check_external_service_health(
                "Test Service", "http://test-service:8000"
            )

            assert result["status"] == "healthy"
            assert "response_time_ms" in result
