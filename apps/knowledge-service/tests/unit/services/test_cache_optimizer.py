"""
Tests for cache optimization and monitoring utilities.
"""

import time
from unittest.mock import MagicMock, Mock, patch

import pytest
from knowledge_service.services.cache_optimizer import (
    CacheHealthChecker, CacheOptimizer, CachePerformanceMonitor)


class TestCachePerformanceMonitor:
    """Test cache performance monitoring."""

    def test_record_cache_access(self):
        """Test recording cache access metrics."""
        monitor = CachePerformanceMonitor(window_size=10)

        # Record some cache accesses
        monitor.record_cache_access("machine learning", True, 0.05, "user1", "proj1")
        monitor.record_cache_access("deep learning", False, 0.15, "user1", "proj1")
        monitor.record_cache_access("machine learning", True, 0.03, "user2", "proj2")

        assert len(monitor.response_times) == 3
        assert len(monitor.hit_miss_history) == 3
        assert monitor.query_patterns["machine learning"] == 2
        assert monitor.query_patterns["deep learning"] == 1
        assert monitor.user_patterns["user1"] == 2
        assert monitor.project_patterns["proj1"] == 2

    def test_get_performance_metrics(self):
        """Test getting performance metrics."""
        monitor = CachePerformanceMonitor()

        # No data case
        metrics = monitor.get_performance_metrics()
        assert metrics["status"] == "no_data"

        # With data
        monitor.record_cache_access("query1", True, 0.05)
        monitor.record_cache_access("query2", False, 0.10)
        monitor.record_cache_access("query3", True, 0.03)

        metrics = monitor.get_performance_metrics()
        assert metrics["hit_rate"] == 2 / 3  # 2 hits out of 3
        assert metrics["avg_response_time"] == (0.05 + 0.10 + 0.03) / 3
        assert metrics["total_requests"] == 3

    def test_get_optimization_recommendations(self):
        """Test getting optimization recommendations."""
        monitor = CachePerformanceMonitor()

        # No data case
        recommendations = monitor.get_optimization_recommendations()
        assert "Insufficient data for recommendations" in recommendations

        # Low hit rate case
        for i in range(10):
            monitor.record_cache_access(f"query{i}", False, 0.05)  # All misses

        recommendations = monitor.get_optimization_recommendations()
        assert any("Low cache hit rate" in rec for rec in recommendations)

        # High response time case
        monitor = CachePerformanceMonitor()
        for i in range(10):
            monitor.record_cache_access(f"query{i}", True, 0.2)  # High response times

        recommendations = monitor.get_optimization_recommendations()
        assert any("High average response time" in rec for rec in recommendations)


class TestCacheOptimizer:
    """Test cache optimization functionality."""

    @pytest.fixture
    def mock_vector_service(self):
        """Create a mock vector search service."""
        service = Mock()
        service.get_cache_stats.return_value = {
            "search_cache": {
                "hit_rate": 0.7,
                "size": 500,
                "max_size": 1000,
                "evictions": 10,
                "sets": 100,
                "use_compression": False,
            },
            "embedding_cache": {"hit_rate": 0.8, "size": 200, "max_size": 500},
        }
        service.configure_cache = Mock()
        service.warm_up_cache = Mock()
        service.warm_up_embeddings_cache = Mock()
        service.search_cache = Mock()
        service.search_cache.use_compression = False
        return service

    @pytest.mark.asyncio
    async def test_analyze_and_optimize(self, mock_vector_service):
        """Test cache analysis and optimization."""
        optimizer = CacheOptimizer(mock_vector_service)

        # Mock performance metrics
        optimizer.monitor.get_performance_metrics = Mock(
            return_value={
                "status": "ok",
                "top_queries": {"query1": 60, "query2": 30},  # Frequent queries
            }
        )

        result = await optimizer.analyze_and_optimize()

        assert "timestamp" in result
        assert "optimizations_applied" in result
        assert len(optimizer.optimization_history) == 1

        # Should have called configure_cache for TTL adjustment
        mock_vector_service.configure_cache.assert_called()

    @pytest.mark.asyncio
    async def test_preload_cache_intelligently(self, mock_vector_service):
        """Test intelligent cache preloading."""
        optimizer = CacheOptimizer(mock_vector_service)

        recent_queries = ["machine learning", "deep learning", "neural networks"]
        user_project_mapping = {"user1": ["proj1", "proj2"], "user2": ["proj3"]}

        result = await optimizer.preload_cache_intelligently(
            recent_queries, user_project_mapping
        )

        assert "queries_preloaded" in result
        assert "embeddings_preloaded" in result
        assert "duration_seconds" in result

        # Should have called warm up methods
        mock_vector_service.warm_up_embeddings_cache.assert_called_once()
        mock_vector_service.warm_up_cache.assert_called_once()

    def test_get_optimization_history(self, mock_vector_service):
        """Test getting optimization history."""
        optimizer = CacheOptimizer(mock_vector_service)

        # Add some history
        optimizer.optimization_history = [
            {"timestamp": "2023-01-01", "optimizations": ["test1"]},
            {"timestamp": "2023-01-02", "optimizations": ["test2"]},
        ]

        history = optimizer.get_optimization_history()
        assert len(history) == 2
        assert history[0]["timestamp"] == "2023-01-01"


