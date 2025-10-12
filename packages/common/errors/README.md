# Shared Error Handling

This package provides standardized error handling classes and utilities for all services in the DesignSynapse platform.

## Features

- **Standardized Error Types**: Consistent error codes across all services
- **Structured Error Responses**: Uniform JSON error response format
- **Request Tracking**: Automatic request ID generation for error tracking
- **Comprehensive Logging**: Detailed error logging with context
- **FastAPI Integration**: Ready-to-use exception handlers

## Usage

### Basic Setup

```python
from fastapi import FastAPI
from common.errors import register_error_handlers

app = FastAPI()

# Register all error handlers
register_error_handlers(app)
```

### Raising Errors

```python
from common.errors import (
    NotFoundError,
    ValidationError,
    AuthenticationError,
    AuthorizationError,
)

# Not found error
raise NotFoundError("User", user_id)

# Validation error with details
raise ValidationError(
    message="Invalid input data",
    details={"field": "email", "error": "Invalid email format"}
)

# Authentication error
raise AuthenticationError("Invalid credentials")

# Authorization error
raise AuthorizationError("Admin role required")
```

### Custom Error Details

```python
from common.errors import APIError, ErrorType
from fastapi import status

# Create a custom error
raise APIError(
    message="Custom error message",
    error_code=ErrorType.BAD_REQUEST,
    status_code=status.HTTP_400_BAD_REQUEST,
    details={"custom_field": "custom_value"}
)
```

## Available Error Classes

### Client Errors (4xx)

- `ValidationError`: Invalid input data (422)
- `AuthenticationError`: Failed authentication (401)
- `AuthorizationError`: Insufficient permissions (403)
- `NotFoundError`: Resource not found (404)
- `ConflictError`: Resource conflict (409)
- `RateLimitError`: Rate limit exceeded (429)

### Server Errors (5xx)

- `DatabaseError`: Database operation error (500)
- `ExternalServiceError`: Third-party service error (503)
- `LLMServiceError`: LLM service specific error (503)
- `VectorSearchError`: Vector search service error (503)

## Error Response Format

All errors return a standardized JSON response:

```json
{
  "message": "Human-readable error message",
  "error_code": "MACHINE_READABLE_CODE",
  "details": {
    "additional": "context"
  },
  "request_id": "uuid-for-tracking"
}
```

## Error Handlers

The package provides handlers for:

- `APIError`: Custom API errors
- `RequestValidationError`: Pydantic validation errors
- `SQLAlchemyError`: Database errors
- `Exception`: Catch-all for unhandled exceptions

## Best Practices

1. **Use Specific Error Types**: Choose the most appropriate error class
2. **Provide Context**: Include relevant details in the `details` parameter
3. **Log Appropriately**: Errors are automatically logged with context
4. **Track Requests**: Use request IDs for debugging and monitoring
5. **Don't Expose Internals**: Keep error messages user-friendly

## Example: Service Integration

```python
from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
from common.errors import (
    NotFoundError,
    ValidationError,
    register_error_handlers,
)

app = FastAPI()
register_error_handlers(app)

@app.get("/users/{user_id}")
def get_user(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        raise NotFoundError("User", str(user_id))
    
    return user

@app.post("/users")
def create_user(user_data: UserCreate, db: Session = Depends(get_db)):
    # Check for existing user
    existing = db.query(User).filter(User.email == user_data.email).first()
    
    if existing:
        raise ValidationError(
            message="User with this email already exists",
            details={"email": user_data.email}
        )
    
    user = User(**user_data.dict())
    db.add(user)
    db.commit()
    
    return user
```

## Testing

```python
import pytest
from fastapi.testclient import TestClient
from common.errors import NotFoundError

def test_not_found_error(client: TestClient):
    response = client.get("/users/999")
    
    assert response.status_code == 404
    data = response.json()
    assert data["error_code"] == "NOT_FOUND"
    assert "request_id" in data
```
