"""Custom exceptions for knowledge service."""

from typing import Optional


class KnowledgeServiceError(Exception):
    """Base exception for knowledge service errors."""

    def __init__(self, message: str, error_code: Optional[str] = None):
        self.message = message
        self.error_code = error_code
        super().__init__(self.message)


class PDFProcessingError(KnowledgeServiceError):
    """Exception raised during PDF processing."""

    pass


class FileValidationError(PDFProcessingError):
    """Exception raised when file validation fails."""

    pass


class FileSizeError(FileValidationError):
    """Exception raised when file size exceeds limits."""

    pass


class FileFormatError(FileValidationError):
    """Exception raised when file format is invalid."""

    pass


class TextExtractionError(PDFProcessingError):
    """Exception raised during text extraction."""

    pass


class ContentProcessingError(KnowledgeServiceError):
    """Exception raised during content processing operations."""

    pass


class LLMServiceError(KnowledgeServiceError):
    """Exception raised during LLM operations."""

    pass


class EmbeddingGenerationError(LLMServiceError):
    """Exception raised during embedding generation."""

    pass


class VectorSearchError(KnowledgeServiceError):
    """Exception raised during vector search operations."""

    pass


class IndexingError(VectorSearchError):
    """Exception raised during resource indexing."""

    pass


class SearchQueryError(VectorSearchError):
    """Exception raised during search queries."""

    pass


class MetadataValidationError(KnowledgeServiceError):
    """Exception raised when metadata validation fails."""

    pass


class BatchProcessingError(KnowledgeServiceError):
    """Exception raised during batch processing operations."""

    pass
