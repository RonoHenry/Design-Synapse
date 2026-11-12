"""Service interface definitions."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from fastapi import UploadFile
from sqlalchemy.orm import Session

from ..models.resource import Resource


class IPDFProcessingService(ABC):
    """Interface for PDF processing service."""

    @abstractmethod
    async def process_pdf(
        self, file: UploadFile, resource: Resource, db: Session
    ) -> Tuple[str, int]:
        """Process and store a PDF file."""
        pass

    @abstractmethod
    def extract_metadata(self, file_path: str) -> Dict:
        """Extract metadata from a PDF file."""
        pass

    @abstractmethod
    def get_pdf_path(self, resource: Resource) -> Optional[Path]:
        """Get the path to a stored PDF file."""
        pass


class ILLMService(ABC):
    """Interface for LLM service."""

    @abstractmethod
    async def generate_insights(
        self, text: str, resource: Resource, db: Session
    ) -> Tuple[str, List[str], List[str]]:
        """Generate summary, key takeaways, and keywords for a resource."""
        pass

    @abstractmethod
    async def extract_topics(self, content: str) -> List[str]:
        """Extract relevant topics from the content."""
        pass

    @abstractmethod
    async def extract_keywords(self, content: str) -> List[str]:
        """Extract important keywords from the content."""
        pass

    @abstractmethod
    def compare_similarity(self, text1: str, text2: str) -> float:
        """Compare the semantic similarity between two texts."""
        pass


class IVectorSearchService(ABC):
    """Interface for vector search service."""

    @abstractmethod
    async def index_resource(
        self,
        resource_id: int,
        title: str,
        description: str,
        content: str,
        metadata: Dict,
    ) -> None:
        """Index a resource in the vector database."""
        pass

    @abstractmethod
    async def search_resources(
        self, query: str, filter_metadata: Optional[Dict] = None, top_k: int = 10
    ) -> List[Dict]:
        """Search for resources using semantic similarity."""
        pass

    @abstractmethod
    async def delete_resource(self, resource_id: int) -> None:
        """Delete a resource from the vector index."""
        pass

    @abstractmethod
    async def update_resource(
        self,
        resource_id: int,
        title: str,
        description: str,
        content: str,
        metadata: Dict,
    ) -> None:
        """Update a resource in the vector index."""
        pass


class IContentExtractionService(ABC):
    """Interface for content extraction service."""

    @abstractmethod
    async def process_file(
        self, file: UploadFile, resource: Resource, db: Session
    ) -> Tuple[str, int]:
        """Process and store a file with content extraction."""
        pass

    @abstractmethod
    def get_supported_file_types(self) -> List[str]:
        """Get list of supported file extensions."""
        pass

    @abstractmethod
    def is_supported_file_type(self, filename: str) -> bool:
        """Check if file type is supported."""
        pass

    @abstractmethod
    async def extract_content_preview(
        self, file: UploadFile, max_length: int = 1000
    ) -> Dict:
        """Extract a preview of file content without storing the file."""
        pass
