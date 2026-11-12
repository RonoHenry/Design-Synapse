"""
Data models for resilience patterns.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class CircuitBreakerState(Enum):
    """Circuit breaker states."""

    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing if service recovered


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker behavior."""

    failure_threshold: int = 5  # Number of failures before opening
    recovery_timeout: int = 60  # Seconds to wait before trying half-open
    success_threshold: int = 3  # Successes needed to close from half-open
    timeout: int = 30  # Request timeout in seconds

    def __post_init__(self):
        """Validate configuration values."""
        if self.failure_threshold <= 0:
            raise ValueError("failure_threshold must be positive")
        if self.recovery_timeout <= 0:
            raise ValueError("recovery_timeout must be positive")
        if self.success_threshold <= 0:
            raise ValueError("success_threshold must be positive")
        if self.timeout <= 0:
            raise ValueError("timeout must be positive")


@dataclass
class RetryConfig:
    """Configuration for retry behavior."""

    max_attempts: int = 3
    base_delay: float = 1.0  # Base delay in seconds
    max_delay: float = 60.0  # Maximum delay in seconds
    exponential_base: float = 2.0  # Exponential backoff multiplier
    jitter: bool = True  # Add randomness to prevent thundering herd
    retryable_status_codes: List[int] = field(default_factory=lambda: [502, 503, 504])
    retryable_exceptions: List[type] = field(
        default_factory=lambda: [ConnectionError, TimeoutError]
    )

    def __post_init__(self):
        """Validate configuration values."""
        if self.max_attempts <= 0:
            raise ValueError("max_attempts must be positive")
        if self.base_delay <= 0:
            raise ValueError("base_delay must be positive")
        if self.max_delay <= 0:
            raise ValueError("max_delay must be positive")
        if self.exponential_base <= 1:
            raise ValueError("exponential_base must be greater than 1")


@dataclass
class CircuitBreakerStatus:
    """Current status of a circuit breaker."""

    state: CircuitBreakerState
    failure_count: int
    success_count: int
    last_failure_time: Optional[datetime]
    next_attempt_time: Optional[datetime]
    total_requests: int
    successful_requests: int
    failed_requests: int

    @property
    def failure_rate(self) -> float:
        """Calculate current failure rate."""
        if self.total_requests == 0:
            return 0.0
        return self.failed_requests / self.total_requests

    @property
    def success_rate(self) -> float:
        """Calculate current success rate."""
        if self.total_requests == 0:
            return 0.0
        return self.successful_requests / self.total_requests


@dataclass
class RetryAttempt:
    """Information about a retry attempt."""

    attempt_number: int
    delay: float
    exception: Optional[Exception]
    timestamp: datetime


@dataclass
class FailureRecord:
    """Record of a service failure."""

    timestamp: datetime
    exception: Exception
    request_context: Dict[str, Any] = field(default_factory=dict)
