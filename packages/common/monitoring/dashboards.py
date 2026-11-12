"""
Advanced monitoring dashboards and alerting system.

This module provides dashboard creation, widget management, and alerting
capabilities for the DesignSynapse infrastructure monitoring system.
"""

import asyncio
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Union

from packages.common.monitoring.metrics import get_metrics_collector


class AlertCondition(str, Enum):
    """Alert condition types."""

    GREATER_THAN = "greater_than"
    LESS_THAN = "less_than"
    EQUALS = "equals"
    NOT_EQUALS = "not_equals"
    GREATER_THAN_OR_EQUAL = "greater_than_or_equal"
    LESS_THAN_OR_EQUAL = "less_than_or_equal"


class AlertSeverity(str, Enum):
    """Alert severity levels."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AlertStatus(str, Enum):
    """Alert status states."""

    OK = "ok"
    PENDING = "pending"
    FIRING = "firing"
    RESOLVED = "resolved"


class WidgetType(str, Enum):
    """Dashboard widget types."""

    LINE_CHART = "line_chart"
    BAR_CHART = "bar_chart"
    PIE_CHART = "pie_chart"
    GAUGE = "gauge"
    COUNTER = "counter"
    TABLE = "table"
    HEATMAP = "heatmap"


@dataclass
class MetricQuery:
    """Query configuration for dashboard widgets."""

    metric_name: str
    aggregation: str = "avg"  # avg, sum, min, max, count
    time_range_minutes: int = 60
    group_by: Optional[str] = None
    filters: Dict[str, str] = field(default_factory=dict)

    def validate(self) -> bool:
        """Validate query configuration."""
        if not self.metric_name or not self.metric_name.strip():
            return False
        if self.aggregation not in ["avg", "sum", "min", "max", "count"]:
            return False
        if self.time_range_minutes <= 0:
            return False
        return True


@dataclass
class DashboardWidget:
    """Dashboard widget configuration."""

    title: str
    widget_type: WidgetType
    query: MetricQuery
    position_x: int = 0
    position_y: int = 0
    width: int = 6
    height: int = 4
    widget_id: str = field(default_factory=lambda: str(uuid.uuid4()))

    def format_data(self, data_points: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Format data points for the specific widget type."""
        if not data_points:
            return {"labels": [], "values": []}

        if self.widget_type == WidgetType.LINE_CHART:
            return {
                "labels": [point["timestamp"].isoformat() for point in data_points],
                "values": [point["value"] for point in data_points],
            }
        elif self.widget_type == WidgetType.BAR_CHART:
            return {
                "categories": [
                    point.get("category", "Unknown") for point in data_points
                ],
                "series": [
                    {"name": "Value", "data": [point["value"] for point in data_points]}
                ],
            }
        elif self.widget_type == WidgetType.PIE_CHART:
            return {
                "series": [
                    {"name": point.get("category", "Unknown"), "value": point["value"]}
                    for point in data_points
                ]
            }
        elif self.widget_type == WidgetType.GAUGE:
            latest_value = data_points[-1]["value"] if data_points else 0
            return {"value": latest_value, "min": 0, "max": 100}
        elif self.widget_type == WidgetType.COUNTER:
            latest_value = data_points[-1]["value"] if data_points else 0
            return {
                "value": latest_value,
                "change": 0,  # Could calculate change from previous value
            }
        else:
            # Default format
            return {
                "labels": [point["timestamp"].isoformat() for point in data_points],
                "values": [point["value"] for point in data_points],
            }


@dataclass
class AlertRule:
    """Alert rule configuration."""

    name: str
    condition: AlertCondition
    threshold: float
    metric_name: str
    description: str = ""
    severity: AlertSeverity = AlertSeverity.WARNING
    duration_minutes: int = 5
    enabled: bool = True
    status: AlertStatus = AlertStatus.OK
    rule_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_evaluated: Optional[datetime] = None

    def evaluate_condition(self, value: float) -> bool:
        """Evaluate if the condition is met."""
        if self.condition == AlertCondition.GREATER_THAN:
            return value > self.threshold
        elif self.condition == AlertCondition.LESS_THAN:
            return value < self.threshold
        elif self.condition == AlertCondition.EQUALS:
            return value == self.threshold
        elif self.condition == AlertCondition.NOT_EQUALS:
            return value != self.threshold
        elif self.condition == AlertCondition.GREATER_THAN_OR_EQUAL:
            return value >= self.threshold
        elif self.condition == AlertCondition.LESS_THAN_OR_EQUAL:
            return value <= self.threshold
        return False

    def validate(self) -> bool:
        """Validate alert rule configuration."""
        if not self.name or not self.name.strip():
            return False
        if not self.metric_name or not self.metric_name.strip():
            return False
        if not isinstance(self.threshold, (int, float)) or not self._is_finite(
            self.threshold
        ):
            return False
        if self.duration_minutes <= 0:
            return False
        return True

    def _is_finite(self, value: float) -> bool:
        """Check if value is finite (not inf or nan)."""
        import math

        return math.isfinite(value)


