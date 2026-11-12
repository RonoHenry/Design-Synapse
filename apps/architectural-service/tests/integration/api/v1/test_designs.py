"""Integration tests for design management endpoints."""

import json
from datetime import datetime
from uuid import UUID, uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from src.models.design import Design
from src.models.design_version import DesignVersion


class TestDesignEndpoints:
    """Test design CRUD endpoints."""

    @pytest.fixture
    def sample_design_data(self):
        """Sample design data for testing."""
        return {
            "project_id": str(uuid4()),
            "name": "Test Office Building",
            "description": "A test commercial office building",
            "building_type": "commercial",
            "location": {
                "address": "123 Test Street",
                "city": "Test City",
                "state": "Test State",
                "country": "Test Country",
                "postal_code": "12345",
                "latitude": 37.7749,
                "longitude": -122.4194,
                "jurisdiction": "Test Jurisdiction",
            },
            "metadata": {
                "floors": 5,
                "total_area_sqft": 50000,
                "parking_spaces": 25,
            },
        }

    @pytest.fixture
    def auth_headers(self):
        """Authentication headers for testing."""
        return {"Authorization": "Bearer test-token"}

    async def test_create_design_success(
        self, client: AsyncClient, sample_design_data: dict, auth_headers: dict
    ):
        """Test successful design creation."""
        response = await client.post(
            "/api/v1/designs",
            json=sample_design_data,
            headers=auth_headers,
        )

        assert response.status_code == 201
        data = response.json()

        assert "id" in data
        assert data["project_id"] == sample_design_data["project_id"]
        assert data["name"] == sample_design_data["name"]
        assert data["building_type"] == sample_design_data["building_type"]
        assert data["current_version"] == "1.0"
        assert data["version_number"] == 1
        assert data["status"] == "draft"
        assert "created_by" in data
        assert "created_at" in data
        assert "updated_at" in data

    async def test_create_design_validation_error(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test design creation with validation errors."""
        invalid_data = {
            "project_id": "invalid-uuid",
            "name": "",  # Empty name should fail
            "building_type": "invalid_type",
        }

        response = await client.post(
            "/api/v1/designs",
            json=invalid_data,
            headers=auth_headers,
        )

        assert response.status_code == 422  # Validation error

    async def test_create_design_without_auth(
        self, client: AsyncClient, sample_design_data: dict
    ):
        """Test design creation without authentication."""
        response = await client.post(
            "/api/v1/designs",
            json=sample_design_data,
        )

        # Should still work with mock authentication (returns mock user ID)
        assert response.status_code == 201

    async def test_get_design_success(
        self, client: AsyncClient, test_session: AsyncSession, auth_headers: dict
    ):
        """Test successful design retrieval."""
        # Create a design in the database
        design_id = str(uuid4())
        project_id = str(uuid4())
        user_id = str(uuid4())

        design = Design(
            id=design_id,
            project_id=project_id,
            name="Test Design",
            description="Test description",
            building_type="commercial",
            location_data={
                "address": "123 Test St",
                "city": "Test City",
                "state": "Test State",
                "country": "Test Country",
            },
            current_version="1.0",
            version_number=1,
            status="draft",
            metadata={"test": "data"},
            created_by=user_id,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            is_deleted=False,
        )

        test_session.add(design)
        await test_session.commit()

        response = await client.get(f"/api/v1/designs/{design_id}")

        assert response.status_code == 200
        data = response.json()

        assert data["id"] == design_id
        assert data["project_id"] == project_id
        assert data["name"] == "Test Design"
        assert data["description"] == "Test description"
        assert data["building_type"] == "commercial"
        assert data["current_version"] == "1.0"
        assert data["version_number"] == 1
        assert data["status"] == "draft"
        assert data["is_deleted"] is False
        assert data["drawing_count"] == 0
        assert data["material_count"] == 0
        assert data["compliance_check_count"] == 0

    async def test_get_design_not_found(self, client: AsyncClient):
        """Test design retrieval with non-existent ID."""
        non_existent_id = str(uuid4())

        response = await client.get(f"/api/v1/designs/{non_existent_id}")

        assert response.status_code == 404
        data = response.json()
        assert "detail" in data
        assert "error" in data["detail"]

    async def test_get_design_specific_version(
        self, client: AsyncClient, test_session: AsyncSession
    ):
        """Test design retrieval for a specific version."""
        # Create a design with multiple versions
        design_id = str(uuid4())
        project_id = str(uuid4())
        user_id = str(uuid4())

        # Create design
        design = Design(
            id=design_id,
            project_id=project_id,
            name="Test Design v2",
            description="Updated description",
            building_type="commercial",
            location_data={"address": "123 Test St", "country": "United States"},
            current_version="2.0",
            version_number=2,
            status="in_review",
            metadata={},
            created_by=user_id,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            is_deleted=False,
        )

        # Create version records
        version1 = DesignVersion(
            id=str(uuid4()),
            design_id=design_id,
            version="1.0",
            version_number=1,
            design_data={
                "name": "Test Design v1",
                "description": "Original description",
                "building_type": "commercial",
                "status": "draft",
            },
            change_summary="Initial version",
            created_by=user_id,
            created_at=datetime.utcnow(),
        )

        version2 = DesignVersion(
            id=str(uuid4()),
            design_id=design_id,
            version="2.0",
            version_number=2,
            design_data={
                "name": "Test Design v2",
                "description": "Updated description",
                "building_type": "commercial",
                "status": "in_review",
            },
            change_summary="Updated design",
            created_by=user_id,
            created_at=datetime.utcnow(),
        )

        test_session.add_all([design, version1, version2])
        await test_session.commit()

        # Test getting specific version
        response = await client.get(f"/api/v1/designs/{design_id}?version=1.0")

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Test Design v1"
        assert data["description"] == "Original description"
        assert data["status"] == "draft"

    async def test_update_design_success(
        self, client: AsyncClient, test_session: AsyncSession, auth_headers: dict
    ):
        """Test successful design update."""
        # Create a design in the database
        design_id = str(uuid4())
        project_id = str(uuid4())
        user_id = str(uuid4())

        design = Design(
            id=design_id,
            project_id=project_id,
            name="Original Name",
            description="Original description",
            building_type="commercial",
            location_data={"address": "123 Test St", "country": "United States"},
            current_version="1.0",
            version_number=1,
            status="draft",
            metadata={},
            created_by=user_id,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            is_deleted=False,
        )

        test_session.add(design)
        await test_session.commit()

        # Update the design
        update_data = {
            "name": "Updated Name",
            "description": "Updated description",
            "status": "in_review",
            "metadata": {"updated": True},
        }

        response = await client.put(
            f"/api/v1/designs/{design_id}",
            json=update_data,
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()

        assert data["id"] == design_id
        assert data["name"] == "Updated Name"
        assert data["current_version"] == "2.0"
        assert data["version_number"] == 2
        assert data["status"] == "in_review"

    async def test_update_design_not_found(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test design update with non-existent ID."""
        non_existent_id = str(uuid4())
        update_data = {"name": "Updated Name"}

        response = await client.put(
            f"/api/v1/designs/{non_existent_id}",
            json=update_data,
            headers=auth_headers,
        )

        assert response.status_code == 404

    async def test_update_design_validation_error(
        self, client: AsyncClient, test_session: AsyncSession, auth_headers: dict
    ):
        """Test design update with validation errors."""
        # Create a design
        design_id = str(uuid4())
        design = Design(
            id=design_id,
            project_id=str(uuid4()),
            name="Test Design",
            building_type="commercial",
            location_data={},
            current_version="1.0",
            version_number=1,
            status="draft",
            metadata={},
            created_by=str(uuid4()),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            is_deleted=False,
        )

        test_session.add(design)
        await test_session.commit()

        # Try to update with empty data (should fail validation)
        response = await client.put(
            f"/api/v1/designs/{design_id}",
            json={},
            headers=auth_headers,
        )

        assert response.status_code == 400

    async def test_delete_design_success(
        self, client: AsyncClient, test_session: AsyncSession, auth_headers: dict
    ):
        """Test successful design soft deletion."""
        # Create a design
        design_id = str(uuid4())
        design = Design(
            id=design_id,
            project_id=str(uuid4()),
            name="Test Design",
            building_type="commercial",
            location_data={},
            current_version="1.0",
            version_number=1,
            status="draft",
            metadata={},
            created_by=str(uuid4()),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            is_deleted=False,
        )

        test_session.add(design)
        await test_session.commit()

        response = await client.delete(
            f"/api/v1/designs/{design_id}",
            headers=auth_headers,
        )

        assert response.status_code == 204

        # Verify design is soft deleted
        await test_session.refresh(design)
        assert design.is_deleted is True
        assert design.deleted_at is not None

    async def test_delete_design_not_found(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test design deletion with non-existent ID."""
        non_existent_id = str(uuid4())

        response = await client.delete(
            f"/api/v1/designs/{non_existent_id}",
            headers=auth_headers,
        )

        assert response.status_code == 404

    async def test_list_design_versions(
        self, client: AsyncClient, test_session: AsyncSession
    ):
        """Test listing design versions."""
        # Create a design with versions
        design_id = str(uuid4())
        user_id = str(uuid4())

        design = Design(
            id=design_id,
            project_id=str(uuid4()),
            name="Test Design",
            building_type="commercial",
            location_data={},
            current_version="2.0",
            version_number=2,
            status="draft",
            metadata={},
            created_by=user_id,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            is_deleted=False,
        )

        version1 = DesignVersion(
            id=str(uuid4()),
            design_id=design_id,
            version="1.0",
            version_number=1,
            design_data={"name": "Test Design v1"},
            change_summary="Initial version",
            created_by=user_id,
            created_at=datetime.utcnow(),
        )

        version2 = DesignVersion(
            id=str(uuid4()),
            design_id=design_id,
            version="2.0",
            version_number=2,
            design_data={"name": "Test Design v2"},
            change_summary="Updated version",
            created_by=user_id,
            created_at=datetime.utcnow(),
        )

        test_session.add_all([design, version1, version2])
        await test_session.commit()

        response = await client.get(f"/api/v1/designs/{design_id}/versions")

        assert response.status_code == 200
        data = response.json()

        assert len(data) == 2
        assert data[0]["version"] == "1.0"
        assert data[0]["change_summary"] == "Initial version"
        assert data[1]["version"] == "2.0"
        assert data[1]["change_summary"] == "Updated version"

    async def test_get_design_version_detail(
        self, client: AsyncClient, test_session: AsyncSession
    ):
        """Test getting detailed version information."""
        # Create a design with versions
        design_id = str(uuid4())
        user_id = str(uuid4())

        design = Design(
            id=design_id,
            project_id=str(uuid4()),
            name="Test Design v2",
            building_type="commercial",
            location_data={},
            current_version="2.0",
            version_number=2,
            status="in_review",
            metadata={},
            created_by=user_id,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            is_deleted=False,
        )

        version1 = DesignVersion(
            id=str(uuid4()),
            design_id=design_id,
            version="1.0",
            version_number=1,
            design_data={
                "name": "Test Design v1",
                "description": "Original",
                "building_type": "commercial",
                "status": "draft",
            },
            change_summary="Initial version",
            created_by=user_id,
            created_at=datetime.utcnow(),
        )

        test_session.add_all([design, version1])
        await test_session.commit()

        response = await client.get(f"/api/v1/designs/{design_id}/versions/1.0")

        assert response.status_code == 200
        data = response.json()

        assert data["version"] == "1.0"
        assert data["version_number"] == 1
        assert data["change_summary"] == "Initial version"
        assert "design_data" in data
        assert data["design_data"]["name"] == "Test Design v1"
        assert data["design_data"]["status"] == "draft"

    async def test_get_design_version_not_found(self, client: AsyncClient):
        """Test getting non-existent design version."""
        non_existent_id = str(uuid4())

        response = await client.get(f"/api/v1/designs/{non_existent_id}/versions/1.0")

        assert response.status_code == 404
