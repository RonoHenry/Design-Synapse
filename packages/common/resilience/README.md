# Resilience Patterns

This package provides circuit breaker and retry mechanisms to handle service failures gracefully and prevent cascading failures in distributed systems.

## Features

- **Circuit Breaker Pattern**: Prevents cascading failures by stopping requests to failing services
- **Retry with Exponential Backoff**: Automatically retries failed requests with configurable strategies
- **Monitoring and Metrics**: Comprehensive monitoring of resilience patterns
- **Thread-Safe**: All components are thread-safe for concurrent usage

## Circuit Breaker

The circuit breaker pattern prevents cascading failures by monitoring service health and stopping requests when failures exceed a threshold.

### States

- **CLOSED**: Normal operation, requests pass through
- **OPEN**: Service is failing, requests are rejected immediately
- **HALF_OPEN**: Testing if service has recovered

### Usage

```python
from packages.common.resilience import CircuitBreaker, CircuitBreakerConfig

# Create circuit breaker
config = CircuitBreakerConfig(
    failure_threshold=5,      # Open after 5 failures
    recovery_timeout=60,      # Wait 60s before trying half-open
    success_threshold=3,      # Close after 3 successes in half-open
    timeout=30               # Request timeout
)

breaker = CircuitBreaker("user-service", config)

# Use with function calls
try:
    result = breaker.call(some_service_call, arg1, arg2)
except CircuitBreakerOpenException:
    # Handle circuit breaker open
    return fallback_response()

# Use with async functions
try:
    result = await breaker.call_async(async_service_call, arg1, arg2)
except CircuitBreakerOpenException:
    return fallback_response()
```

### Decorator Usage

```python
from packages.common.resilience import circuit_breaker, CircuitBreakerConfig

config = CircuitBreakerConfig(failure_threshold=3)

@circuit_breaker("payment-service", config)
def process_payment(amount, card_token):
    # This function is protected by circuit breaker
    return payment_api.charge(amount, card_token)

@circuit_breaker("notification-service")
async def send_notification(user_id, message):
    # Uses default configuration
    return await notification_api.send(user_id, message)
```

## Retry with Exponential Backoff

Automatically retries failed requests with configurable strategies and jitter to prevent thundering herd problems.

### Usage

```python
from packages.common.resilience import RetryConfig, retry_with_backoff

# Configure retry behavior
config = RetryConfig(
    max_attempts=3,
    base_delay=1.0,
    max_delay=60.0,
    exponential_base=2.0,
    jitter=True,
    retryable_status_codes=[502, 503, 504],
    retryable_exceptions=[ConnectionError, TimeoutError]
)

@retry_with_backoff(config)
def unreliable_service_call():
    # This function will be retried on failure
    return external_api.get_data()

# Direct function calls
from packages.common.resilience import retry_async_call, retry_sync_call

result = await retry_async_call(async_function, arg1, arg2, config=config)
result = retry_sync_call(sync_function, arg1, arg2, config=config)
```

## Monitoring

Monitor the health and performance of resilience patterns:

```python
from packages.common.resilience.monitoring import get_resilience_monitor

monitor = get_resilience_monitor()

# Get current metrics
metrics = monitor.get_current_metrics()

# Get health summary
health = monitor.get_health_summary()
print(f"Overall health score: {health['overall_health_score']}")

# Get circuit breaker status
cb_metrics = monitor.get_circuit_breaker_metrics()
for name, metrics in cb_metrics.items():
    print(f"{name}: {metrics.state} (failure rate: {metrics.failure_rate:.2%})")
```

## Integration with API Gateway

The resilience patterns integrate seamlessly with the API Gateway:

```python
from packages.common.resilience import CircuitBreaker, RetryConfig, retry_with_backoff

class ServiceClient:
    def __init__(self, service_name: str):
        self.service_name = service_name
        self.circuit_breaker = CircuitBreaker(
            service_name,
            CircuitBreakerConfig(failure_threshold=5)
        )
        self.retry_config = RetryConfig(max_attempts=3)

    @retry_with_backoff(retry_config)
    async def make_request(self, endpoint: str, data: dict):
        return await self.circuit_breaker.call_async(
            self._http_request, endpoint, data
        )

    async def _http_request(self, endpoint: str, data: dict):
        # Actual HTTP request implementation
        pass
```

## Configuration

### Circuit Breaker Configuration

- `failure_threshold`: Number of failures before opening (default: 5)
- `recovery_timeout`: Seconds to wait before trying half-open (default: 60)
- `success_threshold`: Successes needed to close from half-open (default: 3)
- `timeout`: Request timeout in seconds (default: 30)

### Retry Configuration

- `max_attempts`: Maximum retry attempts (default: 3)
- `base_delay`: Base delay in seconds (default: 1.0)
- `max_delay`: Maximum delay in seconds (default: 60.0)
- `exponential_base`: Exponential backoff multiplier (default: 2.0)
- `jitter`: Add randomness to prevent thundering herd (default: True)
- `retryable_status_codes`: HTTP status codes to retry (default: [502, 503, 504])
- `retryable_exceptions`: Exception types to retry (default: [ConnectionError, TimeoutError])

## Best Practices

1. **Choose appropriate thresholds**: Set failure thresholds based on your service's normal error rate
2. **Use jitter**: Always enable jitter in retry configurations to prevent thundering herd
3. **Monitor metrics**: Regularly check circuit breaker and retry metrics
4. **Implement fallbacks**: Always have fallback responses for when circuit breakers are open
5. **Test failure scenarios**: Regularly test how your system behaves under failure conditions
6. **Combine patterns**: Use circuit breakers and retries together for maximum resilience

## Error Handling

The package provides specific exceptions for different failure scenarios:

- `CircuitBreakerOpenException`: Raised when circuit breaker is open
- Standard exceptions are re-raised after retry attempts are exhausted

Always handle these exceptions appropriately in your application code.
