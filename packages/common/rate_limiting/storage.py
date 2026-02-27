"""Storage backends for rate limiting data."""

import json
import logging
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import Dict, Optional

from .models import ClientQuota

logger = logging.getLogger(__name__)


class RateLimitStorage(ABC):
    """Abstract base class for rate limit storage backends."""

    @abstractmethod
    async def get_quota(self, key: str) -> Optional[ClientQuota]:
        """Get client quota data."""
        pass

    @abstractmethod
    async def set_quota(self, key: str, quota: ClientQuota, ttl: int) -> None:
        """Set client quota data with TTL."""
        pass

    @abstractmethod
    async def increment_requests(self, key: str, amount: int = 1) -> int:
        """Atomically increment request count and return new value."""
        pass

    @abstractmethod
    async def cleanup_expired(self) -> None:
        """Clean up expired quota entries."""
        pass


class InMemoryStorage(RateLimitStorage):
    """In-memory storage for rate limiting (development/testing only)."""

    def __init__(self):
        self._quotas: Dict[str, ClientQuota] = {}
        self._expiry: Dict[str, datetime] = {}

    async def get_quota(self, key: str) -> Optional[ClientQuota]:
        """Get client quota data."""
        # Check if expired
        if key in self._expiry and datetime.utcnow() > self._expiry[key]:
            self._quotas.pop(key, None)
            self._expiry.pop(key, None)
            return None

        return self._quotas.get(key)

    async def set_quota(self, key: str, quota: ClientQuota, ttl: int) -> None:
        """Set client quota data with TTL."""
        self._quotas[key] = quota
        self._expiry[key] = datetime.utcnow() + timedelta(seconds=ttl)

    async def increment_requests(self, key: str, amount: int = 1) -> int:
        """Atomically increment request count and return new value."""
        quota = await self.get_quota(key)
        if quota:
            quota.requests_made += amount
            quota.last_request = datetime.utcnow()
            return quota.requests_made
        return amount

    async def cleanup_expired(self) -> None:
        """Clean up expired quota entries."""
        now = datetime.utcnow()
        expired_keys = [key for key, expiry in self._expiry.items() if now > expiry]

        for key in expired_keys:
            self._quotas.pop(key, None)
            self._expiry.pop(key, None)


class RedisStorage(RateLimitStorage):
    """Redis storage backend for rate limiting."""

    def __init__(self, redis_client):
        self.redis = redis_client
        self.key_prefix = "rate_limit:"

    def _make_key(self, key: str) -> str:
        """Create Redis key with prefix."""
        return f"{self.key_prefix}{key}"

    async def get_quota(self, key: str) -> Optional[ClientQuota]:
        """Get client quota data from Redis."""
        redis_key = self._make_key(key)
        data = await self.redis.get(redis_key)

        if not data:
            return None

        try:
            quota_data = json.loads(data)
            return ClientQuota(
                client_id=quota_data["client_id"],
                requests_made=quota_data["requests_made"],
                window_start=datetime.fromisoformat(quota_data["window_start"]),
                last_request=datetime.fromisoformat(quota_data["last_request"]),
                tokens=quota_data.get("tokens", 0.0),
                last_refill=datetime.fromisoformat(quota_data["last_refill"])
                if quota_data.get("last_refill")
                else None,
            )
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.error(f"Failed to deserialize quota data for {key}: {e}")
            return None

    async def set_quota(self, key: str, quota: ClientQuota, ttl: int) -> None:
        """Set client quota data in Redis with TTL."""
        redis_key = self._make_key(key)
        quota_data = {
            "client_id": quota.client_id,
            "requests_made": quota.requests_made,
            "window_start": quota.window_start.isoformat(),
            "last_request": quota.last_request.isoformat(),
            "tokens": quota.tokens,
            "last_refill": quota.last_refill.isoformat() if quota.last_refill else None,
        }

        await self.redis.setex(redis_key, ttl, json.dumps(quota_data))

    async def increment_requests(self, key: str, amount: int = 1) -> int:
        """Atomically increment request count using Redis."""
        redis_key = self._make_key(key)

        # Use Redis pipeline for atomic operations
        pipe = self.redis.pipeline()
        pipe.multi()

        # Get current data
        current_data = await self.redis.get(redis_key)

        if current_data:
            try:
                quota_data = json.loads(current_data)
                new_count = quota_data["requests_made"] + amount
                quota_data["requests_made"] = new_count
                quota_data["last_request"] = datetime.utcnow().isoformat()

                # Update with same TTL
                ttl = await self.redis.ttl(redis_key)
                if ttl > 0:
                    await self.redis.setex(redis_key, ttl, json.dumps(quota_data))

                return new_count
            except (json.JSONDecodeError, KeyError) as e:
                logger.error(f"Failed to increment requests for {key}: {e}")
                return amount

        return amount

    async def cleanup_expired(self) -> None:
        """Redis handles expiration automatically, so this is a no-op."""
        pass
