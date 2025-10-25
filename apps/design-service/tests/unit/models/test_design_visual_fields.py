"""
Tests for Design model visual fields functionality.

This module tests the new visual output fields added to the Design model
for the Visualization Service enhancement.
"""

import pytest
from datetime import datetime
from sqlalchemy.exc import IntegrityError
from src.models.design import Design


class TestDesignVisualFields:
    """Test suite for Design model visual fields."""

    def test_design_creation_with_visual_fields(self, db_session):
        """Test creating a design with visual output fields."""
        # Arrange
        design_data = {
            "name": "Test Design with Visuals",
            "description": "A test design with visual outputs",
            "building_type": "residential",
            "project_id": 1,
            "user_id": 1,
            "specification": {"building_info": {"type": "house"}},
            "floor_plan_url": "https://cdn.example.com/floor_plan_123.png",
            "rendering_url": "https://cdn.example.com/rendering_123.png",
            "model_file_url": "https://cdn.example.com/model_123.step",
            "visual_generation_status": "completed",
            "visual_generated_at": datetime.utcnow()
        }

        # Act
        design = Design(**design_data)
        db_session.add(design)
        db_session.commit()

        # Assert
        assert design.id is not None
        assert design.floor_plan_url == "https://cdn.example.com/floor_plan_123.png"
        assert design.rendering_url == "https://cdn.example.com/rendering_123.png"
        assert design.model_file_url == "https://cdn.example.com/model_123.step"
        assert design.visual_generation_status == "completed"
        assert design.visual_generated_at is not None

    def test_design_creation_without_visual_fields(self, db_session):
        """Test creating a design without visual fields (backward compatibility)."""
        # Arrange
        design_data = {
            "name": "Test Design without Visuals",
            "description": "A test design without visual outputs",
            "building_type": "residential",
            "project_id": 1,
            "user_id": 1,
            "specification": {"building_info": {"type": "house"}}
        }

        # Act
        design = Design(**design_data)
        db_session.add(design)
        db_session.commit()

        # Assert
        assert design.id is not None
        assert design.floor_plan_url is None
        assert design.rendering_url is None
        assert design.model_file_url is None
        assert design.visual_generation_status == "not_requested"  # Default value
        assert design.visual_generated_at is None
        assert design.visual_generation_error is None

    def test_visual_url_validation(self, db_session):
        """Test URL format validation for visual fields."""
        # Arrange
        design_data = {
            "name": "Test Design URL Validation",
            "description": "Testing URL validation",
            "building_type": "residential",
            "project_id": 1,
            "user_id": 1,
            "specification": {"building_info": {"type": "house"}},
            "floor_plan_url": "invalid-url"  # Invalid URL format
        }

        # Act & Assert
        with pytest.raises(ValueError, match="Invalid URL format"):
            design = Design(**design_data)
            design.validate_visual_urls()

    def test_visual_generation_status_validation(self, db_session):
        """Test validation of visual generation status values."""
        # Arrange
        valid_statuses = ["pending", "processing", "completed", "failed"]
        
        for status in valid_statuses:
            design_data = {
                "name": f"Test Design Status {status}",
                "description": "Testing status validation",
                "building_type": "residential",
                "project_id": 1,
                "user_id": 1,
                "specification": {"building_info": {"type": "house"}},
                "visual_generation_status": status
            }

            # Act
            design = Design(**design_data)
            db_session.add(design)
            db_session.commit()

            # Assert
            assert design.visual_generation_status == status

        # Test invalid status
        with pytest.raises(ValueError, match="Invalid visual generation status"):
            invalid_design = Design(
                name="Invalid Status Test",
                description="Testing invalid status",
                building_type="residential",
                project_id=1,
                user_id=1,
                specification={"building_info": {"type": "house"}},
                visual_generation_status="invalid_status"
            )

    def test_design_model_serialization_with_visuals(self, db_session):
        """Test that Design model serializes correctly with visual fields."""
        # Arrange
        design = Design(
            name="Serialization Test",
            description="Testing serialization",
            building_type="residential",
            project_id=1,
            user_id=1,
            specification={"building_info": {"type": "house"}},
            floor_plan_url="https://cdn.example.com/floor_plan.png",
            rendering_url="https://cdn.example.com/rendering.png",
            visual_generation_status="completed"
        )
        db_session.add(design)
        db_session.commit()

        # Act
        design_dict = design.to_dict()

        # Assert
        assert "floor_plan_url" in design_dict
        assert "rendering_url" in design_dict
        assert "model_file_url" in design_dict
        assert "visual_generation_status" in design_dict
        assert "visual_generated_at" in design_dict
        assert "visual_generation_error" in design_dict
        
        assert design_dict["floor_plan_url"] == "https://cdn.example.com/floor_plan.png"
        assert design_dict["rendering_url"] == "https://cdn.example.com/rendering.png"
        assert design_dict["visual_generation_status"] == "completed"

    def test_design_repr_includes_visual_status(self, db_session):
        """Test that Design __repr__ includes visual generation status."""
        # Arrange
        design = Design(
            name="Repr Test",
            description="Testing repr",
            building_type="residential",
            project_id=1,
            user_id=1,
            specification={"building_info": {"type": "house"}},
            visual_generation_status="processing"
        )

        # Act
        repr_str = repr(design)

        # Assert
        assert "processing" in repr_str
        assert "visual_status" in repr_str.lower()

    def test_update_visual_fields(self, db_session):
        """Test updating visual fields on existing design."""
        # Arrange
        design = Design(
            name="Update Test",
            description="Testing updates",
            building_type="residential",
            project_id=1,
            user_id=1,
            specification={"building_info": {"type": "house"}}
        )
        db_session.add(design)
        db_session.commit()
        
        original_id = design.id

        # Act
        design.floor_plan_url = "https://cdn.example.com/new_floor_plan.png"
        design.visual_generation_status = "completed"
        design.visual_generated_at = datetime.utcnow()
        db_session.commit()

        # Assert
        updated_design = db_session.query(Design).filter_by(id=original_id).first()
        assert updated_design.floor_plan_url == "https://cdn.example.com/new_floor_plan.png"
        assert updated_design.visual_generation_status == "completed"
        assert updated_design.visual_generated_at is not None

    def test_visual_fields_nullable(self, db_session):
        """Test that visual fields are nullable for backward compatibility."""
        # Arrange & Act
        design = Design(
            name="Nullable Test",
            description="Testing nullable fields",
            building_type="residential",
            project_id=1,
            user_id=1,
            specification={"building_info": {"type": "house"}},
            floor_plan_url=None,
            rendering_url=None,
            model_file_url=None,
            visual_generation_error=None
        )
        db_session.add(design)
        db_session.commit()

        # Assert
        assert design.id is not None
        assert design.floor_plan_url is None
        assert design.rendering_url is None
        assert design.model_file_url is None
        assert design.visual_generation_error is None