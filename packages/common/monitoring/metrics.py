"""
Metrics collection infrastructure for monitoring request duration and error rates.
"""

import time
from collections import defaultdict
from contextlib import contextmanager
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from packages.common.monitoring.models import MetricPoint


class MetricsCollector:
    """Collects and aggregates metrics for monitoring."""

    def __init__(self):
        self._metrics: List[MetricPoint] = []
        self._counters: Dict[str, float] = defaultdict(float)
        self._gauges: Dict[str, float] = {}
        self._histograms: Dict[str, List[float]] = defaultdict(list)
        self._max_metrics = 50000  # Keep last 50k metrics in memory

    def record_counter(
        self, name: str, value: float = 1.0, labels: Dict[str, str] = None
    ):
        """Record a counter metric (cumulative value)."""
        labels = labels or {}
        key = f"{name}:{':'.join(f'{k}={v}' for k, v in sorted(labels.items()))}"
        self._counters[key] += value

        metric = MetricPoint(
            name=name,
            value=self._counters[key],
            labels=labels,
            timestamp=datetime.utcnow(),
        )
        self._add_metric(metric)

    def record_gauge(self, name: str, value: float, labels: Dict[str, str] = None):
        """Record a gauge metric (point-in-time value)."""
        labels = labels or {}
        key = f"{name}:{':'.join(f'{k}={v}' for k, v in sorted(labels.items()))}"
        self._gauges[key] = value

        metric = MetricPoint(
            name=name, value=value, labels=labels, timestamp=datetime.utcnow()
        )
        self._add_metric(metric)

    def record_histogram(self, name: str, value: float, labels: Dict[str, str] = None):
        """Record a histogram metric (for duration measurements)."""
        labels = labels or {}
        key = f"{name}:{':'.join(f'{k}={v}' for k, v in sorted(labels.items()))}"
        self._histograms[key].append(value)

        # Keep only last 1000 values per histogram
        if len(self._histograms[key]) > 1000:
            self._histograms[key] = self._histograms[key][-1000:]

        metric = MetricPoint(
            name=name, value=value, labels=labels, timestamp=datetime.utcnow()
        )
        self._add_metric(metric)

    def _add_metric(self, metric: MetricPoint):
        """Add metric to storage with rotation."""
        self._metrics.append(metric)

        # Rotate metrics if we exceed max
        if len(self._metrics) > self._max_metrics:
            self._metrics = self._metrics[-self._max_metrics :]

    def get_metrics(
        self,
        name: str = None,
        labels: Dict[str, str] = None,
        start_time: datetime = None,
        end_time: datetime = None,
    ) -> List[MetricPoint]:
        """Get metrics matching the specified criteria."""
        filtered_metrics = self._metrics

        # Apply filters
        if name:
            filtered_metrics = [m for m in filtered_metrics if m.name == name]

        if labels:
            filtered_metrics = [
                m
                for m in filtered_metrics
                if all(m.labels.get(k) == v for k, v in labels.items())
            ]

        if start_time:
            filtered_metrics = [
                m for m in filtered_metrics if m.timestamp >= start_time
            ]

        if end_time:
            filtered_metrics = [m for m in filtered_metrics if m.timestamp <= end_time]

        return sorted(filtered_metrics, key=lambda x: x.timestamp)

    def get_counter_value(self, name: str, labels: Dict[str, str] = None) -> float:
        """Get current counter value."""
        labels = labels or {}
        key = f"{name}:{':'.join(f'{k}={v}' for k, v in sorted(labels.items()))}"
        return self._counters.get(key, 0.0)

    def get_gauge_value(
        self, name: str, labels: Dict[str, str] = None
    ) -> Optional[float]:
        """Get current gauge value."""
        labels = labels or {}
        key = f"{name}:{':'.join(f'{k}={v}' for k, v in sorted(labels.items()))}"
        return self._gauges.get(key)

    def get_histogram_stats(
        self, name: str, labels: Dict[str, str] = None
    ) -> Dict[str, float]:
        """Get histogram statistics (min, max, avg, p95, p99)."""
        labels = labels or {}
        key = f"{name}:{':'.join(f'{k}={v}' for k, v in sorted(labels.items()))}"
        values = self._histograms.get(key, [])

        if not values:
            return {}

        sorted_values = sorted(values)
        count = len(sorted_values)

        return {
            "count": count,
            "min": min(sorted_values),
            "max": max(sorted_values),
            "avg": sum(sorted_values) / count,
            "p50": sorted_values[int(count * 0.5)],
            "p95": sorted_values[int(count * 0.95)],
            "p99": sorted_values[int(count * 0.99)],
        }

    def record_request_duration(
        self,
        service: str,
        endpoint: str,
        method: str,
        status_code: int,
        duration_ms: float,
    ):
        """Record HTTP request duration and increment request counter."""
        labels = {
            "service": service,
            "endpoint": endpoint,
            "method": method,
            "status_code": str(status_code),
        }

        # Record duration histogram
        self.record_histogram("http_request_duration_ms", duration_ms, labels)

        # Record request counter
        self.record_counter("http_requests_total", 1.0, labels)

        # Record error counter if status code indicates error
        if status_code >= 400:
            error_labels = {
                "service": service,
                "endpoint": endpoint,
                "method": method,
                "status_code": str(status_code),
            }
            self.record_counter("http_errors_total", 1.0, error_labels)

    def get_error_rate(
        self, service: str, endpoint: str = None, time_window_minutes: int = 5
    ) -> float:
        """Calculate error rate for a service/endpoint over time window."""
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(minutes=time_window_minutes)

        labels = {"service": service}
        if endpoint:
            labels["endpoint"] = endpoint

        # Get total requests
        total_requests = 0
        error_requests = 0

        for metric in self.get_metrics(
            "http_requests_total", labels, start_time, end_time
        ):
            total_requests += metric.value

        for metric in self.get_metrics(
            "http_errors_total", labels, start_time, end_time
        ):
            error_requests += metric.value

        if total_requests == 0:
            return 0.0

        return (error_requests / total_requests) * 100.0

    def get_average_response_time(
        self, service: str, endpoint: str = None, time_window_minutes: int = 5
    ) -> float:
        """Calculate average response time over time window."""
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(minutes=time_window_minutes)

        labels = {"service": service}
        if endpoint:
            labels["endpoint"] = endpoint

        durations = []
        for metric in self.get_metrics(
            "http_request_duration_ms", labels, start_time, end_time
        ):
            durations.append(metric.value)

        if not durations:
            return 0.0

        return sum(durations) / len(durations)

    @contextmanager
    def time_operation(self, name: str, labels: Dict[str, str] = None):
        """Context manager to time an operation."""
        start_time = time.time()
        try:
            yield
        finally:
            duration_ms = (time.time() - start_time) * 1000
            self.record_histogram(name, duration_ms, labels)


# Global metrics collector instance
_metrics_collector = MetricsCollector()


def get_metrics_collector() -> MetricsCollector:
    """Get the global metrics collector instance."""
    return _metrics_collector
