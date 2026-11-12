"""Tests for rate limiting middleware."""

from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from starlette.responses import JSONResponse

from packages.common.errors import RateLimitError

from ..middleware import RateLimitMiddleware
from ..models import RateLimitConfig, RateLimitHeaders, RateLimitStrategy
from ..storage import InMemoryStorage


@pytest.fixture
def app():
    """FastAPI test application."""
    app = FastAPI()

    @app.get("/test")
    async def test_endpoint():
        return {"message": "success"}

    @app.get("/health")
    async def health_endpoint():
        return {"status": "healthy"}

    return app


@pytest.fixture
def rate_limited_app(app):
    """FastAPI app with rate limiting middleware."""
    config = RateLimitConfig(
        requests_per_window=5,
        window_size_seconds=60,
        strategy=RateLimitStrategy.SLIDING_WINDOW,
    )

    app.add_middleware(
        RateLimitMiddleware,
        storage=InMemoryStorage(),
        default_config=config,
        skip_paths=["/health"],
    )

    return app


class TestRateLimitMiddleware:
    """Test rate limiting middleware."""

    def test_requests_within_limit_allowed(self, rate_limited_app):
        """Test requests within limit are allowed."""
        client = TestClient(rate_limited_app)

        # Make requests within limit
        for i in range(5):
            response = client.get("/test")
            assert response.status_code == 200

            # Check rate limit headers
            assert RateLimitHeaders.LIMIT in response.headers
            assert RateLimitHeaders.REMAINING in response.headers
            assert RateLimitHeaders.RESET in response.headers

            assert response.headers[RateLimitHeaders.LIMIT] == "5"
            assert response.headers[RateLimitHeaders.REMAINING] == str(5 - (i + 1))

    def test_rate_limit_exceeded(self, rate_limited_app):
        """Test rate limit exceeded returns 429."""
        client = TestClient(rate_limited_app)

        # Use up the rate limit
        for _ in range(5):
            response = client.get("/test")
            assert response.status_code == 200

        # Next request should be rate limited
        response = client.get("/test")
        assert response.status_code == 429

        # Check error response format
        error_data = response.json()
        assert error_data["error_code"] == "RATE_LIMIT_EXCEEDED"
        assert "retry_after" in error_data["details"]

        # Check retry-after header
        assert "Retry-After" in response.headers

    def test_skip_paths_not_rate_limited(self, rate_limited_app):
        """Test skip paths are not rate limited."""
        client = TestClient(rate_limited_app)

        # Make many requests to health endpoint
        for _ in range(10):
            response = client.get("/health")
            assert response.status_code == 200
            # Should not have rate limit headers
            assert RateLimitHeaders.LIMIT not in response.headers

    def test_different_endpoints_separate_limits(self):
        """Test different endpoints can have separate limits."""
        app = FastAPI()

        @app.get("/api/upload")
        async def upload_endpoint():
            return {"message": "uploaded"}

        @app.get("/api/search")
        async def search_endpoint():
            return {"message": "results"}

        # Configure different limits for endpoints
        endpoint_configs = {
            "/api/upload": RateLimitConfig(
                requests_per_window=2, window_size_seconds=60
            ),
            "/api/search": RateLimitConfig(
                requests_per_window=10, window_size_seconds=60
            ),
        }

        app.add_middleware(
            RateLimitMiddleware,
            storage=InMemoryStorage(),
            endpoint_configs=endpoint_configs,
        )

        client = TestClient(app)

        # Upload endpoint should be limited to 2 requests
        for _ in range(2):
            response = client.get("/api/upload")
            assert response.status_code == 200

        response = client.get("/api/upload")
        assert response.status_code == 429

        # Search endpoint should still work (separate limit)
        response = client.get("/api/search")
        assert response.status_code == 200

    def test_custom_client_id_extractor(self):
        """Test custom client ID extraction."""
        app = FastAPI()

        @app.get("/test")
        async def test_endpoint():
            return {"message": "success"}

        def custom_extractor(request: Request) -> str:
            api_key = request.headers.get("X-API-Key", "anonymous")
            return f"api_key:{api_key}"

        app.add_middleware(
            RateLimitMiddleware,
            storage=InMemoryStorage(),
            default_config=RateLimitConfig(
                requests_per_window=2, window_size_seconds=60
            ),
            client_id_extractor=custom_extractor,
        )

        client = TestClient(app)

        # Requests with different API keys should have separate limits
        headers1 = {"X-API-Key": "key1"}
        headers2 = {"X-API-Key": "key2"}

        # Use up limit for key1
        for _ in range(2):
            response = client.get("/test", headers=headers1)
            assert response.status_code == 200

        response = client.get("/test", headers=headers1)
        assert response.status_code == 429

        # key2 should still work
        response = client.get("/test", headers=headers2)
        assert response.status_code == 200

    def test_token_bucket_strategy(self):
        """Test token bucket rate limiting strategy."""
        app = FastAPI()

        @app.get("/test")
        async def test_endpoint():
            return {"message": "success"}

        config = RateLimitConfig(
            requests_per_window=5,
            window_size_seconds=60,
            strategy=RateLimitStrategy.TOKEN_BUCKET,
            burst_capacity=8,
            refill_rate=0.1,
        )

        app.add_middleware(
            RateLimitMiddleware, storage=InMemoryStorage(), default_config=config
        )

        client = TestClient(app)

        # Should be able to make burst_capacity requests
        for i in range(8):
            response = client.get("/test")
            assert response.status_code == 200
            assert response.headers[RateLimitHeaders.REMAINING] == str(8 - (i + 1))

        # Next request should be rate limited
        response = client.get("/test")
        assert response.status_code == 429

    @patch("packages.common.rate_limiting.middleware.logger")
    def test_middleware_error_handling(self, mock_logger, app):
        """Test middleware handles errors gracefully."""
        # Create middleware with storage that will raise an exception
        storage = Mock()
        storage.get_quota = AsyncMock(side_effect=Exception("Storage error"))

        app.add_middleware(
            RateLimitMiddleware,
            storage=storage,
            default_config=RateLimitConfig(
                requests_per_window=5, window_size_seconds=60
            ),
        )

        client = TestClient(app)

        # Request should still succeed despite storage error
        response = client.get("/test")
        assert response.status_code == 200

        # Error should be logged
        mock_logger.error.assert_called_once()

    def test_rate_limit_headers_format(self, rate_limited_app):
        """Test rate limit headers are properly formatted."""
        client = TestClient(rate_limited_app)

        response = client.get("/test")
        assert response.status_code == 200

        # Check header values are valid
        limit = int(response.headers[RateLimitHeaders.LIMIT])
        remaining = int(response.headers[RateLimitHeaders.REMAINING])
        reset_timestamp = int(response.headers[RateLimitHeaders.RESET])

        assert limit == 5
        assert remaining == 4
        assert reset_timestamp > 0  # Should be a valid timestamp
