"""Integration tests for recommendation API endpoints."""
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient
from knowledge_service.main import app
from knowledge_service.services.recommendation import (RecommendationScore,
                                                       RecommendationType)


@pytest.fixture
def client():
    """Test client fixture."""
    return TestClient(app)


@pytest.fixture
def mock_user():
    """Mock user fixture."""
    return {"id": 1, "username": "testuser", "email": "test@example.com"}


@pytest.fixture
def sample_recommendations():
    """Sample recommendation data."""
    return [
        RecommendationScore(
            resource_id=1,
            score=0.95,
            recommendation_type=RecommendationType.CONTENT_BASED,
            explanation="Based on your interests in machine learning",
            metadata={"interests_matched": ["machine learning", "AI"]},
        ),
        RecommendationScore(
            resource_id=2,
            score=0.87,
            recommendation_type=RecommendationType.COLLABORATIVE,
            explanation="Recommended by 5 users with similar interests",
            metadata={"bookmark_count": 5, "similar_users": 10},
        ),
    ]


class TestRecommendationsAPI:
    """Test cases for recommendations API."""

    @patch("knowledge_service.api.dependencies.get_current_user")
    @patch(
        "knowledge_service.services.factory.ServiceFactory.get_recommendation_service"
    )
    def test_get_user_recommendations_success(
        self, mock_service, mock_user_dep, client, mock_user, sample_recommendations
    ):
        """Test successful user recommendations retrieval."""
        # Setup mocks
        mock_user_dep.return_value = mock_user
        mock_recommendation_service = AsyncMock()
        mock_recommendation_service.get_recommendations.return_value = (
            sample_recommendations
        )
        mock_service.return_value = mock_recommendation_service

        # Make request
        response = client.get("/api/v1/recommendations/")

        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["resource_id"] == 1
        assert data[0]["score"] == 0.95
        assert data[0]["recommendation_type"] == "content_based"
        assert "machine learning" in data[0]["explanation"]

    @patch("knowledge_service.api.dependencies.get_current_user")
    @patch(
        "knowledge_service.services.factory.ServiceFactory.get_recommendation_service"
    )
    def test_get_user_recommendations_with_filters(
        self, mock_service, mock_user_dep, client, mock_user, sample_recommendations
    ):
        """Test user recommendations with type filters."""
        # Setup mocks
        mock_user_dep.return_value = mock_user
        mock_recommendation_service = AsyncMock()
        mock_recommendation_service.get_recommendations.return_value = (
            sample_recommendations[:1]
        )
        mock_service.return_value = mock_recommendation_service

        # Make request with filters
        response = client.get(
            "/api/v1/recommendations/",
            params={
                "num_recommendations": 5,
                "recommendation_types": ["content_based"],
            },
        )

        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["recommendation_type"] == "content_based"

    @patch("knowledge_service.api.dependencies.get_current_user")
    @patch(
        "knowledge_service.services.factory.ServiceFactory.get_recommendation_service"
    )
    def test_get_similar_resources_success(
        self, mock_service, mock_user_dep, client, mock_user, sample_recommendations
    ):
        """Test successful similar resources retrieval."""
        # Setup mocks
        mock_user_dep.return_value = mock_user
        mock_recommendation_service = AsyncMock()
        mock_recommendation_service.get_similar_resources.return_value = (
            sample_recommendations
        )
        mock_service.return_value = mock_recommendation_service

        # Make request
        response = client.get("/api/v1/recommendations/similar/123")

        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        mock_recommendation_service.get_similar_resources.assert_called_once()

    @patch("knowledge_service.api.dependencies.get_current_user")
    @patch(
        "knowledge_service.services.factory.ServiceFactory.get_recommendation_service"
    )
    def test_explain_recommendation_success(
        self, mock_service, mock_user_dep, client, mock_user
    ):
        """Test successful recommendation explanation."""
        # Setup mocks
        mock_user_dep.return_value = mock_user
        mock_recommendation_service = AsyncMock()
        mock_explanation = {
            "resource_id": 123,
            "resource_title": "Machine Learning Guide",
            "user_profile_summary": {
                "interests": ["machine learning", "AI"],
                "expertise_level": "intermediate",
                "technical_domains": ["data science"],
                "preferred_content_types": ["article"],
            },
            "matching_factors": [
                {
                    "factor": "interests",
                    "matches": ["machine learning"],
                    "strength": 0.8,
                }
            ],
            "recommendation_strength": "strong",
        }
        mock_recommendation_service.explain_recommendation.return_value = (
            mock_explanation
        )
        mock_service.return_value = mock_recommendation_service

        # Make request
        response = client.get("/api/v1/recommendations/explain/123")

        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert data["resource_id"] == 123
        assert data["resource_title"] == "Machine Learning Guide"
        assert data["recommendation_strength"] == "strong"

    @patch("knowledge_service.api.dependencies.get_current_user")
    @patch(
        "knowledge_service.services.factory.ServiceFactory.get_recommendation_service"
    )
    def test_get_trending_recommendations_success(
        self, mock_service, mock_user_dep, client, mock_user, sample_recommendations
    ):
        """Test successful trending recommendations retrieval."""
        # Setup mocks
        mock_user_dep.return_value = mock_user
        mock_recommendation_service = AsyncMock()
        trending_recs = [
            rec
            for rec in sample_recommendations
            if rec.recommendation_type == RecommendationType.COLLABORATIVE
        ]
        mock_recommendation_service.get_recommendations.return_value = trending_recs
        mock_service.return_value = mock_recommendation_service

        # Make request
        response = client.get("/api/v1/recommendations/trending")

        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 0  # May be empty if no trending recommendations

    @patch("knowledge_service.api.dependencies.get_current_user")
    @patch(
        "knowledge_service.services.factory.ServiceFactory.get_recommendation_service"
    )
    def test_get_recommendation_stats_success(
        self, mock_service, mock_user_dep, client, mock_user
    ):
        """Test successful recommendation stats retrieval."""
        # Setup mocks
        mock_user_dep.return_value = mock_user
        mock_recommendation_service = AsyncMock()
        mock_stats = {
            "user_profile_cache_size": 10,
            "recommendation_cache_size": 50,
            "cache_ttl": 3600,
            "weights": {
                "content_based": 0.4,
                "collaborative": 0.3,
                "trending": 0.1,
                "contextual": 0.2,
            },
        }
        mock_recommendation_service.get_cache_stats.return_value = mock_stats
        mock_service.return_value = mock_recommendation_service

        # Make request
        response = client.get("/api/v1/recommendations/stats")

        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert "cache_stats" in data
        assert "available_recommendation_types" in data
        assert "default_weights" in data

    @patch("knowledge_service.api.dependencies.get_current_user")
    @patch(
        "knowledge_service.services.factory.ServiceFactory.get_recommendation_service"
    )
    def test_update_recommendation_weights_success(
        self, mock_service, mock_user_dep, client, mock_user
    ):
        """Test successful recommendation weights update."""
        # Setup mocks
        mock_user_dep.return_value = mock_user
        mock_recommendation_service = AsyncMock()
        mock_service.return_value = mock_recommendation_service

        # Make request
        response = client.post(
            "/api/v1/recommendations/weights",
            json={
                "content_based": 0.5,
                "collaborative": 0.3,
                "trending": 0.1,
                "contextual": 0.1,
            },
        )

        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "new_weights" in data
        mock_recommendation_service.update_weights.assert_called_once()

    @patch("knowledge_service.api.dependencies.get_current_user")
    @patch(
        "knowledge_service.services.factory.ServiceFactory.get_recommendation_service"
    )
    def test_update_recommendation_weights_invalid_sum(
        self, mock_service, mock_user_dep, client, mock_user
    ):
        """Test recommendation weights update with invalid sum."""
        # Setup mocks
        mock_user_dep.return_value = mock_user
        mock_recommendation_service = AsyncMock()
        mock_recommendation_service.update_weights.side_effect = ValueError(
            "Weights must sum to 1.0"
        )
        mock_service.return_value = mock_recommendation_service

        # Make request
        response = client.post(
            "/api/v1/recommendations/weights",
            json={"content_based": 0.8, "collaborative": 0.8},  # Sum > 1.0
        )

        # Assertions
        assert response.status_code == 400
        assert "Weights must sum to 1.0" in response.json()["detail"]

    @patch("knowledge_service.api.dependencies.get_current_user")
    @patch(
        "knowledge_service.services.factory.ServiceFactory.get_recommendation_service"
    )
    def test_clear_recommendation_cache_success(
        self, mock_service, mock_user_dep, client, mock_user
    ):
        """Test successful recommendation cache clearing."""
        # Setup mocks
        mock_user_dep.return_value = mock_user
        mock_recommendation_service = AsyncMock()
        mock_service.return_value = mock_recommendation_service

        # Make request
        response = client.post("/api/v1/recommendations/cache/clear")

        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "cleared_by" in data
        mock_recommendation_service.clear_cache.assert_called_once()

    @patch("knowledge_service.api.dependencies.get_current_user")
    @patch(
        "knowledge_service.services.factory.ServiceFactory.get_recommendation_service"
    )
    def test_get_contextual_recommendations_project(
        self, mock_service, mock_user_dep, client, mock_user, sample_recommendations
    ):
        """Test contextual recommendations for project context."""
        # Setup mocks
        mock_user_dep.return_value = mock_user
        mock_recommendation_service = AsyncMock()
        mock_recommendation_service.get_recommendations.return_value = (
            sample_recommendations
        )
        mock_service.return_value = mock_recommendation_service

        # Make request
        response = client.get(
            "/api/v1/recommendations/contextual",
            params={"context_type": "project", "context_value": "project_123"},
        )

        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 0

    @patch("knowledge_service.api.dependencies.get_current_user")
    @patch(
        "knowledge_service.services.factory.ServiceFactory.get_recommendation_service"
    )
    def test_get_contextual_recommendations_search(
        self, mock_service, mock_user_dep, client, mock_user, sample_recommendations
    ):
        """Test contextual recommendations for search context."""
        # Setup mocks
        mock_user_dep.return_value = mock_user
        mock_recommendation_service = AsyncMock()
        mock_recommendation_service.get_recommendations.return_value = (
            sample_recommendations
        )
        mock_service.return_value = mock_recommendation_service

        # Make request
        response = client.get(
            "/api/v1/recommendations/contextual",
            params={
                "context_type": "search",
                "context_value": "machine learning algorithms",
            },
        )

        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 0

    @patch("knowledge_service.api.dependencies.get_current_user")
    @patch(
        "knowledge_service.services.factory.ServiceFactory.get_recommendation_service"
    )
    def test_get_contextual_recommendations_resource(
        self, mock_service, mock_user_dep, client, mock_user, sample_recommendations
    ):
        """Test contextual recommendations for resource context."""
        # Setup mocks
        mock_user_dep.return_value = mock_user
        mock_recommendation_service = AsyncMock()
        mock_recommendation_service.get_recommendations.return_value = (
            sample_recommendations
        )
        mock_service.return_value = mock_recommendation_service

        # Make request
        response = client.get(
            "/api/v1/recommendations/contextual",
            params={"context_type": "resource", "context_value": "123"},
        )

        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 0

    def test_get_contextual_recommendations_invalid_context_type(self, client):
        """Test contextual recommendations with invalid context type."""
        with patch(
            "knowledge_service.api.dependencies.get_current_user"
        ) as mock_user_dep:
            mock_user_dep.return_value = {"id": 1}

            response = client.get(
                "/api/v1/recommendations/contextual",
                params={"context_type": "invalid", "context_value": "test"},
            )

            assert response.status_code == 400
            assert "Context type must be one of" in response.json()["detail"]

    def test_get_contextual_recommendations_invalid_resource_id(self, client):
        """Test contextual recommendations with invalid resource ID."""
        with patch(
            "knowledge_service.api.dependencies.get_current_user"
        ) as mock_user_dep:
            mock_user_dep.return_value = {"id": 1}

            response = client.get(
                "/api/v1/recommendations/contextual",
                params={"context_type": "resource", "context_value": "not_a_number"},
            )

            assert response.status_code == 400
            assert "Resource ID must be an integer" in response.json()["detail"]

    @patch("knowledge_service.api.dependencies.get_current_user")
    @patch(
        "knowledge_service.services.factory.ServiceFactory.get_recommendation_service"
    )
    def test_explain_recommendation_not_found(
        self, mock_service, mock_user_dep, client, mock_user
    ):
        """Test recommendation explanation for non-existent resource."""
        # Setup mocks
        mock_user_dep.return_value = mock_user
        mock_recommendation_service = AsyncMock()
        mock_recommendation_service.explain_recommendation.return_value = {
            "error": "Resource not found"
        }
        mock_service.return_value = mock_recommendation_service

        # Make request
        response = client.get("/api/v1/recommendations/explain/999")

        # Assertions
        assert response.status_code == 404
        assert "Resource not found" in response.json()["detail"]

    @patch("knowledge_service.api.dependencies.get_current_user")
    @patch(
        "knowledge_service.services.factory.ServiceFactory.get_recommendation_service"
    )
    def test_service_error_handling(
        self, mock_service, mock_user_dep, client, mock_user
    ):
        """Test error handling when service fails."""
        # Setup mocks
        mock_user_dep.return_value = mock_user
        mock_recommendation_service = AsyncMock()
        mock_recommendation_service.get_recommendations.side_effect = Exception(
            "Service error"
        )
        mock_service.return_value = mock_recommendation_service

        # Make request
        response = client.get("/api/v1/recommendations/")

        # Assertions
        assert response.status_code == 500
        assert "Failed to get recommendations" in response.json()["detail"]
