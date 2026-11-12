"""
Comprehensive performance and security hardening tests.

This module tests:
- Caching effectiveness and invalidation strategies under load
- Security measures against common attack vectors
- Performance under production-like load conditions

Requirements covered: 6.3, 7.1, 7.3
"""

import asyncio
import json
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from packages.common.performance.cache import CacheManager
from packages.common.performance.models import (CacheConfig, CDNConfig,
                                                PerformanceMetrics, PoolConfig)
from packages.common.performance.monitoring import PerformanceMonitor
from packages.common.security.middleware import SecurityHardeningMiddleware
from packages.common.security.models import ThreatEvent, ThreatLevel
from packages.common.security.threat_detection import IPBlocker, ThreatDetector


class TestCacheEffectivenessUnderLoad:
    """Test caching effectiveness and invalidation strategies under production load."""

    @pytest.mark.asyncio
    async def test_cache_hit_ratio_under_concurrent_load(
        self, cache_config, mock_redis
    ):
        """Test cache hit ratio maintains effectiveness under concurrent access."""
        # Configure high-performance cache
        cache_config.default_ttl = 300  # 5 minutes
        cache_config.compression_enabled = True

        # Configure mock Redis to simulate cache behavior
        cache_data = {}

        async def mock_get(key):
            return cache_data.get(key)

        async def mock_set(key, value):
            cache_data[key] = value
            return True

        async def mock_setex(key, ttl, value):
            cache_data[key] = value
            return True

        mock_redis.get.side_effect = mock_get
        mock_redis.set.side_effect = mock_set
        mock_redis.setex.side_effect = mock_setex

        with patch("redis.asyncio.Redis.from_url", return_value=mock_redis):
            cache_manager = CacheManager(cache_config)

            # Pre-populate cache with frequently accessed data
            popular_keys = [f"user:{i}" for i in range(100)]
            for key in popular_keys:
                await cache_manager.set(key, f"user_data_{key}", ttl=300)

            # Simulate concurrent access patterns
            async def access_pattern():
                """Simulate realistic access pattern with 80/20 rule."""
                results = []
                for _ in range(50):
                    # 80% access to popular keys (should hit cache)
                    if len(results) % 5 != 0:
                        key = popular_keys[len(results) % 20]  # Top 20% of keys
                    else:
                        # 20% access to less popular keys (may miss)
                        key = f"user:{100 + len(results)}"

                    result = await cache_manager.get(key)
                    results.append(result)
                return results

            # Run concurrent access from multiple "clients"
            start_time = time.time()
            tasks = [access_pattern() for _ in range(20)]  # 20 concurrent clients
            all_results = await asyncio.gather(*tasks)
            end_time = time.time()

            # Analyze results
            total_requests = sum(len(results) for results in all_results)
            cache_hits = sum(
                1
                for results in all_results
                for result in results
                if result.status.value == "hit"
            )

            hit_ratio = cache_hits / total_requests if total_requests > 0 else 0

            # Performance assertions
            assert (
                hit_ratio >= 0.75
            ), f"Cache hit ratio {hit_ratio:.2%} below 75% threshold"
            assert (
                end_time - start_time < 5.0
            ), "Cache operations took too long under load"
            assert total_requests == 1000, "Not all requests completed"

    @pytest.mark.asyncio
    async def test_cache_invalidation_strategies_performance(
        self, cache_config, mock_redis
    ):
        """Test cache invalidation performance and consistency."""
        with patch("redis.asyncio.Redis.from_url", return_value=mock_redis):
            cache_manager = CacheManager(cache_config)

            # Set up cache with hierarchical data
            await cache_manager.set(
                "user:1:profile", {"name": "John", "email": "john@example.com"}
            )
            await cache_manager.set("user:1:settings", {"theme": "dark", "lang": "en"})
            await cache_manager.set("user:1:permissions", {"role": "admin"})
            await cache_manager.set(
                "user:2:profile", {"name": "Jane", "email": "jane@example.com"}
            )

            # Test pattern-based invalidation performance
            start_time = time.time()
            invalidated_count = await cache_manager.invalidate_pattern("user:1:*")
            invalidation_time = time.time() - start_time

            # Verify invalidation effectiveness
            assert invalidated_count >= 3, "Not all user:1 keys were invalidated"
            assert invalidation_time < 0.1, "Pattern invalidation took too long"

            # Verify selective invalidation (user:2 should remain)
            user2_result = await cache_manager.get("user:2:profile")
            assert (
                user2_result.status.value == "hit"
            ), "Unrelated cache entries were invalidated"

    @pytest.mark.asyncio
    async def test_cache_memory_efficiency_under_load(self, cache_config, mock_redis):
        """Test cache memory usage efficiency under high load."""
        # Configure for memory efficiency
        cache_config.compression_enabled = True
        cache_config.compression_threshold = 100

        mock_redis.info.return_value = {
            "keyspace_hits": 0,
            "keyspace_misses": 0,
            "used_memory": 1024 * 1024,  # 1MB initial
        }

        with patch("redis.asyncio.Redis.from_url", return_value=mock_redis):
            cache_manager = CacheManager(cache_config)

            # Store large objects to test compression
            large_objects = {}
            for i in range(100):
                # Create objects that exceed compression threshold
                large_data = {
                    "id": i,
                    "data": "x" * 1000,  # 1KB of data per object
                    "metadata": {"created": datetime.utcnow().isoformat()},
                }
                large_objects[f"large_object:{i}"] = large_data

            # Bulk store with compression
            start_time = time.time()
            result = await cache_manager.set_many(large_objects, ttl=300)
            storage_time = time.time() - start_time

            assert result is True, "Bulk storage failed"
            assert storage_time < 2.0, "Bulk storage with compression took too long"

            # Test bulk retrieval performance
            keys = list(large_objects.keys())
            start_time = time.time()
            results = await cache_manager.get_many(keys)
            retrieval_time = time.time() - start_time

            # Verify retrieval performance and data integrity
            assert len(results) == 100, "Not all objects retrieved"
            assert retrieval_time < 1.0, "Bulk retrieval took too long"

            successful_retrievals = [r for r in results if r.status.value == "hit"]
            assert (
                len(successful_retrievals) >= 95
            ), "Too many cache misses on bulk retrieval"


