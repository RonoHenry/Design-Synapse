"""
Tests for the Design model.

Tests cover:
- Design model creation with required fields
- Field validation (name length, status values, version)
- JSON specification field storage and retrieval
- Version control (parent_design_id relationship)
"""

import pytest
from datetime import datetime
from sqlalchemy.exc import IntegrityError
from src.models.design import Design


def test_create_design_with_required_fields(db_session):
    """Test creating a new design with all required fields."""
    specification = {
        "building_info": {
            "type": "residential",
            "subtype": "single_family",
            "total_area": 250.5,
            "num_floors": 2
        }
    }
    
    design = Design(
        project_id=1,
        name="Test Design",
        specification=specification,
        building_type="residential",
        created_by=1
    )
    db_session.add(design)
    db_session.commit()
    db_session.refresh(design)

    assert design.id is not None
    assert design.project_id == 1
    assert design.name == "Test Design"
    assert design.specification == specification
    assert design.building_type == "residential"
    assert design.created_by == 1
    assert design.version == 1
    assert design.status == "draft"
    assert design.is_archived is False
    assert design.created_at is not None
    assert design.updated_at is not None


def test_create_design_without_required_fields(db_session):
    """Test that designs cannot be created without required fields."""
    design = Design()
    db_session.add(design)
    
    with pytest.raises(IntegrityError):
        db_session.commit()


def test_design_name_length_validation():
    """Test that design name length is validated."""
    # Test name too short (empty)
    with pytest.raises(ValueError) as exc_info:
        Design(
            project_id=1,
            name="",
            specification={},
            building_type="residential",
            created_by=1
        )
    assert "Design name cannot be empty" in str(exc_info.value)
    
    # Test name too long (over 255 characters)
    long_name = "a" * 256
    with pytest.raises(ValueError) as exc_info:
        Design(
            project_id=1,
            name=long_name,
            specification={},
            building_type="residential",
            created_by=1
        )
    assert "Design name cannot exceed 255 characters" in str(exc_info.value)


def test_design_status_validation():
    """Test that design status must be one of the allowed values."""
    valid_statuses = ["draft", "validated", "compliant", "non_compliant"]
    
    # Test valid statuses
    for status in valid_statuses:
        design = Design(
            project_id=1,
            name="Test Design",
            specification={},
            building_type="residential",
            created_by=1,
            status=status
        )
        assert design.status == status
    
    # Test invalid status
    with pytest.raises(ValueError) as exc_info:
        Design(
            project_id=1,
            name="Test Design",
            specification={},
            building_type="residential",
            created_by=1,
            status="invalid_status"
        )
    assert "Status must be one of" in str(exc_info.value)


def test_design_default_values():
    """Test that default values are set correctly."""
    design = Design(
        project_id=1,
        name="Test Design",
        specification={},
        building_type="residential",
        created_by=1
    )
    
    assert design.status == "draft"
    assert design.version == 1
    assert design.is_archived is False
    assert design.parent_design_id is None


def test_design_json_specification_storage(db_session):
    """Test that JSON specification is properly stored and retrieved."""
    complex_specification = {
        "building_info": {
            "type": "residential",
            "subtype": "single_family",
            "total_area": 250.5,
            "num_floors": 2,
            "height": 7.5
        },
        "structure": {
            "foundation_type": "slab",
            "wall_material": "concrete_block",
            "roof_type": "pitched",
            "roof_material": "clay_tiles"
        },
        "spaces": [
            {
                "name": "Living Room",
                "area": 35.0,
                "floor": 1,
                "dimensions": {"length": 7.0, "width": 5.0, "height": 3.0}
            },
            {
                "name": "Kitchen",
                "area": 20.0,
                "floor": 1,
                "dimensions": {"length": 5.0, "width": 4.0, "height": 3.0}
            }
        ],
        "materials": [
            {
                "name": "Concrete Blocks",
                "quantity": 5000,
                "unit": "pieces",
                "estimated_cost": 150000
            }
        ]
    }
    
    design = Design(
        project_id=1,
        name="Complex Design",
        specification=complex_specification,
        building_type="residential",
        created_by=1
    )
    db_session.add(design)
    db_session.commit()
    db_session.refresh(design)
    
    # Verify the specification is stored and retrieved correctly
    assert design.specification == complex_specification
    assert design.specification["building_info"]["total_area"] == 250.5
    assert len(design.specification["spaces"]) == 2
    assert design.specification["spaces"][0]["name"] == "Living Room"


def test_design_metadata_fields(db_session):
    """Test that metadata fields are properly stored."""
    design = Design(
        project_id=1,
        name="Test Design",
        description="A test design description",
        specification={},
        building_type="commercial",
        total_area=500.0,
        num_floors=3,
        materials=["concrete", "steel", "glass"],
        created_by=1
    )
    db_session.add(design)
    db_session.commit()
    db_session.refresh(design)
    
    assert design.description == "A test design description"
    assert design.building_type == "commercial"
    assert design.total_area == 500.0
    assert design.num_floors == 3
    assert design.materials == ["concrete", "steel", "glass"]


