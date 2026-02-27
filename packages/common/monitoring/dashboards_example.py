"""
Example demonstrating dashboard and alerting functionality.

This example shows how to create dashboards, add widgets, configure alerts,
and monitor system metrics in the DesignSynapse infrastructure.
"""

import asyncio
import os
import random
import sys
import time
from datetime import datetime, timezone

sys.path.append(os.path.join(os.path.dirname(__file__), "../../.."))

from packages.common.monitoring.dashboards import (AlertCondition, AlertRule,
                                                   AlertSeverity,
                                                   DashboardWidget,
                                                   EmailNotificationHandler,
                                                   MetricQuery,
                                                   SlackNotificationHandler,
                                                   WidgetType,
                                                   get_alert_manager,
                                                   get_dashboard_manager)


def simulate_system_metrics():
    """Simulate system metrics for demonstration."""
    return {
        "cpu_usage_percent": random.uniform(20, 95),
        "memory_usage_percent": random.uniform(30, 90),
        "disk_usage_percent": random.uniform(10, 80),
        "request_count": random.randint(50, 500),
        "error_rate": random.uniform(0.001, 0.1),
        "response_time_ms": random.uniform(50, 300),
        "active_connections": random.randint(10, 100),
    }


def create_system_dashboard():
    """Create a comprehensive system monitoring dashboard."""
    print("=== Creating System Dashboard ===")

    dashboard_manager = get_dashboard_manager()

    # Create main dashboard
    dashboard_id = dashboard_manager.create_dashboard(
        "system_overview", "System Overview Dashboard"
    )

    print(f"Created dashboard: {dashboard_id}")

    # CPU Usage Widget (Line Chart)
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

    dashboard_manager.add_widget(dashboard_id, cpu_widget)
    print("Added CPU Usage widget")

    # Memory Usage Widget (Gauge)
    memory_query = MetricQuery(
        metric_name="memory_usage_percent", aggregation="avg", time_range_minutes=30
    )

    memory_widget = DashboardWidget(
        title="Memory Usage",
        widget_type=WidgetType.GAUGE,
        query=memory_query,
        position_x=6,
        position_y=0,
        width=3,
        height=4,
    )

    dashboard_manager.add_widget(dashboard_id, memory_widget)
    print("Added Memory Usage widget")

    # Request Count Widget (Bar Chart)
    request_query = MetricQuery(
        metric_name="request_count",
        aggregation="sum",
        time_range_minutes=60,
        group_by="endpoint",
    )

    request_widget = DashboardWidget(
        title="Request Count by Endpoint",
        widget_type=WidgetType.BAR_CHART,
        query=request_query,
        position_x=9,
        position_y=0,
        width=3,
        height=4,
    )

    dashboard_manager.add_widget(dashboard_id, request_widget)
    print("Added Request Count widget")

    # Response Time Widget (Line Chart)
    response_query = MetricQuery(
        metric_name="response_time_ms", aggregation="avg", time_range_minutes=120
    )

    response_widget = DashboardWidget(
        title="Average Response Time",
        widget_type=WidgetType.LINE_CHART,
        query=response_query,
        position_x=0,
        position_y=4,
        width=6,
        height=4,
    )

    dashboard_manager.add_widget(dashboard_id, response_widget)
    print("Added Response Time widget")

    # Error Rate Widget (Counter)
    error_query = MetricQuery(
        metric_name="error_rate", aggregation="avg", time_range_minutes=30
    )

    error_widget = DashboardWidget(
        title="Error Rate",
        widget_type=WidgetType.COUNTER,
        query=error_query,
        position_x=6,
        position_y=4,
        width=3,
        height=4,
    )

    dashboard_manager.add_widget(dashboard_id, error_widget)
    print("Added Error Rate widget")

    # Active Connections Widget (Gauge)
    connections_query = MetricQuery(
        metric_name="active_connections", aggregation="avg", time_range_minutes=15
    )

    connections_widget = DashboardWidget(
        title="Active Connections",
        widget_type=WidgetType.GAUGE,
        query=connections_query,
        position_x=9,
        position_y=4,
        width=3,
        height=4,
    )

    dashboard_manager.add_widget(dashboard_id, connections_widget)
    print("Added Active Connections widget")

    return dashboard_id


