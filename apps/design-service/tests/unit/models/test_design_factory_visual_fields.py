"""
Unit tests for DesignFactory visual fields support.

Tests that DesignFactory can create designs with visual output fields
and provides traits for designs with/without visuals.

Requirements tested:
- 10: Visual output generation and storage
"""

import pytest
import factory
from datetime import datetime, timezone

from tests.factories import DesignFactory


class TestDesignFactoryVisualFields:
    """Test DesignFactory visual fields support."""

    def test_design_factory_with_visual_fields(self, db_session):
        """Test DesignFactory can create designs with visual fields."""
        # Act
        design = DesignFactory.create(
            floor_plan_url="https://cdn.example.com/floor_plan.png",
            rendering_url="https://cdn.example.com/rendering.png",
            model_file_url="https://cdn.example.com/model.step",
            visual_generation_status="completed",
            visual_generation_error=None,
            visual_generated_at=datetime.now(timezone.utc)
        )

        # Assert
        assert design.floor_plan_url == "https://cdn.example.com/floor_plan.png"
        assert design.rendering_url == "https://cdn.example.com/rendering.png"
        assert design.model_file_url == "https://cdn.example.com/model.step"
        assert design.visual_generation_status == "completed"
        assert design.visual_generation_error is None
        assert design.visual_generated_at is not None

    def test_design_factory_without_visual_fields(self, db_session):
        """Test DesignFactory creates designs with default visual field values."""
        # Act
        design = DesignFactory.create()

        # Assert - should have default values
        assert design.floor_plan_url is None
        assert design.rendering_url is None
        assert design.model_file_url is None
        assert design.visual_generation_status == "not_requested"  # Default value
        assert design.visual_generation_error is None
        assert design.visual_generated_at is None

    def test_design_factory_with_visuals_trait(self, db_session):
        """Test DesignFactory with_visuals trait creates design with visual outputs."""
        # Act
        design = DesignFactory.create(with_visuals=True)

        # Assert
        assert design.floor_plan_url is not None
        assert design.rendering_url is not None
        assert design.visual_generation_status in ["completed", "processing"]
        # Model file URL might be None (optional)
        assert design.visual_generated_at is not None

    def test_design_factory_without_visuals_trait(self, db_session):
        """Test DesignFactory without_visuals trait creates design without visual outputs."""
        # Act
        design = DesignFactory.create(without_visuals=True)

        # Assert
        assert design.floor_plan_url is None
        assert design.rendering_url is None
        assert design.model_file_url is None
        assert design.visual_generation_status == "pending"
        assert design.visual_generation_error is None
        assert design.visual_generated_at is None

    def test_design_factory_processing_visuals_trait(self, db_session):
        """Test DesignFactory processing_visuals trait creates design with processing status."""
        # Act
        design = DesignFactory.create(processing_visuals=True)

        # Assert
        assert design.visual_generation_status == "processing"
        assert design.visual_generation_error is None
        assert design.visual_generated_at is None
        # URLs should be None when processing
        assert design.floor_plan_url is None
        assert design.rendering_url is None
        assert design.model_file_url is None

    def test_design_factory_failed_visuals_trait(self, db_session):
        """Test DesignFactory failed_visuals trait creates design with failed status."""
        # Act
        design = DesignFactory.create(failed_visuals=True)

        # Assert
        assert design.visual_generation_status == "failed"
        assert design.visual_generation_error is not None
        assert design.visual_generated_at is None
        # URLs should be None when failed
        assert design.floor_plan_url is None
        assert design.rendering_url is None
        assert design.model_file_url is None

    def test_design_factory_build_vs_create_visual_fields(self, db_session):
        """Test that both build() and create() work with visual fields."""
        # Act - build (doesn't save to DB)
        built_design = DesignFactory.build(
            floor_plan_url="https://cdn.example.com/built_floor_plan.png",
            visual_generation_status="completed"
        )
        
        # Act - create (saves to DB)
        created_design = DesignFactory.create(
            floor_plan_url="https://cdn.example.com/created_floor_plan.png",
            visual_generation_status="completed"
        )

        # Assert
        assert built_design.floor_plan_url == "https://cdn.example.com/built_floor_plan.png"
        assert built_design.visual_generation_status == "completed"
        
        assert created_design.floor_plan_url == "https://cdn.example.com/created_floor_plan.png"
        assert created_design.visual_generation_status == "completed"
        assert created_design.id is not None  # Should be saved to DB

    def test_design_factory_batch_create_with_visual_fields(self, db_session):
        """Test DesignFactory can create multiple designs with visual fields."""
        # Act
        designs = DesignFactory.create_batch(
            3,
            visual_generation_status="completed",
            floor_plan_url=factory.Iterator([
                "https://cdn.example.com/floor_plan_1.png",
                "https://cdn.example.com/floor_plan_2.png", 
                "https://cdn.example.com/floor_plan_3.png"
            ])
        )

        # Assert
        assert len(designs) == 3
        for i, design in enumerate(designs):
            assert design.visual_generation_status == "completed"
            assert design.floor_plan_url == f"https://cdn.example.com/floor_plan_{i+1}.png"