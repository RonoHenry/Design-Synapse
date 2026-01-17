"""Test custom exceptions."""

import pytest
from src.core.exceptions import (ArchitecturalServiceException, ConflictError,
                                 ExternalServiceError, ForbiddenError,
                                 NotFoundError, UnauthorizedError,
                                 ValidationError)


def test_base_exception():
    """Test base exception."""
    exc = ArchitecturalServiceException("Test error", status_code=500)
    assert exc.message == "Test error"
    assert exc.status_code == 500
    assert exc.details == {}


def test_base_exception_with_details():
    """Test base exception with details."""
    details = {"field": "value"}
    exc = ArchitecturalServiceException("Test error", details=details)
    assert exc.details == details


def test_not_found_error():
    """Test NotFoundError."""
    exc = NotFoundError("Resource not found")
    assert exc.status_code == 404
    assert exc.message == "Resource not found"


def test_validation_error():
    """Test ValidationError."""
    exc = ValidationError("Invalid input")
    assert exc.status_code == 400
    assert exc.message == "Invalid input"


def test_conflict_error():
    """Test ConflictError."""
    exc = ConflictError("Version conflict")
    assert exc.status_code == 409
    assert exc.message == "Version conflict"


def test_unauthorized_error():
    """Test UnauthorizedError."""
    exc = UnauthorizedError()
    assert exc.status_code == 401
    assert exc.message == "Unauthorized"


def test_forbidden_error():
    """Test ForbiddenError."""
    exc = ForbiddenError()
    assert exc.status_code == 403
    assert exc.message == "Forbidden"


def test_external_service_error():
    """Test ExternalServiceError."""
    exc = ExternalServiceError("Service unavailable", service_name="design-service")
    assert exc.status_code == 502
    assert exc.message == "Service unavailable"
    assert exc.details["service"] == "design-service"
