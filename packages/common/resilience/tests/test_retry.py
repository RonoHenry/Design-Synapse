"""
Tests for retry mechanism with exponential backoff.
"""

import asyncio
import time
from unittest.mock import patch

import pytest

from ..models import RetryConfig
from ..retry import (RetryStrategy, exponential_backoff_with_jitter,
                     retry_async_call, retry_sync_call, retry_with_backoff)
from .conftest import FlakeyService, MockException


class TestExponentialBackoff:
    """Test exponential backoff calculation."""

    def test_basic_backoff(self):
        """Test basic exponential backoff without jitter."""
        delay = exponential_backoff_with_jitter(
            attempt=0, base_delay=1.0, max_delay=60.0, jitter=False
        )
        assert delay == 1.0

        delay = exponential_backoff_with_jitter(
            attempt=1, base_delay=1.0, max_delay=60.0, jitter=False
        )
        assert delay == 2.0

        delay = exponential_backoff_with_jitter(
            attempt=2, base_delay=1.0, max_delay=60.0, jitter=False
        )
        assert delay == 4.0

    def test_max_delay_cap(self):
        """Test delay is capped at max_delay."""
        delay = exponential_backoff_with_jitter(
            attempt=10, base_delay=1.0, max_delay=5.0, jitter=False
        )
        assert delay == 5.0

    def test_custom_exponential_base(self):
        """Test custom exponential base."""
        delay = exponential_backoff_with_jitter(
            attempt=2,
            base_delay=1.0,
            max_delay=60.0,
            exponential_base=3.0,
            jitter=False,
        )
        assert delay == 9.0  # 1.0 * 3^2

    def test_jitter_adds_randomness(self):
        """Test jitter adds randomness to delay."""
        delays = []
        for _ in range(10):
            delay = exponential_backoff_with_jitter(
                attempt=1, base_delay=2.0, max_delay=60.0, jitter=True
            )
            delays.append(delay)

        # With jitter, delays should vary
        assert len(set(delays)) > 1

        # All delays should be positive and around the expected value
        for delay in delays:
            assert delay >= 0
            assert (
                delay <= 3.0
            )  # Base 2.0 + 25% jitter = max 2.5, but allow some margin

    def test_jitter_non_negative(self):
        """Test jitter never produces negative delays."""
        for _ in range(100):
            delay = exponential_backoff_with_jitter(
                attempt=0, base_delay=0.1, max_delay=60.0, jitter=True
            )
            assert delay >= 0


class TestRetryConfig:
    """Test retry configuration validation."""

    def test_valid_config(self):
        """Test valid configuration creation."""
        config = RetryConfig(
            max_attempts=5,
            base_delay=2.0,
            max_delay=120.0,
            exponential_base=3.0,
            jitter=True,
        )
        assert config.max_attempts == 5
        assert config.base_delay == 2.0
        assert config.max_delay == 120.0
        assert config.exponential_base == 3.0
        assert config.jitter is True

    def test_invalid_max_attempts(self):
        """Test invalid max_attempts raises error."""
        with pytest.raises(ValueError, match="max_attempts must be positive"):
            RetryConfig(max_attempts=0)

    def test_invalid_base_delay(self):
        """Test invalid base_delay raises error."""
        with pytest.raises(ValueError, match="base_delay must be positive"):
            RetryConfig(base_delay=-1.0)

    def test_invalid_max_delay(self):
        """Test invalid max_delay raises error."""
        with pytest.raises(ValueError, match="max_delay must be positive"):
            RetryConfig(max_delay=0)

    def test_invalid_exponential_base(self):
        """Test invalid exponential_base raises error."""
        with pytest.raises(ValueError, match="exponential_base must be greater than 1"):
            RetryConfig(exponential_base=1.0)


class TestRetryStrategy:
    """Test retry strategy functionality."""

    def test_should_retry_exception_type(self, retry_config):
        """Test should_retry with retryable exception types."""
        strategy = RetryStrategy(retry_config)

        # Should retry ConnectionError
        assert strategy.should_retry(ConnectionError("Connection failed"), 0)

        # Should retry TimeoutError
        assert strategy.should_retry(TimeoutError("Request timeout"), 1)

        # Should retry ValueError (in test config)
        assert strategy.should_retry(ValueError("Invalid value"), 0)

        # Should not retry RuntimeError (not in config)
        assert not strategy.should_retry(RuntimeError("Runtime error"), 0)

    def test_should_retry_status_code(self, retry_config):
        """Test should_retry with HTTP status codes."""
        strategy = RetryStrategy(retry_config)

        # Should retry 503
        exception = MockException("Service unavailable", 503)
        assert strategy.should_retry(exception, 0)

        # Should retry 502
        exception = MockException("Bad gateway", 502)
        assert strategy.should_retry(exception, 1)

        # Should not retry 404
        exception = MockException("Not found", 404)
        assert not strategy.should_retry(exception, 0)

    def test_should_not_retry_max_attempts(self, retry_config):
        """Test should not retry when max attempts reached."""
        strategy = RetryStrategy(retry_config)

        # Should not retry when attempt >= max_attempts
        assert not strategy.should_retry(ConnectionError("Failed"), 3)
        assert not strategy.should_retry(ConnectionError("Failed"), 5)

    def test_get_delay(self, retry_config):
        """Test delay calculation."""
        strategy = RetryStrategy(retry_config)

        delay0 = strategy.get_delay(0)
        delay1 = strategy.get_delay(1)
        delay2 = strategy.get_delay(2)

        # Delays should increase (no jitter in test config)
        assert delay0 == 0.1  # base_delay
        assert delay1 == 0.2  # base_delay * 2^1
        assert delay2 == 0.4  # base_delay * 2^2

    def test_record_attempt(self, retry_config):
        """Test recording retry attempts."""
        strategy = RetryStrategy(retry_config)

        exception = MockException("Test error")
        strategy.record_attempt(1, 0.5, exception)

        assert len(strategy.attempts) == 1
        attempt = strategy.attempts[0]
        assert attempt.attempt_number == 1
        assert attempt.delay == 0.5
        assert attempt.exception == exception

    def test_reset(self, retry_config):
        """Test resetting strategy state."""
        strategy = RetryStrategy(retry_config)

        strategy.record_attempt(1, 0.5)
        assert len(strategy.attempts) == 1

        strategy.reset()
        assert len(strategy.attempts) == 0


