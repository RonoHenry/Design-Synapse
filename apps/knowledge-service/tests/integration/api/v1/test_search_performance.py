"""Performance tests for search functionality."""

import asyncio
import time
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from knowledge_service.infrastructure.database import get_db
from knowledge_service.main import app

from tests.factories import ResourceFactory, TopicFactory

client = TestClient(app)


@pytest.fixture(autouse=True)
def override_dependency(db_session):
    """Override the get_db dependency with our test session."""

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    yield
    app.dependency_overrides.clear()


class TestSearchPerformance:
    """Performance tests for search endpoints."""

    @patch("knowledge_service.core.vector_search.VectorSearch.search")
    def test_search_response_time(self, mock_search, db_session):
        """Test search response time is acceptable."""
        ResourceFactory._meta.sqlalchemy_session = db_session

        # Create test resources
        resources = [ResourceFactory() for _ in range(10)]
        mock_search.return_value = [
            {"id": r.id, "score": 0.9 - i * 0.05} for i, r in enumerate(resources)
        ]

        # Measure response time
        start_time = time.time()
        response = client.post(
            "/api/v1/search", json={"query": "test query", "limit": 10}
        )
        end_time = time.time()

        assert response.status_code == 200
        response_time = end_time - start_time

        # Response should be under 500ms
        assert (
            response_time < 0.5
        ), f"Search took {response_time:.3f}s, should be under 0.5s"

    @patch("knowledge_service.core.vector_search.VectorSearch.search")
    def test_search_with_large_result_set(self, mock_search, db_session):
        """Test search performance with large result sets."""
        ResourceFactory._meta.sqlalchemy_session = db_session

        # Create 100 test resources
        resources = [ResourceFactory() for _ in range(100)]
        mock_search.return_value = [
            {"id": r.id, "score": 0.95 - i * 0.001} for i, r in enumerate(resources)
        ]

        start_time = time.time()
        response = client.post(
            "/api/v1/search", json={"query": "comprehensive search", "limit": 100}
        )
        end_time = time.time()

        assert response.status_code == 200
        data = response.json()
        assert len(data["results"]) == 100

        response_time = end_time - start_time
        # Should handle large result sets efficiently
        assert (
            response_time < 1.0
        ), f"Large result search took {response_time:.3f}s, should be under 1.0s"

    @patch("knowledge_service.core.vector_search.VectorSearch.search")
    def test_concurrent_search_requests(self, mock_search, db_session):
        """Test search performance under concurrent load."""
        ResourceFactory._meta.sqlalchemy_session = db_session

        resources = [ResourceFactory() for _ in range(20)]
        mock_search.return_value = [{"id": r.id, "score": 0.9} for r in resources[:10]]

        def make_search_request():
            """Make a single search request."""
            response = client.post(
                "/api/v1/search", json={"query": "concurrent test", "limit": 10}
            )
            return response.status_code == 200

        # Test 20 concurrent requests
        start_time = time.time()
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(make_search_request) for _ in range(20)]
            results = [f.result() for f in futures]
        end_time = time.time()

        # All requests should succeed
        assert all(results), "Some concurrent requests failed"

        total_time = end_time - start_time
        # Should handle concurrent requests efficiently
        assert (
            total_time < 3.0
        ), f"20 concurrent searches took {total_time:.3f}s, should be under 3.0s"

    @patch("knowledge_service.api.dependencies.get_current_user")
    @patch(
        "knowledge_service.services.project_knowledge.ProjectKnowledgeService.search_global"
    )
    def test_global_search_with_filters_performance(
        self, mock_search, mock_user, db_session
    ):
        """Test global search performance with multiple filters."""
        mock_user.return_value = 1
        mock_search.return_value = {
            "total": 50,
            "page": 1,
            "page_size": 20,
            "results": [
                {"id": i, "title": f"Resource {i}", "relevance_score": 0.9}
                for i in range(20)
            ],
        }

        start_time = time.time()
        response = client.get(
            "/api/v1/search/global",
            params={
                "query": "filtered search",
                "author": "Test Author",
                "date_from": "2023-01-01T00:00:00",
                "date_to": "2023-12-31T23:59:59",
                "min_file_size": 1024,
                "max_file_size": 1048576,
                "has_doi": True,
                "sort_by": "relevance",
                "sort_order": "desc",
            },
        )
        end_time = time.time()

        assert response.status_code == 200
        response_time = end_time - start_time

        # Complex filtered search should still be fast
        assert (
            response_time < 0.8
        ), f"Filtered search took {response_time:.3f}s, should be under 0.8s"

    @patch("knowledge_service.api.dependencies.get_current_user")
    @patch(
        "knowledge_service.services.project_knowledge.ProjectKnowledgeService.search_project_knowledge"
    )
    def test_project_search_performance(self, mock_search, mock_user, db_session):
        """Test project-specific search performance."""
        mock_user.return_value = 1
        mock_search.return_value = {
            "project_resources": [
                {"id": i, "title": f"Project Resource {i}"} for i in range(10)
            ],
            "global_resources": [
                {"id": i + 100, "title": f"Global Resource {i}"} for i in range(10)
            ],
            "total_global": 10,
            "page": 1,
            "page_size": 20,
        }

        start_time = time.time()
        response = client.get(
            "/api/v1/search/project/1",
            params={"query": "project search", "include_global": True},
        )
        end_time = time.time()

        assert response.status_code == 200
        response_time = end_time - start_time

        # Project search with global results should be efficient
        assert (
            response_time < 0.7
        ), f"Project search took {response_time:.3f}s, should be under 0.7s"

    @patch("knowledge_service.core.vector_search.VectorSearch.search")
    def test_pagination_performance(self, mock_search, db_session):
        """Test pagination performance across multiple pages."""
        ResourceFactory._meta.sqlalchemy_session = db_session

        # Create 100 resources
        resources = [ResourceFactory() for _ in range(100)]

        page_times = []

        # Test fetching 5 pages
        for page in range(5):
            offset = page * 20
            mock_search.return_value = [
                {"id": resources[i].id, "score": 0.9}
                for i in range(offset, min(offset + 20, 100))
            ]

            start_time = time.time()
            response = client.post(
                "/api/v1/search",
                json={"query": "pagination test", "limit": 20, "offset": offset},
            )
            end_time = time.time()

            assert response.status_code == 200
            page_times.append(end_time - start_time)

        # All pages should load quickly
        avg_page_time = sum(page_times) / len(page_times)
        assert (
            avg_page_time < 0.5
        ), f"Average page load time {avg_page_time:.3f}s, should be under 0.5s"

        # Page load times should be consistent
        max_variance = max(page_times) - min(page_times)
        assert (
            max_variance < 0.3
        ), f"Page load time variance {max_variance:.3f}s too high"


