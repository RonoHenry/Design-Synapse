"""
Tests for circuit breaker pattern implementation.
"""

import asyncio
import time
from datetime import datetime, timedelta

import pytest

from ..circuit_breaker import (CircuitBreaker, CircuitBreakerOpenException,
                               CircuitBreakerRegistry, circuit_breaker,
                               get_all_circuit_breaker_status,
                               get_circuit_breaker, reset_all_circuit_breakers)
from ..models import CircuitBreakerConfig, CircuitBreakerState
from .conftest import MockException, MockService


class TestCircuitBreakerConfig:
    """Test circuit breaker configuration validation."""

    def test_valid_config(self):
        """Test valid configuration creation."""
        config = CircuitBreakerConfig(
            failure_threshold=5, recovery_timeout=60, success_threshold=3, timeout=30
        )
        assert config.failure_threshold == 5
        assert config.recovery_timeout == 60
        assert config.success_threshold == 3
        assert config.timeout == 30

    def test_invalid_failure_threshold(self):
        """Test invalid failure threshold raises error."""
        with pytest.raises(ValueError, match="failure_threshold must be positive"):
            CircuitBreakerConfig(failure_threshold=0)

    def test_invalid_recovery_timeout(self):
        """Test invalid recovery timeout raises error."""
        with pytest.raises(ValueError, match="recovery_timeout must be positive"):
            CircuitBreakerConfig(recovery_timeout=-1)

    def test_invalid_success_threshold(self):
        """Test invalid success threshold raises error."""
        with pytest.raises(ValueError, match="success_threshold must be positive"):
            CircuitBreakerConfig(success_threshold=0)

    def test_invalid_timeout(self):
        """Test invalid timeout raises error."""
        with pytest.raises(ValueError, match="timeout must be positive"):
            CircuitBreakerConfig(timeout=-5)


