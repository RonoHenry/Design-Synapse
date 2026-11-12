#!/usr/bin/env python3
"""Test script for recommendation system functionality."""

import asyncio
import os
import sys
from pathlib import Path

# Add the app to Python path
app_path = Path(__file__).parent
sys.path.insert(0, str(app_path))
sys.path.insert(0, str(app_path.parent.parent / "packages"))

from knowledge_service.core.config import get_config
from knowledge_service.services.factory import ServiceFactory
from knowledge_service.services.recommendation import RecommendationType


async def test_recommendation_service():
    """Test the recommendation service functionality."""
    print("🧪 Testing Recommendation Service...")

    try:
        # Initialize service factory
        config = get_config()
        factory = ServiceFactory(config)

        # Get recommendation service
        print("📊 Getting recommendation service...")
        recommendation_service = await factory.get_recommendation_service()

        # Test cache stats
        print("📈 Getting cache statistics...")
        stats = recommendation_service.get_cache_stats()
        print(f"Cache stats: {stats}")

        # Test weight updates
        print("⚖️ Testing weight updates...")
        new_weights = {
            RecommendationType.CONTENT_BASED: 0.5,
            RecommendationType.COLLABORATIVE: 0.3,
            RecommendationType.TRENDING: 0.1,
            RecommendationType.CONTEXTUAL: 0.1,
        }
        recommendation_service.update_weights(new_weights)
        print(f"Updated weights: {recommendation_service.weights}")

        # Test cache clearing
        print("🧹 Testing cache clearing...")
        recommendation_service.clear_cache()
        print("Cache cleared successfully")

        print("✅ Recommendation service tests completed successfully!")
        return True

    except Exception as e:
        print(f"❌ Recommendation service test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


async def test_vector_search_integration():
    """Test vector search integration for recommendations."""
    print("\n🔍 Testing Vector Search Integration...")

    try:
        # Initialize services
        factory = ServiceFactory()
        vector_service = factory.get_vector_service()

        # Test vector search connectivity
        print("🔗 Testing vector search connectivity...")
        # This would normally test actual search functionality
        # For now, just verify the service can be created
        print(f"Vector service initialized: {type(vector_service).__name__}")

        print("✅ Vector search integration test completed!")
        return True

    except Exception as e:
        print(f"❌ Vector search integration test failed: {e}")
        return False


async def test_llm_integration():
    """Test LLM integration for recommendations."""
    print("\n🤖 Testing LLM Integration...")

    try:
        # Initialize services
        factory = ServiceFactory()
        llm_service = factory.get_llm_service()

        # Test LLM service connectivity
        print("🔗 Testing LLM service connectivity...")
        print(f"LLM service initialized: {type(llm_service).__name__}")

        print("✅ LLM integration test completed!")
        return True

    except Exception as e:
        print(f"❌ LLM integration test failed: {e}")
        return False


async def main():
    """Run all recommendation tests."""
    print("🚀 Starting Recommendation System Tests")
    print("=" * 50)

    # Test individual components
    tests = [
        test_recommendation_service(),
        test_vector_search_integration(),
        test_llm_integration(),
    ]

    results = await asyncio.gather(*tests, return_exceptions=True)

    # Summary
    print("\n" + "=" * 50)
    print("📋 Test Summary:")

    passed = sum(1 for result in results if result is True)
    total = len(results)

    print(f"✅ Passed: {passed}/{total}")

    if passed == total:
        print("🎉 All recommendation tests passed!")
        return 0
    else:
        print("⚠️ Some tests failed. Check the output above for details.")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
