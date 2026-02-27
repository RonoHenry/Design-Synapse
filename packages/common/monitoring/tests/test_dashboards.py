"""
Tests for monitoring dashboards and alerting functionality.

Following TDD approach - these tests define the expected behavior
and will initially fail until implementation is complete.
"""

import asyncio
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List
from unittest.mock import AsyncMock, Mock, patch

import pytest

from packages.common.monitoring.dashboards import (AlertCondition,
                                                   AlertManager, AlertRule,
                                                   AlertSeverity, AlertStatus,
                                                   DashboardManager,
                                                   DashboardWidget,
                                                   MetricQuery, WidgetType)


class TestAlertRule:
    """Test cases for AlertRule model."""

    def test_alert_rule_creation(self):
        """Test basic alert rule creation."""
        rule = AlertRule(
            name="high_error_rate",
            description="Alert when error rate exceeds threshold",
            condition=AlertCondition.GREATER_THAN,
            threshold=0.05,
            metric_name="error_rate",
            severity=AlertSeverity.WARNING,
            duration_minutes=5,
        )

        assert rule.name == "high_error_rate"
        assert rule.condition == AlertCondition.GREATER_THAN
        assert rule.threshold == 0.05
        assert rule.severity == AlertSeverity.WARNING
        assert rule.enabled is True
        assert rule.status == AlertStatus.OK

    def test_alert_rule_evaluation(self):
        """Test alert rule evaluation logic."""
        rule = AlertRule(
            name="cpu_usage",
            condition=AlertCondition.GREATER_THAN,
            threshold=80.0,
            metric_name="cpu_usage_percent",
        )

        # Should trigger alert
        assert rule.evaluate_condition(85.0) is True
        assert rule.evaluate_condition(80.1) is True

        # Should not trigger alert
        assert rule.evaluate_condition(75.0) is False
        assert rule.evaluate_condition(80.0) is False

    def test_alert_rule_different_conditions(self):
        """Test different alert conditions."""
        # Less than condition
        rule_lt = AlertRule(
            name="low_memory",
            condition=AlertCondition.LESS_THAN,
            threshold=20.0,
            metric_name="memory_available_percent",
        )
        assert rule_lt.evaluate_condition(15.0) is True
        assert rule_lt.evaluate_condition(25.0) is False

        # Equals condition
        rule_eq = AlertRule(
            name="exact_count",
            condition=AlertCondition.EQUALS,
            threshold=0.0,
            metric_name="active_connections",
        )
        assert rule_eq.evaluate_condition(0.0) is True
        assert rule_eq.evaluate_condition(1.0) is False


class TestDashboardWidget:
    """Test cases for DashboardWidget model."""

    def test_widget_creation(self):
        """Test basic widget creation."""
        query = MetricQuery(
            metric_name="request_count", aggregation="sum", time_range_minutes=60
        )

        widget = DashboardWidget(
            title="Request Count",
            widget_type=WidgetType.LINE_CHART,
            query=query,
            position_x=0,
            position_y=0,
            width=6,
            height=4,
        )

        assert widget.title == "Request Count"
        assert widget.widget_type == WidgetType.LINE_CHART
        assert widget.query.metric_name == "request_count"
        assert widget.width == 6
        assert widget.height == 4

    def test_widget_data_formatting(self):
        """Test widget data formatting for different chart types."""
        query = MetricQuery(
            metric_name="response_time", aggregation="avg", time_range_minutes=30
        )

        widget = DashboardWidget(
            title="Response Time", widget_type=WidgetType.LINE_CHART, query=query
        )

        # Mock data points
        data_points = [
            {"timestamp": datetime.now(timezone.utc), "value": 150.0},
            {"timestamp": datetime.now(timezone.utc), "value": 200.0},
            {"timestamp": datetime.now(timezone.utc), "value": 175.0},
        ]

        formatted_data = widget.format_data(data_points)

        assert "labels" in formatted_data
        assert "values" in formatted_data
        assert len(formatted_data["values"]) == 3
        assert formatted_data["values"] == [150.0, 200.0, 175.0]


