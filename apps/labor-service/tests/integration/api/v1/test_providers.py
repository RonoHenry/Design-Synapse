"""
TDD RED Phase: Failing API tests for provider management endpoints.

These tests define the expected behavior for provider API endpoints
and will fail until the API layer is implemented.
"""
import pytest
from fastapi.testclient import TestClient
from httpx import AsyncClient
from src.main import app


class TestProviderAPI:
    """Test provider management API endpoints."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)

    @pytest.fixture
    async def async_client(self):
        """Create async test client."""
        async with AsyncClient(app=app, base_url="http://test") as ac:
            yield ac

    def test_create_provider_success(self, client):
        """Test successful provider creation."""
        provider_data = {
            "user_id": 1,
            "business_name": "Smith Construction",
            "individual_name": "John Smith",
            "provider_type": "INDIVIDUAL",
            "description": "Professional construction services",
            "experience_years": 10,
        }

        response = client.post("/api/v1/providers", json=provider_data)

        assert response.status_code == 201
        data = response.json()
        assert data["user_id"] == 1
        assert data["business_name"] == "Smith Construction"
        assert data["id"] is not None
        assert "created_at" in data

    def test_create_provider_validation_error(self, client):
        """Test provider creation with invalid data."""
        invalid_data = {
            "user_id": "invalid",  # Should be integer
            "business_name": "",  # Should not be empty
            "hourly_rate": -10,  # Should be positive
        }

        response = client.post("/api/v1/providers", json=invalid_data)

        assert response.status_code == 422
        assert "detail" in response.json()

    def test_get_provider_success(self, client):
        """Test successful provider retrieval."""
        # First create a provider
        provider_data = {
            "user_id": 1,
            "business_name": "Smith Construction",
            "individual_name": "John Smith",
            "provider_type": "INDIVIDUAL",
            "description": "Professional construction services",
            "experience_years": 10,
        }
        create_response = client.post("/api/v1/providers", json=provider_data)
        assert create_response.status_code == 201
        created_provider = create_response.json()

        # Then retrieve it
        response = client.get(f"/api/v1/providers/{created_provider['id']}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == created_provider["id"]
        assert data["business_name"] == "Smith Construction"
        assert data["individual_name"] == "John Smith"

    def test_get_provider_not_found(self, client):
        """Test provider retrieval with non-existent ID."""
        response = client.get("/api/v1/providers/99999")

        assert response.status_code == 404
        assert response.json()["detail"] == "Provider not found"

    def test_update_provider_success(self, client):
        """Test successful provider update."""
        # First create a provider
        provider_data = {
            "user_id": 1,
            "business_name": "Smith Construction",
            "individual_name": "John Smith",
            "provider_type": "INDIVIDUAL",
            "description": "Professional construction services",
            "experience_years": 10,
        }
        create_response = client.post("/api/v1/providers", json=provider_data)
        assert create_response.status_code == 201
        created_provider = create_response.json()

        # Then update it
        update_data = {
            "business_name": "Updated Construction Co",
            "description": "Updated description",
        }

        response = client.put(
            f"/api/v1/providers/{created_provider['id']}", json=update_data
        )

        assert response.status_code == 200
        data = response.json()
        assert data["business_name"] == "Updated Construction Co"
        assert data["description"] == "Updated description"

    def test_list_providers_with_filters(self, client):
        """Test provider listing with search filters."""
        params = {
            "skills": "plumbing,electrical",
            "location": "New York, NY",
            "radius": 25,
            "min_rating": 4.0,
            "available": True,
        }

        response = client.get("/api/v1/providers", params=params)

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert "page" in data
        assert "size" in data
        assert isinstance(data["items"], list)

    def test_add_provider_skill(self, client):
        """Test adding skill to provider."""
        # First create a provider
        provider_data = {
            "user_id": 1,
            "business_name": "Smith Construction",
            "individual_name": "John Smith",
            "provider_type": "INDIVIDUAL",
            "description": "Professional construction services",
            "experience_years": 10,
        }
        create_response = client.post("/api/v1/providers", json=provider_data)
        assert create_response.status_code == 201
        created_provider = create_response.json()

        # Then add a skill
        skill_data = {
            "skill_id": 1,
            "proficiency_level": "expert",
            "years_experience": 5,
            "certifications": ["Licensed Electrician"],
        }

        response = client.post(
            f"/api/v1/providers/{created_provider['id']}/skills", json=skill_data
        )

        assert response.status_code == 201
        data = response.json()
        assert data["skill_id"] == 1
        assert data["proficiency_level"] == "expert"

    def test_update_provider_availability(self, client):
        """Test updating provider availability."""
        # First create a provider
        provider_data = {
            "user_id": 1,
            "business_name": "Smith Construction",
            "individual_name": "John Smith",
            "provider_type": "INDIVIDUAL",
            "description": "Professional construction services",
            "experience_years": 10,
        }
        create_response = client.post("/api/v1/providers", json=provider_data)
        assert create_response.status_code == 201
        created_provider = create_response.json()

        # Then update availability
        availability_data = {"available": True}

        response = client.put(
            f"/api/v1/providers/{created_provider['id']}/availability",
            json=availability_data,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["available"] is True

    def test_get_provider_analytics(self, client):
        """Test provider analytics endpoint."""
        # First create a provider
        provider_data = {
            "user_id": 1,
            "business_name": "Smith Construction",
            "individual_name": "John Smith",
            "provider_type": "INDIVIDUAL",
            "description": "Professional construction services",
            "experience_years": 10,
        }
        create_response = client.post("/api/v1/providers", json=provider_data)
        assert create_response.status_code == 201
        created_provider = create_response.json()

        # Then get analytics
        response = client.get(f"/api/v1/providers/{created_provider['id']}/analytics")

        assert response.status_code == 200
        data = response.json()
        assert "total_jobs" in data
        assert "average_rating" in data

    @pytest.mark.asyncio
    async def test_search_providers_async(self, async_client):
        """Test async provider search."""
        params = {"q": "construction", "location": "40.7128,-74.0060", "radius": 10}

        response = await async_client.get("/api/v1/providers/search", params=params)

        assert response.status_code == 200
        data = response.json()
        assert "results" in data
        assert "total" in data
