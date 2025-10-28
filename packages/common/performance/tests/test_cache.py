"""
Tests for cache management system.

Following TDD approach:
1. RED: Write failing tests first
2. GREEN: Implement minimal code to pass tests
3. REFACTOR: Optimize and improve code quality
"""

import json
import time
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest

from ..cache import CacheEntry, CacheManager
from ..models import CacheConfig, CacheResult, CacheStatus, CacheStrategy


class TestCacheManager:
    """Test cache manager functionality."""

    @pytest.mark.asyncio
    async def test_cache_manager_initialization(self, cache_config):
        """Test cache manager can be initialized with config."""
        # This test will fail until we implement CacheManager
        cache_manager = CacheManager(cache_config)
        assert cache_manager.config == cache_config
        assert cache_manager.redis is not None

    @pytest.mark.asyncio
    async def test_cache_set_and_get_basic(self, cache_config, mock_redis):
        """Test basic cache set and get operations."""
        with patch("redis.asyncio.Redis.from_url", return_value=mock_redis):
            cache_manager = CacheManager(cache_config)

            # Test setting a value
            result = await cache_manager.set("test_key", "test_value")
            assert result is True

            # Test getting the value
            cached_result = await cache_manager.get("test_key")
            assert cached_result.status == CacheStatus.HIT
            assert cached_result.value == "test_value"
            assert cached_result.key == "test_key"

    @pytest.mark.asyncio
    async def test_cache_miss(self, cache_config, mock_redis):
        """Test cache miss scenario."""
        mock_redis.get.return_value = None

        with patch("redis.asyncio.Redis.from_url", return_value=mock_redis):
            cache_manager = CacheManager(cache_config)

            result = await cache_manager.get("nonexistent_key")
            assert result.status == CacheStatus.MISS
            assert result.value is None

    @pytest.mark.asyncio
    async def test_cache_with_ttl(self, cache_config, mock_redis):
        """Test cache operations with TTL."""
        with patch("redis.asyncio.Redis.from_url", return_value=mock_redis):
            cache_manager = CacheManager(cache_config)

            # Set with custom TTL
            result = await cache_manager.set("ttl_key", "ttl_value", ttl=60)
            assert result is True

            # Verify setex was called with correct parameters
            mock_redis.setex.assert_called_once()

    @pytest.mark.asyncio
    async def test_cache_delete(self, cache_config, mock_redis):
        """Test cache deletion."""
        with patch("redis.asyncio.Redis.from_url", return_value=mock_redis):
            cache_manager = CacheManager(cache_config)

            result = await cache_manager.delete("test_key")
            assert result is True
            mock_redis.delete.assert_called_once()

    @pytest.mark.asyncio
    async def test_cache_exists(self, cache_config, mock_redis):
        """Test checking if cache key exists."""
        mock_redis.exists.return_value = 1

        with patch("redis.asyncio.Redis.from_url", return_value=mock_redis):
            cache_manager = CacheManager(cache_config)

            exists = await cache_manager.exists("test_key")
            assert exists is True

    @pytest.mark.asyncio
    async def test_cache_hit_ratio_calculation(self, cache_config, mock_redis):
        """Test cache hit ratio calculation."""
        # Mock Redis info response
        mock_redis.info.return_value = {
            "keyspace_hits": 150,
            "keyspace_misses": 50,
        }

        with patch("redis.asyncio.Redis.from_url", return_value=mock_redis):
            cache_manager = CacheManager(cache_config)

            hit_ratio = await cache_manager.get_hit_ratio()
            assert hit_ratio == 0.75  # 150 / (150 + 50)

    @pytest.mark.asyncio
    async def test_cache_performance_metrics(self, cache_config, mock_redis):
        """Test cache performance metrics collection."""
        mock_redis.info.return_value = {
            "keyspace_hits": 100,
            "keyspace_misses": 25,
            "used_memory": 2048,
        }

        with patch("redis.asyncio.Redis.from_url", return_value=mock_redis):
            cache_manager = CacheManager(cache_config)

            metrics = await cache_manager.get_performance_metrics()
            assert metrics.cache_hit_ratio == 0.8  # 100 / (100 + 25)
            assert metrics.memory_usage_mb > 0

    @pytest.mark.asyncio
    async def test_cache_bulk_operations(
        self, cache_config, mock_redis, sample_cache_data
    ):
        """Test bulk cache operations for performance."""
        with patch("redis.asyncio.Redis.from_url", return_value=mock_redis):
            cache_manager = CacheManager(cache_config)

            # Test bulk set
            result = await cache_manager.set_many(sample_cache_data)
            assert result is True

            # Test bulk get
            keys = list(sample_cache_data.keys())
            results = await cache_manager.get_many(keys)
            assert len(results) == len(keys)

    @pytest.mark.asyncio
    async def test_cache_compression(self, cache_config, mock_redis):
        """Test cache compression for large values."""
        cache_config.compression_enabled = True
        cache_config.compression_threshold = 100

        large_value = "x" * 1000  # Large string to trigger compression

        with patch("redis.asyncio.Redis.from_url", return_value=mock_redis):
            cache_manager = CacheManager(cache_config)

            result = await cache_manager.set("large_key", large_value)
            assert result is True

    @pytest.mark.asyncio
    async def test_cache_serialization_formats(self, cache_config, mock_redis):
        """Test different serialization formats."""
        test_data = {"complex": {"nested": [1, 2, 3]}}

        for format_type in ["json", "pickle"]:
            cache_config.serialization_format = format_type

            with patch("redis.asyncio.Redis.from_url", return_value=mock_redis):
                cache_manager = CacheManager(cache_config)

                result = await cache_manager.set("complex_key", test_data)
                assert result is True

    @pytest.mark.asyncio
    async def test_cache_invalidation_patterns(self, cache_config, mock_redis):
        """Test cache invalidation by pattern."""
        mock_redis.keys.return_value = ["test_cache:user:1", "test_cache:user:2"]

        with patch("redis.asyncio.Redis.from_url", return_value=mock_redis):
            cache_manager = CacheManager(cache_config)

            result = await cache_manager.invalidate_pattern("user:*")
            assert result > 0

    @pytest.mark.asyncio
    async def test_cache_error_handling(self, cache_config):
        """Test cache error handling when Redis is unavailable."""
        # Mock Redis connection failure
        with patch(
            "redis.asyncio.Redis.from_url", side_effect=Exception("Connection failed")
        ):
            cache_manager = CacheManager(cache_config)

            # Should handle errors gracefully
            result = await cache_manager.get("test_key")
            assert result.status == CacheStatus.ERROR


