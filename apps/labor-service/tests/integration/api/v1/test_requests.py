"""
TDD RED Phase: Failing API tests for service request endpoints.

These tests define the expected behavior for service request API endpoints
and will fail until the API layer is implemented.
"""
import pytest
from fastapi.testclient import TestClient
from httpx import AsyncClient
from src.main import app


class TestServiceRequestAPI:
    """Test service request management API endpoints."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)

    @pytest.fixture
    async def async_client(self):
        """Create async test client."""
        async with AsyncClient(app=app, base_url="http://test") as ac:
            yield ac

    def test_create_service_request_success(self, client):
        """Test successful service request creation."""
        request_data = {
            "seeker_id": 1,
            "project_id": 123,
            "title": "Kitchen Renovation - Electrical Work",
            "description": "Need licensed electrician for kitchen renovation project",
            "urgency_level": "MEDIUM",
            "budget_min": 1000.00,
            "budget_max": 2500.00,
            "location_address": "456 Oak Street, Brooklyn, NY 11201",
            "location_latitude": 40.6892,
            "location_longitude": -73.9442,
            "preferred_start_date": "2024-02-01T00:00:00Z",
            "estimated_duration_hours": 40,
            "requirements": "Licensed electrician with experience in kitchen renovations",
        }

        response = client.post("/api/v1/requests", json=request_data)

        assert response.status_code == 201
        data = response.json()
        assert data["seeker_id"] == 1
        assert data["title"] == "Kitchen Renovation - Electrical Work"
        assert data["status"] == "DRAFT"
        assert data["urgency_level"] == "MEDIUM"
        assert data["location_address"] == "456 Oak Street, Brooklyn, NY 11201"
        assert data["id"] is not None

    def test_create_request_validation_error(self, client):
        """Test service request creation with invalid data."""
        invalid_data = {
            "seeker_id": "invalid",
            "title": "",  # Empty title
            "budget_min": -100,  # Negative budget
            "timeline": {"start_date": "invalid-date"},
        }

        response = client.post("/api/v1/requests", json=invalid_data)

        assert response.status_code == 422
        assert "detail" in response.json()

    def test_get_service_request_success(self, client):
        """Test successful service request retrieval."""
        # First create a request
        create_data = {
            "seeker_id": 1,
            "title": "Test Kitchen Project",
            "description": "Test kitchen renovation project for retrieval",
            "urgency_level": "MEDIUM",
            "budget_min": 1000.00,
            "budget_max": 2500.00,
            "location_address": "123 Test St, New York, NY 10001",
            "location_latitude": 40.7128,
            "location_longitude": -74.0060,
        }

        create_response = client.post("/api/v1/requests", json=create_data)
        assert create_response.status_code == 201
        created_request = create_response.json()
        request_id = created_request["id"]

        # Now retrieve the request
        response = client.get(f"/api/v1/requests/{request_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == request_id
        assert data["title"] == "Test Kitchen Project"
        assert data["seeker_id"] == 1
        assert data["status"] == "DRAFT"

    def test_get_request_not_found(self, client):
        """Test request retrieval with non-existent ID."""
        response = client.get("/api/v1/requests/99999")

        assert response.status_code == 404
        assert response.json()["detail"] == "Service request not found"

    def test_update_service_request(self, client):
        """Test service request update."""
        # First create a request
        create_data = {
            "seeker_id": 1,
            "title": "Original Kitchen Project",
            "description": "Original project description for kitchen renovation",
            "urgency_level": "MEDIUM",
            "budget_min": 1000.00,
            "budget_max": 2500.00,
            "location_address": "123 Main St, New York, NY 10001",
            "location_latitude": 40.7128,
            "location_longitude": -74.0060,
        }

        create_response = client.post("/api/v1/requests", json=create_data)
        assert create_response.status_code == 201
        created_request = create_response.json()
        request_id = created_request["id"]

        # Now update the request
        update_data = {
            "title": "Updated Kitchen Project",
            "budget_max": 3000.00,
            "description": "Updated project description",
        }

        response = client.put(f"/api/v1/requests/{request_id}", json=update_data)

        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Updated Kitchen Project"
        assert data["budget_max"] == "3000.00"  # Decimal fields are returned as strings
        assert data["description"] == "Updated project description"

    def test_publish_service_request(self, client):
        """Test publishing a service request."""
        # First create a request
        create_data = {
            "seeker_id": 1,
            "title": "Kitchen Project to Publish",
            "description": "Kitchen renovation project that needs to be published",
            "urgency_level": "MEDIUM",
            "budget_min": 1000.00,
            "budget_max": 2500.00,
            "location_address": "123 Main St, New York, NY 10001",
            "location_latitude": 40.7128,
            "location_longitude": -74.0060,
        }

        create_response = client.post("/api/v1/requests", json=create_data)
        assert create_response.status_code == 201
        created_request = create_response.json()
        request_id = created_request["id"]

        # Now publish the request
        response = client.post(f"/api/v1/requests/{request_id}/publish")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ACTIVE"  # Should be ACTIVE after publishing

    def test_cancel_service_request(self, client):
        """Test canceling a service request."""
        # First create a request
        create_data = {
            "seeker_id": 1,
            "title": "Kitchen Project to Cancel",
            "description": "Kitchen renovation project that will be cancelled",
            "urgency_level": "MEDIUM",
            "budget_min": 1000.00,
            "budget_max": 2500.00,
            "location_address": "123 Main St, New York, NY 10001",
            "location_latitude": 40.7128,
            "location_longitude": -74.0060,
        }

        create_response = client.post("/api/v1/requests", json=create_data)
        assert create_response.status_code == 201
        created_request = create_response.json()
        request_id = created_request["id"]

        # Now cancel the request
        cancel_data = {"reason": "Project postponed"}

        response = client.post(
            f"/api/v1/requests/{request_id}/cancel", json=cancel_data
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "CANCELLED"  # Should be CANCELLED after canceling

    def test_list_requests_with_filters(self, client):
        """Test service request listing with filters."""
        params = {
            "category": "electrical",
            "location": "Brooklyn, NY",
            "radius": 15,
            "budget_min": 1000,
            "budget_max": 5000,
            "urgency": "normal",
            "status": "open",
        }

        response = client.get("/api/v1/requests", params=params)

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert "page" in data
        assert isinstance(data["items"], list)

    def test_search_requests_by_skills(self, client):
        """Test searching requests by skill requirements."""
        params = {
            "skills": "electrical_wiring,plumbing",
            "provider_id": 1,  # Search for requests matching provider skills
        }

        response = client.get("/api/v1/requests/search", params=params)

        assert response.status_code == 200
        data = response.json()
        assert "results" in data
        assert "match_scores" in data

    def test_get_request_analytics(self, client):
        """Test request analytics endpoint."""
        response = client.get("/api/v1/requests/1/analytics")

        assert response.status_code == 200
        data = response.json()
        assert "views" in data
        assert "quotes_received" in data
        assert "average_quote_amount" in data

    @pytest.mark.asyncio
    async def test_get_matching_providers(self, async_client):
        """Test getting matching providers for a request."""
        response = await async_client.get("/api/v1/requests/1/matching-providers")

        assert response.status_code == 200
        data = response.json()
        assert "providers" in data
        assert "match_scores" in data
        assert isinstance(data["providers"], list)
