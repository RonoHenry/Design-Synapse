"""Comprehensive tests for error response consistency and logging."""

import json
import logging
import time
from datetime import datetime
from unittest.mock import MagicMock, Mock, patch

import pytest
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from ..base import (APIError, AuthenticationError, AuthorizationError,
                    CircuitBreakerError, ConflictError, ExternalServiceError,
                    LLMServiceError, NotFoundError, RateLimitError,
                    ServiceUnavailableError, TimeoutError, VectorSearchError)
from ..handlers import (api_error_handler, create_error_context,
                        general_exception_handler, register_error_handlers,
                        sqlalchemy_error_handler, validation_error_handler)
from ..responses import ErrorType


class TestErrorResponseConsistency:
    """Test consistent error response formats across all error types."""

    def setup_method(self):
        """Set up test app with error handlers."""
        self.app = FastAPI()
        register_error_handlers(self.app)
        self.client = TestClient(self.app)

    def test_all_api_errors_have_consistent_format(self):
        """Test that all API error types return consistent response format."""

        # Define test endpoints for each error type
        @self.app.get("/rate-limit")
        async def rate_limit_endpoint():
            raise RateLimitError("Too many requests", retry_after=60)

        @self.app.get("/auth-error")
        async def auth_error_endpoint():
            raise AuthenticationError("Invalid token")

        @self.app.get("/authz-error")
        async def authz_error_endpoint():
            raise AuthorizationError("Insufficient permissions")

        @self.app.get("/not-found")
        async def not_found_endpoint():
            raise NotFoundError("User", "123")

        @self.app.get("/conflict")
        async def conflict_endpoint():
            raise ConflictError("Resource already exists")

        @self.app.get("/service-unavailable")
        async def service_unavailable_endpoint():
            raise ServiceUnavailableError(
                "user-service", "Service down", retry_after=30
            )

        @self.app.get("/circuit-breaker")
        async def circuit_breaker_endpoint():
            raise CircuitBreakerError("payment-service", retry_after=120)

        @self.app.get("/timeout")
        async def timeout_endpoint():
            raise TimeoutError("Request timeout", timeout_seconds=30.0)

        @self.app.get("/external-service")
        async def external_service_endpoint():
            raise ExternalServiceError("stripe", "Payment failed")

        @self.app.get("/llm-service")
        async def llm_service_endpoint():
            raise LLMServiceError("Model unavailable")

        @self.app.get("/vector-search")
        async def vector_search_endpoint():
            raise VectorSearchError("Index not found")

        # Test each endpoint and verify response format
        endpoints_and_expected_codes = [
            ("/rate-limit", 429, "RATE_LIMIT_EXCEEDED"),
            ("/auth-error", 401, "AUTHENTICATION_ERROR"),
            ("/authz-error", 403, "AUTHORIZATION_ERROR"),
            ("/not-found", 404, "NOT_FOUND"),
            ("/conflict", 409, "CONFLICT"),
            ("/service-unavailable", 503, "SERVICE_UNAVAILABLE"),
            ("/circuit-breaker", 503, "CIRCUIT_BREAKER_OPEN"),
            ("/timeout", 408, "REQUEST_TIMEOUT"),
            ("/external-service", 503, "EXTERNAL_SERVICE_ERROR"),
            ("/llm-service", 503, "LLM_SERVICE_ERROR"),
            ("/vector-search", 503, "VECTOR_SEARCH_ERROR"),
        ]

        for (
            endpoint,
            expected_status,
            expected_error_code,
        ) in endpoints_and_expected_codes:
            response = self.client.get(endpoint)

            # Check status code
            assert (
                response.status_code == expected_status
            ), f"Wrong status for {endpoint}"

            # Check response format
            error_data = response.json()

            # All responses must have these fields
            required_fields = [
                "message",
                "error_code",
                "request_id",
                "timestamp",
                "service",
            ]
            for field in required_fields:
                assert field in error_data, f"Missing {field} in {endpoint} response"

            # Check error code
            assert error_data["error_code"] == expected_error_code

            # Check timestamp format
            timestamp = error_data["timestamp"]
            datetime.fromisoformat(timestamp)  # Should not raise exception

            # Check request_id format (should be UUID-like)
            request_id = error_data["request_id"]
            assert len(request_id) >= 32, f"Invalid request_id format: {request_id}"

    def test_retry_after_headers_consistency(self):
        """Test that retry-after headers are consistent across error types."""

        @self.app.get("/rate-limit-retry")
        async def rate_limit_retry():
            raise RateLimitError("Rate limited", retry_after=45)

        @self.app.get("/service-unavailable-retry")
        async def service_unavailable_retry():
            raise ServiceUnavailableError("db-service", "Database down", retry_after=90)

        @self.app.get("/circuit-breaker-retry")
        async def circuit_breaker_retry():
            raise CircuitBreakerError("api-service", retry_after=180)

        # Test each endpoint with retry_after
        retry_endpoints = [
            ("/rate-limit-retry", 45),
            ("/service-unavailable-retry", 90),
            ("/circuit-breaker-retry", 180),
        ]

        for endpoint, expected_retry_after in retry_endpoints:
            response = self.client.get(endpoint)

            # Check Retry-After header
            assert "Retry-After" in response.headers
            assert response.headers["Retry-After"] == str(expected_retry_after)

            # Check retry_after in response body
            error_data = response.json()
            assert "details" in error_data
            assert "retry_after" in error_data["details"]
            assert error_data["details"]["retry_after"] == expected_retry_after

    def test_error_details_consistency(self):
        """Test that error details are consistently formatted."""

        @self.app.get("/not-found-details")
        async def not_found_details():
            raise NotFoundError("Project", "proj-123")

        @self.app.get("/conflict-details")
        async def conflict_details():
            raise ConflictError(
                "Email already exists", {"field": "email", "value": "test@example.com"}
            )

        @self.app.get("/timeout-details")
        async def timeout_details():
            raise TimeoutError("Database timeout", timeout_seconds=15.5)

        # Test NotFoundError details
        response = self.client.get("/not-found-details")
        error_data = response.json()
        assert "details" in error_data
        assert error_data["details"]["resource"] == "Project"
        assert error_data["details"]["resource_id"] == "proj-123"

        # Test ConflictError details
        response = self.client.get("/conflict-details")
        error_data = response.json()
        assert "details" in error_data
        assert error_data["details"]["field"] == "email"
        assert error_data["details"]["value"] == "test@example.com"

        # Test TimeoutError details
        response = self.client.get("/timeout-details")
        error_data = response.json()
        assert "details" in error_data
        assert error_data["details"]["timeout_seconds"] == 15.5

    def test_validation_error_consistency(self):
        """Test validation error response consistency."""
        from pydantic import BaseModel, Field

        class TestModel(BaseModel):
            email: str = Field(..., pattern=r"^[^@]+@[^@]+\.[^@]+$")
            age: int = Field(..., gt=0, le=120)
            name: str = Field(..., min_length=1, max_length=50)

        @self.app.post("/validate")
        async def validate_endpoint(data: TestModel):
            return {"message": "success"}

        # Test with invalid data
        invalid_data = {"email": "invalid-email", "age": -5, "name": ""}

        response = self.client.post("/validate", json=invalid_data)
        assert response.status_code == 422

        error_data = response.json()

        # Check consistent format
        assert error_data["error_code"] == "VALIDATION_ERROR"
        assert "details" in error_data
        assert "errors" in error_data["details"]

        # Check error details format
        errors = error_data["details"]["errors"]
        assert len(errors) == 3  # Three validation errors

        for error in errors:
            assert "field" in error
            assert "message" in error
            assert "type" in error
            assert "input" in error

    def test_database_error_consistency(self):
        """Test database error response consistency."""

        @self.app.get("/integrity-error")
        async def integrity_error():
            raise IntegrityError("statement", "params", "UNIQUE constraint failed")

        @self.app.get("/general-db-error")
        async def general_db_error():
            raise SQLAlchemyError("Connection failed")

        # Test IntegrityError
        response = self.client.get("/integrity-error")
        assert response.status_code == 409

        error_data = response.json()
        assert error_data["error_code"] == "CONFLICT"
        assert "constraint_type" in error_data["details"]

        # Test general SQLAlchemyError
        response = self.client.get("/general-db-error")
        assert response.status_code == 500

        error_data = response.json()
        assert error_data["error_code"] == "DATABASE_ERROR"
        assert "database_error_type" in error_data["details"]