@dataclass
class Alert:
    """Active alert instance."""

    rule_name: str
    rule_id: str
    severity: AlertSeverity
    message: str
    metric_name: str
    current_value: float
    threshold: float
    status: AlertStatus = AlertStatus.FIRING
    triggered_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    resolved_at: Optional[datetime] = None
    alert_id: str = field(default_factory=lambda: str(uuid.uuid4()))


@dataclass
class Dashboard:
    """Dashboard configuration."""

    dashboard_id: str
    name: str
    title: str
    widgets: List[DashboardWidget] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class NotificationHandler(ABC):
    """Abstract base class for alert notification handlers."""

    @abstractmethod
    async def send_alert(self, alert: Alert) -> bool:
        """Send alert notification."""
        pass


class EmailNotificationHandler(NotificationHandler):
    """Email notification handler."""

    def __init__(self, smtp_config: Dict[str, Any]):
        self.smtp_config = smtp_config

    async def send_alert(self, alert: Alert) -> bool:
        """Send alert via email."""
        # Placeholder implementation
        print(f"EMAIL ALERT: {alert.severity.upper()} - {alert.message}")
        return True


class SlackNotificationHandler(NotificationHandler):
    """Slack notification handler."""

    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url

    async def send_alert(self, alert: Alert) -> bool:
        """Send alert via Slack."""
        # Placeholder implementation
        print(f"SLACK ALERT: {alert.severity.upper()} - {alert.message}")
        return True


class AlertManager:
    """Manages alert rules and evaluates conditions."""

    def __init__(self):
        self.rules: Dict[str, AlertRule] = {}
        self.active_alerts: Dict[str, Alert] = {}
        self.notification_handlers: List[NotificationHandler] = []
        self.metrics_collector = get_metrics_collector()

    def add_alert_rule(self, rule: AlertRule) -> bool:
        """Add an alert rule."""
        if not rule.validate():
            return False

        self.rules[rule.rule_id] = rule
        return True

    def remove_alert_rule(self, rule_id: str) -> bool:
        """Remove an alert rule."""
        if rule_id in self.rules:
            del self.rules[rule_id]
            return True
        return False

    def evaluate_rules(self, metrics: Dict[str, float]) -> List[Alert]:
        """Evaluate all alert rules against current metrics."""
        new_alerts = []
        current_time = datetime.now(timezone.utc)

        for rule in self.rules.values():
            if not rule.enabled:
                continue

            rule.last_evaluated = current_time

            if rule.metric_name not in metrics:
                continue

            current_value = metrics[rule.metric_name]
            should_alert = rule.evaluate_condition(current_value)

            if should_alert:
                # Check if alert already exists
                existing_alert = None
                for alert in self.active_alerts.values():
                    if alert.rule_id == rule.rule_id:
                        existing_alert = alert
                        break

                if not existing_alert:
                    # Create new alert
                    alert = Alert(
                        rule_name=rule.name,
                        rule_id=rule.rule_id,
                        severity=rule.severity,
                        message=f"{rule.name}: {rule.metric_name} is {current_value} (threshold: {rule.threshold})",
                        metric_name=rule.metric_name,
                        current_value=current_value,
                        threshold=rule.threshold,
                        status=AlertStatus.FIRING,
                    )

                    self.active_alerts[alert.alert_id] = alert
                    new_alerts.append(alert)

                    # Send notifications (simplified for testing)
                    try:
                        loop = asyncio.get_running_loop()
                        asyncio.create_task(self.send_notifications(alert))
                    except RuntimeError:
                        # No event loop running, skip async notifications for now
                        pass
            else:
                # Resolve any existing alerts for this rule
                alerts_to_resolve = []
                for alert_id, alert in self.active_alerts.items():
                    if (
                        alert.rule_id == rule.rule_id
                        and alert.status == AlertStatus.FIRING
                    ):
                        alert.status = AlertStatus.RESOLVED
                        alert.resolved_at = current_time
                        alerts_to_resolve.append(alert_id)

                # Remove resolved alerts
                for alert_id in alerts_to_resolve:
                    del self.active_alerts[alert_id]

        return new_alerts

    def get_active_alerts(self) -> List[Alert]:
        """Get all currently active alerts."""
        return [
            alert
            for alert in self.active_alerts.values()
            if alert.status == AlertStatus.FIRING
        ]

    def add_notification_handler(self, handler: NotificationHandler) -> None:
        """Add a notification handler."""
        self.notification_handlers.append(handler)

    async def send_notifications(self, alert: Alert) -> None:
        """Send notifications for an alert."""
        for handler in self.notification_handlers:
            try:
                await handler.send_alert(alert)
            except Exception as e:
                print(f"Failed to send notification via {type(handler).__name__}: {e}")


