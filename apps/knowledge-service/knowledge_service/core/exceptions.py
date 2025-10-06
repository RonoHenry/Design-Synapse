"""Knowledge Service specific exceptions and error handling.

This module extends the shared error handling with knowledge service specific errors.
"""

import sys
from pathlib import Path
from typing import Any, Dict, Optional

# Add packages to path for shared error handling
packages_path = Path(__file__).parent.parent.parent.parent.parent / "packages"
sys.path.insert(0, str(packages_path))

from common.errors import (
    APIError,
    AuthenticationError,
    AuthorizationError,
    DatabaseError,
    NotFoundError,
    ValidationError,
    ConflictError,
    LLMServiceError,
    VectorSearchError,
    ExternalServiceError,
)
from common.errors.responses import ErrorType


class PDFProcessingError(APIError):
    """Error during PDF processing operations."""
    
    def __init__(
        self,
        message: str = "PDF processing error",
        details: Optional[Dict[str, Any]] = None,
    ):
        """Initialize a PDF processing error.
        
        Args:
            message: Description of the error
            details: Additional error details
        """
        super().__init__(
            message=message,
            error_code=ErrorType.PDF_PROCESSING_ERROR,
            status_code=500,
            details=details,
        )


class ResourceNotFoundError(NotFoundError):
    """Resource not found in knowledge service."""
    
    def __init__(self, resource_id: str):
        """Initialize a resource not found error.
        
        Args:
            resource_id: ID of the resource that was not found
        """
        super().__init__("Resource", resource_id)


class CitationNotFoundError(NotFoundError):
    """Citation not found in knowledge service."""
    
    def __init__(self, citation_id: str):
        """Initialize a citation not found error.
        
        Args:
            citation_id: ID of the citation that was not found
        """
        super().__init__("Citation", citation_id)


class BookmarkNotFoundError(NotFoundError):
    """Bookmark not found in knowledge service."""
    
    def __init__(self, bookmark_id: str):
        """Initialize a bookmark not found error.
        
        Args:
            bookmark_id: ID of the bookmark that was not found
        """
        super().__init__("Bookmark", bookmark_id)


class InvalidResourceTypeError(ValidationError):
    """Invalid resource type provided."""
    
    def __init__(self, resource_type: str, valid_types: list):
        """Initialize an invalid resource type error.
        
        Args:
            resource_type: The invalid resource type provided
            valid_types: List of valid resource types
        """
        super().__init__(
            message=f"Invalid resource type: {resource_type}",
            details={
                "provided_type": resource_type,
                "valid_types": valid_types,
            },
        )


class ResourceURLValidationError(ValidationError):
    """Resource URL validation error."""
    
    def __init__(self, url: str, reason: str):
        """Initialize a resource URL validation error.
        
        Args:
            url: The invalid URL
            reason: Reason why the URL is invalid
        """
        super().__init__(
            message=f"Invalid resource URL: {reason}",
            details={"url": url, "reason": reason},
        )


class VectorIndexError(VectorSearchError):
    """Error during vector indexing operations."""
    
    def __init__(
        self,
        message: str = "Vector indexing error",
        details: Optional[Dict[str, Any]] = None,
    ):
        """Initialize a vector indexing error.
        
        Args:
            message: Description of the error
            details: Additional error details
        """
        super().__init__(message=message, details=details)


class EmbeddingGenerationError(LLMServiceError):
    """Error during embedding generation."""
    
    def __init__(
        self,
        message: str = "Embedding generation error",
        details: Optional[Dict[str, Any]] = None,
    ):
        """Initialize an embedding generation error.
        
        Args:
            message: Description of the error
            details: Additional error details
        """
        super().__init__(message=message, details=details)


class SearchQueryError(ValidationError):
    """Invalid search query provided."""
    
    def __init__(
        self,
        message: str = "Invalid search query",
        details: Optional[Dict[str, Any]] = None,
    ):
        """Initialize a search query error.
        
        Args:
            message: Description of the error
            details: Additional error details
        """
        super().__init__(message=message, details=details)


# Re-export common errors for convenience
__all__ = [
    # Common errors
    "APIError",
    "AuthenticationError",
    "AuthorizationError",
    "DatabaseError",
    "NotFoundError",
    "ValidationError",
    "ConflictError",
    "LLMServiceError",
    "VectorSearchError",
    "ExternalServiceError",
    # Knowledge service specific errors
    "PDFProcessingError",
    "ResourceNotFoundError",
    "CitationNotFoundError",
    "BookmarkNotFoundError",
    "InvalidResourceTypeError",
    "ResourceURLValidationError",
    "VectorIndexError",
    "EmbeddingGenerationError",
    "SearchQueryError",
]
