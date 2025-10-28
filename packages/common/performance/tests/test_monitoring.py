"""
Tests for performance monitoring and metrics collection.

Following TDD approach:
1. RED: Write failing tests first
2. GREEN: Implement minimal code to pass tests
3. REFACTOR: Optimize and improve code quality
"""

import asyncio
import time
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ..models import PerformanceMetrics
from ..monitoring import MetricsCollector, PerformanceMonitor


class TestPerformanceMonitor:
    """Test performance monitoring functionality."""

    @pytest.mark.asyncio
    async def test_performance_monitor_initialization(
        self, cache_config, pool_config, cdn_config
    ):
        """Test performance monitor initialization."""
        # This test will fail until we implement PerformanceMonitor
        monitor = PerformanceMonitor(cache_config, pool_config, cdn_config)
        assert monitor.cache_config == cache_config
        assert monitor.pool_config == pool_config
        assert monitor.cdn_config == cdn_config

    @pytest.mark.asyncio
    async def test_collect_cache_metrics(
        self, cache_config, pool_config, cdn_config, mock_redis
    ):
        """Test cache metrics collection."""
        mock_redis.info.return_value = {
            "keyspace_hits": 800,
            "keyspace_misses": 200,
            "used_memory": 2048000,  # 2MB
        }

        with patch("redis.asyncio.Redis.from_url", return_value=mock_redis):
            monitor = PerformanceMonitor(cache_config, pool_config, cdn_config)

            metrics = await monitor.collect_cache_metrics()
            assert metrics.cache_hit_ratio == 0.8  # 800 / (800 + 200)
            assert metrics.cache_miss_ratio == 0.2
            assert metrics.memory_usage_mb > 0

    @pytest.mark.asyncio
    async def test_collect_database_metrics(
        self, cache_config, pool_config, cdn_config, mock_db_connection
    ):
        """Test database connection pool metrics collection."""
        with patch("sqlalchemy.create_engine") as mock_engine:
            mock_engine.return_value.pool.size.return_value = 10
            mock_engine.return_value.pool.checked_in.return_value = 7
            mock_engine.return_value.pool.checked_out.return_value = 3

            monitor = PerformanceMonitor(cache_config, pool_config, cdn_config)

            metrics = await monitor.collect_database_metrics()
            assert metrics.active_connections == 3
            assert metrics.pool_utilization == 0.3  # 3 / 10

    @pytest.mark.asyncio
    async def test_collect_response_time_metrics(
        self, cache_config, pool_config, cdn_config
    ):
        """Test response time metrics collection."""
        monitor = PerformanceMonitor(cache_config, pool_config, cdn_config)

        # Simulate response times
        response_times = [10, 20, 30, 40, 50, 100, 200, 300, 400, 500]  # ms
        for rt in response_times:
            await monitor.record_response_time("test_endpoint", rt)

        metrics = await monitor.get_response_time_metrics()
        assert metrics.avg_response_time_ms > 0
        assert metrics.p95_response_time_ms > metrics.avg_response_time_ms
        assert metrics.p99_response_time_ms > metrics.p95_response_time_ms

    @pytest.mark.asyncio
    async def test_collect_error_rate_metrics(
        self, cache_config, pool_config, cdn_config
    ):
        """Test error rate metrics collection."""
        monitor = PerformanceMonitor(cache_config, pool_config, cdn_config)

        # Simulate requests with some errors
        for i in range(100):
            success = i % 10 != 0  # 10% error rate
            await monitor.record_request("test_endpoint", success)

        metrics = await monitor.get_error_rate_metrics()
        assert abs(metrics.error_rate - 0.1) < 0.01  # Should be ~10%
        assert metrics.total_requests == 100

    @pytest.mark.asyncio
    async def test_collect_system_metrics(self, cache_config, pool_config, cdn_config):
        """Test system resource metrics collection."""
        with patch("psutil.cpu_percent", return_value=45.5):
            with patch("psutil.virtual_memory") as mock_memory:
                mock_memory.return_value.percent = 60.0
                mock_memory.return_value.used = 8 * 1024 * 1024 * 1024  # 8GB

                monitor = PerformanceMonitor(cache_config, pool_config, cdn_config)

                metrics = await monitor.collect_system_metrics()
                assert metrics.cpu_usage_percent == 45.5
                assert metrics.memory_usage_mb > 0

    @pytest.mark.asyncio
    async def test_aggregate_performance_metrics(
        self, cache_config, pool_config, cdn_config, mock_redis
    ):
        """Test aggregating all performance metrics."""
        mock_redis.info.return_value = {
            "keyspace_hits": 900,
            "keyspace_misses": 100,
            "used_memory": 1024000,
        }

        with patch("redis.asyncio.Redis.from_url", return_value=mock_redis):
            with patch("psutil.cpu_percent", return_value=30.0):
                with patch("psutil.virtual_memory") as mock_memory:
                    mock_memory.return_value.percent = 50.0
                    mock_memory.return_value.used = 4 * 1024 * 1024 * 1024  # 4GB

                    monitor = PerformanceMonitor(cache_config, pool_config, cdn_config)

                    # Record some activity
                    await monitor.record_response_time("test", 25.0)
                    await monitor.record_request("test", True)

                    metrics = await monitor.get_aggregated_metrics()
                    assert isinstance(metrics, PerformanceMetrics)
                    assert metrics.cache_hit_ratio == 0.9
                    assert metrics.cpu_usage_percent == 30.0

    @pytest.mark.asyncio
    async def test_performance_alerts(self, cache_config, pool_config, cdn_config):
        """Test performance alerting based on thresholds."""
        monitor = PerformanceMonitor(cache_config, pool_config, cdn_config)

        # Configure alert thresholds
        await monitor.set_alert_threshold("response_time_p95", 100.0)  # 100ms
        await monitor.set_alert_threshold("error_rate", 0.05)  # 5%

        # Simulate high response times
        for _ in range(10):
            await monitor.record_response_time(
                "slow_endpoint", 150.0
            )  # Above threshold

        alerts = await monitor.check_alerts()
        assert len(alerts) > 0
        assert any("response_time" in alert.metric for alert in alerts)

    @pytest.mark.asyncio
    async def test_metrics_time_series(self, cache_config, pool_config, cdn_config):
        """Test time series metrics collection."""
        monitor = PerformanceMonitor(cache_config, pool_config, cdn_config)

        # Record metrics over time
        for i in range(5):
            await monitor.record_response_time("test", 10.0 + i)
            await asyncio.sleep(0.1)  # Small delay

        time_series = await monitor.get_metrics_time_series("response_time", minutes=1)
        assert len(time_series) > 0
        assert all(isinstance(point.timestamp, datetime) for point in time_series)

    @pytest.mark.asyncio
    async def test_performance_dashboard_data(
        self, cache_config, pool_config, cdn_config, mock_redis
    ):
        """Test performance dashboard data preparation."""
        mock_redis.info.return_value = {
            "keyspace_hits": 750,
            "keyspace_misses": 250,
            "used_memory": 3072000,
        }

        with patch("redis.asyncio.Redis.from_url", return_value=mock_redis):
            monitor = PerformanceMonitor(cache_config, pool_config, cdn_config)

            dashboard_data = await monitor.get_dashboard_data()

            assert "cache_metrics" in dashboard_data
            assert "response_time_metrics" in dashboard_data
            assert "error_rate_metrics" in dashboard_data
            assert "system_metrics" in dashboard_data


