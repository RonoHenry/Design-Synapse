"""
Test configuration for all integration tests.
"""
import pytest
from src.models.user import User


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
def test_user(db_session, valid_user_data):
    """Create and return a test user, rolling back the transaction after the test."""
    user = User(
        email=valid_user_data["email"],
        username=valid_user_data["username"],
        password=valid_user_data["password"],
        first_name=valid_user_data["first_name"],
        last_name=valid_user_data["last_name"],
    )
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
