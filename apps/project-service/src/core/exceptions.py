"""Project Service error handling using shared error classes."""

import sys
from pathlib import Path

# Add packages to path for common imports
packages_path = Path(__file__).parent.parent.parent.parent.parent / "packages"
sys.path.insert(0, str(packages_path))

# Import all shared error classes and handlers
from common.errors.base import (APIError, AuthenticationError,
                                AuthorizationError, ConflictError,
                                DatabaseError, NotFoundError, ValidationError)
from common.errors.handlers import register_error_handlers
from common.errors.responses import ErrorResponse, ErrorType


def create_project_not_found_error(project_id: int) -> NotFoundError:
    """Create a standardized project not found error."""
    return NotFoundError(resource="Project", resource_id=str(project_id))


def create_project_access_error(
    project_id: int = None, user_id: int = None
) -> AuthorizationError:
    """Create a standardized project access denied error."""
    error = AuthorizationError(message="You don't have access to this project")
    if project_id or user_id:
        error.details = {}
        if project_id:
            error.details["project_id"] = project_id
        if user_id:
            error.details["user_id"] = user_id
    return error


def create_comment_not_found_error(
    comment_id: int, project_id: int = None
) -> NotFoundError:
    """Create a standardized comment not found error."""
    error = NotFoundError(resource="Comment", resource_id=str(comment_id))
    if project_id:
        error.details["project_id"] = project_id
    return error


def create_comment_access_error(
    comment_id: int, user_id: int = None
) -> AuthorizationError:
    """Create a standardized comment access denied error."""
    error = AuthorizationError(
        message="You don't have permission to access this comment"
    )
    error.details = {"comment_id": comment_id}
    if user_id:
        error.details["user_id"] = user_id
    return error


def create_validation_error(
    message: str, field: str = None, value: any = None
) -> ValidationError:
    """Create a standardized validation error."""
    details = {}
    if field:
        details["field"] = field
    if value is not None:
        details["invalid_value"] = value
    return ValidationError(message=message, details=details)
