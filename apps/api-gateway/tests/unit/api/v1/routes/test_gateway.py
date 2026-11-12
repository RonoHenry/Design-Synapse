"""Unit tests for gateway routes."""

from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi import FastAPI, Response
from fastapi.testclient import TestClient
from src.api.v1.routes.gateway import get_request_router, router
from src.core.exceptions import GatewayError, ServiceUnavailableError
from src.models.service import ServiceRoute
from src.services.request_router import RequestRouter


class TestGatewayRoutes:
    """Test cases for gateway routes."""

    @pytest.fixture
    def app(self):
        """Create a test FastAPI app."""
        app = FastAPI()
        app.include_router(router)
        return app

    @pytest.fixture
    def client(self, app):
        """Create a test client."""
        return TestClient(app)

    @pytest.fixture
    def mock_request_router(self):
        """Create a mock request router."""
        return AsyncMock(spec=RequestRouter)

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

    def test_get_routes_success(self, app, mock_request_router, sample_routes):
        """Test successful retrieval of routes."""
        mock_request_router.get_routes.return_value = sample_routes

        # Override the dependency
        app.dependency_overrides[get_request_router] = lambda: mock_request_router

        with TestClient(app) as client:
            response = client.get("/routes")

        assert response.status_code == 200
        data = response.json()

        assert "routes" in data
        assert "total_routes" in data
        assert data["total_routes"] == 2
        assert len(data["routes"]) == 2

        # Verify route structure
        route = data["routes"][0]
        assert "path_pattern" in route
        assert "service_name" in route
        assert "strip_prefix" in route
        assert "timeout_seconds" in route
        assert "retry_attempts" in route

    def test_get_routes_empty(self, app, mock_request_router):
        """Test retrieval of routes when no routes exist."""
        mock_request_router.get_routes.return_value = []

        # Override the dependency
        app.dependency_overrides[get_request_router] = lambda: mock_request_router

        with TestClient(app) as client:
            response = client.get("/routes")

        assert response.status_code == 200
        data = response.json()

        assert data["total_routes"] == 0
        assert len(data["routes"]) == 0

    def test_add_route_success(self, app, mock_request_router):
        """Test successful addition of a new route."""
        route_data = {
            "path_pattern": r"^/api/v1/designs(/.*)?$",
            "service_name": "design-service",
            "strip_prefix": False,
            "timeout_seconds": 60,
            "retry_attempts": 2,
        }

        # Override the dependency
        app.dependency_overrides[get_request_router] = lambda: mock_request_router

        with TestClient(app) as client:
            response = client.post("/routes", json=route_data)

        assert response.status_code == 200
        data = response.json()

        assert "message" in data
        assert "route" in data
        assert data["message"] == "Route added successfully"
        assert data["route"]["service_name"] == "design-service"

        # Verify the router's add_route method was called
        mock_request_router.add_route.assert_called_once()

    def test_add_route_invalid_data(self, app, mock_request_router):
        """Test adding a route with invalid data."""
        # Use truly invalid data that will cause Pydantic validation to fail
        invalid_route_data = {
            "path_pattern": 123,  # Invalid type - should be string
            "service_name": None,  # Invalid type - should be string
        }

        # Override the dependency
        app.dependency_overrides[get_request_router] = lambda: mock_request_router

        with TestClient(app) as client:
            response = client.post("/routes", json=invalid_route_data)

        assert response.status_code == 400  # Route handler validation error
        data = response.json()
        assert "Invalid route configuration" in data["detail"]

    def test_remove_route_success(self, app, mock_request_router):
        """Test successful removal of a route."""
        path_pattern = r"^/api/v1/users(/.*)?$"
        encoded_pattern = path_pattern.replace("/", "%2F").replace("?", "%3F")

        # Override the dependency
        app.dependency_overrides[get_request_router] = lambda: mock_request_router

        with TestClient(app) as client:
            response = client.delete(f"/routes/{encoded_pattern}")

        assert response.status_code == 200
        data = response.json()

        assert "message" in data
        assert "path_pattern" in data
        assert data["message"] == "Route removed successfully"
        assert data["path_pattern"] == path_pattern

        # Verify the router's remove_route method was called
        mock_request_router.remove_route.assert_called_once_with(path_pattern)

    @pytest.mark.asyncio
    async def test_route_request_success(self, mock_request_router):
        """Test successful request routing."""
        # Mock successful response
        mock_response = Response(
            content=b'{"result": "success"}',
            status_code=200,
            headers={"content-type": "application/json"},
        )
        mock_request_router.route_request.return_value = mock_response

        # Mock FastAPI request
        mock_request = Mock()
        mock_request.method = "GET"
        mock_request.url.path = "/api/v1/users/123"
        mock_request.state = Mock()
        mock_request.state.request_id = "test-request-id"

        # Import and test the route function directly
        from src.api.v1.routes.gateway import route_request

        with patch(
            "src.api.v1.routes.gateway.get_request_router",
            return_value=mock_request_router,
        ):
            response = await route_request(
                mock_request, "users/123", mock_request_router
            )

        assert response.status_code == 200
        assert response.body == b'{"result": "success"}'
        mock_request_router.route_request.assert_called_once_with(mock_request)

    @pytest.mark.asyncio
    async def test_route_request_service_unavailable(self, mock_request_router):
        """Test request routing when service is unavailable."""
        # Mock service unavailable error
        mock_request_router.route_request.side_effect = ServiceUnavailableError(
            "user-service", {"reason": "No healthy endpoints"}
        )

        # Mock FastAPI request
        mock_request = Mock()
        mock_request.method = "GET"
        mock_request.url.path = "/api/v1/users/123"
        mock_request.state = Mock()
        mock_request.state.request_id = "test-request-id"

        # Import and test the route function directly
        from src.api.v1.routes.gateway import route_request

        with patch(
            "src.api.v1.routes.gateway.get_request_router",
            return_value=mock_request_router,
        ):
            with pytest.raises(ServiceUnavailableError):
                await route_request(mock_request, "users/123", mock_request_router)

    @pytest.mark.asyncio
    async def test_route_request_unexpected_error(self, mock_request_router):
        """Test request routing with unexpected error."""
        # Mock unexpected error
        mock_request_router.route_request.side_effect = Exception("Unexpected error")

        # Mock FastAPI request
        mock_request = Mock()
        mock_request.method = "GET"
        mock_request.url.path = "/api/v1/users/123"
        mock_request.state = Mock()
        mock_request.state.request_id = "test-request-id"

        # Import and test the route function directly
        from fastapi import HTTPException
        from src.api.v1.routes.gateway import route_request

        with patch(
            "src.api.v1.routes.gateway.get_request_router",
            return_value=mock_request_router,
        ):
            with pytest.raises(HTTPException) as exc_info:
                await route_request(mock_request, "users/123", mock_request_router)

            assert exc_info.value.status_code == 500
            assert "Internal server error" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_route_request_adds_request_id(self, mock_request_router):
        """Test that route_request adds request_id when not present."""
        # Mock successful response
        mock_response = Response(content=b'{"result": "success"}', status_code=200)
        mock_request_router.route_request.return_value = mock_response

        # Mock FastAPI request without request_id
        mock_request = Mock()
        mock_request.method = "GET"
        mock_request.url.path = "/api/v1/users/123"
        mock_request.state = Mock(spec=[])  # Empty state without request_id

        # Import and test the route function directly
        from src.api.v1.routes.gateway import route_request

        with patch(
            "src.api.v1.routes.gateway.get_request_router",
            return_value=mock_request_router,
        ):
            with patch(
                "uuid.uuid4", return_value=Mock(__str__=lambda x: "generated-uuid")
            ):
                response = await route_request(
                    mock_request, "users/123", mock_request_router
                )

        # Verify request_id was added
        assert hasattr(mock_request.state, "request_id")
        assert mock_request.state.request_id == "generated-uuid"
        assert response.status_code == 200


class TestRequestRouterDependency:
    """Test cases for request router dependency injection."""

    @pytest.mark.asyncio
    async def test_get_request_router_singleton(self):
        """Test that get_request_router returns a singleton instance."""
        # Reset global state
        import src.api.v1.routes.gateway as gateway_module
        from src.api.v1.routes.gateway import get_request_router

        gateway_module._request_router = None

        mock_service_registry = AsyncMock()

        # First call should create new instance
        router1 = await get_request_router(mock_service_registry)

        # Verify instance was created
        assert router1 is not None
        assert gateway_module._request_router is not None

        # Second call should return same instance
        router2 = await get_request_router(mock_service_registry)

        # Verify same instance is returned
        assert router1 is router2
