"""
Resilience patterns for service reliability.

This package provides circuit breaker and retry mechanisms to handle
service failures gracefully and prevent cascading failures.
"""

from .circuit_breaker import (CircuitBreaker, CircuitBreakerConfig,
                              CircuitBreakerState)
from .models import CircuitBreakerStatus, FailureRecord, RetryAttempt
from .retry import RetryConfig, RetryStrategy, exponential_backoff_with_jitter

__all__ = [
    "CircuitBreaker",
    "CircuitBreakerState",
    "CircuitBreakerConfig",
    "RetryConfig",
    "RetryStrategy",
    "exponential_backoff_with_jitter",
    "CircuitBreakerStatus",
    "RetryAttempt",
    "FailureRecord",
]