class TestMetricsCollector:
    """Test metrics collector functionality."""

    def test_metrics_collector_initialization(self):
        """Test metrics collector initialization."""
        collector = MetricsCollector()
        assert collector.metrics_buffer is not None
        assert collector.start_time is not None

    @pytest.mark.asyncio
    async def test_record_metric(self):
        """Test recording individual metrics."""
        collector = MetricsCollector()

        await collector.record_metric("test_metric", 42.0, {"endpoint": "test"})

        metrics = await collector.get_metrics()
        assert len(metrics) == 1
        assert metrics[0].name == "test_metric"
        assert metrics[0].value == 42.0

    @pytest.mark.asyncio
    async def test_record_histogram(self):
        """Test recording histogram metrics."""
        collector = MetricsCollector()

        # Record multiple values
        values = [10, 20, 30, 40, 50]
        for value in values:
            await collector.record_histogram("response_time", value)

        histogram = await collector.get_histogram("response_time")
        assert histogram.count == 5
        assert histogram.sum == sum(values)
        assert histogram.avg == sum(values) / len(values)

    @pytest.mark.asyncio
    async def test_record_counter(self):
        """Test recording counter metrics."""
        collector = MetricsCollector()

        # Increment counter multiple times
        for _ in range(10):
            await collector.increment_counter("requests_total", {"method": "GET"})

        counter_value = await collector.get_counter("requests_total", {"method": "GET"})
        assert counter_value == 10

    @pytest.mark.asyncio
    async def test_metrics_buffer_management(self):
        """Test metrics buffer size management."""
        collector = MetricsCollector(max_buffer_size=5)

        # Add more metrics than buffer size
        for i in range(10):
            await collector.record_metric(f"metric_{i}", float(i))

        metrics = await collector.get_metrics()
        # Should only keep the most recent metrics
        assert len(metrics) <= 5

    @pytest.mark.asyncio
    async def test_metrics_export(self):
        """Test exporting metrics in different formats."""
        collector = MetricsCollector()

        await collector.record_metric("test_metric", 100.0, {"tag": "test"})

        # Test JSON export
        json_export = await collector.export_json()
        assert "test_metric" in json_export

        # Test Prometheus export
        prometheus_export = await collector.export_prometheus()
        assert "test_metric" in prometheus_export


