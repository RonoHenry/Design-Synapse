"""
Retry mechanism with exponential backoff and jitter.
"""

import asyncio
import logging
import random
import time
from datetime import datetime
from functools import wraps
from typing import Any, Callable, List, Optional, TypeVar, Union

from .models import RetryAttempt, RetryConfig

logger = logging.getLogger(__name__)

T = TypeVar("T")


def exponential_backoff_with_jitter(
    attempt: int,
    base_delay: float,
    max_delay: float,
    exponential_base: float = 2.0,
    jitter: bool = True,
) -> float:
    """
    Calculate delay for exponential backoff with optional jitter.

    Args:
        attempt: Current attempt number (0-based)
        base_delay: Base delay in seconds
        max_delay: Maximum delay in seconds
        exponential_base: Exponential multiplier
        jitter: Whether to add random jitter

    Returns:
        Delay in seconds
    """
    delay = base_delay * (exponential_base**attempt)
    delay = min(delay, max_delay)

    if jitter:
        # Add up to 25% jitter to prevent thundering herd
        jitter_amount = delay * 0.25
        delay += random.uniform(-jitter_amount, jitter_amount)
        delay = max(0, delay)  # Ensure non-negative

    return delay


class RetryStrategy:
    """Handles retry logic with configurable strategies."""

    def __init__(self, config: RetryConfig):
        self.config = config
        self.attempts: List[RetryAttempt] = []

    def should_retry(self, exception: Exception, attempt: int) -> bool:
        """
        Determine if an exception should trigger a retry.

        Args:
            exception: The exception that occurred
            attempt: Current attempt number (0-based)

        Returns:
            True if should retry, False otherwise
        """
        if attempt >= self.config.max_attempts:
            return False

        # Check if exception type is retryable
        for exc_type in self.config.retryable_exceptions:
            if isinstance(exception, exc_type):
                return True

        # Check if HTTP status code is retryable
        if hasattr(exception, "status_code"):
            return exception.status_code in self.config.retryable_status_codes

        return False

    def get_delay(self, attempt: int) -> float:
        """Get delay for the given attempt number."""
        return exponential_backoff_with_jitter(
            attempt=attempt,
            base_delay=self.config.base_delay,
            max_delay=self.config.max_delay,
            exponential_base=self.config.exponential_base,
            jitter=self.config.jitter,
        )

    def record_attempt(
        self, attempt: int, delay: float, exception: Optional[Exception] = None
    ):
        """Record a retry attempt for monitoring."""
        self.attempts.append(
            RetryAttempt(
                attempt_number=attempt,
                delay=delay,
                exception=exception,
                timestamp=datetime.utcnow(),
            )
        )

    def reset(self):
        """Reset attempt history."""
        self.attempts.clear()


def retry_with_backoff(config: RetryConfig):
    """
    Decorator for adding retry logic with exponential backoff to functions.

    Args:
        config: Retry configuration

    Returns:
        Decorated function with retry logic
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def sync_wrapper(*args, **kwargs) -> T:
            strategy = RetryStrategy(config)
            last_exception = None

            for attempt in range(config.max_attempts):
                try:
                    result = func(*args, **kwargs)
                    if attempt > 0:
                        logger.info(
                            f"Function {func.__name__} succeeded on attempt {attempt + 1}"
                        )
                    return result

                except Exception as e:
                    last_exception = e

                    if not strategy.should_retry(e, attempt):
                        logger.error(
                            f"Function {func.__name__} failed on attempt {attempt + 1}, "
                            f"not retrying: {e}"
                        )
                        raise e

                    if (
                        attempt < config.max_attempts - 1
                    ):  # Don't delay after last attempt
                        delay = strategy.get_delay(attempt)
                        strategy.record_attempt(attempt, delay, e)

                        logger.warning(
                            f"Function {func.__name__} failed on attempt {attempt + 1}, "
                            f"retrying in {delay:.2f}s: {e}"
                        )
                        time.sleep(delay)

            # All attempts failed
            logger.error(
                f"Function {func.__name__} failed after {config.max_attempts} attempts"
            )
            raise last_exception

        @wraps(func)
        async def async_wrapper(*args, **kwargs) -> T:
            strategy = RetryStrategy(config)
            last_exception = None

            for attempt in range(config.max_attempts):
                try:
                    result = await func(*args, **kwargs)
                    if attempt > 0:
                        logger.info(
                            f"Function {func.__name__} succeeded on attempt {attempt + 1}"
                        )
                    return result

                except Exception as e:
                    last_exception = e

                    if not strategy.should_retry(e, attempt):
                        logger.error(
                            f"Function {func.__name__} failed on attempt {attempt + 1}, "
                            f"not retrying: {e}"
                        )
                        raise e

                    if (
                        attempt < config.max_attempts - 1
                    ):  # Don't delay after last attempt
                        delay = strategy.get_delay(attempt)
                        strategy.record_attempt(attempt, delay, e)

                        logger.warning(
                            f"Function {func.__name__} failed on attempt {attempt + 1}, "
                            f"retrying in {delay:.2f}s: {e}"
                        )
                        await asyncio.sleep(delay)

            # All attempts failed
            logger.error(
                f"Function {func.__name__} failed after {config.max_attempts} attempts"
            )
            raise last_exception

        # Return appropriate wrapper based on function type
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


async def retry_async_call(
    func: Callable[..., T], *args, config: Optional[RetryConfig] = None, **kwargs
) -> T:
    """
    Retry an async function call with exponential backoff.

    Args:
        func: Async function to call
        *args: Function arguments
        config: Retry configuration (uses default if None)
        **kwargs: Function keyword arguments

    Returns:
        Function result

    Raises:
        Last exception if all retries fail
    """
    if config is None:
        config = RetryConfig()

    strategy = RetryStrategy(config)
    last_exception = None

    for attempt in range(config.max_attempts):
        try:
            return await func(*args, **kwargs)

        except Exception as e:
            last_exception = e

            if not strategy.should_retry(e, attempt):
                raise e

            if attempt < config.max_attempts - 1:
                delay = strategy.get_delay(attempt)
                strategy.record_attempt(attempt, delay, e)

                logger.warning(
                    f"Async call failed on attempt {attempt + 1}, "
                    f"retrying in {delay:.2f}s: {e}"
                )
                await asyncio.sleep(delay)

    raise last_exception


def retry_sync_call(
    func: Callable[..., T], *args, config: Optional[RetryConfig] = None, **kwargs
) -> T:
    """
    Retry a sync function call with exponential backoff.

    Args:
        func: Function to call
        *args: Function arguments
        config: Retry configuration (uses default if None)
        **kwargs: Function keyword arguments

    Returns:
        Function result

    Raises:
        Last exception if all retries fail
    """
    if config is None:
        config = RetryConfig()

    strategy = RetryStrategy(config)
    last_exception = None

    for attempt in range(config.max_attempts):
        try:
            return func(*args, **kwargs)

        except Exception as e:
            last_exception = e

            if not strategy.should_retry(e, attempt):
                raise e

            if attempt < config.max_attempts - 1:
                delay = strategy.get_delay(attempt)
                strategy.record_attempt(attempt, delay, e)

                logger.warning(
                    f"Sync call failed on attempt {attempt + 1}, "
                    f"retrying in {delay:.2f}s: {e}"
                )
                time.sleep(delay)

    raise last_exception
