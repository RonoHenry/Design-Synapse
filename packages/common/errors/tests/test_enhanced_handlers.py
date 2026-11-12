"""Tests for enhanced error handlers."""

from unittest.mock import Mock, patch

import pytest
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from ..base import (APIError, CircuitBreakerError, RateLimitError,
                    ServiceUnavailableError, TimeoutError)
from ..handlers import (api_error_handler, create_error_context,
                        general_exception_handler, get_request_id,
                        get_service_name, sqlalchemy_error_handler,
                        validation_error_handler)
from ..responses import ErrorType


@pytest.fixture
def mock_request():
    """Mock FastAPI request."""
    request = Mock(spec=Request)
    request.method = "POST"
    request.url.path = "/api/test"
    request.client.host = "192.168.1.1"
    request.headers = {
        "User-Agent": "test-client/1.0",
        "X-Request-ID": "test-request-123",
    }
    return request


class TestErrorContext:
    """Test error context creation."""

    def test_create_error_context(self, mock_request):
        """Test error context creation with all fields."""
        exc = ValueError("Test error")

        with patch(
            "packages.common.errors.handlers.get_service_name",
            return_value="test-service",
        ):
            context = create_error_context(mock_request, exc)

        assert context["request_id"] == "test-request-123"
        assert context["service"] == "test-service"
        assert context["method"] == "POST"
        assert context["path"] == "/api/test"
        assert context["client_ip"] == "192.168.1.1"
        assert context["user_agent"] == "test-client/1.0"
        assert context["exception_type"] == "ValueError"
        assert "timestamp" in context

    def test_get_request_id_from_header(self, mock_request):
        """Test request ID extraction from header."""
        request_id = get_request_id(mock_request)
        assert request_id == "test-request-123"

    def test_get_request_id_generated(self):
        """Test request ID generation when not in header."""
        request = Mock(spec=Request)
        request.headers = {}

        request_id = get_request_id(request)
        assert len(request_id) == 36  # UUID length
        assert "-" in request_id

    @patch.dict("os.environ", {"SERVICE_NAME": "my-service"})
    def test_get_service_name_from_env(self):
        """Test service name from environment variable."""
        service_name = get_service_name()
        assert service_name == "my-service"

    @patch.dict("os.environ", {}, clear=True)
    def test_get_service_name_default(self):
        """Test default service name when env var not set."""
        service_name = get_service_name()
        assert service_name == "unknown-service"


class TestAPIErrorHandler:
    """Test API error handler."""

    @pytest.mark.asyncio
    async def test_api_error_handler_client_error(self, mock_request):
        """Test API error handler for client errors (4xx)."""
        exc = RateLimitError("Rate limit exceeded", retry_after=30)

        with patch("packages.common.errors.handlers.logger") as mock_logger:
            response = await api_error_handler(mock_request, exc)

        assert response.status_code == 429

        # Check response content
        content = response.body.decode()
        assert "Rate limit exceeded" in content
        assert "RATE_LIMIT_EXCEEDED" in content
        assert "retry_after" in content

        # Check headers
        assert response.headers.get("Retry-After") == "30"

        # Check logging level (should be WARNING for 4xx)
        mock_logger.log.assert_called_once()
        args = mock_logger.log.call_args
        assert args[0][0] == 30  # WARNING level

    @pytest.mark.asyncio
    async def test_api_error_handler_server_error(self, mock_request):
        """Test API error handler for server errors (5xx)."""
        exc = ServiceUnavailableError("test-service", "Service down", retry_after=60)

        with patch("packages.common.errors.handlers.logger") as mock_logger:
            response = await api_error_handler(mock_request, exc)

        assert response.status_code == 503

        # Check logging level (should be ERROR for 5xx)
        mock_logger.log.assert_called_once()
        args = mock_logger.log.call_args
        assert args[0][0] == 40  # ERROR level

    @pytest.mark.asyncio
    async def test_circuit_breaker_error_handling(self, mock_request):
        """Test circuit breaker error handling."""
        exc = CircuitBreakerError("user-service", retry_after=120)

        response = await api_error_handler(mock_request, exc)

        assert response.status_code == 503
        assert response.headers.get("Retry-After") == "120"

        content = response.body.decode()
        assert "CIRCUIT_BREAKER_OPEN" in content
        assert "user-service" in content

    @pytest.mark.asyncio
    async def test_timeout_error_handling(self, mock_request):
        """Test timeout error handling."""
        exc = TimeoutError("Request timeout", timeout_seconds=30.0)

        response = await api_error_handler(mock_request, exc)

        assert response.status_code == 408

        content = response.body.decode()
        assert "REQUEST_TIMEOUT" in content
        assert "timeout_seconds" in content


