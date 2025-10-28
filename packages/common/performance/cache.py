"""
Redis-based caching system for frequently accessed data.

This module provides:
- High-performance Redis-based caching
- Multiple serialization formats (JSON, pickle, msgpack)
- Compression for large values
- Cache hit/miss ratio tracking
- Bulk operations for performance
- Cache invalidation patterns
"""

import asyncio
import gzip
import json
import pickle
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union

import redis.asyncio as redis

from .models import (CacheConfig, CacheEntry, CacheResult, CacheStatus,
                     PerformanceMetrics)


class CacheManager:
    """Redis-based cache manager with performance optimization."""

    def __init__(self, config: CacheConfig):
        """Initialize cache manager with configuration."""
        self.config = config
        self.redis: Optional[redis.Redis] = None
        self._stats = {"hits": 0, "misses": 0, "errors": 0, "total_requests": 0}

    async def _get_redis_client(self) -> redis.Redis:
        """Get or create Redis client."""
        if self.redis is None:
            self.redis = redis.Redis.from_url(
                self.config.redis_url,
                decode_responses=False,  # Handle binary data
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True,
                health_check_interval=30,
            )
        return self.redis

    def _make_key(self, key: str) -> str:
        """Create cache key with prefix."""
        return f"{self.config.key_prefix}{key}"

    def _serialize_value(self, value: Any) -> bytes:
        """Serialize value based on configuration."""
        if self.config.serialization_format == "json":
            serialized = json.dumps(value).encode("utf-8")
        elif self.config.serialization_format == "pickle":
            serialized = pickle.dumps(value)
        else:
            # Default to JSON
            serialized = json.dumps(value).encode("utf-8")

        # Apply compression if enabled and value is large enough
        if (
            self.config.compression_enabled
            and len(serialized) > self.config.compression_threshold
        ):
            serialized = gzip.compress(serialized)

        return serialized

    def _deserialize_value(self, data: bytes) -> Any:
        """Deserialize value based on configuration."""
        try:
            # Try to decompress if compression is enabled
            if self.config.compression_enabled:
                try:
                    data = gzip.decompress(data)
                except gzip.BadGzipFile:
                    # Data is not compressed
                    pass

            if self.config.serialization_format == "json":
                return json.loads(data.decode("utf-8"))
            elif self.config.serialization_format == "pickle":
                return pickle.loads(data)
            else:
                return json.loads(data.decode("utf-8"))
        except Exception:
            # Return raw data if deserialization fails
            return data

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set cache value with optional TTL."""
        try:
            redis_client = await self._get_redis_client()
            cache_key = self._make_key(key)
            serialized_value = self._serialize_value(value)

            ttl = ttl or self.config.default_ttl

            if ttl > 0:
                result = await redis_client.setex(cache_key, ttl, serialized_value)
            else:
                result = await redis_client.set(cache_key, serialized_value)

            return bool(result)
        except Exception:
            self._stats["errors"] += 1
            return False

    async def get(self, key: str) -> CacheResult:
        """Get cache value and return detailed result."""
        start_time = time.time()
        self._stats["total_requests"] += 1

        try:
            redis_client = await self._get_redis_client()
            cache_key = self._make_key(key)

            data = await redis_client.get(cache_key)

            if data is None:
                self._stats["misses"] += 1
                return CacheResult(
                    key=key,
                    value=None,
                    status=CacheStatus.MISS,
                    hit_ratio=await self.get_hit_ratio(),
                    response_time_ms=(time.time() - start_time) * 1000,
                    size_bytes=0,
                )

            # Get TTL for the key
            ttl_remaining = await redis_client.ttl(cache_key)

            value = self._deserialize_value(data)
            self._stats["hits"] += 1

            return CacheResult(
                key=key,
                value=value,
                status=CacheStatus.HIT,
                hit_ratio=await self.get_hit_ratio(),
                response_time_ms=(time.time() - start_time) * 1000,
                size_bytes=len(data),
                ttl_remaining=ttl_remaining if ttl_remaining > 0 else None,
            )

        except Exception:
            self._stats["errors"] += 1
            return CacheResult(
                key=key,
                value=None,
                status=CacheStatus.ERROR,
                hit_ratio=await self.get_hit_ratio(),
                response_time_ms=(time.time() - start_time) * 1000,
                size_bytes=0,
            )

    async def delete(self, key: str) -> bool:
        """Delete cache key."""
        try:
            redis_client = await self._get_redis_client()
            cache_key = self._make_key(key)
            result = await redis_client.delete(cache_key)
            return result > 0
        except Exception:
            return False

    async def exists(self, key: str) -> bool:
        """Check if cache key exists."""
        try:
            redis_client = await self._get_redis_client()
            cache_key = self._make_key(key)
            result = await redis_client.exists(cache_key)
            return result > 0
        except Exception:
            return False

    async def get_hit_ratio(self) -> float:
        """Calculate cache hit ratio."""
        try:
            redis_client = await self._get_redis_client()
            info = await redis_client.info()

            hits = info.get("keyspace_hits", 0)
            misses = info.get("keyspace_misses", 0)

            if hits + misses == 0:
                return 0.0

            return hits / (hits + misses)
        except Exception:
            # Fallback to local stats
            total = self._stats["hits"] + self._stats["misses"]
            if total == 0:
                return 0.0
            return self._stats["hits"] / total

    async def get_performance_metrics(self) -> PerformanceMetrics:
        """Get comprehensive performance metrics."""
        try:
            redis_client = await self._get_redis_client()
            info = await redis_client.info()

            hits = info.get("keyspace_hits", 0)
            misses = info.get("keyspace_misses", 0)
            memory_used = info.get("used_memory", 0)

            hit_ratio = hits / (hits + misses) if (hits + misses) > 0 else 0.0

            return PerformanceMetrics(
                cache_hit_ratio=hit_ratio,
                cache_miss_ratio=1.0 - hit_ratio,
                avg_response_time_ms=0.0,  # Would need to track this
                p95_response_time_ms=0.0,
                p99_response_time_ms=0.0,
                total_requests=hits + misses,
                error_rate=0.0,
                memory_usage_mb=memory_used / (1024 * 1024),
                cpu_usage_percent=0.0,
                active_connections=0,
                pool_utilization=0.0,
                cdn_hit_ratio=0.0,
            )
        except Exception:
            return PerformanceMetrics(
                cache_hit_ratio=0.0,
                cache_miss_ratio=1.0,
                avg_response_time_ms=0.0,
                p95_response_time_ms=0.0,
                p99_response_time_ms=0.0,
                total_requests=0,
                error_rate=1.0,
                memory_usage_mb=0.0,
                cpu_usage_percent=0.0,
                active_connections=0,
                pool_utilization=0.0,
                cdn_hit_ratio=0.0,
            )

    async def set_many(self, data: Dict[str, Any], ttl: Optional[int] = None) -> bool:
        """Set multiple cache values in bulk."""
        try:
            redis_client = await self._get_redis_client()
            pipe = redis_client.pipeline()

            ttl = ttl or self.config.default_ttl

            for key, value in data.items():
                cache_key = self._make_key(key)
                serialized_value = self._serialize_value(value)

                if ttl > 0:
                    pipe.setex(cache_key, ttl, serialized_value)
                else:
                    pipe.set(cache_key, serialized_value)

            await pipe.execute()
            return True
        except Exception:
            return False

    async def get_many(self, keys: List[str]) -> List[CacheResult]:
        """Get multiple cache values in bulk."""
        results = []

        try:
            redis_client = await self._get_redis_client()
            cache_keys = [self._make_key(key) for key in keys]

            values = await redis_client.mget(cache_keys)

            for i, (key, data) in enumerate(zip(keys, values)):
                if data is None:
                    results.append(
                        CacheResult(
                            key=key,
                            value=None,
                            status=CacheStatus.MISS,
                            hit_ratio=0.0,
                            response_time_ms=0.0,
                            size_bytes=0,
                        )
                    )
                else:
                    value = self._deserialize_value(data)
                    results.append(
                        CacheResult(
                            key=key,
                            value=value,
                            status=CacheStatus.HIT,
                            hit_ratio=0.0,
                            response_time_ms=0.0,
                            size_bytes=len(data),
                        )
                    )
        except Exception:
            # Return error results for all keys
            for key in keys:
                results.append(
                    CacheResult(
                        key=key,
                        value=None,
                        status=CacheStatus.ERROR,
                        hit_ratio=0.0,
                        response_time_ms=0.0,
                        size_bytes=0,
                    )
                )

        return results

    async def invalidate_pattern(self, pattern: str) -> int:
        """Invalidate cache keys matching pattern."""
        try:
            redis_client = await self._get_redis_client()
            cache_pattern = self._make_key(pattern)

            keys = await redis_client.keys(cache_pattern)
            if keys:
                deleted = await redis_client.delete(*keys)
                return deleted
            return 0
        except Exception:
            return 0

    async def get_memory_usage(self) -> float:
        """Get cache memory usage in MB."""
        try:
            redis_client = await self._get_redis_client()
            info = await redis_client.info()
            memory_used = info.get("used_memory", 0)
            return memory_used / (1024 * 1024)
        except Exception:
            return 0.0

    async def close(self):
        """Close Redis connection."""
        if self.redis:
            await self.redis.close()
