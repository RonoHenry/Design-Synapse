"""
Circuit breaker pattern implementation for service resilience.
"""

import asyncio
import logging
import threading
import time
from datetime import datetime, timedelta
from functools import wraps
from typing import Any, Callable, Dict, Optional, TypeVar

from .models import (CircuitBreakerConfig, CircuitBreakerState,
                     CircuitBreakerStatus, FailureRecord)

logger = logging.getLogger(__name__)

T = TypeVar("T")


class CircuitBreakerOpenException(Exception):
    """Exception raised when circuit breaker is open."""

    def __init__(self, service_name: str, next_attempt_time: Optional[datetime] = None):
        self.service_name = service_name
        self.next_attempt_time = next_attempt_time
        message = f"Circuit breaker is open for service '{service_name}'"
        if next_attempt_time:
            message += f", next attempt at {next_attempt_time}"
        super().__init__(message)


class CircuitBreaker:
    """
    Circuit breaker implementation with configurable failure thresholds
    and automatic recovery testing.
    """

    def __init__(self, name: str, config: CircuitBreakerConfig):
        self.name = name
        self.config = config
        self._state = CircuitBreakerState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time: Optional[datetime] = None
        self._next_attempt_time: Optional[datetime] = None
        self._total_requests = 0
        self._successful_requests = 0
        self._failed_requests = 0
        self._lock = threading.RLock()
        self._failure_records: list[FailureRecord] = []

        logger.info(f"Circuit breaker '{name}' initialized with config: {config}")

    @property
    def state(self) -> CircuitBreakerState:
        """Get current circuit breaker state."""
        with self._lock:
            return self._state

    @property
    def status(self) -> CircuitBreakerStatus:
        """Get detailed status information."""
        with self._lock:
            return CircuitBreakerStatus(
                state=self._state,
                failure_count=self._failure_count,
                success_count=self._success_count,
                last_failure_time=self._last_failure_time,
                next_attempt_time=self._next_attempt_time,
                total_requests=self._total_requests,
                successful_requests=self._successful_requests,
                failed_requests=self._failed_requests,
            )

    def _should_attempt_reset(self) -> bool:
        """Check if circuit breaker should attempt to reset from OPEN to HALF_OPEN."""
        if self._state != CircuitBreakerState.OPEN:
            return False

        if self._next_attempt_time is None:
            return True

        return datetime.utcnow() >= self._next_attempt_time

    def _record_success(self):
        """Record a successful request."""
        with self._lock:
            self._total_requests += 1
            self._successful_requests += 1

            if self._state == CircuitBreakerState.HALF_OPEN:
                self._success_count += 1
                logger.debug(
                    f"Circuit breaker '{self.name}' recorded success in HALF_OPEN state "
                    f"({self._success_count}/{self.config.success_threshold})"
                )

                if self._success_count >= self.config.success_threshold:
                    self._state = CircuitBreakerState.CLOSED
                    self._failure_count = 0
                    self._success_count = 0
                    self._last_failure_time = None
                    self._next_attempt_time = None
                    logger.info(f"Circuit breaker '{self.name}' transitioned to CLOSED")

            elif self._state == CircuitBreakerState.CLOSED:
                # Reset failure count on success in CLOSED state
                if self._failure_count > 0:
                    self._failure_count = 0
                    logger.debug(f"Circuit breaker '{self.name}' reset failure count")

    def _record_failure(
        self, exception: Exception, context: Optional[Dict[str, Any]] = None
    ):
        """Record a failed request."""
        with self._lock:
            self._total_requests += 1
            self._failed_requests += 1
            self._failure_count += 1
            self._last_failure_time = datetime.utcnow()

            # Store failure record for analysis
            failure_record = FailureRecord(
                timestamp=self._last_failure_time,
                exception=exception,
                request_context=context or {},
            )
            self._failure_records.append(failure_record)

            # Keep only recent failure records (last 100)
            if len(self._failure_records) > 100:
                self._failure_records = self._failure_records[-100:]

            logger.warning(
                f"Circuit breaker '{self.name}' recorded failure "
                f"({self._failure_count}/{self.config.failure_threshold}): {exception}"
            )

            if self._state == CircuitBreakerState.CLOSED:
                if self._failure_count >= self.config.failure_threshold:
                    self._state = CircuitBreakerState.OPEN
                    self._success_count = 0
                    self._next_attempt_time = datetime.utcnow() + timedelta(
                        seconds=self.config.recovery_timeout
                    )
                    logger.error(
                        f"Circuit breaker '{self.name}' transitioned to OPEN, "
                        f"next attempt at {self._next_attempt_time}"
                    )

            elif self._state == CircuitBreakerState.HALF_OPEN:
                self._state = CircuitBreakerState.OPEN
                self._success_count = 0
                self._next_attempt_time = datetime.utcnow() + timedelta(
                    seconds=self.config.recovery_timeout
                )
                logger.warning(
                    f"Circuit breaker '{self.name}' failed in HALF_OPEN, "
                    f"back to OPEN until {self._next_attempt_time}"
                )

    def _check_state_transition(self):
        """Check and perform state transitions."""
        with self._lock:
            if self._state == CircuitBreakerState.OPEN and self._should_attempt_reset():
                self._state = CircuitBreakerState.HALF_OPEN
                self._success_count = 0
                logger.info(f"Circuit breaker '{self.name}' transitioned to HALF_OPEN")

    def call(self, func: Callable[..., T], *args, **kwargs) -> T:
        """
        Execute a function through the circuit breaker.

        Args:
            func: Function to execute
            *args: Function arguments
            **kwargs: Function keyword arguments

        Returns:
            Function result

        Raises:
            CircuitBreakerOpenException: If circuit breaker is open
            Exception: Any exception raised by the function
        """
        self._check_state_transition()

        if self._state == CircuitBreakerState.OPEN:
            raise CircuitBreakerOpenException(self.name, self._next_attempt_time)

        try:
            result = func(*args, **kwargs)
            self._record_success()
            return result

        except Exception as e:
            self._record_failure(e, {"args": str(args), "kwargs": str(kwargs)})
            raise

    async def call_async(self, func: Callable[..., T], *args, **kwargs) -> T:
        """
        Execute an async function through the circuit breaker.

        Args:
            func: Async function to execute
            *args: Function arguments
            **kwargs: Function keyword arguments

        Returns:
            Function result

        Raises:
            CircuitBreakerOpenException: If circuit breaker is open
            Exception: Any exception raised by the function
        """
        self._check_state_transition()

        if self._state == CircuitBreakerState.OPEN:
            raise CircuitBreakerOpenException(self.name, self._next_attempt_time)

        try:
            result = await func(*args, **kwargs)
            self._record_success()
            return result

        except Exception as e:
            self._record_failure(e, {"args": str(args), "kwargs": str(kwargs)})
            raise

    def reset(self):
        """Manually reset the circuit breaker to CLOSED state."""
        with self._lock:
            self._state = CircuitBreakerState.CLOSED
            self._failure_count = 0
            self._success_count = 0
            self._last_failure_time = None
            self._next_attempt_time = None
            logger.info(f"Circuit breaker '{self.name}' manually reset to CLOSED")

    def get_failure_records(self, limit: int = 10) -> list[FailureRecord]:
        """Get recent failure records for analysis."""
        with self._lock:
            return self._failure_records[-limit:] if self._failure_records else []


