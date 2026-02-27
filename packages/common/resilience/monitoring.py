"""
Monitoring and metrics collection for resilience patterns.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from .circuit_breaker import get_all_circuit_breaker_status
from .models import CircuitBreakerState, CircuitBreakerStatus, RetryAttempt

logger = logging.getLogger(__name__)


@dataclass
class ResilienceMetrics:
    """Aggregated metrics for resilience patterns."""

    timestamp: datetime
    circuit_breaker_metrics: Dict[str, "CircuitBreakerMetrics"]
    retry_metrics: Dict[str, "RetryMetrics"]


@dataclass
class CircuitBreakerMetrics:
    """Metrics for a specific circuit breaker."""

    name: str
    state: CircuitBreakerState
    total_requests: int
    successful_requests: int
    failed_requests: int
    failure_rate: float
    success_rate: float
    failure_count: int
    success_count: int
    last_failure_time: Optional[datetime]
    next_attempt_time: Optional[datetime]
    uptime_percentage: float = 0.0

    @classmethod
    def from_status(
        cls, status: CircuitBreakerStatus, name: str
    ) -> "CircuitBreakerMetrics":
        """Create metrics from circuit breaker status."""
        return cls(
            name=name,
            state=status.state,
            total_requests=status.total_requests,
            successful_requests=status.successful_requests,
            failed_requests=status.failed_requests,
            failure_rate=status.failure_rate,
            success_rate=status.success_rate,
            failure_count=status.failure_count,
            success_count=status.success_count,
            last_failure_time=status.last_failure_time,
            next_attempt_time=status.next_attempt_time,
        )


@dataclass
class RetryMetrics:
    """Metrics for retry operations."""

    operation_name: str
    total_attempts: int
    successful_retries: int
    failed_retries: int
    average_attempts: float
    max_attempts: int
    total_delay: float
    average_delay: float
    retry_success_rate: float


class ResilienceMonitor:
    """Monitor and collect metrics for resilience patterns."""

    def __init__(self):
        self._retry_history: Dict[str, List[RetryAttempt]] = {}
        self._metrics_history: List[ResilienceMetrics] = []
        self._max_history_size = 1000

    def record_retry_attempts(self, operation_name: str, attempts: List[RetryAttempt]):
        """Record retry attempts for an operation."""
        if operation_name not in self._retry_history:
            self._retry_history[operation_name] = []

        self._retry_history[operation_name].extend(attempts)

        # Keep only recent attempts
        if len(self._retry_history[operation_name]) > self._max_history_size:
            self._retry_history[operation_name] = self._retry_history[operation_name][
                -self._max_history_size :
            ]

    def get_circuit_breaker_metrics(self) -> Dict[str, CircuitBreakerMetrics]:
        """Get current circuit breaker metrics."""
        status_dict = get_all_circuit_breaker_status()
        metrics = {}

        for name, status in status_dict.items():
            metrics[name] = CircuitBreakerMetrics.from_status(status, name)

            # Calculate uptime percentage (simplified - based on current state)
            if status.state == CircuitBreakerState.CLOSED:
                metrics[name].uptime_percentage = 100.0
            elif status.state == CircuitBreakerState.HALF_OPEN:
                metrics[name].uptime_percentage = 50.0
            else:  # OPEN
                metrics[name].uptime_percentage = 0.0

        return metrics

    def get_retry_metrics(
        self, time_window: Optional[timedelta] = None
    ) -> Dict[str, RetryMetrics]:
        """Get retry metrics for all operations."""
        if time_window is None:
            time_window = timedelta(hours=1)

        cutoff_time = datetime.utcnow() - time_window
        metrics = {}

        for operation_name, attempts in self._retry_history.items():
            # Filter attempts within time window
            recent_attempts = [
                attempt for attempt in attempts if attempt.timestamp >= cutoff_time
            ]

            if not recent_attempts:
                continue

            # Group attempts by operation instance (simplified grouping)
            operation_groups = {}
            for attempt in recent_attempts:
                # Use timestamp as a simple grouping key (could be improved)
                group_key = attempt.timestamp.replace(second=0, microsecond=0)
                if group_key not in operation_groups:
                    operation_groups[group_key] = []
                operation_groups[group_key].append(attempt)

            total_attempts = len(recent_attempts)
            successful_retries = len(
                [a for a in recent_attempts if a.exception is None]
            )
            failed_retries = total_attempts - successful_retries

            # Calculate averages
            if operation_groups:
                attempts_per_operation = [
                    len(group) for group in operation_groups.values()
                ]
                average_attempts = sum(attempts_per_operation) / len(
                    attempts_per_operation
                )
                max_attempts = max(attempts_per_operation)
            else:
                average_attempts = 0
                max_attempts = 0

            total_delay = sum(attempt.delay for attempt in recent_attempts)
            average_delay = total_delay / total_attempts if total_attempts > 0 else 0

            retry_success_rate = (
                (successful_retries / total_attempts * 100) if total_attempts > 0 else 0
            )

            metrics[operation_name] = RetryMetrics(
                operation_name=operation_name,
                total_attempts=total_attempts,
                successful_retries=successful_retries,
                failed_retries=failed_retries,
                average_attempts=average_attempts,
                max_attempts=max_attempts,
                total_delay=total_delay,
                average_delay=average_delay,
                retry_success_rate=retry_success_rate,
            )

        return metrics

    def get_current_metrics(self) -> ResilienceMetrics:
        """Get current resilience metrics snapshot."""
        return ResilienceMetrics(
            timestamp=datetime.utcnow(),
            circuit_breaker_metrics=self.get_circuit_breaker_metrics(),
            retry_metrics=self.get_retry_metrics(),
        )

    def collect_metrics(self) -> ResilienceMetrics:
        """Collect and store current metrics."""
        metrics = self.get_current_metrics()
        self._metrics_history.append(metrics)

        # Keep only recent metrics
        if len(self._metrics_history) > self._max_history_size:
            self._metrics_history = self._metrics_history[-self._max_history_size :]

        return metrics

    def get_metrics_history(self, limit: int = 100) -> List[ResilienceMetrics]:
        """Get historical metrics."""
        return self._metrics_history[-limit:] if self._metrics_history else []

    def get_health_summary(self) -> Dict[str, Any]:
        """Get overall health summary of resilience patterns."""
        cb_metrics = self.get_circuit_breaker_metrics()
        retry_metrics = self.get_retry_metrics()

        # Calculate overall health scores
        total_cb = len(cb_metrics)
        healthy_cb = len(
            [m for m in cb_metrics.values() if m.state == CircuitBreakerState.CLOSED]
        )
        cb_health_score = (healthy_cb / total_cb * 100) if total_cb > 0 else 100

        total_retry_ops = len(retry_metrics)
        successful_retry_ops = len(
            [m for m in retry_metrics.values() if m.retry_success_rate > 50]
        )
        retry_health_score = (
            (successful_retry_ops / total_retry_ops * 100)
            if total_retry_ops > 0
            else 100
        )

        overall_health_score = (cb_health_score + retry_health_score) / 2

        return {
            "overall_health_score": overall_health_score,
            "circuit_breaker_health": {
                "score": cb_health_score,
                "total_breakers": total_cb,
                "healthy_breakers": healthy_cb,
                "open_breakers": len(
                    [
                        m
                        for m in cb_metrics.values()
                        if m.state == CircuitBreakerState.OPEN
                    ]
                ),
                "half_open_breakers": len(
                    [
                        m
                        for m in cb_metrics.values()
                        if m.state == CircuitBreakerState.HALF_OPEN
                    ]
                ),
            },
            "retry_health": {
                "score": retry_health_score,
                "total_operations": total_retry_ops,
                "successful_operations": successful_retry_ops,
                "average_success_rate": sum(
                    m.retry_success_rate for m in retry_metrics.values()
                )
                / total_retry_ops
                if total_retry_ops > 0
                else 0,
            },
            "timestamp": datetime.utcnow(),
        }

    def clear_history(self):
        """Clear all historical data."""
        self._retry_history.clear()
        self._metrics_history.clear()
        logger.info("Resilience monitoring history cleared")


# Global monitor instance
_monitor = ResilienceMonitor()


def get_resilience_monitor() -> ResilienceMonitor:
    """Get the global resilience monitor instance."""
    return _monitor


def record_retry_attempts(operation_name: str, attempts: List[RetryAttempt]):
    """Record retry attempts in the global monitor."""
    _monitor.record_retry_attempts(operation_name, attempts)


def get_resilience_health() -> Dict[str, Any]:
    """Get current resilience health summary."""
    return _monitor.get_health_summary()
