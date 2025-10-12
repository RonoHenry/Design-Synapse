# Service Client Infrastructure

This package provides HTTP client utilities for inter-service communication in the DesignSynapse platform.

**Note**: Due to Python's built-in `http` module, import this package as `common.http` from the workspace root, not as a standalone module.

## Features

- **Retry Mechanism**: Automatic retry with exponential backoff for transient failures
- **Circuit Breaker**: Prevents cascade failures by opening circuit after threshold failures
- **Request/Response Logging**: Comprehensive logging for debugging
- **Typed Clients**: Type-safe clients for each service
- **Service Registry**: Centralized service configuration management
- **Timeout Configuration**: Configurable timeouts for all requests

## Components

### BaseHTTPClient

Base HTTP client with retry, circuit breaker, and logging capabilities.

```python
from common.http import BaseHTTPClient

client = BaseHTTPClient(
    base_url="http://service:8000",
    timeout=30.0,
    max_retries=3,
    circuit_breaker_threshold=5,
    circuit_breaker_timeout=60
)

# Make requests
result = await client.get("/api/endpoint")
result = await client.post("/api/endpoint", json={"data": "value"})
```

### Service Registry

Manages service configurations and endpoints.

```python
from common.http import ServiceRegistry, ServiceConfig

registry = ServiceRegistry()

# Get service configuration
config = registry.get("user-service")
print(config.base_url)  # http://localhost:8001/api/v1

# Register custom service
registry.register(ServiceConfig(
    name="custom-service",
    host="custom.example.com",
    port=9000,
    protocol="https"
))
```

### Typed Service Clients

Type-safe clients for each service with domain-specific methods.

#### UserServiceClient

```python
from common.http import UserServiceClient

client = UserServiceClient()

# Get user
user = await client.get_user(user_id=1)

# Create user
new_user = await client.create_user({
    "email": "user@example.com",
    "username": "user123",
    "password": "secure_password"
})

# Authenticate
auth_data = await client.authenticate("user@example.com", "password")

# Get user roles
roles = await client.get_user_roles(user_id=1)
```

#### ProjectServiceClient

```python
from common.http import ProjectServiceClient

client = ProjectServiceClient()

# Get project
project = await client.get_project(project_id=1)

# Create project
new_project = await client.create_project({
    "name": "New Project",
    "description": "Project description",
    "owner_id": 1
})

# List projects
projects = await client.list_projects(skip=0, limit=10)

# Get project comments
comments = await client.get_project_comments(project_id=1)

# Create comment
comment = await client.create_comment(
    project_id=1,
    comment_data={"content": "Great project!"}
)
```

#### KnowledgeServiceClient

```python
from common.http import KnowledgeServiceClient

client = KnowledgeServiceClient()

# Get resource
resource = await client.get_resource(resource_id=1)

# Search resources
results = await client.search_resources(
    query="building codes",
    resource_type="pdf",
    limit=20
)

# Get project resources
resources = await client.get_project_resources(project_id=1)

# Create citation
citation = await client.create_citation(
    resource_id=1,
    project_id=1,
    context="Used for structural design"
)

# Get recommendations
recommendations = await client.get_recommendations(project_id=1)
```

## Configuration

Service endpoints are configured via environment variables:

```bash
# User Service
USER_SERVICE_HOST=localhost
USER_SERVICE_PORT=8001
USER_SERVICE_PROTOCOL=http

# Project Service
PROJECT_SERVICE_HOST=localhost
PROJECT_SERVICE_PORT=8003
PROJECT_SERVICE_PROTOCOL=http

# Knowledge Service
KNOWLEDGE_SERVICE_HOST=localhost
KNOWLEDGE_SERVICE_PORT=8002
KNOWLEDGE_SERVICE_PROTOCOL=http
```

## Circuit Breaker

The circuit breaker prevents cascade failures by monitoring request failures:

1. **CLOSED** (Normal): Requests pass through normally
2. **OPEN** (Failing): After threshold failures, circuit opens and rejects requests immediately
3. **HALF_OPEN** (Testing): After timeout, allows one request to test if service recovered

```python
client = BaseHTTPClient(
    base_url="http://service:8000",
    circuit_breaker_threshold=5,  # Open after 5 failures
    circuit_breaker_timeout=60     # Wait 60s before testing recovery
)
```

## Retry Logic

Automatic retry with exponential backoff for transient failures:

- **Retry on**: Timeout, connection errors
- **No retry on**: HTTP 4xx/5xx errors (fail fast)
- **Backoff**: 1s, 2s, 4s, 8s, etc.

```python
client = BaseHTTPClient(
    base_url="http://service:8000",
    max_retries=3  # Retry up to 3 times
)
```

## Logging

All requests and responses are logged for debugging:

```
INFO: Request: GET http://service:8000/api/endpoint (attempt 1/3)
INFO: Response: GET http://service:8000/api/endpoint - 200
WARNING: Transient error on attempt 1: Timeout
INFO: Retrying in 1s...
```

## Error Handling

```python
from common.http import UserServiceClient

client = UserServiceClient()

try:
    user = await client.get_user(user_id=999)
except httpx.HTTPStatusError as e:
    # HTTP error (404, 500, etc.)
    print(f"HTTP error: {e.response.status_code}")
except Exception as e:
    # Circuit breaker open, timeout, etc.
    print(f"Request failed: {e}")
```

## Testing

Mock the HTTP client in tests:

```python
from unittest.mock import AsyncMock, patch
from common.http import UserServiceClient

async def test_get_user():
    client = UserServiceClient()
    
    with patch.object(client, 'get', new_callable=AsyncMock) as mock_get:
        mock_get.return_value = {"id": 1, "email": "test@example.com"}
        
        user = await client.get_user(user_id=1)
        
        assert user["id"] == 1
        mock_get.assert_called_once_with("/users/1")
```

## Best Practices

1. **Reuse Clients**: Create client instances once and reuse them
2. **Close Clients**: Always close clients when done (use context managers)
3. **Configure Timeouts**: Set appropriate timeouts for your use case
4. **Monitor Circuit Breaker**: Log circuit breaker state changes
5. **Handle Errors**: Always handle potential errors gracefully
6. **Use Typed Clients**: Prefer typed clients over base client for better IDE support

## Example: Complete Usage

```python
from common.http import UserServiceClient, ProjectServiceClient

async def create_project_for_user(user_email: str, project_name: str):
    """Create a project for a user."""
    user_client = UserServiceClient()
    project_client = ProjectServiceClient()
    
    try:
        # Authenticate user
        auth_data = await user_client.authenticate(user_email, "password")
        user_id = auth_data["user_id"]
        
        # Create project
        project = await project_client.create_project({
            "name": project_name,
            "description": "New project",
            "owner_id": user_id
        })
        
        return project
        
    finally:
        # Clean up
        await user_client.close()
        await project_client.close()
```
