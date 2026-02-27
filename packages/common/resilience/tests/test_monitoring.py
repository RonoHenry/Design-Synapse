"""
Tests for resilience monitoring and metrics collection.
"""

from datetime import datetime, timedelta
from unittest.mock import patch

import pytest

from ..circuit_breaker import CircuitBreaker, CircuitBreakerConfig
from ..models import CircuitBreakerState, CircuitBreakerStatus, RetryAttempt
from ..monitoring import (CircuitBreakerMetrics, ResilienceMonitor,
                          RetryMetrics, get_resilience_health,
                          get_resilience_monitor, record_retry_attempts)
from .conftest import MockException


class TestCircuitBreakerMetrics:
    """Test circuit breaker metrics functionality."""

    def test_from_status(self):
        """Test creating metrics from circuit breaker status."""
        status = CircuitBreakerStatus(
            state=CircuitBreakerState.CLOSED,
            failure_count=2,
            success_count=0,
            last_failure_time=datetime.utcnow(),
            next_attempt_time=None,
            total_requests=10,
            successful_requests=8,
            failed_requests=2,
        )

        metrics = CircuitBreakerMetrics.from_status(status, "test-service")

        assert metrics.name == "test-service"
        assert metrics.state == CircuitBreakerState.CLOSED
        assert metrics.total_requests == 10
        assert metrics.successful_requests == 8
        assert metrics.failed_requests == 2
        assert metrics.failure_rate == 0.2
        assert metrics.success_rate == 0.8
        assert metrics.failure_count == 2
        assert metrics.success_count == 0


class TestResilienceMonitor:
    """Test resilience monitor functionality."""

    def test_record_retry_attempts(self):
        """Test recording retry attempts."""
        monitor = ResilienceMonitor()

        attempts = [
            RetryAttempt(1, 0.5, MockException("Error 1"), datetime.utcnow()),
            RetryAttempt(2, 1.0, MockException("Error 2"), datetime.utcnow()),
            RetryAttempt(3, 2.0, None, datetime.utcnow()),  # Success
        ]

        monitor.record_retry_attempts("test-operation", attempts)

        assert "test-operation" in monitor._retry_history
        assert len(monitor._retry_history["test-operation"]) == 3

    def test_get_circuit_breaker_metrics(self):
        """Test getting circuit breaker metrics."""
        from ..circuit_breaker import _registry

        # Clear registry to ensure clean state
        _registry._breakers.clear()

        monitor = ResilienceMonitor()

        # Create a circuit breaker and register it in the global registry
        config = CircuitBreakerConfig(failure_threshold=3)
        breaker = _registry.get_or_create("test-service", config)

        # Make some calls to generate metrics
        try:
            breaker.call(lambda: "success")
        except:
            pass

        metrics = monitor.get_circuit_breaker_metrics()

        # Should include our test service
        assert "test-service" in metrics
        assert metrics["test-service"].name == "test-service"
        assert metrics["test-service"].state == CircuitBreakerState.CLOSED

    def test_get_retry_metrics(self):
        """Test getting retry metrics."""
        monitor = ResilienceMonitor()

        # Record some retry attempts
        now = datetime.utcnow()
        attempts = [
            RetryAttempt(1, 0.5, MockException("Error"), now - timedelta(minutes=5)),
            RetryAttempt(2, 1.0, None, now - timedelta(minutes=5)),  # Success
            RetryAttempt(1, 0.5, MockException("Error"), now - timedelta(minutes=2)),
            RetryAttempt(2, 1.0, MockException("Error"), now - timedelta(minutes=2)),
            RetryAttempt(3, 2.0, None, now - timedelta(minutes=2)),  # Success
        ]

        monitor.record_retry_attempts("test-operation", attempts)

        # Get metrics for last hour
        metrics = monitor.get_retry_metrics(timedelta(hours=1))

        assert "test-operation" in metrics
        retry_metrics = metrics["test-operation"]
        assert retry_metrics.operation_name == "test-operation"
        assert retry_metrics.total_attempts == 5
        assert retry_metrics.successful_retries == 2  # 2 attempts with no exception
        assert retry_metrics.failed_retries == 3

    def test_get_retry_metrics_time_window(self):
        """Test retry metrics with time window filtering."""
        monitor = ResilienceMonitor()

        now = datetime.utcnow()
        old_attempts = [
            RetryAttempt(1, 0.5, MockException("Old error"), now - timedelta(hours=2))
        ]
        recent_attempts = [
            RetryAttempt(
                1, 0.5, MockException("Recent error"), now - timedelta(minutes=5)
            )
        ]

        monitor.record_retry_attempts("test-operation", old_attempts + recent_attempts)

        # Get metrics for last 30 minutes
        metrics = monitor.get_retry_metrics(timedelta(minutes=30))

        assert "test-operation" in metrics
        assert metrics["test-operation"].total_attempts == 1  # Only recent attempt

    def test_get_current_metrics(self):
        """Test getting current metrics snapshot."""
        monitor = ResilienceMonitor()

        # Record some data
        attempts = [RetryAttempt(1, 0.5, None, datetime.utcnow())]
        monitor.record_retry_attempts("test-op", attempts)

        metrics = monitor.get_current_metrics()

        assert metrics.timestamp is not None
        assert isinstance(metrics.circuit_breaker_metrics, dict)
        assert isinstance(metrics.retry_metrics, dict)
        assert "test-op" in metrics.retry_metrics

    def test_collect_metrics(self):
        """Test collecting and storing metrics."""
        monitor = ResilienceMonitor()

        metrics = monitor.collect_metrics()

        assert len(monitor._metrics_history) == 1
        assert monitor._metrics_history[0] == metrics

    def test_get_metrics_history(self):
        """Test getting metrics history."""
        monitor = ResilienceMonitor()

        # Collect some metrics
        for _ in range(5):
            monitor.collect_metrics()

        history = monitor.get_metrics_history(limit=3)
        assert len(history) == 3

        # Should be most recent metrics
        assert history[-1] == monitor._metrics_history[-1]

    def test_get_health_summary(self):
        """Test getting health summary."""
        from ..circuit_breaker import _registry

        # Clear registry to ensure clean state
        _registry._breakers.clear()

        monitor = ResilienceMonitor()

        # Create circuit breaker in different states
        config = CircuitBreakerConfig(failure_threshold=1)

        # Healthy breaker
        healthy_breaker = _registry.get_or_create("healthy-service", config)
        healthy_breaker.call(lambda: "success")

        # Unhealthy breaker
        unhealthy_breaker = _registry.get_or_create("unhealthy-service", config)
        try:
            unhealthy_breaker.call(lambda: (_ for _ in ()).throw(Exception("Fail")))
        except:
            pass

        # Record some retry attempts
        successful_attempts = [RetryAttempt(1, 0.5, None, datetime.utcnow())]
        failed_attempts = [
            RetryAttempt(1, 0.5, MockException("Error"), datetime.utcnow()),
            RetryAttempt(2, 1.0, MockException("Error"), datetime.utcnow()),
        ]

        monitor.record_retry_attempts("successful-op", successful_attempts)
        monitor.record_retry_attempts("failed-op", failed_attempts)

        health = monitor.get_health_summary()

        assert "overall_health_score" in health
        assert "circuit_breaker_health" in health
        assert "retry_health" in health
        assert "timestamp" in health

        cb_health = health["circuit_breaker_health"]
        assert cb_health["total_breakers"] == 2
        assert cb_health["healthy_breakers"] == 1  # Only healthy-service is closed
        assert cb_health["open_breakers"] == 1  # unhealthy-service is open

    def test_clear_history(self):
        """Test clearing monitoring history."""
        monitor = ResilienceMonitor()

        # Add some data
        attempts = [RetryAttempt(1, 0.5, None, datetime.utcnow())]
        monitor.record_retry_attempts("test-op", attempts)
        monitor.collect_metrics()

        assert len(monitor._retry_history) > 0
        assert len(monitor._metrics_history) > 0

        monitor.clear_history()

        assert len(monitor._retry_history) == 0
        assert len(monitor._metrics_history) == 0

    def test_max_history_size_limit(self):
        """Test that history is limited to max size."""
        monitor = ResilienceMonitor()
        monitor._max_history_size = 5  # Set small limit for testing

        # Add more attempts than the limit
        for i in range(10):
            attempts = [RetryAttempt(1, 0.5, None, datetime.utcnow())]
            monitor.record_retry_attempts("test-op", attempts)

        # Should only keep the most recent attempts
        assert len(monitor._retry_history["test-op"]) == 5

        # Same for metrics history
        for _ in range(10):
            monitor.collect_metrics()

        assert len(monitor._metrics_history) == 5


