"""Error handling and exception definitions for API endpoints.

This module provides custom exception classes and handlers for consistent API
error management, including auth, validation, and database error scenarios.
"""

from typing import Any, Dict, Optional

from fastapi import Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict
from sqlalchemy.exc import SQLAlchemyError


class ErrorResponse(BaseModel):
    """Standard error response model."""

    message: str
    error_code: str
    details: Optional[Dict[str, Any]] = None
    
    model_config = ConfigDict(from_attributes=True)


class APIError(Exception):
    """Base exception for API errors."""

    def __init__(
        self,
        message: str,
        error_code: str,
        status_code: int = status.HTTP_400_BAD_REQUEST,
        details: Optional[Dict[str, Any]] = None,
    ):
        """Initialize a new API error.

        Args:
            message: Human-readable error message
            error_code: Machine-readable error code
            status_code: HTTP status code to return
            details: Optional additional error details
        """
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        self.details = details
        super().__init__(message)


class NotFoundError(APIError):
    """Resource not found error."""

    def __init__(self, resource: str, resource_id: str):
        """Initialize a not found error.

        Args:
            resource: Type of resource that was not found
            resource_id: ID of the resource that was not found
        """
        super().__init__(
            message=f"{resource} with id {resource_id} not found",
            error_code="NOT_FOUND",
            status_code=status.HTTP_404_NOT_FOUND,
        )


class ValidationError(APIError):
    """Validation error."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        """Initialize a validation error.

        Args:
            message: Description of the validation error
            details: Optional dictionary with validation error details
        """
        super().__init__(
            message=message,
            error_code="VALIDATION_ERROR",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            details=details,
        )


class DatabaseError(APIError):
    """Database operation error."""

    def __init__(self, message: str = "Database error occurred"):
        """Initialize a database error.

        Args:
            message: Description of the database error
        """
        super().__init__(
            message=message,
            error_code="DATABASE_ERROR",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


class AuthenticationError(APIError):
    """Authentication error."""

    def __init__(self, message: str = "Authentication failed"):
        """Initialize an authentication error.

        Args:
            message: Description of the authentication failure
        """
        super().__init__(
            message=message,
            error_code="AUTHENTICATION_ERROR",
            status_code=status.HTTP_401_UNAUTHORIZED,
        )


class AuthorizationError(APIError):
    """Authorization error."""

    def __init__(self, message: str = "Insufficient permissions"):
        """Initialize an authorization error.

        Args:
            message: Description of the authorization failure
        """
        super().__init__(
            message=message,
            error_code="AUTHORIZATION_ERROR",
            status_code=status.HTTP_403_FORBIDDEN,
        )


async def api_error_handler(request: Request, exc: APIError) -> JSONResponse:
    """Handle APIError exceptions."""
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})


async def validation_error_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Handle FastAPI's RequestValidationError."""
    error_response = ErrorResponse(
        message="Validation error",
        error_code="VALIDATION_ERROR",
        details={"errors": exc.errors()},
    )
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=error_response.model_dump(exclude_none=True),
    )


async def sqlalchemy_error_handler(
    request: Request, exc: SQLAlchemyError
) -> JSONResponse:
    """Handle SQLAlchemy errors."""
    error_response = ErrorResponse(
        message="Database error occurred", error_code="DATABASE_ERROR"
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=error_response.model_dump(exclude_none=True),
    )


async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle any unhandled exceptions."""
    error_response = ErrorResponse(
        message="An unexpected error occurred",
        error_code="INTERNAL_SERVER_ERROR",
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=error_response.model_dump(exclude_none=True),
    )
