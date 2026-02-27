"""Base HTTP client with retry, circuit breaker, and logging."""

import asyncio
import logging
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, Optional

import httpx

logger = logging.getLogger(__name__)


class CircuitBreakerState(Enum):
    """Circuit breaker states."""

    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing if service recovered


class BaseHTTPClient:
    """Base HTTP client with retry, circuit breaker, and logging capabilities."""

    def __init__(
        self,
        base_url: str,
        timeout: float = 30.0,
        max_retries: int = 3,
        circuit_breaker_threshold: int = 5,
        circuit_breaker_timeout: int = 60,
        headers: Optional[Dict[str, str]] = None,
    ):
        """Initialize the HTTP client.

        Args:
            base_url: Base URL for the service
            timeout: Request timeout in seconds
            max_retries: Maximum number of retry attempts
            circuit_breaker_threshold: Number of failures before opening circuit
            circuit_breaker_timeout: Seconds to wait before trying half-open state
            headers: Default headers to include with requests
        """
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries
        self.circuit_breaker_threshold = circuit_breaker_threshold
        self.circuit_breaker_timeout = circuit_breaker_timeout
        self.headers = headers or {}

        # Circuit breaker state
        self.circuit_breaker_state = CircuitBreakerState.CLOSED
        self.failure_count = 0
        self.last_failure_time: Optional[datetime] = None

        # HTTP client
        self._client = httpx.AsyncClient(timeout=timeout)

    async def close(self):
        """Close the HTTP client."""
        await self._client.aclose()

    def _check_circuit_breaker(self):
        """Check circuit breaker state and update if needed."""
        if self.circuit_breaker_state == CircuitBreakerState.OPEN:
            if self.last_failure_time:
                time_since_failure = (
                    datetime.now() - self.last_failure_time
                ).total_seconds()
                if time_since_failure >= self.circuit_breaker_timeout:
                    logger.info("Circuit breaker transitioning to HALF_OPEN")
                    self.circuit_breaker_state = CircuitBreakerState.HALF_OPEN
                    self.failure_count = 0
                else:
                    raise Exception(
                        f"Circuit breaker is OPEN. Service unavailable. "
                        f"Retry in {self.circuit_breaker_timeout - time_since_failure:.0f}s"
                    )

    def _record_success(self):
        """Record a successful request."""
        if self.circuit_breaker_state == CircuitBreakerState.HALF_OPEN:
            logger.info(
                "Circuit breaker transitioning to CLOSED after successful request"
            )
            self.circuit_breaker_state = CircuitBreakerState.CLOSED
        self.failure_count = 0
        self.last_failure_time = None

    def _record_failure(self):
        """Record a failed request."""
        self.failure_count += 1
        self.last_failure_time = datetime.now()

        if self.failure_count >= self.circuit_breaker_threshold:
            logger.warning(f"Circuit breaker OPEN after {self.failure_count} failures")
            self.circuit_breaker_state = CircuitBreakerState.OPEN

    async def _make_request(self, method: str, path: str, **kwargs) -> Any:
        """Make an HTTP request with retry and circuit breaker logic.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE, etc.)
            path: API path (will be appended to base_url)
            **kwargs: Additional arguments to pass to httpx

        Returns:
            Response JSON data

        Raises:
            Exception: If request fails after all retries
        """
        # Check circuit breaker
        self._check_circuit_breaker()

        url = f"{self.base_url}{path}"
        last_exception = None

        for attempt in range(self.max_retries):
            try:
                logger.info(
                    f"Request: {method} {url} (attempt {attempt + 1}/{self.max_retries})"
                )

                # Merge headers
                request_headers = {**self.headers}
                if "headers" in kwargs:
                    request_headers.update(kwargs.pop("headers"))

                # Make the request
                response = await self._client.request(
                    method, url, headers=request_headers, timeout=self.timeout, **kwargs
                )

                # Log success
                logger.info(f"Response: {method} {url} - {response.status_code}")

                # Record success for circuit breaker (only for successful status codes)
                if response.status_code < 400:
                    self._record_success()

                # Return response object so caller can check status code
                return response

            except (httpx.TimeoutException, httpx.ConnectError) as e:
                # Transient errors - retry with backoff
                last_exception = e
                logger.warning(f"Transient error on attempt {attempt + 1}: {e}")

                if attempt < self.max_retries - 1:
                    # Exponential backoff: 1s, 2s, 4s, etc.
                    backoff_time = 2**attempt
                    logger.info(f"Retrying in {backoff_time}s...")
                    await asyncio.sleep(backoff_time)
                else:
                    self._record_failure()

            except httpx.HTTPStatusError as e:
                # HTTP errors (4xx, 5xx) - only record failure for 5xx errors
                logger.error(f"HTTP error: {e.response.status_code} - {e}")
                if e.response.status_code >= 500:
                    self._record_failure()
                # Return the error response so tests can check it
                return e.response

            except Exception as e:
                # Unexpected errors
                logger.error(f"Unexpected error: {e}")
                self._record_failure()
                raise

        # All retries exhausted
        self._record_failure()
        raise Exception(
            f"Request failed after {self.max_retries} attempts: {last_exception}"
        )

    async def get(self, path: str, **kwargs) -> httpx.Response:
        """Make a GET request.

        Args:
            path: API path
            **kwargs: Additional arguments

        Returns:
            HTTP response object
        """
        return await self._make_request("GET", path, **kwargs)

    async def post(self, path: str, **kwargs) -> httpx.Response:
        """Make a POST request.

        Args:
            path: API path
            **kwargs: Additional arguments (json, data, etc.)

        Returns:
            HTTP response object
        """
        return await self._make_request("POST", path, **kwargs)

    async def put(self, path: str, **kwargs) -> httpx.Response:
        """Make a PUT request.

        Args:
            path: API path
            **kwargs: Additional arguments

        Returns:
            HTTP response object
        """
        return await self._make_request("PUT", path, **kwargs)

    async def patch(self, path: str, **kwargs) -> httpx.Response:
        """Make a PATCH request.

        Args:
            path: API path
            **kwargs: Additional arguments

        Returns:
            HTTP response object
        """
        return await self._make_request("PATCH", path, **kwargs)

    async def delete(self, path: str, **kwargs) -> httpx.Response:
        """Make a DELETE request.

        Args:
            path: API path
            **kwargs: Additional arguments

        Returns:
            HTTP response object
        """
        return await self._make_request("DELETE", path, **kwargs)