class CircuitBreakerRegistry:
    """Registry for managing multiple circuit breakers."""

    def __init__(self):
        self._breakers: Dict[str, CircuitBreaker] = {}
        self._lock = threading.RLock()

    def get_or_create(self, name: str, config: CircuitBreakerConfig) -> CircuitBreaker:
        """Get existing circuit breaker or create a new one."""
        with self._lock:
            if name not in self._breakers:
                self._breakers[name] = CircuitBreaker(name, config)
            return self._breakers[name]

    def get(self, name: str) -> Optional[CircuitBreaker]:
        """Get circuit breaker by name."""
        with self._lock:
            return self._breakers.get(name)

    def get_all_status(self) -> Dict[str, CircuitBreakerStatus]:
        """Get status of all circuit breakers."""
        with self._lock:
            return {name: breaker.status for name, breaker in self._breakers.items()}

    def reset_all(self):
        """Reset all circuit breakers."""
        with self._lock:
            for breaker in self._breakers.values():
                breaker.reset()
            logger.info("All circuit breakers reset")


# Global registry instance
_registry = CircuitBreakerRegistry()


def circuit_breaker(name: str, config: Optional[CircuitBreakerConfig] = None):
    """
    Decorator for adding circuit breaker protection to functions.

    Args:
        name: Circuit breaker name
        config: Circuit breaker configuration (uses default if None)

    Returns:
        Decorated function with circuit breaker protection
    """
    if config is None:
        config = CircuitBreakerConfig()

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        breaker = _registry.get_or_create(name, config)

        @wraps(func)
        def sync_wrapper(*args, **kwargs) -> T:
            return breaker.call(func, *args, **kwargs)

        @wraps(func)
        async def async_wrapper(*args, **kwargs) -> T:
            return await breaker.call_async(func, *args, **kwargs)

        # Return appropriate wrapper based on function type
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


def get_circuit_breaker(name: str) -> Optional[CircuitBreaker]:
    """Get circuit breaker by name from global registry."""
    return _registry.get(name)


def get_all_circuit_breaker_status() -> Dict[str, CircuitBreakerStatus]:
    """Get status of all circuit breakers from global registry."""
    return _registry.get_all_status()


def reset_all_circuit_breakers():
    """Reset all circuit breakers in global registry."""
    _registry.reset_all()
