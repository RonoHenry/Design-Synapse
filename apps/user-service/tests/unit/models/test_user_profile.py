"""Tests for the User Profile functionality."""

import pytest
from src.models.user_profile import UserProfile


def test_create_user_profile():
    """Test creating a new user profile with all fields."""
    profile = UserProfile(
        user_id=1,  # Simulating the user id
        display_name="Test User",
        organization="Test Corp",
        phone_number="+254712345678",
        bio="Experienced architect with focus on sustainable design",
        location="Nairobi, Kenya",
        social_links={
            "linkedin": "https://linkedin.com/in/testuser",
            "twitter": "https://twitter.com/testuser",
        },
        preferences={
            "theme": "dark",
            "notifications": {"email": True, "push": False},
            "language": "en",
        },
    )

    assert profile.user_id == 1
    assert profile.phone_number == "+254712345678"
    assert profile.organization == "Test Corp"
    assert profile.display_name == "Test User"
    assert profile.location == "Nairobi, Kenya"
    assert isinstance(profile.social_links, dict)
    assert isinstance(profile.preferences, dict)
    assert profile.created_at is not None


def test_update_user_profile():
    """Test updating user profile fields."""
    profile = UserProfile(
        user_id=1,
        display_name="Test User",
        phone_number="+254712345678",
        organization="Test Corp",
    )

    # Update profile fields
    profile.phone_number = "+254787654321"
    profile.organization = "New Corp"
    profile.display_name = "Updated User"

    assert profile.phone_number == "+254787654321"
    assert profile.organization == "New Corp"
    assert profile.display_name == "Updated User"


def test_phone_number_validation():
    """Test phone number validation."""
    # Invalid phone numbers should raise ValueError
    with pytest.raises(ValueError):
        UserProfile(user_id=1, phone_number="invalid-phone", organization="Test Corp")

    with pytest.raises(ValueError):
        UserProfile(
            user_id=1, phone_number="123", organization="Test Corp"  # Too short
        )


def test_profile_preferences():
    """Test user profile preferences management."""
    profile = UserProfile(
        user_id=1,
        preferences={"theme": "light", "notifications": {"email": True, "push": True}},
    )

    # Update preferences
    profile.update_preferences(
        {"theme": "dark", "notifications": {"email": False, "push": True}}
    )

    assert profile.preferences["theme"] == "dark"
    assert profile.preferences["notifications"]["email"] is False
    assert profile.preferences["notifications"]["push"] is True


def test_social_links_validation():
    """Test social links validation."""
    # Invalid social link URLs should raise ValueError
    with pytest.raises(ValueError):
        UserProfile(
            user_id=1,
            social_links={
                "linkedin": "not-a-url",
            },
        )

    # Valid social links should work
    profile = UserProfile(
        user_id=1,
        social_links={
            "linkedin": "https://linkedin.com/in/testuser",
            "twitter": "https://twitter.com/testuser",
        },
    )

    assert profile.social_links["linkedin"] == "https://linkedin.com/in/testuser"
    assert profile.social_links["twitter"] == "https://twitter.com/testuser"


def test_cascade_delete():
    """Test that deleting a user also deletes their profile."""
    # Create a user and profile for testing cascade delete
    # This is just checking the model setup, actual cascade testing
    # will be done in integration tests
    profile = UserProfile(
        user_id=1,  # Using a dummy ID since this is a unit test
        organization="Test Corp",
    )

    # Verify profile is properly configured with cascade delete
    assert hasattr(profile, "user_id"), "Profile should have user_id field"
    assert hasattr(UserProfile, "user"), "Profile should have user relationship"
    assert (
        getattr(UserProfile.user, "cascade", None) == "all, delete-orphan"
    ), "User relationship should cascade delete"
