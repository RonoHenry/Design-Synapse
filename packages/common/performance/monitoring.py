"""
Performance monitoring and metrics collection.

This module provides:
- Comprehensive performance metrics collection
- Response time tracking and percentile calculations
- Error rate monitoring
- System resource monitoring
- Performance alerting and regression detection
- Auto-scaling trigger evaluation
"""

import asyncio
import json
import statistics
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from .cache import CacheManager
from .cdn import CDNManager
from .connection_pool import ConnectionPoolManager
from .models import CacheConfig, CDNConfig, PerformanceMetrics, PoolConfig


@dataclass
class MetricPoint:
    """Individual metric data point."""

    name: str
    value: float
    labels: Dict[str, str]
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class Alert:
    """Performance alert."""

    metric: str
    threshold: float
    current_value: float
    severity: str
    message: str
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class Regression:
    """Performance regression detection."""

    endpoint: str
    metric: str
    baseline_value: float
    current_value: float
    degradation_percent: float
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class ScalingDecision:
    """Auto-scaling decision."""

    action: str  # scale_up, scale_down, no_action
    reason: str
    metric_triggers: List[str]
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class OptimizationRecommendation:
    """Performance optimization recommendation."""

    category: str
    recommendation: str
    impact: str
    priority: str
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class CacheWarmingResult:
    """Result of cache warming operation."""

    success: bool
    warmed_keys: int
    failed_keys: int
    total_time_ms: float


class MetricsCollector:
    """Metrics collection and aggregation."""

    def __init__(self, max_buffer_size: int = 10000):
        """Initialize metrics collector."""
        self.metrics_buffer: deque = deque(maxlen=max_buffer_size)
        self.histograms: Dict[str, List[float]] = defaultdict(list)
        self.counters: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
        self.start_time = datetime.utcnow()

    async def record_metric(
        self, name: str, value: float, labels: Optional[Dict[str, str]] = None
    ):
        """Record a metric value."""
        labels = labels or {}
        metric = MetricPoint(name=name, value=value, labels=labels)
        self.metrics_buffer.append(metric)

    async def record_histogram(self, name: str, value: float):
        """Record histogram metric."""
        self.histograms[name].append(value)
        # Keep only recent values to prevent memory growth
        if len(self.histograms[name]) > 1000:
            self.histograms[name] = self.histograms[name][-1000:]

    async def increment_counter(
        self, name: str, labels: Optional[Dict[str, str]] = None
    ):
        """Increment counter metric."""
        labels = labels or {}
        label_key = json.dumps(labels, sort_keys=True)
        self.counters[name][label_key] += 1

    async def get_metrics(self) -> List[MetricPoint]:
        """Get all collected metrics."""
        return list(self.metrics_buffer)

    async def get_histogram(self, name: str) -> Dict[str, float]:
        """Get histogram statistics."""
        values = self.histograms.get(name, [])
        if not values:
            return {
                "count": 0,
                "sum": 0.0,
                "avg": 0.0,
                "p50": 0.0,
                "p95": 0.0,
                "p99": 0.0,
            }

        return {
            "count": len(values),
            "sum": sum(values),
            "avg": statistics.mean(values),
            "p50": statistics.median(values),
            "p95": statistics.quantiles(values, n=20)[18]
            if len(values) >= 20
            else max(values),
            "p99": statistics.quantiles(values, n=100)[98]
            if len(values) >= 100
            else max(values),
        }

    async def get_counter(
        self, name: str, labels: Optional[Dict[str, str]] = None
    ) -> int:
        """Get counter value."""
        labels = labels or {}
        label_key = json.dumps(labels, sort_keys=True)
        return self.counters[name][label_key]

    async def export_json(self) -> str:
        """Export metrics as JSON."""
        data = {
            "metrics": [
                {
                    "name": m.name,
                    "value": m.value,
                    "labels": m.labels,
                    "timestamp": m.timestamp.isoformat(),
                }
                for m in self.metrics_buffer
            ],
            "histograms": {
                name: await self.get_histogram(name) for name in self.histograms.keys()
            },
            "counters": dict(self.counters),
        }
        return json.dumps(data, indent=2)

    async def export_prometheus(self) -> str:
        """Export metrics in Prometheus format."""
        lines = []

        # Export regular metrics
        for metric in self.metrics_buffer:
            labels_str = ",".join(f'{k}="{v}"' for k, v in metric.labels.items())
            if labels_str:
                lines.append(f"{metric.name}{{{labels_str}}} {metric.value}")
            else:
                lines.append(f"{metric.name} {metric.value}")

        return "\n".join(lines)


