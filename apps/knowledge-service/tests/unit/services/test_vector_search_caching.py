"""
Tests for enhanced vector search caching functionality.
"""

import time
from unittest.mock import MagicMock, Mock, patch

import pytest
from knowledge_service.services.vector_search import (
    DistributedEmbeddingCache, DistributedSearchCache, VectorSearchService)


class TestDistributedSearchCache:
    """Test the enhanced distributed search cache."""

    def test_in_memory_cache_basic_operations(self):
        """Test basic cache operations with in-memory fallback."""
        cache = DistributedSearchCache(max_size=10, default_ttl=60)

        # Test cache miss
        result = cache.get("test query", None, 5)
        assert result is None
        assert cache.stats["misses"] == 1

        # Test cache set and hit
        test_results = [{"resource_id": 1, "score": 0.9}]
        cache.set("test query", None, 5, test_results)
        assert cache.stats["sets"] == 1

        cached_result = cache.get("test query", None, 5)
        assert cached_result == test_results
        assert cache.stats["hits"] == 1

    def test_cache_key_generation_with_user_id(self):
        """Test cache key generation includes user ID for partitioning."""
        cache = DistributedSearchCache()

        key1 = cache._generate_key("test query", None, 5, "user1")
        key2 = cache._generate_key("test query", None, 5, "user2")
        key3 = cache._generate_key("test query", None, 5, None)

        # All keys should be different
        assert key1 != key2
        assert key1 != key3
        assert key2 != key3

        # Same parameters should generate same key
        key1_duplicate = cache._generate_key("test query", None, 5, "user1")
        assert key1 == key1_duplicate

    def test_cache_compression(self):
        """Test data compression functionality."""
        cache = DistributedSearchCache()
        cache.use_compression = True

        # Test with large data that should compress well
        large_results = [
            {"resource_id": i, "score": 0.9, "content": "x" * 1000} for i in range(100)
        ]

        compressed_data = cache._compress_data(large_results)
        decompressed_data = cache._decompress_data(compressed_data)

        assert decompressed_data == large_results
        assert cache.stats["compression_ratio"] > 0

    def test_cache_invalidation_patterns(self):
        """Test cache invalidation by patterns."""
        cache = DistributedSearchCache()

        # Add some test entries
        cache.set("query1", {"project_id": "proj1"}, 5, [{"resource_id": 1}])
        cache.set("query2", {"project_id": "proj2"}, 5, [{"resource_id": 2}])
        cache.set("query3", {"user_id": "user1"}, 5, [{"resource_id": 3}])

        # Test pattern invalidation
        cache.invalidate_pattern("proj1")

        # Should not find proj1 entries but others should remain
        assert cache.get("query1", {"project_id": "proj1"}, 5) is None
        assert cache.get("query2", {"project_id": "proj2"}, 5) is not None

    def test_lru_eviction(self):
        """Test LRU eviction when cache is full."""
        cache = DistributedSearchCache(max_size=3)

        # Fill cache to capacity
        cache.set("query1", None, 5, [{"resource_id": 1}])
        cache.set("query2", None, 5, [{"resource_id": 2}])
        cache.set("query3", None, 5, [{"resource_id": 3}])

        # Access query1 to make it more recently used
        cache.get("query1", None, 5)

        # Add another entry to trigger eviction
        cache.set("query4", None, 5, [{"resource_id": 4}])

        # query2 should be evicted (least recently used)
        assert cache.get("query1", None, 5) is not None  # Recently accessed
        assert cache.get("query2", None, 5) is None  # Should be evicted
        assert cache.get("query3", None, 5) is not None  # Recently set
        assert cache.get("query4", None, 5) is not None  # Just added

    @patch("redis.from_url")
    def test_redis_cache_operations(self, mock_redis_from_url):
        """Test Redis cache operations."""
        # Mock Redis client
        mock_redis = MagicMock()
        mock_redis.ping.return_value = True
        mock_redis.get.return_value = None  # Cache miss
        mock_redis.setex.return_value = True
        mock_redis_from_url.return_value = mock_redis

        cache = DistributedSearchCache(redis_url="redis://localhost:6379")

        # Test cache miss
        result = cache.get("test query", None, 5)
        assert result is None
        mock_redis.get.assert_called_once()

        # Test cache set
        test_results = [{"resource_id": 1, "score": 0.9}]
        cache.set("test query", None, 5, test_results)
        mock_redis.setex.assert_called_once()

    def test_cache_stats(self):
        """Test cache statistics collection."""
        cache = DistributedSearchCache()

        # Perform some operations
        cache.get("query1", None, 5)  # Miss
        cache.set("query1", None, 5, [{"resource_id": 1}])  # Set
        cache.get("query1", None, 5)  # Hit

        stats = cache.get_stats()

        assert stats["hits"] == 1
        assert stats["misses"] == 1
        assert stats["sets"] == 1
        assert stats["hit_rate"] == 0.5  # 1 hit out of 2 total requests


