"""Unit tests for project service error handling."""

import os
import sys
from pathlib import Path

import pytest

# Set up environment variables for testing
os.environ.setdefault("DB_USERNAME", "test")
os.environ.setdefault("DB_PASSWORD", "test")
os.environ.setdefault("DB_DATABASE", "test")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key")

# Add packages to path for common imports
packages_path = Path(__file__).parent.parent.parent.parent.parent.parent / "packages"
sys.path.insert(0, str(packages_path))

from common.errors.base import (APIError, AuthenticationError,
                                AuthorizationError, ConflictError,
                                DatabaseError, NotFoundError, ValidationError)

# Import the functions we're testing
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "src"))
from src.core.exceptions import (create_comment_access_error,
                                 create_comment_not_found_error,
                                 create_project_access_error,
                                 create_project_not_found_error,
                                 create_validation_error)


class TestProjectExceptionCreators:
    """Test project service exception creator functions."""

    def test_create_project_not_found_error(self):
        """Test creating a project not found error."""
        project_id = 123
        error = create_project_not_found_error(project_id)

        assert isinstance(error, NotFoundError)
        assert error.resource == "Project"
        assert error.resource_id == "123"
        assert "Project" in error.message
        assert "123" in error.message

    def test_create_project_access_error_basic(self):
        """Test creating a basic project access error."""
        error = create_project_access_error()

        assert isinstance(error, AuthorizationError)
        assert "don't have access to this project" in error.message
        assert error.details is None

    def test_create_project_access_error_with_details(self):
        """Test creating a project access error with details."""
        project_id = 456
        user_id = 789
        error = create_project_access_error(project_id=project_id, user_id=user_id)

        assert isinstance(error, AuthorizationError)
        assert "don't have access to this project" in error.message
        assert error.details is not None
        assert error.details["project_id"] == project_id
        assert error.details["user_id"] == user_id

    def test_create_project_access_error_with_project_id_only(self):
        """Test creating a project access error with only project ID."""
        project_id = 456
        error = create_project_access_error(project_id=project_id)

        assert isinstance(error, AuthorizationError)
        assert error.details is not None
        assert error.details["project_id"] == project_id
        assert "user_id" not in error.details

    def test_create_project_access_error_with_user_id_only(self):
        """Test creating a project access error with only user ID."""
        user_id = 789
        error = create_project_access_error(user_id=user_id)

        assert isinstance(error, AuthorizationError)
        assert error.details is not None
        assert error.details["user_id"] == user_id
        assert "project_id" not in error.details

    def test_create_comment_not_found_error_basic(self):
        """Test creating a basic comment not found error."""
        comment_id = 321
        error = create_comment_not_found_error(comment_id)

        assert isinstance(error, NotFoundError)
        assert error.resource == "Comment"
        assert error.resource_id == "321"
        assert "Comment" in error.message

    def test_create_comment_not_found_error_with_project_id(self):
        """Test creating a comment not found error with project ID."""
        comment_id = 321
        project_id = 654
        error = create_comment_not_found_error(comment_id, project_id=project_id)

        assert isinstance(error, NotFoundError)
        assert error.resource == "Comment"
        assert error.resource_id == "321"
        assert error.details["project_id"] == project_id

    def test_create_comment_access_error_basic(self):
        """Test creating a basic comment access error."""
        comment_id = 987
        error = create_comment_access_error(comment_id)

        assert isinstance(error, AuthorizationError)
        assert "don't have permission to access this comment" in error.message
        assert error.details["comment_id"] == comment_id
        assert "user_id" not in error.details

    def test_create_comment_access_error_with_user_id(self):
        """Test creating a comment access error with user ID."""
        comment_id = 987
        user_id = 111
        error = create_comment_access_error(comment_id, user_id=user_id)

        assert isinstance(error, AuthorizationError)
        assert "don't have permission to access this comment" in error.message
        assert error.details["comment_id"] == comment_id
        assert error.details["user_id"] == user_id

    def test_create_validation_error_basic(self):
        """Test creating a basic validation error."""
        message = "Invalid input provided"
        error = create_validation_error(message)

        assert isinstance(error, ValidationError)
        assert error.message == message
        assert error.details == {}

    def test_create_validation_error_with_field(self):
        """Test creating a validation error with field."""
        message = "Field is required"
        field = "name"
        error = create_validation_error(message, field=field)

        assert isinstance(error, ValidationError)
        assert error.message == message
        assert error.details["field"] == field
        assert "invalid_value" not in error.details

    def test_create_validation_error_with_field_and_value(self):
        """Test creating a validation error with field and value."""
        message = "Invalid value"
        field = "status"
        value = "invalid_status"
        error = create_validation_error(message, field=field, value=value)

        assert isinstance(error, ValidationError)
        assert error.message == message
        assert error.details["field"] == field
        assert error.details["invalid_value"] == value

    def test_create_validation_error_with_none_value(self):
        """Test creating a validation error with None value."""
        message = "Value cannot be None"
        field = "required_field"
        value = None
        error = create_validation_error(message, field=field, value=value)

        assert isinstance(error, ValidationError)
        assert error.message == message
        assert error.details["field"] == field
        assert error.details["invalid_value"] is None

    def test_create_validation_error_with_zero_value(self):
        """Test creating a validation error with zero value."""
        message = "Value must be positive"
        field = "count"
        value = 0
        error = create_validation_error(message, field=field, value=value)

        assert isinstance(error, ValidationError)
        assert error.message == message
        assert error.details["field"] == field
        assert error.details["invalid_value"] == 0
