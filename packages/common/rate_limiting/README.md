# Rate Limiting System

A comprehensive rate limiting system with multiple algorithms and storage backends for FastAPI applications.

## Features

- **Multiple Algorithms**: Sliding window and token bucket rate limiting
- **Flexible Storage**: In-memory and Redis storage backends
- **Per-Client & Per-Endpoint**: Configurable rate limits for different clients and endpoints
- **FastAPI Integration**: Middleware for easy integration with FastAPI applications
- **Comprehensive Monitoring**: Rate limit status tracking and quota monitoring

## Quick Start

### Basic Usage with Middleware

```python
from fastapi import FastAPI
from packages.common.rate_limiting import (
    RateLimitMiddleware,
    RateLimitConfig,
    RateLimitStrategy,
    InMemoryStorage
)

app = FastAPI()

# Configure rate limiting
default_config = RateLimitConfig(
    requests_per_window=100,
    window_size_seconds=3600,  # 1 hour
    strategy=RateLimitStrategy.SLIDING_WINDOW
)

# Add middleware
app.add_middleware(
    RateLimitMiddleware,
    storage=InMemoryStorage(),
    default_config=default_config,
    endpoint_configs={
        "/api/v1/upload": RateLimitConfig(
            requests_per_window=10,
            window_size_seconds=60,  # 1 minute
            strategy=RateLimitStrategy.TOKEN_BUCKET,
            burst_capacity=15,
            refill_rate=0.2  # 0.2 tokens per second
        )
    }
)
```

### Using Redis Storage

```python
import redis.asyncio as redis
from packages.common.rate_limiting import RedisStorage

# Create Redis client
redis_client = redis.Redis(host='localhost', port=6379, db=0)

# Use Redis storage
app.add_middleware(
    RateLimitMiddleware,
    storage=RedisStorage(redis_client),
    default_config=default_config
)
```

## Rate Limiting Algorithms

### Sliding Window

The sliding window algorithm maintains a count of requests within a time window that slides continuously.

```python
config = RateLimitConfig(
    requests_per_window=100,
    window_size_seconds=3600,
    strategy=RateLimitStrategy.SLIDING_WINDOW
)
```

**Characteristics:**
- Smooth rate limiting without burst allowance
- Memory efficient
- Good for steady-state rate limiting

### Token Bucket

The token bucket algorithm allows for burst traffic up to a configured capacity, with tokens refilled at a steady rate.

```python
config = RateLimitConfig(
    requests_per_window=100,
    window_size_seconds=3600,
    strategy=RateLimitStrategy.TOKEN_BUCKET,
    burst_capacity=150,  # Allow bursts up to 150 requests
    refill_rate=0.028    # ~100 requests per hour
)
```

**Characteristics:**
- Allows burst traffic
- More flexible for varying traffic patterns
- Good for APIs with occasional high-volume usage

## Configuration Options

### RateLimitConfig

- `requests_per_window`: Maximum requests allowed in the time window
- `window_size_seconds`: Time window duration in seconds
- `strategy`: Rate limiting algorithm (SLIDING_WINDOW or TOKEN_BUCKET)
- `burst_capacity`: Maximum tokens in bucket (token bucket only)
- `refill_rate`: Token refill rate per second (token bucket only)

### Middleware Options

- `storage`: Storage backend for rate limit data
- `default_config`: Default rate limit configuration
- `endpoint_configs`: Per-endpoint rate limit configurations
- `client_id_extractor`: Function to extract client ID from request
- `skip_paths`: List of paths to skip rate limiting

## Client ID Extraction

By default, the middleware extracts client IDs in this order:
1. User ID from authenticated request (`user:123`)
2. IP address from request (`ip:192.168.1.1`)

You can provide a custom extractor:

```python
def custom_client_id_extractor(request: Request) -> str:
    # Extract from API key header
    api_key = request.headers.get("X-API-Key")
    if api_key:
        return f"api_key:{api_key}"

    # Fall back to default behavior
    return f"ip:{request.client.host}"

app.add_middleware(
    RateLimitMiddleware,
    client_id_extractor=custom_client_id_extractor,
    # ... other config
)
```

## Per-Endpoint Configuration

Configure different rate limits for specific endpoints:

```python
endpoint_configs = {
    # Exact path and method match
    "POST:/api/v1/upload": RateLimitConfig(
        requests_per_window=5,
        window_size_seconds=60
    ),

    # Path-only match (applies to all methods)
    "/api/v1/search": RateLimitConfig(
        requests_per_window=50,
        window_size_seconds=60
    ),

    # Method-only match (applies to all paths)
    "POST": RateLimitConfig(
        requests_per_window=20,
        window_size_seconds=60
    )
}
```

## Rate Limit Headers

The middleware automatically adds standard rate limit headers to responses:

- `X-RateLimit-Limit`: Maximum requests allowed in window
- `X-RateLimit-Remaining`: Remaining requests in current window
- `X-RateLimit-Reset`: Unix timestamp when rate limit resets
- `Retry-After`: Seconds to wait before retry (when rate limited)

## Error Handling

When rate limits are exceeded, the middleware raises a `RateLimitError` which is handled by the error handling framework:

```json
{
  "message": "Rate limit exceeded. Try again in 30 seconds.",
  "error_code": "RATE_LIMIT_EXCEEDED",
  "details": {
    "retry_after": 30
  },
  "request_id": "abc123",
  "timestamp": "2023-10-01T12:00:00Z"
}
```

## Storage Backends

### InMemoryStorage

- **Use case**: Development, testing, single-instance deployments
- **Pros**: No external dependencies, fast
- **Cons**: Not shared across instances, data lost on restart

### RedisStorage

- **Use case**: Production, multi-instance deployments
- **Pros**: Shared across instances, persistent, atomic operations
- **Cons**: Requires Redis server

## Monitoring and Observability

The rate limiting system integrates with the error handling and logging framework:

- Rate limit violations are logged with context
- Metrics can be collected on rate limit usage
- Request IDs enable tracing rate limited requests

## Best Practices

1. **Choose the Right Algorithm**:
   - Use sliding window for steady-state rate limiting
   - Use token bucket for APIs that need to handle bursts

2. **Set Appropriate Limits**:
   - Consider your system's capacity
   - Account for legitimate usage patterns
   - Set different limits for different user tiers

3. **Monitor Rate Limit Usage**:
   - Track rate limit violations
   - Monitor quota utilization
   - Adjust limits based on usage patterns

4. **Handle Rate Limit Errors Gracefully**:
   - Provide clear error messages
   - Include retry-after information
   - Implement client-side retry logic

5. **Use Redis in Production**:
   - Ensures consistency across multiple instances
   - Provides better performance for high-traffic scenarios
   - Enables rate limit data persistence