def setup_alerting_rules():
    """Set up comprehensive alerting rules."""
    print("\n=== Setting Up Alert Rules ===")

    alert_manager = get_alert_manager()

    # High CPU Alert
    cpu_alert = AlertRule(
        name="High CPU Usage",
        description="Alert when CPU usage exceeds 80%",
        condition=AlertCondition.GREATER_THAN,
        threshold=80.0,
        metric_name="cpu_usage_percent",
        severity=AlertSeverity.WARNING,
        duration_minutes=5,
    )

    alert_manager.add_alert_rule(cpu_alert)
    print("Added High CPU Usage alert")

    # Critical CPU Alert
    critical_cpu_alert = AlertRule(
        name="Critical CPU Usage",
        description="Alert when CPU usage exceeds 90%",
        condition=AlertCondition.GREATER_THAN,
        threshold=90.0,
        metric_name="cpu_usage_percent",
        severity=AlertSeverity.CRITICAL,
        duration_minutes=2,
    )

    alert_manager.add_alert_rule(critical_cpu_alert)
    print("Added Critical CPU Usage alert")

    # High Memory Alert
    memory_alert = AlertRule(
        name="High Memory Usage",
        description="Alert when memory usage exceeds 85%",
        condition=AlertCondition.GREATER_THAN,
        threshold=85.0,
        metric_name="memory_usage_percent",
        severity=AlertSeverity.WARNING,
        duration_minutes=10,
    )

    alert_manager.add_alert_rule(memory_alert)
    print("Added High Memory Usage alert")

    # High Error Rate Alert
    error_alert = AlertRule(
        name="High Error Rate",
        description="Alert when error rate exceeds 5%",
        condition=AlertCondition.GREATER_THAN,
        threshold=0.05,
        metric_name="error_rate",
        severity=AlertSeverity.ERROR,
        duration_minutes=3,
    )

    alert_manager.add_alert_rule(error_alert)
    print("Added High Error Rate alert")

    # Slow Response Time Alert
    response_alert = AlertRule(
        name="Slow Response Time",
        description="Alert when response time exceeds 250ms",
        condition=AlertCondition.GREATER_THAN,
        threshold=250.0,
        metric_name="response_time_ms",
        severity=AlertSeverity.WARNING,
        duration_minutes=5,
    )

    alert_manager.add_alert_rule(response_alert)
    print("Added Slow Response Time alert")

    # Low Disk Space Alert
    disk_alert = AlertRule(
        name="Low Disk Space",
        description="Alert when disk usage exceeds 75%",
        condition=AlertCondition.GREATER_THAN,
        threshold=75.0,
        metric_name="disk_usage_percent",
        severity=AlertSeverity.WARNING,
        duration_minutes=15,
    )

    alert_manager.add_alert_rule(disk_alert)
    print("Added Low Disk Space alert")

    return alert_manager


def setup_notification_handlers():
    """Set up notification handlers for alerts."""
    print("\n=== Setting Up Notification Handlers ===")

    alert_manager = get_alert_manager()

    # Email notifications
    email_handler = EmailNotificationHandler(
        {
            "smtp_server": "smtp.company.com",
            "smtp_port": 587,
            "username": "alerts@company.com",
            "password": "password",
            "recipients": ["devops@company.com", "admin@company.com"],
        }
    )

    alert_manager.add_notification_handler(email_handler)
    print("Added email notification handler")

    # Slack notifications
    slack_handler = SlackNotificationHandler(
        "https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK"
    )

    alert_manager.add_notification_handler(slack_handler)
    print("Added Slack notification handler")


def display_dashboard_data(dashboard_id: str):
    """Display dashboard data in a formatted way."""
    print(f"\n=== Dashboard Data: {dashboard_id} ===")

    dashboard_manager = get_dashboard_manager()
    dashboard_data = dashboard_manager.get_dashboard_data(dashboard_id)

    if not dashboard_data:
        print("Dashboard not found!")
        return

    print(f"Dashboard: {dashboard_data['title']}")
    print(f"Created: {dashboard_data['created_at']}")
    print(f"Updated: {dashboard_data['updated_at']}")
    print(f"Widgets: {len(dashboard_data['widgets'])}")

    for widget in dashboard_data["widgets"]:
        print(f"\n  📊 {widget['title']} ({widget['type']})")
        print(f"     Position: ({widget['position']['x']}, {widget['position']['y']})")
        print(f"     Size: {widget['size']['width']}x{widget['size']['height']}")

        # Display sample data
        data = widget["data"]
        if widget["type"] == "line_chart":
            if data["values"]:
                print(f"     Latest Value: {data['values'][-1]:.2f}")
                print(f"     Data Points: {len(data['values'])}")
        elif widget["type"] == "gauge":
            print(f"     Current Value: {data['value']:.2f}")
        elif widget["type"] == "counter":
            print(f"     Count: {data['value']:.0f}")
        elif widget["type"] == "bar_chart":
            if data["series"]:
                total = sum(data["series"][0]["data"])
                print(f"     Total: {total:.0f}")


