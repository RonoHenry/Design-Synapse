# Service Registry

A comprehensive service registry implementation with health monitoring and service discovery capabilities for the DesignSynapse infrastructure.

## Features

- **Service Registration**: Register services with metadata, tags, and health check endpoints
- **Health Monitoring**: Automatic periodic health checks with configurable intervals and failure thresholds
- **Service Discovery**: Find services based on various filter criteria (name, health status, tags, response time)
- **Load Balancing**: Get healthy endpoints with basic load balancing
- **Automatic Cleanup**: Remove stale services that haven't been seen for a configurable timeout
- **Health Aggregation**: System-wide health status reporting
- **REST API**: FastAPI endpoints for all registry operations

## Components

### Models (`models.py`)
- `ServiceInfo`: Service registration information
- `ServiceEndpoint`: Service endpoint with health status
- `HealthCheck`: Individual health check result
- `SystemHealthStatus`: System-wide health status
- `ServiceRegistrationRequest`: Registration request model
- `ServiceDiscoveryFilter`: Service discovery filter criteria

### Health Checker (`health_checker.py`)
- Periodic health checks for registered services
- Configurable failure and recovery thresholds
- Health status change callbacks
- Automatic service deregistration on prolonged failures

### Service Registry (`registry.py`)
- Core service registry functionality
- Service registration and deregistration
- Service discovery with filtering
- Health status aggregation
- Concurrent operation support

### API Endpoints (`api.py`)
- `POST /registry/register`: Register a service
- `POST /registry/deregister`: Deregister a service
- `GET /registry/discover`: Discover services with filters
- `GET /registry/services/{service_name}/healthy`: Get a healthy endpoint
- `GET /registry/services/{service_name}/instances`: Get all service instances
- `GET /registry/health`: Get system health status
- `GET /registry/services`: Get all registered services

## Usage

### Basic Service Registration

```python
from packages.common.service_registry import ServiceRegistry, ServiceInfo, ServiceRegistrationRequest

# Create service info
service_info = ServiceInfo(
    name="my-service",
    version="1.0.0",
    host="localhost",
    port=8000,
    health_check_url="/health",
    metadata={"env": "production"},
    tags=["api", "web"]
)

# Create registration request
request = ServiceRegistrationRequest(
    service=service_info,
    health_check_interval=30,  # seconds
    failure_threshold=3
)

# Register service
async with ServiceRegistry() as registry:
    instance_id = await registry.register_service(request)
    print(f"Registered service with instance ID: {instance_id}")
```

### Service Discovery

```python
from packages.common.service_registry import ServiceDiscoveryFilter, HealthStatus

# Discover healthy API services
filter_criteria = ServiceDiscoveryFilter(
    tags=["api"],
    health_status=HealthStatus.HEALTHY,
    max_response_time=100.0
)

endpoints = await registry.discover_services(filter_criteria)
for endpoint in endpoints:
    print(f"Found service: {endpoint.service_name} at {endpoint.url}")
```

### Health Monitoring

```python
# Get system health
health_status = await registry.get_system_health()
print(f"System status: {health_status.status}")
print(f"Healthy services: {health_status.healthy_services}/{health_status.total_services}")

# Get healthy endpoint for load balancing
endpoint = await registry.get_healthy_endpoint("my-service")
if endpoint:
    print(f"Use endpoint: {endpoint.url}")
```

### Using the REST API

```python
import httpx

# Register a service
registration_data = {
    "service": {
        "name": "my-service",
        "version": "1.0.0",
        "host": "localhost",
        "port": 8000,
        "health_check_url": "/health"
    },
    "health_check_interval": 30,
    "failure_threshold": 3
}

async with httpx.AsyncClient() as client:
    response = await client.post("/registry/register", json=registration_data)
    result = response.json()
    print(f"Instance ID: {result['instance_id']}")
```

## Configuration

### Environment Variables

- `SERVICE_REGISTRY_HOST`: Registry host (default: localhost)
- `SERVICE_REGISTRY_PORT`: Registry port (default: 8080)
- `HEALTH_CHECK_INTERVAL`: Default health check interval in seconds (default: 30)
- `FAILURE_THRESHOLD`: Default failure threshold (default: 3)
- `CLEANUP_INTERVAL`: Cleanup interval in seconds (default: 300)
- `STALE_SERVICE_TIMEOUT`: Stale service timeout in seconds (default: 600)

### Service Registry Configuration

```python
registry = ServiceRegistry(
    default_health_check_interval=30,  # seconds
    default_failure_threshold=3,       # consecutive failures
    cleanup_interval=300,              # cleanup every 5 minutes
    stale_service_timeout=600          # remove services after 10 minutes
)
```

### Health Checker Configuration

```python
health_checker = HealthChecker(
    check_interval=30,        # seconds between checks
    timeout=10.0,            # HTTP request timeout
    failure_threshold=3,      # failures before marking unhealthy
    recovery_threshold=2      # successes needed for recovery
)
```

## Testing

The service registry includes comprehensive tests covering:

- Model validation and serialization
- Service registration and deregistration
- Health checking and monitoring
- Service discovery with various filters
- Concurrent operations
- API endpoint functionality
- Error handling and edge cases

Run tests with:

```bash
pytest packages/common/service_registry/tests/ -v
```

## Integration with Existing Services

To integrate with existing services in the DesignSynapse ecosystem:

1. **Service Startup**: Register the service on startup
2. **Health Endpoint**: Implement a `/health` endpoint
3. **Graceful Shutdown**: Deregister on shutdown
4. **Service Discovery**: Use the registry to find other services

Example integration:

```python
from fastapi import FastAPI
from packages.common.service_registry import get_service_registry, ServiceInfo, ServiceRegistrationRequest

app = FastAPI()

@app.on_event("startup")
async def startup():
    registry = await get_service_registry()
    service_info = ServiceInfo(
        name="user-service",
        version="1.0.0",
        host="localhost",
        port=8001,
        health_check_url="/health"
    )
    request = ServiceRegistrationRequest(service=service_info)
    await registry.register_service(request)

@app.get("/health")
async def health():
    return {"status": "healthy", "timestamp": datetime.utcnow()}

@app.on_event("shutdown")
async def shutdown():
    registry = await get_service_registry()
    await registry.deregister_service("user-service")
```

## Requirements

The Service Registry addresses the following requirements from the infrastructure specification:

- **Requirement 1.2**: Service registration and deregistration endpoints
- **Requirement 1.3**: Health check monitoring with configurable intervals
- **Requirement 1.6**: Service discovery with filtering capabilities
- **Requirement 3.3**: Health status aggregation and reporting

## Architecture

The Service Registry follows a modular architecture:

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   API Layer     │    │  Service Registry │    │ Health Checker  │
│   (FastAPI)     │◄──►│   (Core Logic)   │◄──►│  (Monitoring)   │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                        │                        │
         ▼                        ▼                        ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│     Models      │    │   Data Storage   │    │   HTTP Client   │
│  (Pydantic)     │    │  (In-Memory)     │    │    (httpx)      │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

This implementation provides a solid foundation for service discovery and health monitoring in the DesignSynapse infrastructure, enabling reliable service-to-service communication and system observability.
