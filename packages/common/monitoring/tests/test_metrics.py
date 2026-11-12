"""
Tests for metrics collection infrastructure.
"""

import time
from datetime import datetime, timedelta

import pytest

from ..metrics import MetricsCollector, get_metrics_collector
from ..models import MetricPoint


class TestMetricsCollector:
    """Test metrics collection functionality."""

    def test_record_counter(self, metrics_collector):
        """Test recording counter metrics."""
        metrics_collector.record_counter("test_counter", 1.0, {"service": "test"})
        metrics_collector.record_counter("test_counter", 2.0, {"service": "test"})

        # Counter should be cumulative
        value = metrics_collector.get_counter_value("test_counter", {"service": "test"})
        assert value == 3.0

    def test_record_gauge(self, metrics_collector):
        """Test recording gauge metrics."""
        metrics_collector.record_gauge("test_gauge", 10.0, {"service": "test"})
        metrics_collector.record_gauge("test_gauge", 20.0, {"service": "test"})

        # Gauge should be the latest value
        value = metrics_collector.get_gauge_value("test_gauge", {"service": "test"})
        assert value == 20.0

    def test_record_histogram(self, metrics_collector):
        """Test recording histogram metrics."""
        values = [10.0, 20.0, 30.0, 40.0, 50.0]
        for value in values:
            metrics_collector.record_histogram(
                "test_histogram", value, {"service": "test"}
            )

        stats = metrics_collector.get_histogram_stats(
            "test_histogram", {"service": "test"}
        )
        assert stats["count"] == 5
        assert stats["min"] == 10.0
        assert stats["max"] == 50.0
        assert stats["avg"] == 30.0

    def test_get_metrics_with_filters(self, metrics_collector):
        """Test getting metrics with various filters."""
        # Add metrics with different names and labels
        metrics_collector.record_counter("metric_1", 1.0, {"service": "service_1"})
        metrics_collector.record_counter("metric_2", 2.0, {"service": "service_2"})
        metrics_collector.record_counter("metric_1", 3.0, {"service": "service_1"})

        # Filter by name
        metrics = metrics_collector.get_metrics(name="metric_1")
        assert len(metrics) == 2
        assert all(m.name == "metric_1" for m in metrics)

        # Filter by labels
        metrics = metrics_collector.get_metrics(labels={"service": "service_1"})
        assert len(metrics) == 2
        assert all(m.labels.get("service") == "service_1" for m in metrics)

    def test_get_metrics_with_time_filter(self, metrics_collector):
        """Test getting metrics with time range filter."""
        now = datetime.utcnow()
        past = now - timedelta(minutes=5)

        # Add metric in the past (simulate by manually creating metric)
        past_metric = MetricPoint(
            name="test_metric", value=1.0, labels={"service": "test"}, timestamp=past
        )
        metrics_collector._add_metric(past_metric)

        # Add current metric
        metrics_collector.record_counter("test_metric", 2.0, {"service": "test"})

        # Filter by time range
        metrics = metrics_collector.get_metrics(start_time=now - timedelta(minutes=1))
        assert len(metrics) == 1  # Only the recent metric

    def test_record_request_duration(self, metrics_collector):
        """Test recording HTTP request duration and counters."""
        metrics_collector.record_request_duration(
            service="test-service",
            endpoint="/api/test",
            method="GET",
            status_code=200,
            duration_ms=150.0,
        )

        # Check that duration histogram was recorded
        duration_stats = metrics_collector.get_histogram_stats(
            "http_request_duration_ms",
            {
                "service": "test-service",
                "endpoint": "/api/test",
                "method": "GET",
                "status_code": "200",
            },
        )
        assert duration_stats["count"] == 1
        assert duration_stats["avg"] == 150.0

        # Check that request counter was incremented
        request_count = metrics_collector.get_counter_value(
            "http_requests_total",
            {
                "service": "test-service",
                "endpoint": "/api/test",
                "method": "GET",
                "status_code": "200",
            },
        )
        assert request_count == 1.0

    def test_record_error_requests(self, metrics_collector):
        """Test recording error requests."""
        # Record successful request
        metrics_collector.record_request_duration(
            service="test-service",
            endpoint="/api/test",
            method="GET",
            status_code=200,
            duration_ms=150.0,
        )

        # Record error request
        metrics_collector.record_request_duration(
            service="test-service",
            endpoint="/api/test",
            method="GET",
            status_code=500,
            duration_ms=200.0,
        )

        # Check error counter
        error_count = metrics_collector.get_counter_value(
            "http_errors_total",
            {
                "service": "test-service",
                "endpoint": "/api/test",
                "method": "GET",
                "status_code": "500",
            },
        )
        assert error_count == 1.0

        # Total requests should be 2
        total_requests = metrics_collector.get_counter_value(
            "http_requests_total",
            {
                "service": "test-service",
                "endpoint": "/api/test",
                "method": "GET",
                "status_code": "200",
            },
        )
        total_requests += metrics_collector.get_counter_value(
            "http_requests_total",
            {
                "service": "test-service",
                "endpoint": "/api/test",
                "method": "GET",
                "status_code": "500",
            },
        )
        assert total_requests == 2.0

    def test_get_error_rate(self, metrics_collector):
        """Test calculating error rate."""
        # Record multiple requests with some errors
        for i in range(10):
            status_code = 500 if i < 2 else 200  # 2 errors out of 10 requests
            metrics_collector.record_request_duration(
                service="test-service",
                endpoint="/api/test",
                method="GET",
                status_code=status_code,
                duration_ms=150.0,
            )

        error_rate = metrics_collector.get_error_rate("test-service", "/api/test")
        assert error_rate == 20.0  # 2/10 * 100 = 20%

    def test_get_average_response_time(self, metrics_collector):
        """Test calculating average response time."""
        durations = [100.0, 200.0, 300.0]
        for duration in durations:
            metrics_collector.record_request_duration(
                service="test-service",
                endpoint="/api/test",
                method="GET",
                status_code=200,
                duration_ms=duration,
            )

        avg_time = metrics_collector.get_average_response_time(
            "test-service", "/api/test"
        )
        assert avg_time == 200.0  # (100 + 200 + 300) / 3

    def test_time_operation_context_manager(self, metrics_collector):
        """Test timing operations with context manager."""
        with metrics_collector.time_operation("test_operation", {"service": "test"}):
            time.sleep(0.01)  # Sleep for 10ms

        stats = metrics_collector.get_histogram_stats(
            "test_operation", {"service": "test"}
        )
        assert stats["count"] == 1
        assert stats["avg"] >= 10.0  # Should be at least 10ms

    def test_metrics_rotation(self, metrics_collector):
        """Test metrics rotation when max metrics exceeded."""
        # Set a small max for testing
        metrics_collector._max_metrics = 5

        # Add more metrics than max
        for i in range(10):
            metrics_collector.record_counter(f"metric_{i}", 1.0)

        # Should only keep the last 5 metrics
        assert len(metrics_collector._metrics) == 5

    def test_histogram_value_rotation(self, metrics_collector):
        """Test histogram value rotation."""
        # Add many values to trigger rotation
        for i in range(1500):  # More than the 1000 limit
            metrics_collector.record_histogram(
                "test_histogram", float(i), {"service": "test"}
            )

        # Should only keep the last 1000 values
        key = "test_histogram:service=test"
        assert len(metrics_collector._histograms[key]) == 1000
        assert metrics_collector._histograms[key][-1] == 1499.0  # Last value


class TestGlobalMetricsCollector:
    """Test global metrics collector instance."""

    def test_get_global_instance(self):
        """Test getting global metrics collector instance."""
        collector1 = get_metrics_collector()
        collector2 = get_metrics_collector()

        # Should return the same instance
        assert collector1 is collector2
        assert isinstance(collector1, MetricsCollector)
