"""Shared error handling classes and utilities for all services."""

from .base import (
    APIError,
    AuthenticationError,
    AuthorizationError,
    DatabaseError,
    NotFoundError,
    ValidationError,
    ConflictError,
    RateLimitError,
)
from .handlers import (
    api_error_handler,
    validation_error_handler,
    sqlalchemy_error_handler,
    general_exception_handler,
)
from .responses import ErrorResponse, ErrorType

__all__ = [
    # Base exceptions
    "APIError",
    "AuthenticationError",
    "AuthorizationError",
    "DatabaseError",
    "NotFoundError",
    "ValidationError",
    "ConflictError",
    "RateLimitError",
    # Handlers
    "api_error_handler",
    "validation_error_handler",
    "sqlalchemy_error_handler",
    "general_exception_handler",
    # Response models
    "ErrorResponse",
    "ErrorType",
]
