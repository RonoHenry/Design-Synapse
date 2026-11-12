"""Unit tests for request router."""

from datetime import datetime
from unittest.mock import AsyncMock, Mock, patch

import httpx
import pytest
from src.core.exceptions import ServiceUnavailableError
from src.models.service import HealthStatus, ServiceEndpoint, ServiceRoute
from src.services.request_router import RequestRouter, RoundRobinLoadBalancer
from src.services.service_registry import ServiceRegistry


class TestRequestRouter:
    """Test cases for RequestRouter."""

    @pytest.fixture
    def mock_service_registry(self):
        """Create a mock service registry."""
        registry = AsyncMock(spec=ServiceRegistry)
        return registry

    @pytest.fixture
    def request_router(self, mock_service_registry):
        """Create a RequestRouter instance."""
        return RequestRouter(mock_service_registry)

    @pytest.fixture
    def sample_routes(self):
        """Sample route configurations."""
        return [
            ServiceRoute(
                path_pattern=r"^/api/v1/users(/.*)?$",
                service_name="user-service",
                strip_prefix=False,
                timeout_seconds=30,
                retry_attempts=3,
            ),
            ServiceRoute(
                path_pattern=r"^/api/v1/projects(/.*)?$",
                service_name="project-service",
                strip_prefix=False,
                timeout_seconds=30,
                retry_attempts=3,
            ),
        ]

    @pytest.fixture
    def sample_endpoints(self):
        """Sample service endpoints."""
        return [
            ServiceEndpoint(
                service_name="user-service",
                url="http://user-service:8001",
                health_status=HealthStatus.HEALTHY,
                last_health_check=datetime.utcnow(),
                response_time_ms=50.0,
            ),
            ServiceEndpoint(
                service_name="project-service",
                url="http://project-service:8002",
                health_status=HealthStatus.HEALTHY,
                last_health_check=datetime.utcnow(),
                response_time_ms=75.0,
            ),
        ]

    def test_find_matching_route_success(self, request_router, sample_routes):
        """Test successful route matching."""
        request_router._route_patterns = sample_routes

        # Test exact match
        route = request_router._find_matching_route("/api/v1/users")
        assert route is not None
        assert route.service_name == "user-service"

        # Test with subpath
        route = request_router._find_matching_route("/api/v1/users/123")
        assert route is not None
        assert route.service_name == "user-service"

        # Test projects route
        route = request_router._find_matching_route("/api/v1/projects/456/comments")
        assert route is not None
        assert route.service_name == "project-service"

    def test_find_matching_route_no_match(self, request_router, sample_routes):
        """Test route matching when no route matches."""
        request_router._route_patterns = sample_routes

        # Test non-matching path
        route = request_router._find_matching_route("/api/v1/unknown")
        assert route is None

        # Test different API version
        route = request_router._find_matching_route("/api/v2/users")
        assert route is None

    def test_add_route(self, request_router):
        """Test adding a new route."""
        new_route = ServiceRoute(
            path_pattern=r"^/api/v1/designs(/.*)?$",
            service_name="design-service",
            strip_prefix=False,
            timeout_seconds=60,
            retry_attempts=2,
        )

        initial_count = len(request_router._route_patterns)
        request_router.add_route(new_route)

        assert len(request_router._route_patterns) == initial_count + 1
        assert new_route in request_router._route_patterns

    def test_remove_route(self, request_router, sample_routes):
        """Test removing a route."""
        request_router._route_patterns = sample_routes.copy()

        initial_count = len(request_router._route_patterns)
        request_router.remove_route(r"^/api/v1/users(/.*)?$")

        assert len(request_router._route_patterns) == initial_count - 1

        # Verify the route was actually removed
        route = request_router._find_matching_route("/api/v1/users")
        assert route is None

    def test_get_routes(self, request_router, sample_routes):
        """Test getting all routes."""
        request_router._route_patterns = sample_routes

        routes = request_router.get_routes()
        assert len(routes) == len(sample_routes)
        assert routes == sample_routes

        # Verify it returns a copy (not the original list)
        routes.append(
            ServiceRoute(
                path_pattern="test",
                service_name="test-service",
                strip_prefix=False,
                timeout_seconds=30,
                retry_attempts=3,
            )
        )
        assert len(request_router._route_patterns) == len(sample_routes)

    @pytest.mark.asyncio
    async def test_route_request_success(
        self, request_router, mock_service_registry, sample_routes, sample_endpoints
    ):
        """Test successful request routing."""
        # Setup
        request_router._route_patterns = sample_routes
        request_router._load_balancer = AsyncMock()
        request_router._load_balancer.get_endpoint.return_value = sample_endpoints[0]

        # Mock HTTP client and response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b'{"result": "success"}'
        mock_response.headers = {"content-type": "application/json"}

        request_router._http_client = AsyncMock()
        request_router._make_request_with_retry = AsyncMock(return_value=mock_response)

        # Mock FastAPI request
        mock_request = Mock()
        mock_request.url.path = "/api/v1/users/123"
        mock_request.url.query = "limit=10"
        mock_request.url.scheme = "http"
        mock_request.method = "GET"
        mock_request.headers = {"authorization": "Bearer token123"}
        mock_request.client.host = "192.168.1.1"
        mock_request.body = AsyncMock(return_value=b"")

        # Execute
        response = await request_router.route_request(mock_request)

        # Verify
        assert response.status_code == 200
        assert response.body == b'{"result": "success"}'
        request_router._load_balancer.get_endpoint.assert_called_once_with(
            mock_service_registry, "user-service"
        )

    @pytest.mark.asyncio
    async def test_route_request_no_matching_route(self, request_router, sample_routes):
        """Test routing when no route matches."""
        request_router._route_patterns = sample_routes

        mock_request = Mock()
        mock_request.url.path = "/api/v1/unknown"

        with pytest.raises(ServiceUnavailableError) as exc_info:
            await request_router.route_request(mock_request)

        assert (
            exc_info.value.details["reason"]
            == "No route found for path: /api/v1/unknown"
        )

    @pytest.mark.asyncio
    async def test_route_request_service_unavailable(
        self, request_router, mock_service_registry, sample_routes
    ):
        """Test routing when service is unavailable."""
        request_router._route_patterns = sample_routes
        request_router._load_balancer = AsyncMock()
        request_router._load_balancer.get_endpoint.side_effect = (
            ServiceUnavailableError("user-service", {"reason": "No healthy endpoints"})
        )

        mock_request = Mock()
        mock_request.url.path = "/api/v1/users/123"

        with pytest.raises(ServiceUnavailableError):
            await request_router.route_request(mock_request)

    @pytest.mark.asyncio
    async def test_make_request_with_retry_success(self, request_router):
        """Test successful request without retry."""
        mock_response = Mock()
        mock_response.status_code = 200

        request_router._http_client = AsyncMock()
        request_router._http_client.request.return_value = mock_response

        response = await request_router._make_request_with_retry(
            method="GET",
            url="http://test.com/api",
            headers={},
            content=None,
            timeout=30,
            max_retries=3,
        )

        assert response == mock_response
        request_router._http_client.request.assert_called_once()

    @pytest.mark.asyncio
    async def test_make_request_with_retry_server_error_retry(self, request_router):
        """Test retry on server error."""
        mock_response_fail = Mock()
        mock_response_fail.status_code = 503

        mock_response_success = Mock()
        mock_response_success.status_code = 200

        request_router._http_client = AsyncMock()
        request_router._http_client.request.side_effect = [
            mock_response_fail,
            mock_response_success,
        ]

        response = await request_router._make_request_with_retry(
            method="GET",
            url="http://test.com/api",
            headers={},
            content=None,
            timeout=30,
            max_retries=3,
        )

        assert response == mock_response_success
        assert request_router._http_client.request.call_count == 2

    @pytest.mark.asyncio
    async def test_make_request_with_retry_timeout_exception(self, request_router):
        """Test retry on timeout exception."""
        request_router._http_client = AsyncMock()
        request_router._http_client.request.side_effect = [
            httpx.TimeoutException("Timeout"),
            httpx.TimeoutException("Timeout"),
            Mock(status_code=200),
        ]

        response = await request_router._make_request_with_retry(
            method="GET",
            url="http://test.com/api",
            headers={},
            content=None,
            timeout=30,
            max_retries=3,
        )

        assert response.status_code == 200
        assert request_router._http_client.request.call_count == 3

    @pytest.mark.asyncio
    async def test_make_request_with_retry_max_retries_exceeded(self, request_router):
        """Test when max retries are exceeded."""
        request_router._http_client = AsyncMock()
        request_router._http_client.request.side_effect = httpx.TimeoutException(
            "Timeout"
        )

        with pytest.raises(httpx.TimeoutException):
            await request_router._make_request_with_retry(
                method="GET",
                url="http://test.com/api",
                headers={},
                content=None,
                timeout=30,
                max_retries=2,
            )

        assert (
            request_router._http_client.request.call_count == 3
        )  # Initial + 2 retries


