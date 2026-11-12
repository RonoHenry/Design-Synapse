"""Unit tests for API error handlers."""

import json
import uuid
from datetime import datetime
from unittest.mock import Mock

import pytest
from fastapi import Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.testclient import TestClient
from pydantic import ValidationError as PydanticValidationError
from sqlalchemy.exc import IntegrityError, OperationalError
from src.core.exceptions import (ConflictError, ExternalServiceError,
                                 ForbiddenError, NotFoundError,
                                 UnauthorizedError, ValidationError)
from starlette.exceptions import HTTPException


class TestValidationErrorHandling:
    """Test validation error response format."""

    async def test_request_validation_error_response_format(self):
        """Test validation error response format."""
        # Create a validation error with multiple field errors
        errors = [
            {
                "loc": ("name",),
                "msg": "field required",
                "type": "value_error.missing",
                "input": None,
            },
            {
                "loc": ("building_type",),
                "msg": "value is not a valid enumeration member",
                "type": "type_error.enum",
                "input": "invalid_type",
            },
            {
                "loc": ("location", "latitude"),
                "msg": "ensure this value is greater than -90",
                "type": "value_error.number.not_gt",
                "input": -100,
            },
        ]

        validation_error = RequestValidationError(errors)

        # Create mock request
        request = Mock(spec=Request)

        # Import and test the handler
        from src.main import validation_exception_handler

        response = await validation_exception_handler(request, validation_error)

        # Verify response
        assert response.status_code == status.HTTP_400_BAD_REQUEST

        response_data = json.loads(response.body)
        assert "error" in response_data

        error = response_data["error"]
        assert error["code"] == "VALIDATION_ERROR"
        assert error["message"] == "Input validation failed"
        assert "validation_errors" in error["details"]
        assert error["details"]["error_count"] == 3

        # Verify validation errors structure
        validation_errors = error["details"]["validation_errors"]
        assert len(validation_errors) == 3

        # Check first error
        first_error = validation_errors[0]
        assert first_error["field"] == "name"
        assert first_error["message"] == "field required"
        assert first_error["type"] == "value_error.missing"

        # Check nested field error
        nested_error = validation_errors[2]
        assert nested_error["field"] == "location -> latitude"
        assert nested_error["message"] == "ensure this value is greater than -90"

    async def test_pydantic_validation_error_response_format(self):
        """Test Pydantic validation error response format."""
        # Create a Pydantic validation error using the correct constructor
        from pydantic_core import ValidationError as CoreValidationError

        # Create core validation error first
        core_errors = [
            {"type": "missing", "loc": ("email",), "msg": "Field required", "input": {}}
        ]

        validation_error = PydanticValidationError.from_exception_data(
            "ValidationError", core_errors
        )

        # Create mock request
        request = Mock(spec=Request)

        # Import and test the handler
        from src.main import pydantic_validation_exception_handler

        response = await pydantic_validation_exception_handler(
            request, validation_error
        )

        # Verify response
        assert response.status_code == status.HTTP_400_BAD_REQUEST

        response_data = json.loads(response.body)
        error = response_data["error"]
        assert error["code"] == "VALIDATION_ERROR"
        assert error["message"] == "Data validation failed"

    async def test_custom_validation_error_response_format(self):
        """Test custom validation error response format."""
        validation_error = ValidationError(
            message="Invalid design parameters",
            details={"field": "building_type", "reason": "not supported"},
        )

        # Create mock request
        request = Mock(spec=Request)

        # Import and test the handler
        from src.main import custom_validation_exception_handler

        response = await custom_validation_exception_handler(request, validation_error)

        # Verify response
        assert response.status_code == status.HTTP_400_BAD_REQUEST

        response_data = json.loads(response.body)
        error = response_data["error"]
        assert error["code"] == "VALIDATION_ERROR"
        assert error["message"] == "Invalid design parameters"
        assert error["details"]["field"] == "building_type"