class TestVectorSearchPerformance:
    """Performance tests for vector search operations."""

    @patch("knowledge_service.core.vector_search.VectorSearch.search")
    def test_vector_search_latency(self, mock_search, db_session):
        """Test vector search latency is acceptable."""
        ResourceFactory._meta.sqlalchemy_session = db_session

        resources = [ResourceFactory() for _ in range(50)]

        # Simulate vector search with realistic delay
        def slow_search(*args, **kwargs):
            time.sleep(0.05)  # Simulate 50ms vector search
            return [{"id": r.id, "score": 0.9} for r in resources[:10]]

        mock_search.side_effect = slow_search

        start_time = time.time()
        response = client.post(
            "/api/v1/search", json={"query": "vector search test", "limit": 10}
        )
        end_time = time.time()

        assert response.status_code == 200
        total_time = end_time - start_time

        # Total time should include vector search + processing
        assert (
            total_time < 0.3
        ), f"Search with vector latency took {total_time:.3f}s, should be under 0.3s"

    @patch("knowledge_service.core.vector_search.VectorSearch.find_similar")
    def test_similar_resources_performance(self, mock_similar, db_session):
        """Test similar resources search performance."""
        ResourceFactory._meta.sqlalchemy_session = db_session

        base_resource = ResourceFactory()
        similar_resources = [ResourceFactory() for _ in range(20)]

        mock_similar.return_value = [
            {"id": r.id, "score": 0.85} for r in similar_resources
        ]

        start_time = time.time()
        response = client.get(f"/api/v1/resources/{base_resource.id}/similar")
        end_time = time.time()

        assert response.status_code == 200
        response_time = end_time - start_time

        # Similar resources search should be fast
        assert (
            response_time < 0.6
        ), f"Similar search took {response_time:.3f}s, should be under 0.6s"


