"""Base HTTP client with retry, circuit breaker, and logging."""

import asyncio
import logging
from enum import Enum
from typing import Any, Dict, Optional
from datetime import datetime, timedelta

import httpx


logger = logging.getLogger(__name__)


class CircuitBreakerState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"  # Normal operation
    OPEN = "open"      # Failing, reject requests
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
    ):
        """Initialize the HTTP client.
        
        Args:
            base_url: Base URL for the service
            timeout: Request timeout in seconds
            max_retries: Maximum number of retry attempts
            circuit_breaker_threshold: Number of failures before opening circuit
            circuit_breaker_timeout: Seconds to wait before trying half-open state
        """
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries
        self.circuit_breaker_threshold = circuit_breaker_threshold
        self.circuit_breaker_timeout = circuit_breaker_timeout
        
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
                time_since_failure = (datetime.now() - self.last_failure_time).total_seconds()
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
            logger.info("Circuit breaker transitioning to CLOSED after successful request")
            self.circuit_breaker_state = CircuitBreakerState.CLOSED
        self.failure_count = 0
        self.last_failure_time = None
    
    def _record_failure(self):
        """Record a failed request."""
        self.failure_count += 1
        self.last_failure_time = datetime.now()
        
        if self.failure_count >= self.circuit_breaker_threshold:
            logger.warning(
                f"Circuit breaker OPEN after {self.failure_count} failures"
            )
            self.circuit_breaker_state = CircuitBreakerState.OPEN
    
    async def _make_request(
        self,
        method: str,
        path: str,
        **kwargs
    ) -> Any:
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
                logger.info(f"Request: {method} {url} (attempt {attempt + 1}/{self.max_retries})")
                
                # Make the request
                response = await self._client.request(
                    method,
                    url,
                    timeout=self.timeout,
                    **kwargs
                )
                
                # Raise for HTTP errors
                response.raise_for_status()
                
                # Log success
                logger.info(f"Response: {method} {url} - {response.status_code}")
                
                # Record success for circuit breaker
                self._record_success()
                
                # Return JSON response
                return response.json()
                
            except (httpx.TimeoutException, httpx.ConnectError) as e:
                # Transient errors - retry with backoff
                last_exception = e
                logger.warning(f"Transient error on attempt {attempt + 1}: {e}")
                
                if attempt < self.max_retries - 1:
                    # Exponential backoff: 1s, 2s, 4s, etc.
                    backoff_time = 2 ** attempt
                    logger.info(f"Retrying in {backoff_time}s...")
                    await asyncio.sleep(backoff_time)
                else:
                    self._record_failure()
                    
            except httpx.HTTPStatusError as e:
                # HTTP errors (4xx, 5xx)
                logger.error(f"HTTP error: {e.response.status_code} - {e}")
                self._record_failure()
                raise
                
            except Exception as e:
                # Unexpected errors
                logger.error(f"Unexpected error: {e}")
                self._record_failure()
                raise
        
        # All retries exhausted
        self._record_failure()
        raise Exception(f"Request failed after {self.max_retries} attempts: {last_exception}")
    
    async def get(self, path: str, **kwargs) -> Any:
        """Make a GET request.
        
        Args:
            path: API path
            **kwargs: Additional arguments
            
        Returns:
            Response JSON data
        """
        return await self._make_request("GET", path, **kwargs)
    
    async def post(self, path: str, **kwargs) -> Any:
        """Make a POST request.
        
        Args:
            path: API path
            **kwargs: Additional arguments (json, data, etc.)
            
        Returns:
            Response JSON data
        """
        return await self._make_request("POST", path, **kwargs)
    
    async def put(self, path: str, **kwargs) -> Any:
        """Make a PUT request.
        
        Args:
            path: API path
            **kwargs: Additional arguments
            
        Returns:
            Response JSON data
        """
        return await self._make_request("PUT", path, **kwargs)
    
    async def patch(self, path: str, **kwargs) -> Any:
        """Make a PATCH request.
        
        Args:
            path: API path
            **kwargs: Additional arguments
            
        Returns:
            Response JSON data
        """
        return await self._make_request("PATCH", path, **kwargs)
    
    async def delete(self, path: str, **kwargs) -> Any:
        """Make a DELETE request.
        
        Args:
            path: API path
            **kwargs: Additional arguments
            
        Returns:
            Response JSON data
        """
        return await self._make_request("DELETE", path, **kwargs)
