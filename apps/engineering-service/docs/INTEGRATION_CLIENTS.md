# External Service Integration Clients

## Overview

This document describes the external service integration clients implemented for the Engineering Service. These clients provide resilient, cached communication with four external platform services.

## Implemented Clients

### 1. ArchitecturalServiceClient

**Purpose:** Retrieve architectural designs and subscribe to design changes.

**Key Methods:**
- `get_design(design_id, use_cache=True)` - Retrieve architectural design by ID
- `get_space_requirements(project_id, use_cache=True)` - Get space requirements for MEP sizing
- `subscribe_to_design_changes(design_id, callback)` - Subscribe to design change notifications
- `get_design_version(design_id, version)` - Retrieve specific version of design

**Configuration:**
- Base URL: `settings.architectural_service_url` (default: http://localhost:8005)
- Timeout: 30 seconds
- Max Retries: 3
- Cache TTL: 300 seconds (5 minutes)

### 2. DesignServiceClient

**Purpose:** Update technical requirements and retrieve technical drawings.

**Key Methods:**
- `update_technical_requirements(design_id, requirements)` - Update technical drawing requirements
- `get_drawings(project_id, use_cache=True)` - Retrieve technical drawings for a project
- `get_design(design_id, use_cache=True)` - Retrieve design by ID
- `create_technical_specification(design_id, specification_data)` - Create technical specification

**Configuration:**
- Base URL: `settings.design_service_url` (default: http://localhost:8001)
- Timeout: 30 seconds
- Max Retries: 3
- Cache TTL: 300 seconds (5 minutes)

### 3. KnowledgeServiceClient

**Purpose:** Retrieve engineering codes, standards, formulas, and technical references.

**Key Methods:**
- `get_code_requirements(code_type, jurisdiction, version=None)` - Retrieve code requirements
- `search_code_sections(code_type, search_query, jurisdiction=None)` - Search for specific code sections
- `get_engineering_formula(formula_name, discipline=None)` - Retrieve engineering formula by name
- `search_formulas(query, discipline=None, limit=10)` - Search engineering formulas
- `get_material_properties(material_name, material_type=None)` - Retrieve material properties
- `get_standard_reference(standard_name)` - Retrieve engineering standard reference

**Configuration:**
- Base URL: `settings.knowledge_service_url` (default: http://localhost:8002)
- Timeout: 30 seconds
- Max Retries: 3

### 4. ProjectServiceClient

**Purpose:** Update engineering milestones and retrieve project information.

**Key Methods:**
- `get_project_info(project_id, use_cache=True)` - Retrieve project information
- `update_milestone(project_id, milestone_data)` - Update engineering milestone status
- `get_milestones(project_id, use_cache=True)` - Get all milestones for a project
- `create_milestone(project_id, milestone_data)` - Create a new engineering milestone
- `get_project_team(project_id, use_cache=True)` - Get project team members

**Configuration:**
- Base URL: `settings.project_service_url` (default: http://localhost:8003)
- Timeout: 30 seconds
- Max Retries: 3
- Cache TTL: 300 seconds (5 minutes)

## Features

### 1. Response Caching (Requirements 6.6)

All clients support Redis-based response caching:

```python
# Cache is used by default
design = await client.get_design(design_id)

# Bypass cache if needed
design = await client.get_design(design_id, use_cache=False)
```

**Cache Keys:**
- ArchitecturalServiceClient: `arch_design:{design_id}`, `arch_spaces:{project_id}`
- DesignServiceClient: `design:{design_id}`, `design_drawings:{project_id}`
- ProjectServiceClient: `project:{project_id}`, `project_milestones:{project_id}`, `project_team:{project_id}`

**Cache Invalidation:**
- Automatic invalidation on updates (PUT/POST operations)
- Pattern-based invalidation using Redis SCAN
- Graceful degradation if cache is unavailable

### 2. Retry Logic with Exponential Backoff (Requirements 6.5)

Built into the BaseHTTPClient from `packages/common/http/base_client.py`:

- Maximum retries: 3 (configurable)
- Exponential backoff: 1s, 2s, 4s
- Automatic retry on transient errors (timeouts, connection errors)
- No retry on client errors (4xx)

### 3. Circuit Breaker Pattern (Requirements 6.5)

Built into the BaseHTTPClient:

- Failure threshold: 5 failures (configurable via `settings.circuit_breaker_failure_threshold`)
- Recovery timeout: 60 seconds (configurable via `settings.circuit_breaker_timeout`)
- States: CLOSED (normal), OPEN (failing), HALF_OPEN (testing recovery)
- Automatic state transitions

### 4. Error Handling

All clients handle errors gracefully:

```python
try:
    design = await client.get_design(design_id)
except httpx.HTTPError as e:
    logger.error(f"Failed to fetch design: {e}")
    # Handle error appropriately
```

**Error Types:**
- `httpx.HTTPError` - HTTP-level errors (4xx, 5xx)
- `httpx.TimeoutException` - Request timeout
- `httpx.ConnectError` - Connection failure

### 5. Async Context Manager Support

All clients support async context managers for automatic resource cleanup:

```python
async with ArchitecturalServiceClient() as client:
    design = await client.get_design(design_id)
# Client is automatically closed
```

## Usage Examples

### Example 1: Retrieve Architectural Design

```python
from src.integrations import ArchitecturalServiceClient
import redis.asyncio as redis

# Create Redis client for caching
redis_client = redis.from_url(settings.redis_url)

# Create client
async with ArchitecturalServiceClient(redis_client=redis_client) as client:
    # Get design with caching
    design = await client.get_design(design_id)

    # Get space requirements
    spaces = await client.get_space_requirements(project_id)
```

### Example 2: Update Technical Requirements

```python
from src.integrations import DesignServiceClient

async with DesignServiceClient() as client:
    requirements = {
        "structural_loads": {
            "dead_load": 100,
            "live_load": 50,
        },
        "mep_requirements": {
            "hvac": "central",
            "electrical": "3-phase",
        },
    }

    result = await client.update_technical_requirements(
        design_id, requirements
    )
```

### Example 3: Retrieve Code Requirements

```python
from src.integrations import KnowledgeServiceClient

async with KnowledgeServiceClient() as client:
    # Get structural code requirements
    code_reqs = await client.get_code_requirements(
        code_type="structural",
        jurisdiction="California",
    )

    # Search for specific code sections
    sections = await client.search_code_sections(
        code_type="structural",
        search_query="load combinations",
    )
```

### Example 4: Update Project Milestone

```python
from src.integrations import ProjectServiceClient

async with ProjectServiceClient() as client:
    milestone_data = {
        "milestone_id": str(milestone_id),
        "status": "completed",
        "completion_date": "2024-01-15",
        "notes": "Engineering calculations completed",
    }

    result = await client.update_milestone(
        project_id, milestone_data
    )
```

## Testing

Comprehensive unit tests are provided for all clients:

```bash
# Run all integration client tests
pytest apps/engineering-service/tests/unit/integrations/ -v

# Run specific client tests
pytest apps/engineering-service/tests/unit/integrations/test_architectural_service_client.py -v
```

**Test Coverage:**
- ArchitecturalServiceClient: 86%
- DesignServiceClient: 86%
- KnowledgeServiceClient: 87%
- ProjectServiceClient: 84%

**Test Scenarios:**
- Successful API calls
- Cache hit/miss scenarios
- HTTP error handling
- Cache failure graceful degradation
- Context manager lifecycle
- Async generator support for cache invalidation

## Configuration

All clients use settings from `src/core/config.py`:

```python
# External Services
architectural_service_url: str = "http://localhost:8005"
design_service_url: str = "http://localhost:8001"
knowledge_service_url: str = "http://localhost:8002"
project_service_url: str = "http://localhost:8003"

# Circuit Breaker
circuit_breaker_failure_threshold: int = 5
circuit_breaker_timeout: int = 60
circuit_breaker_half_open_timeout: int = 30

# Retry
retry_max_attempts: int = 3
retry_backoff_factor: float = 2.0
retry_max_delay: int = 60

# Redis
redis_url: str = "redis://localhost:6379/1"
redis_cache_ttl: int = 300  # 5 minutes
```

## Dependencies

- `httpx` - Async HTTP client
- `redis.asyncio` - Async Redis client for caching
- `packages/common/http/base_client.py` - Base HTTP client with retry and circuit breaker
- `packages/common/resilience/retry.py` - Retry logic
- `packages/common/resilience/circuit_breaker.py` - Circuit breaker pattern

## Future Enhancements

1. **WebSocket Support** - Real-time design change notifications
2. **Webhook Registration** - Subscribe to events via webhooks
3. **Request Batching** - Batch multiple requests for efficiency
4. **Metrics Collection** - Track request latency, cache hit rates, circuit breaker state
5. **Request Deduplication** - Prevent duplicate concurrent requests
6. **Adaptive Timeouts** - Adjust timeouts based on historical performance

## Troubleshooting

### Cache Issues

If caching is not working:
1. Verify Redis is running: `redis-cli ping`
2. Check Redis URL in settings
3. Review logs for cache warnings
4. Clients gracefully degrade if cache is unavailable

### Connection Errors

If experiencing connection errors:
1. Verify external services are running
2. Check service URLs in settings
3. Review circuit breaker state
4. Check network connectivity

### Timeout Issues

If requests are timing out:
1. Increase timeout in client initialization
2. Check external service performance
3. Review retry configuration
4. Consider increasing circuit breaker threshold

## Related Documentation

- [Engineering Service Design](../.kiro/specs/engineering-service/design.md)
- [Engineering Service Requirements](../.kiro/specs/engineering-service/requirements.md)
- [Common HTTP Client](../../packages/common/http/README.md)
- [Resilience Patterns](../../packages/common/resilience/README.md)
