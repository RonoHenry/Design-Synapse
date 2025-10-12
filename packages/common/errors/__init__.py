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
    ExternalServiceError,
    LLMServiceError,
    VectorSearchError,
)
from .handlers import (
    api_error_handler,
    validation_error_handler,
    sqlalchemy_error_handler,
    general_exception_handler,
    register_error_handlers,
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
    "ExternalServiceError",
    "LLMServiceError",
    "VectorSearchError",
    # Handlers
    "api_error_handler",
    "validation_error_handler",
    "sqlalchemy_error_handler",
    "general_exception_handler",
    "register_error_handlers",
    # Response models
    "ErrorResponse",
    "ErrorType",
]
