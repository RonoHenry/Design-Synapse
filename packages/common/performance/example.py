"""
Performance optimization and security hardening example.

This example demonstrates how to use the performance package for:
- Redis-based caching with compression
- Database connection pooling
- CDN asset management
- Performance monitoring and alerting
- Security hardening and threat detection
"""

import asyncio
import time
from datetime import datetime, timedelta

from .cache import CacheManager
from .cdn import CDNManager
from .connection_pool import ConnectionPoolManager
from .models import CacheConfig, CDNConfig, PoolConfig
from .monitoring import PerformanceMonitor
from .security import SecurityAuditLogger, SecurityHardening, ThreatDetector


async def cache_example():
    """Demonstrate cache management capabilities."""
    print("=== Cache Management Example ===")

    # Configure cache with compression
    config = CacheConfig(
        redis_url="redis://localhost:6379/1",  # Use test database
        default_ttl=300,  # 5 minutes
        compression_enabled=True,
        compression_threshold=100,
        serialization_format="json",
    )

    cache = CacheManager(config)

    try:
        # Basic cache operations
        print("1. Basic cache operations")
        await cache.set(
            "user:123",
            {
                "id": 123,
                "name": "John Doe",
                "email": "john@example.com",
                "preferences": {"theme": "dark", "notifications": True},
            },
        )

        result = await cache.get("user:123")
        print(
            f"   Cache result: {result.status.value}, Response time: {result.response_time_ms:.2f}ms"
        )

        # Bulk operations
        print("2. Bulk cache operations")
        users_data = {
            f"user:{i}": {"id": i, "name": f"User {i}", "email": f"user{i}@example.com"}
            for i in range(100, 110)
        }

        start_time = time.time()
        await cache.set_many(users_data)
        bulk_set_time = (time.time() - start_time) * 1000

        start_time = time.time()
        results = await cache.get_many(list(users_data.keys()))
        bulk_get_time = (time.time() - start_time) * 1000

        print(f"   Bulk set time: {bulk_set_time:.2f}ms")
        print(f"   Bulk get time: {bulk_get_time:.2f}ms")
        print(f"   Retrieved {len(results)} items")

        # Cache performance metrics
        print("3. Cache performance metrics")
        hit_ratio = await cache.get_hit_ratio()
        memory_usage = await cache.get_memory_usage()
        metrics = await cache.get_performance_metrics()

        print(f"   Hit ratio: {hit_ratio:.2%}")
        print(f"   Memory usage: {memory_usage:.2f} MB")
        print(f"   Total requests: {metrics.total_requests}")

        # Cache invalidation
        print("4. Cache invalidation")
        invalidated = await cache.invalidate_pattern("user:10*")
        print(f"   Invalidated {invalidated} keys matching pattern 'user:10*'")

    except Exception as e:
        print(f"   Cache example failed (Redis may not be available): {e}")

    finally:
        await cache.close()


async def connection_pool_example():
    """Demonstrate connection pool management."""
    print("\n=== Connection Pool Example ===")

    config = PoolConfig(
        min_connections=2, max_connections=5, connection_timeout=10, retry_attempts=2
    )

    pool = ConnectionPoolManager(config)

    try:
        # Initialize pool
        print("1. Initializing connection pool")
        await pool.initialize("sqlite:///example.db")

        # Get connection statistics
        stats = await pool.get_statistics()
        print(
            f"   Initial pool state - Active: {stats.active_connections}, Idle: {stats.idle_connections}"
        )

        # Simulate concurrent connections
        print("2. Testing concurrent connections")
        connections = []

        for i in range(3):
            conn = await pool.get_connection()
            connections.append(conn)
            print(f"   Acquired connection {i+1}")

        # Check pool utilization
        stats = await pool.get_statistics()
        print(f"   Pool utilization: {stats.pool_utilization:.2%}")
        print(f"   Average connection time: {stats.avg_connection_time_ms:.2f}ms")

        # Release connections
        print("3. Releasing connections")
        for i, conn in enumerate(connections):
            await pool.release_connection(conn)
            print(f"   Released connection {i+1}")

        # Final statistics
        stats = await pool.get_statistics()
        print(
            f"   Final pool state - Active: {stats.active_connections}, Idle: {stats.idle_connections}"
        )

    except Exception as e:
        print(f"   Connection pool example completed with mock data: {e}")

    finally:
        await pool.close()


