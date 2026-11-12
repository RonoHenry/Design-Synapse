"""Middleware for the Architectural Service API."""

import time
from typing import Callable

from fastapi import Request, Response
from src.core.config import settings
from src.core.metrics import get_metrics_collector
from starlette.middleware.base import BaseHTTPMiddleware


class MetricsMiddleware(BaseHTTPMiddleware):
    """Middleware to collect request metrics."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Collect metrics for each request."""
        start_time = time.time()

        # Process request
        response = await call_next(request)

        # Calculate latency
        latency_ms = (time.time() - start_time) * 1000

        # Record metrics
        metrics_collector = get_metrics_collector()
        metrics_collector.record_request(
            endpoint=request.url.path,
            method=request.method,
            status_code=response.status_code,
            latency_ms=latency_ms,
            error=None
            if response.status_code < 400
            else f"HTTP {response.status_code}",
        )

        return response


class ResponseHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware to add standard response headers."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Add standard headers to all responses."""
        start_time = time.time()

        response = await call_next(request)

        # Calculate processing time
        process_time = time.time() - start_time

        # Add cache-control headers
        if request.method == "GET":
            if "/health" in str(request.url):
                response.headers[
                    "Cache-Control"
                ] = "no-cache, no-store, must-revalidate"
            elif "/api/v1/" in str(request.url):
                response.headers["Cache-Control"] = "private, max-age=300"  # 5 minutes
            else:
                response.headers["Cache-Control"] = "public, max-age=3600"  # 1 hour
        else:
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"

        # Add security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"

        # Add processing time header
        response.headers["X-Process-Time"] = str(process_time)

        # Add service identification
        response.headers["X-Service"] = settings.app_name
        response.headers["X-Version"] = settings.app_version

        # Add rate limiting headers (placeholder - would be populated by rate limiter)
        response.headers["X-RateLimit-Limit"] = "1000"
        response.headers["X-RateLimit-Remaining"] = "999"
        response.headers["X-RateLimit-Reset"] = str(int(time.time()) + 3600)

        return response


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Middleware to add request ID to all requests."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Add request ID to request state and response headers."""
        import uuid

        # Generate or extract request ID
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))

        # Add to request state for use in handlers
        request.state.request_id = request_id

        response = await call_next(request)

        # Add request ID to response headers
        response.headers["X-Request-ID"] = request_id

        return response
