"""Tests for rate limiting algorithms."""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest

from ..algorithms import SlidingWindowRateLimiter, TokenBucketRateLimiter
from ..models import ClientQuota


class TestSlidingWindowRateLimiter:
    """Test sliding window rate limiter."""

    @pytest.mark.asyncio
    async def test_first_request_allowed(self, sliding_window_config, memory_storage):
        """Test first request is always allowed."""
        limiter = SlidingWindowRateLimiter(sliding_window_config, memory_storage)

        result = await limiter.check_rate_limit("client1", "/api/test")

        assert result.allowed is True
        assert result.remaining == 9  # 10 - 1
        assert result.retry_after is None

    @pytest.mark.asyncio
    async def test_requests_within_limit(self, sliding_window_config, memory_storage):
        """Test requests within limit are allowed."""
        limiter = SlidingWindowRateLimiter(sliding_window_config, memory_storage)

        # Make several requests
        for i in range(5):
            result = await limiter.check_rate_limit("client1", "/api/test")
            assert result.allowed is True
            assert result.remaining == 10 - (i + 1)

    @pytest.mark.asyncio
    async def test_rate_limit_exceeded(self, sliding_window_config, memory_storage):
        """Test rate limit exceeded scenario."""
        limiter = SlidingWindowRateLimiter(sliding_window_config, memory_storage)

        # Make requests up to limit
        for _ in range(10):
            result = await limiter.check_rate_limit("client1", "/api/test")
            assert result.allowed is True

        # Next request should be denied
        result = await limiter.check_rate_limit("client1", "/api/test")
        assert result.allowed is False
        assert result.remaining == 0
        assert result.retry_after is not None
        assert result.retry_after > 0

    @pytest.mark.asyncio
    async def test_window_sliding(self, sliding_window_config, memory_storage):
        """Test sliding window behavior."""
        limiter = SlidingWindowRateLimiter(sliding_window_config, memory_storage)

        # Create quota that's partially outside the window
        now = datetime.utcnow()
        old_quota = ClientQuota(
            client_id="client1",
            requests_made=8,
            window_start=now - timedelta(seconds=90),  # 90 seconds ago
            last_request=now - timedelta(seconds=30),
        )

        await memory_storage.set_quota("client1:/api/test", old_quota, 3600)

        # Request should be allowed as window has slid
        result = await limiter.check_rate_limit("client1", "/api/test")
        assert result.allowed is True
        # Some requests should have been subtracted due to sliding
        assert result.remaining < 10

    @pytest.mark.asyncio
    async def test_different_clients_separate_limits(
        self, sliding_window_config, memory_storage
    ):
        """Test different clients have separate rate limits."""
        limiter = SlidingWindowRateLimiter(sliding_window_config, memory_storage)

        # Client 1 uses up their limit
        for _ in range(10):
            result = await limiter.check_rate_limit("client1", "/api/test")
            assert result.allowed is True

        # Client 1 should be rate limited
        result = await limiter.check_rate_limit("client1", "/api/test")
        assert result.allowed is False

        # Client 2 should still be allowed
        result = await limiter.check_rate_limit("client2", "/api/test")
        assert result.allowed is True


class TestTokenBucketRateLimiter:
    """Test token bucket rate limiter."""

    @pytest.mark.asyncio
    async def test_first_request_allowed(self, token_bucket_config, memory_storage):
        """Test first request is allowed with full bucket."""
        limiter = TokenBucketRateLimiter(token_bucket_config, memory_storage)

        result = await limiter.check_rate_limit("client1", "/api/test")

        assert result.allowed is True
        assert result.remaining == 14  # 15 - 1 (burst_capacity - 1)
        assert result.retry_after is None

    @pytest.mark.asyncio
    async def test_burst_capacity(self, token_bucket_config, memory_storage):
        """Test burst capacity allows more than steady rate."""
        limiter = TokenBucketRateLimiter(token_bucket_config, memory_storage)

        # Should be able to make burst_capacity requests immediately
        for i in range(15):
            result = await limiter.check_rate_limit("client1", "/api/test")
            assert result.allowed is True
            assert result.remaining == 15 - (i + 1)

        # Next request should be denied (no tokens left)
        result = await limiter.check_rate_limit("client1", "/api/test")
        assert result.allowed is False
        assert result.remaining == 0
        assert result.retry_after is not None

    @pytest.mark.asyncio
    async def test_token_refill(self, token_bucket_config, memory_storage):
        """Test token refill over time."""
        limiter = TokenBucketRateLimiter(token_bucket_config, memory_storage)

        # Create quota with some tokens used and time passed
        now = datetime.utcnow()
        quota = ClientQuota(
            client_id="client1",
            requests_made=5,
            window_start=now - timedelta(seconds=30),
            last_request=now - timedelta(seconds=10),
            tokens=5.0,  # 5 tokens remaining
            last_refill=now - timedelta(seconds=10),  # 10 seconds ago
        )

        await memory_storage.set_quota("client1:/api/test", quota, 3600)

        # Request should be allowed and tokens should be refilled
        # 10 seconds * 0.2 tokens/second = 2 tokens refilled
        result = await limiter.check_rate_limit("client1", "/api/test")
        assert result.allowed is True
        # Should have ~6 tokens (5 + 2 - 1 for request)
        assert result.remaining >= 6

    @pytest.mark.asyncio
    async def test_token_refill_capped_at_capacity(
        self, token_bucket_config, memory_storage
    ):
        """Test token refill is capped at burst capacity."""
        limiter = TokenBucketRateLimiter(token_bucket_config, memory_storage)

        # Create quota with long time passed (should refill to capacity)
        now = datetime.utcnow()
        quota = ClientQuota(
            client_id="client1",
            requests_made=1,
            window_start=now - timedelta(seconds=300),  # 5 minutes ago
            last_request=now - timedelta(seconds=300),
            tokens=1.0,
            last_refill=now - timedelta(seconds=300),
        )

        await memory_storage.set_quota("client1:/api/test", quota, 3600)

        result = await limiter.check_rate_limit("client1", "/api/test")
        assert result.allowed is True
        # Should be capped at burst_capacity - 1
        assert result.remaining == 14

    @pytest.mark.asyncio
    async def test_no_tokens_available(self, token_bucket_config, memory_storage):
        """Test behavior when no tokens are available."""
        limiter = TokenBucketRateLimiter(token_bucket_config, memory_storage)

        # Create quota with no tokens
        now = datetime.utcnow()
        quota = ClientQuota(
            client_id="client1",
            requests_made=15,
            window_start=now,
            last_request=now,
            tokens=0.5,  # Less than 1 token
            last_refill=now,
        )

        await memory_storage.set_quota("client1:/api/test", quota, 3600)

        result = await limiter.check_rate_limit("client1", "/api/test")
        assert result.allowed is False
        assert result.remaining == 0
        assert result.retry_after is not None
        assert result.retry_after > 0
