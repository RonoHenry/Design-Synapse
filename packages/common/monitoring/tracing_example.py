"""
Example demonstrating distributed tracing functionality.

This example shows how to use the tracing system to track requests
across service boundaries in the DesignSynapse infrastructure.
"""

import asyncio
import os
import sys
import time

sys.path.append(os.path.join(os.path.dirname(__file__), "../../.."))

from packages.common.monitoring.tracing import (SpanKind, SpanStatus,
                                                get_tracing_collector)


def simulate_database_query(query: str, duration: float = 0.1):
    """Simulate a database query with some processing time."""
    time.sleep(duration)
    return f"Results for: {query}"


def simulate_external_api_call(endpoint: str, duration: float = 0.2):
    """Simulate an external API call."""
    time.sleep(duration)
    return {"status": "success", "endpoint": endpoint}


def simulate_service_operation():
    """Demonstrate tracing within a single service."""
    print("=== Single Service Tracing Example ===")

    # Get tracing collector for this service
    tracer = get_tracing_collector("user-service")

    # Start a root span for the main operation
    with tracer.trace_operation("handle_user_request", SpanKind.SERVER) as root_span:
        root_span.add_tag("http.method", "POST")
        root_span.add_tag("http.url", "/api/users")
        root_span.add_tag("user.id", "user-123")
        root_span.add_log("Processing user creation request")

        # Simulate validation step
        with tracer.trace_operation(
            "validate_user_data", SpanKind.INTERNAL
        ) as validation_span:
            validation_span.add_tag("validation.type", "user_data")
            validation_span.add_log("Validating user input")
            time.sleep(0.05)  # Simulate validation time
            validation_span.add_log("Validation completed successfully")

        # Simulate database operation
        with tracer.trace_operation("create_user_db", SpanKind.CLIENT) as db_span:
            db_span.add_tag("db.operation", "INSERT")
            db_span.add_tag("db.table", "users")
            db_span.add_log("Executing database query")

            result = simulate_database_query("INSERT INTO users ...")
            db_span.add_tag("db.rows_affected", "1")
            db_span.add_log("Database operation completed", result=result)

        # Simulate external service call
        with tracer.trace_operation(
            "send_welcome_email", SpanKind.CLIENT
        ) as email_span:
            email_span.add_tag("service.name", "email-service")
            email_span.add_tag("email.type", "welcome")
            email_span.add_log("Sending welcome email")

            try:
                api_result = simulate_external_api_call("/api/emails/send")
                email_span.add_tag("email.status", "sent")
                email_span.add_log("Email sent successfully", response=api_result)
            except Exception as e:
                email_span.add_log(f"Email sending failed: {str(e)}", error=True)
                email_span.finish(SpanStatus.ERROR)
                raise

        root_span.add_log("User creation completed successfully")

    # Display trace information
    trace = tracer.get_trace(root_span.trace_id)
    print(f"\nTrace ID: {trace.trace_id}")
    print(f"Total Duration: {trace.duration_ms:.2f}ms")
    print(f"Number of Spans: {len(trace.spans)}")

    for span in trace.spans:
        print(f"\n  Span: {span.operation_name}")
        print(f"    Duration: {span.duration_ms:.2f}ms")
        print(f"    Status: {span.status}")
        print(f"    Tags: {span.tags}")
        if span.logs:
            print(f"    Logs: {len(span.logs)} entries")


def simulate_cross_service_tracing():
    """Demonstrate tracing across multiple services."""
    print("\n\n=== Cross-Service Tracing Example ===")

    # Service A (API Gateway)
    gateway_tracer = get_tracing_collector("api-gateway")

    with gateway_tracer.trace_operation(
        "route_request", SpanKind.SERVER
    ) as gateway_span:
        gateway_span.add_tag("http.method", "GET")
        gateway_span.add_tag("http.url", "/api/projects/123")
        gateway_span.add_tag("client.ip", "192.168.1.100")
        gateway_span.add_log("Received request from client")

        # Inject trace context for propagation
        headers = gateway_tracer.inject_trace_context(
            {"Authorization": "Bearer token123", "Content-Type": "application/json"}
        )

        gateway_span.add_log(
            "Forwarding request to project-service", headers=list(headers.keys())
        )

        # Simulate network delay
        time.sleep(0.01)

    # Service B (Project Service) - receives the request
    project_tracer = get_tracing_collector("project-service")

    # Extract trace context from headers
    parent_span = project_tracer.extract_trace_context(headers)

    with project_tracer.trace_operation(
        "get_project", SpanKind.SERVER, parent_span
    ) as project_span:
        project_span.add_tag("project.id", "123")
        project_span.add_tag("service.name", "project-service")
        project_span.add_log("Processing project retrieval request")

        # Simulate database query
        with project_tracer.trace_operation(
            "query_project_db", SpanKind.CLIENT
        ) as db_span:
            db_span.add_tag("db.operation", "SELECT")
            db_span.add_tag("db.table", "projects")
            db_span.add_log("Querying project database")

            result = simulate_database_query("SELECT * FROM projects WHERE id = 123")
            db_span.add_log("Database query completed", rows_returned=1)

        project_span.add_log("Project retrieval completed successfully")

    # Display cross-service trace
    trace = gateway_tracer.get_trace(gateway_span.trace_id)
    print(f"\nCross-Service Trace ID: {trace.trace_id}")
    print(f"Total Duration: {trace.duration_ms:.2f}ms")
    print(f"Services Involved: api-gateway, project-service")

    # Show spans from both services
    all_spans = trace.spans
    if project_span.trace_id == gateway_span.trace_id:
        # In a real implementation, spans would be collected centrally
        print(f"Total Spans: {len(all_spans)} (+ spans from project-service)")

    for span in all_spans:
        service = span.service_name or "unknown"
        print(f"\n  [{service}] {span.operation_name}")
        print(f"    Duration: {span.duration_ms:.2f}ms")
        print(f"    Parent: {span.parent_span_id or 'root'}")


