"""
Example usage of the monitoring infrastructure.
"""

import asyncio
import sys
import time
from datetime import datetime
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from packages.common.monitoring.health import get_health_aggregator
from packages.common.monitoring.log_aggregator import (get_logger,
                                                       set_correlation_id,
                                                       set_request_id,
                                                       set_user_id)
from packages.common.monitoring.metrics import get_metrics_collector


async def demonstrate_monitoring():
    """Demonstrate the monitoring infrastructure components."""

    print("=== Monitoring Infrastructure Demo ===\n")

    # 1. Demonstrate structured logging with correlation IDs
    print("1. Structured Logging with Correlation IDs")
    logger = get_logger("demo-service")

    # Set context for request tracing
    correlation_id = set_correlation_id("demo-correlation-123")
    request_id = set_request_id("demo-request-456")
    set_user_id("demo-user-789")

    logger.info("Starting demo request", operation="demo", version="1.0")
    logger.info("Processing user data", user_count=100, processing_time=0.5)
    logger.warning("Rate limit approaching", current_rate=85, limit=100)

    try:
        # Simulate an error
        raise ValueError("Demo error for logging")
    except ValueError as e:
        logger.log_error(e, {"context": "demo_operation", "step": "validation"})

    print(f"✓ Logged messages with correlation_id: {correlation_id}\n")

    # 2. Demonstrate metrics collection
    print("2. Metrics Collection")
    metrics = get_metrics_collector()

    # Record some HTTP request metrics
    for i in range(5):
        status_code = 200 if i < 4 else 500  # One error
        duration = 100 + (i * 50)  # Increasing duration

        metrics.record_request_duration(
            service="demo-service",
            endpoint="/api/demo",
            method="GET",
            status_code=status_code,
            duration_ms=duration,
        )

    # Record some custom metrics
    metrics.record_counter("demo_operations_total", 1.0, {"operation": "process_data"})
    metrics.record_gauge("demo_active_connections", 25.0, {"service": "demo-service"})

    # Use timing context manager
    with metrics.time_operation("demo_database_query", {"table": "users"}):
        time.sleep(0.01)  # Simulate database query

    # Display metrics
    error_rate = metrics.get_error_rate("demo-service", "/api/demo")
    avg_response_time = metrics.get_average_response_time("demo-service", "/api/demo")

    print(f"✓ Error rate: {error_rate:.1f}%")
    print(f"✓ Average response time: {avg_response_time:.1f}ms")
    print(
        f"✓ Total operations: {metrics.get_counter_value('demo_operations_total', {'operation': 'process_data'})}"
    )
    print(
        f"✓ Active connections: {metrics.get_gauge_value('demo_active_connections', {'service': 'demo-service'})}\n"
    )

    # 3. Demonstrate health check aggregation
    print("3. Health Check Aggregation")
    health_aggregator = get_health_aggregator()

    # Simulate checking health of multiple services
    services = [
        {"name": "user-service", "health_endpoint": "http://localhost:8001/health"},
        {"name": "project-service", "health_endpoint": "http://localhost:8002/health"},
        {"name": "design-service", "health_endpoint": "http://localhost:8003/health"},
    ]

    # Note: This would normally make actual HTTP requests
    # For demo purposes, we'll simulate the response
    print("✓ Health check aggregation configured for services:")
    for service in services:
        print(f"  - {service['name']}: {service['health_endpoint']}")

    # Create a basic health response structure
    health_response = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "services": {
            service["name"]: {
                "status": "healthy",
                "message": "Service is operational",
                "response_time_ms": 150.0,
                "last_check": datetime.utcnow().isoformat(),
            }
            for service in services
        },
        "summary": {
            "total": len(services),
            "healthy": len(services),
            "unhealthy": 0,
            "unknown": 0,
        },
    }

    print(f"✓ System health: {health_response['status']}")
    print(
        f"✓ Healthy services: {health_response['summary']['healthy']}/{health_response['summary']['total']}\n"
    )

    print("=== Demo Complete ===")
    print("The monitoring infrastructure provides:")
    print("• Structured logging with correlation IDs for request tracing")
    print("• Metrics collection for request duration and error rates")
    print("• Health check aggregation for system-wide monitoring")


if __name__ == "__main__":
    asyncio.run(demonstrate_monitoring())