class TestAuthenticationErrorHandling:
    """Test authentication failure (401)."""

    async def test_unauthorized_error_response_format(self):
        """Test unauthorized error response format."""
        unauthorized_error = UnauthorizedError(
            message="Invalid token",
            details={"token_type": "Bearer", "reason": "expired"},
        )

        # Create mock request
        request = Mock(spec=Request)

        # Import and test the handler
        from src.main import unauthorized_exception_handler

        response = await unauthorized_exception_handler(request, unauthorized_error)

        # Verify response
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

        response_data = json.loads(response.body)
        error = response_data["error"]
        assert error["code"] == "UNAUTHORIZED"
        assert error["message"] == "Invalid token"
        assert error["details"]["token_type"] == "Bearer"

        # Verify WWW-Authenticate header
        assert "WWW-Authenticate" in response.headers
        assert response.headers["WWW-Authenticate"] == "Bearer"

    async def test_unauthorized_error_default_message(self):
        """Test unauthorized error with default message."""
        unauthorized_error = UnauthorizedError()

        # Create mock request
        request = Mock(spec=Request)

        # Import and test the handler
        from src.main import unauthorized_exception_handler

        response = await unauthorized_exception_handler(request, unauthorized_error)

        # Verify response
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

        response_data = json.loads(response.body)
        error = response_data["error"]
        assert error["message"] == "Unauthorized"


class TestAuthorizationErrorHandling:
    """Test authorization failure (403)."""

    async def test_forbidden_error_response_format(self):
        """Test forbidden error response format."""
        forbidden_error = ForbiddenError(
            message="Insufficient permissions",
            details={
                "required_permission": "design:write",
                "user_permissions": ["design:read"],
            },
        )

        # Create mock request
        request = Mock(spec=Request)

        # Import and test the handler
        from src.main import forbidden_exception_handler

        response = await forbidden_exception_handler(request, forbidden_error)

        # Verify response
        assert response.status_code == status.HTTP_403_FORBIDDEN

        response_data = json.loads(response.body)
        error = response_data["error"]
        assert error["code"] == "FORBIDDEN"
        assert error["message"] == "Insufficient permissions"
        assert error["details"]["required_permission"] == "design:write"

    async def test_forbidden_error_default_message(self):
        """Test forbidden error with default message."""
        forbidden_error = ForbiddenError()

        # Create mock request
        request = Mock(spec=Request)

        # Import and test the handler
        from src.main import forbidden_exception_handler

        response = await forbidden_exception_handler(request, forbidden_error)

        # Verify response
        assert response.status_code == status.HTTP_403_FORBIDDEN

        response_data = json.loads(response.body)
        error = response_data["error"]
        assert error["message"] == "Forbidden"


class TestNotFoundErrorHandling:
    """Test not found error (404)."""

    async def test_not_found_error_response_format(self):
        """Test not found error response format."""
        not_found_error = NotFoundError(
            message="Design not found",
            details={"design_id": str(uuid.uuid4()), "resource_type": "design"},
        )

        # Create mock request
        request = Mock(spec=Request)

        # Import and test the handler
        from src.main import not_found_exception_handler

        response = await not_found_exception_handler(request, not_found_error)

        # Verify response
        assert response.status_code == status.HTTP_404_NOT_FOUND

        response_data = json.loads(response.body)
        error = response_data["error"]
        assert error["code"] == "NOT_FOUND"
        assert error["message"] == "Design not found"
        assert error["details"]["resource_type"] == "design"


class TestConflictErrorHandling:
    """Test optimistic locking conflict (409)."""

    async def test_conflict_error_response_format(self):
        """Test conflict error response format."""
        conflict_error = ConflictError(
            message="Version conflict detected",
            details={
                "current_version": 5,
                "provided_version": 3,
                "design_id": str(uuid.uuid4()),
            },
        )

        # Create mock request
        request = Mock(spec=Request)

        # Import and test the handler
        from src.main import conflict_exception_handler

        response = await conflict_exception_handler(request, conflict_error)

        # Verify response
        assert response.status_code == status.HTTP_409_CONFLICT

        response_data = json.loads(response.body)
        error = response_data["error"]
        assert error["code"] == "CONFLICT"
        assert error["message"] == "Version conflict detected"
        assert error["details"]["current_version"] == 5
        assert error["details"]["provided_version"] == 3

    async def test_optimistic_locking_conflict_scenario(self):
        """Test specific optimistic locking conflict scenario."""
        design_id = uuid.uuid4()
        conflict_error = ConflictError(
            message=f"Design {design_id} was modified by another user",
            details={
                "conflict_type": "optimistic_locking",
                "design_id": str(design_id),
                "expected_version": 2,
                "actual_version": 3,
                "last_modified_by": "user123",
                "resolution": "Please refresh and try again",
            },
        )

        # Create mock request
        request = Mock(spec=Request)

        # Import and test the handler
        from src.main import conflict_exception_handler

        response = await conflict_exception_handler(request, conflict_error)

        # Verify response
        assert response.status_code == status.HTTP_409_CONFLICT

        response_data = json.loads(response.body)
        error = response_data["error"]
        assert error["details"]["conflict_type"] == "optimistic_locking"
        assert error["details"]["resolution"] == "Please refresh and try again"