class TestAlertManager:
    """Test cases for AlertManager."""

    def test_alert_manager_initialization(self):
        """Test alert manager initialization."""
        manager = AlertManager()

        assert len(manager.rules) == 0
        assert len(manager.active_alerts) == 0
        assert manager.notification_handlers == []

    def test_add_alert_rule(self):
        """Test adding alert rules."""
        manager = AlertManager()

        rule = AlertRule(
            name="test_rule",
            condition=AlertCondition.GREATER_THAN,
            threshold=100.0,
            metric_name="test_metric",
        )

        result = manager.add_alert_rule(rule)
        assert result is True
        assert rule.rule_id in manager.rules
        assert manager.rules[rule.rule_id] == rule

    def test_add_invalid_alert_rule(self):
        """Test adding invalid alert rule."""
        manager = AlertManager()

        invalid_rule = AlertRule(
            name="",  # Invalid empty name
            condition=AlertCondition.GREATER_THAN,
            threshold=100.0,
            metric_name="test_metric",
        )

        result = manager.add_alert_rule(invalid_rule)
        assert result is False
        assert len(manager.rules) == 0

    def test_evaluate_rules(self):
        """Test evaluating alert rules."""
        manager = AlertManager()

        rule = AlertRule(
            name="high_cpu",
            condition=AlertCondition.GREATER_THAN,
            threshold=80.0,
            metric_name="cpu_usage",
        )
        manager.add_alert_rule(rule)

        # Test with normal metrics - no alerts
        metrics = {"cpu_usage": 70.0}
        alerts = manager.evaluate_rules(metrics)
        assert len(alerts) == 0

        # Test with high CPU - should trigger alert
        metrics = {"cpu_usage": 90.0}
        alerts = manager.evaluate_rules(metrics)
        assert len(alerts) == 1
        assert alerts[0].rule_name == "high_cpu"
        assert alerts[0].current_value == 90.0

    def test_get_active_alerts(self):
        """Test getting active alerts."""
        manager = AlertManager()

        rule = AlertRule(
            name="memory_usage",
            condition=AlertCondition.GREATER_THAN,
            threshold=85.0,
            metric_name="memory_usage",
        )
        manager.add_alert_rule(rule)

        # No active alerts initially
        active_alerts = manager.get_active_alerts()
        assert len(active_alerts) == 0

        # Trigger alert
        metrics = {"memory_usage": 95.0}
        manager.evaluate_rules(metrics)

        active_alerts = manager.get_active_alerts()
        assert len(active_alerts) == 1
        assert active_alerts[0].rule_name == "memory_usage"

    def test_add_notification_handler(self):
        """Test adding notification handlers."""
        manager = AlertManager()

        handler = Mock()
        manager.add_notification_handler(handler)

        assert len(manager.notification_handlers) == 1
        assert manager.notification_handlers[0] == handler


