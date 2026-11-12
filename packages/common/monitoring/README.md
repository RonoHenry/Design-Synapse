# Monitoring Infrastructure

This package provides centralized monitoring capabilities for the DesignSynapse infrastructure, including structured logging, metrics collection, and health check aggregation.

## Features

### 1. Structured Logging with Correlation IDs

- **Structured JSON logging** for all services
- **Request correlation IDs** for tracing requests across services
- **Context variables** for user ID, request ID, and correlation ID
- **Centralized log aggregation** with filtering and search capabilities

### 2. Metrics Collection

- **HTTP request metrics** (duration, error rates, request counts)
- **Custom counters, gauges, and histograms**
- **Performance monitoring** with percentile calculations
- **Time-based aggregation** and filtering

### 3. Health Check Aggregation

- **System-wide health monitoring**
- **Service health status aggregation**
- **Health history tracking**
- **Configurable health check endpoints**

### 4. Distributed Tracing

- **Request flow tracking** across service boundaries
- **OpenTelemetry-compatible** span creation and management
- **Trace context propagation** via HTTP headers
- **Performance monitoring** with span duration tracking
- **Error tracking** with automatic error status setting

## Quick Start

```python
from packages.common.monitoring import (
    get_logger, get_metrics_collector, get_health_aggregator, get_tracing_collector,
    set_correlation_id, set_request_id, set_user_id
)

# Structured logging
logger = get_logger("my-service")
set_correlation_id("req-123")
set_request_id("request-456")
set_user_id("user-789")

logger.info("Processing request", operation="create_user", user_count=1)
logger.log_request("POST", "/api/users", 201, 150.5)

# Metrics collection
metrics = get_metrics_collector()
metrics.record_request_duration("my-service", "/api/users", "POST", 201, 150.5)
metrics.record_counter("users_created_total", 1.0, {"service": "my-service"})

# Health monitoring
health = get_health_aggregator()
services = [
    {"name": "user-service", "health_endpoint": "http://localhost:8001/health"}
]
system_health = await health.check_all_services_health(services)

# Distributed tracing
tracer = get_tracing_collector("my-service")
with tracer.trace_operation("handle_request") as span:
    span.add_tag("http.method", "POST")
    span.add_tag("user.id", "user-123")
    span.add_log("Processing request")

    # Nested operation
    with tracer.trace_operation("database_query") as db_span:
        db_span.add_tag("db.table", "users")
        # ... perform database operation
```

## Components

### LogAggregator

Centralized log collection and filtering:

```python
from packages.common.monitoring.log_aggregator import LogAggregator, LogFilters

aggregator = LogAggregator()
filters = LogFilters(service="my-service", level=LogLevel.ERROR)
error_logs = aggregator.get_logs(filters)
```

### MetricsCollector

Performance and business metrics:

```python
from packages.common.monitoring.metrics import MetricsCollector

collector = MetricsCollector()

# Record different metric types
collector.record_counter("requests_total", 1.0, {"endpoint": "/api/users"})
collector.record_gauge("active_connections", 25.0)
collector.record_histogram("request_duration_ms", 150.0)

# Get aggregated data
error_rate = collector.get_error_rate("my-service", "/api/users")
avg_time = collector.get_average_response_time("my-service")
```

### HealthAggregator

System health monitoring:

```python
from packages.common.monitoring.health import HealthAggregator

aggregator = HealthAggregator()

# Check individual service
service_health = await aggregator.check_service_health(
    "user-service",
    "http://localhost:8001/health"
)

# Check all services
services = [
    {"name": "user-service", "health_endpoint": "http://localhost:8001/health"},
    {"name": "project-service", "health_endpoint": "http://localhost:8002/health"}
]
system_health = await aggregator.check_all_services_health(services)
```

### TracingCollector

Distributed request tracing:

```python
from packages.common.monitoring.tracing import TracingCollector, SpanKind

collector = TracingCollector("my-service")

# Basic span creation
span = collector.start_span("operation_name")
span.add_tag("key", "value")
span.add_log("Operation started")
collector.finish_span(span)

# Context manager (recommended)
with collector.trace_operation("operation_name", SpanKind.SERVER) as span:
    span.add_tag("http.method", "GET")
    span.add_log("Processing request")

    # Nested operations
    with collector.trace_operation("database_query", SpanKind.CLIENT) as db_span:
        db_span.add_tag("db.table", "users")
        # ... perform operation

# Cross-service propagation
headers = collector.inject_trace_context({"Authorization": "Bearer token"})
# Send headers to another service

# In receiving service
parent_span = collector.extract_trace_context(headers)
with collector.trace_operation("handle_request", parent_span=parent_span) as span:
    # This span will be part of the same trace
    pass
```

## Data Models

### LogEntry

```python
@dataclass
class LogEntry:
    timestamp: datetime
    level: LogLevel
    service: str
    message: str
    request_id: Optional[str] = None
    user_id: Optional[str] = None
    correlation_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
```

### MetricPoint