class TestDatabaseErrorHandling:
    """Test database-specific error handling."""

    async def test_integrity_error_duplicate_entry(self):
        """Test integrity error for duplicate entry."""
        # Mock SQLAlchemy IntegrityError with duplicate entry
        orig_error = Mock()
        orig_error.__str__ = Mock(
            return_value="Duplicate entry 'test-design' for key 'name_unique'"
        )

        integrity_error = IntegrityError(
            statement="INSERT INTO designs...", params={}, orig=orig_error
        )

        # Create mock request
        request = Mock(spec=Request)

        # Import and test the handler
        from src.main import integrity_error_handler

        response = await integrity_error_handler(request, integrity_error)

        # Verify response
        assert response.status_code == status.HTTP_409_CONFLICT

        response_data = json.loads(response.body)
        error = response_data["error"]
        assert error["code"] == "DUPLICATE_RESOURCE"
        assert error["message"] == "Resource already exists"

    async def test_integrity_error_foreign_key_constraint(self):
        """Test integrity error for foreign key constraint."""
        # Mock SQLAlchemy IntegrityError with foreign key constraint
        orig_error = Mock()
        orig_error.__str__ = Mock(return_value="foreign key constraint fails")

        integrity_error = IntegrityError(
            statement="INSERT INTO designs...", params={}, orig=orig_error
        )

        # Create mock request
        request = Mock(spec=Request)

        # Import and test the handler
        from src.main import integrity_error_handler

        response = await integrity_error_handler(request, integrity_error)

        # Verify response
        assert response.status_code == status.HTTP_400_BAD_REQUEST

        response_data = json.loads(response.body)
        error = response_data["error"]
        assert error["code"] == "INVALID_REFERENCE"
        assert error["message"] == "Referenced resource does not exist"

    async def test_operational_error_database_unavailable(self):
        """Test operational error for database unavailable."""
        operational_error = OperationalError(
            statement="SELECT * FROM designs",
            params={},
            orig=Exception("Connection refused"),
        )

        # Create mock request
        request = Mock(spec=Request)

        # Import and test the handler
        from src.main import operational_error_handler

        response = await operational_error_handler(request, operational_error)

        # Verify response
        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE

        response_data = json.loads(response.body)
        error = response_data["error"]
        assert error["code"] == "DATABASE_ERROR"
        assert error["message"] == "Database service temporarily unavailable"


class TestExternalServiceErrorHandling:
    """Test external service error handling."""

    async def test_external_service_error_502(self):
        """Test external service error with 502 status."""
        external_error = ExternalServiceError(
            message="Design service returned invalid response",
            service_name="design-service",
            status_code=502,
            details={"endpoint": "/render", "response_code": 500},
        )

        # Create mock request
        request = Mock(spec=Request)

        # Import and test the handler
        from src.main import external_service_exception_handler

        response = await external_service_exception_handler(request, external_error)

        # Verify response
        assert response.status_code == 502

        response_data = json.loads(response.body)
        error = response_data["error"]
        assert error["code"] == "EXTERNAL_SERVICE_ERROR"
        assert error["message"] == "Design service returned invalid response"
        assert error["details"]["service"] == "design-service"
        assert error["details"]["endpoint"] == "/render"

    async def test_external_service_error_503(self):
        """Test external service error with 503 status."""
        external_error = ExternalServiceError(
            message="Knowledge service temporarily unavailable",
            service_name="knowledge-service",
            status_code=503,
            details={"retry_after": 60},
        )

        # Create mock request
        request = Mock(spec=Request)

        # Import and test the handler
        from src.main import external_service_exception_handler

        response = await external_service_exception_handler(request, external_error)

        # Verify response
        assert response.status_code == 503

        response_data = json.loads(response.body)
        error = response_data["error"]
        assert error["code"] == "EXTERNAL_SERVICE_ERROR"
        assert error["details"]["service"] == "knowledge-service"
        assert error["details"]["retry_after"] == 60