class TestDashboardManager:
    """Test cases for DashboardManager."""

    def test_dashboard_manager_initialization(self):
        """Test dashboard manager initialization."""
        manager = DashboardManager()

        assert len(manager.dashboards) == 0
        assert manager.metrics_collector is not None

    def test_create_dashboard(self):
        """Test creating dashboards."""
        manager = DashboardManager()

        dashboard_id = manager.create_dashboard("test_dashboard", "Test Dashboard")

        assert dashboard_id is not None
        assert dashboard_id in manager.dashboards

        dashboard = manager.dashboards[dashboard_id]
        assert dashboard.name == "test_dashboard"
        assert dashboard.title == "Test Dashboard"
        assert len(dashboard.widgets) == 0

    def test_add_widget(self):
        """Test adding widgets to dashboard."""
        manager = DashboardManager()

        dashboard_id = manager.create_dashboard("test_dashboard", "Test Dashboard")

        query = MetricQuery(
            metric_name="test_metric", aggregation="avg", time_range_minutes=60
        )

        widget = DashboardWidget(
            title="Test Widget", widget_type=WidgetType.LINE_CHART, query=query
        )

        result = manager.add_widget(dashboard_id, widget)
        assert result is True

        dashboard = manager.dashboards[dashboard_id]
        assert len(dashboard.widgets) == 1
        assert dashboard.widgets[0].title == "Test Widget"

    def test_add_widget_invalid_dashboard(self):
        """Test adding widget to non-existent dashboard."""
        manager = DashboardManager()

        query = MetricQuery(
            metric_name="test_metric", aggregation="avg", time_range_minutes=60
        )

        widget = DashboardWidget(
            title="Test Widget", widget_type=WidgetType.LINE_CHART, query=query
        )

        result = manager.add_widget("non_existent", widget)
        assert result is False

    def test_get_dashboard_data(self):
        """Test getting dashboard data."""
        manager = DashboardManager()

        dashboard_id = manager.create_dashboard("test_dashboard", "Test Dashboard")

        query = MetricQuery(
            metric_name="cpu_usage", aggregation="avg", time_range_minutes=60
        )

        widget = DashboardWidget(
            title="CPU Usage", widget_type=WidgetType.LINE_CHART, query=query
        )

        manager.add_widget(dashboard_id, widget)

        dashboard_data = manager.get_dashboard_data(dashboard_id)

        assert dashboard_data is not None
        assert dashboard_data["name"] == "test_dashboard"
        assert dashboard_data["title"] == "Test Dashboard"
        assert len(dashboard_data["widgets"]) == 1
        assert dashboard_data["widgets"][0]["title"] == "CPU Usage"

    def test_get_dashboard_data_non_existent(self):
        """Test getting data for non-existent dashboard."""
        manager = DashboardManager()

        dashboard_data = manager.get_dashboard_data("non_existent")
        assert dashboard_data is None

    def test_get_real_time_metrics(self):
        """Test getting real-time metrics."""
        manager = DashboardManager()

        metrics = manager.get_real_time_metrics(["cpu_usage", "memory_usage"])

        assert "cpu_usage" in metrics
        assert "memory_usage" in metrics
        assert isinstance(metrics["cpu_usage"], list)
        assert isinstance(metrics["memory_usage"], list)


class TestAlertManagerIntegration:
    """Integration tests for alert manager - these will pass after GREEN phase."""

    def test_complete_alert_workflow(self):
        """Test complete alert creation and evaluation workflow."""
        manager = AlertManager()

        # Add alert rule
        rule = AlertRule(
            name="high_cpu",
            condition=AlertCondition.GREATER_THAN,
            threshold=80.0,
            metric_name="cpu_usage_percent",
            severity=AlertSeverity.CRITICAL,
        )
        manager.add_alert_rule(rule)

        # Evaluate with normal metrics
        metrics = {"cpu_usage_percent": 65.0}
        alerts = manager.evaluate_rules(metrics)
        assert len(alerts) == 0

        # Evaluate with high CPU
        metrics = {"cpu_usage_percent": 85.0}
        alerts = manager.evaluate_rules(metrics)
        assert len(alerts) == 1
        assert alerts[0].rule_name == "high_cpu"
        assert alerts[0].severity == AlertSeverity.CRITICAL

    @pytest.mark.asyncio
    async def test_alert_notification_workflow(self):
        """Test alert notification handling."""
        manager = AlertManager()

        # Mock notification handler
        notification_handler = AsyncMock()
        manager.add_notification_handler(notification_handler)

        # Add alert rule
        rule = AlertRule(
            name="error_rate",
            condition=AlertCondition.GREATER_THAN,
            threshold=0.05,
            metric_name="error_rate",
        )
        manager.add_alert_rule(rule)

        # Trigger alert
        metrics = {"error_rate": 0.08}
        manager.evaluate_rules(metrics)

        # Wait a bit for async notification
        await asyncio.sleep(0.1)

        # Verify notification was sent
        notification_handler.send_alert.assert_called_once()

    def test_alert_state_management(self):
        """Test alert state transitions."""
        manager = AlertManager()

        rule = AlertRule(
            name="memory_usage",
            condition=AlertCondition.GREATER_THAN,
            threshold=90.0,
            metric_name="memory_usage_percent",
        )
        manager.add_alert_rule(rule)

        # Trigger alert
        metrics = {"memory_usage_percent": 95.0}
        manager.evaluate_rules(metrics)

        active_alerts = manager.get_active_alerts()
        assert len(active_alerts) == 1
        assert active_alerts[0].status == AlertStatus.FIRING

        # Resolve alert
        metrics = {"memory_usage_percent": 85.0}
        manager.evaluate_rules(metrics)

        active_alerts = manager.get_active_alerts()
        assert len(active_alerts) == 0


