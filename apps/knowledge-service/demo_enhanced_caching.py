#!/usr/bin/env python3
"""
Demonstration of enhanced vector search caching capabilities.
This script shows the new caching features without requiring full service setup.
"""

import json
import os
import sys
import time
from typing import Dict, List, Optional

# Add the knowledge service to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from knowledge_service.services.vector_search import (
    DistributedEmbeddingCache, DistributedSearchCache)


def demo_search_cache():
    """Demonstrate enhanced search cache functionality."""
    print("=== Enhanced Search Cache Demo ===")

    # Initialize cache (will use in-memory since Redis not configured)
    cache = DistributedSearchCache(max_size=100, default_ttl=300)

    print(f"Cache type: {cache.get_stats()['type']}")
    print(f"Compression enabled: {cache.use_compression}")

    # Demo 1: Basic caching
    print("\n1. Basic Cache Operations:")

    # Cache miss
    result = cache.get("machine learning", None, 10)
    print(f"Cache miss result: {result}")

    # Cache set
    sample_results = [
        {"resource_id": 1, "score": 0.95, "metadata": {"title": "ML Fundamentals"}},
        {"resource_id": 2, "score": 0.87, "metadata": {"title": "Deep Learning Guide"}},
        {"resource_id": 3, "score": 0.82, "metadata": {"title": "Neural Networks"}},
    ]

    cache.set("machine learning", None, 10, sample_results)
    print("Cached search results for 'machine learning'")

    # Cache hit
    cached_result = cache.get("machine learning", None, 10)
    print(f"Cache hit - found {len(cached_result)} results")

    # Demo 2: User-specific caching
    print("\n2. User-Specific Cache Partitioning:")

    # Same query, different users
    cache.set(
        "python tutorial",
        {"project_id": "proj1"},
        5,
        sample_results[:2],
        user_id="user1",
    )
    cache.set(
        "python tutorial",
        {"project_id": "proj2"},
        5,
        sample_results[1:],
        user_id="user2",
    )

    user1_results = cache.get(
        "python tutorial", {"project_id": "proj1"}, 5, user_id="user1"
    )
    user2_results = cache.get(
        "python tutorial", {"project_id": "proj2"}, 5, user_id="user2"
    )

    print(f"User1 results: {len(user1_results)} items")
    print(f"User2 results: {len(user2_results)} items")

    # Demo 3: Cache invalidation
    print("\n3. Cache Invalidation:")

    # Add entries for different projects
    cache.set("design patterns", {"project_id": "proj1"}, 10, sample_results)
    cache.set("architecture", {"project_id": "proj1"}, 10, sample_results)
    cache.set("testing", {"project_id": "proj2"}, 10, sample_results)

    print("Added cache entries for proj1 and proj2")

    # Invalidate proj1 entries
    cache.invalidate_pattern("proj1")
    print("Invalidated proj1 cache entries")

    # Check what remains
    proj1_result = cache.get("design patterns", {"project_id": "proj1"}, 10)
    proj2_result = cache.get("testing", {"project_id": "proj2"}, 10)

    print(f"Proj1 cache after invalidation: {proj1_result is not None}")
    print(f"Proj2 cache after invalidation: {proj2_result is not None}")

    # Demo 4: Cache statistics
    print("\n4. Cache Statistics:")
    stats = cache.get_stats()
    print(json.dumps(stats, indent=2))


def demo_embedding_cache():
    """Demonstrate enhanced embedding cache functionality."""
    print("\n=== Enhanced Embedding Cache Demo ===")

    # Initialize embedding cache
    cache = DistributedEmbeddingCache(max_size=50)

    print(f"Cache type: {cache.get_stats()['type']}")

    # Demo 1: Basic embedding caching
    print("\n1. Basic Embedding Cache:")

    # Simulate embeddings
    sample_embeddings = {
        "machine learning": [0.1, 0.2, 0.3, 0.4, 0.5],
        "deep learning": [0.2, 0.3, 0.4, 0.5, 0.6],
        "neural networks": [0.3, 0.4, 0.5, 0.6, 0.7],
    }

    # Cache embeddings
    for text, embedding in sample_embeddings.items():
        cache.set(text, embedding)
        print(f"Cached embedding for: {text}")

    # Retrieve embeddings
    for text in sample_embeddings.keys():
        cached_embedding = cache.get(text)
        print(f"Retrieved embedding for '{text}': {cached_embedding is not None}")

    # Demo 2: Cache statistics
    print("\n2. Embedding Cache Statistics:")
    stats = cache.get_stats()
    print(json.dumps(stats, indent=2))


