"""Integration tests for search endpoints."""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch

from knowledge_service.main import app
from knowledge_service.infrastructure.database import get_db
from tests.factories import ResourceFactory, TopicFactory, create_resource_with_topics

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


class TestSearchEndpoints:
    """Test suite for search functionality."""
    
    @patch('knowledge_service.core.vector_search.VectorSearch.search')
    def test_search_resources_success(self, mock_search, db_session):
        """Test successful resource search."""
        ResourceFactory._meta.sqlalchemy_session = db_session
        
        # Create test resources
        resource1 = ResourceFactory(title="Machine Learning Basics")
        resource2 = ResourceFactory(title="Deep Learning Advanced")
        
        # Mock vector search results
        mock_search.return_value = [
            {"id": resource1.id, "score": 0.95},
            {"id": resource2.id, "score": 0.85},
        ]
        
        response = client.post(
            "/api/v1/search",
            json={"query": "machine learning", "limit": 10}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["results"]) == 2
        assert data["results"][0]["title"] == "Machine Learning Basics"
    
    @patch('knowledge_service.core.vector_search.VectorSearch.search')
    def test_search_with_filters(self, mock_search, db_session):
        """Test search with topic filters."""
        ResourceFactory._meta.sqlalchemy_session = db_session
        TopicFactory._meta.sqlalchemy_session = db_session
        
        topic = TopicFactory(name="AI")
        resource = create_resource_with_topics(db_session, topic_count=1)
        resource.topics = [topic]
        db_session.commit()
        
        mock_search.return_value = [{"id": resource.id, "score": 0.9}]
        
        response = client.post(
            "/api/v1/search",
            json={
                "query": "artificial intelligence",
                "filters": {"topics": ["AI"]},
                "limit": 10
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["results"]) >= 0
    
    def test_search_empty_query(self, db_session):
        """Test search with empty query."""
        response = client.post(
            "/api/v1/search",
            json={"query": "", "limit": 10}
        )
        
        assert response.status_code == 422  # Validation error
    
    @patch('knowledge_service.core.vector_search.VectorSearch.search')
    def test_search_no_results(self, mock_search, db_session):
        """Test search with no matching results."""
        mock_search.return_value = []
        
        response = client.post(
            "/api/v1/search",
            json={"query": "nonexistent topic", "limit": 10}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["results"]) == 0
    
    @patch('knowledge_service.core.vector_search.VectorSearch.search')
    def test_search_pagination(self, mock_search, db_session):
        """Test search with pagination."""
        ResourceFactory._meta.sqlalchemy_session = db_session
        
        resources = [ResourceFactory() for _ in range(5)]
        mock_search.return_value = [
            {"id": r.id, "score": 0.9 - i * 0.1}
            for i, r in enumerate(resources)
        ]
        
        response = client.post(
            "/api/v1/search",
            json={"query": "test", "limit": 3, "offset": 0}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["results"]) <= 3
    
    @patch('knowledge_service.core.vector_search.VectorSearch.search')
    def test_search_service_error(self, mock_search, db_session):
        """Test search when vector service fails."""
        mock_search.side_effect = Exception("Vector service unavailable")
        
        response = client.post(
            "/api/v1/search",
            json={"query": "test query", "limit": 10}
        )
        
        assert response.status_code == 503  # Service unavailable
        data = response.json()
        assert "error_code" in data


class TestSimilarResourcesEndpoint:
    """Test suite for similar resources functionality."""
    
    @patch('knowledge_service.core.vector_search.VectorSearch.find_similar')
    def test_find_similar_resources(self, mock_similar, db_session):
        """Test finding similar resources."""
        ResourceFactory._meta.sqlalchemy_session = db_session
        
        base_resource = ResourceFactory(title="Base Resource")
        similar1 = ResourceFactory(title="Similar Resource 1")
        similar2 = ResourceFactory(title="Similar Resource 2")
        
        mock_similar.return_value = [
            {"id": similar1.id, "score": 0.9},
            {"id": similar2.id, "score": 0.8},
        ]
        
        response = client.get(f"/api/v1/resources/{base_resource.id}/similar")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["title"] == "Similar Resource 1"
    
    def test_find_similar_nonexistent_resource(self, db_session):
        """Test finding similar resources for nonexistent resource."""
        response = client.get("/api/v1/resources/99999/similar")
        
        assert response.status_code == 404
        data = response.json()
        assert data["error_code"] == "NOT_FOUND"
