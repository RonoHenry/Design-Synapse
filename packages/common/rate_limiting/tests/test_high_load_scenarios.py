"""High load scenario tests for rate limiting system."""

import asyncio
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

import pytest

from ..algorithms import SlidingWindowRateLimiter, TokenBucketRateLimiter
from ..models import RateLimitConfig, RateLimitStrategy
from ..storage import InMemoryStorage


class TestHighLoadScenarios:
    """Test rate limiting under extreme load conditions."""

    @pytest.mark.asyncio
    async def test_burst_traffic_handling(self):
        """Test handling of sudden burst traffic."""
        config = RateLimitConfig(
            requests_per_window=50,
            window_size_seconds=60,
            strategy=RateLimitStrategy.SLIDING_WINDOW,
        )
        storage = InMemoryStorage()
        limiter = SlidingWindowRateLimiter(config, storage)

        # Simulate burst of 200 requests in quick succession
        async def burst_request(client_id: str, request_num: int):
            return await limiter.check_rate_limit(
                f"{client_id}_{request_num % 5}", "/api/burst"
            )

        tasks = [burst_request("burst_client", i) for i in range(200)]
        start_time = time.time()
        results = await asyncio.gather(*tasks)
        end_time = time.time()

        # Should handle burst quickly
        assert end_time - start_time < 2.0

        # Count results by client
        client_results = {}
        for i, result in enumerate(results):
            client_id = f"burst_client_{i % 5}"
            if client_id not in client_results:
                client_results[client_id] = []
            client_results[client_id].append(result)

        # Each client should have proper rate limiting
        for client_id, client_results_list in client_results.items():
            allowed = sum(1 for r in client_results_list if r.allowed)
            assert allowed <= 50  # Respect per-client limit

    @pytest.mark.asyncio
    async def test_sustained_high_load(self):
        """Test sustained high load over time."""
        config = RateLimitConfig(
            requests_per_window=100,
            window_size_seconds=10,  # Shorter window for faster test
            strategy=RateLimitStrategy.TOKEN_BUCKET,
            burst_capacity=150,
            refill_rate=10.0,  # 10 tokens per second
        )
        storage = InMemoryStorage()
        limiter = TokenBucketRateLimiter(config, storage)

        # Simulate sustained load over multiple windows
        async def sustained_requests(client_id: str, duration_seconds: int):
            results = []
            start_time = time.time()
            request_count = 0

            while time.time() - start_time < duration_seconds:
                result = await limiter.check_rate_limit(client_id, "/api/sustained")
                results.append(result)
                request_count += 1

                # Small delay to simulate realistic request rate
                await asyncio.sleep(0.05)  # 20 requests per second

            return results, request_count

        # Run sustained load for 3 seconds
        results, total_requests = await sustained_requests("sustained_client", 3)

        allowed_count = sum(1 for r in results if r.allowed)
        denied_count = sum(1 for r in results if not r.allowed)

        # Should allow reasonable number based on refill rate
        # 3 seconds * 10 tokens/sec + initial burst = ~180 tokens max
        assert allowed_count <= 180
        assert allowed_count >= 30  # Should allow at least initial burst
        assert denied_count > 0  # Should deny some requests under sustained load

    @pytest.mark.asyncio
    async def test_concurrent_clients_fairness(self):
        """Test fairness under concurrent load from multiple clients."""
        config = RateLimitConfig(
            requests_per_window=20,
            window_size_seconds=60,
            strategy=RateLimitStrategy.SLIDING_WINDOW,
        )
        storage = InMemoryStorage()
        limiter = SlidingWindowRateLimiter(config, storage)

        async def client_load(client_id: str, num_requests: int):
            results = []
            for i in range(num_requests):
                result = await limiter.check_rate_limit(client_id, "/api/fair")
                results.append(result)
                # Small delay to interleave requests
                if i % 5 == 0:
                    await asyncio.sleep(0.01)
            return results

        # 20 clients making 25 requests each
        tasks = [client_load(f"client_{i}", 25) for i in range(20)]
        all_results = await asyncio.gather(*tasks)

        # Check fairness - each client should get roughly equal treatment
        allowed_counts = []
        for client_results in all_results:
            allowed = sum(1 for r in client_results if r.allowed)
            allowed_counts.append(allowed)

        # All clients should get their fair share (up to limit)
        for allowed in allowed_counts:
            assert allowed <= 20  # Respect individual limit
            assert allowed >= 15  # Should get most of their allocation

        # Variance should be reasonable (no client gets significantly more/less)
        avg_allowed = sum(allowed_counts) / len(allowed_counts)
        for allowed in allowed_counts:
            assert abs(allowed - avg_allowed) <= 5  # Within 5 requests of average

    @pytest.mark.asyncio
    async def test_storage_contention_handling(self):
        """Test handling of storage contention under load."""
        storage = InMemoryStorage()

        # Mock storage to simulate contention
        original_get = storage.get_quota
        original_set = storage.set_quota

        call_count = 0

        async def slow_get_quota(key: str):
            nonlocal call_count
            call_count += 1
            # Simulate occasional slow storage operations
            if call_count % 10 == 0:
                await asyncio.sleep(0.1)
            return await original_get(key)

        async def slow_set_quota(key: str, quota, ttl: int):
            # Simulate occasional storage delays
            if call_count % 15 == 0:
                await asyncio.sleep(0.05)
            return await original_set(key, quota, ttl)

        storage.get_quota = slow_get_quota
        storage.set_quota = slow_set_quota

        config = RateLimitConfig(
            requests_per_window=30,
            window_size_seconds=60,
            strategy=RateLimitStrategy.SLIDING_WINDOW,
        )
        limiter = SlidingWindowRateLimiter(config, storage)

        # Make concurrent requests with storage contention
        tasks = [
            limiter.check_rate_limit(f"client_{i % 5}", "/api/contention")
            for i in range(100)
        ]

        start_time = time.time()
        results = await asyncio.gather(*tasks)
        end_time = time.time()

        # Should still complete in reasonable time despite contention
        assert end_time - start_time < 5.0

        # Should still enforce rate limits correctly
        client_results = {}
        for i, result in enumerate(results):
            client_id = f"client_{i % 5}"
            if client_id not in client_results:
                client_results[client_id] = []
            client_results[client_id].append(result)

        for client_results_list in client_results.values():
            allowed = sum(1 for r in client_results_list if r.allowed)
            assert allowed <= 30

    @pytest.mark.asyncio
    async def test_memory_pressure_handling(self):
        """Test rate limiter behavior under memory pressure."""
        config = RateLimitConfig(
            requests_per_window=10,
            window_size_seconds=60,
            strategy=RateLimitStrategy.SLIDING_WINDOW,
        )
        storage = InMemoryStorage()
        limiter = SlidingWindowRateLimiter(config, storage)

        # Create many unique clients to pressure memory
        async def create_client_quota(client_num: int):
            client_id = f"memory_client_{client_num}"
            result = await limiter.check_rate_limit(client_id, "/api/memory")
            return result.allowed

        # Create 1000 unique client quotas
        tasks = [create_client_quota(i) for i in range(1000)]
        results = await asyncio.gather(*tasks)

        # All first requests should be allowed
        assert all(results)

        # Storage should handle cleanup properly
        await storage.cleanup_expired()

        # Should still work after cleanup
        result = await limiter.check_rate_limit("test_client", "/api/memory")
        assert result.allowed

    @pytest.mark.asyncio
    async def test_algorithm_accuracy_under_load(self):
        """Test rate limiting algorithm accuracy under concurrent load."""
        config = RateLimitConfig(
            requests_per_window=5,
            window_size_seconds=60,
            strategy=RateLimitStrategy.SLIDING_WINDOW,
        )
        storage = InMemoryStorage()
        limiter = SlidingWindowRateLimiter(config, storage)

        # Make exactly 100 concurrent requests from same client
        tasks = [
            limiter.check_rate_limit("accuracy_client", "/api/accuracy")
            for _ in range(100)
        ]

        results = await asyncio.gather(*tasks)

        allowed_count = sum(1 for r in results if r.allowed)
        denied_count = sum(1 for r in results if not r.allowed)

        # Should allow exactly the limit (with small margin for race conditions)
        assert allowed_count <= 7  # 5 + small margin for race conditions
        assert allowed_count >= 5  # Should allow at least the configured limit
        assert denied_count >= 93  # Most should be denied

        # All denied requests should have consistent retry_after
        denied_results = [r for r in results if not r.allowed]
        if denied_results:
            retry_afters = [r.retry_after for r in denied_results if r.retry_after]
            if retry_afters:
                # All retry_after values should be similar (within window)
                assert max(retry_afters) - min(retry_afters) <= 5

    @pytest.mark.asyncio
    async def test_error_recovery_under_load(self):
        """Test error recovery behavior under load."""
        storage = InMemoryStorage()

        # Mock storage to fail occasionally
        original_get = storage.get_quota
        call_count = 0

        async def failing_get_quota(key: str):
            nonlocal call_count
            call_count += 1
            # Fail every 20th call
            if call_count % 20 == 0:
                raise Exception("Storage temporarily unavailable")
            return await original_get(key)

        storage.get_quota = failing_get_quota

        config = RateLimitConfig(
            requests_per_window=10,
            window_size_seconds=60,
            strategy=RateLimitStrategy.SLIDING_WINDOW,
        )
        limiter = SlidingWindowRateLimiter(config, storage)

        # Make requests that will encounter storage errors
        results = []
        errors = []

        for i in range(50):
            try:
                result = await limiter.check_rate_limit(
                    "recovery_client", "/api/recovery"
                )
                results.append(result)
            except Exception as e:
                errors.append(e)

        # Should have some successful results despite errors
        assert len(results) > 30  # Most should succeed
        assert len(errors) > 0  # Some should fail

        # Successful results should still respect rate limits
        allowed = sum(1 for r in results if r.allowed)
        assert allowed <= 10
