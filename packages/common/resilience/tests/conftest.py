"""
Test configuration and fixtures for resilience patterns.
"""

import asyncio
from datetime import datetime
from typing import Any, Dict

import pytest

from ..circuit_breaker import CircuitBreaker, CircuitBreakerRegistry
from ..models import CircuitBreakerConfig, RetryConfig
from ..retry import RetryStrategy


@pytest.fixture
def circuit_breaker_config():
    """Default circuit breaker configuration for testing."""
    return CircuitBreakerConfig(
        failure_threshold=3,
        recovery_timeout=1,  # Short timeout for testing
        success_threshold=2,
        timeout=5,
    )


@pytest.fixture
def retry_config():
    """Default retry configuration for testing."""
    return RetryConfig(
        max_attempts=3,
        base_delay=0.1,  # Short delays for testing
        max_delay=1.0,
        exponential_base=2.0,
        jitter=False,  # Disable jitter for predictable tests
        retryable_status_codes=[502, 503, 504],
        retryable_exceptions=[ConnectionError, TimeoutError, ValueError],
    )


@pytest.fixture
def circuit_breaker(circuit_breaker_config):
    """Circuit breaker instance for testing."""
    return CircuitBreaker("test-service", circuit_breaker_config)


@pytest.fixture
def retry_strategy(retry_config):
    """Retry strategy instance for testing."""
    return RetryStrategy(retry_config)


@pytest.fixture
def fresh_registry():
    """Fresh circuit breaker registry for testing."""
    return CircuitBreakerRegistry()


class MockException(Exception):
    """Mock exception for testing."""

    def __init__(self, message="Mock error", status_code=None):
        super().__init__(message)
        self.status_code = status_code


class MockService:
    """Mock service for testing resilience patterns."""

    def __init__(self):
        self.call_count = 0
        self.fail_count = 0
        self.should_fail = False
        self.failure_exception = MockException("Service unavailable", 503)
        self.response_value = "success"

    def reset(self):
        """Reset service state."""
        self.call_count = 0
        self.fail_count = 0
        self.should_fail = False

    def set_failure_mode(self, should_fail: bool, exception: Exception = None):
        """Set service to fail or succeed."""
        self.should_fail = should_fail
        if exception:
            self.failure_exception = exception

    def call(self, *args, **kwargs) -> str:
        """Synchronous service call."""
        self.call_count += 1

        if self.should_fail:
            self.fail_count += 1
            raise self.failure_exception

        return self.response_value

    async def async_call(self, *args, **kwargs) -> str:
        """Asynchronous service call."""
        self.call_count += 1

        if self.should_fail:
            self.fail_count += 1
            raise self.failure_exception

        return self.response_value


@pytest.fixture
def mock_service():
    """Mock service instance for testing."""
    return MockService()


class FlakeyService:
    """Service that fails intermittently for testing retry logic."""

    def __init__(self, fail_attempts: int = 2):
        self.call_count = 0
        self.fail_attempts = fail_attempts
        self.response_value = "success"

    def call(self) -> str:
        """Call that fails for the first N attempts."""
        self.call_count += 1

        if self.call_count <= self.fail_attempts:
            raise MockException(f"Attempt {self.call_count} failed", 503)

        return self.response_value

    async def async_call(self) -> str:
        """Async call that fails for the first N attempts."""
        self.call_count += 1

        if self.call_count <= self.fail_attempts:
            raise MockException(f"Attempt {self.call_count} failed", 503)

        return self.response_value


@pytest.fixture
def flakey_service():
    """Flakey service instance for testing."""
    return FlakeyService()


@pytest.fixture
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()
