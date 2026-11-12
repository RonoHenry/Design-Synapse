"""
Caching utilities for Architectural Service.
"""

import hashlib
import json
import logging
import sys
from datetime import datetime, timedelta
from functools import wraps
from pathlib import Path
from typing import Any, Callable, Dict, Optional, TypeVar, Union

# Add workspace root to path for common packages
workspace_root = Path(__file__).parent.parent.parent.parent.parent
if str(workspace_root) not in sys.path:
    sys.path.insert(0, str(workspace_root))

from packages.common.performance.cache import CacheManager
from packages.common.performance.models import CacheConfig

# Import metrics collector
try:
    from .metrics import get_metrics_collector

    METRICS_AVAILABLE = True
except ImportError:
    METRICS_AVAILABLE = False

    def get_metrics_collector():
        return None


logger = logging.getLogger(__name__)

F = TypeVar("F", bound=Callable[..., Any])


class ArchitecturalServiceCache:
    """Cache manager for Architectural Service."""

    def __init__(self, redis_url: str = "redis://localhost:6379/0"):
        """Initialize cache manager."""
        config = CacheConfig(
            redis_url=redis_url,
            default_ttl=3600,  # 1 hour default
            key_prefix="arch_service:",
            compression_enabled=True,
            compression_threshold=1024,
            serialization_format="json",
        )
        self.cache_manager = CacheManager(config)

    async def close(self):
        """Close cache connections."""
        await self.cache_manager.close()

    def _generate_cache_key(self, prefix: str, *args, **kwargs) -> str:
        """Generate cache key from function arguments."""
        # Create a deterministic key from arguments
        key_data = {"args": args, "kwargs": kwargs}
        key_json = json.dumps(key_data, sort_keys=True, default=str)
        key_hash = hashlib.md5(key_json.encode()).hexdigest()
        return f"{prefix}:{key_hash}"

    def cached(
        self,
        prefix: str,
        ttl: Optional[int] = None,
        invalidation_patterns: Optional[list] = None,
    ):
        """
        Decorator for caching function results.

        Args:
            prefix: Cache key prefix
            ttl: Time to live in seconds (None uses default)
            invalidation_patterns: Patterns for cache invalidation
        """

        def decorator(func: F) -> F:
            @wraps(func)
            async def wrapper(*args, **kwargs):
                import time

                start_time = time.time()

                # Generate cache key
                cache_key = self._generate_cache_key(prefix, *args, **kwargs)

                # Try to get from cache
                result = await self.cache_manager.get(cache_key)
                latency_ms = (time.time() - start_time) * 1000

                if result.value is not None:
                    logger.debug(f"Cache hit for key: {cache_key}")
                    # Record cache hit metric
                    if METRICS_AVAILABLE:
                        metrics = get_metrics_collector()
                        if metrics:
                            metrics.record_cache_operation("hit", prefix, latency_ms)
                    return result.value

                # Cache miss - execute function
                logger.debug(f"Cache miss for key: {cache_key}")
                # Record cache miss metric
                if METRICS_AVAILABLE:
                    metrics = get_metrics_collector()
                    if metrics:
                        metrics.record_cache_operation("miss", prefix, latency_ms)

                value = await func(*args, **kwargs)

                # Store in cache
                set_start = time.time()
                await self.cache_manager.set(cache_key, value, ttl)
                set_latency_ms = (time.time() - set_start) * 1000

                # Record cache set metric
                if METRICS_AVAILABLE:
                    metrics = get_metrics_collector()
                    if metrics:
                        metrics.record_cache_operation("set", prefix, set_latency_ms)

                return value

            return wrapper

        return decorator

    async def invalidate_pattern(self, pattern: str) -> int:
        """Invalidate cache keys matching pattern."""
        return await self.cache_manager.invalidate_pattern(pattern)

    async def invalidate_knowledge_cache(self):
        """Invalidate all knowledge service cache entries."""
        patterns = [
            "knowledge:search:*",
            "knowledge:applicable:*",
            "knowledge:section:*",
        ]
        total_deleted = 0
        for pattern in patterns:
            deleted = await self.invalidate_pattern(pattern)
            total_deleted += deleted
            logger.info(f"Invalidated {deleted} cache entries for pattern: {pattern}")
        return total_deleted

    async def invalidate_rendering_cache(self, design_id: Optional[str] = None):
        """Invalidate rendering cache entries."""
        if design_id:
            pattern = f"rendering:{design_id}:*"
        else:
            pattern = "rendering:*"
        deleted = await self.invalidate_pattern(pattern)
        logger.info(f"Invalidated {deleted} rendering cache entries")
        return deleted


# Global cache instance
_cache_instance: Optional[ArchitecturalServiceCache] = None


def get_cache() -> ArchitecturalServiceCache:
    """Get global cache instance."""
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = ArchitecturalServiceCache()
    return _cache_instance


async def close_cache():
    """Close global cache instance."""
    global _cache_instance
    if _cache_instance:
        await _cache_instance.close()
        _cache_instance = None


async def get_redis_client():
    """Get Redis client for health checks."""
    cache = get_cache()
    return cache.cache_manager.redis_client
