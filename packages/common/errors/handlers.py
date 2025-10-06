"""FastAPI exception handlers for standardized error responses."""

import logging
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


async def api_error_handler(request: Request, exc: APIError) -> JSONResponse:
    """Handle APIError exceptions with standardized response.
    
    Args:
        request: FastAPI request object
        exc: APIError exception
        
    Returns:
        JSONResponse with error details
    """
    request_id = get_request_id(request)
    
    logger.error(
        f"API Error: {exc.message}",
        extra={
            "error_code": exc.error_code,
            "status_code": exc.status_code,
            "request_id": request_id,
            "details": exc.details,
        },
    )
    
    error_response = ErrorResponse(
        message=exc.message,
        error_code=exc.error_code,
        details=exc.details,
        request_id=request_id,
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content=error_response.model_dump(exclude_none=True),
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
    request_id = get_request_id(request)
    
    # Format validation errors
    errors = []
    for error in exc.errors():
        field = ".".join(str(loc) for loc in error["loc"])
        errors.append({
            "field": field,
            "message": error["msg"],
            "type": error["type"],
        })
    
    logger.warning(
        "Validation error",
        extra={
            "request_id": request_id,
            "errors": errors,
        },
    )
    
    error_response = ErrorResponse(
        message="Validation error",
        error_code=ErrorType.VALIDATION_ERROR,
        details={"errors": errors},
        request_id=request_id,
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
    request_id = get_request_id(request)
    
    # Determine error message based on exception type
    if isinstance(exc, IntegrityError):
        message = "Database integrity constraint violation"
        error_code = ErrorType.CONFLICT
        status_code = status.HTTP_409_CONFLICT
    else:
        message = "Database error occurred"
        error_code = ErrorType.DATABASE_ERROR
        status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    
    logger.error(
        f"Database error: {str(exc)}",
        extra={
            "request_id": request_id,
            "exception_type": type(exc).__name__,
        },
        exc_info=True,
    )
    
    error_response = ErrorResponse(
        message=message,
        error_code=error_code,
        request_id=request_id,
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
    request_id = get_request_id(request)
    
    logger.error(
        f"Unhandled exception: {str(exc)}",
        extra={
            "request_id": request_id,
            "exception_type": type(exc).__name__,
        },
        exc_info=True,
    )
    
    error_response = ErrorResponse(
        message="An unexpected error occurred",
        error_code=ErrorType.INTERNAL_SERVER_ERROR,
        request_id=request_id,
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
