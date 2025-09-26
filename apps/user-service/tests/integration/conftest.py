"""Test configuration for all integration tests."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from src.core.security import create_access_token
from src.main import app
from src.models.role import Role
from src.models.user import User


@pytest.fixture
def user_role(db_session: Session) -> Role:
    """Create a user role for testing."""
    role = db_session.query(Role).filter_by(name="user").first()
    if not role:
        role = Role(name="user", description="Regular user role")
        db_session.add(role)
        db_session.commit()
        db_session.refresh(role)
    return role


@pytest.fixture
def valid_user_data():
    """Return valid user data for testing."""
    return {
        "email": "test@example.com",
        "username": "testuser",
        "password": "testpassword",
        "first_name": "Test",
        "last_name": "User",
    }


@pytest.fixture
def test_user(db_session, valid_user_data, user_role):
    """Create and return a test user, rolling back the transaction after the test."""
    user = User(
        email=valid_user_data["email"],
        username=valid_user_data["username"],
        password=valid_user_data["password"],
        first_name=valid_user_data["first_name"],
        last_name=valid_user_data["last_name"],
    )
    user.roles = [user_role]
    db_session.add(user)
    db_session.commit()

    yield user

    # Clean up if the user still exists
    existing_user = db_session.query(User).filter_by(id=user.id).first()
    if existing_user:
        # Clean up the user's roles first
        existing_user.roles = []
        db_session.commit()

        # Then delete the user
        db_session.delete(existing_user)
        db_session.commit()


@pytest.fixture
def client(db_session) -> TestClient:
    """Create a FastAPI test client."""
    from src.infrastructure.database import get_db

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def auth_headers(test_user: User) -> dict[str, str]:
    """Create authentication headers with JWT token."""
    access_token = create_access_token(data={"sub": test_user.email}, roles=["user"])
    return {"Authorization": f"Bearer {access_token}"}
