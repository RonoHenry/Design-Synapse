"""
TDD RED Phase: Failing API tests for review management endpoints.

These tests define the expected behavior for review API endpoints
and will fail until the API layer is implemented.
"""
import pytest
from fastapi.testclient import TestClient
from httpx import AsyncClient
from src.main import app


class TestReviewAPI:
    """Test review management API endpoints."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)

    @pytest.fixture
    async def async_client(self):
        """Create async test client."""
        async with AsyncClient(app=app, base_url="http://test") as ac:
            yield ac

    def test_submit_provider_review(self, client, test_data):
        """Test submitting review for provider."""
        review_data = {
            "booking_id": 1,
            "reviewer_id": 1,
            "reviewee_id": 2,
            "review_type": "provider_review",
            "rating": 5,
            "title": "Excellent electrical work",
            "comment": "Professional, punctual, and high-quality work. Highly recommended!",
            "categories": {
                "quality": 5,
                "timeliness": 5,
                "communication": 4,
                "professionalism": 5,
                "value": 4,
            },
            "would_recommend": True,
            "photos": ["completed_work1.jpg", "completed_work2.jpg"],
        }

        response = client.post("/api/v1/reviews", json=review_data)

        # Debug: print response content if test fails
        if response.status_code != 201:
            print(f"Response status: {response.status_code}")
            print(f"Response content: {response.text}")

        assert response.status_code == 201
        data = response.json()
        assert data["booking_id"] == 1
        assert data["rating"] == 5
        assert data["review_type"] == "provider_review"
        assert data["status"] == "published"
        assert data["id"] is not None

    def test_submit_seeker_review(self, client, test_data):
        """Test submitting review for seeker."""
        review_data = {
            "booking_id": 1,
            "reviewer_id": 2,
            "reviewee_id": 1,
            "review_type": "seeker_review",
            "rating": 4,
            "title": "Good client to work with",
            "comment": "Clear communication and prompt payment. Minor delays in decision making.",
            "categories": {
                "communication": 4,
                "payment_promptness": 5,
                "project_clarity": 3,
                "professionalism": 4,
            },
            "would_recommend": True,
        }

        response = client.post("/api/v1/reviews", json=review_data)

        # Debug: print response content if test fails
        if response.status_code != 201:
            print(f"Response status: {response.status_code}")
            print(f"Response content: {response.text}")

        assert response.status_code == 201
        data = response.json()
        assert data["review_type"] == "seeker_review"
        assert data["rating"] == 4

    def test_submit_review_validation_error(self, client):
        """Test review submission with invalid data."""
        invalid_data = {
            "booking_id": "invalid",
            "rating": 6,  # Rating out of range
            "review_type": "invalid_type",
        }

        response = client.post("/api/v1/reviews", json=invalid_data)

        assert response.status_code == 422
        assert "detail" in response.json()

    def test_get_review_success(self, client, test_data):
        """Test successful review retrieval."""
        response = client.get("/api/v1/reviews/1")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == 1
        assert "rating" in data
        assert "comment" in data
        assert "reviewer" in data
        assert "reviewee" in data

    def test_get_review_not_found(self, client):
        """Test review retrieval with non-existent ID."""
        response = client.get("/api/v1/reviews/99999")

        assert response.status_code == 404
        assert response.json()["detail"] == "Review not found"

    def test_get_provider_reviews(self, client, test_data):
        """Test getting reviews for a provider."""
        params = {
            "provider_id": 1,
            "rating_min": 3,
            "page": 1,
            "size": 10,
            "sort_by": "created_at",
            "order": "desc",
        }

        response = client.get("/api/v1/reviews/provider", params=params)

        # Debug: print response content if test fails
        if response.status_code != 200:
            print(f"Response status: {response.status_code}")
            print(f"Response content: {response.text}")
        else:
            print(f"Response data keys: {list(response.json().keys())}")

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert "average_rating" in data
        assert "rating_distribution" in data

    def test_get_seeker_reviews(self, client, test_data):
        """Test getting reviews for a seeker."""
        params = {"seeker_id": 1, "page": 1, "size": 5}

        response = client.get("/api/v1/reviews/seeker", params=params)

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert "average_rating" in data

    def test_respond_to_review(self, client, test_data):
        """Test responding to a review."""
        response_data = {
            "response": "Thank you for the positive feedback! It was a pleasure working on your project."
        }

        response = client.post("/api/v1/reviews/1/respond", json=response_data)

        # Debug: print response content if test fails
        if response.status_code != 200:
            print(f"Response status: {response.status_code}")
            print(f"Response content: {response.text}")

        assert response.status_code == 200
        data = response.json()
        assert "response" in data
        assert "response_date" in data

    def test_flag_review_inappropriate(self, client, test_data):
        """Test flagging review as inappropriate."""
        flag_data = {
            "reason": "inappropriate_language",
            "details": "Contains offensive language",
        }

        response = client.post("/api/v1/reviews/1/flag", json=flag_data)

        assert response.status_code == 200
        data = response.json()
        assert data["flagged"] is True
        assert "flag_reason" in data

    def test_mark_review_helpful(self, client, test_data):
        """Test marking review as helpful."""
        response = client.post("/api/v1/reviews/1/helpful")

        assert response.status_code == 200
        data = response.json()
        assert "helpful_count" in data

    def test_search_reviews(self, client, test_data):
        """Test searching reviews."""
        params = {
            "q": "excellent work",
            "rating_min": 4,
            "category": "electrical",
            "location": "New York, NY",
        }

        response = client.get("/api/v1/reviews/search", params=params)

        assert response.status_code == 200
        data = response.json()
        assert "items" in data  # Changed from "results" to "items" to match schema
        assert "total" in data

    def test_get_review_analytics(self, client, test_data):
        """Test review analytics endpoint."""
        response = client.get("/api/v1/reviews/analytics")

        assert response.status_code == 200
        data = response.json()
        assert "total_reviews" in data
        assert "average_rating" in data
        assert "rating_trends" in data
        assert "category_averages" in data

    def test_moderate_review(self, client, test_data):
        """Test moderating a review (admin function)."""
        moderation_data = {
            "action": "approve",
            "moderator_notes": "Review meets community guidelines",
        }

        response = client.post("/api/v1/reviews/1/moderate", json=moderation_data)

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "published"
        assert "moderated_at" in data

    def test_bulk_update_provider_ratings(self, client, test_data):
        """Test bulk updating provider ratings."""
        update_data = {"provider_ids": [1, 2, 3]}

        response = client.post("/api/v1/reviews/bulk-update-ratings", json=update_data)

        assert response.status_code == 200
        data = response.json()
        assert "updated_count" in data
        assert data["updated_count"] == 3
