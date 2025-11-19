"""Custom exception classes and handlers for Project Service."""

import sys
from pathlib import Path

# Add packages to path for common imports
packages_path = Path(__file__).parent.parent.parent.parent.parent / "packages"
sys.path.insert(0, str(packages_path))

from common.errors.base import APIError, NotFoundError, ForbiddenError
from common.errors.handlers import register_error_handlers


class ProjectNotFoundError(NotFoundError):
    """Raised when a project is not found."""

    def __init__(self, project_id: int):
        """Initialize project not found error."""
        super().__init__(
            message=f"Project with ID {project_id} not found",
            error_code="PROJECT_NOT_FOUND",
            details={"project_id": project_id}
        )


class ProjectAccessError(ForbiddenError):
    """Raised when a user doesn't have access to a project."""

    def __init__(self, project_id: int = None):
        """Initialize project access error."""
        details = {"project_id": project_id} if project_id else {}
        super().__init__(
            message="You don't have access to this project",
            error_code="PROJECT_ACCESS_DENIED",
            details=details
        )