"""Custom exceptions for the Knowledge Service."""
from typing import Optional, Dict, Any
from packages.common.errors.base import APIError


class KnowledgeServiceError(APIError):
    """Base exception for Knowledge Service errors."""
    pass


class ResourceNotFoundError(KnowledgeServiceError):
    """Raised when a resource is not found."""
    
    def __init__(self, resource_id: int, message: str = None):
        super().__init__(
            message=message or f"Resource with ID {resource_id} not found",
            error_code="RESOURCE_NOT_FOUND",
            status_code=404,
            details={"resource_id": resource_id}
        )


class TopicNotFoundError(KnowledgeServiceError):
    """Raised when a topic is not found."""
    
    def __init__(self, topic_id: int, message: str = None):
        super().__init__(
            message=message or f"Topic with ID {topic_id} not found",
            error_code="TOPIC_NOT_FOUND",
            status_code=404,
            details={"topic_id": topic_id}
        )


class BookmarkNotFoundError(KnowledgeServiceError):
    """Raised when a bookmark is not found."""
    
    def __init__(self, bookmark_id: int, message: str = None):
        super().__init__(
            message=message or f"Bookmark with ID {bookmark_id} not found",
            error_code="BOOKMARK_NOT_FOUND",
            status_code=404,
            details={"bookmark_id": bookmark_id}
        )


class FileProcessingError(KnowledgeServiceError):
    """Raised when file processing fails."""
    
    def __init__(self, filename: str, message: str = None, details: Dict[str, Any] = None):
        super().__init__(
            message=message or f"Failed to process file: {filename}",
            error_code="FILE_PROCESSING_ERROR",
            status_code=422,
            details={"filename": filename, **(details or {})}
        )


class UnsupportedFileTypeError(KnowledgeServiceError):
    """Raised when an unsupported file type is uploaded."""
    
    def __init__(self, filename: str, supported_types: list = None):
        super().__init__(
            message=f"Unsupported file type: {filename}",
            error_code="UNSUPPORTED_FILE_TYPE",
            status_code=400,
            details={
                "filename": filename,
                "supported_types": supported_types or []
            }
        )


class FileSizeExceededError(KnowledgeServiceError):
    """Raised when uploaded file exceeds size limit."""
    
    def __init__(self, filename: str, file_size: int, max_size: int):
        super().__init__(
            message=f"File size exceeds limit: {filename}",
            error_code="FILE_SIZE_EXCEEDED",
            status_code=413,
            details={
                "filename": filename,
                "file_size_bytes": file_size,
                "max_size_bytes": max_size
            }
        )


class VectorSearchError(KnowledgeServiceError):
    """Raised when vector search operations fail."""
    
    def __init__(self, message: str = None, details: Dict[str, Any] = None):
        super().__init__(
            message=message or "Vector search operation failed",
            error_code="VECTOR_SEARCH_ERROR",
            status_code=500,
            details=details or {}
        )


class LLMServiceError(KnowledgeServiceError):
    """Raised when LLM service operations fail."""
    
    def __init__(self, message: str = None, details: Dict[str, Any] = None):
        super().__init__(
            message=message or "LLM service operation failed",
            error_code="LLM_SERVICE_ERROR",
            status_code=500,
            details=details or {}
        )


class BatchProcessingError(KnowledgeServiceError):
    """Raised when batch processing operations fail."""
    
    def __init__(self, job_id: str = None, message: str = None, details: Dict[str, Any] = None):
        super().__init__(
            message=message or "Batch processing operation failed",
            error_code="BATCH_PROCESSING_ERROR",
            status_code=500,
            details={"job_id": job_id, **(details or {})}
        )


class ContentExtractionError(KnowledgeServiceError):
    """Raised when content extraction fails."""
    
    def __init__(self, filename: str, message: str = None, details: Dict[str, Any] = None):
        super().__init__(
            message=message or f"Failed to extract content from: {filename}",
            error_code="CONTENT_EXTRACTION_ERROR",
            status_code=422,
            details={"filename": filename, **(details or {})}
        )


class DuplicateResourceError(KnowledgeServiceError):
    """Raised when attempting to create a duplicate resource."""
    
    def __init__(self, identifier: str, message: str = None):
        super().__init__(
            message=message or f"Resource already exists: {identifier}",
            error_code="DUPLICATE_RESOURCE",
            status_code=409,
            details={"identifier": identifier}
        )


class InvalidSearchQueryError(KnowledgeServiceError):
    """Raised when search query is invalid."""
    
    def __init__(self, query: str, message: str = None, details: Dict[str, Any] = None):
        super().__init__(
            message=message or f"Invalid search query: {query}",
            error_code="INVALID_SEARCH_QUERY",
            status_code=400,
            details={"query": query, **(details or {})}
        )


class StorageError(KnowledgeServiceError):
    """Raised when storage operations fail."""
    
    def __init__(self, operation: str, path: str = None, message: str = None):
        super().__init__(
            message=message or f"Storage operation failed: {operation}",
            error_code="STORAGE_ERROR",
            status_code=500,
            details={"operation": operation, "path": path}
        )