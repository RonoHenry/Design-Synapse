"""
Test fixtures and utilities for user model tests.
"""
import pytest
from src.models.user import User


@pytest.fixture
def valid_user_data():
    """Return valid user data for testing."""
    return {
        "email": "test@example.com",
        "username": "testuser",
        "password": "securepass123",
        "first_name": "Test",
        "last_name": "User",
    }


@pytest.fixture
def test_user(db_session, valid_user_data):
    """Create and return a test user."""
    user = User(**valid_user_data)
    db_session.add(user)
    db_session.commit()
    return user


@pytest.fixture
def admin_user(db_session, valid_user_data):
    """Create and return an admin user."""
    admin_data = valid_user_data.copy()
    admin_data.update(
        {
            "email": "admin@example.com",
            "username": "adminuser",
            "roles": ["admin", "user"],
        }
    )
    user = User(**admin_data)
    db_session.add(user)
    db_session.commit()
    return user