class DashboardManager:
    """Manages dashboards and widgets."""

    def __init__(self):
        self.dashboards: Dict[str, Dashboard] = {}
        self.metrics_collector = get_metrics_collector()

    def create_dashboard(self, name: str, title: str) -> str:
        """Create a new dashboard."""
        dashboard_id = str(uuid.uuid4())
        dashboard = Dashboard(dashboard_id=dashboard_id, name=name, title=title)
        self.dashboards[dashboard_id] = dashboard
        return dashboard_id

    def delete_dashboard(self, dashboard_id: str) -> bool:
        """Delete a dashboard."""
        if dashboard_id in self.dashboards:
            del self.dashboards[dashboard_id]
            return True
        return False

    def add_widget(self, dashboard_id: str, widget: DashboardWidget) -> bool:
        """Add a widget to a dashboard."""
        if dashboard_id not in self.dashboards:
            return False

        if not widget.query.validate():
            return False

        dashboard = self.dashboards[dashboard_id]
        dashboard.widgets.append(widget)
        dashboard.updated_at = datetime.now(timezone.utc)
        return True

    def remove_widget(self, dashboard_id: str, widget_id: str) -> bool:
        """Remove a widget from a dashboard."""
        if dashboard_id not in self.dashboards:
            return False

        dashboard = self.dashboards[dashboard_id]
        original_count = len(dashboard.widgets)
        dashboard.widgets = [w for w in dashboard.widgets if w.widget_id != widget_id]

        if len(dashboard.widgets) < original_count:
            dashboard.updated_at = datetime.now(timezone.utc)
            return True
        return False

    def get_dashboard_data(self, dashboard_id: str) -> Optional[Dict[str, Any]]:
        """Get dashboard data with widget data."""
        if dashboard_id not in self.dashboards:
            return None

        dashboard = self.dashboards[dashboard_id]

        widgets_data = []
        for widget in dashboard.widgets:
            widget_data = self.get_widget_data(widget)
            widgets_data.append(
                {
                    "widget_id": widget.widget_id,
                    "title": widget.title,
                    "type": widget.widget_type.value,
                    "position": {"x": widget.position_x, "y": widget.position_y},
                    "size": {"width": widget.width, "height": widget.height},
                    "data": widget_data,
                }
            )

        return {
            "dashboard_id": dashboard.dashboard_id,
            "name": dashboard.name,
            "title": dashboard.title,
            "widgets": widgets_data,
            "created_at": dashboard.created_at.isoformat(),
            "updated_at": dashboard.updated_at.isoformat(),
        }

    def get_real_time_metrics(
        self, metric_names: List[str]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Get real-time metrics data."""
        result = {}

        for metric_name in metric_names:
            # Get recent data points (mock implementation)
            data_points = self._get_metric_data_points(
                metric_name, 60
            )  # Last 60 minutes
            result[metric_name] = data_points

        return result

    def get_widget_data(self, widget: DashboardWidget) -> Dict[str, Any]:
        """Get data for a specific widget."""
        # Get data points based on widget query
        data_points = self._get_metric_data_points(
            widget.query.metric_name, widget.query.time_range_minutes
        )

        # Format data according to widget type
        return widget.format_data(data_points)

    def _get_metric_data_points(
        self, metric_name: str, time_range_minutes: int
    ) -> List[Dict[str, Any]]:
        """Get metric data points (mock implementation)."""
        # This is a simplified implementation
        # In a real system, this would query the metrics collector
        import random

        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(minutes=time_range_minutes)

        # Generate mock data points
        data_points = []
        current_time = start_time
        interval_minutes = max(1, time_range_minutes // 60)  # At most 60 data points

        while current_time <= end_time:
            data_points.append(
                {
                    "timestamp": current_time,
                    "value": random.uniform(0, 100),  # Mock value
                    "category": f"category_{len(data_points) % 5}",  # For grouped data
                }
            )
            current_time += timedelta(minutes=interval_minutes)

        return data_points


# Global instances
_alert_manager: Optional[AlertManager] = None
_dashboard_manager: Optional[DashboardManager] = None


def get_alert_manager() -> AlertManager:
    """Get or create the global alert manager instance."""
    global _alert_manager
    if _alert_manager is None:
        _alert_manager = AlertManager()
    return _alert_manager


def get_dashboard_manager() -> DashboardManager:
    """Get or create the global dashboard manager instance."""
    global _dashboard_manager
    if _dashboard_manager is None:
        _dashboard_manager = DashboardManager()
    return _dashboard_manager


def set_alert_manager(manager: AlertManager) -> None:
    """Set the global alert manager instance."""
    global _alert_manager
    _alert_manager = manager


def set_dashboard_manager(manager: DashboardManager) -> None:
    """Set the global dashboard manager instance."""
    global _dashboard_manager
    _dashboard_manager = manager
