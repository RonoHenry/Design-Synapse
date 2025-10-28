"""
Performance optimization and caching package.

This package provides:
- Redis-based caching for frequently accessed data
- Database connection pooling optimization
- CDN integration for static asset delivery
- Performance monitoring and metrics
"""

from .cache import CacheConfig, CacheManager, CacheResult
from .cdn import CDNConfig, CDNManager
from .connection_pool import ConnectionPoolManager, PoolConfig
from .monitoring import PerformanceMetrics, PerformanceMonitor
from .security import SecurityAuditLogger, SecurityHardening, ThreatDetector

__all__ = [
    "CacheManager",
    "CacheConfig",
    "CacheResult",
    "ConnectionPoolManager",
    "PoolConfig",
    "CDNManager",
    "CDNConfig",
    "PerformanceMonitor",
    "PerformanceMetrics",
    "SecurityHardening",
    "ThreatDetector",
    "SecurityAuditLogger",
]
