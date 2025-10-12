"""Error response models and types."""

from enum import Enum
from typing import Any, Dict, Optional

from pydantic import BaseModel, ConfigDict, Field


class ErrorType(str, Enum):
    """Standard error types across all services."""
    
    # Client errors (4xx)
    VALIDATION_ERROR = "VALIDATION_ERROR"
    AUTHENTICATION_ERROR = "AUTHENTICATION_ERROR"
    AUTHORIZATION_ERROR = "AUTHORIZATION_ERROR"
    NOT_FOUND = "NOT_FOUND"
    CONFLICT = "CONFLICT"
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"
    BAD_REQUEST = "BAD_REQUEST"
    
    # Server errors (5xx)
    DATABASE_ERROR = "DATABASE_ERROR"
    EXTERNAL_SERVICE_ERROR = "EXTERNAL_SERVICE_ERROR"
    INTERNAL_SERVER_ERROR = "INTERNAL_SERVER_ERROR"
    
    # Service-specific errors
    LLM_SERVICE_ERROR = "LLM_SERVICE_ERROR"
    VECTOR_SEARCH_ERROR = "VECTOR_SEARCH_ERROR"
    PDF_PROCESSING_ERROR = "PDF_PROCESSING_ERROR"


class ErrorResponse(BaseModel):
    """Standard error response model for all services."""
    
    model_config = ConfigDict(from_attributes=True)
    
    message: str = Field(..., description="Human-readable error message")
    error_code: str = Field(..., description="Machine-readable error code")
    details: Optional[Dict[str, Any]] = Field(
        None, description="Additional error details"
    )
    request_id: Optional[str] = Field(
        None, description="Request ID for tracking"
    )
    
    @classmethod
    def from_exception(
        cls,
        message: str,
        error_code: str,
        details: Optional[Dict[str, Any]] = None,
        request_id: Optional[str] = None,
    ) -> "ErrorResponse":
        """Create an ErrorResponse from exception details."""
        return cls(
            message=message,
            error_code=error_code,
            details=details,
            request_id=request_id,
        )


class ValidationErrorDetail(BaseModel):
    """Detailed validation error information."""
    
    model_config = ConfigDict(from_attributes=True)
    
    field: str = Field(..., description="Field that failed validation")
    message: str = Field(..., description="Validation error message")
    type: str = Field(..., description="Type of validation error")
