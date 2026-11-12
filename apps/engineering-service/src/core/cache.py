"""Redis cache configuration and management for Engineering Service."""

import json
from typing import Any, Optional

import redis.asyncio as redis

from .config import settings

# Global Redis client instance
_redis_client: Optional[redis.Redis] = None


async def get_redis_client() -> redis.Redis:
    """Get or create the Redis client.

    Returns:
        redis.Redis: Redis client instance
    """
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True,
            socket_connect_timeout=5,
            socket_keepalive=True,
        )
    return _redis_client


async def close_redis() -> None:
    """Close Redis connection."""
    global _redis_client
    if _redis_client is not None:
        await _redis_client.close()
        _redis_client = None


class CacheService:
    """Service for caching operations."""

    def __init__(self, redis_client: redis.Redis):
        """Initialize cache service.

        Args:
            redis_client: Redis client instance
        """
        self.redis = redis_client

    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found
        """
        try:
            value = await self.redis.get(key)
            if value is not None:
                return json.loads(value)
            return None
        except Exception:
            # Log error but don't fail on cache miss
            return None

    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
    ) -> bool:
        """Set value in cache.

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds (default from settings)

        Returns:
            True if successful, False otherwise
        """
        try:
            ttl = ttl or settings.redis_cache_ttl
            serialized = json.dumps(value)
            await self.redis.setex(key, ttl, serialized)
            return True
        except Exception:
            # Log error but don't fail on cache write
            return False

    async def delete(self, key: str) -> bool:
        """Delete value from cache.

        Args:
            key: Cache key

        Returns:
            True if successful, False otherwise
        """
        try:
            await self.redis.delete(key)
            return True
        except Exception:
            return False

    async def exists(self, key: str) -> bool:
        """Check if key exists in cache.

        Args:
            key: Cache key

        Returns:
            True if key exists, False otherwise
        """
        try:
            return await self.redis.exists(key) > 0
        except Exception:
            return False

    async def clear_pattern(self, pattern: str) -> int:
        """Clear all keys matching pattern.

        Args:
            pattern: Key pattern (e.g., "calculation:*")

        Returns:
            Number of keys deleted
        """
        try:
            keys = []
            async for key in self.redis.scan_iter(match=pattern):
                keys.append(key)

            if keys:
                return await self.redis.delete(*keys)
            return 0
        except Exception:
            return 0

    async def ping(self) -> bool:
        """Check if Redis is available.

        Returns:
            True if Redis is available, False otherwise
        """
        try:
            return await self.redis.ping()
        except Exception:
            return False


async def get_cache_service() -> CacheService:
    """Dependency for getting cache service.

    Returns:
        CacheService: Cache service instance
    """
    redis_client = await get_redis_client()
    return CacheService(redis_client)
