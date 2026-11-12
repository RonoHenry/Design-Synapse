"""Integration tests between rate limiting and error handling systems."""

import asyncio
import time
from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from packages.common.errors import RateLimitError
from packages.common.errors.handlers import register_error_handlers

from ..middleware import RateLimitMiddleware
from ..models import RateLimitConfig, RateLimitStrategy
from ..storage import InMemoryStorage


class TestRateLimitingErrorIntegration:
    """Test integration between rate limiting and error handling."""

    def setup_method(self):
        """Set up test application with rate limiting and error handling."""
        self.app = FastAPI()

        # Add test endpoints
        @self.app.get("/api/test")
        async def test_endpoint():
            return {"message": "success"}

        @self.app.get("/api/upload")
        async def upload_endpoint():
            return {"message": "uploaded"}

        # Configure rate limiting
        config = RateLimitConfig(
            requests_per_window=3,
            window_size_seconds=60,
            strategy=RateLimitStrategy.SLIDING_WINDOW,
        )

        self.app.add_middleware(
            RateLimitMiddleware, storage=InMemoryStorage(), default_config=config
        )

        # Register error handlers
        register_error_handlers(self.app)

        self.client = TestClient(self.app)

    def test_rate_limit_error_response_format(self):
        """Test that rate limit errors have consistent response format."""
        # Use up the rate limit
        for _ in range(3):
            response = self.client.get("/api/test")
            assert response.status_code == 200

        # Next request should be rate limited
        response = self.client.get("/api/test")
        assert response.status_code == 429

        # Check error response format
        error_data = response.json()

        # Required fields
        assert "message" in error_data
        assert "error_code" in error_data
        assert "request_id" in error_data
        assert "timestamp" in error_data
        assert "service" in error_data

        # Rate limit specific fields
        assert error_data["error_code"] == "RATE_LIMIT_EXCEEDED"
        assert "details" in error_data
        assert "retry_after" in error_data["details"]

        # Headers
        assert "Retry-After" in response.headers
        assert response.headers["Retry-After"] == str(
            error_data["details"]["retry_after"]
        )

    @patch("packages.common.errors.handlers.logger")
    def test_rate_limit_error_logging(self, mock_logger):
        """Test that rate limit errors are properly logged."""
        # Trigger rate limit
        for _ in range(4):  # 3 allowed + 1 rate limited
            self.client.get("/api/test")

        # Verify logging
        mock_logger.log.assert_called()
        call_args = mock_logger.log.call_args

        # Should be logged as WARNING (4xx error)
        assert call_args[0][0] == 30  # WARNING level

        # Check log context
        extra_context = call_args[1]["extra"]
        assert extra_context["error_code"] == "RATE_LIMIT_EXCEEDED"
        assert extra_context["status_code"] == 429
        assert "retry_after" in extra_context["details"]

    def test_rate_limit_headers_consistency(self):
        """Test that rate limit headers are consistent across requests."""
        responses = []

        # Make requests and collect responses
        for i in range(5):  # 3 allowed + 2 rate limited
            response = self.client.get("/api/test")
            responses.append(response)

        # Check allowed requests have proper headers
        for i, response in enumerate(responses[:3]):
            assert response.status_code == 200
            assert "X-RateLimit-Limit" in response.headers
            assert "X-RateLimit-Remaining" in response.headers
            assert "X-RateLimit-Reset" in response.headers

            assert response.headers["X-RateLimit-Limit"] == "3"
            assert response.headers["X-RateLimit-Remaining"] == str(3 - (i + 1))

        # Check rate limited requests
        for response in responses[3:]:
            assert response.status_code == 429
            assert "Retry-After" in response.headers

            error_data = response.json()
            assert error_data["error_code"] == "RATE_LIMIT_EXCEEDED"

    def test_different_endpoints_separate_error_tracking(self):
        """Test that different endpoints have separate rate limit error tracking."""
        # Use up rate limit for /api/test
        for _ in range(3):
            response = self.client.get("/api/test")
            assert response.status_code == 200

        # /api/test should be rate limited
        response = self.client.get("/api/test")
        assert response.status_code == 429

        # /api/upload should still work
        response = self.client.get("/api/upload")
        assert response.status_code == 200

        # Use up rate limit for /api/upload
        for _ in range(2):  # Already made 1 request
            response = self.client.get("/api/upload")
            assert response.status_code == 200

        # Now /api/upload should be rate limited too
        response = self.client.get("/api/upload")
        assert response.status_code == 429

        # Both should have consistent error format
        test_error = self.client.get("/api/test").json()
        upload_error = self.client.get("/api/upload").json()

        assert test_error["error_code"] == upload_error["error_code"]
        assert "retry_after" in test_error["details"]
        assert "retry_after" in upload_error["details"]

    def test_rate_limit_error_context_preservation(self):
        """Test that error context is preserved in rate limit errors."""
        # Make requests with specific headers
        headers = {
            "X-Request-ID": "test-rate-limit-123",
            "User-Agent": "test-client/1.0",
        }

        # Use up rate limit
        for _ in range(3):
            self.client.get("/api/test", headers=headers)

        # Trigger rate limit error
        with patch("packages.common.errors.handlers.logger") as mock_logger:
            response = self.client.get("/api/test", headers=headers)

        assert response.status_code == 429

        # Check response contains request context
        error_data = response.json()
        assert error_data["request_id"] == "test-rate-limit-123"

        # Check logging context
        mock_logger.log.assert_called()
        call_args = mock_logger.log.call_args
        extra_context = call_args[1]["extra"]

        assert extra_context["request_id"] == "test-rate-limit-123"
        assert extra_context["user_agent"] == "test-client/1.0"
        assert extra_context["method"] == "GET"
        assert extra_context["path"] == "/api/test"

    @patch("packages.common.rate_limiting.middleware.logger")
    def test_rate_limiting_middleware_error_handling(self, mock_middleware_logger):
        """Test that rate limiting middleware handles errors gracefully."""
        # Create app with failing storage
        app = FastAPI()

        @app.get("/api/failing-storage")
        async def failing_storage_endpoint():
            return {"message": "success"}

        # Mock storage that fails
        failing_storage = Mock()
        failing_storage.get_quota = AsyncMock(side_effect=Exception("Storage failure"))

        config = RateLimitConfig(requests_per_window=5, window_size_seconds=60)

        app.add_middleware(
            RateLimitMiddleware, storage=failing_storage, default_config=config
        )

        register_error_handlers(app)
        client = TestClient(app)

        # Request should still succeed despite storage failure
        response = client.get("/api/failing-storage")
        assert response.status_code == 200

        # Middleware should log the error
        mock_middleware_logger.error.assert_called()

    def test_concurrent_rate_limit_error_consistency(self):
        """Test error consistency under concurrent rate limiting."""
        import queue
        import threading

        # Use a queue to collect responses from threads
        response_queue = queue.Queue()

        def make_request():
            response = self.client.get("/api/test")
            response_queue.put(
                {
                    "status_code": response.status_code,
                    "data": response.json() if response.status_code != 200 else None,
                }
            )

        # Create many concurrent requests
        threads = []
        for _ in range(20):
            thread = threading.Thread(target=make_request)
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Collect all responses
        responses = []
        while not response_queue.empty():
            responses.append(response_queue.get())

        # Count successful vs rate limited responses
        successful = [r for r in responses if r["status_code"] == 200]
        rate_limited = [r for r in responses if r["status_code"] == 429]

        # Should have exactly 3 successful requests
        assert len(successful) == 3
        assert len(rate_limited) == 17

        # All rate limited responses should have consistent format
        for response in rate_limited:
            error_data = response["data"]
            assert error_data["error_code"] == "RATE_LIMIT_EXCEEDED"
            assert "retry_after" in error_data["details"]
            assert "request_id" in error_data
            assert "timestamp" in error_data

    def test_rate_limit_reset_after_window(self):
        """Test that rate limits reset properly and errors stop occurring."""
        # Use short window for testing
        app = FastAPI()

        @app.get("/api/reset-test")
        async def reset_test_endpoint():
            return {"message": "success"}

        config = RateLimitConfig(
            requests_per_window=2,
            window_size_seconds=1,  # 1 second window
            strategy=RateLimitStrategy.SLIDING_WINDOW,
        )

        app.add_middleware(
            RateLimitMiddleware, storage=InMemoryStorage(), default_config=config
        )

        register_error_handlers(app)
        client = TestClient(app)

        # Use up rate limit
        for _ in range(2):
            response = client.get("/api/reset-test")
            assert response.status_code == 200

        # Should be rate limited
        response = client.get("/api/reset-test")
        assert response.status_code == 429

        # Wait for window to reset
        time.sleep(1.1)

        # Should work again
        response = client.get("/api/reset-test")
        assert response.status_code == 200, "Rate limit should have reset"

        # Should be able to make another request
        response = client.get("/api/reset-test")
        assert response.status_code == 200

        # Third request should be rate limited again
        response = client.get("/api/reset-test")
        assert response.status_code == 429