class TestGlobalMonitorFunctions:
    """Test global monitoring functions."""

    def test_get_resilience_monitor(self):
        """Test getting global monitor instance."""
        monitor1 = get_resilience_monitor()
        monitor2 = get_resilience_monitor()

        # Should return same instance
        assert monitor1 is monitor2

    def test_record_retry_attempts_global(self):
        """Test recording retry attempts globally."""
        attempts = [RetryAttempt(1, 0.5, None, datetime.utcnow())]

        record_retry_attempts("global-test", attempts)

        monitor = get_resilience_monitor()
        assert "global-test" in monitor._retry_history

    def test_get_resilience_health_global(self):
        """Test getting resilience health globally."""
        health = get_resilience_health()

        assert isinstance(health, dict)
        assert "overall_health_score" in health
        assert "circuit_breaker_health" in health
        assert "retry_health" in health


class TestRetryMetrics:
    """Test retry metrics calculations."""

    def test_retry_metrics_calculations(self):
        """Test retry metrics calculations are correct."""
        metrics = RetryMetrics(
            operation_name="test-op",
            total_attempts=10,
            successful_retries=7,
            failed_retries=3,
            average_attempts=2.5,
            max_attempts=4,
            total_delay=15.0,
            average_delay=1.5,
            retry_success_rate=70.0,
        )

        assert metrics.operation_name == "test-op"
        assert metrics.total_attempts == 10
        assert metrics.successful_retries == 7
        assert metrics.failed_retries == 3
        assert metrics.retry_success_rate == 70.0
        assert metrics.average_delay == 1.5