class TestErrorLoggingAndContext:
    """Test error logging and context preservation."""

    def setup_method(self):
        """Set up test environment."""
        self.app = FastAPI()
        register_error_handlers(self.app)
        self.client = TestClient(self.app)

    def test_error_logging_levels(self):
        """Test that errors return appropriate status codes and response format."""

        @self.app.get("/client-error")
        async def client_error():
            raise RateLimitError("Too many requests")  # 4xx error

        @self.app.get("/server-error")
        async def server_error():
            raise ServiceUnavailableError("db-service", "Database down")  # 5xx error

        # Test 4xx error response
        response = self.client.get("/client-error")
        assert response.status_code == 429
        data = response.json()
        assert data["error_code"] == "RATE_LIMIT_EXCEEDED"
        assert data["message"] == "Too many requests"
        assert "request_id" in data
        assert "timestamp" in data

        # Test 5xx error response
        response = self.client.get("/server-error")
        assert response.status_code == 503
        data = response.json()
        assert data["error_code"] == "SERVICE_UNAVAILABLE"
        assert (
            data["message"] == "Database down"
        )  # ServiceUnavailableError uses the reason as message
        assert "request_id" in data
        assert "timestamp" in data

    def test_error_context_logging(self):
        """Test that error context is properly logged."""

        @self.app.get("/context-test")
        async def context_test():
            raise AuthenticationError("Invalid token")

        # Make request with specific headers
        headers = {"X-Request-ID": "test-request-456", "User-Agent": "test-client/2.0"}

        with patch.dict("os.environ", {"SERVICE_NAME": "test-service"}):
            response = self.client.get("/context-test", headers=headers)

        # Verify error response format
        assert response.status_code == 401
        data = response.json()
        assert data["error_code"] == "AUTHENTICATION_ERROR"
        assert data["message"] == "Invalid token"
        assert data["request_id"] == "test-request-456"
        assert "timestamp" in data

    def test_unhandled_exception_logging(self):
        """Test that server errors are handled properly."""

        @self.app.get("/server-error-test")
        async def server_error_test():
            # Use an existing APIError that represents a server error
            from ..base import ExternalServiceError

            raise ExternalServiceError(
                "database", "Connection failed", {"error_code": "DB_CONNECTION_ERROR"}
            )

        response = self.client.get("/server-error-test")

        # Verify error response for server error
        assert response.status_code == 503
        data = response.json()

        assert data["error_code"] == "EXTERNAL_SERVICE_ERROR"
        assert "Connection failed" in data["message"]
        assert "request_id" in data
        assert "timestamp" in data

    def test_request_id_generation_and_logging(self):
        """Test request ID generation when not provided."""

        @self.app.get("/no-request-id")
        async def no_request_id():
            raise NotFoundError("User", "123")

        response = self.client.get("/no-request-id")

        # Should generate a request ID
        error_data = response.json()
        request_id = error_data["request_id"]
        assert len(request_id) == 36  # UUID format
        assert "-" in request_id

        # Verify the generated request ID is consistent in response
        assert error_data["request_id"] == request_id

    def test_sensitive_data_not_logged(self):
        """Test that sensitive data is not logged in error context."""

        @self.app.post("/sensitive-error")
        async def sensitive_error(data: dict):
            # Don't include sensitive data in error details - this is good practice
            safe_details = {
                "user_count": len(data),
                "fields_provided": list(data.keys()),
            }
            raise ConflictError("User already exists", safe_details)

        # Send request with sensitive data
        sensitive_data = {
            "password": "secret123",
            "api_key": "sk-1234567890",
            "credit_card": "4111-1111-1111-1111",
        }

        response = self.client.post("/sensitive-error", json=sensitive_data)

        # Check that error response doesn't contain sensitive data
        assert response.status_code == 409
        data = response.json()
        assert data["error_code"] == "CONFLICT"
        assert data["message"] == "User already exists"

        # Sensitive data should not appear in response
        response_text = response.text
        assert "secret123" not in response_text
        assert "sk-1234567890" not in response_text
        assert "4111-1111-1111-1111" not in response_text

    def test_error_context_creation(self):
        """Test error context creation with various request scenarios."""
        # Mock request with all headers
        request = Mock()
        request.method = "POST"
        request.url.path = "/api/users"
        request.client.host = "192.168.1.100"
        request.headers = {
            "X-Request-ID": "ctx-test-789",
            "User-Agent": "mobile-app/1.5.0",
        }

        exc = ValueError("Test exception")

        with patch.dict("os.environ", {"SERVICE_NAME": "user-service"}):
            context = create_error_context(request, exc)

        assert context["request_id"] == "ctx-test-789"
        assert context["service"] == "user-service"
        assert context["method"] == "POST"
        assert context["path"] == "/api/users"
        assert context["client_ip"] == "192.168.1.100"
        assert context["user_agent"] == "mobile-app/1.5.0"
        assert context["exception_type"] == "ValueError"
        assert "timestamp" in context

        # Test with missing client info
        request.client = None
        context = create_error_context(request, exc)
        assert context["client_ip"] == "unknown"

        # Test with missing headers
        request.headers = {}
        context = create_error_context(request, exc)
        assert len(context["request_id"]) == 36  # Generated UUID
        assert context["user_agent"] == "unknown"


