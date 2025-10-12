"""Comment fixtures for testing."""

import pytest
from src.models.project import Project
from src.models.comment import Comment
from jose import jwt
from datetime import datetime, timedelta
from src.core.config import settings


def create_test_token(user_id: int, expires_delta: timedelta = None) -> str:
    """Create a test JWT token."""
    if expires_delta is None:
        expires_delta = timedelta(minutes=15)
    
    expires = datetime.utcnow() + expires_delta
    jwt_payload = {
        "sub": str(user_id),
        "exp": expires,
    }
    token = jwt.encode(
        jwt_payload,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM
    )
    return token


@pytest.fixture
def test_project(db):
    """Create a test project."""
    project = Project(
        name="Test Project",
        description="A test project for testing comments",
        owner_id=1
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


@pytest.fixture
def test_comment(db, test_project):
    """Create a test comment."""
    comment = Comment(
        content="Test comment",
        project_id=test_project.id,
        user_id=1,
    )
    db.add(comment)
    db.commit()
    db.refresh(comment)
    return comment


@pytest.fixture
def auth_headers():
    """Create authorization headers with a test token."""
    token = create_test_token(1)
    return {"Authorization": f"Bearer {token}"}