class TestHTTPExceptionHandling:
    """Test Starlette HTTP exception handling."""

    async def test_http_exception_404(self):
        """Test HTTP exception for 404."""
        http_exception = HTTPException(status_code=404, detail="Endpoint not found")

        # Create mock request
        request = Mock(spec=Request)

        # Import and test the handler
        from src.main import http_exception_handler

        response = await http_exception_handler(request, http_exception)

        # Verify response
        assert response.status_code == 404

        response_data = json.loads(response.body)
        error = response_data["error"]
        assert error["code"] == "HTTP_ERROR"
        assert error["message"] == "Endpoint not found"

    async def test_http_exception_405(self):
        """Test HTTP exception for method not allowed."""
        http_exception = HTTPException(status_code=405, detail="Method not allowed")

        # Create mock request
        request = Mock(spec=Request)

        # Import and test the handler
        from src.main import http_exception_handler

        response = await http_exception_handler(request, http_exception)

        # Verify response
        assert response.status_code == 405

        response_data = json.loads(response.body)
        error = response_data["error"]
        assert error["code"] == "HTTP_ERROR"
        assert error["message"] == "Method not allowed"


class TestGeneralExceptionHandling:
    """Test general exception handling."""

    async def test_general_exception_handler(self):
        """Test general exception handler for unexpected errors."""
        # Create a generic exception
        generic_exception = ValueError("Unexpected value error")

        # Create mock request
        request = Mock(spec=Request)

        # Import and test the handler
        from src.main import general_exception_handler

        response = await general_exception_handler(request, generic_exception)

        # Verify response
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR

        response_data = json.loads(response.body)
        error = response_data["error"]
        assert error["code"] == "INTERNAL_ERROR"
        assert error["message"] == "An unexpected error occurred"
        assert error["details"]["exception_type"] == "ValueError"

    async def test_general_exception_handler_debug_mode(self, monkeypatch):
        """Test general exception handler in debug mode."""
        # Enable debug mode
        from src.core.config import settings

        monkeypatch.setattr(settings, "debug", True)

        # Create a generic exception
        generic_exception = RuntimeError("Something went wrong")

        # Create mock request
        request = Mock(spec=Request)

        # Import and test the handler
        from src.main import general_exception_handler

        response = await general_exception_handler(request, generic_exception)

        # Verify response
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR

        response_data = json.loads(response.body)
        error = response_data["error"]
        assert error["details"]["exception_message"] == "Something went wrong"

    async def test_general_exception_handler_production_mode(self, monkeypatch):
        """Test general exception handler in production mode."""
        # Disable debug mode
        from src.core.config import settings

        monkeypatch.setattr(settings, "debug", False)

        # Create a generic exception
        generic_exception = RuntimeError("Something went wrong")

        # Create mock request
        request = Mock(spec=Request)

        # Import and test the handler
        from src.main import general_exception_handler

        response = await general_exception_handler(request, generic_exception)

        # Verify response
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR

        response_data = json.loads(response.body)
        error = response_data["error"]
        assert error["details"]["exception_message"] == "Internal server error"


class TestErrorResponseConsistency:
    """Test that all error responses follow consistent format."""

    async def test_all_errors_have_required_fields(self):
        """Test that all error responses have required fields."""
        # Test various error types
        errors_to_test = [
            (ValidationError("Test validation"), "custom_validation_exception_handler"),
            (UnauthorizedError("Test auth"), "unauthorized_exception_handler"),
            (ForbiddenError("Test forbidden"), "forbidden_exception_handler"),
            (NotFoundError("Test not found"), "not_found_exception_handler"),
            (ConflictError("Test conflict"), "conflict_exception_handler"),
        ]

        request = Mock(spec=Request)

        for error, handler_name in errors_to_test:
            # Import and call the handler
            from src import main

            handler = getattr(main, handler_name)
            response = await handler(request, error)

            # Verify response structure
            response_data = json.loads(response.body)
            assert "error" in response_data

            error_obj = response_data["error"]
            required_fields = ["code", "message", "details", "timestamp", "request_id"]

            for field in required_fields:
                assert field in error_obj, f"Missing field {field} in {handler_name}"

            # Verify timestamp format
            timestamp = error_obj["timestamp"]
            assert timestamp.endswith("Z")
            datetime.fromisoformat(timestamp.replace("Z", "+00:00"))

            # Verify request ID is valid UUID
            uuid.UUID(error_obj["request_id"])
