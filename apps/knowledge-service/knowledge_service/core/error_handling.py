"""Enhanced error handling utilities for the Knowledge Service."""

import functools
import logging
import sys
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Callable, Dict, Optional, Type, Union

# Add the packages directory to the Python path
packages_path = Path(__file__).parent.parent.parent.parent.parent / "packages"
sys.path.insert(0, str(packages_path))

from common.errors.base import (APIError, DatabaseError, ExternalServiceError,
                                LLMServiceError, ValidationError,
                                VectorSearchError)

from ..exceptions import (BatchProcessingError, ContentProcessingError,
                          FileValidationError, KnowledgeServiceError,
                          PDFProcessingError)
from .logging import get_logger, log_service_operation

logger = get_logger(__name__)


def handle_service_errors(
    service_name: str, operation: str, reraise_as: Optional[Type[Exception]] = None
):
    """Decorator to handle service-level errors with consistent logging and error transformation.

    Args:
        service_name: Name of the service for logging
        operation: Name of the operation for logging
        reraise_as: Optional exception type to reraise as
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs) -> Any:
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                duration_ms = (time.time() - start_time) * 1000

                log_service_operation(
                    operation=operation,
                    service=service_name,
                    success=True,
                    duration_ms=duration_ms,
                )

                return result

            except Exception as e:
                duration_ms = (time.time() - start_time) * 1000
                error_msg = str(e)

                # Log the error with context
                log_service_operation(
                    operation=operation,
                    service=service_name,
                    success=False,
                    duration_ms=duration_ms,
                    error=error_msg,
                )

                # Transform error if needed
                if reraise_as:
                    raise reraise_as(f"{operation} failed: {error_msg}") from e

                # Re-raise original exception
                raise

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs) -> Any:
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                duration_ms = (time.time() - start_time) * 1000

                log_service_operation(
                    operation=operation,
                    service=service_name,
                    success=True,
                    duration_ms=duration_ms,
                )

                return result

            except Exception as e:
                duration_ms = (time.time() - start_time) * 1000
                error_msg = str(e)

                # Log the error with context
                log_service_operation(
                    operation=operation,
                    service=service_name,
                    success=False,
                    duration_ms=duration_ms,
                    error=error_msg,
                )

                # Transform error if needed
                if reraise_as:
                    raise reraise_as(f"{operation} failed: {error_msg}") from e

                # Re-raise original exception
                raise

        # Return appropriate wrapper based on function type
        if hasattr(func, "__code__") and func.__code__.co_flags & 0x80:  # CO_COROUTINE
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


@contextmanager
def error_context(operation: str, service: str = "knowledge-service", **context_data):
    """Context manager for error handling with structured logging.

    Args:
        operation: Name of the operation
        service: Name of the service
        **context_data: Additional context data for logging
    """
    start_time = time.time()
    operation_logger = get_logger(f"knowledge_service.{service}")

    try:
        operation_logger.info(
            f"Starting {operation}",
            extra={"operation": operation, "service": service, **context_data},
        )

        yield

        duration_ms = (time.time() - start_time) * 1000
        operation_logger.info(
            f"Completed {operation}",
            extra={
                "operation": operation,
                "service": service,
                "duration_ms": duration_ms,
                "success": True,
                **context_data,
            },
        )

    except Exception as e:
        duration_ms = (time.time() - start_time) * 1000
        operation_logger.error(
            f"Failed {operation}: {str(e)}",
            extra={
                "operation": operation,
                "service": service,
                "duration_ms": duration_ms,
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__,
                **context_data,
            },
            exc_info=True,
        )
        raise


def map_internal_to_api_error(error: Exception) -> APIError:
    """Map internal service errors to standardized API errors.

    Args:
        error: Internal service error

    Returns:
        Mapped API error
    """
    error_msg = str(error)

    # File validation errors
    if isinstance(error, FileValidationError):
        return ValidationError(
            message=error_msg,
            details={
                "validation_type": "file",
                "error_code": getattr(error, "error_code", None),
            },
        )

    # PDF processing errors
    if isinstance(error, PDFProcessingError):
        return APIError(
            message=f"PDF processing failed: {error_msg}",
            error_code="PDF_PROCESSING_ERROR",
            status_code=422,
            details={"processing_error": error_msg},
        )

    # Content processing errors
    if isinstance(error, ContentProcessingError):
        return APIError(
            message=f"Content processing failed: {error_msg}",
            error_code="CONTENT_PROCESSING_ERROR",
            status_code=422,
            details={"processing_error": error_msg},
        )

    # Batch processing errors
    if isinstance(error, BatchProcessingError):
        return APIError(
            message=f"Batch processing failed: {error_msg}",
            error_code="BATCH_PROCESSING_ERROR",
            status_code=500,
            details={"batch_error": error_msg},
        )

    # Generic knowledge service errors
    if isinstance(error, KnowledgeServiceError):
        return APIError(
            message=error_msg,
            error_code=getattr(error, "error_code", "KNOWLEDGE_SERVICE_ERROR"),
            status_code=500,
            details={"service_error": error_msg},
        )

    # Default mapping for unknown errors
    return APIError(
        message="An unexpected error occurred",
        error_code="INTERNAL_SERVER_ERROR",
        status_code=500,
        details={"original_error": error_msg, "error_type": type(error).__name__},
    )


class ErrorRecovery:
    """Utilities for error recovery and resilience."""

    @staticmethod
    def with_retry(
        max_attempts: int = 3,
        delay_seconds: float = 1.0,
        backoff_multiplier: float = 2.0,
        exceptions: tuple = (Exception,),
    ):
        """Decorator for retrying operations with exponential backoff.

        Args:
            max_attempts: Maximum number of retry attempts
            delay_seconds: Initial delay between retries
            backoff_multiplier: Multiplier for exponential backoff
            exceptions: Tuple of exceptions to retry on
        """

        def decorator(func: Callable) -> Callable:
            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs) -> Any:
                last_exception = None
                delay = delay_seconds

                for attempt in range(max_attempts):
                    try:
                        return await func(*args, **kwargs)
                    except exceptions as e:
                        last_exception = e

                        if attempt == max_attempts - 1:
                            logger.error(
                                f"Operation failed after {max_attempts} attempts: {str(e)}",
                                extra={
                                    "function": func.__name__,
                                    "attempt": attempt + 1,
                                    "max_attempts": max_attempts,
                                    "error": str(e),
                                },
                            )
                            raise

                        logger.warning(
                            f"Operation failed, retrying in {delay}s (attempt {attempt + 1}/{max_attempts}): {str(e)}",
                            extra={
                                "function": func.__name__,
                                "attempt": attempt + 1,
                                "max_attempts": max_attempts,
                                "delay_seconds": delay,
                                "error": str(e),
                            },
                        )

                        await asyncio.sleep(delay)
                        delay *= backoff_multiplier

                raise last_exception

            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs) -> Any:
                import time

                last_exception = None
                delay = delay_seconds

                for attempt in range(max_attempts):
                    try:
                        return func(*args, **kwargs)
                    except exceptions as e:
                        last_exception = e

                        if attempt == max_attempts - 1:
                            logger.error(
                                f"Operation failed after {max_attempts} attempts: {str(e)}",
                                extra={
                                    "function": func.__name__,
                                    "attempt": attempt + 1,
                                    "max_attempts": max_attempts,
                                    "error": str(e),
                                },
                            )
                            raise

                        logger.warning(
                            f"Operation failed, retrying in {delay}s (attempt {attempt + 1}/{max_attempts}): {str(e)}",
                            extra={
                                "function": func.__name__,
                                "attempt": attempt + 1,
                                "max_attempts": max_attempts,
                                "delay_seconds": delay,
                                "error": str(e),
                            },
                        )

                        time.sleep(delay)
                        delay *= backoff_multiplier

                raise last_exception

            # Return appropriate wrapper based on function type
            if (
                hasattr(func, "__code__") and func.__code__.co_flags & 0x80
            ):  # CO_COROUTINE
                return async_wrapper
            else:
                return sync_wrapper

        return decorator

    @staticmethod
    def with_fallback(fallback_value: Any = None, log_error: bool = True):
        """Decorator to provide fallback values on error.

        Args:
            fallback_value: Value to return on error
            log_error: Whether to log the error
        """

        def decorator(func: Callable) -> Callable:
            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs) -> Any:
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    if log_error:
                        logger.error(
                            f"Operation failed, using fallback: {str(e)}",
                            extra={
                                "function": func.__name__,
                                "fallback_value": fallback_value,
                                "error": str(e),
                            },
                        )
                    return fallback_value

            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs) -> Any:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if log_error:
                        logger.error(
                            f"Operation failed, using fallback: {str(e)}",
                            extra={
                                "function": func.__name__,
                                "fallback_value": fallback_value,
                                "error": str(e),
                            },
                        )
                    return fallback_value

            # Return appropriate wrapper based on function type
            if (
                hasattr(func, "__code__") and func.__code__.co_flags & 0x80
            ):  # CO_COROUTINE
                return async_wrapper
            else:
                return sync_wrapper

        return decorator


# Import asyncio for retry decorator
import asyncio