class TestCircuitBreaker:
    """Test circuit breaker functionality."""

    def test_initial_state(self, circuit_breaker):
        """Test circuit breaker starts in CLOSED state."""
        assert circuit_breaker.state == CircuitBreakerState.CLOSED
        status = circuit_breaker.status
        assert status.failure_count == 0
        assert status.success_count == 0
        assert status.total_requests == 0

    def test_successful_call(self, circuit_breaker, mock_service):
        """Test successful call through circuit breaker."""
        result = circuit_breaker.call(mock_service.call)

        assert result == "success"
        assert mock_service.call_count == 1
        assert circuit_breaker.state == CircuitBreakerState.CLOSED

        status = circuit_breaker.status
        assert status.successful_requests == 1
        assert status.total_requests == 1
        assert status.failure_count == 0

    def test_failed_call(self, circuit_breaker, mock_service):
        """Test failed call through circuit breaker."""
        mock_service.set_failure_mode(True)

        with pytest.raises(MockException):
            circuit_breaker.call(mock_service.call)

        assert mock_service.call_count == 1
        assert circuit_breaker.state == CircuitBreakerState.CLOSED

        status = circuit_breaker.status
        assert status.failed_requests == 1
        assert status.total_requests == 1
        assert status.failure_count == 1

    def test_circuit_opens_after_threshold(self, circuit_breaker, mock_service):
        """Test circuit breaker opens after failure threshold."""
        mock_service.set_failure_mode(True)

        # Fail up to threshold (3 failures)
        for i in range(3):
            with pytest.raises(MockException):
                circuit_breaker.call(mock_service.call)

            if i < 2:  # Still closed for first 2 failures
                assert circuit_breaker.state == CircuitBreakerState.CLOSED

        # Should be open after 3rd failure
        assert circuit_breaker.state == CircuitBreakerState.OPEN

        # Next call should raise CircuitBreakerOpenException
        with pytest.raises(CircuitBreakerOpenException):
            circuit_breaker.call(mock_service.call)

        # Service should not be called when circuit is open
        assert mock_service.call_count == 3

    def test_circuit_transitions_to_half_open(self, circuit_breaker, mock_service):
        """Test circuit breaker transitions to half-open after timeout."""
        mock_service.set_failure_mode(True)

        # Open the circuit
        for _ in range(3):
            with pytest.raises(MockException):
                circuit_breaker.call(mock_service.call)

        assert circuit_breaker.state == CircuitBreakerState.OPEN

        # Wait for recovery timeout (1 second in test config)
        time.sleep(1.1)

        # Next call should transition to half-open
        mock_service.set_failure_mode(False)  # Service is now working
        result = circuit_breaker.call(mock_service.call)

        assert result == "success"
        assert circuit_breaker.state == CircuitBreakerState.HALF_OPEN

    def test_circuit_closes_from_half_open(self, circuit_breaker, mock_service):
        """Test circuit breaker closes from half-open after success threshold."""
        # Open the circuit
        mock_service.set_failure_mode(True)
        for _ in range(3):
            with pytest.raises(MockException):
                circuit_breaker.call(mock_service.call)

        # Wait and transition to half-open
        time.sleep(1.1)
        mock_service.set_failure_mode(False)

        # Make successful calls to close circuit (need 2 successes)
        for i in range(2):
            result = circuit_breaker.call(mock_service.call)
            assert result == "success"

            if i == 0:  # Still half-open after first success
                assert circuit_breaker.state == CircuitBreakerState.HALF_OPEN

        # Should be closed after 2nd success
        assert circuit_breaker.state == CircuitBreakerState.CLOSED

    def test_circuit_reopens_from_half_open_on_failure(
        self, circuit_breaker, mock_service
    ):
        """Test circuit breaker reopens from half-open on failure."""
        # Open the circuit
        mock_service.set_failure_mode(True)
        for _ in range(3):
            with pytest.raises(MockException):
                circuit_breaker.call(mock_service.call)

        # Wait and transition to half-open
        time.sleep(1.1)

        # Fail in half-open state
        with pytest.raises(MockException):
            circuit_breaker.call(mock_service.call)

        # Should be open again
        assert circuit_breaker.state == CircuitBreakerState.OPEN

    def test_manual_reset(self, circuit_breaker, mock_service):
        """Test manual circuit breaker reset."""
        # Open the circuit
        mock_service.set_failure_mode(True)
        for _ in range(3):
            with pytest.raises(MockException):
                circuit_breaker.call(mock_service.call)

        assert circuit_breaker.state == CircuitBreakerState.OPEN

        # Manual reset
        circuit_breaker.reset()
        assert circuit_breaker.state == CircuitBreakerState.CLOSED

        status = circuit_breaker.status
        assert status.failure_count == 0
        assert status.success_count == 0

    def test_failure_records(self, circuit_breaker, mock_service):
        """Test failure record collection."""
        mock_service.set_failure_mode(True, MockException("Test error"))

        with pytest.raises(MockException):
            circuit_breaker.call(mock_service.call)

        records = circuit_breaker.get_failure_records()
        assert len(records) == 1
        assert str(records[0].exception) == "Test error"
        assert records[0].timestamp is not None


class TestAsyncCircuitBreaker:
    """Test async circuit breaker functionality."""

    @pytest.mark.asyncio
    async def test_async_successful_call(self, circuit_breaker, mock_service):
        """Test successful async call through circuit breaker."""
        result = await circuit_breaker.call_async(mock_service.async_call)

        assert result == "success"
        assert mock_service.call_count == 1
        assert circuit_breaker.state == CircuitBreakerState.CLOSED

    @pytest.mark.asyncio
    async def test_async_failed_call(self, circuit_breaker, mock_service):
        """Test failed async call through circuit breaker."""
        mock_service.set_failure_mode(True)

        with pytest.raises(MockException):
            await circuit_breaker.call_async(mock_service.async_call)

        assert mock_service.call_count == 1
        status = circuit_breaker.status
        assert status.failed_requests == 1

    @pytest.mark.asyncio
    async def test_async_circuit_opens(self, circuit_breaker, mock_service):
        """Test async circuit breaker opens after failures."""
        mock_service.set_failure_mode(True)

        # Fail 3 times to open circuit
        for _ in range(3):
            with pytest.raises(MockException):
                await circuit_breaker.call_async(mock_service.async_call)

        assert circuit_breaker.state == CircuitBreakerState.OPEN

        # Next call should raise CircuitBreakerOpenException
        with pytest.raises(CircuitBreakerOpenException):
            await circuit_breaker.call_async(mock_service.async_call)


