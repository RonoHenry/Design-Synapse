"""
Advanced tests for User model roles and validation.
"""
import pytest
from datetime import datetime, UTC
from src.models.user import User
from src.models.role import Role

def test_user_role_management(test_user):
    """Test adding and removing user roles."""
    # Test default role
    assert test_user.role_names == ["user"]
    assert test_user.has_role("user") is True
    
    # Create an admin role
    admin_role = Role(name="admin", description="Admin role")
    
    # Test adding a role
    test_user.add_role(admin_role)
    assert test_user.has_role("admin") is True
    assert len(test_user.roles) == 2
    
    # Test adding duplicate role
    test_user.add_role(admin_role)
    assert len(test_user.roles) == 2
    
    # Test removing role
    test_user.remove_role(admin_role)
    assert test_user.has_role("admin") is False
    assert len(test_user.roles) == 1
    
    # Test cannot remove user role
    user_role = test_user.roles[0]
    test_user.remove_role(user_role)
    assert test_user.has_role("user") is True

def test_user_timestamps():
    """Test that timestamps are set correctly."""
    before_create = datetime.now(UTC)
    user = User(
        email="test@example.com",
        username="testuser",
        password="securepass123"
    )
    after_create = datetime.now(UTC)
    assert before_create <= user.created_at_datetime <= after_create
    assert user.created_at_datetime == user.updated_at_datetime

def test_password_validation():
    """Test password validation rules."""
    with pytest.raises(ValueError, match="Password must be at least 8 characters long"):
        User(
            email="test@example.com",
            username="testuser",
            password="short"
        )

def test_user_full_name():
    """Test user full name handling."""
    user = User(
        email="test@example.com",
        username="testuser",
        password="securepass123",
        first_name="Test",
        last_name="User"
    )
    
    assert user.first_name_str == "Test"
    assert user.last_name_str == "User"