class TestCacheHealthChecker:
    """Test cache health checking functionality."""

    @pytest.fixture
    def mock_vector_service(self):
        """Create a mock vector search service."""
        service = Mock()
        service.get_service_health.return_value = {
            "cache_healthy": True,
            "pinecone_healthy": True,
        }
        service.get_cache_stats.return_value = {
            "search_cache": {
                "hit_rate": 0.8,
                "size": 800,
                "max_size": 1000,
                "evictions": 5,
                "sets": 100,
                "use_compression": True,
                "compression_ratio": 0.3,
                "type": "memory",
            }
        }
        service.search_cache = Mock()
        return service

    @pytest.mark.asyncio
    async def test_check_cache_health_healthy(self, mock_vector_service):
        """Test cache health check with healthy cache."""
        checker = CacheHealthChecker(mock_vector_service)

        health_report = await checker.check_cache_health()

        assert health_report["overall_status"] == "healthy"
        assert len(health_report["issues"]) == 0
        assert "timestamp" in health_report

    @pytest.mark.asyncio
    async def test_check_cache_health_issues(self, mock_vector_service):
        """Test cache health check with issues."""
        # Mock unhealthy cache
        mock_vector_service.get_service_health.return_value = {"cache_healthy": False}
        mock_vector_service.get_cache_stats.return_value = {
            "search_cache": {
                "hit_rate": 0.2,  # Very low hit rate
                "size": 950,
                "max_size": 1000,  # Nearly full
                "evictions": 500,
                "sets": 600,  # High eviction rate
                "use_compression": True,
                "compression_ratio": 0.9,  # Poor compression
                "type": "memory",
            }
        }

        checker = CacheHealthChecker(mock_vector_service)
        health_report = await checker.check_cache_health()

        assert health_report["overall_status"] == "degraded"
        assert len(health_report["issues"]) > 0
        assert len(health_report["warnings"]) > 0
        assert len(health_report["recommendations"]) > 0

    @pytest.mark.asyncio
    async def test_run_cache_diagnostics(self, mock_vector_service):
        """Test running cache diagnostics."""
        checker = CacheHealthChecker(mock_vector_service)

        diagnostics = await checker.run_cache_diagnostics()

        assert "timestamp" in diagnostics
        assert "cache_stats" in diagnostics
        assert "performance_test" in diagnostics
        assert "connectivity_test" in diagnostics

        # Performance test should have timing data
        perf_test = diagnostics["performance_test"]
        assert "set_time_ms" in perf_test
        assert "get_time_ms" in perf_test
        assert "avg_set_time_ms" in perf_test
        assert "avg_get_time_ms" in perf_test

    @pytest.mark.asyncio
    async def test_run_cache_diagnostics_with_redis(self, mock_vector_service):
        """Test cache diagnostics with Redis."""
        # Mock Redis client
        mock_redis = Mock()
        mock_redis.ping.return_value = True
        mock_vector_service.search_cache.redis_client = mock_redis

        checker = CacheHealthChecker(mock_vector_service)
        diagnostics = await checker.run_cache_diagnostics()

        assert diagnostics["connectivity_test"]["redis"] == "connected"
        mock_redis.ping.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_cache_diagnostics_redis_error(self, mock_vector_service):
        """Test cache diagnostics with Redis connection error."""
        # Mock Redis client with error
        mock_redis = Mock()
        mock_redis.ping.side_effect = Exception("Connection failed")
        mock_vector_service.search_cache.redis_client = mock_redis

        checker = CacheHealthChecker(mock_vector_service)
        diagnostics = await checker.run_cache_diagnostics()

        assert "error: Connection failed" in diagnostics["connectivity_test"]["redis"]
