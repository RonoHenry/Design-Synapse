"""Knowledge Service specific error handlers."""

import logging
import sys
from pathlib import Path
from typing import Any, Dict

from fastapi import Request, status
from fastapi.responses import JSONResponse

# Add the packages directory to the Python path
packages_path = Path(__file__).parent.parent.parent.parent.parent / "packages"
sys.path.insert(0, str(packages_path))

from common.errors.base import APIError
from common.errors.handlers import (create_error_context, get_request_id,
                                    get_service_name)
from common.errors.responses import ErrorResponse, ErrorType

from ..core.error_handling import map_internal_to_api_error
from ..exceptions import (BatchProcessingError, ContentProcessingError,
                          EmbeddingGenerationError, FileFormatError,
                          FileSizeError, FileValidationError, IndexingError,
                          KnowledgeServiceError, LLMServiceError,
                          MetadataValidationError, PDFProcessingError,
                          SearchQueryError, TextExtractionError,
                          VectorSearchError)

logger = logging.getLogger(__name__)


async def knowledge_service_error_handler(
    request: Request, exc: KnowledgeServiceError
) -> JSONResponse:
    """Handle knowledge service specific errors.

    Args:
        request: FastAPI request object
        exc: Knowledge service exception

    Returns:
        JSONResponse with error details
    """
    context = create_error_context(request, exc)

    # Map internal error to API error
    api_error = map_internal_to_api_error(exc)

    # Log with appropriate level
    log_level = logging.WARNING if api_error.status_code < 500 else logging.ERROR
    logger.log(
        log_level,
        f"Knowledge Service Error: {api_error.message}",
        extra={
            **context,
            "error_code": api_error.error_code,
            "status_code": api_error.status_code,
            "details": api_error.details,
            "original_error_type": type(exc).__name__,
        },
    )

    error_response = ErrorResponse(
        message=api_error.message,
        error_code=api_error.error_code,
        details=api_error.details,
        request_id=context["request_id"],
        timestamp=context["timestamp"],
        service=context["service"],
    )

    return JSONResponse(
        status_code=api_error.status_code,
        content=error_response.model_dump(exclude_none=True),
    )


async def pdf_processing_error_handler(
    request: Request, exc: PDFProcessingError
) -> JSONResponse:
    """Handle PDF processing errors with specific context.

    Args:
        request: FastAPI request object
        exc: PDF processing exception

    Returns:
        JSONResponse with error details
    """
    context = create_error_context(request, exc)

    # Determine specific error type and status code
    if isinstance(exc, FileValidationError):
        if isinstance(exc, FileSizeError):
            error_code = ErrorType.PAYLOAD_TOO_LARGE
            status_code = status.HTTP_413_REQUEST_ENTITY_TOO_LARGE
        elif isinstance(exc, FileFormatError):
            error_code = ErrorType.VALIDATION_ERROR
            status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
        else:
            error_code = ErrorType.VALIDATION_ERROR
            status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    elif isinstance(exc, TextExtractionError):
        error_code = "TEXT_EXTRACTION_ERROR"
        status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    else:
        error_code = "PDF_PROCESSING_ERROR"
        status_code = status.HTTP_500_INTERNAL_SERVER_ERROR

    logger.warning(
        f"PDF Processing Error: {str(exc)}",
        extra={
            **context,
            "error_code": error_code,
            "status_code": status_code,
            "pdf_error_type": type(exc).__name__,
        },
    )

    error_response = ErrorResponse(
        message=str(exc),
        error_code=error_code,
        details={
            "processing_stage": "pdf_processing",
            "error_type": type(exc).__name__,
        },
        request_id=context["request_id"],
        timestamp=context["timestamp"],
        service=context["service"],
    )

    return JSONResponse(
        status_code=status_code,
        content=error_response.model_dump(exclude_none=True),
    )