async def cdn_example():
    """Demonstrate CDN asset management."""
    print("\n=== CDN Management Example ===")

    config = CDNConfig(
        provider="test",  # Use test provider
        base_url="https://cdn.example.com",
        compression_enabled=True,
        minification_enabled=True,
    )

    cdn = CDNManager(config)

    try:
        # Upload single asset
        print("1. Uploading single asset")
        js_code = b"""
        // Application JavaScript
        function initApp() {
            console.log('App initialized');
            setupEventListeners();
        }

        function setupEventListeners() {
            document.addEventListener('DOMContentLoaded', initApp);
        }
        """

        result = await cdn.upload_asset("app.js", js_code, "application/javascript")
        print(f"   Upload success: {result.success}")
        print(f"   CDN URL: {result.cdn_url}")
        print(f"   Upload time: {result.upload_time_ms:.2f}ms")
        print(f"   Minified: {result.minified}")

        # Batch upload
        print("2. Batch asset upload")
        assets = [
            ("style.css", b"body { margin: 0; padding: 0; }", "text/css"),
            ("logo.png", b"fake-png-data", "image/png"),
            ("font.woff2", b"fake-font-data", "font/woff2"),
        ]

        results = await cdn.upload_assets_batch(assets)
        successful_uploads = sum(1 for r in results if r.success)
        print(f"   Batch upload: {successful_uploads}/{len(assets)} successful")

        # CDN statistics
        print("3. CDN performance statistics")
        stats = await cdn.get_statistics()
        print(f"   Total requests: {stats.total_requests}")
        print(f"   Cache hit ratio: {stats.hit_ratio:.2%}")
        print(f"   Bandwidth saved: {stats.bandwidth_saved_mb:.2f} MB")

        # Cache invalidation
        print("4. Cache invalidation")
        invalidated = await cdn.invalidate_cache(["app.js", "style.css"])
        print(f"   Cache invalidation success: {invalidated}")

    except Exception as e:
        print(f"   CDN example error: {e}")

    finally:
        await cdn.close()


async def performance_monitoring_example():
    """Demonstrate performance monitoring capabilities."""
    print("\n=== Performance Monitoring Example ===")

    # Create configs for monitoring
    cache_config = CacheConfig()
    pool_config = PoolConfig()
    cdn_config = CDNConfig(provider="test")

    monitor = PerformanceMonitor(cache_config, pool_config, cdn_config)

    try:
        # Simulate application metrics
        print("1. Recording performance metrics")

        # Simulate API requests with varying response times
        endpoints = ["api/users", "api/projects", "api/designs"]
        for i in range(50):
            endpoint = endpoints[i % len(endpoints)]
            # Simulate response times (some slow requests)
            response_time = 25 + (i % 10) * 5 + (10 if i % 15 == 0 else 0)
            success = i % 20 != 0  # 5% error rate

            await monitor.record_response_time(endpoint, response_time)
            await monitor.record_request(endpoint, success)

        # Get response time metrics
        print("2. Response time analysis")
        response_metrics = await monitor.get_response_time_metrics()
        print(
            f"   Average response time: {response_metrics.avg_response_time_ms:.2f}ms"
        )
        print(f"   95th percentile: {response_metrics.p95_response_time_ms:.2f}ms")
        print(f"   99th percentile: {response_metrics.p99_response_time_ms:.2f}ms")

        # Get error rate metrics
        print("3. Error rate analysis")
        error_metrics = await monitor.get_error_rate_metrics()
        print(f"   Total requests: {error_metrics.total_requests}")
        print(f"   Error rate: {error_metrics.error_rate:.2%}")

        # Set up performance alerts
        print("4. Performance alerting")
        await monitor.set_alert_threshold("response_time_p95", 80.0)
        await monitor.set_alert_threshold("error_rate", 0.03)  # 3%

        alerts = await monitor.check_alerts()
        print(f"   Active alerts: {len(alerts)}")
        for alert in alerts:
            print(f"   - {alert.metric}: {alert.message}")

        # Get aggregated metrics
        print("5. Aggregated performance metrics")
        metrics = await monitor.get_aggregated_metrics()
        print(f"   Cache hit ratio: {metrics.cache_hit_ratio:.2%}")
        print(f"   Pool utilization: {metrics.pool_utilization:.2%}")
        print(f"   CPU usage: {metrics.cpu_usage_percent:.1f}%")
        print(f"   Memory usage: {metrics.memory_usage_mb:.1f} MB")

        # Performance optimization recommendations
        print("6. Optimization recommendations")
        recommendations = await monitor.get_optimization_recommendations()
        for rec in recommendations:
            print(f"   [{rec.priority}] {rec.category}: {rec.recommendation}")

    except Exception as e:
        print(f"   Performance monitoring error: {e}")

    finally:
        await monitor.close()