class TestCircuitBreakerDecorator:
    """Test circuit breaker decorator functionality."""

    def test_sync_decorator(self, mock_service):
        """Test circuit breaker decorator on sync function."""
        config = CircuitBreakerConfig(failure_threshold=2, recovery_timeout=1)

        @circuit_breaker("test-sync", config)
        def test_function():
            return mock_service.call()

        # Successful call
        mock_service.set_failure_mode(False)
        result = test_function()
        assert result == "success"

        # Fail to open circuit
        mock_service.set_failure_mode(True)
        for _ in range(2):
            with pytest.raises(MockException):
                test_function()

        # Circuit should be open
        with pytest.raises(CircuitBreakerOpenException):
            test_function()

    @pytest.mark.asyncio
    async def test_async_decorator(self, mock_service):
        """Test circuit breaker decorator on async function."""
        config = CircuitBreakerConfig(failure_threshold=2, recovery_timeout=1)

        @circuit_breaker("test-async", config)
        async def test_async_function():
            return await mock_service.async_call()

        # Successful call
        mock_service.set_failure_mode(False)
        result = await test_async_function()
        assert result == "success"

        # Fail to open circuit
        mock_service.set_failure_mode(True)
        for _ in range(2):
            with pytest.raises(MockException):
                await test_async_function()

        # Circuit should be open
        with pytest.raises(CircuitBreakerOpenException):
            await test_async_function()


class TestCircuitBreakerRegistry:
    """Test circuit breaker registry functionality."""

    def test_get_or_create(self, fresh_registry):
        """Test getting or creating circuit breakers."""
        config = CircuitBreakerConfig()

        # Create new circuit breaker
        breaker1 = fresh_registry.get_or_create("service1", config)
        assert breaker1.name == "service1"

        # Get existing circuit breaker
        breaker2 = fresh_registry.get_or_create("service1", config)
        assert breaker1 is breaker2

    def test_get_nonexistent(self, fresh_registry):
        """Test getting non-existent circuit breaker."""
        breaker = fresh_registry.get("nonexistent")
        assert breaker is None

    def test_get_all_status(self, fresh_registry):
        """Test getting status of all circuit breakers."""
        config = CircuitBreakerConfig()

        breaker1 = fresh_registry.get_or_create("service1", config)
        breaker2 = fresh_registry.get_or_create("service2", config)

        status_dict = fresh_registry.get_all_status()
        assert len(status_dict) == 2
        assert "service1" in status_dict
        assert "service2" in status_dict

    def test_reset_all(self, fresh_registry, mock_service):
        """Test resetting all circuit breakers."""
        config = CircuitBreakerConfig(failure_threshold=1)

        breaker = fresh_registry.get_or_create("service1", config)

        # Open the circuit
        mock_service.set_failure_mode(True)
        with pytest.raises(MockException):
            breaker.call(mock_service.call)

        assert breaker.state == CircuitBreakerState.OPEN

        # Reset all
        fresh_registry.reset_all()
        assert breaker.state == CircuitBreakerState.CLOSED


class TestGlobalFunctions:
    """Test global circuit breaker functions."""

    def test_get_circuit_breaker(self):
        """Test getting circuit breaker from global registry."""
        # Should return None for non-existent breaker
        breaker = get_circuit_breaker("nonexistent")
        assert breaker is None

    def test_get_all_status(self):
        """Test getting all circuit breaker status."""
        status_dict = get_all_circuit_breaker_status()
        assert isinstance(status_dict, dict)

    def test_reset_all(self):
        """Test resetting all circuit breakers."""
        # Should not raise any errors
        reset_all_circuit_breakers()