class TestDashboardManagerIntegration:
    """Integration tests for dashboard manager - these will pass after GREEN phase."""

    def test_complete_dashboard_workflow(self):
        """Test complete dashboard creation and data retrieval workflow."""
        manager = DashboardManager()

        # Create dashboard
        dashboard_id = manager.create_dashboard("system_overview", "System Overview")
        assert dashboard_id is not None

        # Add widgets
        cpu_query = MetricQuery(
            metric_name="cpu_usage_percent", aggregation="avg", time_range_minutes=60
        )

        cpu_widget = DashboardWidget(
            title="CPU Usage",
            widget_type=WidgetType.LINE_CHART,
            query=cpu_query,
            position_x=0,
            position_y=0,
            width=6,
            height=4,
        )

        manager.add_widget(dashboard_id, cpu_widget)

        # Get dashboard data
        dashboard_data = manager.get_dashboard_data(dashboard_id)
        assert "widgets" in dashboard_data
        assert len(dashboard_data["widgets"]) == 1
        assert dashboard_data["widgets"][0]["title"] == "CPU Usage"

    def test_real_time_metrics_aggregation(self):
        """Test real-time metrics data aggregation."""
        manager = DashboardManager()

        # Mock metrics data
        with patch.object(manager, "_get_metric_data_points") as mock_get_data:
            mock_get_data.return_value = [
                {"timestamp": datetime.now(timezone.utc), "value": 75.0},
                {"timestamp": datetime.now(timezone.utc), "value": 80.0},
                {"timestamp": datetime.now(timezone.utc), "value": 78.0},
            ]

            metrics = manager.get_real_time_metrics(["cpu_usage_percent"])

            assert "cpu_usage_percent" in metrics
            assert len(metrics["cpu_usage_percent"]) == 3
            assert metrics["cpu_usage_percent"][1]["value"] == 80.0

    def test_dashboard_widget_data_formatting(self):
        """Test dashboard widget data formatting for different chart types."""
        manager = DashboardManager()

        dashboard_id = manager.create_dashboard("test_dashboard", "Test Dashboard")

        # Line chart widget
        line_query = MetricQuery(
            metric_name="response_time_ms", aggregation="avg", time_range_minutes=30
        )

        line_widget = DashboardWidget(
            title="Response Time", widget_type=WidgetType.LINE_CHART, query=line_query
        )

        manager.add_widget(dashboard_id, line_widget)

        # Bar chart widget
        bar_query = MetricQuery(
            metric_name="request_count",
            aggregation="sum",
            time_range_minutes=60,
            group_by="endpoint",
        )

        bar_widget = DashboardWidget(
            title="Requests by Endpoint",
            widget_type=WidgetType.BAR_CHART,
            query=bar_query,
        )

        manager.add_widget(dashboard_id, bar_widget)

        dashboard_data = manager.get_dashboard_data(dashboard_id)

        # Verify different data formats
        widgets = dashboard_data["widgets"]
        line_data = widgets[0]["data"]
        bar_data = widgets[1]["data"]

        assert "labels" in line_data and "values" in line_data
        assert "categories" in bar_data and "series" in bar_data


