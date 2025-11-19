"""Service for processing and storing PDF resources."""

import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import uuid
import fitz  # PyMuPDF
from fastapi import HTTPException, UploadFile
from sqlalchemy.orm import Session
import logging

from ..models import Resource
from ..core.vector_search import get_vector_search_service
from ..interfaces.services import IPDFProcessingService
from ..exceptions import (
    FileValidationError, FileSizeError, FileFormatError,
    TextExtractionError, PDFProcessingError
)
from ..config import get_config
from ..core.error_handling import handle_service_errors, error_context, ErrorRecovery
from ..core.logging import log_service_operation

logger = logging.getLogger(__name__)


class PDFProcessingService(IPDFProcessingService):
    """Service for handling PDF document processing."""

    def __init__(self, storage_path: Optional[str] = None):
        """Initialize the service.
        
        Args:
            storage_path: Base path for storing PDF files (optional, uses config if not provided)
        """
        self.config = get_config()
        self.storage_path = Path(storage_path or self.config.storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"PDF processing service initialized with storage path: {self.storage_path}")
    
    @handle_service_errors("pdf_processing", "process_pdf")
    async def process_pdf(
        self,
        file: UploadFile,
        resource: Resource,
        db: Session
    ) -> Tuple[str, int]:
        """Process and store a PDF file.
        
        Args:
            file: The uploaded PDF file
            resource: The associated resource model
            db: Database session
        
        Returns:
            Tuple of (storage path, file size)
        
        Raises:
            PDFProcessingError: If file processing fails
        """
        with error_context(
            "pdf_validation",
            resource_id=resource.id,
            filename=file.filename
        ):
            # Validate file extension
            self._validate_file_extension(file.filename)
            
            # Read file content for validation
            content = await file.read()
            
            # Validate file size
            self._validate_file_size(content)
            
            # Validate file content
            self._validate_file_content(content)
        
        filepath = None
        try:
            with error_context(
                "pdf_storage",
                resource_id=resource.id,
                file_size=len(content)
            ):
                # Generate unique filename
                filename = f"{uuid.uuid4()}.pdf"
                filepath = self.storage_path / filename
                
                # Save file (content already read for validation)
                with open(filepath, "wb") as f:
                    f.write(content)
            
            # Extract text and process with vector search
            with error_context(
                "text_extraction",
                resource_id=resource.id,
                filepath=str(filepath)
            ):
                text = self._extract_text(filepath)
                logger.info(f"Extracted {len(text)} characters from PDF")
                
                # Enhanced content processing for better indexing
                processed_content = self._process_content_for_indexing(text)
                
                # Use chunked indexing for better granularity if content is large
                use_chunking = len(processed_content) > 5000  # Use chunking for large documents
                
                vector_service = get_vector_search_service()
                metadata = {
                    "content_type": resource.content_type,
                    "source_platform": resource.source_platform,
                    "author": resource.author,
                    "topics": [topic.name for topic in resource.topics],
                    "page_count": self._get_page_count(filepath),
                    "file_extension": ".pdf",
                    "processing_timestamp": str(resource.created_at)
                }
                
                with error_context(
                    "vector_indexing",
                    resource_id=resource.id,
                    use_chunking=use_chunking,
                    content_length=len(processed_content)
                ):
                    if use_chunking:
                        # Split content into chunks for better indexing
                        chunks = self._chunk_content(processed_content)
                        await vector_service.index_resource_chunks(
                            resource.id,
                            resource.title,
                            resource.description,
                            chunks,
                            metadata
                        )
                        logger.info(f"Indexed {len(chunks)} chunks for resource {resource.id}")
                    else:
                        # Use standard indexing for smaller documents
                        await vector_service.update_resource(
                            resource.id,
                            resource.title,
                            resource.description,
                            processed_content,
                            metadata
                        )
                        logger.info(f"Indexed resource {resource.id} as single document")
                
                # Update resource with storage info
                resource.storage_path = str(filepath)
                resource.file_size = len(content)
                db.commit()
                
                logger.info(f"Successfully processed PDF for resource {resource.id}")
                return str(filepath), len(content)
        
        except Exception as e:
            # Clean up file if it was created
            if filepath and filepath.exists():
                filepath.unlink()
                logger.info(f"Cleaned up file after error: {filepath}")
            
            # Re-raise as PDFProcessingError for consistent error handling
            if isinstance(e, (FileValidationError, TextExtractionError)):
                raise
            
            raise PDFProcessingError(f"Failed to process PDF: {str(e)}") from e
    
    def _validate_file_extension(self, filename: str) -> None:
        """Validate file extension."""
        if not filename:
            raise FileValidationError("Filename is required")
        
        if not any(filename.lower().endswith(ext) for ext in self.config.allowed_file_types):
            raise FileFormatError(f"File must be one of: {', '.join(self.config.allowed_file_types)}")
    
    def _validate_file_size(self, content: bytes) -> None:
        """Validate file size."""
        max_size = self.config.max_file_size_mb * 1024 * 1024
        if len(content) > max_size:
            raise FileSizeError(f"File too large. Maximum size is {self.config.max_file_size_mb}MB")
    
    def _validate_file_content(self, content: bytes) -> None:
        """Validate file content."""
        if not content.startswith(b'%PDF-'):
            raise FileFormatError("Invalid PDF file format")
    
    def _extract_text(self, filepath: Path) -> str:
        """Extract text content from a PDF file.
        
        Args:
            filepath: Path to the PDF file
        
        Returns:
            Extracted text content
            
        Raises:
            TextExtractionError: If text extraction fails
        """
        try:
            text = []
            with fitz.open(filepath) as doc:
                for page_num, page in enumerate(doc):
                    try:
                        page_text = page.get_text()
                        if page_text.strip():  # Only add non-empty pages
                            text.append(page_text)
                    except Exception as e:
                        logger.warning(f"Failed to extract text from page {page_num}: {e}")
                        continue
            
            extracted_text = "\n".join(text)
            if not extracted_text.strip():
                raise TextExtractionError("No text content found in PDF")
            
            return extracted_text
            
        except Exception as e:
            if isinstance(e, TextExtractionError):
                raise
            raise TextExtractionError(f"Failed to extract text from PDF: {str(e)}")
    
    def get_pdf_path(self, resource: Resource) -> Optional[Path]:
        """Get the path to a stored PDF file.
        
        Args:
            resource: The resource model
        
        Returns:
            Path to the PDF file if it exists
        """
        if not resource.storage_path:
            return None
        
        path = Path(resource.storage_path)
        return path if path.exists() else None
    
    def extract_metadata(self, file_path: str) -> Dict:
        """Extract metadata from a PDF file."""
        with fitz.open(file_path) as pdf:
            metadata = pdf.metadata
            return {
                "title": metadata.get("title", ""),
                "author": metadata.get("author", ""),
                "subject": metadata.get("subject", ""),
                "keywords": metadata.get("keywords", ""),
                "creator": metadata.get("creator", ""),
                "producer": metadata.get("producer", ""),
                "creation_date": metadata.get("creationDate", ""),
                "modification_date": metadata.get("modDate", ""),
                "page_count": len(pdf)
            }
    
    def extract_text_with_layout(self, file_path: str) -> Dict:
        """Extract text while preserving layout information."""
        pages = []
        with fitz.open(file_path) as pdf:
            for page_num, page in enumerate(pdf):
                blocks = page.get_text("dict")["blocks"]
                page_content = {
                    "page_number": page_num + 1,
                    "width": page.rect.width,
                    "height": page.rect.height,
                    "blocks": []
                }
                
                for block in blocks:
                    if block.get("type") == 0:  # Text block
                        page_content["blocks"].append({
                            "type": "text",
                            "content": "".join([line["text"] for line in block.get("lines", [])]),
                            "bbox": block.get("bbox", []),
                            "lines": len(block.get("lines", [])),
                        })
                    elif block.get("type") == 1:  # Image block
                        page_content["blocks"].append({
                            "type": "image",
                            "bbox": block.get("bbox", []),
                        })
                
                pages.append(page_content)
        
        return {"pages": pages}
    
    async def generate_thumbnails(self, file_path: str, size: tuple = (200, 200)) -> List[bytes]:
        """Generate thumbnails for all pages in a PDF."""
        import io
        from PIL import Image
        
        thumbnails = []
        with fitz.open(file_path) as pdf:
            for page in pdf:
                pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
                img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                img.thumbnail(size)
                
                img_byte_arr = io.BytesIO()
                img.save(img_byte_arr, format='PNG')
                thumbnails.append(img_byte_arr.getvalue())
        
        return thumbnails
    
    def _process_content_for_indexing(self, text: str) -> str:
        """Process extracted text for better vector indexing.
        
        Args:
            text: Raw extracted text
            
        Returns:
            Processed text optimized for indexing
        """
        if not text or not text.strip():
            return text
        
        # Clean up common PDF extraction artifacts
        processed_text = text
        
        # Remove excessive whitespace and normalize line breaks
        import re
        processed_text = re.sub(r'\n\s*\n\s*\n+', '\n\n', processed_text)  # Multiple empty lines
        processed_text = re.sub(r'[ \t]+', ' ', processed_text)  # Multiple spaces/tabs
        processed_text = processed_text.strip()
        
        # Remove common PDF artifacts
        processed_text = re.sub(r'^\s*\d+\s*$', '', processed_text, flags=re.MULTILINE)  # Page numbers on their own lines
        processed_text = re.sub(r'\f', '\n', processed_text)  # Form feed characters
        
        # Ensure content doesn't exceed maximum length for embedding
        max_length = self.config.max_content_length if hasattr(self.config, 'max_content_length') else 50000
        if len(processed_text) > max_length:
            # Truncate at word boundary
            truncated = processed_text[:max_length]
            last_space = truncated.rfind(' ')
            if last_space > max_length * 0.9:  # Only truncate at word boundary if it's not too far back
                processed_text = truncated[:last_space]
            else:
                processed_text = truncated
            
            logger.info(f"Truncated content from {len(text)} to {len(processed_text)} characters")
        
        return processed_text
    
    def _get_page_count(self, filepath: Path) -> int:
        """Get the number of pages in a PDF file.
        
        Args:
            filepath: Path to the PDF file
            
        Returns:
            Number of pages
        """
        try:
            with fitz.open(filepath) as doc:
                return len(doc)
        except Exception as e:
            logger.warning(f"Failed to get page count for {filepath}: {e}")
            return 0
    
    def _chunk_content(self, text: str, chunk_size: int = None, overlap: int = None) -> List[str]:
        """Split content into chunks for better indexing.
        
        Args:
            text: Text to chunk
            chunk_size: Size of each chunk (defaults to config value)
            overlap: Overlap between chunks (defaults to config value)
            
        Returns:
            List of text chunks
        """
        if not text or not text.strip():
            return []
        
        chunk_size = chunk_size or getattr(self.config, 'chunk_size', 1000)
        overlap = overlap or getattr(self.config, 'chunk_overlap', 200)
        
        # Simple sentence-aware chunking
        sentences = text.split('. ')
        chunks = []
        current_chunk = ""
        
        for sentence in sentences:
            # Add sentence to current chunk
            test_chunk = current_chunk + sentence + ". "
            
            if len(test_chunk) <= chunk_size:
                current_chunk = test_chunk
            else:
                # Current chunk is full, start a new one
                if current_chunk:
                    chunks.append(current_chunk.strip())
                
                # Start new chunk with overlap from previous chunk
                if overlap > 0 and current_chunk:
                    # Take last part of current chunk as overlap
                    overlap_text = current_chunk[-overlap:] if len(current_chunk) > overlap else current_chunk
                    current_chunk = overlap_text + sentence + ". "
                else:
                    current_chunk = sentence + ". "
        
        # Add the last chunk
        if current_chunk:
            chunks.append(current_chunk.strip())
        
        return chunks