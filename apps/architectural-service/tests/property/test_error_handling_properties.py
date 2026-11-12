"""Property-based tests for error handling."""

import json
import uuid
from datetime import datetime
from typing import Any, Dict

import pytest
from fastapi import status
from fastapi.exceptions import RequestValidationError
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st
from pydantic import ValidationError as PydanticValidationError
from src.core.exceptions import (ConflictError, ExternalServiceError,
                                 ForbiddenError, NotFoundError,
                                 UnauthorizedError, ValidationError)


class TestErrorResponseProperties:
    """Property-based tests for error response format."""

    @given(
        message=st.text(min_size=1, max_size=200),
        status_code=st.integers(min_value=400, max_value=599),
        details=st.dictionaries(
            keys=st.text(min_size=1, max_size=50),
            values=st.one_of(
                st.text(max_size=100), st.integers(), st.booleans(), st.none()
            ),
            max_size=5,
        ),
    )
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    async def test_property_error_response_format(
        self, message: str, status_code: int, details: Dict[str, Any]
    ):
        """
        Property 45: Error response format
        For any API request that results in an error, the response should include
        appropriate HTTP status code, error message, and error details.

        **Validates: Requirements 12.3**
        """
        # Create a custom exception to test error response format
        from src.core.exceptions import ArchitecturalServiceException

        class TestException(ArchitecturalServiceException):
            pass

        # Mock an endpoint that raises the exception
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        app = FastAPI()

        @app.get("/test-error")
        async def test_error_endpoint():
            raise TestException(
                message=message, status_code=status_code, details=details
            )

        # Add our error handlers
        from src.main import architectural_service_exception_handler

        app.add_exception_handler(
            ArchitecturalServiceException, architectural_service_exception_handler
        )

        test_client = TestClient(app)
        response = test_client.get("/test-error")

        # Verify response format
        assert response.status_code == status_code

        response_data = response.json()
        assert "error" in response_data

        error = response_data["error"]
        assert "code" in error
        assert "message" in error
        assert "details" in error
        assert "timestamp" in error
        assert "request_id" in error

        # Verify error content
        assert error["message"] == message
        assert error["details"] == details

        # Verify timestamp format (ISO 8601)
        timestamp = error["timestamp"]
        assert timestamp.endswith("Z")
        datetime.fromisoformat(timestamp.replace("Z", "+00:00"))  # Should not raise

        # Verify request ID is a valid UUID
        request_id = error["request_id"]
        uuid.UUID(request_id)  # Should not raise

    @given(
        field_errors=st.lists(
            st.tuples(
                st.lists(
                    st.text(min_size=1, max_size=20), min_size=1, max_size=3
                ),  # field path
                st.text(min_size=1, max_size=100),  # error message
                st.text(min_size=1, max_size=50),  # error type
            ),
            min_size=1,
            max_size=5,
        )
    )
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    async def test_property_validation_error_details(self, field_errors):
        """
        Property 46: Input validation error details
        For any API request with invalid input, the validation error response should
        include field-level details indicating which fields failed validation and why.

        **Validates: Requirements 12.4**
        """
        # Create a mock validation error
        from pydantic_core import ValidationError as CoreValidationError

        # Convert field_errors to the format expected by RequestValidationError
        pydantic_errors = []
        for field_path, message, error_type in field_errors:
            pydantic_errors.append(
                {
                    "loc": tuple(field_path),
                    "msg": message,
                    "type": error_type,
                    "input": "test_input",
                }
            )

        validation_error = RequestValidationError(pydantic_errors)

        # Mock an endpoint that raises validation error
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        app = FastAPI()

        @app.get("/test-validation")
        async def test_validation_endpoint():
            raise validation_error

        # Add our validation error handler
        from src.main import validation_exception_handler

        app.add_exception_handler(RequestValidationError, validation_exception_handler)

        test_client = TestClient(app)
        response = test_client.get("/test-validation")

        # Verify response format
        assert response.status_code == status.HTTP_400_BAD_REQUEST

        response_data = response.json()
        assert "error" in response_data

        error = response_data["error"]
        assert error["code"] == "VALIDATION_ERROR"
        assert "validation_errors" in error["details"]
        assert "error_count" in error["details"]

        # Verify validation error details
        validation_errors = error["details"]["validation_errors"]
        assert len(validation_errors) == len(field_errors)
        assert error["details"]["error_count"] == len(field_errors)

        # Verify each validation error has required fields
        for validation_error in validation_errors:
            assert "field" in validation_error
            assert "message" in validation_error
            assert "type" in validation_error
            assert isinstance(validation_error["field"], str)
            assert isinstance(validation_error["message"], str)
            assert isinstance(validation_error["type"], str)

    @given(
        exception_type=st.sampled_from(
            [
                (UnauthorizedError, "UNAUTHORIZED", 401),
                (ForbiddenError, "FORBIDDEN", 403),
                (NotFoundError, "NOT_FOUND", 404),
                (ConflictError, "CONFLICT", 409),
                (ValidationError, "VALIDATION_ERROR", 400),
            ]
        ),
        message=st.text(min_size=1, max_size=200),
        details=st.dictionaries(
            keys=st.text(min_size=1, max_size=50),
            values=st.text(max_size=100),
            max_size=3,
        ),
    )
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    async def test_property_specific_error_types(
        self, exception_type, message: str, details: Dict[str, str]
    ):
        """
        Property: Specific error type handling
        For any specific error type (401, 403, 404, 409, 400), the response should
        include the correct status code and error code.

        **Validates: Requirements 12.3**
        """
        exception_class, expected_code, expected_status = exception_type

        # Create exception instance
        if exception_class in [UnauthorizedError, ForbiddenError]:
            # These have default messages
            exc = exception_class(details=details)
        else:
            exc = exception_class(message=message, details=details)

        # Mock an endpoint that raises the exception
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        app = FastAPI()

        @app.get("/test-specific-error")
        async def test_specific_error_endpoint():
            raise exc

        # Add appropriate error handler
        if exception_class == UnauthorizedError:
            from src.main import unauthorized_exception_handler

            app.add_exception_handler(UnauthorizedError, unauthorized_exception_handler)
        elif exception_class == ForbiddenError:
            from src.main import forbidden_exception_handler

            app.add_exception_handler(ForbiddenError, forbidden_exception_handler)
        elif exception_class == NotFoundError:
            from src.main import not_found_exception_handler

            app.add_exception_handler(NotFoundError, not_found_exception_handler)
        elif exception_class == ConflictError:
            from src.main import conflict_exception_handler

            app.add_exception_handler(ConflictError, conflict_exception_handler)
        elif exception_class == ValidationError:
            from src.main import custom_validation_exception_handler

            app.add_exception_handler(
                ValidationError, custom_validation_exception_handler
            )

        test_client = TestClient(app)
        response = test_client.get("/test-specific-error")

        # Verify response format
        assert response.status_code == expected_status

        response_data = response.json()
        assert "error" in response_data

        error = response_data["error"]
        assert error["code"] == expected_code
        assert "message" in error
        assert "details" in error
        assert "timestamp" in error
        assert "request_id" in error

        # Verify details match
        assert error["details"] == details

        # For unauthorized errors, verify WWW-Authenticate header
        if exception_class == UnauthorizedError:
            assert "WWW-Authenticate" in response.headers
            assert response.headers["WWW-Authenticate"] == "Bearer"

    @given(
        service_name=st.text(min_size=1, max_size=50),
        message=st.text(min_size=1, max_size=200),
        status_code=st.sampled_from([502, 503, 504]),
        details=st.dictionaries(
            keys=st.text(min_size=1, max_size=50),
            values=st.text(max_size=100),
            max_size=3,
        ),
    )
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    async def test_property_external_service_error_format(
        self, service_name: str, message: str, status_code: int, details: Dict[str, str]
    ):
        """
        Property: External service error format
        For any external service error, the response should include service name
        in details and appropriate 5xx status code.

        **Validates: Requirements 12.3**
        """
        exc = ExternalServiceError(
            message=message,
            service_name=service_name,
            status_code=status_code,
            details=details,
        )

        # Mock an endpoint that raises the exception
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        app = FastAPI()

        @app.get("/test-external-error")
        async def test_external_error_endpoint():
            raise exc

        # Add error handler
        from src.main import external_service_exception_handler

        app.add_exception_handler(
            ExternalServiceError, external_service_exception_handler
        )

        test_client = TestClient(app)
        response = test_client.get("/test-external-error")

        # Verify response format
        assert response.status_code == status_code

        response_data = response.json()
        assert "error" in response_data

        error = response_data["error"]
        assert error["code"] == "EXTERNAL_SERVICE_ERROR"
        assert error["message"] == message

        # Verify service name is included in details
        assert "service" in error["details"]
        assert error["details"]["service"] == service_name

        # Verify original details are preserved
        for key, value in details.items():
            assert error["details"][key] == value

    @given(
        headers=st.dictionaries(
            keys=st.text(min_size=1, max_size=50),
            values=st.text(min_size=1, max_size=100),
            max_size=5,
        )
    )
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    async def test_property_response_headers_completeness(self, headers):
        """
        Property 47: Response header completeness
        For any API response, the headers should include appropriate cache-control,
        rate-limit information, and CORS headers.

        **Validates: Requirements 12.5**
        """
        # Mock a successful endpoint
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        app = FastAPI()

        @app.get("/test-headers")
        async def test_headers_endpoint():
            return {"status": "ok"}

        # Add our middleware
        from src.api.middleware import (RequestIDMiddleware,
                                        ResponseHeadersMiddleware)

        app.add_middleware(ResponseHeadersMiddleware)
        app.add_middleware(RequestIDMiddleware)

        test_client = TestClient(app)
        response = test_client.get("/test-headers", headers=headers)

        # Verify response is successful
        assert response.status_code == 200

        # Verify required headers are present
        required_headers = [
            "Cache-Control",
            "X-Content-Type-Options",
            "X-Frame-Options",
            "X-XSS-Protection",
            "X-Process-Time",
            "X-Service",
            "X-Version",
            "X-RateLimit-Limit",
            "X-RateLimit-Remaining",
            "X-RateLimit-Reset",
            "X-Request-ID",
        ]

        for header in required_headers:
            assert header in response.headers, f"Missing required header: {header}"

        # Verify header values are appropriate
        assert response.headers["Cache-Control"] in [
            "private, max-age=300",
            "public, max-age=3600",
            "no-cache, no-store, must-revalidate",
        ]
        assert response.headers["X-Content-Type-Options"] == "nosniff"
        assert response.headers["X-Frame-Options"] == "DENY"
        assert response.headers["X-XSS-Protection"] == "1; mode=block"

        # Verify numeric headers
        assert float(response.headers["X-Process-Time"]) >= 0
        assert int(response.headers["X-RateLimit-Limit"]) > 0
        assert int(response.headers["X-RateLimit-Remaining"]) >= 0
        assert int(response.headers["X-RateLimit-Reset"]) > 0

        # Verify request ID is a valid UUID
        uuid.UUID(response.headers["X-Request-ID"])  # Should not raise
