"""Custom exceptions for the Architectural Service."""

from typing import Any, Optional


class ArchitecturalServiceException(Exception):
    """Base exception for Architectural Service."""

    def __init__(
        self,
        message: str,
        status_code: int = 500,
        details: Optional[dict[str, Any]] = None,
    ):
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)


class NotFoundError(ArchitecturalServiceException):
    """Resource not found exception."""

    def __init__(self, message: str, details: Optional[dict[str, Any]] = None):
        super().__init__(message, status_code=404, details=details)


class ValidationError(ArchitecturalServiceException):
    """Validation error exception."""

    def __init__(self, message: str, details: Optional[dict[str, Any]] = None):
        super().__init__(message, status_code=400, details=details)


class ConflictError(ArchitecturalServiceException):
    """Conflict error exception (e.g., optimistic locking)."""

    def __init__(self, message: str, details: Optional[dict[str, Any]] = None):
        super().__init__(message, status_code=409, details=details)


class UnauthorizedError(ArchitecturalServiceException):
    """Unauthorized access exception."""

    def __init__(
        self, message: str = "Unauthorized", details: Optional[dict[str, Any]] = None
    ):
        super().__init__(message, status_code=401, details=details)


class ForbiddenError(ArchitecturalServiceException):
    """Forbidden access exception."""

    def __init__(
        self, message: str = "Forbidden", details: Optional[dict[str, Any]] = None
    ):
        super().__init__(message, status_code=403, details=details)


class ExternalServiceError(ArchitecturalServiceException):
    """External service error exception."""

    def __init__(
        self,
        message: str,
        service_name: str,
        status_code: int = 502,
        details: Optional[dict[str, Any]] = None,
    ):
        details = details or {}
        details["service"] = service_name
        super().__init__(message, status_code=status_code, details=details)