def demo_compression():
    """Demonstrate cache compression functionality."""
    print("\n=== Cache Compression Demo ===")

    # Create large sample data
    large_results = []
    for i in range(100):
        large_results.append(
            {
                "resource_id": i,
                "score": 0.9 - (i * 0.001),
                "metadata": {
                    "title": f"Resource {i}",
                    "description": "This is a long description that repeats many times. "
                    * 20,
                    "content": "Sample content that is repeated across many resources. "
                    * 50,
                    "tags": ["tag1", "tag2", "tag3", "tag4", "tag5"],
                },
            }
        )

    # Test with compression enabled
    cache_compressed = DistributedSearchCache()
    cache_compressed.use_compression = True

    # Test with compression disabled
    cache_uncompressed = DistributedSearchCache()
    cache_uncompressed.use_compression = False

    # Compress and measure
    compressed_data = cache_compressed._compress_data(large_results)
    uncompressed_data = cache_uncompressed._compress_data(large_results)

    print(f"Original data size: {len(str(large_results))} characters")
    print(f"Compressed data size: {len(compressed_data)} bytes")
    print(f"Uncompressed data size: {len(uncompressed_data)} bytes")
    print(f"Compression ratio: {len(compressed_data) / len(uncompressed_data):.2f}")

    # Verify decompression works
    decompressed_data = cache_compressed._decompress_data(compressed_data)
    print(f"Decompression successful: {decompressed_data == large_results}")


def demo_performance():
    """Demonstrate cache performance improvements."""
    print("\n=== Cache Performance Demo ===")

    cache = DistributedSearchCache(max_size=1000)

    # Generate test data
    test_queries = [f"query {i}" for i in range(100)]
    test_results = [{"resource_id": i, "score": 0.9} for i in range(10)]

    # Measure cache set performance
    start_time = time.time()
    for query in test_queries:
        cache.set(query, None, 10, test_results)
    set_time = time.time() - start_time

    # Measure cache get performance (hits)
    start_time = time.time()
    for query in test_queries:
        cache.get(query, None, 10)
    get_time = time.time() - start_time

    print(f"Cache set time for {len(test_queries)} queries: {set_time:.4f}s")
    print(f"Cache get time for {len(test_queries)} queries: {get_time:.4f}s")
    print(f"Average set time per query: {set_time/len(test_queries)*1000:.2f}ms")
    print(f"Average get time per query: {get_time/len(test_queries)*1000:.2f}ms")

    # Show final statistics
    stats = cache.get_stats()
    print(f"Final cache hit rate: {stats['hit_rate']:.2f}")


if __name__ == "__main__":
    print("Enhanced Vector Search Caching Demo")
    print("=" * 50)

    try:
        demo_search_cache()
        demo_embedding_cache()
        demo_compression()
        demo_performance()

        print("\n" + "=" * 50)
        print("Demo completed successfully!")
        print("\nKey improvements implemented:")
        print("✓ Redis-based distributed caching with in-memory fallback")
        print("✓ User and project-specific cache partitioning")
        print("✓ Cache compression for large result sets")
        print("✓ Pattern-based cache invalidation")
        print("✓ Comprehensive cache statistics and monitoring")
        print("✓ LRU eviction with performance metrics")
        print("✓ Separate caching for search results and embeddings")

    except Exception as e:
        print(f"Demo failed with error: {e}")
        import traceback

        traceback.print_exc()
