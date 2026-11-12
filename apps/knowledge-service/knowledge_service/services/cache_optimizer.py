"""
Cache optimization and monitoring utilities for vector search.

This module provides advanced cache optimization features including:
- Cache performance analysis
- Automatic cache tuning
- Cache preloading strategies
- Memory usage optimization
"""

import asyncio
import logging
import statistics
import time
from collections import defaultdict, deque
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class CachePerformanceMonitor:
    """Monitor and analyze cache performance metrics."""

    def __init__(self, window_size: int = 1000):
        self.window_size = window_size
        self.response_times = deque(maxlen=window_size)
        self.hit_miss_history = deque(maxlen=window_size)
        self.query_patterns = defaultdict(int)
        self.user_patterns = defaultdict(int)
        self.project_patterns = defaultdict(int)
        self.start_time = time.time()

    def record_cache_access(
        self,
        query: str,
        hit: bool,
        response_time: float,
        user_id: Optional[str] = None,
        project_id: Optional[str] = None,
    ):
        """Record a cache access for performance analysis."""
        self.response_times.append(response_time)
        self.hit_miss_history.append(hit)

        # Track query patterns
        query_key = query.lower().strip()[:50]  # First 50 chars
        self.query_patterns[query_key] += 1

        if user_id:
            self.user_patterns[user_id] += 1

        if project_id:
            self.project_patterns[project_id] += 1

    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get comprehensive performance metrics."""
        if not self.response_times:
            return {"status": "no_data"}

        hit_rate = (
            sum(self.hit_miss_history) / len(self.hit_miss_history)
            if self.hit_miss_history
            else 0
        )

        return {
            "hit_rate": hit_rate,
            "avg_response_time": statistics.mean(self.response_times),
            "median_response_time": statistics.median(self.response_times),
            "p95_response_time": statistics.quantiles(self.response_times, n=20)[18]
            if len(self.response_times) > 20
            else max(self.response_times),
            "total_requests": len(self.response_times),
            "uptime_hours": (time.time() - self.start_time) / 3600,
            "top_queries": dict(
                sorted(self.query_patterns.items(), key=lambda x: x[1], reverse=True)[
                    :10
                ]
            ),
            "top_users": dict(
                sorted(self.user_patterns.items(), key=lambda x: x[1], reverse=True)[
                    :10
                ]
            ),
            "top_projects": dict(
                sorted(self.project_patterns.items(), key=lambda x: x[1], reverse=True)[
                    :10
                ]
            ),
        }

    def get_optimization_recommendations(self) -> List[str]:
        """Get cache optimization recommendations based on performance data."""
        recommendations = []

        if not self.response_times:
            return ["Insufficient data for recommendations"]

        metrics = self.get_performance_metrics()

        # Hit rate recommendations
        if metrics["hit_rate"] < 0.5:
            recommendations.append(
                "Low cache hit rate (<50%). Consider increasing cache size or TTL."
            )
        elif metrics["hit_rate"] < 0.7:
            recommendations.append(
                "Moderate cache hit rate. Consider cache warming for common queries."
            )

        # Response time recommendations
        if metrics["avg_response_time"] > 0.1:  # 100ms
            recommendations.append(
                "High average response time. Consider enabling compression or optimizing cache storage."
            )

        # Usage pattern recommendations
        if len(self.query_patterns) > 100 and metrics["hit_rate"] < 0.8:
            recommendations.append(
                "High query diversity with low hit rate. Consider increasing cache size."
            )

        # User/project pattern recommendations
        if len(self.user_patterns) > 10:
            recommendations.append(
                "Multiple users detected. Ensure user-specific cache partitioning is enabled."
            )

        if len(self.project_patterns) > 5:
            recommendations.append(
                "Multiple projects detected. Consider project-specific cache warming."
            )

        return recommendations if recommendations else ["Cache performance is optimal"]


class CacheOptimizer:
    """Automatic cache optimization and tuning."""

    def __init__(self, vector_search_service):
        self.service = vector_search_service
        self.monitor = CachePerformanceMonitor()
        self.optimization_history = []

    async def analyze_and_optimize(self) -> Dict[str, Any]:
        """Analyze cache performance and apply optimizations."""
        logger.info("Starting cache performance analysis and optimization")

        # Get current cache statistics
        cache_stats = self.service.get_cache_stats()
        performance_metrics = self.monitor.get_performance_metrics()

        optimizations_applied = []

        # Optimization 1: Adjust cache sizes based on usage
        search_cache_stats = cache_stats.get("search_cache", {})
        embedding_cache_stats = cache_stats.get("embedding_cache", {})

        if (
            search_cache_stats.get("hit_rate", 0) > 0.9
            and search_cache_stats.get("size", 0)
            < search_cache_stats.get("max_size", 1000) * 0.8
        ):
            # High hit rate but cache not full - could reduce size
            new_size = max(500, int(search_cache_stats.get("max_size", 1000) * 0.8))
            self.service.configure_cache(max_search_cache_size=new_size)
            optimizations_applied.append(f"Reduced search cache size to {new_size}")

        elif (
            search_cache_stats.get("hit_rate", 0) < 0.6
            and search_cache_stats.get("evictions", 0) > 100
        ):
            # Low hit rate with many evictions - increase size
            new_size = min(5000, int(search_cache_stats.get("max_size", 1000) * 1.5))
            self.service.configure_cache(max_search_cache_size=new_size)
            optimizations_applied.append(f"Increased search cache size to {new_size}")

        # Optimization 2: Adjust TTL based on query patterns
        if performance_metrics.get("status") != "no_data":
            top_queries = performance_metrics.get("top_queries", {})
            if len(top_queries) > 0:
                # If we have frequently repeated queries, increase TTL
                max_query_count = max(top_queries.values()) if top_queries else 0
                if max_query_count > 50:  # Very frequent queries
                    self.service.configure_cache(search_cache_ttl=7200)  # 2 hours
                    optimizations_applied.append(
                        "Increased cache TTL to 2 hours for frequent queries"
                    )

        # Optimization 3: Enable compression if not already enabled and cache is large
        if (
            not self.service.search_cache.use_compression
            and search_cache_stats.get("size", 0) > 500
        ):
            self.service.configure_cache(enable_compression=True)
            optimizations_applied.append("Enabled cache compression for large cache")

        # Record optimization
        optimization_record = {
            "timestamp": datetime.now().isoformat(),
            "cache_stats": cache_stats,
            "performance_metrics": performance_metrics,
            "optimizations_applied": optimizations_applied,
        }
        self.optimization_history.append(optimization_record)

        # Keep only last 10 optimization records
        if len(self.optimization_history) > 10:
            self.optimization_history = self.optimization_history[-10:]

        logger.info(
            f"Cache optimization completed. Applied {len(optimizations_applied)} optimizations."
        )

        return optimization_record

    async def preload_cache_intelligently(
        self,
        recent_queries: List[str],
        user_project_mapping: Optional[Dict[str, List[str]]] = None,
    ) -> Dict[str, Any]:
        """Intelligently preload cache based on usage patterns."""
        logger.info("Starting intelligent cache preloading")

        preload_stats = {
            "queries_preloaded": 0,
            "embeddings_preloaded": 0,
            "errors": 0,
            "start_time": time.time(),
        }

        try:
            # Preload embeddings for common query terms
            unique_terms = set()
            for query in recent_queries:
                unique_terms.update(query.lower().split())

            # Preload embeddings for individual terms (useful for query expansion)
            common_terms = [term for term in unique_terms if len(term) > 3][
                :50
            ]  # Limit to 50 terms
            await self.service.warm_up_embeddings_cache(common_terms)
            preload_stats["embeddings_preloaded"] = len(common_terms)

            # Preload search results for recent queries
            if user_project_mapping:
                # Create filters for each user-project combination
                filters = []
                for user_id, projects in user_project_mapping.items():
                    for project_id in projects:
                        filters.append({"user_id": user_id, "project_id": project_id})

                await self.service.warm_up_cache(
                    recent_queries[:20], filters[:10]
                )  # Limit to prevent overload
                preload_stats["queries_preloaded"] = min(20, len(recent_queries)) * min(
                    10, len(filters)
                )
            else:
                # Preload without filters
                await self.service.warm_up_cache(recent_queries[:30])
                preload_stats["queries_preloaded"] = min(30, len(recent_queries))

        except Exception as e:
            logger.error(f"Error during cache preloading: {e}")
            preload_stats["errors"] += 1

        preload_stats["duration_seconds"] = time.time() - preload_stats["start_time"]
        logger.info(
            f"Cache preloading completed in {preload_stats['duration_seconds']:.2f}s"
        )

        return preload_stats

    def get_optimization_history(self) -> List[Dict[str, Any]]:
        """Get the history of cache optimizations."""
        return self.optimization_history.copy()


class CacheHealthChecker:
    """Monitor cache health and detect issues."""

    def __init__(self, vector_search_service):
        self.service = vector_search_service

    async def check_cache_health(self) -> Dict[str, Any]:
        """Perform comprehensive cache health check."""
        health_report = {
            "timestamp": datetime.now().isoformat(),
            "overall_status": "healthy",
            "issues": [],
            "warnings": [],
            "recommendations": [],
        }

        try:
            # Get service health (includes cache health)
            service_health = self.service.get_service_health()
            cache_stats = self.service.get_cache_stats()

            # Check cache connectivity
            if not service_health.get("cache_healthy", True):
                health_report["issues"].append("Cache connectivity issues detected")
                health_report["overall_status"] = "degraded"

            # Check cache performance
            search_cache_stats = cache_stats.get("search_cache", {})
            hit_rate = search_cache_stats.get("hit_rate", 0)

            if hit_rate < 0.3:
                health_report["issues"].append(
                    f"Very low cache hit rate: {hit_rate:.2%}"
                )
                health_report["overall_status"] = "degraded"
            elif hit_rate < 0.6:
                health_report["warnings"].append(f"Low cache hit rate: {hit_rate:.2%}")

            # Check cache size utilization
            cache_size = search_cache_stats.get("size", 0)
            max_size = search_cache_stats.get("max_size", 1000)
            utilization = cache_size / max_size if max_size > 0 else 0

            if utilization > 0.95:
                health_report["warnings"].append(
                    f"Cache nearly full: {utilization:.1%} utilization"
                )
                health_report["recommendations"].append(
                    "Consider increasing cache size"
                )

            # Check eviction rate
            evictions = search_cache_stats.get("evictions", 0)
            sets = search_cache_stats.get("sets", 1)
            eviction_rate = evictions / sets if sets > 0 else 0

            if eviction_rate > 0.5:
                health_report["warnings"].append(
                    f"High eviction rate: {eviction_rate:.1%}"
                )
                health_report["recommendations"].append(
                    "Consider increasing cache size or TTL"
                )

            # Check compression effectiveness
            if search_cache_stats.get("use_compression", False):
                compression_ratio = search_cache_stats.get("compression_ratio", 1.0)
                if compression_ratio > 0.8:  # Poor compression
                    health_report["warnings"].append(
                        f"Poor compression ratio: {compression_ratio:.2f}"
                    )
                    health_report["recommendations"].append(
                        "Consider disabling compression for better performance"
                    )

            # Check Redis connectivity if applicable
            if search_cache_stats.get("type") == "redis":
                # Redis-specific health checks could be added here
                pass

        except Exception as e:
            health_report["issues"].append(f"Health check failed: {str(e)}")
            health_report["overall_status"] = "error"

        return health_report

    async def run_cache_diagnostics(self) -> Dict[str, Any]:
        """Run detailed cache diagnostics."""
        diagnostics = {
            "timestamp": datetime.now().isoformat(),
            "cache_stats": {},
            "performance_test": {},
            "connectivity_test": {},
        }

        try:
            # Get detailed cache statistics
            diagnostics["cache_stats"] = self.service.get_cache_stats()

            # Performance test - measure cache response times
            test_queries = ["test query 1", "test query 2", "test query 3"]
            test_results = [{"resource_id": 1, "score": 0.9}]

            # Test cache set performance
            start_time = time.time()
            for i, query in enumerate(test_queries):
                self.service.search_cache.set(f"diag_{query}", None, 5, test_results)
            set_time = time.time() - start_time

            # Test cache get performance
            start_time = time.time()
            for i, query in enumerate(test_queries):
                self.service.search_cache.get(f"diag_{query}", None, 5)
            get_time = time.time() - start_time

            diagnostics["performance_test"] = {
                "set_time_ms": set_time * 1000,
                "get_time_ms": get_time * 1000,
                "avg_set_time_ms": (set_time / len(test_queries)) * 1000,
                "avg_get_time_ms": (get_time / len(test_queries)) * 1000,
            }

            # Clean up test entries
            for query in test_queries:
                try:
                    self.service.search_cache.invalidate_pattern(f"diag_{query}")
                except:
                    pass

            # Connectivity test
            if (
                hasattr(self.service.search_cache, "redis_client")
                and self.service.search_cache.redis_client
            ):
                try:
                    self.service.search_cache.redis_client.ping()
                    diagnostics["connectivity_test"]["redis"] = "connected"
                except Exception as e:
                    diagnostics["connectivity_test"]["redis"] = f"error: {str(e)}"
            else:
                diagnostics["connectivity_test"]["redis"] = "not_configured"

        except Exception as e:
            diagnostics["error"] = str(e)

        return diagnostics