async def monitor_system_with_alerts():
    """Monitor system metrics and trigger alerts."""
    print("\n=== Starting System Monitoring ===")

    alert_manager = get_alert_manager()

    for cycle in range(10):
        print(f"\nMonitoring Cycle {cycle + 1}/10")

        # Generate simulated metrics
        metrics = simulate_system_metrics()

        print("Current Metrics:")
        for metric, value in metrics.items():
            if metric.endswith("_percent"):
                print(f"  {metric}: {value:.1f}%")
            elif metric == "error_rate":
                print(f"  {metric}: {value:.3f}")
            elif metric.endswith("_ms"):
                print(f"  {metric}: {value:.1f}ms")
            else:
                print(f"  {metric}: {value:.0f}")

        # Evaluate alert rules
        triggered_alerts = alert_manager.evaluate_rules(metrics)

        if triggered_alerts:
            print(f"\n🚨 {len(triggered_alerts)} Alert(s) Triggered:")
            for alert in triggered_alerts:
                severity_emoji = {
                    "info": "ℹ️",
                    "warning": "⚠️",
                    "error": "❌",
                    "critical": "🔥",
                }

                emoji = severity_emoji.get(alert.severity.value, "🚨")
                print(f"  {emoji} {alert.rule_name}")
                print(f"     {alert.message}")
                print(f"     Severity: {alert.severity.value.upper()}")

        # Show active alerts
        active_alerts = alert_manager.get_active_alerts()
        if active_alerts:
            print(f"\n📋 Active Alerts: {len(active_alerts)}")
            for alert in active_alerts:
                print(
                    f"  - {alert.rule_name} (since {alert.triggered_at.strftime('%H:%M:%S')})"
                )
        else:
            print("\n✅ No active alerts")

        # Wait before next cycle
        await asyncio.sleep(2)

    print("\n=== Monitoring Complete ===")


def demonstrate_real_time_metrics():
    """Demonstrate real-time metrics retrieval."""
    print("\n=== Real-Time Metrics Demo ===")

    dashboard_manager = get_dashboard_manager()

    # Get real-time metrics for key indicators
    metrics = dashboard_manager.get_real_time_metrics(
        ["cpu_usage_percent", "memory_usage_percent", "response_time_ms", "error_rate"]
    )

    for metric_name, data_points in metrics.items():
        print(f"\n📈 {metric_name}:")
        if data_points:
            latest = data_points[-1]
            print(f"   Latest: {latest['value']:.2f}")
            print(f"   Data Points: {len(data_points)}")

            # Calculate trend
            if len(data_points) >= 2:
                trend = data_points[-1]["value"] - data_points[-2]["value"]
                trend_indicator = "📈" if trend > 0 else "📉" if trend < 0 else "➡️"
                print(f"   Trend: {trend_indicator} {trend:+.2f}")


def demonstrate_widget_types():
    """Demonstrate different widget types and their data formatting."""
    print("\n=== Widget Types Demo ===")

    dashboard_manager = get_dashboard_manager()

    # Create a demo dashboard
    demo_dashboard_id = dashboard_manager.create_dashboard(
        "widget_demo", "Widget Types Demo"
    )

    # Line Chart Widget
    line_widget = DashboardWidget(
        title="CPU Trend",
        widget_type=WidgetType.LINE_CHART,
        query=MetricQuery("cpu_usage_percent", "avg", 30),
    )
    dashboard_manager.add_widget(demo_dashboard_id, line_widget)

    # Pie Chart Widget
    pie_widget = DashboardWidget(
        title="Resource Distribution",
        widget_type=WidgetType.PIE_CHART,
        query=MetricQuery("resource_usage", "sum", 60, group_by="resource_type"),
    )
    dashboard_manager.add_widget(demo_dashboard_id, pie_widget)

    # Heatmap Widget
    heatmap_widget = DashboardWidget(
        title="Request Heatmap",
        widget_type=WidgetType.HEATMAP,
        query=MetricQuery("request_count", "sum", 120, group_by="hour"),
    )
    dashboard_manager.add_widget(demo_dashboard_id, heatmap_widget)

    # Display the demo dashboard
    display_dashboard_data(demo_dashboard_id)


async def main():
    """Run the complete dashboard and alerting demonstration."""
    print("🔍 Dashboard and Alerting System Demo")
    print("=" * 50)

    # Create system dashboard
    dashboard_id = create_system_dashboard()

    # Set up alerting
    alert_manager = setup_alerting_rules()
    setup_notification_handlers()

    # Display dashboard data
    display_dashboard_data(dashboard_id)

    # Demonstrate real-time metrics
    demonstrate_real_time_metrics()

    # Demonstrate different widget types
    demonstrate_widget_types()

    # Monitor system with alerts
    await monitor_system_with_alerts()

    print("\n✅ Dashboard and Alerting Demo Complete!")
    print("\nKey Features Demonstrated:")
    print("- Dashboard creation and widget management")
    print("- Multiple widget types (line, bar, pie, gauge, counter)")
    print("- Real-time metrics aggregation")
    print("- Alert rule configuration and evaluation")
    print("- Notification handler setup")
    print("- System monitoring with alert triggering")
    print("- Dashboard data visualization")


if __name__ == "__main__":
    asyncio.run(main())
