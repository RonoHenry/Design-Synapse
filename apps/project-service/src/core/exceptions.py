"""Custom exception classes and handlers."""

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError


class APIError(Exception):
    """Base class for API errors."""

    def __init__(self, status_code: int, message: str):
        """Initialize API error."""
        self.status_code = status_code
        self.message = message
        super().__init__(message)


class ProjectNotFoundError(APIError):
    """Raised when a project is not found."""

    def __init__(self, project_id: int):
        """Initialize project not found error."""
        super().__init__(
            status_code=404,
            message=f"Project with ID {project_id} not found"
        )


class ProjectAccessError(APIError):
    """Raised when a user doesn't have access to a project."""

    def __init__(self):
        """Initialize project access error."""
        super().__init__(
            status_code=403,
            message="You don't have access to this project"
        )


async def api_error_handler(request: Request, exc: APIError) -> JSONResponse:
    """Handle API errors."""
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.message}
    )


async def validation_error_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Handle validation errors."""
    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors()}
    )


async def sqlalchemy_error_handler(
    request: Request, exc: SQLAlchemyError
) -> JSONResponse:
    """Handle database errors."""
    return JSONResponse(
        status_code=500,
        content={"detail": "Database error occurred"}
    )


async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle general exceptions."""
    return JSONResponse(
        status_code=500,
        content={"detail": "An unexpected error occurred"}
    )