#!/usr/bin/env python3
"""Demo script for testing the recommendation system."""

import asyncio
import os
import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from knowledge_service.core.database import get_db
from knowledge_service.models.bookmark import Bookmark
from knowledge_service.models.resource import Resource
from knowledge_service.services.factory import ServiceFactory
from knowledge_service.services.recommendation import RecommendationType


async def demo_recommendations():
    """Demonstrate the recommendation system functionality."""
    print("🤖 Knowledge Service Recommendation System Demo")
    print("=" * 50)

    try:
        # Initialize service factory
        service_factory = ServiceFactory()
        recommendation_service = await service_factory.get_recommendation_service()

        print("✅ Recommendation service initialized successfully")

        # Get cache stats
        print("\n📊 Cache Statistics:")
        stats = recommendation_service.get_cache_stats()
        for key, value in stats.items():
            print(f"  {key}: {value}")

        # Test different recommendation types
        print("\n🎯 Testing Recommendation Types:")

        # Simulate a user ID (in real scenario, this would come from authentication)
        test_user_id = 1

        # Get database session
        db = next(get_db())

        try:
            # Test content-based recommendations
            print("\n1. Content-Based Recommendations:")
            content_recs = await recommendation_service.get_recommendations(
                user_id=test_user_id,
                db=db,
                num_recommendations=5,
                recommendation_types=[RecommendationType.CONTENT_BASED],
            )

            if content_recs:
                for i, rec in enumerate(content_recs, 1):
                    print(f"  {i}. Resource {rec.resource_id} (Score: {rec.score:.3f})")
                    print(f"     {rec.explanation}")
            else:
                print("  No content-based recommendations available")

            # Test collaborative filtering
            print("\n2. Collaborative Filtering Recommendations:")
            collab_recs = await recommendation_service.get_recommendations(
                user_id=test_user_id,
                db=db,
                num_recommendations=5,
                recommendation_types=[RecommendationType.COLLABORATIVE],
            )

            if collab_recs:
                for i, rec in enumerate(collab_recs, 1):
                    print(f"  {i}. Resource {rec.resource_id} (Score: {rec.score:.3f})")
                    print(f"     {rec.explanation}")
            else:
                print("  No collaborative recommendations available")

            # Test trending recommendations
            print("\n3. Trending Recommendations:")
            trending_recs = await recommendation_service.get_recommendations(
                user_id=test_user_id,
                db=db,
                num_recommendations=5,
                recommendation_types=[RecommendationType.TRENDING],
            )

            if trending_recs:
                for i, rec in enumerate(trending_recs, 1):
                    print(f"  {i}. Resource {rec.resource_id} (Score: {rec.score:.3f})")
                    print(f"     {rec.explanation}")
            else:
                print("  No trending recommendations available")

            # Test hybrid recommendations (all types combined)
            print("\n4. Hybrid Recommendations (All Types):")
            hybrid_recs = await recommendation_service.get_recommendations(
                user_id=test_user_id, db=db, num_recommendations=10
            )

            if hybrid_recs:
                for i, rec in enumerate(hybrid_recs, 1):
                    print(
                        f"  {i}. Resource {rec.resource_id} (Score: {rec.score:.3f}) [{rec.recommendation_type.value}]"
                    )
                    print(f"     {rec.explanation}")
            else:
                print("  No hybrid recommendations available")

            # Test contextual recommendations
            print("\n5. Contextual Recommendations (Search Context):")
            context = {"search_query": "machine learning algorithms"}
            contextual_recs = await recommendation_service.get_recommendations(
                user_id=test_user_id,
                db=db,
                num_recommendations=5,
                recommendation_types=[RecommendationType.CONTEXTUAL],
                context=context,
            )

            if contextual_recs:
                for i, rec in enumerate(contextual_recs, 1):
                    print(f"  {i}. Resource {rec.resource_id} (Score: {rec.score:.3f})")
                    print(f"     {rec.explanation}")
            else:
                print("  No contextual recommendations available")

            # Test similar resources (if we have any resources)
            print("\n6. Similar Resources:")
            # Try to find a resource to use as reference
            sample_resource = db.query(Resource).first()
            if sample_resource:
                similar_recs = await recommendation_service.get_similar_resources(
                    resource_id=sample_resource.id, db=db, num_similar=5
                )

                if similar_recs:
                    print(
                        f"  Similar to Resource {sample_resource.id} ('{sample_resource.title}'):"
                    )
                    for i, rec in enumerate(similar_recs, 1):
                        print(
                            f"    {i}. Resource {rec.resource_id} (Score: {rec.score:.3f})"
                        )
                        print(f"       {rec.explanation}")
                else:
                    print(
                        f"  No similar resources found for Resource {sample_resource.id}"
                    )
            else:
                print("  No resources available for similarity testing")

            # Test recommendation explanation
            if hybrid_recs:
                print("\n7. Recommendation Explanation:")
                first_rec = hybrid_recs[0]
                explanation = await recommendation_service.explain_recommendation(
                    user_id=test_user_id, resource_id=first_rec.resource_id, db=db
                )

                if "error" not in explanation:
                    print(f"  Resource: {explanation['resource_title']}")
                    print(
                        f"  Recommendation Strength: {explanation['recommendation_strength']}"
                    )
                    print("  Matching Factors:")
                    for factor in explanation["matching_factors"]:
                        print(
                            f"    - {factor['factor']}: {factor.get('matches', 'N/A')}"
                        )
                else:
                    print(f"  Error: {explanation['error']}")

            # Test weight updates
            print("\n8. Testing Weight Updates:")
            original_weights = recommendation_service.weights.copy()
            print(f"  Original weights: {original_weights}")

            # Update weights
            new_weights = {
                RecommendationType.CONTENT_BASED: 0.5,
                RecommendationType.COLLABORATIVE: 0.2,
                RecommendationType.TRENDING: 0.1,
                RecommendationType.CONTEXTUAL: 0.2,
            }

            try:
                recommendation_service.update_weights(new_weights)
                print(f"  Updated weights: {recommendation_service.weights}")

                # Restore original weights
                recommendation_service.update_weights(original_weights)
                print(f"  Restored weights: {recommendation_service.weights}")
            except ValueError as e:
                print(f"  Weight update error: {e}")

            # Test cache operations
            print("\n9. Cache Operations:")
            print("  Clearing recommendation cache...")
            recommendation_service.clear_cache()

            final_stats = recommendation_service.get_cache_stats()
            print(f"  Cache stats after clearing: {final_stats}")

        finally:
            db.close()

        print("\n✅ Recommendation system demo completed successfully!")

    except Exception as e:
        print(f"\n❌ Demo failed with error: {e}")
        import traceback

        traceback.print_exc()