class TestCacheEntry:
    """Test cache entry model."""

    def test_cache_entry_creation(self):
        """Test cache entry creation and properties."""
        entry = CacheEntry(
            key="test_key",
            value="test_value",
            created_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(hours=1),
        )

        assert entry.key == "test_key"
        assert entry.value == "test_value"
        assert not entry.is_expired()

    def test_cache_entry_expiration(self):
        """Test cache entry expiration logic."""
        # Create expired entry
        entry = CacheEntry(
            key="expired_key",
            value="expired_value",
            created_at=datetime.utcnow() - timedelta(hours=2),
            expires_at=datetime.utcnow() - timedelta(hours=1),
        )

        assert entry.is_expired()

    def test_cache_entry_touch(self):
        """Test cache entry access tracking."""
        entry = CacheEntry(key="test", value="test", created_at=datetime.utcnow())

        initial_count = entry.access_count
        initial_time = entry.last_accessed

        time.sleep(0.01)  # Small delay
        entry.touch()

        assert entry.access_count == initial_count + 1
        assert entry.last_accessed > initial_time


class TestCachePerformance:
    """Test cache performance characteristics."""

    @pytest.mark.asyncio
    async def test_cache_response_time_tracking(self, cache_config, mock_redis):
        """Test cache response time measurement."""
        with patch("redis.asyncio.Redis.from_url", return_value=mock_redis):
            cache_manager = CacheManager(cache_config)

            result = await cache_manager.get("test_key")
            assert result.response_time_ms >= 0

    @pytest.mark.asyncio
    async def test_cache_memory_usage_tracking(self, cache_config, mock_redis):
        """Test cache memory usage tracking."""
        mock_redis.info.return_value = {"used_memory": 1024}

        with patch("redis.asyncio.Redis.from_url", return_value=mock_redis):
            cache_manager = CacheManager(cache_config)

            memory_usage = await cache_manager.get_memory_usage()
            assert memory_usage > 0

    @pytest.mark.asyncio
    async def test_cache_throughput_measurement(
        self, cache_config, mock_redis, performance_test_data
    ):
        """Test cache throughput under load."""
        with patch("redis.asyncio.Redis.from_url", return_value=mock_redis):
            cache_manager = CacheManager(cache_config)

            start_time = time.time()

            # Simulate high-throughput operations
            tasks = []
            for key, value in list(performance_test_data.items())[
                :100
            ]:  # Test with 100 items
                tasks.append(cache_manager.set(key, value))

            await asyncio.gather(*tasks)

            end_time = time.time()
            duration = end_time - start_time

            # Should complete within reasonable time
            assert duration < 5.0  # 5 seconds max for 100 operations


# Import asyncio for the performance test
import asyncio