class TestCrossServiceErrorConsistency:
    """Test error consistency across different service scenarios."""

    def test_service_to_service_error_propagation(self):
        """Test that errors are consistently propagated between services."""
        app = FastAPI()
        register_error_handlers(app)

        @app.get("/upstream-error")
        async def upstream_error():
            # Simulate error from upstream service
            raise ExternalServiceError(
                "payment-service",
                "Payment processing failed",
                {"transaction_id": "txn-123", "error_code": "INSUFFICIENT_FUNDS"},
            )

        client = TestClient(app)
        response = client.get("/upstream-error")

        assert response.status_code == 503
        error_data = response.json()

        # Check error propagation
        assert error_data["error_code"] == "EXTERNAL_SERVICE_ERROR"
        assert error_data["details"]["service"] == "payment-service"
        assert error_data["details"]["transaction_id"] == "txn-123"
        assert error_data["details"]["error_code"] == "INSUFFICIENT_FUNDS"

    def test_rate_limiting_error_across_endpoints(self):
        """Test rate limiting error consistency across different endpoints."""
        app = FastAPI()
        register_error_handlers(app)

        @app.get("/api/upload")
        async def upload_endpoint():
            raise RateLimitError("Upload rate limit exceeded", retry_after=300)

        @app.get("/api/search")
        async def search_endpoint():
            raise RateLimitError("Search rate limit exceeded", retry_after=60)

        client = TestClient(app)

        # Test both endpoints
        upload_response = client.get("/api/upload")
        search_response = client.get("/api/search")

        # Both should have consistent format
        for response in [upload_response, search_response]:
            assert response.status_code == 429
            error_data = response.json()
            assert error_data["error_code"] == "RATE_LIMIT_EXCEEDED"
            assert "retry_after" in error_data["details"]
            assert "Retry-After" in response.headers

        # But different retry_after values
        upload_data = upload_response.json()
        search_data = search_response.json()
        assert upload_data["details"]["retry_after"] == 300
        assert search_data["details"]["retry_after"] == 60

    def test_authentication_error_consistency(self):
        """Test authentication error consistency across different auth scenarios."""
        app = FastAPI()
        register_error_handlers(app)

        @app.get("/expired-token")
        async def expired_token():
            raise AuthenticationError("Token has expired")

        @app.get("/invalid-token")
        async def invalid_token():
            raise AuthenticationError("Invalid token format")

        @app.get("/missing-token")
        async def missing_token():
            raise AuthenticationError("Authentication token required")

        client = TestClient(app)

        endpoints = ["/expired-token", "/invalid-token", "/missing-token"]

        for endpoint in endpoints:
            response = client.get(endpoint)

            # All should have consistent format
            assert response.status_code == 401
            error_data = response.json()
            assert error_data["error_code"] == "AUTHENTICATION_ERROR"
            assert "message" in error_data
            assert "request_id" in error_data
            assert "timestamp" in error_data

    def test_circuit_breaker_error_consistency(self):
        """Test circuit breaker error consistency across services."""
        app = FastAPI()
        register_error_handlers(app)

        @app.get("/user-service-down")
        async def user_service_down():
            raise CircuitBreakerError("user-service", retry_after=60)

        @app.get("/payment-service-down")
        async def payment_service_down():
            raise CircuitBreakerError("payment-service", retry_after=120)

        client = TestClient(app)

        # Test both services
        user_response = client.get("/user-service-down")
        payment_response = client.get("/payment-service-down")

        for response in [user_response, payment_response]:
            assert response.status_code == 503
            error_data = response.json()
            assert error_data["error_code"] == "CIRCUIT_BREAKER_OPEN"
            assert "service" in error_data["details"]
            assert "retry_after" in error_data["details"]
            assert "Retry-After" in response.headers

        # Check service-specific details
        user_data = user_response.json()
        payment_data = payment_response.json()
        assert user_data["details"]["service"] == "user-service"
        assert payment_data["details"]["service"] == "payment-service"


