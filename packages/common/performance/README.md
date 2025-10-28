# Performance Optimization Package

This package provides comprehensive performance optimization and security hardening capabilities for the DesignSynapse platform.

## Features

### 🚀 Performance Optimization
- **Redis-based Caching**: High-performance caching with compression and multiple serialization formats
- **Connection Pooling**: Optimized database connection management with health monitoring
- **CDN Integration**: Multi-provider CDN support for static asset delivery
- **Performance Monitoring**: Real-time metrics collection and alerting

### 🔒 Security Hardening
- **Input Validation**: Advanced sanitization against SQL injection, XSS, and command injection
- **Threat Detection**: Real-time threat pattern recognition and blocking
- **Rate Limiting**: DDoS protection with IP-based rate limiting
- **Security Auditing**: Comprehensive audit logging and compliance reporting

## Quick Start

### Cache Management

```python
from packages.common.performance import CacheManager, CacheConfig

# Configure cache
config = CacheConfig(
    redis_url="redis://localhost:6379/0",
    default_ttl=3600,
    compression_enabled=True
)

# Initialize cache manager
cache = CacheManager(config)

# Basic operations
await cache.set("user:123", {"name": "John", "email": "john@example.com"})
result = await cache.get("user:123")
print(f"Cache hit: {result.status}, Value: {result.value}")

# Bulk operations
data = {
    "user:124": {"name": "Jane"},
    "user:125": {"name": "Bob"}
}
await cache.set_many(data)
results = await cache.get_many(["user:124", "user:125"])
```

### Connection Pool Management

```python
from packages.common.performance import ConnectionPoolManager, PoolConfig

# Configure connection pool
config = PoolConfig(
    min_connections=5,
    max_connections=20,
    connection_timeout=30
)

# Initialize pool manager
pool = ConnectionPoolManager(config)
await pool.initialize("postgresql://user:pass@localhost/db")

# Get connection
connection = await pool.get_connection()
result = await connection.execute("SELECT * FROM users")
await pool.release_connection(connection)

# Get pool statistics
stats = await pool.get_statistics()
print(f"Pool utilization: {stats.pool_utilization:.2%}")
```

### CDN Integration

```python
from packages.common.performance import CDNManager, CDNConfig

# Configure CDN
config = CDNConfig(
    provider="cloudflare",
    base_url="https://cdn.example.com",
    api_key="your-api-key",
    compression_enabled=True
)

# Initialize CDN manager
cdn = CDNManager(config)

# Upload asset
with open("app.js", "rb") as f:
    result = await cdn.upload_asset("app.js", f.read(), "application/javascript")
    print(f"CDN URL: {result.cdn_url}")

# Batch upload
assets = [
    ("style.css", css_data, "text/css"),
    ("logo.png", png_data, "image/png")
]
results = await cdn.upload_assets_batch(assets)

# Invalidate cache
await cdn.invalidate_cache(["app.js", "style.css"])
```

### Performance Monitoring

```python
from packages.common.performance import PerformanceMonitor

# Initialize monitor
monitor = PerformanceMonitor(cache_config, pool_config, cdn_config)

# Record metrics
await monitor.record_response_time("api/users", 45.2)
await monitor.record_request("api/users", success=True)

# Get aggregated metrics
metrics = await monitor.get_aggregated_metrics()
print(f"Cache hit ratio: {metrics.cache_hit_ratio:.2%}")
print(f"Avg response time: {metrics.avg_response_time_ms:.2f}ms")

# Set up alerts
await monitor.set_alert_threshold("response_time_p95", 100.0)
alerts = await monitor.check_alerts()

# Get dashboard data
dashboard = await monitor.get_dashboard_data()
```

### Security Hardening