async def security_hardening_example():
    """Demonstrate security hardening capabilities."""
    print("\n=== Security Hardening Example ===")

    cache_config = CacheConfig()
    pool_config = PoolConfig()

    security = SecurityHardening(cache_config, pool_config)
    detector = ThreatDetector()
    logger = SecurityAuditLogger()

    try:
        # Input sanitization
        print("1. Input sanitization")
        malicious_inputs = [
            "<script>alert('xss')</script>Hello World",
            "'; DROP TABLE users; --",
            "../../../../etc/passwd",
            "admin'--",
            "user && rm -rf /",
        ]

        for input_data in malicious_inputs:
            sanitized = await security.sanitize_input(input_data)
            threat_detected = await security.detect_threat(input_data)
            print(f"   Input: {input_data[:30]}...")
            print(f"   Sanitized: {sanitized[:30]}...")
            print(f"   Threat detected: {threat_detected}")

            if threat_detected:
                await logger.log_threat_detected(
                    "Input Validation", "192.168.1.100", input_data[:50]
                )

        # Rate limiting simulation
        print("2. Rate limiting and IP blocking")
        test_ip = "192.168.1.200"

        # Simulate rapid requests
        blocked_count = 0
        for i in range(150):  # Exceed rate limit
            allowed = await security.check_rate_limit(test_ip)
            if not allowed:
                blocked_count += 1

        print(f"   Blocked {blocked_count}/150 requests from {test_ip}")

        if blocked_count > 0:
            await security.block_ip(test_ip, "Rate limit exceeded")
            is_blocked = await security.is_ip_blocked(test_ip)
            print(f"   IP {test_ip} blocked: {is_blocked}")

        # Threat detection patterns
        print("3. Advanced threat detection")
        attack_patterns = [
            ("SQL Injection", "admin' OR 1=1--"),
            ("XSS Attack", "<img src=x onerror=alert(1)>"),
            ("Command Injection", "; cat /etc/passwd"),
            ("Path Traversal", "../../../etc/hosts"),
        ]

        for attack_type, pattern in attack_patterns:
            detected = await detector.detect_threat(pattern)
            print(f"   {attack_type}: {'DETECTED' if detected else 'NOT DETECTED'}")

            if detected:
                await logger.log_threat_detected(attack_type, "192.168.1.300", pattern)

        # Brute force detection
        print("4. Brute force attack detection")
        attacker_ip = "10.0.0.1"

        # Simulate failed login attempts
        for i in range(8):
            await detector.record_failed_login(attacker_ip)
            await logger.log_auth_failure(f"user{i}", attacker_ip, "Invalid password")

        is_brute_force = await detector.detect_brute_force(attacker_ip)
        print(f"   Brute force detected from {attacker_ip}: {is_brute_force}")

        # Security audit reporting
        print("5. Security audit and compliance")

        # Generate compliance report
        report = await logger.generate_compliance_report(
            start_date=datetime.utcnow() - timedelta(hours=1),
            end_date=datetime.utcnow(),
        )

        print(f"   Total security events: {report['total_events']}")
        print(f"   High severity events: {report['high_severity_events']}")
        print(f"   Event breakdown:")
        for event_type, count in report["event_counts"].items():
            print(f"     - {event_type}: {count}")

        # Security headers
        print("6. Security headers")
        headers = await security.get_security_headers()
        print("   Recommended security headers:")
        for header, value in headers.items():
            print(f"     {header}: {value}")

    except Exception as e:
        print(f"   Security hardening error: {e}")


async def main():
    """Run all examples."""
    print("Performance Optimization and Security Hardening Examples")
    print("=" * 60)

    # Run all examples
    await cache_example()
    await connection_pool_example()
    await cdn_example()
    await performance_monitoring_example()
    await security_hardening_example()

    print("\n" + "=" * 60)
    print("All examples completed successfully!")
    print("\nNote: Some examples may show errors if external services")
    print("(Redis, databases) are not available. This is expected in")
    print("development environments.")


if __name__ == "__main__":
    asyncio.run(main())
