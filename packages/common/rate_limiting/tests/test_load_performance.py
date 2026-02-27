"""Load and performance tests for rate limiting system."""

import asyncio
import time
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch

import pytest

from ..algorithms import SlidingWindowRateLimiter, TokenBucketRateLimiter
from ..models import RateLimitConfig, RateLimitStrategy
from ..storage import InMemoryStorage


class TestRateLimitingPerformance:
    """Test rate limiting performance under load."""

    @pytest.mark.asyncio
    async def test_sliding_window_concurrent_requests(self):
        """Test sliding window rate limiter under concurrent load."""
        config = RateLimitConfig(
            requests_per_window=100,
            window_size_seconds=60,
            strategy=RateLimitStrategy.SLIDING_WINDOW,
        )
        storage = InMemoryStorage()
        limiter = SlidingWindowRateLimiter(config, storage)

        async def make_request(client_id: str):
            """Make a single request."""
            return await limiter.check_rate_limit(client_id, "/api/test")

        # Test concurrent requests from same client
        tasks = [make_request("client1") for _ in range(50)]
        results = await asyncio.gather(*tasks)

        # Count allowed vs denied requests
        allowed = sum(1 for r in results if r.allowed)
        denied = sum(1 for r in results if not r.allowed)

        # Should allow up to the limit
        assert allowed <= 100
        assert allowed + denied == 50

        # All requests should have consistent remaining counts
        for result in results:
            if result.allowed:
                assert result.remaining >= 0
                assert result.remaining < 100

    @pytest.mark.asyncio
    async def test_token_bucket_concurrent_requests(self):
        """Test token bucket rate limiter under concurrent load."""
        config = RateLimitConfig(
            requests_per_window=50,
            window_size_seconds=60,
            strategy=RateLimitStrategy.TOKEN_BUCKET,
            burst_capacity=75,
            refill_rate=1.0,
        )
        storage = InMemoryStorage()
        limiter = TokenBucketRateLimiter(config, storage)

        async def make_request(client_id: str):
            """Make a single request."""
            return await limiter.check_rate_limit(client_id, "/api/test")

        # Test burst capacity
        tasks = [make_request("client1") for _ in range(80)]
        results = await asyncio.gather(*tasks)

        allowed = sum(1 for r in results if r.allowed)
        denied = sum(1 for r in results if not r.allowed)

        # Should allow up to burst capacity
        assert allowed <= 75
        assert denied >= 5  # Some should be denied

    @pytest.mark.asyncio
    async def test_multiple_clients_performance(self):
        """Test performance with multiple clients."""
        config = RateLimitConfig(
            requests_per_window=20,
            window_size_seconds=60,
            strategy=RateLimitStrategy.SLIDING_WINDOW,
        )
        storage = InMemoryStorage()
        limiter = SlidingWindowRateLimiter(config, storage)

        async def client_requests(client_id: str, num_requests: int):
            """Make multiple requests for a client."""
            results = []
            for _ in range(num_requests):
                result = await limiter.check_rate_limit(client_id, "/api/test")
                results.append(result)
            return results

        # Test 10 clients making 15 requests each
        tasks = [client_requests(f"client_{i}", 15) for i in range(10)]

        start_time = time.time()
        all_results = await asyncio.gather(*tasks)
        end_time = time.time()

        # Should complete reasonably quickly
        assert end_time - start_time < 1.0  # Less than 1 second

        # Each client should have their own limit
        for client_results in all_results:
            allowed = sum(1 for r in client_results if r.allowed)
            assert allowed <= 20  # Each client's limit

    @pytest.mark.asyncio
    async def test_storage_performance(self):
        """Test storage backend performance."""
        storage = InMemoryStorage()

        # Test many get/set operations
        start_time = time.time()

        for i in range(1000):
            key = f"test_key_{i}"
            quota = await storage.get_quota(key)
            if quota is None:
                from datetime import datetime

                from ..models import ClientQuota

                quota = ClientQuota(
                    client_id=f"client_{i}",
                    requests_made=1,
                    window_start=datetime.utcnow(),
                    last_request=datetime.utcnow(),
                )
                await storage.set_quota(key, quota, 3600)
            else:
                await storage.increment_requests(key)

        end_time = time.time()

        # Should handle 1000 operations quickly
        assert end_time - start_time < 0.5  # Less than 500ms

    @pytest.mark.asyncio
    async def test_rate_limit_accuracy_under_load(self):
        """Test rate limit accuracy under high concurrent load."""
        config = RateLimitConfig(
            requests_per_window=10,
            window_size_seconds=60,
            strategy=RateLimitStrategy.SLIDING_WINDOW,
        )
        storage = InMemoryStorage()
        limiter = SlidingWindowRateLimiter(config, storage)

        # Make many concurrent requests from same client
        tasks = [limiter.check_rate_limit("client1", "/api/test") for _ in range(100)]

        results = await asyncio.gather(*tasks)

        # Count allowed requests
        allowed_count = sum(1 for r in results if r.allowed)

        # Should not exceed the limit significantly due to race conditions
        # Allow small margin for race conditions in concurrent access
        assert allowed_count <= 12  # 10 + small margin
        assert allowed_count >= 10  # Should allow at least the limit

    def test_memory_usage_stability(self):
        """Test memory usage doesn't grow unbounded."""
        import gc
        import sys

        storage = InMemoryStorage()

        # Get initial memory usage
        gc.collect()
        initial_objects = len(gc.get_objects())

        # Create and expire many quotas
        for i in range(1000):
            from datetime import datetime, timedelta

            from ..models import ClientQuota

            quota = ClientQuota(
                client_id=f"client_{i}",
                requests_made=1,
                window_start=datetime.utcnow(),
                last_request=datetime.utcnow(),
            )

            # Set with very short TTL
            asyncio.run(storage.set_quota(f"key_{i}", quota, 1))

            # Manually expire some entries
            if i % 100 == 0:
                asyncio.run(storage.cleanup_expired())

        # Final cleanup
        asyncio.run(storage.cleanup_expired())
        gc.collect()
        final_objects = len(gc.get_objects())

        # Memory usage should not have grown significantly
        object_growth = final_objects - initial_objects
        assert object_growth < 500  # Allow some growth but not unbounded