```python
@dataclass
class MetricPoint:
    name: str
    value: float
    labels: Dict[str, str] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)
```

### ServiceHealth

```python
@dataclass
class ServiceHealth:
    service_name: str
    status: HealthStatus
    message: str
    timestamp: datetime
    response_time_ms: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
```

### Span

```python
@dataclass
class Span:
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
```

### Trace

```python
@dataclass
class Trace:
    trace_id: str
    spans: List[Span] = field(default_factory=list)
    root_span: Optional[Span] = None
```

## Context Management

The monitoring system uses context variables to track request correlation across service boundaries:

```python
from packages.common.monitoring.log_aggregator import (
    set_correlation_id, set_request_id, set_user_id,
    get_correlation_id, get_request_id, get_user_id
)

# Set context at request start
correlation_id = set_correlation_id()  # Auto-generates UUID
request_id = set_request_id("custom-request-id")
set_user_id("user-123")

# Context is automatically included in all logs
logger.info("Processing request")  # Will include correlation_id, request_id, user_id

# Get context in other parts of the code
current_correlation = get_correlation_id()
```

## Integration with Services

### FastAPI Integration

```python
from fastapi import FastAPI, Request
from packages.common.monitoring import get_logger, get_metrics_collector
from packages.common.monitoring.log_aggregator import set_correlation_id, set_request_id

app = FastAPI()
logger = get_logger("my-service")
metrics = get_metrics_collector()

@app.middleware("http")
async def monitoring_middleware(request: Request, call_next):
    # Set request context
    correlation_id = request.headers.get("X-Correlation-ID") or set_correlation_id()
    request_id = set_request_id()

    start_time = time.time()
    response = await call_next(request)
    duration_ms = (time.time() - start_time) * 1000

    # Log request
    logger.log_request(
        request.method,
        str(request.url.path),
        response.status_code,
        duration_ms
    )

    # Record metrics
    metrics.record_request_duration(
        "my-service",
        str(request.url.path),
        request.method,
        response.status_code,
        duration_ms
    )

    return response
```

### Health Check Endpoint

```python
from fastapi import FastAPI
from packages.common.monitoring import get_health_aggregator

app = FastAPI()
health_aggregator = get_health_aggregator()

@app.get("/health")
async def health_check():
    services = [
        {"name": "database", "health_endpoint": "http://localhost:5432/health"},
        {"name": "redis", "health_endpoint": "http://localhost:6379/health"}
    ]

    return await health_aggregator.create_basic_health_endpoint_response(services)
```

### Distributed Tracing Integration

```python
from fastapi import FastAPI, Request
from packages.common.monitoring import get_tracing_collector, SpanKind

app = FastAPI()
tracer = get_tracing_collector("my-service")

@app.middleware("http")
async def tracing_middleware(request: Request, call_next):
    # Extract trace context from incoming headers
    parent_span = tracer.extract_trace_context(dict(request.headers))

    with tracer.trace_operation(
        f"{request.method} {request.url.path}",
        SpanKind.SERVER,
        parent_span
    ) as span:
        span.add_tag("http.method", request.method)
        span.add_tag("http.url", str(request.url))
        span.add_tag("http.user_agent", request.headers.get("user-agent", ""))

        response = await call_next(request)

        span.add_tag("http.status_code", str(response.status_code))
        if response.status_code >= 400:
            span.add_log(f"HTTP error: {response.status_code}")

        # Inject trace context into response headers
        trace_headers = tracer.inject_trace_context({})
        for key, value in trace_headers.items():
            response.headers[key] = value

        return response

@app.get("/api/users/{user_id}")
async def get_user(user_id: str):
    # Current span is automatically available
    current_span = tracer.get_current_span()
    if current_span:
        current_span.add_tag("user.id", user_id)
        current_span.add_log("Fetching user data")

    # Nested operation
    with tracer.trace_operation("database_query", SpanKind.CLIENT) as db_span:
        db_span.add_tag("db.operation", "SELECT")
        db_span.add_tag("db.table", "users")
        # ... perform database query

    return {"user_id": user_id, "name": "John Doe"}
```

## Testing

Run the test suite:

```bash
python -m pytest packages/common/monitoring/tests/ -v
```

Run the example demonstration:

```bash
python packages/common/monitoring/example.py
```

## Requirements

This package addresses the following infrastructure requirements:

- **Requirement 3.1**: Centralized log collection with structured formatting
- **Requirement 3.2**: Request duration and error rate metrics tracking
- **Requirement 3.3**: Health check aggregation across services
- **Requirement 3.4**: Request tracing with correlation IDs across services
- **Requirement 3.6**: Distributed tracing for request flow visibility

## Architecture

The monitoring infrastructure follows a modular design:

```
monitoring/
├── models.py          # Data models and enums
├── log_aggregator.py  # Structured logging and correlation
├── metrics.py         # Metrics collection and aggregation
├── health.py          # Health check aggregation
├── example.py         # Usage demonstration
└── tests/             # Comprehensive test suite
```

Each component can be used independently or together as part of the complete monitoring solution.
