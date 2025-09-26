"""Tests for role-based access control functionality."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from src.core.security import create_access_token
from src.infrastructure.database import get_db
from src.main import app
from src.models.role import Role
from src.models.user import User

client = TestClient(app)


@pytest.fixture(autouse=True)
def override_dependency(db_session: Session):
    """Override the get_db dependency with our test session."""

    def override_get_db():
        try:
            yield db_session
        finally:
            pass  # Session cleanup is handled by the db_session fixture

    app.dependency_overrides[get_db] = override_get_db
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def admin_role(db_session: Session) -> Role:
    """Create an admin role for testing."""
    role = db_session.query(Role).filter_by(name="admin").first()
    if not role:
        role = Role(name="admin", description="Administrator role")
        db_session.add(role)
        db_session.commit()
        db_session.refresh(role)
    return role


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
def admin_user(db_session: Session, test_user: User, admin_role: Role) -> User:
    """Create an admin user for testing."""
    test_user.add_role(admin_role)
    db_session.commit()
    db_session.refresh(test_user)
    return test_user


def test_create_role(db_session: Session, admin_user: User):
    """Test creating a new role."""
    # Create admin token
    token = create_access_token(
        data={"sub": admin_user.email}, roles=[role.name for role in admin_user.roles]
    )

    response = client.post(
        "/api/v1/roles",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "editor", "description": "Editor role"},
    )

    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "editor"
    assert data["description"] == "Editor role"


def test_create_role_unauthorized(db_session: Session, test_user: User):
    """Test that non-admin users cannot create roles."""
    # Create non-admin token
    token = create_access_token(
        data={"sub": test_user.email}, roles=[role.name for role in test_user.roles]
    )

    response = client.post(
        "/api/v1/roles",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "editor", "description": "Editor role"},
    )

    assert response.status_code == 403


def test_assign_role(
    db_session: Session, admin_user: User, test_user: User, user_role: Role
):
    """Test assigning a role to a user."""
    # Create admin token
    token = create_access_token(
        data={"sub": admin_user.email}, roles=[role.name for role in admin_user.roles]
    )

    response = client.post(
        f"/api/v1/users/{test_user.id}/roles/{user_role.name}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    db_session.refresh(test_user)
    assert any(role.name == "user" for role in test_user.roles)


def test_remove_role(db_session: Session, admin_user: User, test_user: User):
    """Test removing a role from a user."""
    # Create a test role
    editor_role = Role(name="editor", description="Editor role")
    db_session.add(editor_role)
    db_session.commit()

    # Add the role to the test user
    test_user.add_role(editor_role)
    db_session.commit()

    # Create admin token
    token = create_access_token(
        data={"sub": admin_user.email}, roles=[role.name for role in admin_user.roles]
    )

    response = client.delete(
        f"/api/v1/users/{test_user.id}/roles/{editor_role.name}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    db_session.refresh(test_user)
    assert not any(role.name == "editor" for role in test_user.roles)


def test_get_my_roles(db_session: Session, test_user: User, user_role: Role):
    """Test getting current user's roles."""
    # Add a role to the user
    test_user.add_role(user_role)
    db_session.commit()

    # Create user token
    token = create_access_token(
        data={"sub": test_user.email}, roles=[role.name for role in test_user.roles]
    )

    response = client.get(
        "/api/v1/users/me/roles", headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["name"] == "user"
