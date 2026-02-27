"""FastAPI middleware for rate limiting."""

import logging
from typing import Callable, Dict, Optional

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from packages.common.errors import RateLimitError

from .algorithms import (RateLimiter, SlidingWindowRateLimiter,
                         TokenBucketRateLimiter)
from .models import RateLimitConfig, RateLimitHeaders, RateLimitStrategy
from .storage import InMemoryStorage, RateLimitStorage

logger = logging.getLogger(__name__)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """FastAPI middleware for rate limiting requests."""

    def __init__(
        self,
        app,
        storage: Optional[RateLimitStorage] = None,
        default_config: Optional[RateLimitConfig] = None,
        endpoint_configs: Optional[Dict[str, RateLimitConfig]] = None,
        client_id_extractor: Optional[Callable[[Request], str]] = None,
        skip_paths: Optional[list] = None,
    ):
        """Initialize rate limiting middleware.

        Args:
            app: FastAPI application
            storage: Storage backend for rate limit data
            default_config: Default rate limit configuration
            endpoint_configs: Per-endpoint rate limit configurations
            client_id_extractor: Function to extract client ID from request
            skip_paths: List of paths to skip rate limiting
        """
        super().__init__(app)

        self.storage = storage or InMemoryStorage()
        self.default_config = default_config or RateLimitConfig(
            requests_per_window=100,
            window_size_seconds=3600,  # 1 hour
            strategy=RateLimitStrategy.SLIDING_WINDOW,
        )
        self.endpoint_configs = endpoint_configs or {}
        self.client_id_extractor = (
            client_id_extractor or self._default_client_id_extractor
        )
        self.skip_paths = skip_paths or [
            "/health",
            "/metrics",
            "/docs",
            "/openapi.json",
        ]

        # Cache rate limiters
        self._limiters: Dict[str, RateLimiter] = {}

    def _default_client_id_extractor(self, request: Request) -> str:
        """Default client ID extraction from request."""
        # Try to get user ID from auth context
        if hasattr(request.state, "user") and request.state.user:
            return f"user:{request.state.user.user_id}"

        # Fall back to IP address
        client_ip = request.client.host if request.client else "unknown"
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            client_ip = forwarded_for.split(",")[0].strip()

        return f"ip:{client_ip}"

    def _get_rate_limiter(self, endpoint: str, config: RateLimitConfig) -> RateLimiter:
        """Get or create rate limiter for endpoint."""
        cache_key = f"{endpoint}:{config.strategy.value}"

        if cache_key not in self._limiters:
            if config.strategy == RateLimitStrategy.SLIDING_WINDOW:
                self._limiters[cache_key] = SlidingWindowRateLimiter(
                    config, self.storage
                )
            elif config.strategy == RateLimitStrategy.TOKEN_BUCKET:
                self._limiters[cache_key] = TokenBucketRateLimiter(config, self.storage)
            else:
                raise ValueError(f"Unknown rate limit strategy: {config.strategy}")

        return self._limiters[cache_key]

    def _get_endpoint_config(self, path: str, method: str) -> RateLimitConfig:
        """Get rate limit configuration for endpoint."""
        # Try exact path match first
        endpoint_key = f"{method}:{path}"
        if endpoint_key in self.endpoint_configs:
            return self.endpoint_configs[endpoint_key]

        # Try path-only match
        if path in self.endpoint_configs:
            return self.endpoint_configs[path]

        # Try method-only match
        if method in self.endpoint_configs:
            return self.endpoint_configs[method]

        return self.default_config

    def _should_skip_path(self, path: str) -> bool:
        """Check if path should be skipped for rate limiting."""
        return any(skip_path in path for skip_path in self.skip_paths)

    async def dispatch(self, request: Request, call_next) -> Response:
        """Process request with rate limiting."""
        path = request.url.path
        method = request.method

        # Skip rate limiting for certain paths
        if self._should_skip_path(path):
            return await call_next(request)

        try:
            # Extract client ID
            client_id = self.client_id_extractor(request)

            # Get rate limit configuration for this endpoint
            config = self._get_endpoint_config(path, method)

            # Get rate limiter
            rate_limiter = self._get_rate_limiter(path, config)

            # Check rate limit
            result = await rate_limiter.check_rate_limit(client_id, path)

            if not result.allowed:
                # Rate limit exceeded
                logger.warning(
                    f"Rate limit exceeded for client {client_id} on {method} {path}",
                    extra={
                        "client_id": client_id,
                        "endpoint": path,
                        "method": method,
                        "retry_after": result.retry_after,
                    },
                )

                raise RateLimitError(
                    message=f"Rate limit exceeded. Try again in {result.retry_after} seconds.",
                    retry_after=result.retry_after,
                )

            # Process request
            response = await call_next(request)

            # Add rate limit headers
            response.headers[RateLimitHeaders.LIMIT] = str(config.requests_per_window)
            response.headers[RateLimitHeaders.REMAINING] = str(result.remaining)
            response.headers[RateLimitHeaders.RESET] = str(
                int(result.reset_time.timestamp())
            )

            return response

        except RateLimitError:
            # Re-raise rate limit errors
            raise
        except Exception as e:
            # Log error but don't block request
            logger.error(f"Rate limiting error for {method} {path}: {e}", exc_info=True)
            return await call_next(request)
