"""User Service error handling using shared error classes."""

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


def create_user_not_found_error(user_id: int) -> NotFoundError:
    """Create a standardized user not found error."""
    return NotFoundError(resource="User", resource_id=str(user_id))


def create_role_not_found_error(role_id: int) -> NotFoundError:
    """Create a standardized role not found error."""
    return NotFoundError(resource="Role", resource_id=str(role_id))


def create_user_validation_error(
    message: str, field: str = None, value: any = None
) -> ValidationError:
    """Create a standardized user validation error."""
    details = {}
    if field:
        details["field"] = field
    if value is not None:
        details["invalid_value"] = value
    return ValidationError(message=message, details=details)


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


def create_authentication_error(
    message: str = "Authentication failed",
) -> AuthenticationError:
    """Create a standardized authentication error."""
    return AuthenticationError(message=message)


def create_authorization_error(
    message: str = "Insufficient permissions",
) -> AuthorizationError:
    """Create a standardized authorization error."""
    return AuthorizationError(message=message)