class TestRetryDecorator:
    """Test retry decorator functionality."""

    def test_sync_retry_success_after_failures(self, flakey_service):
        """Test sync retry succeeds after initial failures."""
        config = RetryConfig(max_attempts=5, base_delay=0.01, jitter=False)

        @retry_with_backoff(config)
        def test_function():
            return flakey_service.call()

        # Service fails first 2 attempts, succeeds on 3rd
        result = test_function()
        assert result == "success"
        assert flakey_service.call_count == 3

    def test_sync_retry_exhausts_attempts(self):
        """Test sync retry exhausts all attempts."""
        config = RetryConfig(max_attempts=3, base_delay=0.01, jitter=False)

        call_count = 0

        @retry_with_backoff(config)
        def always_fails():
            nonlocal call_count
            call_count += 1
            raise ConnectionError("Always fails")

        with pytest.raises(ConnectionError):
            always_fails()

        assert call_count == 3

    def test_sync_retry_non_retryable_exception(self):
        """Test sync retry doesn't retry non-retryable exceptions."""
        config = RetryConfig(max_attempts=3, base_delay=0.01)

        call_count = 0

        @retry_with_backoff(config)
        def non_retryable_failure():
            nonlocal call_count
            call_count += 1
            raise RuntimeError("Non-retryable error")

        with pytest.raises(RuntimeError):
            non_retryable_failure()

        # Should only be called once (no retries)
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_async_retry_success_after_failures(self, flakey_service):
        """Test async retry succeeds after initial failures."""
        config = RetryConfig(max_attempts=5, base_delay=0.01, jitter=False)

        @retry_with_backoff(config)
        async def test_async_function():
            return await flakey_service.async_call()

        result = await test_async_function()
        assert result == "success"
        assert flakey_service.call_count == 3

    @pytest.mark.asyncio
    async def test_async_retry_exhausts_attempts(self):
        """Test async retry exhausts all attempts."""
        config = RetryConfig(max_attempts=3, base_delay=0.01, jitter=False)

        call_count = 0

        @retry_with_backoff(config)
        async def always_fails():
            nonlocal call_count
            call_count += 1
            raise TimeoutError("Always fails")

        with pytest.raises(TimeoutError):
            await always_fails()

        assert call_count == 3


class TestRetryFunctions:
    """Test retry utility functions."""

    @pytest.mark.asyncio
    async def test_retry_async_call_success(self, flakey_service):
        """Test retry_async_call with eventual success."""
        config = RetryConfig(max_attempts=5, base_delay=0.01, jitter=False)

        result = await retry_async_call(flakey_service.async_call, config=config)
        assert result == "success"
        assert flakey_service.call_count == 3

    @pytest.mark.asyncio
    async def test_retry_async_call_failure(self):
        """Test retry_async_call with all attempts failing."""
        config = RetryConfig(max_attempts=2, base_delay=0.01, jitter=False)

        call_count = 0

        async def always_fails():
            nonlocal call_count
            call_count += 1
            raise ConnectionError("Always fails")

        with pytest.raises(ConnectionError):
            await retry_async_call(always_fails, config=config)

        assert call_count == 2

    def test_retry_sync_call_success(self, flakey_service):
        """Test retry_sync_call with eventual success."""
        config = RetryConfig(max_attempts=5, base_delay=0.01, jitter=False)

        result = retry_sync_call(flakey_service.call, config=config)
        assert result == "success"
        assert flakey_service.call_count == 3

    def test_retry_sync_call_failure(self):
        """Test retry_sync_call with all attempts failing."""
        config = RetryConfig(max_attempts=2, base_delay=0.01, jitter=False)

        call_count = 0

        def always_fails():
            nonlocal call_count
            call_count += 1
            raise ValueError("Always fails")

        with pytest.raises(ValueError):
            retry_sync_call(always_fails, config=config)

        assert call_count == 2

    def test_retry_sync_call_default_config(self):
        """Test retry_sync_call with default configuration."""
        call_count = 0

        def fails_twice():
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                raise ConnectionError("Failing")
            return "success"

        result = retry_sync_call(fails_twice)
        assert result == "success"
        assert call_count == 3


class TestRetryTiming:
    """Test retry timing and delays."""

    def test_retry_delays_increase(self):
        """Test that retry delays increase exponentially."""
        config = RetryConfig(max_attempts=4, base_delay=0.1, jitter=False)

        call_times = []

        @retry_with_backoff(config)
        def failing_function():
            call_times.append(time.time())
            raise ConnectionError("Always fails")

        start_time = time.time()

        with pytest.raises(ConnectionError):
            failing_function()

        # Should have 4 call times (initial + 3 retries)
        assert len(call_times) == 4

        # Calculate delays between calls
        delays = []
        for i in range(1, len(call_times)):
            delay = call_times[i] - call_times[i - 1]
            delays.append(delay)

        # Delays should increase (approximately)
        assert delays[0] < delays[1] < delays[2]

        # First delay should be around base_delay (0.1s)
        assert 0.08 <= delays[0] <= 0.15

        # Second delay should be around 2 * base_delay (0.2s)
        assert 0.18 <= delays[1] <= 0.25