async def test_recommendation_performance():
    """Test recommendation system performance."""
    print("\n🚀 Performance Testing:")
    print("-" * 30)

    import time

    try:
        service_factory = ServiceFactory()
        recommendation_service = await service_factory.get_recommendation_service()
        db = next(get_db())

        try:
            test_user_id = 1
            num_tests = 5

            print(f"Running {num_tests} recommendation requests...")

            start_time = time.time()

            for i in range(num_tests):
                recommendations = await recommendation_service.get_recommendations(
                    user_id=test_user_id, db=db, num_recommendations=10
                )
                print(f"  Test {i+1}: {len(recommendations)} recommendations")

            end_time = time.time()
            total_time = end_time - start_time
            avg_time = total_time / num_tests

            print(f"\nPerformance Results:")
            print(f"  Total time: {total_time:.3f} seconds")
            print(f"  Average time per request: {avg_time:.3f} seconds")
            print(f"  Requests per second: {1/avg_time:.2f}")

        finally:
            db.close()

    except Exception as e:
        print(f"Performance test failed: {e}")


if __name__ == "__main__":
    print("Starting Knowledge Service Recommendation Demo...")

    # Run the main demo
    asyncio.run(demo_recommendations())

    # Run performance test
    asyncio.run(test_recommendation_performance())

    print("\nDemo completed! 🎉")
