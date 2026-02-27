"""
Common monitoring package for DesignSynapse infrastructure.

This package provides centralized logging, metrics collection, and health check aggregation
for all services in the DesignSynapse ecosystem.
"""

from packages.common.monitoring.dashboards import (Alert, AlertCondition,
                                                   AlertManager, AlertRule,
                                                   AlertSeverity, Dashboard,
                                                   DashboardManager,
                                                   DashboardWidget,
                                                   MetricQuery, WidgetType,
                                                   get_alert_manager,
                                                   get_dashboard_manager)
from packages.common.monitoring.health import (HealthAggregator,
                                               SystemHealthStatus,
                                               get_health_aggregator)
from packages.common.monitoring.log_aggregator import (LogAggregator,
                                                       StructuredLogger,
                                                       get_log_aggregator,
                                                       get_logger)
from packages.common.monitoring.metrics import (MetricPoint, MetricsCollector,
                                                get_metrics_collector)
from packages.common.monitoring.tracing import (Span, SpanKind, SpanStatus,
                                                Trace, TracingCollector,
                                                get_tracing_collector,
                                                set_tracing_collector)

__all__ = [
    "LogAggregator",
    "StructuredLogger",
    "get_logger",
    "get_log_aggregator",
    "MetricsCollector",
    "MetricPoint",
    "get_metrics_collector",
    "HealthAggregator",
    "SystemHealthStatus",
    "get_health_aggregator",
    "TracingCollector",
    "Span",
    "Trace",
    "SpanStatus",
    "SpanKind",
    "get_tracing_collector",
    "set_tracing_collector",
    "DashboardManager",
    "AlertManager",
    "AlertRule",
    "AlertCondition",
    "AlertSeverity",
    "DashboardWidget",
    "WidgetType",
    "MetricQuery",
    "Alert",
    "Dashboard",
    "get_dashboard_manager",
    "get_alert_manager",
]