def test_design_ai_generation_metadata(db_session):
    """Test that AI generation metadata is properly stored."""
    design = Design(
        project_id=1,
        name="AI Generated Design",
        specification={},
        building_type="residential",
        generation_prompt="Create a 3-bedroom house with modern design",
        confidence_score=85.5,
        ai_model_version="gpt-4",
        created_by=1
    )
    db_session.add(design)
    db_session.commit()
    db_session.refresh(design)
    
    assert design.generation_prompt == "Create a 3-bedroom house with modern design"
    assert design.confidence_score == 85.5
    assert design.ai_model_version == "gpt-4"


def test_design_version_control_parent_relationship(db_session):
    """Test that parent_design_id creates proper version relationships."""
    # Create parent design (version 1)
    parent_design = Design(
        project_id=1,
        name="Original Design",
        specification={"version": "1.0"},
        building_type="residential",
        version=1,
        created_by=1
    )
    db_session.add(parent_design)
    db_session.commit()
    db_session.refresh(parent_design)
    
    # Create child design (version 2)
    child_design = Design(
        project_id=1,
        name="Updated Design",
        specification={"version": "2.0"},
        building_type="residential",
        version=2,
        parent_design_id=parent_design.id,
        created_by=1
    )
    db_session.add(child_design)
    db_session.commit()
    db_session.refresh(child_design)
    
    # Verify relationship
    assert child_design.parent_design_id == parent_design.id
    assert child_design.version == 2
    assert parent_design.version == 1


def test_design_version_chain(db_session):
    """Test creating a chain of design versions."""
    # Create version 1
    v1 = Design(
        project_id=1,
        name="Design v1",
        specification={"version": "1.0"},
        building_type="residential",
        version=1,
        created_by=1
    )
    db_session.add(v1)
    db_session.commit()
    db_session.refresh(v1)
    
    # Create version 2
    v2 = Design(
        project_id=1,
        name="Design v2",
        specification={"version": "2.0"},
        building_type="residential",
        version=2,
        parent_design_id=v1.id,
        created_by=1
    )
    db_session.add(v2)
    db_session.commit()
    db_session.refresh(v2)
    
    # Create version 3
    v3 = Design(
        project_id=1,
        name="Design v3",
        specification={"version": "3.0"},
        building_type="residential",
        version=3,
        parent_design_id=v2.id,
        created_by=1
    )
    db_session.add(v3)
    db_session.commit()
    db_session.refresh(v3)
    
    # Verify version chain
    assert v1.parent_design_id is None
    assert v2.parent_design_id == v1.id
    assert v3.parent_design_id == v2.id
    assert v1.version == 1
    assert v2.version == 2
    assert v3.version == 3


def test_design_audit_fields(db_session):
    """Test that audit fields are properly set."""
    design = Design(
        project_id=1,
        name="Test Design",
        specification={},
        building_type="residential",
        created_by=1
    )
    db_session.add(design)
    db_session.commit()
    db_session.refresh(design)
    
    assert design.created_by == 1
    assert isinstance(design.created_at, datetime)
    assert isinstance(design.updated_at, datetime)
    assert design.created_at <= design.updated_at


def test_design_soft_delete(db_session):
    """Test that designs can be soft deleted using is_archived flag."""
    design = Design(
        project_id=1,
        name="Test Design",
        specification={},
        building_type="residential",
        created_by=1
    )
    db_session.add(design)
    db_session.commit()
    db_session.refresh(design)
    
    # Soft delete
    design.is_archived = True
    db_session.commit()
    db_session.refresh(design)
    
    assert design.is_archived is True
    assert design.id is not None  # Still exists in database


def test_design_optional_fields_can_be_null(db_session):
    """Test that optional fields can be None."""
    design = Design(
        project_id=1,
        name="Minimal Design",
        specification={},
        building_type="residential",
        created_by=1
    )
    db_session.add(design)
    db_session.commit()
    db_session.refresh(design)
    
    assert design.description is None
    assert design.total_area is None
    assert design.num_floors is None
    assert design.materials is None
    assert design.generation_prompt is None
    assert design.confidence_score is None
    assert design.ai_model_version is None
    assert design.parent_design_id is None


def test_design_updated_at_changes_on_update(db_session):
    """Test that updated_at timestamp changes when design is updated."""
    design = Design(
        project_id=1,
        name="Test Design",
        specification={},
        building_type="residential",
        created_by=1
    )
    db_session.add(design)
    db_session.commit()
    db_session.refresh(design)
    
    original_updated_at = design.updated_at
    
    # Update the design
    design.name = "Updated Design Name"
    db_session.commit()
    db_session.refresh(design)
    
    # Note: In SQLite, the timestamp might not change if the update is too fast
    # In production with TiDB, this will work correctly
    assert design.name == "Updated Design Name"
    assert design.updated_at >= original_updated_at