class TestPerformanceAndScaling:
    """Performance tests for dashboard and alerting systems."""

    def test_dashboard_performance_with_many_widgets(self):
        """Test dashboard performance with multiple widgets."""
        manager = DashboardManager()

        dashboard_id = manager.create_dashboard("performance_test", "Performance Test")

        # Add many widgets
        for i in range(50):
            query = MetricQuery(
                metric_name=f"metric_{i}", aggregation="avg", time_range_minutes=60
            )

            widget = DashboardWidget(
                title=f"Widget {i}",
                widget_type=WidgetType.LINE_CHART,
                query=query,
                position_x=i % 10,
                position_y=i // 10,
            )

            manager.add_widget(dashboard_id, widget)

        # Measure dashboard data retrieval time
        import time

        start_time = time.time()
        dashboard_data = manager.get_dashboard_data(dashboard_id)
        end_time = time.time()

        # Should complete within reasonable time
        assert (end_time - start_time) < 5.0  # 5 seconds max
        assert len(dashboard_data["widgets"]) == 50

    def test_alert_evaluation_performance(self):
        """Test alert evaluation performance with many rules."""
        manager = AlertManager()

        # Add many alert rules
        for i in range(100):
            rule = AlertRule(
                name=f"rule_{i}",
                condition=AlertCondition.GREATER_THAN,
                threshold=float(i),
                metric_name=f"metric_{i}",
            )
            manager.add_alert_rule(rule)

        # Prepare metrics data
        metrics = {f"metric_{i}": float(i + 50) for i in range(100)}

        # Measure evaluation time
        import time

        start_time = time.time()
        alerts = manager.evaluate_rules(metrics)
        end_time = time.time()

        # Should complete quickly
        assert (end_time - start_time) < 1.0  # 1 second max
        assert len(alerts) > 0  # Some alerts should trigger


class TestErrorHandling:
    """Test error handling in dashboard and alerting systems."""

    def test_dashboard_error_handling(self):
        """Test dashboard error handling with invalid data."""
        manager = DashboardManager()

        # Test with non-existent dashboard
        dashboard_data = manager.get_dashboard_data("non_existent")
        assert dashboard_data is None

        # Test with invalid widget configuration
        invalid_query = MetricQuery(
            metric_name="",  # Empty metric name
            aggregation="invalid_aggregation",
            time_range_minutes=-1,  # Invalid time range
        )

        invalid_widget = DashboardWidget(
            title="Invalid Widget",
            widget_type=WidgetType.LINE_CHART,
            query=invalid_query,
        )

        dashboard_id = manager.create_dashboard("error_test", "Error Test")

        # Should handle gracefully
        result = manager.add_widget(dashboard_id, invalid_widget)
        assert result is False

    def test_alert_error_handling(self):
        """Test alert error handling with invalid configurations."""
        manager = AlertManager()

        # Test with invalid alert rule
        invalid_rule = AlertRule(
            name="",  # Empty name
            condition=AlertCondition.GREATER_THAN,
            threshold=float("inf"),  # Invalid threshold
            metric_name="test_metric",
        )

        # Should handle gracefully
        result = manager.add_alert_rule(invalid_rule)
        assert result is False

        # Test evaluation with missing metrics
        valid_rule = AlertRule(
            name="valid_rule",
            condition=AlertCondition.GREATER_THAN,
            threshold=100.0,
            metric_name="missing_metric",
        )

        manager.add_alert_rule(valid_rule)

        # Evaluate with empty metrics
        alerts = manager.evaluate_rules({})
        assert len(alerts) == 0  # Should not crash, just return no alerts