def simulate_error_tracing():
    """Demonstrate error handling in tracing."""
    print("\n\n=== Error Tracing Example ===")

    tracer = get_tracing_collector("design-service")

    try:
        with tracer.trace_operation("process_design", SpanKind.SERVER) as root_span:
            root_span.add_tag("design.id", "design-456")
            root_span.add_log("Starting design processing")

            # Simulate successful validation
            with tracer.trace_operation(
                "validate_design", SpanKind.INTERNAL
            ) as validation_span:
                validation_span.add_log("Validating design parameters")
                time.sleep(0.02)
                validation_span.add_log("Design validation passed")

            # Simulate an error in processing
            with tracer.trace_operation(
                "generate_output", SpanKind.INTERNAL
            ) as generation_span:
                generation_span.add_tag("output.format", "pdf")
                generation_span.add_log("Starting output generation")

                # Simulate an error
                raise ValueError("Invalid design parameters for PDF generation")

    except ValueError as e:
        print(f"Caught error: {e}")

    # Display error trace
    trace = tracer.get_trace(root_span.trace_id)
    print(f"\nError Trace ID: {trace.trace_id}")

    for span in trace.spans:
        status_indicator = "❌" if span.status == SpanStatus.ERROR else "✅"
        print(f"\n  {status_indicator} {span.operation_name}")
        print(f"    Status: {span.status}")
        print(f"    Duration: {span.duration_ms:.2f}ms")

        # Show error logs
        error_logs = [log for log in span.logs if log.get("error")]
        if error_logs:
            print(f"    Error Logs:")
            for log in error_logs:
                print(f"      - {log['message']}")


async def simulate_async_tracing():
    """Demonstrate tracing with async operations."""
    print("\n\n=== Async Tracing Example ===")

    tracer = get_tracing_collector("async-service")

    async def async_operation(name: str, duration: float):
        with tracer.trace_operation(f"async_{name}", SpanKind.INTERNAL) as span:
            span.add_tag("operation.type", "async")
            span.add_log(f"Starting async operation: {name}")
            await asyncio.sleep(duration)
            span.add_log(f"Completed async operation: {name}")
            return f"Result from {name}"

    with tracer.trace_operation("async_workflow", SpanKind.SERVER) as root_span:
        root_span.add_log("Starting async workflow")

        # Run multiple async operations concurrently
        tasks = [
            async_operation("fetch_data", 0.1),
            async_operation("process_data", 0.15),
            async_operation("save_results", 0.08),
        ]

        results = await asyncio.gather(*tasks)
        root_span.add_log("All async operations completed", results=len(results))

    # Display async trace
    trace = tracer.get_trace(root_span.trace_id)
    print(f"\nAsync Trace ID: {trace.trace_id}")
    print(f"Total Duration: {trace.duration_ms:.2f}ms")

    for span in trace.spans:
        print(f"\n  {span.operation_name}")
        print(f"    Duration: {span.duration_ms:.2f}ms")
        print(f"    Tags: {span.tags}")


def main():
    """Run all tracing examples."""
    print("🔍 Distributed Tracing Examples")
    print("=" * 50)

    # Run synchronous examples
    simulate_service_operation()
    simulate_cross_service_tracing()
    simulate_error_tracing()

    # Run async example
    asyncio.run(simulate_async_tracing())

    print("\n\n✅ All tracing examples completed!")
    print("\nKey Features Demonstrated:")
    print("- Span creation and nesting")
    print("- Tag and log management")
    print("- Cross-service trace propagation")
    print("- Error handling and status tracking")
    print("- Context manager usage")
    print("- Async operation tracing")


if __name__ == "__main__":
    main()
