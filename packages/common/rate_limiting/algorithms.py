"""Rate limiting algorithms implementation."""

import logging
import math
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import Optional

from .models import ClientQuota, RateLimitConfig, RateLimitResult
from .storage import RateLimitStorage

logger = logging.getLogger(__name__)


class RateLimiter(ABC):
    """Abstract base class for rate limiting algorithms."""

    def __init__(self, config: RateLimitConfig, storage: RateLimitStorage):
        self.config = config
        self.storage = storage

    @abstractmethod
    async def check_rate_limit(self, client_id: str, endpoint: str) -> RateLimitResult:
        """Check if request is allowed under rate limit."""
        pass

    def _make_key(self, client_id: str, endpoint: str) -> str:
        """Create storage key for client and endpoint."""
        return f"{client_id}:{endpoint}"


class SlidingWindowRateLimiter(RateLimiter):
    """Sliding window rate limiter implementation."""

    async def check_rate_limit(self, client_id: str, endpoint: str) -> RateLimitResult:
        """Check rate limit using sliding window algorithm."""
        key = self._make_key(client_id, endpoint)
        now = datetime.utcnow()
        window_start = now - timedelta(seconds=self.config.window_size_seconds)

        # Get current quota
        quota = await self.storage.get_quota(key)

        if not quota:
            # First request - create new quota
            quota = ClientQuota(
                client_id=client_id, requests_made=1, window_start=now, last_request=now
            )
            await self.storage.set_quota(
                key, quota, self.config.window_size_seconds * 2
            )

            return RateLimitResult(
                allowed=True,
                remaining=self.config.requests_per_window - 1,
                reset_time=now + timedelta(seconds=self.config.window_size_seconds),
            )

        # Check if we need to slide the window
        if quota.window_start < window_start:
            # Calculate how much of the window has passed
            time_passed = (now - quota.window_start).total_seconds()
            window_ratio = min(1.0, time_passed / self.config.window_size_seconds)

            # Reduce request count proportionally
            requests_to_subtract = int(quota.requests_made * window_ratio)
            quota.requests_made = max(0, quota.requests_made - requests_to_subtract)
            quota.window_start = window_start

        # Check if request is allowed
        if quota.requests_made >= self.config.requests_per_window:
            # Rate limit exceeded
            reset_time = quota.window_start + timedelta(
                seconds=self.config.window_size_seconds
            )
            retry_after = int((reset_time - now).total_seconds())

            return RateLimitResult(
                allowed=False,
                remaining=0,
                reset_time=reset_time,
                retry_after=max(1, retry_after),
            )

        # Allow request and increment counter
        quota.requests_made += 1
        quota.last_request = now
        await self.storage.set_quota(key, quota, self.config.window_size_seconds * 2)

        remaining = self.config.requests_per_window - quota.requests_made
        reset_time = quota.window_start + timedelta(
            seconds=self.config.window_size_seconds
        )

        return RateLimitResult(allowed=True, remaining=remaining, reset_time=reset_time)


class TokenBucketRateLimiter(RateLimiter):
    """Token bucket rate limiter implementation."""

    def __init__(self, config: RateLimitConfig, storage: RateLimitStorage):
        super().__init__(config, storage)

        # Token bucket specific configuration
        if config.burst_capacity is None:
            self.burst_capacity = config.requests_per_window
        else:
            self.burst_capacity = config.burst_capacity

        if config.refill_rate is None:
            # Default: refill at rate to allow requests_per_window over window_size_seconds
            self.refill_rate = config.requests_per_window / config.window_size_seconds
        else:
            self.refill_rate = config.refill_rate

    async def check_rate_limit(self, client_id: str, endpoint: str) -> RateLimitResult:
        """Check rate limit using token bucket algorithm."""
        key = self._make_key(client_id, endpoint)
        now = datetime.utcnow()

        # Get current quota
        quota = await self.storage.get_quota(key)

        if not quota:
            # First request - create new bucket with full capacity minus one token
            quota = ClientQuota(
                client_id=client_id,
                requests_made=1,
                window_start=now,
                last_request=now,
                tokens=float(self.burst_capacity - 1),
                last_refill=now,
            )
            await self.storage.set_quota(
                key, quota, self.config.window_size_seconds * 4
            )

            return RateLimitResult(
                allowed=True,
                remaining=int(quota.tokens),
                reset_time=self._calculate_reset_time(quota.tokens),
            )

        # Refill tokens based on time passed
        time_passed = (now - (quota.last_refill or quota.last_request)).total_seconds()
        tokens_to_add = time_passed * self.refill_rate
        quota.tokens = min(self.burst_capacity, quota.tokens + tokens_to_add)
        quota.last_refill = now

        # Check if we have tokens available
        if quota.tokens < 1.0:
            # No tokens available
            time_for_next_token = (1.0 - quota.tokens) / self.refill_rate
            retry_after = max(1, int(math.ceil(time_for_next_token)))

            return RateLimitResult(
                allowed=False,
                remaining=0,
                reset_time=now + timedelta(seconds=time_for_next_token),
                retry_after=retry_after,
            )

        # Consume one token
        quota.tokens -= 1.0
        quota.requests_made += 1
        quota.last_request = now
        await self.storage.set_quota(key, quota, self.config.window_size_seconds * 4)

        return RateLimitResult(
            allowed=True,
            remaining=int(quota.tokens),
            reset_time=self._calculate_reset_time(quota.tokens),
        )

    def _calculate_reset_time(self, current_tokens: float) -> datetime:
        """Calculate when the bucket will be full again."""
        if current_tokens >= self.burst_capacity:
            return datetime.utcnow()

        tokens_needed = self.burst_capacity - current_tokens
        seconds_to_full = tokens_needed / self.refill_rate
        return datetime.utcnow() + timedelta(seconds=seconds_to_full)