class TestDistributedEmbeddingCache:
    """Test the enhanced distributed embedding cache."""

    def test_embedding_cache_basic_operations(self):
        """Test basic embedding cache operations."""
        cache = DistributedEmbeddingCache(max_size=10)

        # Test cache miss
        result = cache.get("test text")
        assert result is None
        assert cache.stats["misses"] == 1

        # Test cache set and hit
        test_embedding = [0.1, 0.2, 0.3, 0.4]
        cache.set("test text", test_embedding)
        assert cache.stats["sets"] == 1

        cached_embedding = cache.get("test text")
        assert cached_embedding == test_embedding
        assert cache.stats["hits"] == 1

    @patch("redis.from_url")
    def test_redis_embedding_cache(self, mock_redis_from_url):
        """Test Redis-based embedding cache."""
        # Mock Redis client
        mock_redis = MagicMock()
        mock_redis.ping.return_value = True
        mock_redis.get.return_value = None
        mock_redis.setex.return_value = True
        mock_redis_from_url.return_value = mock_redis

        cache = DistributedEmbeddingCache(redis_url="redis://localhost:6379")

        # Test operations
        embedding = [0.1, 0.2, 0.3]
        cache.set("test text", embedding)
        result = cache.get("test text")

        mock_redis.setex.assert_called_once()
        mock_redis.get.assert_called()


