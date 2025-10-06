"""Base exception classes for all services."""

from typing import Any, Dict, Optional

from fastapi import status

from .responses import ErrorType


class APIError(Exception):
    """Base exception for all API errors."""
    
    def __init__(
        self,
        message: str,
        error_code: str,
        status_code: int = status.HTTP_400_BAD_REQUEST,
        details: Optional[Dict[str, Any]] = None,
    ):
        """Initialize an API error.
        
        Args:
            message: Human-readable error message
            error_code: Machine-readable error code
            status_code: HTTP status code to return
            details: Optional additional error details
        """
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        self.details = details or {}
        super().__init__(message)


class ValidationError(APIError):
    """Validation error for invalid input data."""
    
    def __init__(
        self,
        message: str = "Validation error",
        details: Optional[Dict[str, Any]] = None,
    ):
        """Initialize a validation error.
        
        Args:
            message: Description of the validation error
            details: Dictionary with validation error details
        """
        super().__init__(
            message=message,
            error_code=ErrorType.VALIDATION_ERROR,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            details=details,
        )


class AuthenticationError(APIError):
    """Authentication error for failed authentication attempts."""
    
    def __init__(self, message: str = "Authentication failed"):
        """Initialize an authentication error.
        
        Args:
            message: Description of the authentication failure
        """
        super().__init__(
            message=message,
            error_code=ErrorType.AUTHENTICATION_ERROR,
            status_code=status.HTTP_401_UNAUTHORIZED,
        )


class AuthorizationError(APIError):
    """Authorization error for insufficient permissions."""
    
    def __init__(self, message: str = "Insufficient permissions"):
        """Initialize an authorization error.
        
        Args:
            message: Description of the authorization failure
        """
        super().__init__(
            message=message,
            error_code=ErrorType.AUTHORIZATION_ERROR,
            status_code=status.HTTP_403_FORBIDDEN,
        )


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
            error_code=ErrorType.NOT_FOUND,
            status_code=status.HTTP_404_NOT_FOUND,
            details={"resource": resource, "resource_id": resource_id},
        )


class ConflictError(APIError):
    """Conflict error for duplicate resources or conflicting operations."""
    
    def __init__(
        self,
        message: str = "Resource conflict",
        details: Optional[Dict[str, Any]] = None,
    ):
        """Initialize a conflict error.
        
        Args:
            message: Description of the conflict
            details: Additional conflict details
        """
        super().__init__(
            message=message,
            error_code=ErrorType.CONFLICT,
            status_code=status.HTTP_409_CONFLICT,
            details=details,
        )


class DatabaseError(APIError):
    """Database operation error."""
    
    def __init__(
        self,
        message: str = "Database error occurred",
        details: Optional[Dict[str, Any]] = None,
    ):
        """Initialize a database error.
        
        Args:
            message: Description of the database error
            details: Additional error details
        """
        super().__init__(
            message=message,
            error_code=ErrorType.DATABASE_ERROR,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details=details,
        )


class RateLimitError(APIError):
    """Rate limit exceeded error."""
    
    def __init__(
        self,
        message: str = "Rate limit exceeded",
        retry_after: Optional[int] = None,
    ):
        """Initialize a rate limit error.
        
        Args:
            message: Description of the rate limit error
            retry_after: Seconds until the rate limit resets
        """
        details = {"retry_after": retry_after} if retry_after else None
        super().__init__(
            message=message,
            error_code=ErrorType.RATE_LIMIT_EXCEEDED,
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            details=details,
        )


class ExternalServiceError(APIError):
    """External service error for third-party service failures."""
    
    def __init__(
        self,
        service_name: str,
        message: str = "External service error",
        details: Optional[Dict[str, Any]] = None,
    ):
        """Initialize an external service error.
        
        Args:
            service_name: Name of the external service
            message: Description of the error
            details: Additional error details
        """
        error_details = {"service": service_name}
        if details:
            error_details.update(details)
        
        super().__init__(
            message=message,
            error_code=ErrorType.EXTERNAL_SERVICE_ERROR,
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            details=error_details,
        )


class LLMServiceError(ExternalServiceError):
    """LLM service specific error."""
    
    def __init__(
        self,
        message: str = "LLM service error",
        details: Optional[Dict[str, Any]] = None,
    ):
        """Initialize an LLM service error.
        
        Args:
            message: Description of the error
            details: Additional error details
        """
        super().__init__(
            service_name="LLM",
            message=message,
            details=details,
        )
        self.error_code = ErrorType.LLM_SERVICE_ERROR


class VectorSearchError(ExternalServiceError):
    """Vector search service specific error."""
    
    def __init__(
        self,
        message: str = "Vector search error",
        details: Optional[Dict[str, Any]] = None,
    ):
        """Initialize a vector search error.
        
        Args:
            message: Description of the error
            details: Additional error details
        """
        super().__init__(
            service_name="VectorSearch",
            message=message,
            details=details,
        )
        self.error_code = ErrorType.VECTOR_SEARCH_ERROR
