"""FastAPI exception handlers for standardized error responses."""

import logging
from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

from fastapi import Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError, IntegrityError

from .base import APIError
from .responses import ErrorResponse, ErrorType

logger = logging.getLogger(__name__)


def get_request_id(request: Request) -> str:
    """Get or generate a request ID for tracking."""
    return request.headers.get("X-Request-ID", str(uuid4()))


def get_service_name() -> str:
    """Get service name from environment or default."""
    import os
    return os.getenv("SERVICE_NAME", "unknown-service")


def create_error_context(request: Request, exc: Exception) -> dict:
    """Create standardized error logging context."""
    return {
        "request_id": get_request_id(request),
        "service": get_service_name(),
        "method": request.method,
        "path": request.url.path,
        "client_ip": request.client.host if request.client else "unknown",
        "user_agent": request.headers.get("User-Agent", "unknown"),
        "exception_type": type(exc).__name__,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


async def api_error_handler(request: Request, exc: APIError) -> JSONResponse:
    """Handle APIError exceptions with standardized response.
    
    Args:
        request: FastAPI request object
        exc: APIError exception
        
    Returns:
        JSONResponse with error details
    """
    context = create_error_context(request, exc)
    
    # Log with appropriate level based on status code
    log_level = logging.WARNING if exc.status_code < 500 else logging.ERROR
    logger.log(
        log_level,
        f"API Error: {exc.message}",
        extra={
            **context,
            "error_code": exc.error_code,
            "status_code": exc.status_code,
            "details": exc.details,
        },
    )
    
    error_response = ErrorResponse(
        message=exc.message,
        error_code=exc.error_code,
        details=exc.details,
        request_id=context["request_id"],
        timestamp=context["timestamp"],
        service=context["service"],
    )
    
    # Add retry-after header for rate limiting and service unavailable errors
    headers = {}
    if exc.details and "retry_after" in exc.details:
        headers["Retry-After"] = str(exc.details["retry_after"])
    
    return JSONResponse(
        status_code=exc.status_code,
        content=error_response.model_dump(exclude_none=True),
        headers=headers,
    )


async def validation_error_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Handle FastAPI's RequestValidationError with standardized response.
    
    Args:
        request: FastAPI request object
        exc: RequestValidationError exception
        
    Returns:
        JSONResponse with validation error details
    """
    context = create_error_context(request, exc)
    
    # Format validation errors
    errors = []
    for error in exc.errors():
        field = ".".join(str(loc) for loc in error["loc"])
        errors.append({
            "field": field,
            "message": error["msg"],
            "type": error["type"],
            "input": error.get("input"),
        })
    
    logger.warning(
        "Validation error",
        extra={
            **context,
            "validation_errors": errors,
        },
    )
    
    error_response = ErrorResponse(
        message="Request validation failed",
        error_code=ErrorType.VALIDATION_ERROR,
        details={"errors": errors},
        request_id=context["request_id"],
        timestamp=context["timestamp"],
        service=context["service"],
    )
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=error_response.model_dump(exclude_none=True),
    )


async def sqlalchemy_error_handler(
    request: Request, exc: SQLAlchemyError
) -> JSONResponse:
    """Handle SQLAlchemy errors with standardized response.
    
    Args:
        request: FastAPI request object
        exc: SQLAlchemyError exception
        
    Returns:
        JSONResponse with database error details
    """
    context = create_error_context(request, exc)
    
    # Determine error message based on exception type
    if isinstance(exc, IntegrityError):
        message = "Database integrity constraint violation"
        error_code = ErrorType.CONFLICT
        status_code = status.HTTP_409_CONFLICT
        
        # Extract constraint details if available
        details = {"constraint_type": "integrity"}
        if hasattr(exc, "orig") and exc.orig:
            details["database_error"] = str(exc.orig)
    else:
        message = "Database error occurred"
        error_code = ErrorType.DATABASE_ERROR
        status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        details = {"database_error_type": type(exc).__name__}
    
    logger.error(
        f"Database error: {str(exc)}",
        extra={
            **context,
            "database_error_details": str(exc),
        },
        exc_info=True,
    )
    
    error_response = ErrorResponse(
        message=message,
        error_code=error_code,
        details=details,
        request_id=context["request_id"],
        timestamp=context["timestamp"],
        service=context["service"],
    )
    
    return JSONResponse(
        status_code=status_code,
        content=error_response.model_dump(exclude_none=True),
    )


async def general_exception_handler(
    request: Request, exc: Exception
) -> JSONResponse:
    """Handle any unhandled exceptions with standardized response.
    
    Args:
        request: FastAPI request object
        exc: Exception
        
    Returns:
        JSONResponse with generic error details
    """
    context = create_error_context(request, exc)
    
    logger.error(
        f"Unhandled exception: {str(exc)}",
        extra={
            **context,
            "exception_details": str(exc),
        },
        exc_info=True,
    )
    
    error_response = ErrorResponse(
        message="An unexpected error occurred",
        error_code=ErrorType.INTERNAL_SERVER_ERROR,
        details={"exception_type": type(exc).__name__},
        request_id=context["request_id"],
        timestamp=context["timestamp"],
        service=context["service"],
    )
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=error_response.model_dump(exclude_none=True),
    )


def register_error_handlers(app):
    """Register all error handlers with a FastAPI application.
    
    Args:
        app: FastAPI application instance
    """
    app.add_exception_handler(APIError, api_error_handler)
    app.add_exception_handler(RequestValidationError, validation_error_handler)
    app.add_exception_handler(SQLAlchemyError, sqlalchemy_error_handler)
    app.add_exception_handler(Exception, general_exception_handler)
