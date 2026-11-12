"""Test fixtures for project integration tests."""

import pytest
from src.models.project import Project


@pytest.fixture
def test_project(db):
    """Create a test project."""
    project = Project(
        name="Test Project",
        description="A test project description",
        owner_id=1,
        status="draft"
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


@pytest.fixture
def test_projects(db):
    """Create multiple test projects."""
    projects = [
        Project(
            name=f"Test Project {i}",
            description=f"Description for project {i}",
            owner_id=1,
            status="draft"
        )
        for i in range(3)
    ]
    for project in projects:
        db.add(project)
    db.commit()
    for project in projects:
        db.refresh(project)
    return projects