class TestRoundRobinLoadBalancer:
    """Test cases for RoundRobinLoadBalancer."""

    @pytest.fixture
    def load_balancer(self):
        """Create a RoundRobinLoadBalancer instance."""
        return RoundRobinLoadBalancer()

    @pytest.fixture
    def mock_service_registry(self):
        """Create a mock service registry."""
        return AsyncMock(spec=ServiceRegistry)

    @pytest.fixture
    def healthy_endpoints(self):
        """Create sample healthy endpoints."""
        return [
            ServiceEndpoint(
                service_name="test-service",
                url="http://test-service-1:8001",
                health_status=HealthStatus.HEALTHY,
                last_health_check=datetime.utcnow(),
                response_time_ms=50.0,
            ),
            ServiceEndpoint(
                service_name="test-service",
                url="http://test-service-2:8001",
                health_status=HealthStatus.HEALTHY,
                last_health_check=datetime.utcnow(),
                response_time_ms=75.0,
            ),
            ServiceEndpoint(
                service_name="test-service",
                url="http://test-service-3:8001",
                health_status=HealthStatus.HEALTHY,
                last_health_check=datetime.utcnow(),
                response_time_ms=60.0,
            ),
        ]

    @pytest.mark.asyncio
    async def test_get_endpoint_round_robin(
        self, load_balancer, mock_service_registry, healthy_endpoints
    ):
        """Test round-robin endpoint selection."""
        mock_service_registry.discover_services.return_value = healthy_endpoints

        # Test multiple selections to verify round-robin behavior
        selected_endpoints = []
        for _ in range(6):  # Two full rounds
            endpoint = await load_balancer.get_endpoint(
                mock_service_registry, "test-service"
            )
            selected_endpoints.append(endpoint.url)

        # Verify round-robin pattern
        expected_pattern = [
            "http://test-service-1:8001",
            "http://test-service-2:8001",
            "http://test-service-3:8001",
            "http://test-service-1:8001",
            "http://test-service-2:8001",
            "http://test-service-3:8001",
        ]
        assert selected_endpoints == expected_pattern

    @pytest.mark.asyncio
    async def test_get_endpoint_no_registered_endpoints(
        self, load_balancer, mock_service_registry
    ):
        """Test when no endpoints are registered."""
        mock_service_registry.discover_services.return_value = []

        with pytest.raises(ServiceUnavailableError) as exc_info:
            await load_balancer.get_endpoint(mock_service_registry, "test-service")

        assert exc_info.value.details["reason"] == "No registered endpoints"

    @pytest.mark.asyncio
    async def test_get_endpoint_no_healthy_endpoints(
        self, load_balancer, mock_service_registry
    ):
        """Test when no healthy endpoints are available."""
        unhealthy_endpoints = [
            ServiceEndpoint(
                service_name="test-service",
                url="http://test-service-1:8001",
                health_status=HealthStatus.UNHEALTHY,
                last_health_check=datetime.utcnow(),
                response_time_ms=None,
            )
        ]
        mock_service_registry.discover_services.return_value = unhealthy_endpoints

        with pytest.raises(ServiceUnavailableError) as exc_info:
            await load_balancer.get_endpoint(mock_service_registry, "test-service")

        assert exc_info.value.details["reason"] == "No healthy endpoints available"

    @pytest.mark.asyncio
    async def test_get_endpoint_fallback_to_unknown(
        self, load_balancer, mock_service_registry
    ):
        """Test fallback to unknown status endpoints when no healthy ones exist."""
        mixed_endpoints = [
            ServiceEndpoint(
                service_name="test-service",
                url="http://test-service-1:8001",
                health_status=HealthStatus.UNHEALTHY,
                last_health_check=datetime.utcnow(),
                response_time_ms=None,
            ),
            ServiceEndpoint(
                service_name="test-service",
                url="http://test-service-2:8001",
                health_status=HealthStatus.UNKNOWN,
                last_health_check=None,
                response_time_ms=None,
            ),
        ]
        mock_service_registry.discover_services.return_value = mixed_endpoints

        endpoint = await load_balancer.get_endpoint(
            mock_service_registry, "test-service"
        )

        assert endpoint.url == "http://test-service-2:8001"
        assert endpoint.health_status == HealthStatus.UNKNOWN

    @pytest.mark.asyncio
    async def test_get_endpoint_multiple_services_independent_counters(
        self, load_balancer, mock_service_registry
    ):
        """Test that different services have independent round-robin counters."""
        service1_endpoints = [
            ServiceEndpoint(
                service_name="service1",
                url="http://service1-1:8001",
                health_status=HealthStatus.HEALTHY,
                last_health_check=datetime.utcnow(),
                response_time_ms=50.0,
            ),
            ServiceEndpoint(
                service_name="service1",
                url="http://service1-2:8001",
                health_status=HealthStatus.HEALTHY,
                last_health_check=datetime.utcnow(),
                response_time_ms=60.0,
            ),
        ]

        service2_endpoints = [
            ServiceEndpoint(
                service_name="service2",
                url="http://service2-1:8002",
                health_status=HealthStatus.HEALTHY,
                last_health_check=datetime.utcnow(),
                response_time_ms=70.0,
            ),
            ServiceEndpoint(
                service_name="service2",
                url="http://service2-2:8002",
                health_status=HealthStatus.HEALTHY,
                last_health_check=datetime.utcnow(),
                response_time_ms=80.0,
            ),
        ]

        def mock_discover_services(service_name):
            if service_name == "service1":
                return service1_endpoints
            elif service_name == "service2":
                return service2_endpoints
            return []

        mock_service_registry.discover_services.side_effect = mock_discover_services

        # Test interleaved requests to both services
        endpoint1_1 = await load_balancer.get_endpoint(
            mock_service_registry, "service1"
        )
        endpoint2_1 = await load_balancer.get_endpoint(
            mock_service_registry, "service2"
        )
        endpoint1_2 = await load_balancer.get_endpoint(
            mock_service_registry, "service1"
        )
        endpoint2_2 = await load_balancer.get_endpoint(
            mock_service_registry, "service2"
        )

        # Verify independent round-robin for each service
        assert endpoint1_1.url == "http://service1-1:8001"
        assert endpoint1_2.url == "http://service1-2:8001"
        assert endpoint2_1.url == "http://service2-1:8002"
        assert endpoint2_2.url == "http://service2-2:8002"