async def vector_search_error_handler(
    request: Request, exc: VectorSearchError
) -> JSONResponse:
    """Handle vector search errors with specific context.

    Args:
        request: FastAPI request object
        exc: Vector search exception

    Returns:
        JSONResponse with error details
    """
    context = create_error_context(request, exc)

    # Determine specific error type and status code
    if isinstance(exc, SearchQueryError):
        error_code = ErrorType.VALIDATION_ERROR
        status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    elif isinstance(exc, IndexingError):
        error_code = ErrorType.EXTERNAL_SERVICE_ERROR
        status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    elif isinstance(exc, MetadataValidationError):
        error_code = ErrorType.VALIDATION_ERROR
        status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    else:
        error_code = ErrorType.VECTOR_SEARCH_ERROR
        status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    logger.error(
        f"Vector Search Error: {str(exc)}",
        extra={
            **context,
            "error_code": error_code,
            "status_code": status_code,
            "vector_error_type": type(exc).__name__,
        },
    )

    error_response = ErrorResponse(
        message=str(exc),
        error_code=error_code,
        details={
            "service": "vector_search",
            "error_type": type(exc).__name__,
        },
        request_id=context["request_id"],
        timestamp=context["timestamp"],
        service=context["service"],
    )

    return JSONResponse(
        status_code=status_code,
        content=error_response.model_dump(exclude_none=True),
    )


async def llm_service_error_handler(
    request: Request, exc: LLMServiceError
) -> JSONResponse:
    """Handle LLM service errors with specific context.

    Args:
        request: FastAPI request object
        exc: LLM service exception

    Returns:
        JSONResponse with error details
    """
    context = create_error_context(request, exc)

    # Determine specific error type
    if isinstance(exc, EmbeddingGenerationError):
        error_code = "EMBEDDING_GENERATION_ERROR"
        details = {"service": "embedding_generation"}
    else:
        error_code = ErrorType.LLM_SERVICE_ERROR
        details = {"service": "llm"}

    logger.error(
        f"LLM Service Error: {str(exc)}",
        extra={
            **context,
            "error_code": error_code,
            "status_code": status.HTTP_503_SERVICE_UNAVAILABLE,
            "llm_error_type": type(exc).__name__,
        },
    )

    error_response = ErrorResponse(
        message=str(exc),
        error_code=error_code,
        details=details,
        request_id=context["request_id"],
        timestamp=context["timestamp"],
        service=context["service"],
    )

    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content=error_response.model_dump(exclude_none=True),
    )


async def batch_processing_error_handler(
    request: Request, exc: BatchProcessingError
) -> JSONResponse:
    """Handle batch processing errors with specific context.

    Args:
        request: FastAPI request object
        exc: Batch processing exception

    Returns:
        JSONResponse with error details
    """
    context = create_error_context(request, exc)

    logger.error(
        f"Batch Processing Error: {str(exc)}",
        extra={
            **context,
            "error_code": "BATCH_PROCESSING_ERROR",
            "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
            "batch_error_type": type(exc).__name__,
        },
    )

    error_response = ErrorResponse(
        message=str(exc),
        error_code="BATCH_PROCESSING_ERROR",
        details={
            "service": "batch_processing",
            "error_type": type(exc).__name__,
        },
        request_id=context["request_id"],
        timestamp=context["timestamp"],
        service=context["service"],
    )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=error_response.model_dump(exclude_none=True),
    )


def register_knowledge_service_error_handlers(app):
    """Register knowledge service specific error handlers.

    Args:
        app: FastAPI application instance
    """
    # Register specific error handlers
    app.add_exception_handler(PDFProcessingError, pdf_processing_error_handler)
    app.add_exception_handler(VectorSearchError, vector_search_error_handler)
    app.add_exception_handler(LLMServiceError, llm_service_error_handler)
    app.add_exception_handler(BatchProcessingError, batch_processing_error_handler)

    # Register base knowledge service error handler (should be last)
    app.add_exception_handler(KnowledgeServiceError, knowledge_service_error_handler)

    logger.info("Knowledge service error handlers registered")
