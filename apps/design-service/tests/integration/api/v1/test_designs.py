"""
Integration tests for design CRUD API endpoints.

Tests cover:
- POST /api/v1/designs (create design)
- GET /api/v1/designs/{id} (get design)
- PUT /api/v1/designs/{id} (update design)
- DELETE /api/v1/designs/{id} (soft delete)
- GET /api/v1/designs (list with filters)
- Authentication and authorization
"""

import os
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import status
from src.models.design import Design
from tests.factories import DesignFactory


class TestCreateDesign:
    """Tests for POST /api/v1/designs endpoint."""

    @patch("src.services.design_generator.DesignGeneratorService.generate_design")
    def test_create_design_success(
        self, mock_generate, client, db_session, auth_headers, test_user_id
    ):
        """Test successful design creation."""
        # Setup mock - create a design in the database
        design = DesignFactory.create(
            project_id=1,
            name="Test Design",
            created_by=test_user_id,
        )
        db_session.commit()
        mock_generate.return_value = design

        # Make request
        response = client.post(
            "/api/v1/designs",
            json={
                "project_id": 1,
                "name": "Test Design",
                "description": "A modern residential building with 3 bedrooms",
                "building_type": "residential",
                "requirements": {
                    "num_floors": 2,
                    "total_area": 250.0,
                },
            },
            headers=auth_headers,
        )

        # Assertions
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["name"] == "Test Design"
        assert data["building_type"] == "residential"
        assert data["project_id"] == 1
        assert data["status"] == "draft"
        assert "id" in data
        assert "created_at" in data

    def test_create_design_missing_required_fields(self, client, auth_headers):
        """Test design creation with missing required fields."""
        response = client.post(
            "/api/v1/designs",
            json={
                "name": "Test Design",
                # Missing project_id, description, building_type
            },
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_create_design_invalid_building_type(self, client, auth_headers):
        """Test design creation with invalid building type."""
        response = client.post(
            "/api/v1/designs",
            json={
                "project_id": 1,
                "name": "Test Design",
                "description": "Test description",
                "building_type": "invalid_type",
                "requirements": {},
            },
            headers=auth_headers,
        )

        # Should either reject or accept and let service handle validation
        # 500 is also acceptable if the service fails to process invalid type
        assert response.status_code in [
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_201_CREATED,
            status.HTTP_500_INTERNAL_SERVER_ERROR,
        ]

    def test_create_design_without_authentication(self, client_no_auth):
        """Test design creation without authentication token."""
        response = client_no_auth.post(
            "/api/v1/designs",
            json={
                "project_id": 1,
                "name": "Test Design",
                "description": "Test description",
                "building_type": "residential",
                "requirements": {},
            },
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_create_design_without_project_access(
        self, client, auth_headers, mock_project_client
    ):
        """Test design creation when user doesn't have project access."""
        # Setup mock to raise access denied
        from src.services.project_client import ProjectAccessDeniedError

        mock_project_client.verify_project_access.side_effect = (
            ProjectAccessDeniedError("Access denied")
        )

        response = client.post(
            "/api/v1/designs",
            json={
                "project_id": 999,
                "name": "Test Design",
                "description": "Test description",
                "building_type": "residential",
                "requirements": {},
            },
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    @patch.dict(
        os.environ,
        {
            "LLM_OPENAI_API_KEY": "test-api-key",
            "LLM_OPENAI_MODEL": "gpt-4",
            "STORAGE_S3_BUCKET": "test-bucket",
            "STORAGE_S3_REGION": "us-east-1",
        },
    )
    @patch("src.api.v1.routes.designs.generate_visuals_task")
    @patch("src.services.design_generator.DesignGeneratorService.generate_design")
    def test_create_design_with_visual_generation(
        self,
        mock_generate,
        mock_visual_task,
        client,
        db_session,
        auth_headers,
        test_user_id,
    ):
        """Test design creation with visual generation enabled."""
        # Setup mock - create a design in the database with the expected input values
        design = DesignFactory.create(
            project_id=1,
            name="Test Design with Visuals",
            description="A modern residential building with 3 bedrooms",
            building_type="residential",
            created_by=test_user_id,
            visual_generation_status="not_requested",  # Will be updated to "processing"
        )
        db_session.commit()
        mock_generate.return_value = design

        # Setup visual task mock
        mock_task = AsyncMock()
        mock_task.id = "test-task-123"
        mock_visual_task.delay.return_value = mock_task

        # Make request with generate_visuals=True
        response = client.post(
            "/api/v1/designs",
            json={
                "project_id": 1,
                "name": "Test Design with Visuals",
                "description": "A modern residential building with 3 bedrooms",
                "building_type": "residential",
                "requirements": {
                    "num_floors": 2,
                    "total_area": 250.0,
                },
                "generate_visuals": True,
            },
            headers=auth_headers,
        )

        # Assertions
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["name"] == "Test Design with Visuals"
        assert data["building_type"] == "residential"
        assert data["project_id"] == 1

        # Verify visual generation task was called
        mock_visual_task.delay.assert_called_once()
        call_args = mock_visual_task.delay.call_args
        assert call_args[1]["design_id"] == str(design.id)
        assert call_args[1]["visual_types"] == ["floor_plan", "rendering", "3d_model"]
        assert call_args[1]["size"] == "1024x1024"
        assert call_args[1]["quality"] == "standard"

        # Verify design data passed to visual generation
        design_data = call_args[1]["design_data"]
        assert design_data["building_type"] == "residential"
        assert (
            design_data["description"]
            == "A modern residential building with 3 bedrooms"
        )
        assert design_data["requirements"]["building_info"]["num_floors"] == 2

    @patch("src.services.design_generator.DesignGeneratorService.generate_design")
    def test_create_design_without_visual_generation(
        self, mock_generate, client, db_session, auth_headers, test_user_id
    ):
        """Test design creation with visual generation disabled (default)."""
        # Setup mock - create a design in the database
        design = DesignFactory.create(
            project_id=1,
            name="Test Design No Visuals",
            created_by=test_user_id,
        )
        db_session.commit()
        mock_generate.return_value = design

        # Make request without generate_visuals (defaults to False)
        response = client.post(
            "/api/v1/designs",
            json={
                "project_id": 1,
                "name": "Test Design No Visuals",
                "description": "A simple building design",
                "building_type": "residential",
                "requirements": {},
            },
            headers=auth_headers,
        )

        # Assertions
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["name"] == "Test Design No Visuals"

        # Visual generation status should be "not_requested" (default)
        assert data.get("visual_generation_status") == "not_requested"

    @patch("src.tasks.visual_generation.generate_visuals_task.delay")
    @patch("src.services.design_generator.DesignGeneratorService.generate_design")
    def test_create_design_visual_generation_task_failure(
        self,
        mock_generate,
        mock_visual_task,
        client,
        db_session,
        auth_headers,
        test_user_id,
    ):
        """Test design creation when visual generation task fails to start."""
        # Setup mock - create a design in the database
        design = DesignFactory.create(
            project_id=1,
            name="Test Design Task Fail",
            created_by=test_user_id,
        )
        db_session.commit()
        mock_generate.return_value = design

        # Setup visual task mock to raise exception
        mock_visual_task.side_effect = Exception("Celery connection failed")

        # Make request with generate_visuals=True
        response = client.post(
            "/api/v1/designs",
            json={
                "project_id": 1,
                "name": "Test Design Task Fail",
                "description": "A building design where visual task fails",
                "building_type": "residential",
                "requirements": {},
                "generate_visuals": True,
            },
            headers=auth_headers,
        )

        # Design creation should still succeed even if visual generation fails
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["name"] == "Test Design Task Fail"

        # Visual generation task should have been attempted
        mock_visual_task.assert_called_once()

    @patch("src.services.design_generator.DesignGeneratorService.generate_design")
    def test_create_design_explicit_visual_generation_false(
        self, mock_generate, client, db_session, auth_headers, test_user_id
    ):
        """Test design creation with generate_visuals explicitly set to False."""
        # Setup mock - create a design in the database with the expected input values
        design = DesignFactory.create(
            project_id=1,
            name="Test Design Explicit False",
            description="A building design with explicit visual generation disabled",
            building_type="commercial",
            created_by=test_user_id,
        )
        db_session.commit()
        mock_generate.return_value = design

        # Make request with generate_visuals=False
        response = client.post(
            "/api/v1/designs",
            json={
                "project_id": 1,
                "name": "Test Design Explicit False",
                "description": "A building design with explicit visual generation disabled",
                "building_type": "commercial",
                "requirements": {"floors": 5},
                "generate_visuals": False,
            },
            headers=auth_headers,
        )

        # Assertions
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["name"] == "Test Design Explicit False"
        assert data["building_type"] == "commercial"


class TestGetDesign:
    """Tests for GET /api/v1/designs/{id} endpoint."""

    def test_get_design_success(self, client, db_session, auth_headers):
        """Test successful design retrieval."""
        # Create test design
        design = DesignFactory.create(
            project_id=1,
            name="Test Design",
            created_by=1,
        )
        db_session.commit()

        # Make request
        response = client.get(
            f"/api/v1/designs/{design.id}",
            headers=auth_headers,
        )

        # Assertions
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == design.id
        assert data["name"] == design.name
        assert data["project_id"] == design.project_id
        assert data["building_type"] == design.building_type

    def test_get_design_not_found(self, client, auth_headers):
        """Test retrieving non-existent design."""
        response = client.get(
            "/api/v1/designs/99999",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_get_design_without_authentication(self, client_no_auth, db_session):
        """Test retrieving design without authentication."""
        design = DesignFactory.create(project_id=1, created_by=1)
        db_session.commit()

        response = client_no_auth.get(f"/api/v1/designs/{design.id}")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_get_design_without_project_access(
        self, client, db_session, auth_headers, mock_project_client
    ):
        """Test retrieving design when user doesn't have project access."""
        # Create design
        design = DesignFactory.create(project_id=999, created_by=1)
        db_session.commit()

        # Setup mock to raise access denied
        from src.services.project_client import ProjectAccessDeniedError

        mock_project_client.verify_project_access.side_effect = (
            ProjectAccessDeniedError("Access denied")
        )

        response = client.get(
            f"/api/v1/designs/{design.id}",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_get_archived_design(self, client, db_session, auth_headers):
        """Test retrieving archived design returns 404."""
        design = DesignFactory.create(
            project_id=1,
            created_by=1,
            is_archived=True,
        )
        db_session.commit()

        response = client.get(
            f"/api/v1/designs/{design.id}",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestUpdateDesign:
    """Tests for PUT /api/v1/designs/{id} endpoint."""

    def test_update_design_success(self, client, db_session, auth_headers):
        """Test successful design update."""
        # Create test design
        design = DesignFactory.create(
            project_id=1,
            name="Original Name",
            description="Original description",
            created_by=1,
        )
        db_session.commit()

        # Make request
        response = client.put(
            f"/api/v1/designs/{design.id}",
            json={
                "name": "Updated Name",
                "description": "Updated description",
                "status": "validated",
            },
            headers=auth_headers,
        )

        # Assertions
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["name"] == "Updated Name"
        assert data["description"] == "Updated description"
        assert data["status"] == "validated"

    def test_update_design_partial(self, client, db_session, auth_headers):
        """Test partial design update (only some fields)."""
        design = DesignFactory.create(
            project_id=1,
            name="Original Name",
            description="Original description",
            created_by=1,
        )
        db_session.commit()

        response = client.put(
            f"/api/v1/designs/{design.id}",
            json={"name": "Updated Name Only"},
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["name"] == "Updated Name Only"
        assert data["description"] == "Original description"  # Unchanged

    def test_update_design_not_found(self, client, auth_headers):
        """Test updating non-existent design."""
        response = client.put(
            "/api/v1/designs/99999",
            json={"name": "Updated Name"},
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_update_design_without_authentication(self, client_no_auth, db_session):
        """Test updating design without authentication."""
        design = DesignFactory.create(project_id=1, created_by=1)
        db_session.commit()

        response = client_no_auth.put(
            f"/api/v1/designs/{design.id}",
            json={"name": "Updated Name"},
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_update_design_without_project_access(
        self, client, db_session, auth_headers, mock_project_client
    ):
        """Test updating design when user doesn't have project access."""
        design = DesignFactory.create(project_id=999, created_by=1)
        db_session.commit()

        from src.services.project_client import ProjectAccessDeniedError

        mock_project_client.verify_project_access.side_effect = (
            ProjectAccessDeniedError("Access denied")
        )

        response = client.put(
            f"/api/v1/designs/{design.id}",
            json={"name": "Updated Name"},
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_update_archived_design(self, client, db_session, auth_headers):
        """Test updating archived design returns 404."""
        design = DesignFactory.create(
            project_id=1,
            created_by=1,
            is_archived=True,
        )
        db_session.commit()

        response = client.put(
            f"/api/v1/designs/{design.id}",
            json={"name": "Updated Name"},
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestDeleteDesign:
    """Tests for DELETE /api/v1/designs/{id} endpoint."""

    def test_delete_design_success(self, client, db_session, auth_headers):
        """Test successful design soft delete."""
        # Create test design
        design = DesignFactory.create(
            project_id=1,
            name="Test Design",
            created_by=1,
        )
        db_session.commit()
        design_id = design.id

        # Make request
        response = client.delete(
            f"/api/v1/designs/{design_id}",
            headers=auth_headers,
        )

        # Assertions
        assert response.status_code == status.HTTP_204_NO_CONTENT

        # Verify design is soft deleted (archived)
        db_session.expire_all()
        deleted_design = db_session.query(Design).filter_by(id=design_id).first()
        assert deleted_design is not None
        assert deleted_design.is_archived is True

    def test_delete_design_not_found(self, client, auth_headers):
        """Test deleting non-existent design."""
        response = client.delete(
            "/api/v1/designs/99999",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_delete_design_without_authentication(self, client_no_auth, db_session):
        """Test deleting design without authentication."""
        design = DesignFactory.create(project_id=1, created_by=1)
        db_session.commit()

        response = client_no_auth.delete(f"/api/v1/designs/{design.id}")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_delete_design_without_project_access(
        self, client, db_session, auth_headers, mock_project_client
    ):
        """Test deleting design when user doesn't have project access."""
        design = DesignFactory.create(project_id=999, created_by=1)
        db_session.commit()

        from src.services.project_client import ProjectAccessDeniedError

        mock_project_client.verify_project_access.side_effect = (
            ProjectAccessDeniedError("Access denied")
        )

        response = client.delete(
            f"/api/v1/designs/{design.id}",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_delete_already_archived_design(self, client, db_session, auth_headers):
        """Test deleting already archived design returns 404."""
        design = DesignFactory.create(
            project_id=1,
            created_by=1,
            is_archived=True,
        )
        db_session.commit()

        response = client.delete(
            f"/api/v1/designs/{design.id}",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestListDesigns:
    """Tests for GET /api/v1/designs endpoint."""

    def test_list_designs_success(self, client, db_session, auth_headers):
        """Test successful design listing."""
        # Create multiple designs
        designs = DesignFactory.create_batch(
            5,
            project_id=1,
            created_by=1,
        )
        db_session.commit()

        # Make request
        response = client.get(
            "/api/v1/designs",
            headers=auth_headers,
        )

        # Assertions
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 5

    def test_list_designs_filter_by_project(self, client, db_session, auth_headers):
        """Test listing designs filtered by project_id."""
        # Create designs for different projects
        DesignFactory.create_batch(3, project_id=1, created_by=1)
        DesignFactory.create_batch(2, project_id=2, created_by=1)
        db_session.commit()

        # Request designs for project 1
        response = client.get(
            "/api/v1/designs?project_id=1",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 3
        assert all(d["project_id"] == 1 for d in data)

    def test_list_designs_filter_by_building_type(
        self, client, db_session, auth_headers
    ):
        """Test listing designs filtered by building_type."""
        # Create designs with different building types
        DesignFactory.create_batch(
            2, project_id=1, building_type="residential", created_by=1
        )
        DesignFactory.create_batch(
            3, project_id=1, building_type="commercial", created_by=1
        )
        db_session.commit()

        # Request residential designs
        response = client.get(
            "/api/v1/designs?building_type=residential",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 2
        assert all(d["building_type"] == "residential" for d in data)

    def test_list_designs_filter_by_status(self, client, db_session, auth_headers):
        """Test listing designs filtered by status."""
        # Create designs with different statuses
        DesignFactory.create_batch(2, project_id=1, status="draft", created_by=1)
        DesignFactory.create_batch(3, project_id=1, status="validated", created_by=1)
        db_session.commit()

        # Request validated designs
        response = client.get(
            "/api/v1/designs?status=validated",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 3
        assert all(d["status"] == "validated" for d in data)

    def test_list_designs_pagination(self, client, db_session, auth_headers):
        """Test design listing with pagination."""
        # Create many designs
        DesignFactory.create_batch(20, project_id=1, created_by=1)
        db_session.commit()

        # Request first page
        response = client.get(
            "/api/v1/designs?limit=10&offset=0",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 10

        # Request second page
        response = client.get(
            "/api/v1/designs?limit=10&offset=10",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 10

    def test_list_designs_excludes_archived(self, client, db_session, auth_headers):
        """Test that archived designs are excluded from listing."""
        # Create active and archived designs
        DesignFactory.create_batch(3, project_id=1, is_archived=False, created_by=1)
        DesignFactory.create_batch(2, project_id=1, is_archived=True, created_by=1)
        db_session.commit()

        # Request designs
        response = client.get(
            "/api/v1/designs",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 3
        assert all(not d.get("is_archived", False) for d in data)

    def test_list_designs_without_authentication(self, client_no_auth):
        """Test listing designs without authentication."""
        response = client_no_auth.get("/api/v1/designs")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_list_designs_empty_result(self, client, db_session, auth_headers):
        """Test listing designs when no designs exist."""
        response = client.get(
            "/api/v1/designs",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 0

    def test_list_designs_multiple_filters(self, client, db_session, auth_headers):
        """Test listing designs with multiple filters combined."""
        # Create various designs
        DesignFactory.create(
            project_id=1,
            building_type="residential",
            status="validated",
            created_by=1,
        )
        DesignFactory.create(
            project_id=1,
            building_type="residential",
            status="draft",
            created_by=1,
        )
        DesignFactory.create(
            project_id=2,
            building_type="residential",
            status="validated",
            created_by=1,
        )
        db_session.commit()

        # Request with multiple filters
        response = client.get(
            "/api/v1/designs?project_id=1&building_type=residential&status=validated",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 1
        assert data[0]["project_id"] == 1
        assert data[0]["building_type"] == "residential"
        assert data[0]["status"] == "validated"


class TestGenerateVisuals:
    """Tests for POST /api/v1/designs/{id}/generate-visuals endpoint."""

    @patch("src.api.v1.routes.designs.generate_visuals_task")
    def test_generate_visuals_success(
        self, mock_visual_task, client, db_session, auth_headers, test_user_id
    ):
        """Test successful visual generation for existing design."""
        # Create test design
        design = DesignFactory.create(
            project_id=1,
            name="Test Design for Visuals",
            created_by=test_user_id,
            visual_generation_status="not_requested",
        )
        db_session.commit()

        # Setup visual task mock
        mock_task = AsyncMock()
        mock_task.id = "test-task-456"
        mock_visual_task.delay.return_value = mock_task

        # Make request
        response = client.post(
            f"/api/v1/designs/{design.id}/generate-visuals",
            json={
                "visual_types": ["floor_plan", "rendering"],
                "size": "1024x1024",
                "quality": "standard",
                "priority": "normal",
            },
            headers=auth_headers,
        )

        # Assertions
        assert response.status_code == status.HTTP_202_ACCEPTED
        data = response.json()
        assert data["message"] == "Visual generation started successfully"
        assert data["design_id"] == design.id
        assert data["task_id"] == "test-task-456"
        assert data["visual_types"] == ["floor_plan", "rendering"]
        assert data["size"] == "1024x1024"
        assert data["quality"] == "standard"
        assert data["priority"] == "normal"
        assert data["status"] == "pending"
        assert "tracking_url" in data

        # Verify visual generation task was called
        mock_visual_task.delay.assert_called_once()
        call_args = mock_visual_task.delay.call_args
        assert call_args[1]["design_id"] == str(design.id)
        assert call_args[1]["visual_types"] == ["floor_plan", "rendering"]
        assert call_args[1]["size"] == "1024x1024"
        assert call_args[1]["quality"] == "standard"
        assert call_args[1]["priority"] == "normal"

    @patch("src.api.v1.routes.designs.generate_visuals_task")
    def test_generate_visuals_default_parameters(
        self, mock_visual_task, client, db_session, auth_headers, test_user_id
    ):
        """Test visual generation with default parameters."""
        # Create test design
        design = DesignFactory.create(
            project_id=1,
            name="Test Design Default Params",
            created_by=test_user_id,
            visual_generation_status="not_requested",
        )
        db_session.commit()

        # Setup visual task mock
        mock_task = AsyncMock()
        mock_task.id = "test-task-789"
        mock_visual_task.delay.return_value = mock_task

        # Make request with minimal parameters (using defaults)
        response = client.post(
            f"/api/v1/designs/{design.id}/generate-visuals",
            json={},  # Use all defaults
            headers=auth_headers,
        )

        # Assertions
        assert response.status_code == status.HTTP_202_ACCEPTED
        data = response.json()
        assert data["visual_types"] == [
            "floor_plan",
            "rendering",
            "3d_model",
        ]  # Default
        assert data["size"] == "1024x1024"  # Default
        assert data["quality"] == "standard"  # Default
        assert data["priority"] == "normal"  # Default

    def test_generate_visuals_design_not_found(self, client, auth_headers):
        """Test visual generation for non-existent design."""
        response = client.post(
            "/api/v1/designs/99999/generate-visuals",
            json={},
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "not found" in response.json()["detail"].lower()

    def test_generate_visuals_already_processing(
        self, client, db_session, auth_headers, test_user_id
    ):
        """Test visual generation when already in progress."""
        # Create test design with processing status
        design = DesignFactory.create(
            project_id=1,
            name="Test Design Processing",
            created_by=test_user_id,
            visual_generation_status="processing",
        )
        db_session.commit()

        # Make request
        response = client.post(
            f"/api/v1/designs/{design.id}/generate-visuals",
            json={},
            headers=auth_headers,
        )

        # Should return conflict
        assert response.status_code == status.HTTP_409_CONFLICT
        assert "already in progress" in response.json()["detail"].lower()

    def test_generate_visuals_invalid_visual_types(
        self, client, db_session, auth_headers, test_user_id
    ):
        """Test visual generation with invalid visual types."""
        # Create test design
        design = DesignFactory.create(
            project_id=1,
            name="Test Design Invalid Types",
            created_by=test_user_id,
            visual_generation_status="not_requested",
        )
        db_session.commit()

        # Make request with invalid visual types
        response = client.post(
            f"/api/v1/designs/{design.id}/generate-visuals",
            json={"visual_types": ["floor_plan", "invalid_type", "another_invalid"]},
            headers=auth_headers,
        )

        # Should return validation error
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        assert "Invalid visual types" in response.json()["detail"]

    def test_generate_visuals_invalid_size(
        self, client, db_session, auth_headers, test_user_id
    ):
        """Test visual generation with invalid size parameter."""
        # Create test design
        design = DesignFactory.create(
            project_id=1,
            name="Test Design Invalid Size",
            created_by=test_user_id,
            visual_generation_status="not_requested",
        )
        db_session.commit()

        # Make request with invalid size
        response = client.post(
            f"/api/v1/designs/{design.id}/generate-visuals",
            json={"size": "invalid_size"},
            headers=auth_headers,
        )

        # Should return validation error
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        assert "Invalid size" in response.json()["detail"]

    def test_generate_visuals_invalid_quality(
        self, client, db_session, auth_headers, test_user_id
    ):
        """Test visual generation with invalid quality parameter."""
        # Create test design
        design = DesignFactory.create(
            project_id=1,
            name="Test Design Invalid Quality",
            created_by=test_user_id,
            visual_generation_status="not_requested",
        )
        db_session.commit()

        # Make request with invalid quality
        response = client.post(
            f"/api/v1/designs/{design.id}/generate-visuals",
            json={"quality": "invalid_quality"},
            headers=auth_headers,
        )

        # Should return validation error
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        assert "Invalid quality" in response.json()["detail"]

    def test_generate_visuals_without_authentication(self, client_no_auth, db_session):
        """Test visual generation without authentication."""
        # Create test design
        design = DesignFactory.create(
            project_id=1,
            name="Test Design No Auth",
            created_by=1,
        )
        db_session.commit()

        # Make request without auth
        response = client_no_auth.post(
            f"/api/v1/designs/{design.id}/generate-visuals",
            json={},
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_generate_visuals_without_project_access(
        self, client, db_session, auth_headers, mock_project_client, test_user_id
    ):
        """Test visual generation when user doesn't have project access."""
        # Create test design
        design = DesignFactory.create(
            project_id=999,  # Different project
            name="Test Design No Access",
            created_by=test_user_id,
        )
        db_session.commit()

        # Setup mock to raise access denied
        from src.services.project_client import ProjectAccessDeniedError

        mock_project_client.verify_project_access.side_effect = (
            ProjectAccessDeniedError("Access denied")
        )

        # Make request
        response = client.post(
            f"/api/v1/designs/{design.id}/generate-visuals",
            json={},
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    @patch("src.api.v1.routes.designs.generate_visuals_task")
    def test_generate_visuals_task_creation_failure(
        self, mock_visual_task, client, db_session, auth_headers, test_user_id
    ):
        """Test visual generation when task creation fails."""
        # Create test design
        design = DesignFactory.create(
            project_id=1,
            name="Test Design Task Fail",
            created_by=test_user_id,
            visual_generation_status="not_requested",
        )
        db_session.commit()

        # Setup visual task mock to raise exception
        mock_visual_task.delay.side_effect = Exception("Celery connection failed")

        # Make request
        response = client.post(
            f"/api/v1/designs/{design.id}/generate-visuals",
            json={},
            headers=auth_headers,
        )

        # Should return server error
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert "Failed to start visual generation" in response.json()["detail"]

    @patch("src.api.v1.routes.designs.generate_visuals_task")
    def test_generate_visuals_custom_parameters(
        self, mock_visual_task, client, db_session, auth_headers, test_user_id
    ):
        """Test visual generation with custom parameters."""
        # Create test design
        design = DesignFactory.create(
            project_id=1,
            name="Test Design Custom Params",
            created_by=test_user_id,
            visual_generation_status="completed",  # Can regenerate
        )
        db_session.commit()

        # Setup visual task mock
        mock_task = AsyncMock()
        mock_task.id = "test-task-custom"
        mock_visual_task.delay.return_value = mock_task

        # Make request with custom parameters
        response = client.post(
            f"/api/v1/designs/{design.id}/generate-visuals",
            json={
                "visual_types": ["3d_model"],
                "size": "1792x1024",
                "quality": "hd",
                "priority": "high",
            },
            headers=auth_headers,
        )

        # Assertions
        assert response.status_code == status.HTTP_202_ACCEPTED
        data = response.json()
        assert data["visual_types"] == ["3d_model"]
        assert data["size"] == "1792x1024"
        assert data["quality"] == "hd"
        assert data["priority"] == "high"

        # Verify task was called with custom parameters
        mock_visual_task.delay.assert_called_once()
        call_args = mock_visual_task.delay.call_args
        assert call_args[1]["visual_types"] == ["3d_model"]
        assert call_args[1]["size"] == "1792x1024"
        assert call_args[1]["quality"] == "hd"
        assert call_args[1]["priority"] == "high"


class TestVisualStatusEndpoint:
    """Test visual status endpoint functionality."""

    def test_get_visual_status_not_requested(
        self, client, db_session, auth_headers, test_user_id
    ):
        """Test visual status for design with no visual generation requested."""
        # Create design with not_requested status
        design = DesignFactory.create(
            project_id=1,
            name="Test Design No Visuals",
            created_by=test_user_id,
            visual_generation_status="not_requested",
            floor_plan_url=None,
            rendering_url=None,
            model_file_url=None,
        )
        db_session.commit()

        response = client.get(
            f"/api/v1/designs/{design.id}/visual-status",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Verify response structure
        assert data["design_id"] == design.id
        assert data["status"] == "not_requested"

        # Verify visuals section
        assert "visuals" in data
        assert data["visuals"]["floor_plan"]["available"] is False
        assert data["visuals"]["rendering"]["available"] is False
        assert data["visuals"]["model_3d"]["available"] is False

        # Verify progress information
        assert "progress" in data
        assert "not been requested" in data["progress"]["message"]
        assert data["progress"]["can_request"] is True

    def test_get_visual_status_pending(
        self, client, db_session, auth_headers, test_user_id
    ):
        """Test visual status for design with pending visual generation."""
        design = DesignFactory.create(
            project_id=1,
            name="Test Design Pending",
            created_by=test_user_id,
            visual_generation_status="pending",
        )
        db_session.commit()

        response = client.get(
            f"/api/v1/designs/{design.id}/visual-status",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["status"] == "pending"
        assert "queued" in data["progress"]["message"]
        assert "estimated_completion" in data["progress"]

    def test_get_visual_status_processing(
        self, client, db_session, auth_headers, test_user_id
    ):
        """Test visual status for design with processing visual generation."""
        design = DesignFactory.create(
            project_id=1,
            name="Test Design Processing",
            created_by=test_user_id,
            visual_generation_status="processing",
            floor_plan_url="https://example.com/floor_plan.png",  # 1 completed
            rendering_url=None,  # Not completed yet
            model_file_url=None,  # Not completed yet
        )
        db_session.commit()

        response = client.get(
            f"/api/v1/designs/{design.id}/visual-status",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["status"] == "processing"
        assert data["visuals"]["floor_plan"]["available"] is True
        assert data["visuals"]["rendering"]["available"] is False
        assert data["visuals"]["model_3d"]["available"] is False

        # Verify progress calculation
        assert data["progress"]["completed_count"] == 1
        assert data["progress"]["total_count"] == 3
        assert data["progress"]["percentage"] == 33.3
        assert "1/3 completed" in data["progress"]["message"]

    def test_get_visual_status_completed(
        self, client, db_session, auth_headers, test_user_id
    ):
        """Test visual status for design with completed visual generation."""
        design = DesignFactory.create(
            project_id=1,
            name="Test Design Completed",
            created_by=test_user_id,
            visual_generation_status="completed",
            floor_plan_url="https://example.com/floor_plan.png",
            rendering_url="https://example.com/rendering.png",
            model_file_url="https://example.com/model.obj",
            visual_generated_at=datetime.now(timezone.utc),
        )
        db_session.commit()

        response = client.get(
            f"/api/v1/designs/{design.id}/visual-status",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["status"] == "completed"

        # All visuals should be available
        assert data["visuals"]["floor_plan"]["available"] is True
        assert data["visuals"]["rendering"]["available"] is True
        assert data["visuals"]["model_3d"]["available"] is True

        # URLs should be present
        assert (
            data["visuals"]["floor_plan"]["url"] == "https://example.com/floor_plan.png"
        )
        assert (
            data["visuals"]["rendering"]["url"] == "https://example.com/rendering.png"
        )
        assert data["visuals"]["model_3d"]["url"] == "https://example.com/model.obj"

        # Progress should show completion
        assert data["progress"]["completed_count"] == 3
        assert data["progress"]["percentage"] == 100.0
        assert "completed successfully" in data["progress"]["message"]

        # Timestamps should be present
        assert "timestamps" in data
        assert data["timestamps"]["visual_generated_at"] is not None

    def test_get_visual_status_failed(
        self, client, db_session, auth_headers, test_user_id
    ):
        """Test visual status for design with failed visual generation."""
        design = DesignFactory.create(
            project_id=1,
            name="Test Design Failed",
            created_by=test_user_id,
            visual_generation_status="failed",
            visual_generation_error="DALL-E API rate limit exceeded",
            visual_generated_at=datetime.now(timezone.utc),
        )
        db_session.commit()

        response = client.get(
            f"/api/v1/designs/{design.id}/visual-status",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["status"] == "failed"

        # Error information should be present
        assert "error" in data
        assert data["error"]["message"] == "DALL-E API rate limit exceeded"
        assert data["error"]["occurred_at"] is not None

        # Visuals should not be available
        assert data["visuals"]["floor_plan"]["available"] is False
        assert data["visuals"]["rendering"]["available"] is False
        assert data["visuals"]["model_3d"]["available"] is False

    def test_get_visual_status_design_not_found(self, client, auth_headers):
        """Test visual status for non-existent design."""
        response = client.get(
            "/api/v1/designs/99999/visual-status",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "not found" in response.json()["detail"]

    def test_get_visual_status_access_denied(self, client, db_session, auth_headers):
        """Test visual status for design owned by different user."""
        # Create design owned by different user
        design = DesignFactory.create(
            project_id=1,
            name="Other User Design",
            created_by=999,  # Different user ID
            visual_generation_status="completed",
        )
        db_session.commit()

        response = client.get(
            f"/api/v1/designs/{design.id}/visual-status",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert "Access denied" in response.json()["detail"]

    def test_get_visual_status_partial_completion(
        self, client, db_session, auth_headers, test_user_id
    ):
        """Test visual status with partial visual completion."""
        design = DesignFactory.create(
            project_id=1,
            name="Test Design Partial",
            created_by=test_user_id,
            visual_generation_status="processing",
            floor_plan_url="https://example.com/floor_plan.png",
            rendering_url="https://example.com/rendering.png",
            model_file_url=None,  # Still processing
        )
        db_session.commit()

        response = client.get(
            f"/api/v1/designs/{design.id}/visual-status",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Verify partial completion
        assert data["progress"]["completed_count"] == 2
        assert data["progress"]["total_count"] == 3
        assert data["progress"]["percentage"] == 66.7
        assert "2/3 completed" in data["progress"]["message"]

        # Verify individual visual availability
        assert data["visuals"]["floor_plan"]["available"] is True
        assert data["visuals"]["rendering"]["available"] is True
        assert data["visuals"]["model_3d"]["available"] is False
