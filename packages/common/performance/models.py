"""
Performance optimization models and data structures.
"""

import json
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Union


class CacheStrategy(Enum):
    """Cache strategy types."""

    LRU = "lru"  # Least Recently Used
    LFU = "lfu"  # Least Frequently Used
    TTL = "ttl"  # Time To Live
    WRITE_THROUGH = "write_through"
    WRITE_BACK = "write_back"


class CacheStatus(Enum):
    """Cache operation status."""

    HIT = "hit"
    MISS = "miss"
    EXPIRED = "expired"
    ERROR = "error"


@dataclass
class CacheConfig:
    """Configuration for cache management."""

    redis_url: str = "redis://localhost:6379/0"
    default_ttl: int = 3600  # 1 hour
    max_memory: str = "100mb"
    eviction_policy: str = "allkeys-lru"
    key_prefix: str = "cache:"
    compression_enabled: bool = True
    compression_threshold: int = 1024  # bytes
    serialization_format: str = "json"  # json, pickle, msgpack


@dataclass
class CacheResult:
    """Result of a cache operation."""

    key: str
    value: Any
    status: CacheStatus
    hit_ratio: float
    response_time_ms: float
    size_bytes: int
    ttl_remaining: Optional[int] = None
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class PoolConfig:
    """Database connection pool configuration."""

    min_connections: int = 5
    max_connections: int = 20
    max_idle_time: int = 300  # 5 minutes
    max_lifetime: int = 3600  # 1 hour
    connection_timeout: int = 30
    retry_attempts: int = 3
    health_check_interval: int = 60
    pool_pre_ping: bool = True


@dataclass
class CDNConfig:
    """CDN configuration for static assets."""

    provider: str = "cloudflare"  # cloudflare, aws, azure
    base_url: str = ""
    api_key: str = ""
    zone_id: str = ""
    cache_ttl: int = 86400  # 24 hours
    compression_enabled: bool = True
    minification_enabled: bool = True
    supported_formats: List[str] = field(
        default_factory=lambda: [
            "js",
            "css",
            "png",
            "jpg",
            "jpeg",
            "gif",
            "svg",
            "woff",
            "woff2",
        ]
    )


@dataclass
class PerformanceMetrics:
    """Performance monitoring metrics."""

    cache_hit_ratio: float
    cache_miss_ratio: float
    avg_response_time_ms: float
    p95_response_time_ms: float
    p99_response_time_ms: float
    total_requests: int
    error_rate: float
    memory_usage_mb: float
    cpu_usage_percent: float
    active_connections: int
    pool_utilization: float
    cdn_hit_ratio: float
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class CacheEntry:
    """Internal cache entry representation."""

    key: str
    value: Any
    created_at: datetime
    expires_at: Optional[datetime] = None
    access_count: int = 0
    last_accessed: datetime = field(default_factory=datetime.utcnow)
    size_bytes: int = 0

    def is_expired(self) -> bool:
        """Check if cache entry is expired."""
        if self.expires_at is None:
            return False
        return datetime.utcnow() > self.expires_at

    def touch(self) -> None:
        """Update last accessed time and increment access count."""
        self.last_accessed = datetime.utcnow()
        self.access_count += 1


@dataclass
class ConnectionStats:
    """Database connection pool statistics."""

    total_connections: int
    active_connections: int
    idle_connections: int
    failed_connections: int
    avg_connection_time_ms: float
    pool_utilization: float
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class CDNStats:
    """CDN performance statistics."""

    total_requests: int
    cache_hits: int
    cache_misses: int
    hit_ratio: float
    avg_response_time_ms: float
    bandwidth_saved_mb: float
    timestamp: datetime = field(default_factory=datetime.utcnow)