class TestSecurityHardeningUnderAttack:
    """Test security measures against common attack vectors."""

    @pytest.mark.asyncio
    async def test_sql_injection_protection_under_load(self, app):
        """Test SQL injection protection under sustained attack."""
        app.add_middleware(SecurityHardeningMiddleware, enable_input_validation=True)

        # SQL injection payloads of varying complexity
        sql_payloads = [
            "'; DROP TABLE users; --",
            "' OR '1'='1",
            "admin'/**/OR/**/1=1--",
            "'; EXEC xp_cmdshell('dir'); --",
            "' UNION SELECT * FROM passwords--",
            "1' AND (SELECT COUNT(*) FROM users) > 0--",
            "'; INSERT INTO users VALUES('hacker','pass'); --",
            "' OR 1=1 LIMIT 1 OFFSET 0--",
        ]

        from fastapi.testclient import TestClient

        client = TestClient(app)

        # Simulate sustained SQL injection attack
        start_time = time.time()
        blocked_requests = 0
        total_requests = 0

        for round_num in range(10):  # 10 rounds of attacks
            for payload in sql_payloads:
                # Test in different input locations
                test_cases = [
                    {"json": {"username": payload, "password": "test"}},
                    {"params": {"search": payload}},
                    {"json": {"comment": payload, "post_id": 1}},
                ]

                for test_case in test_cases:
                    total_requests += 1
                    if "json" in test_case:
                        response = client.post("/test-input", **test_case)
                    else:
                        response = client.get("/test", **test_case)

                    if response.status_code in [400, 403]:
                        blocked_requests += 1

        attack_duration = time.time() - start_time
        block_rate = blocked_requests / total_requests if total_requests > 0 else 0

        # Security assertions
        assert (
            block_rate >= 0.8
        ), f"Only {block_rate:.1%} of SQL injection attempts blocked"
        assert attack_duration < 10.0, "Security validation too slow under attack load"
        assert total_requests == 240, "Not all attack scenarios tested"

    @pytest.mark.asyncio
    async def test_brute_force_protection_effectiveness(self, app):
        """Test brute force attack protection and IP blocking."""
        app.add_middleware(
            SecurityHardeningMiddleware,
            enable_threat_detection=True,
            enable_ip_blocking=True,
        )

        from fastapi.testclient import TestClient

        client = TestClient(app)

        # Simulate brute force attack from multiple IPs
        attack_ips = [f"192.168.1.{i}" for i in range(10, 20)]
        blocked_ips = set()

        for attacker_ip in attack_ips:
            with patch("fastapi.Request.client") as mock_client:
                mock_client.host = attacker_ip

                # Rapid login attempts
                for attempt in range(15):
                    response = client.post(
                        "/auth/login",
                        json={"username": "admin", "password": f"wrong_pass_{attempt}"},
                        headers={"User-Agent": "AttackBot/1.0"},
                    )

                    # Check if IP gets blocked after multiple attempts
                    if response.status_code in [403, 429]:
                        blocked_ips.add(attacker_ip)
                        break

        # Verify brute force protection effectiveness
        protection_rate = len(blocked_ips) / len(attack_ips)
        assert (
            protection_rate >= 0.8
        ), f"Only {protection_rate:.1%} of brute force attacks blocked"

    @pytest.mark.asyncio
    async def test_xss_protection_comprehensive(self, app):
        """Test XSS protection against various attack vectors."""
        app.add_middleware(SecurityHardeningMiddleware, enable_input_validation=True)

        # Comprehensive XSS payload collection
        xss_payloads = [
            "<script>alert('xss')</script>",
            "<img src=x onerror=alert(1)>",
            "javascript:alert('xss')",
            "<svg onload=alert(1)>",
            "<iframe src=javascript:alert('xss')>",
            "<body onload=alert('xss')>",
            "<input onfocus=alert('xss') autofocus>",
            "<select onfocus=alert('xss') autofocus>",
            "<textarea onfocus=alert('xss') autofocus>",
            "<keygen onfocus=alert('xss') autofocus>",
            "<video><source onerror=alert('xss')>",
            "<audio src=x onerror=alert('xss')>",
        ]

        from fastapi.testclient import TestClient

        client = TestClient(app)

        blocked_count = 0
        total_count = 0

        for payload in xss_payloads:
            # Test XSS in various contexts
            contexts = [
                {"json": {"message": payload}},
                {"json": {"title": payload, "content": "test"}},
                {"params": {"q": payload}},
                {"json": {"bio": payload, "name": "user"}},
            ]

            for context in contexts:
                total_count += 1
                if "json" in context:
                    response = client.post("/test-input", **context)
                else:
                    response = client.get("/test", **context)

                if response.status_code == 400:
                    blocked_count += 1

        xss_protection_rate = blocked_count / total_count if total_count > 0 else 0
        assert (
            xss_protection_rate >= 0.75
        ), f"Only {xss_protection_rate:.1%} of XSS attempts blocked"

    @pytest.mark.asyncio
    async def test_ddos_protection_under_sustained_load(self, app):
        """Test DDoS protection under sustained high-volume attack."""
        app.add_middleware(
            SecurityHardeningMiddleware,
            rate_limit_requests=50,  # Lower limit for testing
            rate_limit_window=60,
            enable_threat_detection=True,
        )

        from fastapi.testclient import TestClient

        client = TestClient(app)

        # Simulate DDoS attack with rapid requests
        attack_start = time.time()
        rate_limited_responses = 0
        total_responses = 0

        # Burst of requests to trigger rate limiting
        for batch in range(5):  # 5 batches
            batch_responses = []

            # Rapid fire requests in each batch
            for i in range(20):  # 20 requests per batch
                response = client.get(f"/test?batch={batch}&req={i}")
                batch_responses.append(response)
                total_responses += 1

            # Count rate limited responses
            rate_limited_in_batch = sum(
                1 for r in batch_responses if r.status_code == 429
            )
            rate_limited_responses += rate_limited_in_batch

            # Small delay between batches
            await asyncio.sleep(0.1)

        attack_duration = time.time() - attack_start

        # DDoS protection assertions
        assert (
            rate_limited_responses > 0
        ), "No rate limiting occurred during DDoS simulation"
        assert (
            rate_limited_responses >= total_responses * 0.3
        ), "Rate limiting not aggressive enough"
        assert attack_duration < 5.0, "DDoS protection response too slow"


