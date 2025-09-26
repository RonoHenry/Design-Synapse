"""Tests for the Project model."""

import pytest
from sqlalchemy.exc import IntegrityError
from src.models.project import Project


def test_create_project(db):
    """Test creating a new project with required fields."""
    project = Project(
        name="Test Project",
        description="A test project description",
        owner_id=1,
        status="draft"
    )
    db.add(project)
    db.commit()
    db.refresh(project)

    assert project.id is not None
    assert project.name == "Test Project"
    assert project.description == "A test project description"
    assert project.owner_id == 1
    assert project.status == "draft"
    assert project.created_at is not None
    assert project.updated_at is not None


def test_project_without_required_fields(db):
    """Test that projects cannot be created without required fields."""
    project = Project()
    db.add(project)
    
    with pytest.raises(IntegrityError):
        db.commit()


def test_project_status_validation():
    """Test that project status must be one of the allowed values."""
    with pytest.raises(ValueError):
        Project(
            name="Test Project",
            description="A test project",
            owner_id=1,
            status="invalid_status"
        )


def test_project_name_max_length(db):
        """Test that project name cannot exceed maximum length."""
        long_name = "a" * 256  # Assuming max length is 255
        
        with pytest.raises(ValueError) as exc_info:
            Project(
                name=long_name,
                description="Test description",
                owner_id=1,
                status="draft"
            )
        
        assert "Project name cannot exceed 255 characters" in str(exc_info.value)
def test_project_default_values():
    """Test that default values are set correctly."""
    project = Project(
        name="Test Project",
        owner_id=1
    )
    
    assert project.status == "draft"
    assert project.is_public is False
    assert project.is_archived is False
    assert project.version == 1


def test_project_collaborators(db):
    """Test project collaborators association table."""
    project = Project(
        name="Test Project",
        description="Test description",
        owner_id=1,
        status="draft"
    )
    db.add(project)
    db.commit()

    # For now, we just verify the project was created successfully
    assert project.id is not None
    assert project.owner_id == 1