class PerformanceMonitor:
    """Comprehensive performance monitoring system."""

    def __init__(
        self, cache_config: CacheConfig, pool_config: PoolConfig, cdn_config: CDNConfig
    ):
        """Initialize performance monitor."""
        self.cache_config = cache_config
        self.pool_config = pool_config
        self.cdn_config = cdn_config

        self.cache_manager: Optional[CacheManager] = None
        self.pool_manager: Optional[ConnectionPoolManager] = None
        self.cdn_manager: Optional[CDNManager] = None

        self.metrics_collector = MetricsCollector()
        self.response_times: Dict[str, List[float]] = defaultdict(list)
        self.request_counts: Dict[str, int] = defaultdict(int)
        self.error_counts: Dict[str, int] = defaultdict(int)
        self.alert_thresholds: Dict[str, float] = {}
        self.scaling_thresholds: Dict[str, Tuple[float, str]] = {}
        self.baselines: Dict[str, float] = {}

    async def _get_cache_manager(self) -> CacheManager:
        """Get or create cache manager."""
        if self.cache_manager is None:
            self.cache_manager = CacheManager(self.cache_config)
        return self.cache_manager

    async def _get_pool_manager(self) -> ConnectionPoolManager:
        """Get or create pool manager."""
        if self.pool_manager is None:
            self.pool_manager = ConnectionPoolManager(self.pool_config)
            await self.pool_manager.initialize()
        return self.pool_manager

    async def _get_cdn_manager(self) -> CDNManager:
        """Get or create CDN manager."""
        if self.cdn_manager is None:
            self.cdn_manager = CDNManager(self.cdn_config)
        return self.cdn_manager

    async def collect_cache_metrics(self) -> PerformanceMetrics:
        """Collect cache performance metrics."""
        try:
            cache_manager = await self._get_cache_manager()
            return await cache_manager.get_performance_metrics()
        except Exception:
            return PerformanceMetrics(
                cache_hit_ratio=0.0,
                cache_miss_ratio=1.0,
                avg_response_time_ms=0.0,
                p95_response_time_ms=0.0,
                p99_response_time_ms=0.0,
                total_requests=0,
                error_rate=1.0,
                memory_usage_mb=0.0,
                cpu_usage_percent=0.0,
                active_connections=0,
                pool_utilization=0.0,
                cdn_hit_ratio=0.0,
            )

    async def collect_database_metrics(self) -> PerformanceMetrics:
        """Collect database connection pool metrics."""
        try:
            pool_manager = await self._get_pool_manager()
            stats = await pool_manager.get_statistics()

            return PerformanceMetrics(
                cache_hit_ratio=0.0,
                cache_miss_ratio=0.0,
                avg_response_time_ms=stats.avg_connection_time_ms,
                p95_response_time_ms=0.0,
                p99_response_time_ms=0.0,
                total_requests=0,
                error_rate=0.0,
                memory_usage_mb=0.0,
                cpu_usage_percent=0.0,
                active_connections=stats.active_connections,
                pool_utilization=stats.pool_utilization,
                cdn_hit_ratio=0.0,
            )
        except Exception:
            return PerformanceMetrics(
                cache_hit_ratio=0.0,
                cache_miss_ratio=0.0,
                avg_response_time_ms=0.0,
                p95_response_time_ms=0.0,
                p99_response_time_ms=0.0,
                total_requests=0,
                error_rate=0.0,
                memory_usage_mb=0.0,
                cpu_usage_percent=0.0,
                active_connections=0,
                pool_utilization=0.0,
                cdn_hit_ratio=0.0,
            )

    async def collect_system_metrics(self) -> PerformanceMetrics:
        """Collect system resource metrics."""
        try:
            # Try to import psutil for system metrics
            try:
                import psutil

                cpu_percent = psutil.cpu_percent()
                memory = psutil.virtual_memory()
                memory_mb = memory.used / (1024 * 1024)
            except ImportError:
                # Fallback values if psutil not available
                cpu_percent = 0.0
                memory_mb = 0.0

            return PerformanceMetrics(
                cache_hit_ratio=0.0,
                cache_miss_ratio=0.0,
                avg_response_time_ms=0.0,
                p95_response_time_ms=0.0,
                p99_response_time_ms=0.0,
                total_requests=0,
                error_rate=0.0,
                memory_usage_mb=memory_mb,
                cpu_usage_percent=cpu_percent,
                active_connections=0,
                pool_utilization=0.0,
                cdn_hit_ratio=0.0,
            )
        except Exception:
            return PerformanceMetrics(
                cache_hit_ratio=0.0,
                cache_miss_ratio=0.0,
                avg_response_time_ms=0.0,
                p95_response_time_ms=0.0,
                p99_response_time_ms=0.0,
                total_requests=0,
                error_rate=0.0,
                memory_usage_mb=0.0,
                cpu_usage_percent=0.0,
                active_connections=0,
                pool_utilization=0.0,
                cdn_hit_ratio=0.0,
            )

    async def record_response_time(self, endpoint: str, response_time_ms: float):
        """Record response time for an endpoint."""
        self.response_times[endpoint].append(response_time_ms)
        # Keep only recent response times
        if len(self.response_times[endpoint]) > 1000:
            self.response_times[endpoint] = self.response_times[endpoint][-1000:]

        await self.metrics_collector.record_histogram(
            f"response_time_{endpoint}", response_time_ms
        )

    async def record_request(self, endpoint: str, success: bool):
        """Record request outcome."""
        self.request_counts[endpoint] += 1
        if not success:
            self.error_counts[endpoint] += 1

        await self.metrics_collector.increment_counter(
            "requests_total", {"endpoint": endpoint}
        )
        if not success:
            await self.metrics_collector.increment_counter(
                "errors_total", {"endpoint": endpoint}
            )

    async def get_response_time_metrics(self) -> PerformanceMetrics:
        """Get response time metrics."""
        all_times = []
        for times in self.response_times.values():
            all_times.extend(times)

        if not all_times:
            return PerformanceMetrics(
                cache_hit_ratio=0.0,
                cache_miss_ratio=0.0,
                avg_response_time_ms=0.0,
                p95_response_time_ms=0.0,
                p99_response_time_ms=0.0,
                total_requests=0,
                error_rate=0.0,
                memory_usage_mb=0.0,
                cpu_usage_percent=0.0,
                active_connections=0,
                pool_utilization=0.0,
                cdn_hit_ratio=0.0,
            )

        avg_time = statistics.mean(all_times)
        p95_time = (
            statistics.quantiles(all_times, n=20)[18]
            if len(all_times) >= 20
            else max(all_times)
        )
        p99_time = (
            statistics.quantiles(all_times, n=100)[98]
            if len(all_times) >= 100
            else max(all_times)
        )

        return PerformanceMetrics(
            cache_hit_ratio=0.0,
            cache_miss_ratio=0.0,
            avg_response_time_ms=avg_time,
            p95_response_time_ms=p95_time,
            p99_response_time_ms=p99_time,
            total_requests=len(all_times),
            error_rate=0.0,
            memory_usage_mb=0.0,
            cpu_usage_percent=0.0,
            active_connections=0,
            pool_utilization=0.0,
            cdn_hit_ratio=0.0,
        )

    async def get_error_rate_metrics(self) -> PerformanceMetrics:
        """Get error rate metrics."""
        total_requests = sum(self.request_counts.values())
        total_errors = sum(self.error_counts.values())

        error_rate = total_errors / total_requests if total_requests > 0 else 0.0

        return PerformanceMetrics(
            cache_hit_ratio=0.0,
            cache_miss_ratio=0.0,
            avg_response_time_ms=0.0,
            p95_response_time_ms=0.0,
            p99_response_time_ms=0.0,
            total_requests=total_requests,
            error_rate=error_rate,
            memory_usage_mb=0.0,
            cpu_usage_percent=0.0,
            active_connections=0,
            pool_utilization=0.0,
            cdn_hit_ratio=0.0,
        )

    async def get_aggregated_metrics(self) -> PerformanceMetrics:
        """Get aggregated performance metrics."""
        cache_metrics = await self.collect_cache_metrics()
        db_metrics = await self.collect_database_metrics()
        system_metrics = await self.collect_system_metrics()
        response_metrics = await self.get_response_time_metrics()
        error_metrics = await self.get_error_rate_metrics()

        return PerformanceMetrics(
            cache_hit_ratio=cache_metrics.cache_hit_ratio,
            cache_miss_ratio=cache_metrics.cache_miss_ratio,
            avg_response_time_ms=response_metrics.avg_response_time_ms,
            p95_response_time_ms=response_metrics.p95_response_time_ms,
            p99_response_time_ms=response_metrics.p99_response_time_ms,
            total_requests=error_metrics.total_requests,
            error_rate=error_metrics.error_rate,
            memory_usage_mb=system_metrics.memory_usage_mb,
            cpu_usage_percent=system_metrics.cpu_usage_percent,
            active_connections=db_metrics.active_connections,
            pool_utilization=db_metrics.pool_utilization,
            cdn_hit_ratio=0.0,
        )

    async def set_alert_threshold(self, metric: str, threshold: float):
        """Set alert threshold for a metric."""
        self.alert_thresholds[metric] = threshold

    async def check_alerts(self) -> List[Alert]:
        """Check for performance alerts."""
        alerts = []
        metrics = await self.get_aggregated_metrics()

        # Check response time alerts
        if "response_time_p95" in self.alert_thresholds:
            threshold = self.alert_thresholds["response_time_p95"]
            if metrics.p95_response_time_ms > threshold:
                alerts.append(
                    Alert(
                        metric="response_time_p95",
                        threshold=threshold,
                        current_value=metrics.p95_response_time_ms,
                        severity="warning",
                        message=f"95th percentile response time ({metrics.p95_response_time_ms:.2f}ms) exceeds threshold ({threshold}ms)",
                    )
                )

        # Check error rate alerts
        if "error_rate" in self.alert_thresholds:
            threshold = self.alert_thresholds["error_rate"]
            if metrics.error_rate > threshold:
                alerts.append(
                    Alert(
                        metric="error_rate",
                        threshold=threshold,
                        current_value=metrics.error_rate,
                        severity="critical",
                        message=f"Error rate ({metrics.error_rate:.2%}) exceeds threshold ({threshold:.2%})",
                    )
                )

        return alerts

    async def get_metrics_time_series(
        self, metric: str, minutes: int = 60
    ) -> List[MetricPoint]:
        """Get time series data for a metric."""
        cutoff_time = datetime.utcnow() - timedelta(minutes=minutes)

        return [
            point
            for point in self.metrics_collector.metrics_buffer
            if point.name == metric and point.timestamp >= cutoff_time
        ]

    async def get_dashboard_data(self) -> Dict[str, Any]:
        """Get data for performance dashboard."""
        metrics = await self.get_aggregated_metrics()

        return {
            "cache_metrics": {
                "hit_ratio": metrics.cache_hit_ratio,
                "miss_ratio": metrics.cache_miss_ratio,
                "memory_usage_mb": metrics.memory_usage_mb,
            },
            "response_time_metrics": {
                "avg_ms": metrics.avg_response_time_ms,
                "p95_ms": metrics.p95_response_time_ms,
                "p99_ms": metrics.p99_response_time_ms,
            },
            "error_rate_metrics": {
                "error_rate": metrics.error_rate,
                "total_requests": metrics.total_requests,
            },
            "system_metrics": {
                "cpu_usage_percent": metrics.cpu_usage_percent,
                "memory_usage_mb": metrics.memory_usage_mb,
            },
            "database_metrics": {
                "active_connections": metrics.active_connections,
                "pool_utilization": metrics.pool_utilization,
            },
        }

    async def warm_cache(self, keys: List[str]) -> CacheWarmingResult:
        """Warm cache with specified keys."""
        start_time = time.time()
        warmed_keys = 0
        failed_keys = 0

        try:
            cache_manager = await self._get_cache_manager()

            for key in keys:
                try:
                    # In a real implementation, this would fetch data and cache it
                    # For now, just simulate cache warming
                    await cache_manager.set(key, f"warmed_value_{key}", ttl=3600)
                    warmed_keys += 1
                except Exception:
                    failed_keys += 1

            total_time = (time.time() - start_time) * 1000

            return CacheWarmingResult(
                success=failed_keys == 0,
                warmed_keys=warmed_keys,
                failed_keys=failed_keys,
                total_time_ms=total_time,
            )
        except Exception:
            return CacheWarmingResult(
                success=False,
                warmed_keys=0,
                failed_keys=len(keys),
                total_time_ms=(time.time() - start_time) * 1000,
            )

    async def record_pool_utilization(self, utilization: float):
        """Record pool utilization for testing."""
        await self.metrics_collector.record_metric("pool_utilization", utilization)

    async def get_optimization_recommendations(
        self,
    ) -> List[OptimizationRecommendation]:
        """Get performance optimization recommendations."""
        recommendations = []
        metrics = await self.get_aggregated_metrics()

        # Check pool utilization
        if metrics.pool_utilization > 0.9:
            recommendations.append(
                OptimizationRecommendation(
                    category="connection_pool",
                    recommendation="Increase maximum connection pool size",
                    impact="High",
                    priority="High",
                )
            )

        # Check cache hit ratio
        if metrics.cache_hit_ratio < 0.8:
            recommendations.append(
                OptimizationRecommendation(
                    category="cache",
                    recommendation="Optimize cache strategy and increase TTL for frequently accessed data",
                    impact="Medium",
                    priority="Medium",
                )
            )

        return recommendations

    async def establish_baseline(self, endpoint: str):
        """Establish performance baseline for an endpoint."""
        if endpoint in self.response_times and self.response_times[endpoint]:
            self.baselines[endpoint] = statistics.mean(self.response_times[endpoint])

    async def detect_regressions(self) -> List[Regression]:
        """Detect performance regressions."""
        regressions = []

        for endpoint, times in self.response_times.items():
            if endpoint in self.baselines and times:
                baseline = self.baselines[endpoint]
                current_avg = statistics.mean(times[-100:])  # Last 100 requests

                if current_avg > baseline * 1.5:  # 50% degradation threshold
                    degradation = ((current_avg - baseline) / baseline) * 100
                    regressions.append(
                        Regression(
                            endpoint=endpoint,
                            metric="response_time",
                            baseline_value=baseline,
                            current_value=current_avg,
                            degradation_percent=degradation,
                        )
                    )

        return regressions

    async def set_scaling_threshold(self, metric: str, threshold: float, action: str):
        """Set auto-scaling threshold."""
        self.scaling_thresholds[metric] = (threshold, action)

    async def evaluate_scaling(self) -> List[ScalingDecision]:
        """Evaluate auto-scaling decisions."""
        decisions = []
        metrics = await self.get_aggregated_metrics()

        # Check CPU usage
        if "cpu_usage" in self.scaling_thresholds:
            threshold, action = self.scaling_thresholds["cpu_usage"]
            if metrics.cpu_usage_percent > threshold:
                decisions.append(
                    ScalingDecision(
                        action=action,
                        reason=f"CPU usage ({metrics.cpu_usage_percent:.1f}%) exceeds threshold ({threshold}%)",
                        metric_triggers=["cpu_usage"],
                    )
                )

        # Check response time
        if "response_time_p95" in self.scaling_thresholds:
            threshold, action = self.scaling_thresholds["response_time_p95"]
            if metrics.p95_response_time_ms > threshold:
                decisions.append(
                    ScalingDecision(
                        action=action,
                        reason=f"95th percentile response time ({metrics.p95_response_time_ms:.2f}ms) exceeds threshold ({threshold}ms)",
                        metric_triggers=["response_time_p95"],
                    )
                )

        return decisions

    async def close(self):
        """Close all managers and cleanup resources."""
        if self.cache_manager:
            await self.cache_manager.close()
        if self.pool_manager:
            await self.pool_manager.close()
        if self.cdn_manager:
            await self.cdn_manager.close()
