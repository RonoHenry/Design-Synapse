"""Request logging middleware for the Knowledge Service."""
import time
import uuid
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from ..core.logging import get_logger, log_api_request

logger = get_logger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware to log all API requests with timing and context."""

    def __init__(self, app, skip_paths: list = None):
        """Initialize request logging middleware.

        Args:
            app: FastAPI application
            skip_paths: List of paths to skip logging for
        """
        super().__init__(app)
        self.skip_paths = skip_paths or [
            "/health",
            "/metrics",
            "/docs",
            "/redoc",
            "/openapi.json",
        ]

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with logging."""
        # Skip logging for certain paths
        if any(skip_path in request.url.path for skip_path in self.skip_paths):
            return await call_next(request)

        # Generate request ID if not present
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))

        # Add request ID to request state
        request.state.request_id = request_id

        # Get user context if available
        user_id = None
        if hasattr(request.state, "user") and request.state.user:
            user_id = request.state.user.user_id

        # Record start time
        start_time = time.time()

        # Process request
        try:
            response = await call_next(request)

            # Calculate response time
            response_time_ms = (time.time() - start_time) * 1000

            # Log successful request
            log_api_request(
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
                response_time_ms=response_time_ms,
                user_id=user_id,
                request_id=request_id,
            )

            # Add request ID to response headers
            response.headers["X-Request-ID"] = request_id

            return response

        except Exception as e:
            # Calculate response time for failed requests
            response_time_ms = (time.time() - start_time) * 1000

            # Log failed request
            log_api_request(
                method=request.method,
                path=request.url.path,
                status_code=500,
                response_time_ms=response_time_ms,
                user_id=user_id,
                request_id=request_id,
                error=str(e),
            )

            # Re-raise the exception
            raise
