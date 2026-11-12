"""
Distributed tracing implementation for request flow visibility.

This module provides OpenTelemetry-based distributed tracing capabilities
to track requests across service boundaries in the DesignSynapse infrastructure.
"""

import time
import uuid
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Union

# Placeholder for OpenTelemetry imports - will be implemented in GREEN phase
# from opentelemetry import trace
# from opentelemetry.exporter.jaeger.thrift import JaegerExporter
# from opentelemetry.sdk.trace import TracerProvider
# from opentelemetry.sdk.trace.export import BatchSpanProcessor


class SpanStatus(str, Enum):
    """Status of a trace span."""

    OK = "OK"
    ERROR = "ERROR"
    TIMEOUT = "TIMEOUT"
    CANCELLED = "CANCELLED"


class SpanKind(str, Enum):
    """Kind of span operation."""

    SERVER = "SERVER"
    CLIENT = "CLIENT"
    PRODUCER = "PRODUCER"
    CONSUMER = "CONSUMER"
    INTERNAL = "INTERNAL"


@dataclass
class Span:
    """Represents a single span in a distributed trace."""

    trace_id: str
    span_id: str
    parent_span_id: Optional[str]
    operation_name: str
    start_time: datetime
    end_time: Optional[datetime] = None
    status: SpanStatus = SpanStatus.OK
    kind: SpanKind = SpanKind.INTERNAL
    tags: Dict[str, str] = field(default_factory=dict)
    logs: List[Dict[str, Any]] = field(default_factory=list)
    service_name: str = ""

    @property
    def duration_ms(self) -> Optional[float]:
        """Calculate span duration in milliseconds."""
        if self.end_time:
            return (self.end_time - self.start_time).total_seconds() * 1000
        return None

    def add_tag(self, key: str, value: str) -> None:
        """Add a tag to the span."""
        self.tags[key] = value

    def add_log(self, message: str, **kwargs) -> None:
        """Add a log entry to the span."""
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "message": message,
            **kwargs,
        }
        self.logs.append(log_entry)

    def finish(self, status: SpanStatus = SpanStatus.OK) -> None:
        """Finish the span with optional status."""
        self.end_time = datetime.now(timezone.utc)
        self.status = status


@dataclass
class Trace:
    """Represents a complete distributed trace."""

    trace_id: str
    spans: List[Span] = field(default_factory=list)
    root_span: Optional[Span] = None

    def add_span(self, span: Span) -> None:
        """Add a span to the trace."""
        self.spans.append(span)
        if span.parent_span_id is None:
            self.root_span = span

    def get_span_by_id(self, span_id: str) -> Optional[Span]:
        """Get a span by its ID."""
        return next((span for span in self.spans if span.span_id == span_id), None)

    @property
    def duration_ms(self) -> Optional[float]:
        """Calculate total trace duration."""
        if self.root_span:
            return self.root_span.duration_ms
        return None


class TracingCollector:
    """Collects and manages distributed traces."""

    def __init__(self, service_name: str = "unknown"):
        self.service_name = service_name
        self.active_spans: Dict[str, Span] = {}
        self.completed_traces: Dict[str, Trace] = {}
        self._current_span: Optional[Span] = None
        self._span_stack: List[Span] = []

    def start_span(
        self,
        operation_name: str,
        parent_span: Optional[Span] = None,
        kind: SpanKind = SpanKind.INTERNAL,
        tags: Optional[Dict[str, str]] = None,
    ) -> Span:
        """Start a new span."""
        # Generate IDs
        span_id = str(uuid.uuid4())

        # Determine trace ID and parent
        if parent_span:
            trace_id = parent_span.trace_id
            parent_span_id = parent_span.span_id
        else:
            trace_id = str(uuid.uuid4())
            parent_span_id = None

        # Create span
        span = Span(
            trace_id=trace_id,
            span_id=span_id,
            parent_span_id=parent_span_id,
            operation_name=operation_name,
            start_time=datetime.now(timezone.utc),
            kind=kind,
            service_name=self.service_name,
        )

        # Add tags if provided
        if tags:
            for key, value in tags.items():
                span.add_tag(key, value)

        # Track active span
        self.active_spans[span_id] = span
        self._current_span = span
        self._span_stack.append(span)

        # Add to trace
        if trace_id not in self.completed_traces:
            self.completed_traces[trace_id] = Trace(trace_id=trace_id)

        self.completed_traces[trace_id].add_span(span)

        return span

    def finish_span(self, span: Span, status: SpanStatus = SpanStatus.OK) -> None:
        """Finish a span and update trace."""
        span.finish(status)

        # Remove from active spans
        if span.span_id in self.active_spans:
            del self.active_spans[span.span_id]

        # Update current span to parent
        if self._span_stack and self._span_stack[-1] == span:
            self._span_stack.pop()
            self._current_span = self._span_stack[-1] if self._span_stack else None

    def get_trace(self, trace_id: str) -> Optional[Trace]:
        """Get a complete trace by ID."""
        return self.completed_traces.get(trace_id)

    def get_current_span(self) -> Optional[Span]:
        """Get the currently active span."""
        return self._current_span

    @contextmanager
    def trace_operation(
        self,
        operation_name: str,
        kind: SpanKind = SpanKind.INTERNAL,
        parent_span: Optional[Span] = None,
        tags: Optional[Dict[str, str]] = None,
    ):
        """Context manager for tracing an operation."""
        parent = parent_span or self._current_span
        span = self.start_span(operation_name, parent, kind, tags)
        try:
            yield span
            self.finish_span(span, SpanStatus.OK)
        except Exception as e:
            span.add_log(f"Error occurred: {str(e)}", error=True)
            self.finish_span(span, SpanStatus.ERROR)
            raise

    def inject_trace_context(self, headers: Dict[str, str]) -> Dict[str, str]:
        """Inject trace context into HTTP headers for propagation."""
        result_headers = headers.copy()

        if self._current_span:
            result_headers["X-Trace-ID"] = self._current_span.trace_id
            result_headers["X-Span-ID"] = self._current_span.span_id
            result_headers["X-Parent-Span-ID"] = self._current_span.span_id

        return result_headers

    def extract_trace_context(self, headers: Dict[str, str]) -> Optional[Span]:
        """Extract trace context from HTTP headers."""
        trace_id = headers.get("X-Trace-ID")
        parent_span_id = headers.get("X-Parent-Span-ID")

        if trace_id and parent_span_id:
            # Create a parent span context for continuation
            parent_span = Span(
                trace_id=trace_id,
                span_id=parent_span_id,
                parent_span_id=None,
                operation_name="remote_parent",
                start_time=datetime.now(timezone.utc),
                service_name="remote",
            )
            return parent_span

        return None


# Global tracing collector instance
_tracing_collector: Optional[TracingCollector] = None


def get_tracing_collector(service_name: str = "unknown") -> TracingCollector:
    """Get or create the global tracing collector instance."""
    global _tracing_collector
    if _tracing_collector is None:
        _tracing_collector = TracingCollector(service_name)
    return _tracing_collector


def set_tracing_collector(collector: TracingCollector) -> None:
    """Set the global tracing collector instance."""
    global _tracing_collector
    _tracing_collector = collector
