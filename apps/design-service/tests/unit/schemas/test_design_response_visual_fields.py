"""
Unit tests for DesignResponse schema visual fields.

Tests serialization of visual output fields in DesignResponse schema,
ensuring proper field mapping and backward compatibility.

Requirements tested:
- 10: Visual output generation and storage
"""

import pytest
from datetime import datetime, timezone

from src.api.v1.schemas.responses import DesignResponse
from tests.factories import DesignFactory


class TestDesignResponseVisualFields:
    """Test DesignResponse schema visual fields serialization."""

    def test_design_response_with_visual_fields(self, db_session):
        """Test DesignResponse serialization with visual output fields."""
        # Arrange
        visual_generated_at = datetime.now(timezone.utc)
        design = DesignFactory.create(
            name="Test Design with Visuals",
            description="A design with visual outputs",
            project_id=1,
            building_type="residential",
            floor_plan_url="https://cdn.example.com/floor_plan_123.png",
            rendering_url="https://cdn.example.com/rendering_123.png",
            model_file_url="https://cdn.example.com/model_123.step",
            visual_generation_status="completed",
            visual_generation_error=None,
            visual_generated_at=visual_generated_at
        )

        # Act
        response = DesignResponse.model_validate(design)

        # Assert
        assert response.floor_plan_url == "https://cdn.example.com/floor_plan_123.png"
        assert response.rendering_url == "https://cdn.example.com/rendering_123.png"
        assert response.model_file_url == "https://cdn.example.com/model_123.step"
        assert response.visual_generation_status == "completed"
        assert response.visual_generation_error is None
        # Compare datetime without timezone info (database stores naive datetime)
        assert response.visual_generated_at.replace(tzinfo=None) == visual_generated_at.replace(tzinfo=None)

    def test_design_response_without_visual_fields(self, db_session):
        """Test DesignResponse serialization without visual fields (backward compatibility)."""
        # Arrange
        design = DesignFactory.create(
            name="Test Design without Visuals",
            description="A design without visual outputs",
            project_id=1,
            building_type="residential"
            # No visual fields provided - should use defaults
        )

        # Act
        response = DesignResponse.model_validate(design)

        # Assert - should have default/null values
        assert response.floor_plan_url is None
        assert response.rendering_url is None
        assert response.model_file_url is None
        assert response.visual_generation_status == "not_requested"  # Default value
        assert response.visual_generation_error is None
        assert response.visual_generated_at is None

    def test_design_response_with_partial_visual_fields(self, db_session):
        """Test DesignResponse serialization with partial visual fields."""
        # Arrange
        design = DesignFactory.create(
            name="Test Design Partial Visuals",
            description="A design with some visual outputs",
            project_id=1,
            building_type="residential",
            floor_plan_url="https://cdn.example.com/floor_plan.png",
            visual_generation_status="processing",
            visual_generation_error="Generation in progress"
            # Other visual fields not provided
        )

        # Act
        response = DesignResponse.model_validate(design)

        # Assert
        assert response.floor_plan_url == "https://cdn.example.com/floor_plan.png"
        assert response.rendering_url is None
        assert response.model_file_url is None
        assert response.visual_generation_status == "processing"
        assert response.visual_generation_error == "Generation in progress"
        assert response.visual_generated_at is None

    def test_design_response_visual_fields_serialization(self, db_session):
        """Test that visual fields are included in JSON serialization."""
        # Arrange
        design = DesignFactory.create(
            name="Serialization Test",
            project_id=1,
            building_type="residential",
            floor_plan_url="https://cdn.example.com/floor_plan.png",
            rendering_url="https://cdn.example.com/rendering.png",
            visual_generation_status="completed"
        )

        # Act
        response = DesignResponse.model_validate(design)
        json_data = response.model_dump()

        # Assert
        assert "floor_plan_url" in json_data
        assert "rendering_url" in json_data
        assert "model_file_url" in json_data
        assert "visual_generation_status" in json_data
        assert "visual_generation_error" in json_data
        assert "visual_generated_at" in json_data
        
        assert json_data["floor_plan_url"] == "https://cdn.example.com/floor_plan.png"
        assert json_data["rendering_url"] == "https://cdn.example.com/rendering.png"
        assert json_data["visual_generation_status"] == "completed"

    def test_design_response_visual_fields_types(self, db_session):
        """Test that visual fields have correct types in response schema."""
        # Arrange
        visual_generated_at = datetime.now(timezone.utc)
        design = DesignFactory.create(
            name="Type Test",
            project_id=1,
            building_type="residential",
            floor_plan_url="https://cdn.example.com/floor_plan.png",
            rendering_url="https://cdn.example.com/rendering.png",
            model_file_url="https://cdn.example.com/model.step",
            visual_generation_status="completed",
            visual_generation_error="Some error message",
            visual_generated_at=visual_generated_at
        )

        # Act
        response = DesignResponse.model_validate(design)

        # Assert types
        assert isinstance(response.floor_plan_url, str) or response.floor_plan_url is None
        assert isinstance(response.rendering_url, str) or response.rendering_url is None
        assert isinstance(response.model_file_url, str) or response.model_file_url is None
        assert isinstance(response.visual_generation_status, str)
        assert isinstance(response.visual_generation_error, str) or response.visual_generation_error is None
        assert isinstance(response.visual_generated_at, datetime) or response.visual_generated_at is None

    def test_design_response_visual_status_validation(self, db_session):
        """Test that visual generation status values are properly handled."""
        # Arrange
        valid_statuses = ["pending", "processing", "completed", "failed"]
        
        for status in valid_statuses:
            design = DesignFactory.create(
                name=f"Status Test {status}",
                project_id=1,
                building_type="residential",
                visual_generation_status=status
            )

            # Act
            response = DesignResponse.model_validate(design)

            # Assert
            assert response.visual_generation_status == status