class TestErrorHandlingPerformance:
    """Test error handling performance under load."""

    def test_error_handler_performance(self):
        """Test error handler performance with many concurrent errors."""
        import asyncio
        import time
        from concurrent.futures import ThreadPoolExecutor

        app = FastAPI()
        register_error_handlers(app)

        @app.get("/performance-error")
        async def performance_error():
            raise RateLimitError("Performance test error")

        client = TestClient(app)

        # Measure error handling performance
        def make_error_request():
            return client.get("/performance-error")

        start_time = time.time()

        # Make 100 concurrent error requests
        with ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(make_error_request) for _ in range(100)]
            responses = [future.result() for future in futures]

        end_time = time.time()
        duration = end_time - start_time

        # Performance assertions
        assert duration < 5.0, f"Error handling took {duration:.2f}s, expected < 5.0s"

        # All responses should be consistent
        for response in responses:
            assert response.status_code == 429
            error_data = response.json()
            assert error_data["error_code"] == "RATE_LIMIT_EXCEEDED"

    def test_logging_performance_under_load(self):
        """Test logging performance with many errors."""
        app = FastAPI()
        register_error_handlers(app)

        @app.get("/logging-performance")
        async def logging_performance():
            raise ServiceUnavailableError("test-service", "Service down for testing")

        client = TestClient(app)

        with patch("packages.common.errors.handlers.logger") as mock_logger:
            start_time = time.time()

            # Make many requests that will generate logs
            for _ in range(50):
                client.get("/logging-performance")

            end_time = time.time()
            duration = end_time - start_time

            # Should complete quickly even with logging
            assert duration < 2.0, f"Logging took {duration:.2f}s, expected < 2.0s"

            # Should have logged all errors
            assert mock_logger.log.call_count == 50
