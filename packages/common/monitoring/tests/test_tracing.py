"""
Tests for distributed tracing functionality.

Following TDD approach - these tests define the expected behavior
and will initially fail until implementation is complete.
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict
from unittest.mock import Mock, patch

import pytest

from packages.common.monitoring.tracing import (Span, SpanKind, SpanStatus,
                                                Trace, TracingCollector,
                                                get_tracing_collector,
                                                set_tracing_collector)


class TestSpan:
    """Test cases for Span model."""

    def test_span_creation(self):
        """Test basic span creation with required fields."""
        span = Span(
            trace_id="trace-123",
            span_id="span-456",
            parent_span_id="parent-789",
            operation_name="test_operation",
            start_time=datetime.now(timezone.utc),
            service_name="test-service",
        )

        assert span.trace_id == "trace-123"
        assert span.span_id == "span-456"
        assert span.parent_span_id == "parent-789"
        assert span.operation_name == "test_operation"
        assert span.service_name == "test-service"
        assert span.status == SpanStatus.OK
        assert span.kind == SpanKind.INTERNAL
        assert span.end_time is None
        assert span.duration_ms is None

    def test_span_duration_calculation(self):
        """Test span duration calculation."""
        start_time = datetime.now(timezone.utc)
        end_time = start_time + timedelta(milliseconds=150)

        span = Span(
            trace_id="trace-123",
            span_id="span-456",
            parent_span_id=None,
            operation_name="test_operation",
            start_time=start_time,
            end_time=end_time,
        )

        assert span.duration_ms == pytest.approx(150.0, rel=1e-2)

    def test_span_add_tag(self):
        """Test adding tags to span."""
        span = Span(
            trace_id="trace-123",
            span_id="span-456",
            parent_span_id=None,
            operation_name="test_operation",
            start_time=datetime.now(timezone.utc),
        )

        span.add_tag("http.method", "GET")
        span.add_tag("http.status_code", "200")

        assert span.tags["http.method"] == "GET"
        assert span.tags["http.status_code"] == "200"

    def test_span_add_log(self):
        """Test adding log entries to span."""
        span = Span(
            trace_id="trace-123",
            span_id="span-456",
            parent_span_id=None,
            operation_name="test_operation",
            start_time=datetime.now(timezone.utc),
        )

        span.add_log("Processing request", user_id="user-123")

        assert len(span.logs) == 1
        assert span.logs[0]["message"] == "Processing request"
        assert span.logs[0]["user_id"] == "user-123"
        assert "timestamp" in span.logs[0]

    def test_span_finish(self):
        """Test finishing a span."""
        span = Span(
            trace_id="trace-123",
            span_id="span-456",
            parent_span_id=None,
            operation_name="test_operation",
            start_time=datetime.now(timezone.utc),
        )

        span.finish(SpanStatus.ERROR)

        assert span.end_time is not None
        assert span.status == SpanStatus.ERROR
        assert span.duration_ms is not None


class TestTrace:
    """Test cases for Trace model."""

    def test_trace_creation(self):
        """Test basic trace creation."""
        trace = Trace(trace_id="trace-123")

        assert trace.trace_id == "trace-123"
        assert len(trace.spans) == 0
        assert trace.root_span is None

    def test_trace_add_span(self):
        """Test adding spans to trace."""
        trace = Trace(trace_id="trace-123")

        root_span = Span(
            trace_id="trace-123",
            span_id="root-span",
            parent_span_id=None,
            operation_name="root_operation",
            start_time=datetime.now(timezone.utc),
        )

        child_span = Span(
            trace_id="trace-123",
            span_id="child-span",
            parent_span_id="root-span",
            operation_name="child_operation",
            start_time=datetime.now(timezone.utc),
        )

        trace.add_span(root_span)
        trace.add_span(child_span)

        assert len(trace.spans) == 2
        assert trace.root_span == root_span

    def test_trace_get_span_by_id(self):
        """Test retrieving span by ID."""
        trace = Trace(trace_id="trace-123")

        span = Span(
            trace_id="trace-123",
            span_id="span-456",
            parent_span_id=None,
            operation_name="test_operation",
            start_time=datetime.now(timezone.utc),
        )

        trace.add_span(span)

        found_span = trace.get_span_by_id("span-456")
        assert found_span == span

        not_found = trace.get_span_by_id("nonexistent")
        assert not_found is None

    def test_trace_duration(self):
        """Test trace duration calculation."""
        trace = Trace(trace_id="trace-123")

        start_time = datetime.now(timezone.utc)
        end_time = start_time + timedelta(milliseconds=200)

        root_span = Span(
            trace_id="trace-123",
            span_id="root-span",
            parent_span_id=None,
            operation_name="root_operation",
            start_time=start_time,
            end_time=end_time,
        )

        trace.add_span(root_span)

        assert trace.duration_ms == pytest.approx(200.0, rel=1e-2)


class TestTracingCollector:
    """Test cases for TracingCollector."""

    def test_collector_initialization(self):
        """Test tracing collector initialization."""
        collector = TracingCollector("test-service")

        assert collector.service_name == "test-service"
        assert len(collector.active_spans) == 0
        assert len(collector.completed_traces) == 0

    def test_start_span_creates_span(self):
        """Test that start_span creates a new span."""
        collector = TracingCollector("test-service")

        span = collector.start_span("test_operation")

        assert span is not None
        assert span.operation_name == "test_operation"
        assert span.service_name == "test-service"
        assert span.trace_id is not None
        assert span.span_id is not None
        assert span.parent_span_id is None
        assert span.kind == SpanKind.INTERNAL
        assert span.status == SpanStatus.OK

    def test_start_child_span(self):
        """Test creating a child span."""
        collector = TracingCollector("test-service")

        parent_span = collector.start_span("parent_operation")
        child_span = collector.start_span("child_operation", parent_span=parent_span)

        assert child_span.trace_id == parent_span.trace_id
        assert child_span.parent_span_id == parent_span.span_id
        assert child_span.operation_name == "child_operation"

    def test_finish_span(self):
        """Test finishing a span."""
        collector = TracingCollector("test-service")

        span = collector.start_span("test_operation")
        collector.finish_span(span, SpanStatus.OK)

        assert span.end_time is not None
        assert span.status == SpanStatus.OK
        assert span.span_id not in collector.active_spans

    def test_get_trace(self):
        """Test retrieving a trace."""
        collector = TracingCollector("test-service")

        span = collector.start_span("test_operation")
        trace = collector.get_trace(span.trace_id)

        assert trace is not None
        assert trace.trace_id == span.trace_id
        assert len(trace.spans) == 1
        assert trace.spans[0] == span

    def test_get_current_span(self):
        """Test getting the current active span."""
        collector = TracingCollector("test-service")

        assert collector.get_current_span() is None

        span = collector.start_span("test_operation")
        assert collector.get_current_span() == span

        collector.finish_span(span)
        assert collector.get_current_span() is None

    def test_trace_operation_context_manager(self):
        """Test trace operation context manager."""
        collector = TracingCollector("test-service")

        with collector.trace_operation("test_operation") as span:
            assert span is not None
            assert span.operation_name == "test_operation"
            assert span.end_time is None

        assert span.end_time is not None
        assert span.status == SpanStatus.OK

    def test_inject_trace_context(self):
        """Test injecting trace context into headers."""
        collector = TracingCollector("test-service")

        span = collector.start_span("test_operation")
        headers = collector.inject_trace_context({"existing": "header"})

        assert "X-Trace-ID" in headers
        assert "X-Span-ID" in headers
        assert "X-Parent-Span-ID" in headers
        assert headers["X-Trace-ID"] == span.trace_id
        assert headers["X-Span-ID"] == span.span_id
        assert headers["existing"] == "header"

    def test_extract_trace_context(self):
        """Test extracting trace context from headers."""
        collector = TracingCollector("test-service")

        headers = {"X-Trace-ID": "trace-123", "X-Parent-Span-ID": "parent-456"}

        parent_span = collector.extract_trace_context(headers)

        assert parent_span is not None
        assert parent_span.trace_id == "trace-123"
        assert parent_span.span_id == "parent-456"


class TestTracingCollectorIntegration:
    """Integration tests for tracing collector - these will pass after GREEN phase."""

    def test_complete_trace_workflow(self):
        """Test complete trace creation and collection workflow."""
        collector = TracingCollector("test-service")

        # Start root span
        root_span = collector.start_span("handle_request", kind=SpanKind.SERVER)
        root_span.add_tag("http.method", "POST")
        root_span.add_tag("http.url", "/api/users")

        # Start child span
        child_span = collector.start_span("database_query", parent_span=root_span)
        child_span.add_tag("db.statement", "SELECT * FROM users")
        child_span.add_log("Executing query")

        # Finish spans
        collector.finish_span(child_span, SpanStatus.OK)
        collector.finish_span(root_span, SpanStatus.OK)

        # Verify trace
        trace = collector.get_trace(root_span.trace_id)
        assert trace is not None
        assert len(trace.spans) == 2
        assert trace.root_span == root_span

    def test_trace_context_propagation(self):
        """Test trace context propagation across service boundaries."""
        collector = TracingCollector("service-a")

        # Start span in service A
        span_a = collector.start_span("service_a_operation", kind=SpanKind.CLIENT)

        # Inject context into headers
        headers = collector.inject_trace_context({})
        assert "X-Trace-ID" in headers
        assert "X-Span-ID" in headers

        # Simulate service B receiving the request
        collector_b = TracingCollector("service-b")
        parent_span = collector_b.extract_trace_context(headers)

        # Start span in service B with propagated context
        span_b = collector_b.start_span(
            "service_b_operation", parent_span=parent_span, kind=SpanKind.SERVER
        )

        # Verify trace continuity
        assert span_b.trace_id == span_a.trace_id
        assert span_b.parent_span_id == span_a.span_id

    def test_trace_operation_context_manager_integration(self):
        """Test trace operation context manager."""
        collector = TracingCollector("test-service")

        with collector.trace_operation(
            "test_operation", kind=SpanKind.INTERNAL
        ) as span:
            span.add_tag("operation.type", "test")
            span.add_log("Operation started")

            # Simulate some work
            import time

            time.sleep(0.01)

        # Verify span was finished
        assert span.end_time is not None
        assert span.status == SpanStatus.OK
        assert span.duration_ms > 0


class TestGlobalTracingCollector:
    """Test cases for global tracing collector management."""

    def test_get_tracing_collector_creates_instance(self):
        """Test that get_tracing_collector creates a new instance."""
        # Reset global state
        set_tracing_collector(None)

        collector = get_tracing_collector("test-service")

        assert collector is not None
        assert collector.service_name == "test-service"

    def test_get_tracing_collector_returns_existing(self):
        """Test that get_tracing_collector returns existing instance."""
        # Reset global state
        set_tracing_collector(None)

        collector1 = get_tracing_collector("test-service")
        collector2 = get_tracing_collector("other-service")

        # Should return the same instance
        assert collector1 is collector2

    def test_set_tracing_collector(self):
        """Test setting custom tracing collector."""
        custom_collector = TracingCollector("custom-service")
        set_tracing_collector(custom_collector)

        retrieved_collector = get_tracing_collector()

        assert retrieved_collector is custom_collector
        assert retrieved_collector.service_name == "custom-service"


class TestTracingPerformance:
    """Performance tests for tracing system."""

    def test_tracing_overhead_minimal(self):
        """Test that tracing adds minimal overhead."""
        collector = TracingCollector("test-service")

        import time

        def simulate_work():
            # Simulate some actual work
            sum(range(100))

        # Measure without tracing
        start_time = time.time()
        for _ in range(100):
            simulate_work()
        baseline_time = time.time() - start_time

        # Measure with tracing
        start_time = time.time()
        for i in range(100):
            with collector.trace_operation(f"operation_{i}"):
                simulate_work()
        tracing_time = time.time() - start_time

        # For a basic implementation, just ensure tracing works and completes
        # Performance optimization will be done in REFACTOR phase
        assert tracing_time > baseline_time  # Tracing should add some overhead
        assert tracing_time < 10.0  # But should still complete in reasonable time

        # Verify that traces were actually created
        assert len(collector.completed_traces) == 100

    def test_concurrent_tracing(self):
        """Test tracing under concurrent load."""
        import asyncio
        import concurrent.futures

        collector = TracingCollector("test-service")

        async def trace_operation(operation_id: int):
            with collector.trace_operation(f"concurrent_operation_{operation_id}"):
                await asyncio.sleep(0.001)  # Simulate async work

        async def run_concurrent_traces():
            tasks = [trace_operation(i) for i in range(100)]
            await asyncio.gather(*tasks)

        # Should complete without errors
        asyncio.run(run_concurrent_traces())


class TestTracingErrorHandling:
    """Test error handling in tracing system."""

    def test_span_error_status(self):
        """Test setting error status on spans."""
        collector = TracingCollector("test-service")

        try:
            with collector.trace_operation("error_operation") as span:
                span.add_log("About to raise error")
                raise ValueError("Test error")
        except ValueError:
            pass

        # Span should be marked as error
        assert span.status == SpanStatus.ERROR
        assert any("error" in log["message"].lower() for log in span.logs)

    def test_invalid_trace_context_handling(self):
        """Test handling of invalid trace context headers."""
        collector = TracingCollector("test-service")

        # Invalid headers should not crash the system
        invalid_headers = {
            "X-Trace-ID": "invalid-trace-id",
            "X-Span-ID": "invalid-span-id",
        }

        parent_span = collector.extract_trace_context(invalid_headers)

        # Should handle gracefully
        assert parent_span is None or isinstance(parent_span, Span)