```python
from packages.common.performance import SecurityHardening, ThreatDetector

# Initialize security
security = SecurityHardening(cache_config, pool_config)

# Input sanitization
user_input = "<script>alert('xss')</script>Hello"
sanitized = await security.sanitize_input(user_input)
print(f"Sanitized: {sanitized}")  # Output: "Hello"

# Threat detection
threat_detected = await security.detect_threat("' OR 1=1--")
print(f"Threat detected: {threat_detected}")  # Output: True

# Rate limiting
allowed = await security.check_rate_limit("192.168.1.100")
if not allowed:
    await security.block_ip("192.168.1.100", "Rate limit exceeded")

# Security headers
headers = await security.get_security_headers()
```

### Security Audit Logging

```python
from packages.common.performance import SecurityAuditLogger

# Initialize audit logger
logger = SecurityAuditLogger()

# Log security events
await logger.log_threat_detected("SQL Injection", "192.168.1.50", "' OR 1=1--")
await logger.log_auth_failure("user123", "192.168.1.50", "Invalid password")

# Generate compliance report
report = await logger.generate_compliance_report(
    start_date=datetime.now() - timedelta(days=30),
    end_date=datetime.now()
)
print(f"Total security events: {report['total_events']}")

# Set up real-time alerts
await logger.set_alert_threshold("failed_logins", 5, timedelta(minutes=5))
alerts = await logger.get_active_alerts()
```

## Configuration

### Cache Configuration

```python
CacheConfig(
    redis_url="redis://localhost:6379/0",
    default_ttl=3600,                    # Default TTL in seconds
    max_memory="100mb",                  # Redis memory limit
    eviction_policy="allkeys-lru",       # Eviction policy
    key_prefix="cache:",                 # Key prefix
    compression_enabled=True,            # Enable compression
    compression_threshold=1024,          # Compression threshold in bytes
    serialization_format="json"          # json, pickle, msgpack
)
```

### Pool Configuration

```python
PoolConfig(
    min_connections=5,                   # Minimum pool size
    max_connections=20,                  # Maximum pool size
    max_idle_time=300,                   # Max idle time in seconds
    max_lifetime=3600,                   # Max connection lifetime
    connection_timeout=30,               # Connection timeout
    retry_attempts=3,                    # Retry attempts
    health_check_interval=60,            # Health check interval
    pool_pre_ping=True                   # Enable pre-ping
)
```

### CDN Configuration

```python
CDNConfig(
    provider="cloudflare",               # cloudflare, aws, azure
    base_url="https://cdn.example.com",
    api_key="your-api-key",
    zone_id="your-zone-id",
    cache_ttl=86400,                     # Cache TTL in seconds
    compression_enabled=True,            # Enable compression
    minification_enabled=True,           # Enable minification
    supported_formats=[                  # Supported file formats
        "js", "css", "png", "jpg", "gif", "svg", "woff", "woff2"
    ]
)
```

## Performance Metrics

The package tracks comprehensive performance metrics:

- **Cache Metrics**: Hit/miss ratios, memory usage, response times
- **Database Metrics**: Connection pool utilization, query performance
- **CDN Metrics**: Upload success rates, bandwidth savings
- **System Metrics**: CPU usage, memory consumption
- **Security Metrics**: Threat detection rates, blocked IPs

## Security Features

### Input Validation
- SQL injection prevention
- XSS attack mitigation
- Command injection blocking
- Path traversal protection

### Threat Detection
- Pattern-based threat recognition
- Brute force attack detection
- Geographic anomaly detection
- Real-time IP blocking

### Audit Logging
- Comprehensive security event logging
- Compliance reporting (SOX, GDPR, HIPAA)
- Real-time alerting
- Log retention management

## Testing

Run the test suite:

```bash
# Run all tests
python -m pytest packages/common/performance/tests/ -v

# Run specific test categories
python -m pytest packages/common/performance/tests/test_cache.py -v
python -m pytest packages/common/performance/tests/test_security_hardening.py -v

# Run with coverage
python -m pytest packages/common/performance/tests/ --cov=packages.common.performance
```

## Dependencies

- `redis`: Redis client for caching
- `aiohttp`: HTTP client for CDN operations
- `sqlalchemy`: Database connection pooling
- `psutil`: System metrics collection (optional)

## License

This package is part of the DesignSynapse platform and follows the same licensing terms.
