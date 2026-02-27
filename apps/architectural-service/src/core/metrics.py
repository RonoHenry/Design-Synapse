"""Metrics collection for monitoring service performance."""

import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional


@dataclass
class RequestMetrics:
    """Metrics for a single request."""

    endpoint: str
    method: str
    status_code: int
    latency_ms: float
    timestamp: datetime
    error: Optional[str] = None


@dataclass
class ExternalServiceMetrics:
    """Metrics for external service calls."""

    service_name: str
    operation: str
    latency_ms: float
    success: bool
    timestamp: datetime
    error: Optional[str] = None


@dataclass
class CacheMetrics:
    """Metrics for cache operations."""

    operation: str  # hit, miss, set, delete
    key_pattern: str
    timestamp: datetime
    latency_ms: Optional[float] = None


class MetricsCollector:
    """Collects and aggregates service metrics."""

    def __init__(self, max_history: int = 10000):
        """
        Initialize metrics collector.

        Args:
            max_history: Maximum number of metrics to keep in memory
        """
        self.max_history = max_history

        # Request metrics
        self._request_metrics: List[RequestMetrics] = []
        self._request_count_by_endpoint: Dict[str, int] = defaultdict(int)
        self._error_count_by_endpoint: Dict[str, int] = defaultdict(int)

        # External service metrics
        self._external_service_metrics: List[ExternalServiceMetrics] = []
        self._external_service_call_count: Dict[str, int] = defaultdict(int)
        self._external_service_error_count: Dict[str, int] = defaultdict(int)

        # Cache metrics
        self._cache_metrics: List[CacheMetrics] = []
        self._cache_hit_count: int = 0
        self._cache_miss_count: int = 0

        # Start time for uptime calculation
        self._start_time = datetime.now(timezone.utc)

    def record_request(
        self,
        endpoint: str,
        method: str,
        status_code: int,
        latency_ms: float,
        error: Optional[str] = None,
    ):
        """Record a request metric."""
        metric = RequestMetrics(
            endpoint=endpoint,
            method=method,
            status_code=status_code,
            latency_ms=latency_ms,
            timestamp=datetime.now(timezone.utc),
            error=error,
        )

        self._request_metrics.append(metric)
        self._request_count_by_endpoint[endpoint] += 1

        if status_code >= 400:
            self._error_count_by_endpoint[endpoint] += 1

        # Rotate history if needed
        if len(self._request_metrics) > self.max_history:
            self._request_metrics = self._request_metrics[-self.max_history :]

    def record_external_service_call(
        self,
        service_name: str,
        operation: str,
        latency_ms: float,
        success: bool,
        error: Optional[str] = None,
    ):
        """Record an external service call metric."""
        metric = ExternalServiceMetrics(
            service_name=service_name,
            operation=operation,
            latency_ms=latency_ms,
            success=success,
            timestamp=datetime.now(timezone.utc),
            error=error,
        )

        self._external_service_metrics.append(metric)
        self._external_service_call_count[service_name] += 1

        if not success:
            self._external_service_error_count[service_name] += 1

        # Rotate history if needed
        if len(self._external_service_metrics) > self.max_history:
            self._external_service_metrics = self._external_service_metrics[
                -self.max_history :
            ]

    def record_cache_operation(
        self,
        operation: str,
        key_pattern: str,
        latency_ms: Optional[float] = None,
    ):
        """Record a cache operation metric."""
        metric = CacheMetrics(
            operation=operation,
            key_pattern=key_pattern,
            timestamp=datetime.now(timezone.utc),
            latency_ms=latency_ms,
        )

        self._cache_metrics.append(metric)

        if operation == "hit":
            self._cache_hit_count += 1
        elif operation == "miss":
            self._cache_miss_count += 1

        # Rotate history if needed
        if len(self._cache_metrics) > self.max_history:
            self._cache_metrics = self._cache_metrics[-self.max_history :]

    def get_request_latency_percentiles(
        self, endpoint: Optional[str] = None
    ) -> Dict[str, float]:
        """
        Calculate request latency percentiles.

        Args:
            endpoint: Optional endpoint filter

        Returns:
            Dictionary with p50, p95, p99 latencies
        """
        metrics = self._request_metrics

        if endpoint:
            metrics = [m for m in metrics if m.endpoint == endpoint]

        if not metrics:
            return {"p50": 0.0, "p95": 0.0, "p99": 0.0}

        latencies = sorted([m.latency_ms for m in metrics])
        n = len(latencies)

        return {
            "p50": latencies[int(n * 0.50)] if n > 0 else 0.0,
            "p95": latencies[int(n * 0.95)] if n > 0 else 0.0,
            "p99": latencies[int(n * 0.99)] if n > 0 else 0.0,
        }

    def get_error_rate(self, endpoint: Optional[str] = None) -> float:
        """
        Calculate error rate as percentage.

        Args:
            endpoint: Optional endpoint filter

        Returns:
            Error rate as percentage (0-100)
        """
        if endpoint:
            total = self._request_count_by_endpoint.get(endpoint, 0)
            errors = self._error_count_by_endpoint.get(endpoint, 0)
        else:
            total = sum(self._request_count_by_endpoint.values())
            errors = sum(self._error_count_by_endpoint.values())

        if total == 0:
            return 0.0

        return (errors / total) * 100

    def get_external_service_latency_percentiles(
        self, service_name: Optional[str] = None
    ) -> Dict[str, float]:
        """
        Calculate external service call latency percentiles.

        Args:
            service_name: Optional service name filter

        Returns:
            Dictionary with p50, p95, p99 latencies
        """
        metrics = self._external_service_metrics

        if service_name:
            metrics = [m for m in metrics if m.service_name == service_name]

        if not metrics:
            return {"p50": 0.0, "p95": 0.0, "p99": 0.0}

        latencies = sorted([m.latency_ms for m in metrics])
        n = len(latencies)

        return {
            "p50": latencies[int(n * 0.50)] if n > 0 else 0.0,
            "p95": latencies[int(n * 0.95)] if n > 0 else 0.0,
            "p99": latencies[int(n * 0.99)] if n > 0 else 0.0,
        }

    def get_external_service_error_rate(
        self, service_name: Optional[str] = None
    ) -> float:
        """
        Calculate external service error rate as percentage.

        Args:
            service_name: Optional service name filter

        Returns:
            Error rate as percentage (0-100)
        """
        if service_name:
            total = self._external_service_call_count.get(service_name, 0)
            errors = self._external_service_error_count.get(service_name, 0)
        else:
            total = sum(self._external_service_call_count.values())
            errors = sum(self._external_service_error_count.values())

        if total == 0:
            return 0.0

        return (errors / total) * 100

    def get_cache_hit_rate(self) -> float:
        """
        Calculate cache hit rate as percentage.

        Returns:
            Cache hit rate as percentage (0-100)
        """
        total = self._cache_hit_count + self._cache_miss_count

        if total == 0:
            return 0.0

        return (self._cache_hit_count / total) * 100

    def get_uptime_seconds(self) -> float:
        """Get service uptime in seconds."""
        return (datetime.now(timezone.utc) - self._start_time).total_seconds()

    def get_metrics_summary(self) -> Dict:
        """
        Get comprehensive metrics summary.

        Returns:
            Dictionary with all collected metrics
        """
        return {
            "uptime_seconds": self.get_uptime_seconds(),
            "requests": {
                "total": sum(self._request_count_by_endpoint.values()),
                "by_endpoint": dict(self._request_count_by_endpoint),
                "error_count": sum(self._error_count_by_endpoint.values()),
                "error_rate_percent": self.get_error_rate(),
                "latency_percentiles": self.get_request_latency_percentiles(),
            },
            "external_services": {
                "total_calls": sum(self._external_service_call_count.values()),
                "by_service": dict(self._external_service_call_count),
                "error_count": sum(self._external_service_error_count.values()),
                "error_rate_percent": self.get_external_service_error_rate(),
                "latency_percentiles": self.get_external_service_latency_percentiles(),
            },
            "cache": {
                "hit_count": self._cache_hit_count,
                "miss_count": self._cache_miss_count,
                "hit_rate_percent": self.get_cache_hit_rate(),
            },
        }

    def get_endpoint_metrics(self, endpoint: str) -> Dict:
        """
        Get metrics for a specific endpoint.

        Args:
            endpoint: Endpoint path

        Returns:
            Dictionary with endpoint-specific metrics
        """
        return {
            "endpoint": endpoint,
            "request_count": self._request_count_by_endpoint.get(endpoint, 0),
            "error_count": self._error_count_by_endpoint.get(endpoint, 0),
            "error_rate_percent": self.get_error_rate(endpoint),
            "latency_percentiles": self.get_request_latency_percentiles(endpoint),
        }

    def get_service_metrics(self, service_name: str) -> Dict:
        """
        Get metrics for a specific external service.

        Args:
            service_name: Service name

        Returns:
            Dictionary with service-specific metrics
        """
        return {
            "service_name": service_name,
            "call_count": self._external_service_call_count.get(service_name, 0),
            "error_count": self._external_service_error_count.get(service_name, 0),
            "error_rate_percent": self.get_external_service_error_rate(service_name),
            "latency_percentiles": self.get_external_service_latency_percentiles(
                service_name
            ),
        }


# Global metrics collector instance
_metrics_collector = MetricsCollector()


def get_metrics_collector() -> MetricsCollector:
    """Get the global metrics collector instance."""
    return _metrics_collector
