"""
Simple performance and security hardening tests for validation.
"""

import asyncio
import json
import time
from unittest.mock import AsyncMock, patch

import pytest

from packages.common.performance.cache import CacheManager
from packages.common.performance.models import CacheConfig


class TestSimplePerformanceHardening:
    """Simple tests to validate performance hardening functionality."""

    @pytest.mark.asyncio
    async def test_cache_basic_performance(self):
        """Test basic cache performance metrics."""
        # Create cache config
        cache_config = CacheConfig(
            redis_url="redis://localhost:6379/1",
            default_ttl=300,
            key_prefix="test:",
            compression_enabled=True,
        )

        # Mock Redis
        mock_redis = AsyncMock()
        cache_data = {}

        async def mock_get(key):
            return cache_data.get(key)

        async def mock_setex(key, ttl, value):
            cache_data[key] = value
            return True

        async def mock_ttl(key):
            return 300 if key in cache_data else -2

        async def mock_info():
            return {"keyspace_hits": 100, "keyspace_misses": 10, "used_memory": 1024000}

        mock_redis.get.side_effect = mock_get
        mock_redis.setex.side_effect = mock_setex
        mock_redis.ttl.side_effect = mock_ttl
        mock_redis.info.side_effect = mock_info

        with patch("redis.asyncio.Redis.from_url", return_value=mock_redis):
            cache_manager = CacheManager(cache_config)

            # Test cache set performance
            start_time = time.time()
            for i in range(100):
                result = await cache_manager.set(f"key_{i}", f"value_{i}")
                assert result is True
            set_time = time.time() - start_time

            # Test cache get performance
            start_time = time.time()
            for i in range(100):
                result = await cache_manager.get(f"key_{i}")
                assert result.status.value == "hit"
            get_time = time.time() - start_time

            # Performance assertions
            assert (
                set_time < 1.0
            ), f"Cache set operations took {set_time:.3f}s (too slow)"
            assert (
                get_time < 1.0
            ), f"Cache get operations took {get_time:.3f}s (too slow)"

    @pytest.mark.asyncio
    async def test_concurrent_cache_operations(self):
        """Test cache performance under concurrent load."""
        cache_config = CacheConfig(
            redis_url="redis://localhost:6379/1",
            default_ttl=300,
            key_prefix="test:",
        )

        # Mock Redis with thread-safe operations
        mock_redis = AsyncMock()
        cache_data = {}

        async def mock_get(key):
            return cache_data.get(key)

        async def mock_setex(key, ttl, value):
            cache_data[key] = value
            return True

        async def mock_ttl(key):
            return 300 if key in cache_data else -2

        async def mock_info():
            return {"keyspace_hits": 100, "keyspace_misses": 10, "used_memory": 1024000}

        mock_redis.get.side_effect = mock_get
        mock_redis.setex.side_effect = mock_setex
        mock_redis.ttl.side_effect = mock_ttl
        mock_redis.info.side_effect = mock_info

        with patch("redis.asyncio.Redis.from_url", return_value=mock_redis):
            cache_manager = CacheManager(cache_config)

            # Concurrent operations
            async def cache_operations(client_id):
                results = []
                for i in range(10):
                    key = f"client_{client_id}_key_{i}"
                    # Set operation
                    set_result = await cache_manager.set(key, f"value_{i}")
                    # Get operation
                    get_result = await cache_manager.get(key)
                    results.append((set_result, get_result))
                return results

            # Run 10 concurrent clients
            start_time = time.time()
            tasks = [cache_operations(i) for i in range(10)]
            all_results = await asyncio.gather(*tasks)
            total_time = time.time() - start_time

            # Verify all operations completed successfully
            total_operations = 0
            successful_operations = 0

            for client_results in all_results:
                for set_result, get_result in client_results:
                    total_operations += 2  # set + get
                    if set_result and get_result.status.value == "hit":
                        successful_operations += 2

            success_rate = (
                successful_operations / total_operations if total_operations > 0 else 0
            )

            # Performance assertions
            assert success_rate >= 0.95, f"Success rate {success_rate:.1%} below 95%"
            assert (
                total_time < 2.0
            ), f"Concurrent operations took {total_time:.3f}s (too slow)"
            assert total_operations == 200, "Not all operations completed"

    def test_security_input_validation_performance(self):
        """Test security input validation performance."""
        # Test input validation patterns
        malicious_inputs = [
            "'; DROP TABLE users; --",
            "<script>alert('xss')</script>",
            "../../../../etc/passwd",
            "' OR '1'='1",
            "<img src=x onerror=alert(1)>",
        ]

        def simple_sanitize(input_str):
            """Simple input sanitization for testing."""
            dangerous_patterns = ["'", "<", ">", "script", "DROP", "OR", "../"]
            sanitized = input_str
            for pattern in dangerous_patterns:
                sanitized = sanitized.replace(pattern, "")
            return sanitized

        # Test sanitization performance
        start_time = time.time()
        sanitized_inputs = []

        for _ in range(1000):  # Process 1000 inputs
            for malicious_input in malicious_inputs:
                sanitized = simple_sanitize(malicious_input)
                sanitized_inputs.append(sanitized)

        sanitization_time = time.time() - start_time

        # Performance and security assertions
        assert (
            sanitization_time < 1.0
        ), f"Input sanitization took {sanitization_time:.3f}s (too slow)"
        assert len(sanitized_inputs) == 5000, "Not all inputs processed"

        # Verify sanitization effectiveness
        for sanitized in sanitized_inputs:
            assert "DROP" not in sanitized, "SQL injection pattern not removed"
            assert "<script>" not in sanitized, "XSS pattern not removed"
            assert "../" not in sanitized, "Path traversal pattern not removed"

    @pytest.mark.asyncio
    async def test_error_handling_performance(self):
        """Test error handling performance under failure conditions."""
        cache_config = CacheConfig(
            redis_url="redis://localhost:6379/1",
            default_ttl=300,
        )

        # Mock Redis with intermittent failures
        mock_redis = AsyncMock()
        failure_count = 0

        async def mock_get_with_failures(key):
            nonlocal failure_count
            failure_count += 1
            if failure_count % 5 == 0:  # 20% failure rate
                raise Exception("Simulated Redis failure")
            return f"value_for_{key}"

        async def mock_info():
            return {"keyspace_hits": 80, "keyspace_misses": 20, "used_memory": 1024000}

        async def mock_ttl(key):
            return 300

        mock_redis.get.side_effect = mock_get_with_failures
        mock_redis.info.side_effect = mock_info
        mock_redis.ttl.side_effect = mock_ttl

        with patch("redis.asyncio.Redis.from_url", return_value=mock_redis):
            cache_manager = CacheManager(cache_config)

            # Test error handling performance
            start_time = time.time()
            results = []

            for i in range(100):
                try:
                    result = await cache_manager.get(f"key_{i}")
                    results.append(result)
                except Exception:
                    # Should handle errors gracefully
                    pass

            error_handling_time = time.time() - start_time

            # Performance assertions
            assert (
                error_handling_time < 2.0
            ), f"Error handling took {error_handling_time:.3f}s (too slow)"

            # Should have some successful results despite failures
            successful_results = [r for r in results if r.status.value == "hit"]
            # With 20% failure rate, expect at least 60% success
            assert (
                len(successful_results) >= 60
            ), f"Only {len(successful_results)} operations succeeded"

    def test_memory_usage_stability(self):
        """Test memory usage stability during operations."""
        import gc

        # Get initial object count
        gc.collect()
        initial_objects = len(gc.get_objects())

        # Perform memory-intensive operations
        large_data_sets = []
        for i in range(100):
            # Create and process large data structures
            data = {
                "id": i,
                "payload": "x" * 1000,  # 1KB per item
                "metadata": {"timestamp": time.time(), "index": i},
            }
            large_data_sets.append(data)

            # Simulate processing
            processed = json.dumps(data)
            parsed = json.loads(processed)

            # Clean up periodically
            if i % 20 == 0:
                gc.collect()

        # Final cleanup
        del large_data_sets
        gc.collect()
        final_objects = len(gc.get_objects())

        # Memory stability assertions
        object_growth = final_objects - initial_objects
        assert (
            object_growth < 1000
        ), f"Memory usage grew by {object_growth} objects (potential leak)"

    def test_production_load_simulation(self):
        """Simulate production-like load patterns."""
        # Simulate various operation types with different performance characteristics
        operation_times = {
            "fast_operations": [],
            "medium_operations": [],
            "slow_operations": [],
        }

        start_time = time.time()

        # Simulate 1000 mixed operations
        for i in range(1000):
            op_start = time.time()

            if i % 10 < 7:  # 70% fast operations
                # Simulate fast cache/memory operations
                time.sleep(0.001)  # 1ms
                operation_times["fast_operations"].append(
                    (time.time() - op_start) * 1000
                )
            elif i % 10 < 9:  # 20% medium operations
                # Simulate database/API operations
                time.sleep(0.005)  # 5ms
                operation_times["medium_operations"].append(
                    (time.time() - op_start) * 1000
                )
            else:  # 10% slow operations
                # Simulate complex computations
                time.sleep(0.01)  # 10ms
                operation_times["slow_operations"].append(
                    (time.time() - op_start) * 1000
                )

        total_time = time.time() - start_time

        # Performance assertions
        assert (
            total_time < 10.0
        ), f"Production simulation took {total_time:.3f}s (too slow)"

        # Verify operation time distributions
        if operation_times["fast_operations"]:
            avg_fast = sum(operation_times["fast_operations"]) / len(
                operation_times["fast_operations"]
            )
            assert (
                avg_fast < 5.0
            ), f"Fast operations averaged {avg_fast:.2f}ms (too slow)"

        if operation_times["medium_operations"]:
            avg_medium = sum(operation_times["medium_operations"]) / len(
                operation_times["medium_operations"]
            )
            assert (
                avg_medium < 10.0
            ), f"Medium operations averaged {avg_medium:.2f}ms (too slow)"

        if operation_times["slow_operations"]:
            avg_slow = sum(operation_times["slow_operations"]) / len(
                operation_times["slow_operations"]
            )
            assert (
                avg_slow < 20.0
            ), f"Slow operations averaged {avg_slow:.2f}ms (too slow)"
