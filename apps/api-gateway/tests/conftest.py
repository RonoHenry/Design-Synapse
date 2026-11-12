"""Test configuration and fixtures for API Gateway tests."""

import sys
from pathlib import Path
from unittest.mock import AsyncMock, Mock

import pytest

# Add src to Python path for imports
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))


@pytest.fixture
def mock_settings():
    """Mock settings for testing."""
    settings = Mock()
    settings.debug = True
    settings.host = "0.0.0.0"
    settings.port = 8000
    settings.allowed_origins = ["*"]
    settings.service_registry_url = "http://localhost:8001"
    settings.jwt_secret_key = "test-secret-key"
    settings.jwt_algorithm = "HS256"
    settings.jwt_expiration_hours = 24
    settings.rate_limit_requests = 100
    settings.rate_limit_window = 60
    settings.circuit_breaker_failure_threshold = 5
    settings.circuit_breaker_recovery_timeout = 60
    settings.redis_url = "redis://localhost:6379"
    settings.enable_metrics = True
    settings.enable_tracing = True
    return settings


@pytest.fixture
def mock_http_client():
    """Mock HTTP client for testing."""
    client = AsyncMock()
    client.request = AsyncMock()
    client.aclose = AsyncMock()
    return client


@pytest.fixture
def mock_fastapi_request():
    """Mock FastAPI request for testing."""
    request = Mock()
    request.method = "GET"
    request.url.path = "/api/v1/test"
    request.url.query = ""
    request.url.scheme = "http"
    request.headers = {"authorization": "Bearer test-token"}
    request.client.host = "192.168.1.1"
    request.body = AsyncMock(return_value=b"")
    request.state = Mock()
    request.state.request_id = "test-request-id"
    return request


@pytest.fixture(autouse=True)
def reset_global_state():
    """Reset global state before each test."""
    # Reset any global variables that might affect tests
    import src.api.v1.routes.gateway as gateway_module

    gateway_module._request_router = None

    import src.services.service_registry as registry_module

    registry_module._service_registry = None

    yield

    # Cleanup after test
    gateway_module._request_router = None
    registry_module._service_registry = None
