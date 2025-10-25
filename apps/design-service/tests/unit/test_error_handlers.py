"""Unit tests for error handler registration and functionality."""

import pytest
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.testclient import TestClient
from pydantic import BaseModel, Field, ValidationError as PydanticValidationError
from sqlalchemy.exc import IntegrityError, OperationalError

from common.errors import (
    APIError,
    NotFoundError,
    ValidationError as CustomValidationError,
    AuthenticationError,
    DatabaseError,
    register_error_handlers,
)


def test_register_error_handlers():
    """Test that register_error_handlers adds all required handlers."""
    app = FastAPI()
    
    # Register handlers
    register_error_handlers(app)
    
    # Verify handlers are registered
    # FastAPI stores exception handlers in app.exception_handlers
    assert len(app.exception_handlers) > 0
    
    # Check that key exception types are registered
    exception_types = list(app.exception_handlers.keys())
    
    # Should have handlers for APIError or Exception (base handler)
    assert APIError in exception_types or Exception in exception_types


def test_api_error_handler_integration():
    """Test that APIError is properly handled by the registered handler."""
    app = FastAPI()
    register_error_handlers(app)
    
    @app.get("/test-not-found")
    async def test_endpoint():
        raise NotFoundError("Design", "123")
    
    client = TestClient(app)
    response = client.get("/test-not-found")
    
    assert response.status_code == 404
    data = response.json()
    
    # Verify error response structure
    assert "message" in data
    assert "error_code" in data
    assert "request_id" in data
    assert data["message"] == "Design with id 123 not found"
    assert data["error_code"] == "NOT_FOUND"


def test_validation_error_handler_integration():
    """Test that Pydantic validation errors are properly handled."""
    app = FastAPI()
    register_error_handlers(app)
    
    class TestModel(BaseModel):
        name: str = Field(..., min_length=3)
        age: int = Field(..., gt=0)
    
    @app.post("/test-validation")
    async def test_endpoint(data: TestModel):
        return {"success": True}
    
    client = TestClient(app)
    
    # Send invalid data
    response = client.post("/test-validation", json={"name": "ab", "age": -1})
    
    assert response.status_code == 422
    data = response.json()
    
    # Verify error response structure
    assert "message" in data
    assert "error_code" in data
    assert "details" in data
    assert "errors" in data["details"]
    assert data["error_code"] == "VALIDATION_ERROR"
    
    # Verify validation errors are formatted
    errors = data["details"]["errors"]
    assert len(errors) > 0
    assert all("field" in err and "message" in err for err in errors)


def test_sqlalchemy_error_handler_integration():
    """Test that SQLAlchemy errors are properly handled."""
    app = FastAPI()
    register_error_handlers(app)
    
    @app.get("/test-db-error")
    async def test_endpoint():
        # Simulate a database error
        raise OperationalError("statement", {}, Exception("Database connection failed"))
    
    client = TestClient(app)
    response = client.get("/test-db-error")
    
    assert response.status_code == 500
    data = response.json()
    
    # Verify error response structure
    assert "message" in data
    assert "error_code" in data
    assert "request_id" in data
    assert data["error_code"] == "DATABASE_ERROR"


def test_sqlalchemy_integrity_error_handler():
    """Test that SQLAlchemy IntegrityError is handled as conflict."""
    app = FastAPI()
    register_error_handlers(app)
    
    @app.post("/test-integrity-error")
    async def test_endpoint():
        # Simulate an integrity constraint violation
        raise IntegrityError("statement", {}, Exception("UNIQUE constraint failed"))
    
    client = TestClient(app)
    response = client.post("/test-integrity-error")
    
    assert response.status_code == 409
    data = response.json()
    
    # Verify error response structure
    assert "message" in data
    assert "error_code" in data
    assert data["error_code"] == "CONFLICT"


def test_general_exception_handler_integration():
    """Test that unhandled exceptions are caught by general handler."""
    app = FastAPI()
    register_error_handlers(app)
    
    @app.get("/test-general-error")
    async def test_endpoint():
        raise RuntimeError("Unexpected error")
    
    client = TestClient(app, raise_server_exceptions=False)
    response = client.get("/test-general-error")
    
    assert response.status_code == 500
    data = response.json()
    
    # Verify error response structure
    assert "message" in data
    assert "error_code" in data
    assert "request_id" in data
    assert data["error_code"] == "INTERNAL_SERVER_ERROR"
    assert data["message"] == "An unexpected error occurred"


def test_custom_request_id_preserved():
    """Test that custom X-Request-ID header is preserved in error response."""
    app = FastAPI()
    register_error_handlers(app)
    
    @app.get("/test-request-id")
    async def test_endpoint():
        raise NotFoundError("Design", "456")
    
    client = TestClient(app)
    custom_id = "test-request-123"
    response = client.get("/test-request-id", headers={"X-Request-ID": custom_id})
    
    assert response.status_code == 404
    data = response.json()
    
    # Should use the custom request ID
    assert data["request_id"] == custom_id


def test_authentication_error_handler():
    """Test that AuthenticationError is properly handled."""
    app = FastAPI()
    register_error_handlers(app)
    
    @app.get("/test-auth")
    async def test_endpoint():
        raise AuthenticationError("Invalid token")
    
    client = TestClient(app)
    response = client.get("/test-auth")
    
    assert response.status_code == 401
    data = response.json()
    
    assert "message" in data
    assert "error_code" in data
    assert data["message"] == "Invalid token"
    assert data["error_code"] == "AUTHENTICATION_ERROR"


def test_database_error_handler():
    """Test that DatabaseError is properly handled."""
    app = FastAPI()
    register_error_handlers(app)
    
    @app.get("/test-db")
    async def test_endpoint():
        raise DatabaseError("Connection failed")
    
    client = TestClient(app)
    response = client.get("/test-db")
    
    assert response.status_code == 500
    data = response.json()
    
    assert "message" in data
    assert "error_code" in data
    assert data["message"] == "Connection failed"
    assert data["error_code"] == "DATABASE_ERROR"


def test_error_response_excludes_none():
    """Test that error responses don't include None values."""
    app = FastAPI()
    register_error_handlers(app)
    
    @app.get("/test-no-details")
    async def test_endpoint():
        # Raise error without details
        raise NotFoundError("Design", "789")
    
    client = TestClient(app)
    response = client.get("/test-no-details")
    
    data = response.json()
    
    # Verify no None values in response
    for key, value in data.items():
        assert value is not None


def test_multiple_handlers_dont_conflict():
    """Test that multiple error handlers can coexist."""
    app = FastAPI()
    register_error_handlers(app)
    
    @app.get("/test-not-found")
    async def test_not_found():
        raise NotFoundError("Design", "123")
    
    @app.get("/test-validation")
    async def test_validation():
        raise CustomValidationError("Invalid input")
    
    @app.get("/test-auth")
    async def test_auth():
        raise AuthenticationError("Unauthorized")
    
    client = TestClient(app)
    
    # Test each endpoint
    response1 = client.get("/test-not-found")
    assert response1.status_code == 404
    assert response1.json()["error_code"] == "NOT_FOUND"
    
    response2 = client.get("/test-validation")
    assert response2.status_code == 422
    assert response2.json()["error_code"] == "VALIDATION_ERROR"
    
    response3 = client.get("/test-auth")
    assert response3.status_code == 401
    assert response3.json()["error_code"] == "AUTHENTICATION_ERROR"