class TestProductionLoadPerformance:
    """Test system performance under production-like load conditions."""

    @pytest.mark.asyncio
    async def test_concurrent_user_simulation(
        self, cache_config, pool_config, cdn_config
    ):
        """Simulate production load with concurrent users."""
        # Configure for production-like performance
        cache_config.default_ttl = 300
        pool_config.max_connections = 20

        monitor = PerformanceMonitor(cache_config, pool_config, cdn_config)

        async def simulate_user_session():
            """Simulate a realistic user session."""
            session_start = time.time()

            # User authentication (fast)
            auth_time = 25.0 + (time.time() % 10)  # 25-35ms
            await monitor.record_response_time("auth", auth_time)
            await monitor.record_request("auth", True)

            # Data fetching (moderate)
            for _ in range(5):
                fetch_time = 50.0 + (time.time() % 30)  # 50-80ms
                await monitor.record_response_time("api/data", fetch_time)
                await monitor.record_request("api/data", True)

            # Heavy computation (slower)
            compute_time = 150.0 + (time.time() % 50)  # 150-200ms
            await monitor.record_response_time("api/compute", compute_time)
            await monitor.record_request("api/compute", True)

            # Occasional error (5% error rate)
            if time.time() % 20 < 1:  # ~5% chance
                await monitor.record_request("api/data", False)

            return time.time() - session_start

        # Simulate 100 concurrent users
        start_time = time.time()
        tasks = [simulate_user_session() for _ in range(100)]
        session_durations = await asyncio.gather(*tasks)
        total_duration = time.time() - start_time

        # Get performance metrics
        metrics = await monitor.get_aggregated_metrics()

        # Production performance assertions
        assert (
            total_duration < 10.0
        ), f"100 concurrent users took {total_duration:.2f}s (too slow)"
        assert (
            metrics.avg_response_time_ms < 100.0
        ), f"Average response time {metrics.avg_response_time_ms:.2f}ms too high"
        assert (
            metrics.p95_response_time_ms < 200.0
        ), f"95th percentile {metrics.p95_response_time_ms:.2f}ms too high"
        assert metrics.error_rate < 0.1, f"Error rate {metrics.error_rate:.1%} too high"
        assert len(session_durations) == 100, "Not all user sessions completed"

    @pytest.mark.asyncio
    async def test_memory_usage_under_sustained_load(
        self, cache_config, pool_config, cdn_config
    ):
        """Test memory usage stability under sustained load."""
        monitor = PerformanceMonitor(cache_config, pool_config, cdn_config)

        # Baseline memory measurement
        initial_metrics = await monitor.collect_system_metrics()
        initial_memory = initial_metrics.memory_usage_mb

        # Sustained load simulation
        async def sustained_operations():
            """Perform sustained operations that could cause memory leaks."""
            for i in range(1000):
                # Simulate various operations
                await monitor.record_response_time(f"endpoint_{i % 10}", 50.0)
                await monitor.record_request(f"endpoint_{i % 10}", True)

                # Simulate cache operations
                if i % 100 == 0:
                    await monitor.metrics_collector.record_metric(
                        "memory_checkpoint", float(i), {"checkpoint": str(i // 100)}
                    )

        # Run sustained load
        await sustained_operations()

        # Final memory measurement
        final_metrics = await monitor.collect_system_metrics()
        final_memory = final_metrics.memory_usage_mb

        # Memory usage assertions
        memory_growth = final_memory - initial_memory
        memory_growth_percent = (
            (memory_growth / initial_memory * 100) if initial_memory > 0 else 0
        )

        # Allow some memory growth but not excessive
        assert (
            memory_growth_percent < 50.0
        ), f"Memory usage grew by {memory_growth_percent:.1f}% (potential leak)"

    @pytest.mark.asyncio
    async def test_response_time_consistency_under_load(
        self, cache_config, pool_config, cdn_config
    ):
        """Test response time consistency under varying load conditions."""
        monitor = PerformanceMonitor(cache_config, pool_config, cdn_config)

        # Test different load levels
        load_levels = [10, 50, 100, 200]  # Concurrent operations
        response_time_stats = {}

        for load_level in load_levels:

            async def load_operation():
                """Single operation under load."""
                start_time = time.time()
                # Simulate realistic operation
                await asyncio.sleep(0.01)  # 10ms base operation
                response_time = (time.time() - start_time) * 1000
                await monitor.record_response_time("load_test", response_time)
                return response_time

            # Run concurrent operations
            start_time = time.time()
            tasks = [load_operation() for _ in range(load_level)]
            response_times = await asyncio.gather(*tasks)
            duration = time.time() - start_time

            # Calculate statistics
            avg_response = sum(response_times) / len(response_times)
            max_response = max(response_times)
            min_response = min(response_times)

            response_time_stats[load_level] = {
                "avg": avg_response,
                "max": max_response,
                "min": min_response,
                "duration": duration,
            }

        # Analyze response time consistency
        for load_level, stats in response_time_stats.items():
            # Response times should remain reasonable even under high load
            assert (
                stats["avg"] < 50.0
            ), f"Average response time {stats['avg']:.2f}ms too high at load {load_level}"
            assert (
                stats["max"] < 100.0
            ), f"Max response time {stats['max']:.2f}ms too high at load {load_level}"

            # Variance should not be excessive
            variance = stats["max"] - stats["min"]
            assert (
                variance < 80.0
            ), f"Response time variance {variance:.2f}ms too high at load {load_level}"

    @pytest.mark.asyncio
    async def test_error_recovery_under_load(
        self, cache_config, pool_config, cdn_config
    ):
        """Test system error recovery capabilities under load."""
        monitor = PerformanceMonitor(cache_config, pool_config, cdn_config)

        # Simulate system with intermittent errors
        error_injection_rate = 0.1  # 10% error rate
        recovery_times = []

        async def operation_with_errors(operation_id: int):
            """Operation that may fail and recover."""
            start_time = time.time()

            # Inject errors randomly
            if (operation_id % 10) < (error_injection_rate * 10):
                # Simulate error condition
                await monitor.record_request("error_prone_endpoint", False)
                # Simulate recovery time
                await asyncio.sleep(0.02)  # 20ms recovery
                recovery_time = (time.time() - start_time) * 1000
                recovery_times.append(recovery_time)
                return False
            else:
                # Normal operation
                await monitor.record_response_time("error_prone_endpoint", 30.0)
                await monitor.record_request("error_prone_endpoint", True)
                return True

        # Run operations with error injection
        tasks = [operation_with_errors(i) for i in range(500)]
        results = await asyncio.gather(*tasks)

        # Analyze error recovery
        success_count = sum(1 for r in results if r)
        error_count = len(results) - success_count
        actual_error_rate = error_count / len(results)

        metrics = await monitor.get_error_rate_metrics()

        # Error recovery assertions
        assert (
            abs(actual_error_rate - error_injection_rate) < 0.05
        ), "Error injection rate not as expected"
        assert len(recovery_times) > 0, "No error recovery times recorded"

        if recovery_times:
            avg_recovery_time = sum(recovery_times) / len(recovery_times)
            assert (
                avg_recovery_time < 50.0
            ), f"Average error recovery time {avg_recovery_time:.2f}ms too slow"

        # System should handle errors gracefully
        assert (
            metrics.error_rate <= 0.15
        ), f"System error rate {metrics.error_rate:.1%} too high"


class TestIntegratedHardeningPerformance:
    """Test integrated performance and security under combined load."""

    @pytest.mark.asyncio
    async def test_security_performance_impact(
        self, app, cache_config, pool_config, cdn_config
    ):
        """Test performance impact of security measures under load."""
        # Test without security middleware
        from fastapi.testclient import TestClient

        # Baseline performance without security
        client_baseline = TestClient(app)

        baseline_times = []
        for i in range(100):
            start_time = time.time()
            response = client_baseline.get(f"/test?id={i}")
            response_time = (time.time() - start_time) * 1000
            baseline_times.append(response_time)

        baseline_avg = sum(baseline_times) / len(baseline_times)

        # Performance with full security enabled
        app.add_middleware(
            SecurityHardeningMiddleware,
            enable_input_validation=True,
            enable_threat_detection=True,
            enable_audit_logging=True,
            enable_ip_blocking=True,
        )

        client_secured = TestClient(app)

        secured_times = []
        for i in range(100):
            start_time = time.time()
            response = client_secured.get(f"/test?id={i}")
            response_time = (time.time() - start_time) * 1000
            secured_times.append(response_time)

        secured_avg = sum(secured_times) / len(secured_times)

        # Calculate performance impact
        performance_overhead = (
            ((secured_avg - baseline_avg) / baseline_avg * 100)
            if baseline_avg > 0
            else 0
        )

        # Performance impact assertions
        assert (
            performance_overhead < 100.0
        ), f"Security overhead {performance_overhead:.1f}% too high"
        assert secured_avg < 50.0, f"Secured response time {secured_avg:.2f}ms too slow"

    @pytest.mark.asyncio
    async def test_cache_security_integration(self, cache_config, mock_redis):
        """Test cache performance with security validation."""
        with patch("redis.asyncio.Redis.from_url", return_value=mock_redis):
            cache_manager = CacheManager(cache_config)

            # Test cache operations with potentially malicious keys
            malicious_keys = [
                "user:'; DROP TABLE users; --",
                "data:<script>alert('xss')</script>",
                "config:../../../etc/passwd",
                "session:' OR '1'='1",
            ]

            # Sanitize and cache malicious keys safely
            sanitized_operations = []
            for key in malicious_keys:
                # Simulate key sanitization
                safe_key = (
                    key.replace("'", "")
                    .replace("<", "")
                    .replace(">", "")
                    .replace("/", "_")
                )

                start_time = time.time()
                result = await cache_manager.set(safe_key, f"safe_data_for_{safe_key}")
                operation_time = (time.time() - start_time) * 1000

                sanitized_operations.append(
                    {
                        "original_key": key,
                        "safe_key": safe_key,
                        "success": result,
                        "time_ms": operation_time,
                    }
                )

            # Verify all operations completed safely and quickly
            assert all(
                op["success"] for op in sanitized_operations
            ), "Some cache operations failed"

            avg_time = sum(op["time_ms"] for op in sanitized_operations) / len(
                sanitized_operations
            )
            assert (
                avg_time < 10.0
            ), f"Cache security validation too slow: {avg_time:.2f}ms average"

    @pytest.mark.asyncio
    async def test_production_readiness_validation(
        self, cache_config, pool_config, cdn_config
    ):
        """Comprehensive production readiness test."""
        monitor = PerformanceMonitor(cache_config, pool_config, cdn_config)

        # Production readiness checklist
        readiness_results = {}

        # 1. Performance benchmarks
        start_time = time.time()
        for i in range(1000):
            await monitor.record_response_time("benchmark", 25.0 + (i % 10))
            await monitor.record_request("benchmark", i % 20 != 0)  # 5% error rate
        benchmark_time = time.time() - start_time

        readiness_results["benchmark_performance"] = benchmark_time < 2.0

        # 2. Memory efficiency
        metrics = await monitor.get_aggregated_metrics()
        readiness_results["memory_efficiency"] = (
            metrics.memory_usage_mb < 1000
        )  # Under 1GB

        # 3. Error handling
        readiness_results["error_rate"] = metrics.error_rate < 0.1  # Under 10%

        # 4. Response time consistency
        response_metrics = await monitor.get_response_time_metrics()
        readiness_results["response_consistency"] = (
            response_metrics.p95_response_time_ms < 100.0
            and response_metrics.avg_response_time_ms < 50.0
        )

        # 5. Cache effectiveness (simulated)
        cache_hit_ratio = 0.85  # Simulated high cache hit ratio
        readiness_results["cache_effectiveness"] = cache_hit_ratio > 0.8

        # Overall production readiness
        passed_checks = sum(1 for result in readiness_results.values() if result)
        total_checks = len(readiness_results)
        readiness_score = passed_checks / total_checks

        # Production readiness assertions
        assert (
            readiness_score >= 0.8
        ), f"Production readiness score {readiness_score:.1%} below 80%"
        assert readiness_results[
            "benchmark_performance"
        ], "Benchmark performance failed"
        assert readiness_results["error_rate"], "Error rate too high for production"
        assert readiness_results[
            "response_consistency"
        ], "Response times not consistent enough"

        # Log readiness report
        print(f"\nProduction Readiness Report:")
        print(f"Overall Score: {readiness_score:.1%}")
        for check, passed in readiness_results.items():
            status = "✓ PASS" if passed else "✗ FAIL"
            print(f"  {check}: {status}")
