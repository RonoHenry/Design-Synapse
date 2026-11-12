"""Standalone test for project service error handling."""

import os
import sys
from pathlib import Path

# Set up environment variables for testing
os.environ.setdefault("DB_USERNAME", "test")
os.environ.setdefault("DB_PASSWORD", "test")
os.environ.setdefault("DB_DATABASE", "test")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key")

# Add packages to path for common imports
packages_path = Path(__file__).parent / "packages"
sys.path.insert(0, str(packages_path))

from common.errors.base import (AuthorizationError, NotFoundError,
                                ValidationError)

# Add project service to path
project_service_path = Path(__file__).parent / "apps" / "project-service" / "src"
sys.path.insert(0, str(project_service_path))

from core.exceptions import (create_comment_access_error,
                             create_comment_not_found_error,
                             create_project_access_error,
                             create_project_not_found_error,
                             create_validation_error)


def test_create_project_not_found_error():
    """Test creating a project not found error."""
    project_id = 123
    error = create_project_not_found_error(project_id)

    assert isinstance(error, NotFoundError)
    assert error.resource == "Project"
    assert error.resource_id == "123"
    assert "Project" in error.message
    assert "123" in error.message
    print("✅ test_create_project_not_found_error passed")


def test_create_project_access_error_basic():
    """Test creating a basic project access error."""
    error = create_project_access_error()

    assert isinstance(error, AuthorizationError)
    assert "don't have access to this project" in error.message
    assert error.details is None
    print("✅ test_create_project_access_error_basic passed")


def test_create_project_access_error_with_details():
    """Test creating a project access error with details."""
    project_id = 456
    user_id = 789
    error = create_project_access_error(project_id=project_id, user_id=user_id)

    assert isinstance(error, AuthorizationError)
    assert "don't have access to this project" in error.message
    assert error.details is not None
    assert error.details["project_id"] == project_id
    assert error.details["user_id"] == user_id
    print("✅ test_create_project_access_error_with_details passed")


def test_create_comment_not_found_error_basic():
    """Test creating a basic comment not found error."""
    comment_id = 321
    error = create_comment_not_found_error(comment_id)

    assert isinstance(error, NotFoundError)
    assert error.resource == "Comment"
    assert error.resource_id == "321"
    assert "Comment" in error.message
    print("✅ test_create_comment_not_found_error_basic passed")


def test_create_comment_access_error_basic():
    """Test creating a basic comment access error."""
    comment_id = 987
    error = create_comment_access_error(comment_id)

    assert isinstance(error, AuthorizationError)
    assert "don't have permission to access this comment" in error.message
    assert error.details["comment_id"] == comment_id
    assert "user_id" not in error.details
    print("✅ test_create_comment_access_error_basic passed")


def test_create_validation_error_basic():
    """Test creating a basic validation error."""
    message = "Invalid input provided"
    error = create_validation_error(message)

    assert isinstance(error, ValidationError)
    assert error.message == message
    assert error.details == {}
    print("✅ test_create_validation_error_basic passed")


def test_create_validation_error_with_field_and_value():
    """Test creating a validation error with field and value."""
    message = "Invalid value"
    field = "status"
    value = "invalid_status"
    error = create_validation_error(message, field=field, value=value)

    assert isinstance(error, ValidationError)
    assert error.message == message
    assert error.details["field"] == field
    assert error.details["invalid_value"] == value
    print("✅ test_create_validation_error_with_field_and_value passed")


if __name__ == "__main__":
    print("Running project service exception tests...")

    test_create_project_not_found_error()
    test_create_project_access_error_basic()
    test_create_project_access_error_with_details()
    test_create_comment_not_found_error_basic()
    test_create_comment_access_error_basic()
    test_create_validation_error_basic()
    test_create_validation_error_with_field_and_value()

    print("\n🎉 All project service exception tests passed!")