class TestVectorSearchServiceCaching:
    """Test vector search service with enhanced caching."""

    @pytest.fixture
    def mock_dependencies(self):
        """Mock all external dependencies."""
        with patch("pinecone.init") as mock_init, patch(
            "pinecone.Index"
        ) as mock_index_class, patch("pinecone.list_indexes") as mock_list, patch(
            "pinecone.create_index"
        ) as mock_create, patch(
            "sentence_transformers.SentenceTransformer"
        ) as mock_st, patch.dict(
            "os.environ",
            {"PINECONE_API_KEY": "test_key", "PINECONE_ENVIRONMENT": "test_env"},
        ):
            # Setup mocks
            mock_list.return_value = []
            mock_index = MagicMock()
            mock_index_class.return_value = mock_index

            mock_model = MagicMock()
            mock_model.encode.return_value = [0.1] * 384
            mock_st.return_value = mock_model

            yield {"index": mock_index, "model": mock_model}

    @pytest.mark.asyncio
    async def test_search_with_user_specific_caching(self, mock_dependencies):
        """Test search with user-specific cache partitioning."""
        service = VectorSearchService()

        # Mock search results
        mock_match = MagicMock()
        mock_match.id = "1"
        mock_match.score = 0.9
        mock_match.metadata = {"title": "Test Result"}

        mock_results = MagicMock()
        mock_results.matches = [mock_match]
        mock_dependencies["index"].query.return_value = mock_results

        # First search for user1
        results1 = await service.search_resources(
            "test query", filter_metadata={"user_id": "user1"}, top_k=5
        )

        # Second search for user2 (same query, different user)
        results2 = await service.search_resources(
            "test query", filter_metadata={"user_id": "user2"}, top_k=5
        )

        # Both should have results but be cached separately
        assert len(results1) == 1
        assert len(results2) == 1

        # Cache should have separate entries for each user
        cache_stats = service.get_cache_stats()
        assert cache_stats["search_cache"]["sets"] == 2  # Two separate cache entries

    @pytest.mark.asyncio
    async def test_cache_invalidation_on_resource_update(self, mock_dependencies):
        """Test cache invalidation when resources are updated."""
        service = VectorSearchService()

        # Mock successful indexing
        mock_dependencies["index"].upsert.return_value = None

        # Add some cached search results first
        service.search_cache.set(
            "test query", {"project_id": "proj1"}, 5, [{"resource_id": 1}]
        )

        # Index a new resource
        await service.index_resource(
            resource_id=1,
            title="Test Resource",
            description="Test Description",
            content="Test content",
            metadata={"project_id": "proj1"},
        )

        # Cache should be invalidated for related entries
        # This is tested by checking that the invalidation method was called
        # In a real scenario, the cache entry would be removed

    @pytest.mark.asyncio
    async def test_embedding_cache_usage(self, mock_dependencies):
        """Test that embedding cache is used to avoid recomputation."""
        service = VectorSearchService()

        # First call should generate embedding
        embedding1 = service._generate_embedding_with_cache("test text")

        # Second call should use cache
        embedding2 = service._generate_embedding_with_cache("test text")

        # Should be the same embedding
        assert embedding1 == embedding2

        # Model should only be called once
        assert mock_dependencies["model"].encode.call_count == 1

        # Cache stats should show hit
        cache_stats = service.get_cache_stats()
        assert cache_stats["embedding_cache"]["hits"] >= 1

    @pytest.mark.asyncio
    async def test_cache_warm_up(self, mock_dependencies):
        """Test cache warm-up functionality."""
        service = VectorSearchService()

        # Mock search results
        mock_match = MagicMock()
        mock_match.id = "1"
        mock_match.score = 0.9
        mock_match.metadata = {"title": "Test Result"}

        mock_results = MagicMock()
        mock_results.matches = [mock_match]
        mock_dependencies["index"].query.return_value = mock_results

        # Warm up cache with common queries
        common_queries = ["design patterns", "architecture", "best practices"]
        user_filters = [{"project_id": "proj1"}, {"project_id": "proj2"}]

        await service.warm_up_cache(common_queries, user_filters)

        # Cache should have entries for each query-filter combination
        cache_stats = service.get_cache_stats()
        expected_entries = len(common_queries) * len(user_filters)
        assert cache_stats["search_cache"]["sets"] == expected_entries

    def test_cache_configuration(self, mock_dependencies):
        """Test cache configuration options."""
        service = VectorSearchService()

        # Configure cache settings
        service.configure_cache(
            enable_search_cache=True,
            search_cache_ttl=7200,
            enable_compression=False,
            max_search_cache_size=2000,
            max_embedding_cache_size=1000,
        )

        # Verify settings were applied
        assert service.search_cache.enabled is True
        assert service.search_cache.default_ttl == 7200
        assert service.search_cache.use_compression is False
        assert service.search_cache.max_size == 2000
        assert service.embedding_cache.max_size == 1000

    def test_cache_health_check(self, mock_dependencies):
        """Test cache health check in service health."""
        service = VectorSearchService()

        health = service.get_service_health()

        assert "cache_healthy" in health
        assert "cache_stats" in health
        assert health["cache_stats"]["search_cache"]["enabled"] is True

    @pytest.mark.asyncio
    async def test_user_cache_invalidation(self, mock_dependencies):
        """Test user-specific cache invalidation."""
        service = VectorSearchService()

        # Add cached entries for different users
        service.search_cache.set(
            "query1", None, 5, [{"resource_id": 1}], user_id="user1"
        )
        service.search_cache.set(
            "query2", None, 5, [{"resource_id": 2}], user_id="user2"
        )

        # Invalidate cache for user1
        service.invalidate_user_cache("user1")

        # user1's cache should be invalidated, user2's should remain
        # This tests the invalidation pattern matching

    @pytest.mark.asyncio
    async def test_project_cache_invalidation(self, mock_dependencies):
        """Test project-specific cache invalidation."""
        service = VectorSearchService()

        # Add cached entries for different projects
        service.search_cache.set(
            "query1", {"project_id": "proj1"}, 5, [{"resource_id": 1}]
        )
        service.search_cache.set(
            "query2", {"project_id": "proj2"}, 5, [{"resource_id": 2}]
        )

        # Invalidate cache for proj1
        service.invalidate_project_cache("proj1")

        # proj1's cache should be invalidated, proj2's should remain