class TestPerformanceOptimization:
    """Test performance optimization strategies."""

    @pytest.mark.asyncio
    async def test_cache_warming(self, cache_config, pool_config, cdn_config):
        """Test cache warming strategies."""
        monitor = PerformanceMonitor(cache_config, pool_config, cdn_config)

        # Define cache warming strategy
        warm_keys = ["user:popular", "config:app", "data:frequent"]

        result = await monitor.warm_cache(warm_keys)
        assert result.success is True
        assert result.warmed_keys == len(warm_keys)

    @pytest.mark.asyncio
    async def test_connection_pool_optimization(
        self, cache_config, pool_config, cdn_config
    ):
        """Test connection pool optimization recommendations."""
        monitor = PerformanceMonitor(cache_config, pool_config, cdn_config)

        # Simulate high pool utilization
        await monitor.record_pool_utilization(0.95)  # 95% utilization

        recommendations = await monitor.get_optimization_recommendations()

        pool_recommendations = [
            r for r in recommendations if r.category == "connection_pool"
        ]
        assert len(pool_recommendations) > 0
        assert any("increase" in r.recommendation.lower() for r in pool_recommendations)

    @pytest.mark.asyncio
    async def test_performance_regression_detection(
        self, cache_config, pool_config, cdn_config
    ):
        """Test performance regression detection."""
        monitor = PerformanceMonitor(cache_config, pool_config, cdn_config)

        # Record baseline performance
        for _ in range(100):
            await monitor.record_response_time("api_endpoint", 50.0)  # 50ms baseline

        await monitor.establish_baseline("api_endpoint")

        # Record degraded performance
        for _ in range(20):
            await monitor.record_response_time("api_endpoint", 150.0)  # 150ms degraded

        regressions = await monitor.detect_regressions()
        assert len(regressions) > 0
        assert any("api_endpoint" in r.endpoint for r in regressions)

    @pytest.mark.asyncio
    async def test_auto_scaling_triggers(self, cache_config, pool_config, cdn_config):
        """Test auto-scaling trigger conditions."""
        monitor = PerformanceMonitor(cache_config, pool_config, cdn_config)

        # Configure scaling thresholds
        await monitor.set_scaling_threshold("cpu_usage", 80.0, "scale_up")
        await monitor.set_scaling_threshold("response_time_p95", 200.0, "scale_up")

        # Simulate high load conditions
        with patch("psutil.cpu_percent", return_value=85.0):
            await monitor.record_response_time("api", 250.0)

            scaling_decisions = await monitor.evaluate_scaling()

            scale_up_decisions = [
                d for d in scaling_decisions if d.action == "scale_up"
            ]
            assert len(scale_up_decisions) > 0
