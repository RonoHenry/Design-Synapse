"""
Tests for the User model.
"""
import pytest
from datetime import datetime
from src.models.user import User

def test_create_user():
    """Test creating a new user with valid data."""
    user = User(
        email="test@example.com",
        username="testuser",
        password="securepass123"
    )
    
    assert user.email == "test@example.com"
    assert user.username == "testuser"
    assert user.password != "securepass123"  # Password should be hashed
    assert user.created_at is not None
    assert user.is_active is True
    assert user.role_names == ["user"]  # Default role

def test_user_password_hashing():
    """Test that passwords are properly hashed."""
    password = "securepass123"
    user = User(
        email="test@example.com",
        username="testuser",
        password=password
    )
    
    assert user.password != password
    assert user.verify_password(password) is True
    assert user.verify_password("wrongpass") is False

def test_user_email_validation():
    """Test that email validation works correctly."""
    with pytest.raises(ValueError):
        User(
            email="invalid-email",
            username="testuser",
            password="securepass123"
        )

def test_username_validation():
    """Test username validation rules."""
    with pytest.raises(ValueError):
        User(
            email="test@example.com",
            username="u",  # Too short
            password="securepass123"
        )
        
    with pytest.raises(ValueError):
        User(
            email="test@example.com",
            username="user@invalid",  # Invalid characters
            password="securepass123"
        )