"""Error handlers for the vendor service API."""

import logging
from typing import Any, Dict

from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from src.core.exceptions import VendorServiceError

logger = logging.getLogger(__name__)


async def vendor_service_error_handler(
    request: Request, exc: VendorServiceError
) -> JSONResponse:
    """Handle custom vendor service errors."""
    logger.error(
        f"Vendor service error: {exc.message}",
        extra={
            "error_code": exc.error_code,
            "path": request.url.path,
            "method": request.method,
        },
    )

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.error_code,
                "message": exc.message,
                "type": "vendor_service_error",
            }
        },
    )


async def validation_error_handler(request: Request, exc: ValueError) -> JSONResponse:
    """Handle validation errors."""
    logger.warning(
        f"Validation error: {str(exc)}",
        extra={
            "path": request.url.path,
            "method": request.method,
        },
    )

    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": str(exc),
                "type": "validation_error",
            }
        },
    )


async def integrity_error_handler(
    request: Request, exc: IntegrityError
) -> JSONResponse:
    """Handle database integrity constraint violations."""
    logger.error(
        f"Database integrity error: {str(exc)}",
        extra={
            "path": request.url.path,
            "method": request.method,
        },
    )

    # Extract meaningful error messages from common constraint violations
    error_message = "Data integrity constraint violation"
    error_code = "INTEGRITY_ERROR"

    if "Duplicate entry" in str(exc):
        error_message = "Resource already exists"
        error_code = "DUPLICATE_RESOURCE"
    elif "foreign key constraint" in str(exc).lower():
        error_message = "Referenced resource not found"
        error_code = "FOREIGN_KEY_ERROR"
    elif "cannot be null" in str(exc).lower():
        error_message = "Required field is missing"
        error_code = "MISSING_REQUIRED_FIELD"

    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={
            "error": {
                "code": error_code,
                "message": error_message,
                "type": "integrity_error",
            }
        },
    )


async def database_error_handler(
    request: Request, exc: SQLAlchemyError
) -> JSONResponse:
    """Handle general database errors."""
    logger.error(
        f"Database error: {str(exc)}",
        extra={
            "path": request.url.path,
            "method": request.method,
        },
    )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "code": "DATABASE_ERROR",
                "message": "An error occurred while processing your request",
                "type": "database_error",
            }
        },
    )


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Handle FastAPI HTTP exceptions with consistent format."""
    logger.warning(
        f"HTTP exception: {exc.detail}",
        extra={
            "status_code": exc.status_code,
            "path": request.url.path,
            "method": request.method,
        },
    )

    # Map status codes to error codes
    status_code_map = {
        400: "BAD_REQUEST",
        401: "UNAUTHORIZED",
        403: "FORBIDDEN",
        404: "NOT_FOUND",
        405: "METHOD_NOT_ALLOWED",
        409: "CONFLICT",
        422: "UNPROCESSABLE_ENTITY",
        429: "TOO_MANY_REQUESTS",
        500: "INTERNAL_SERVER_ERROR",
    }

    error_code = status_code_map.get(exc.status_code, "HTTP_ERROR")

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": error_code,
                "message": exc.detail,
                "type": "http_error",
            }
        },
    )


async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle unexpected exceptions."""
    logger.error(
        f"Unexpected error: {str(exc)}",
        extra={
            "path": request.url.path,
            "method": request.method,
            "exception_type": type(exc).__name__,
        },
        exc_info=True,
    )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "An unexpected error occurred",
                "type": "internal_error",
            }
        },
    )


def get_error_handlers() -> Dict[Any, Any]:
    """Get all error handlers for the application."""
    return {
        VendorServiceError: vendor_service_error_handler,
        ValueError: validation_error_handler,
        IntegrityError: integrity_error_handler,
        SQLAlchemyError: database_error_handler,
        HTTPException: http_exception_handler,
        Exception: general_exception_handler,
    }