class TestSearchScalability:
    """Test search scalability with increasing data volumes."""

    @patch("knowledge_service.core.vector_search.VectorSearch.search")
    def test_search_scales_with_database_size(self, mock_search, db_session):
        """Test search performance doesn't degrade significantly with more data."""
        ResourceFactory._meta.sqlalchemy_session = db_session

        # Test with different database sizes
        sizes = [10, 50, 100]
        response_times = []

        for size in sizes:
            # Create resources
            resources = [ResourceFactory() for _ in range(size)]

            mock_search.return_value = [
                {"id": r.id, "score": 0.9} for r in resources[:10]
            ]

            start_time = time.time()
            response = client.post(
                "/api/v1/search", json={"query": "scalability test", "limit": 10}
            )
            end_time = time.time()

            assert response.status_code == 200
            response_times.append(end_time - start_time)

            # Clean up for next iteration
            db_session.query(type(resources[0])).delete()
            db_session.commit()

        # Response time should not increase dramatically
        # Allow 2x increase from smallest to largest
        assert (
            response_times[-1] < response_times[0] * 2
        ), f"Search time increased too much: {response_times[0]:.3f}s -> {response_times[-1]:.3f}s"

    @patch("knowledge_service.api.dependencies.get_current_user")
    @patch(
        "knowledge_service.services.project_knowledge.ProjectKnowledgeService.get_recommendations"
    )
    def test_recommendations_performance_at_scale(
        self, mock_recommendations, mock_user, db_session
    ):
        """Test recommendations performance with large datasets."""
        mock_user.return_value = 1

        # Simulate large recommendation set
        mock_recommendations.return_value = {
            "total": 500,
            "page": 1,
            "page_size": 20,
            "results": [
                {"id": i, "title": f"Recommendation {i}", "relevance_score": 0.8}
                for i in range(20)
            ],
        }

        start_time = time.time()
        response = client.get(
            "/api/v1/search/project/1/recommendations",
            params={"page": 1, "page_size": 20},
        )
        end_time = time.time()

        assert response.status_code == 200
        response_time = end_time - start_time

        # Recommendations should be fast even with large datasets
        assert (
            response_time < 0.8
        ), f"Recommendations took {response_time:.3f}s, should be under 0.8s"


class TestSearchMemoryUsage:
    """Test search memory efficiency."""

    @patch("knowledge_service.core.vector_search.VectorSearch.search")
    def test_memory_efficient_large_queries(self, mock_search, db_session):
        """Test that large queries don't cause memory issues."""
        import gc

        ResourceFactory._meta.sqlalchemy_session = db_session

        # Create resources
        resources = [ResourceFactory() for _ in range(100)]
        mock_search.return_value = [{"id": r.id, "score": 0.9} for r in resources]

        # Get initial memory state
        gc.collect()
        initial_objects = len(gc.get_objects())

        # Make multiple large queries
        for _ in range(10):
            response = client.post(
                "/api/v1/search", json={"query": "memory test", "limit": 100}
            )
            assert response.status_code == 200

        # Check memory hasn't grown significantly
        gc.collect()
        final_objects = len(gc.get_objects())
        object_growth = final_objects - initial_objects

        # Allow some growth but not unbounded
        assert (
            object_growth < 1000
        ), f"Memory grew by {object_growth} objects, should be under 1000"