class TestValidationErrorHandler:
    """Test validation error handler."""

    @pytest.mark.asyncio
    async def test_validation_error_handler(self, mock_request):
        """Test validation error handler with detailed errors."""
        # Create mock validation error
        validation_errors = [
            {
                "loc": ("body", "email"),
                "msg": "field required",
                "type": "value_error.missing",
                "input": None,
            },
            {
                "loc": ("body", "age"),
                "msg": "ensure this value is greater than 0",
                "type": "value_error.number.not_gt",
                "input": -5,
            },
        ]

        exc = Mock(spec=RequestValidationError)
        exc.errors.return_value = validation_errors

        with patch("packages.common.errors.handlers.logger") as mock_logger:
            response = await validation_error_handler(mock_request, exc)

        assert response.status_code == 422

        # Check response content
        content = response.body.decode()
        assert "VALIDATION_ERROR" in content
        assert "body.email" in content
        assert "body.age" in content
        assert "field required" in content

        # Check logging
        mock_logger.warning.assert_called_once()


class TestSQLAlchemyErrorHandler:
    """Test SQLAlchemy error handler."""

    @pytest.mark.asyncio
    async def test_integrity_error_handler(self, mock_request):
        """Test integrity error handling."""
        exc = IntegrityError("statement", "params", "orig_error")

        with patch("packages.common.errors.handlers.logger") as mock_logger:
            response = await sqlalchemy_error_handler(mock_request, exc)

        assert response.status_code == 409

        content = response.body.decode()
        assert "CONFLICT" in content
        assert "integrity constraint violation" in content
        assert "constraint_type" in content

        # Check logging
        mock_logger.error.assert_called_once()

    @pytest.mark.asyncio
    async def test_general_sqlalchemy_error_handler(self, mock_request):
        """Test general SQLAlchemy error handling."""
        exc = SQLAlchemyError("Database connection failed")

        response = await sqlalchemy_error_handler(mock_request, exc)

        assert response.status_code == 500

        content = response.body.decode()
        assert "DATABASE_ERROR" in content
        assert "Database error occurred" in content


class TestGeneralExceptionHandler:
    """Test general exception handler."""

    @pytest.mark.asyncio
    async def test_general_exception_handler(self, mock_request):
        """Test general exception handler for unhandled exceptions."""
        exc = ValueError("Unexpected error")

        with patch("packages.common.errors.handlers.logger") as mock_logger:
            response = await general_exception_handler(mock_request, exc)

        assert response.status_code == 500

        content = response.body.decode()
        assert "INTERNAL_SERVER_ERROR" in content
        assert "unexpected error occurred" in content
        assert "ValueError" in content

        # Check logging with exc_info
        mock_logger.error.assert_called_once()
        call_args = mock_logger.error.call_args
        assert call_args[1]["exc_info"] is True


class TestErrorHandlerIntegration:
    """Test error handler integration with FastAPI."""

    def test_error_handlers_registration(self):
        """Test error handlers can be registered with FastAPI app."""
        from ..handlers import register_error_handlers

        app = FastAPI()
        register_error_handlers(app)

        # Check that handlers are registered
        assert len(app.exception_handlers) >= 4

    def test_end_to_end_error_handling(self):
        """Test end-to-end error handling in FastAPI app."""
        app = FastAPI()

        @app.get("/test-rate-limit")
        async def test_rate_limit():
            raise RateLimitError("Too many requests", retry_after=60)

        @app.get("/test-validation")
        async def test_validation():
            raise ValueError("Invalid input")

        from ..handlers import register_error_handlers

        register_error_handlers(app)

        client = TestClient(app)

        # Test rate limit error
        response = client.get("/test-rate-limit")
        assert response.status_code == 429
        assert response.headers.get("Retry-After") == "60"

        error_data = response.json()
        assert error_data["error_code"] == "RATE_LIMIT_EXCEEDED"
        assert "request_id" in error_data
        assert "timestamp" in error_data

        # Test general exception
        response = client.get("/test-validation")
        assert response.status_code == 500

        error_data = response.json()
        assert error_data["error_code"] == "INTERNAL_SERVER_ERROR"
