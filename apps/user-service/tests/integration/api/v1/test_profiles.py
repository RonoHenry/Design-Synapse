"""Integration tests for user profile API endpoints."""

import pytest
from fastapi import status

from src.models.user_profile import UserProfile


def test_get_profile_creates_default_profile(client, test_user, auth_headers):
    """Test that getting a profile creates a default one if it doesn't exist."""
    response = client.get("/api/v1/users/me/profile", headers=auth_headers)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["user_id"] == test_user.id
    assert data["preferences"] is None
    assert data["display_name"] is None


def test_get_existing_profile(client, test_user_with_profile, auth_headers):
    """Test retrieving an existing profile."""
    response = client.get("/api/v1/users/me/profile", headers=auth_headers)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["display_name"] == test_user_with_profile.profile.display_name
    assert data["user_id"] == test_user_with_profile.id


def test_update_profile(client, test_user, auth_headers, db_session):
    """Test updating a user's profile."""
    profile_data = {
        "display_name": "Test User",
        "bio": "A test user",
        "organization": "Test Org",
        "phone_number": "+1234567890",
        "location": "Test City",
        "social_links": {"github": "https://github.com/testuser"},
    }

    response = client.put(
        "/api/v1/users/me/profile",
        headers=auth_headers,
        json=profile_data,
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    # Verify all fields were updated
    for key, value in profile_data.items():
        assert data[key] == value

    # Verify database was updated
    db_profile = (
        db_session.query(UserProfile)
        .filter(UserProfile.user_id == test_user.id)
        .first()
    )
    for key, value in profile_data.items():
        assert getattr(db_profile, key) == value


def test_update_preferences(client, test_user_with_profile, auth_headers):
    """Test updating just the preferences field."""
    preferences = {
        "theme": "dark",
        "notifications": {"email": True, "push": False},
        "language": "en",
    }

    response = client.patch(
        "/api/v1/users/me/profile/preferences",
        headers=auth_headers,
        json={"preferences": preferences},
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["preferences"] == preferences


def test_update_preferences_no_profile(client, test_user, auth_headers):
    """Test that updating preferences without a profile returns 404."""
    preferences = {"theme": "dark"}
    response = client.patch(
        "/api/v1/users/me/profile/preferences",
        headers=auth_headers,
        json={"preferences": preferences},
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.fixture
def test_user_with_profile(test_user, db_session):
    """Create a test user with a profile."""
    profile = UserProfile(
        user_id=test_user.id,
        display_name="Test Display Name",
        bio="Test Bio",
    )
    db_session.add(profile)
    db_session.commit()
    db_session.refresh(test_user)
    return test_user
