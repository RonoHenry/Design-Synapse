"""
Comprehensive backward compatibility tests for visual generation enhancements.

Tests ensure that all visual generation features are backward compatible with:
- Existing API contracts
- Legacy designs without visual fields
- Existing client integrations
- Database migration compatibility
- Response schema compatibility

Requirements: 10 (Backward compatibility maintained)
Target: 8+ comprehensive backward compatibility tests
"""

import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from fastapi import status
from src.models.design import Design

from tests.factories import DesignFactory


class TestAPIBackwardCompatibility:
    """Tests for API backward compatibility with existing client integrations."""

    def test_design_response_schema_backward_compatibility(
        self, client, db_session, auth_headers, test_user_id
    ):
        """Test that design response schema maintains backward compatibility."""
        # Create legacy design (without visual fields)
        design = DesignFactory.create(
            project_id=1,
            name="Legacy API Test",
            description="Test design for API compatibility",
            building_type="residential",
            created_by=test_user_id,
            # Legacy designs would have these as None/default
            visual_generation_status="not_requested",
            floor_plan_url=None,
            rendering_url=None,
            model_file_url=None,
            visual_generated_at=None,
            visual_generation_error=None,
        )
        db_session.commit()

        # Get design via API
        response = client.get(
            f"/api/v1/designs/{design.id}",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Verify all original fields are present
        required_legacy_fields = [
            "id",
            "name",
            "description",
            "building_type",
            "project_id",
            "status",
            "created_at",
            "updated_at",
            "created_by",
        ]

        for field in required_legacy_fields:
            assert field in data, f"Legacy field '{field}' missing from response"

        # Verify new visual fields are present but null/default
        assert "visual_generation_status" in data
        assert data["visual_generation_status"] == "not_requested"
        assert data.get("floor_plan_url") is None
        assert data.get("rendering_url") is None
        assert data.get("model_file_url") is None

        # Verify response can be serialized (client compatibility)
        json_str = json.dumps(data)
        parsed_data = json.loads(json_str)
        assert parsed_data["id"] == design.id

    def test_design_list_response_backward_compatibility(
        self, client, db_session, auth_headers, test_user_id
    ):
        """Test that design list response maintains backward compatibility."""
        # Create mix of legacy and new designs
        legacy_design = DesignFactory.create(
            project_id=1,
            name="Legacy Design",
            created_by=test_user_id,
            visual_generation_status="not_requested",
        )

        modern_design = DesignFactory.create(
            project_id=1,
            name="Modern Design",
            created_by=test_user_id,
            visual_generation_status="completed",
            floor_plan_url="https://cdn.example.com/floor_plan.jpg",
        )
        db_session.commit()

        # Get design list
        response = client.get("/api/v1/designs", headers=auth_headers)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 2

        # Verify both legacy and modern designs are properly serialized
        design_names = [d["name"] for d in data]
        assert "Legacy Design" in design_names
        assert "Modern Design" in design_names

        # Verify all designs have consistent schema
        for design_data in data:
            assert "visual_generation_status" in design_data
            assert design_data["visual_generation_status"] in [
                "not_requested",
                "pending",
                "processing",
                "completed",
                "failed",
            ]

    def test_design_creation_without_visual_fields(
        self, client, db_session, auth_headers, test_user_id
    ):
        """Test that design creation works without specifying visual fields."""
        # Create design using legacy API call (no visual fields)
        with patch(
            "src.services.design_generator.DesignGeneratorService.generate_design"
        ) as mock_generate:
            design = DesignFactory.create(
                project_id=1,
                name="Legacy Creation Test",
                created_by=test_user_id,
            )
            db_session.commit()
            mock_generate.return_value = design

            response = client.post(
                "/api/v1/designs",
                json={
                    "project_id": 1,
                    "name": "Legacy Creation Test",
                    "description": "Test legacy design creation",
                    "building_type": "residential",
                    "requirements": {"num_floors": 1},
                    # Note: NOT including generate_visuals field
                },
                headers=auth_headers,
            )

            assert response.status_code == status.HTTP_201_CREATED
            data = response.json()
            assert data["name"] == "Legacy Creation Test"
            assert data["visual_generation_status"] == "not_requested"

    def test_design_update_preserves_visual_fields(
        self, client, db_session, auth_headers, test_user_id
    ):
        """Test that design updates preserve existing visual fields."""
        # Create design with visual fields
        design = DesignFactory.create(
            project_id=1,
            name="Update Test Design",
            created_by=test_user_id,
            visual_generation_status="completed",
            floor_plan_url="https://cdn.example.com/original_floor_plan.jpg",
            rendering_url="https://cdn.example.com/original_rendering.jpg",
        )
        db_session.commit()

        # Update design using legacy update (no visual fields in request)
        response = client.put(
            f"/api/v1/designs/{design.id}",
            json={
                "name": "Updated Design Name",
                "description": "Updated description",
            },
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Verify update worked
        assert data["name"] == "Updated Design Name"
        assert data["description"] == "Updated description"

        # Verify visual fields were preserved
        assert data["visual_generation_status"] == "completed"
        assert (
            data["floor_plan_url"] == "https://cdn.example.com/original_floor_plan.jpg"
        )
        assert data["rendering_url"] == "https://cdn.example.com/original_rendering.jpg"


class TestDatabaseMigrationCompatibility:
    """Tests for database migration compatibility with existing data."""

    def test_existing_designs_after_migration(
        self, client, db_session, auth_headers, test_user_id
    ):
        """Test that existing designs work correctly after visual fields migration."""
        # Simulate pre-migration design by creating with minimal visual fields
        design = Design(
            project_id=1,
            name="Pre-Migration Design",
            description="Design created before visual fields migration",
            building_type="commercial",
            status="validated",
            created_by=test_user_id,
            specification={"building_info": {"type": "commercial"}},  # Required field
            # Visual fields would be NULL in pre-migration database
            visual_generation_status="not_requested",  # Default after migration
            floor_plan_url=None,
            rendering_url=None,
            model_file_url=None,
            visual_generated_at=None,
            visual_generation_error=None,
        )
        db_session.add(design)
        db_session.commit()

        # Verify design can be retrieved
        response = client.get(f"/api/v1/designs/{design.id}", headers=auth_headers)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["name"] == "Pre-Migration Design"
        assert data["visual_generation_status"] == "not_requested"

        # Verify design can be updated
        update_response = client.put(
            f"/api/v1/designs/{design.id}",
            json={"status": "approved"},
            headers=auth_headers,
        )

        assert update_response.status_code == status.HTTP_200_OK
        assert update_response.json()["status"] == "approved"

        # Verify visual generation can be requested
        with patch("src.api.v1.routes.designs.generate_visuals_task") as mock_task:
            mock_task.delay.return_value = AsyncMock(id=str(uuid4()))

            visual_response = client.post(
                f"/api/v1/designs/{design.id}/generate-visuals",
                json={},
                headers=auth_headers,
            )

            assert visual_response.status_code == status.HTTP_202_ACCEPTED

    def test_design_model_field_defaults(self, db_session):
        """Test that Design model handles missing visual fields gracefully."""
        # Create design with minimal required fields (simulating old data)
        design = Design(
            project_id=1,
            name="Minimal Design",
            description="Design with minimal fields",
            building_type="residential",
            status="draft",
            created_by=1,
            specification={"building_info": {"type": "residential"}},  # Required field
        )

        # Don't set visual fields explicitly
        db_session.add(design)
        db_session.commit()

        # Retrieve and verify defaults
        retrieved_design = db_session.query(Design).filter_by(id=design.id).first()

        assert retrieved_design is not None
        assert retrieved_design.visual_generation_status == "not_requested"
        assert retrieved_design.floor_plan_url is None
        assert retrieved_design.rendering_url is None
        assert retrieved_design.model_file_url is None
        assert retrieved_design.visual_generated_at is None
        assert retrieved_design.visual_generation_error is None

    def test_design_serialization_with_null_visual_fields(self, db_session):
        """Test that designs with NULL visual fields serialize correctly."""
        # Create design with explicit NULL visual fields
        design = DesignFactory.create(
            project_id=1,
            name="Null Fields Design",
            visual_generation_status="not_requested",
            floor_plan_url=None,
            rendering_url=None,
            model_file_url=None,
            visual_generated_at=None,
            visual_generation_error=None,
        )
        db_session.commit()

        # Test to_dict method
        design_dict = design.to_dict()

        assert design_dict["visual_generation_status"] == "not_requested"
        assert design_dict["floor_plan_url"] is None
        assert design_dict["rendering_url"] is None
        assert design_dict["model_file_url"] is None

        # Verify JSON serialization works
        json_str = json.dumps(design_dict, default=str)
        parsed = json.loads(json_str)
        assert parsed["name"] == "Null Fields Design"


class TestClientIntegrationCompatibility:
    """Tests for compatibility with existing client integration patterns."""

    def test_existing_client_workflow_compatibility(
        self, client, db_session, auth_headers, test_user_id
    ):
        """Test that existing client workflows continue to work."""
        # Simulate typical client workflow: create → get → update → list

        # Step 1: Create design (legacy client - no visual fields)
        with patch(
            "src.services.design_generator.DesignGeneratorService.generate_design"
        ) as mock_generate:
            design = DesignFactory.create(
                project_id=1,
                name="Client Workflow Test",
                created_by=test_user_id,
            )
            db_session.commit()
            mock_generate.return_value = design

            create_response = client.post(
                "/api/v1/designs",
                json={
                    "project_id": 1,
                    "name": "Client Workflow Test",
                    "description": "Testing client workflow",
                    "building_type": "residential",
                    "requirements": {},
                },
                headers=auth_headers,
            )

            assert create_response.status_code == status.HTTP_201_CREATED
            design_id = create_response.json()["id"]

        # Step 2: Get design
        get_response = client.get(f"/api/v1/designs/{design_id}", headers=auth_headers)
        assert get_response.status_code == status.HTTP_200_OK

        # Step 3: Update design
        update_response = client.put(
            f"/api/v1/designs/{design_id}",
            json={"status": "validated"},
            headers=auth_headers,
        )
        assert update_response.status_code == status.HTTP_200_OK

        # Step 4: List designs
        list_response = client.get("/api/v1/designs", headers=auth_headers)
        assert list_response.status_code == status.HTTP_200_OK

        # Verify design appears in list
        designs = list_response.json()
        design_names = [d["name"] for d in designs]
        assert "Client Workflow Test" in design_names

    def test_response_field_access_patterns(
        self, client, db_session, auth_headers, test_user_id
    ):
        """Test that common client field access patterns work."""
        # Create design
        design = DesignFactory.create(
            project_id=1,
            name="Field Access Test",
            created_by=test_user_id,
            visual_generation_status="completed",
            floor_plan_url="https://cdn.example.com/floor_plan.jpg",
        )
        db_session.commit()

        response = client.get(f"/api/v1/designs/{design.id}", headers=auth_headers)
        data = response.json()

        # Test common field access patterns that clients might use

        # Direct field access
        assert data["name"] == "Field Access Test"
        assert data["project_id"] == 1

        # Safe field access with get() method simulation
        assert data.get("visual_generation_status") == "completed"
        assert data.get("floor_plan_url") == "https://cdn.example.com/floor_plan.jpg"
        assert data.get("nonexistent_field") is None

        # Boolean checks that clients might do
        has_floor_plan = bool(data.get("floor_plan_url"))
        assert has_floor_plan is True

        has_rendering = bool(data.get("rendering_url"))
        assert has_rendering is False  # This design doesn't have rendering

    def test_filtering_and_pagination_compatibility(
        self, client, db_session, auth_headers, test_user_id
    ):
        """Test that existing filtering and pagination still works."""
        # Create mix of designs
        designs = [
            DesignFactory.create(
                project_id=1,
                name=f"Filter Test {i}",
                building_type="residential" if i % 2 == 0 else "commercial",
                status="draft" if i < 3 else "validated",
                created_by=test_user_id,
                visual_generation_status="not_requested",
            )
            for i in range(6)
        ]
        db_session.commit()

        # Test project filtering
        response = client.get("/api/v1/designs?project_id=1", headers=auth_headers)
        assert response.status_code == status.HTTP_200_OK
        assert len(response.json()) >= 6

        # Test building type filtering
        response = client.get(
            "/api/v1/designs?building_type=residential", headers=auth_headers
        )
        assert response.status_code == status.HTTP_200_OK
        residential_designs = response.json()
        assert all(d["building_type"] == "residential" for d in residential_designs)

        # Test status filtering
        response = client.get("/api/v1/designs?status=validated", headers=auth_headers)
        assert response.status_code == status.HTTP_200_OK
        validated_designs = response.json()
        assert all(d["status"] == "validated" for d in validated_designs)

        # Test pagination
        response = client.get("/api/v1/designs?limit=3&offset=0", headers=auth_headers)
        assert response.status_code == status.HTTP_200_OK
        page1 = response.json()
        assert len(page1) <= 3

        response = client.get("/api/v1/designs?limit=3&offset=3", headers=auth_headers)
        assert response.status_code == status.HTTP_200_OK
        page2 = response.json()

        # Verify different results (no overlap)
        page1_ids = {d["id"] for d in page1}
        page2_ids = {d["id"] for d in page2}
        assert page1_ids.isdisjoint(page2_ids)


class TestSchemaCompatibility:
    """Tests for response schema compatibility with existing clients."""

    def test_design_response_schema_evolution(
        self, client, db_session, auth_headers, test_user_id
    ):
        """Test that schema evolution maintains compatibility."""
        # Create design with all visual fields
        design = DesignFactory.create(
            project_id=1,
            name="Schema Evolution Test",
            created_by=test_user_id,
            visual_generation_status="completed",
            floor_plan_url="https://cdn.example.com/floor_plan.jpg",
            rendering_url="https://cdn.example.com/rendering.jpg",
            model_file_url="https://cdn.example.com/model.obj",
            visual_generated_at=datetime.now(timezone.utc),
        )
        db_session.commit()

        response = client.get(f"/api/v1/designs/{design.id}", headers=auth_headers)
        data = response.json()

        # Verify schema structure
        assert isinstance(data, dict)

        # Core fields (always present)
        core_fields = [
            "id",
            "name",
            "description",
            "building_type",
            "project_id",
            "status",
        ]
        for field in core_fields:
            assert field in data
            assert data[field] is not None

        # Timestamp fields (always present)
        timestamp_fields = ["created_at", "updated_at"]
        for field in timestamp_fields:
            assert field in data
            assert isinstance(data[field], str)  # ISO format string

        # Visual fields (may be null)
        visual_fields = [
            "visual_generation_status",
            "floor_plan_url",
            "rendering_url",
            "model_file_url",
            "visual_generated_at",
            "visual_generation_error",
        ]
        for field in visual_fields:
            assert field in data  # Field exists
            # Value may be null, which is fine

    def test_error_response_compatibility(self, client, auth_headers):
        """Test that error responses maintain expected format."""
        # Test 404 error format
        response = client.get("/api/v1/designs/99999", headers=auth_headers)

        assert response.status_code == status.HTTP_404_NOT_FOUND
        error_data = response.json()

        # Verify error response structure (may use custom error format)
        assert "detail" in error_data or "message" in error_data
        if "detail" in error_data:
            assert isinstance(error_data["detail"], str)
            assert "not found" in error_data["detail"].lower()
        else:
            assert isinstance(error_data["message"], str)
            assert "not found" in error_data["message"].lower()

        # Test 422 validation error format
        response = client.post(
            "/api/v1/designs",
            json={"invalid": "data"},  # Missing required fields
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        error_data = response.json()

        # Validation error format should be maintained (may use custom format)
        assert (
            "detail" in error_data or "details" in error_data or "message" in error_data
        )

    def test_content_type_compatibility(
        self, client, db_session, auth_headers, test_user_id
    ):
        """Test that content types remain consistent."""
        design = DesignFactory.create(
            project_id=1,
            name="Content Type Test",
            created_by=test_user_id,
        )
        db_session.commit()

        # Test GET response content type
        response = client.get(f"/api/v1/designs/{design.id}", headers=auth_headers)

        assert response.status_code == status.HTTP_200_OK
        assert response.headers["content-type"] == "application/json"

        # Test POST response content type
        with patch(
            "src.services.design_generator.DesignGeneratorService.generate_design"
        ) as mock_generate:
            new_design = DesignFactory.create(
                project_id=1,
                name="New Design",
                created_by=test_user_id,
            )
            db_session.commit()
            mock_generate.return_value = new_design

            response = client.post(
                "/api/v1/designs",
                json={
                    "project_id": 1,
                    "name": "New Design",
                    "description": "Test design",
                    "building_type": "residential",
                    "requirements": {},
                },
                headers=auth_headers,
            )

            assert response.status_code == status.HTTP_201_CREATED
            assert response.headers["content-type"] == "application/json"


class TestPerformanceCompatibility:
    """Tests that performance characteristics remain acceptable for existing clients."""

    def test_response_time_compatibility(
        self, client, db_session, auth_headers, test_user_id
    ):
        """Test that response times haven't degraded significantly."""
        import time

        # Create test design
        design = DesignFactory.create(
            project_id=1,
            name="Performance Test",
            created_by=test_user_id,
            visual_generation_status="completed",
            floor_plan_url="https://cdn.example.com/floor_plan.jpg",
        )
        db_session.commit()

        # Test GET performance
        start_time = time.time()
        response = client.get(f"/api/v1/designs/{design.id}", headers=auth_headers)
        end_time = time.time()

        assert response.status_code == status.HTTP_200_OK
        response_time = end_time - start_time

        # Response should be under 1 second (reasonable for API)
        assert (
            response_time < 1.0
        ), f"GET response took {response_time:.2f}s, expected < 1.0s"

        # Test LIST performance with multiple designs
        designs = DesignFactory.create_batch(
            20,
            project_id=1,
            created_by=test_user_id,
        )
        db_session.commit()

        start_time = time.time()
        response = client.get("/api/v1/designs?limit=20", headers=auth_headers)
        end_time = time.time()

        assert response.status_code == status.HTTP_200_OK
        response_time = end_time - start_time

        # List response should be under 2 seconds even with 20+ designs
        assert (
            response_time < 2.0
        ), f"LIST response took {response_time:.2f}s, expected < 2.0s"

    def test_payload_size_compatibility(
        self, client, db_session, auth_headers, test_user_id
    ):
        """Test that response payload sizes remain reasonable."""
        # Create design with all visual fields populated
        design = DesignFactory.create(
            project_id=1,
            name="Payload Size Test",
            description="A" * 500,  # Longer description
            created_by=test_user_id,
            visual_generation_status="completed",
            floor_plan_url="https://cdn.example.com/very/long/path/to/floor_plan.jpg",
            rendering_url="https://cdn.example.com/very/long/path/to/rendering.jpg",
            model_file_url="https://cdn.example.com/very/long/path/to/model.obj",
        )
        db_session.commit()

        response = client.get(f"/api/v1/designs/{design.id}", headers=auth_headers)

        assert response.status_code == status.HTTP_200_OK

        # Check response size (should be reasonable for JSON)
        response_size = len(response.content)

        # Response should be under 10KB for a single design (very generous limit)
        assert (
            response_size < 10240
        ), f"Response size {response_size} bytes, expected < 10KB"

        # Verify response is still valid JSON
        data = response.json()
        assert data["name"] == "Payload Size Test"
        assert len(data["description"]) == 500
