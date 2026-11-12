"""
TDD RED Phase: Failing API tests for matching and search endpoints.

These tests define the expected behavior for matching API endpoints
and will fail until the API layer is implemented.
"""
import pytest
from fastapi.testclient import TestClient
from httpx import AsyncClient
from src.main import app


class TestMatchingAPI:
    """Test matching and search API endpoints."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)

    @pytest.fixture
    async def async_client(self):
        """Create async test client."""
        async with AsyncClient(app=app, base_url="http://test") as ac:
            yield ac

    def test_find_providers_for_request(self, client):
        """Test finding matching providers for a service request."""
        params = {"request_id": 1, "max_distance": 25, "min_rating": 4.0, "limit": 10}

        response = client.get("/api/v1/matching/providers", params=params)

        assert response.status_code == 200
        data = response.json()
        assert "providers" in data
        assert "match_scores" in data
        assert "total_matches" in data
        assert isinstance(data["providers"], list)

    def test_find_opportunities_for_provider(self, client):
        """Test finding matching opportunities for a provider."""
        params = {"provider_id": 1, "max_distance": 30, "budget_min": 1000, "limit": 15}

        response = client.get("/api/v1/matching/opportunities", params=params)

        assert response.status_code == 200
        data = response.json()
        assert "requests" in data
        assert "match_scores" in data
        assert "total_matches" in data

    def test_calculate_match_score(self, client):
        """Test calculating match score between provider and request."""
        match_data = {"provider_id": 1, "request_id": 1}

        response = client.post("/api/v1/matching/calculate-score", json=match_data)

        assert response.status_code == 200
        data = response.json()
        assert "overall_score" in data
        assert "skill_match" in data
        assert "location_score" in data
        assert "availability_score" in data
        assert "rating_score" in data

    def test_search_providers_advanced(self, client):
        """Test advanced provider search."""
        params = {
            "skills": "electrical,plumbing",
            "location": "40.7128,-74.0060",  # NYC coordinates
            "radius": 20,
            "min_rating": 4.0,
            "max_hourly_rate": 100,
            "available_from": "2024-02-01",
            "available_until": "2024-02-15",
            "certifications": "licensed",
            "sort_by": "rating",
            "order": "desc",
        }

        response = client.get("/api/v1/search/providers", params=params)

        assert response.status_code == 200
        data = response.json()
        assert "results" in data
        assert "filters_applied" in data
        assert "total" in data
        assert "facets" in data

    def test_search_requests_advanced(self, client):
        """Test advanced request search."""
        params = {
            "category": "electrical",
            "location": "Brooklyn, NY",
            "radius": 15,
            "budget_min": 1000,
            "budget_max": 5000,
            "urgency": "normal",
            "timeline_start": "2024-02-01",
            "timeline_end": "2024-03-01",
        }

        response = client.get("/api/v1/search/requests", params=params)

        assert response.status_code == 200
        data = response.json()
        assert "results" in data
        assert "total" in data
        assert "facets" in data

    def test_get_search_suggestions(self, client):
        """Test getting search suggestions."""
        params = {"q": "electr", "type": "skills"}

        response = client.get("/api/v1/search/suggestions", params=params)

        assert response.status_code == 200
        data = response.json()
        assert "suggestions" in data
        assert isinstance(data["suggestions"], list)

    def test_notify_providers_of_new_request(self, client):
        """Test notifying matching providers of new request."""
        notification_data = {
            "request_id": 1,
            "max_providers": 20,
            "min_match_score": 0.7,
        }

        response = client.post(
            "/api/v1/matching/notify-providers", json=notification_data
        )

        assert response.status_code == 200
        data = response.json()
        assert "notified_count" in data
        assert "notification_id" in data

    def test_emergency_request_matching(self, client):
        """Test emergency request matching with priority."""
        emergency_data = {
            "request_id": 1,
            "urgency_level": "emergency",
            "max_distance": 50,
            "immediate_notification": True,
        }

        response = client.post("/api/v1/matching/emergency", json=emergency_data)

        assert response.status_code == 200
        data = response.json()
        assert "priority_providers" in data
        assert "notification_sent" in data
        assert data["notification_sent"] is True

    def test_bulk_matching_for_project(self, client):
        """Test bulk matching for multiple requests in a project."""
        bulk_data = {
            "project_id": 123,
            "request_ids": [1, 2, 3],
            "coordination_required": True,
        }

        response = client.post("/api/v1/matching/bulk", json=bulk_data)

        assert response.status_code == 200
        data = response.json()
        assert "matches" in data
        assert "coordination_suggestions" in data

    def test_get_matching_analytics(self, client):
        """Test matching analytics endpoint."""
        params = {"period": "last_30_days", "provider_id": 1}

        response = client.get("/api/v1/matching/analytics", params=params)

        assert response.status_code == 200
        data = response.json()
        assert "match_success_rate" in data
        assert "average_response_time" in data
        assert "top_skills_requested" in data

    @pytest.mark.asyncio
    async def test_real_time_matching_updates(self, async_client):
        """Test real-time matching updates via WebSocket-like endpoint."""
        params = {"provider_id": 1, "subscribe_to": "new_opportunities"}

        response = await async_client.get("/api/v1/matching/updates", params=params)

        assert response.status_code == 200
        data = response.json()
        assert "subscription_id" in data
        assert "status" in data
