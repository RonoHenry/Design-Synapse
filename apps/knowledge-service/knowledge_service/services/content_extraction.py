"""Service for extracting content from various file types."""

import logging
import os
import tempfile
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

from fastapi import HTTPException, UploadFile
from sqlalchemy.orm import Session

from ..core.config import settings
from ..core.vector_search import get_vector_search_service
from ..exceptions import (ContentProcessingError, FileFormatError,
                          FileSizeError, FileValidationError,
                          TextExtractionError)
from ..interfaces.services import IContentExtractionService
from ..models import Resource

logger = logging.getLogger(__name__)


class BaseContentExtractor(ABC):
    """Base class for content extractors."""

    def __init__(self, config=None):
        self.config = config or settings
        self.storage_path = Path(self.config.file_processing.storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)

    @abstractmethod
    def extract_text(self, file_path: Path) -> str:
        """Extract text content from file."""
        pass

    @abstractmethod
    def extract_metadata(self, file_path: Path) -> Dict:
        """Extract metadata from file."""
        pass

    @abstractmethod
    def get_supported_extensions(self) -> List[str]:
        """Get list of supported file extensions."""
        pass

    def validate_file_size(self, content: bytes) -> None:
        """Validate file size."""
        max_size = self.config.file_processing.max_file_size_mb * 1024 * 1024
        if len(content) > max_size:
            raise FileSizeError(
                f"File too large. Maximum size is {self.config.file_processing.max_file_size_mb}MB"
            )

    def process_content_for_indexing(self, text: str) -> str:
        """Process extracted text for better vector indexing."""
        if not text or not text.strip():
            return text

        # Clean up common extraction artifacts
        processed_text = text

        # Remove excessive whitespace and normalize line breaks
        import re

        processed_text = re.sub(
            r"\n\s*\n\s*\n+", "\n\n", processed_text
        )  # Multiple empty lines
        processed_text = re.sub(r"[ \t]+", " ", processed_text)  # Multiple spaces/tabs
        processed_text = processed_text.strip()

        # Ensure content doesn't exceed maximum length for embedding
        max_length = self.config.max_content_length
        if len(processed_text) > max_length:
            # Truncate at word boundary
            truncated = processed_text[:max_length]
            last_space = truncated.rfind(" ")
            if (
                last_space > max_length * 0.9
            ):  # Only truncate at word boundary if it's not too far back
                processed_text = truncated[:last_space]
            else:
                processed_text = truncated

            logger.info(
                f"Truncated content from {len(text)} to {len(processed_text)} characters"
            )

        return processed_text

    def chunk_content(
        self, text: str, chunk_size: int = None, overlap: int = None
    ) -> List[str]:
        """Split content into chunks for better indexing."""
        if not text or not text.strip():
            return []

        chunk_size = chunk_size or self.config.file_processing.chunk_size
        overlap = overlap or self.config.file_processing.chunk_overlap

        # Simple sentence-aware chunking
        sentences = text.split(". ")
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
                    overlap_text = (
                        current_chunk[-overlap:]
                        if len(current_chunk) > overlap
                        else current_chunk
                    )
                    current_chunk = overlap_text + sentence + ". "
                else:
                    current_chunk = sentence + ". "

        # Add the last chunk
        if current_chunk:
            chunks.append(current_chunk.strip())

        return chunks


class DocxExtractor(BaseContentExtractor):
    """Content extractor for DOCX files."""

    def extract_text(self, file_path: Path) -> str:
        """Extract text content from DOCX file."""
        try:
            from docx import Document

            doc = Document(file_path)
            text_content = []

            # Extract text from paragraphs
            for paragraph in doc.paragraphs:
                if paragraph.text.strip():
                    text_content.append(paragraph.text)

            # Extract text from tables
            for table in doc.tables:
                for row in table.rows:
                    row_text = []
                    for cell in row.cells:
                        if cell.text.strip():
                            row_text.append(cell.text.strip())
                    if row_text:
                        text_content.append(" | ".join(row_text))

            extracted_text = "\n".join(text_content)
            if not extracted_text.strip():
                raise TextExtractionError("No text content found in DOCX file")

            return extracted_text

        except ImportError:
            raise ContentProcessingError(
                "python-docx library not installed. Install with: pip install python-docx"
            )
        except Exception as e:
            raise TextExtractionError(f"Failed to extract text from DOCX: {str(e)}")

    def extract_metadata(self, file_path: Path) -> Dict:
        """Extract metadata from DOCX file."""
        try:
            from docx import Document

            doc = Document(file_path)
            core_props = doc.core_properties

            return {
                "title": core_props.title or "",
                "author": core_props.author or "",
                "subject": core_props.subject or "",
                "keywords": core_props.keywords or "",
                "category": core_props.category or "",
                "comments": core_props.comments or "",
                "created": str(core_props.created) if core_props.created else "",
                "modified": str(core_props.modified) if core_props.modified else "",
                "last_modified_by": core_props.last_modified_by or "",
                "revision": core_props.revision or 0,
                "paragraph_count": len(doc.paragraphs),
                "table_count": len(doc.tables),
            }

        except ImportError:
            return {"error": "python-docx library not installed"}
        except Exception as e:
            logger.warning(f"Failed to extract DOCX metadata: {e}")
            return {"error": str(e)}

    def get_supported_extensions(self) -> List[str]:
        """Get supported file extensions."""
        return [".docx", ".doc"]


class TextExtractor(BaseContentExtractor):
    """Content extractor for plain text files."""

    def extract_text(self, file_path: Path) -> str:
        """Extract text content from text file."""
        try:
            # Try different encodings
            encodings = ["utf-8", "utf-16", "latin-1", "cp1252"]

            for encoding in encodings:
                try:
                    with open(file_path, "r", encoding=encoding) as f:
                        content = f.read()

                    if not content.strip():
                        raise TextExtractionError("No text content found in file")

                    return content

                except UnicodeDecodeError:
                    continue

            raise TextExtractionError(
                "Could not decode text file with any supported encoding"
            )

        except Exception as e:
            if isinstance(e, TextExtractionError):
                raise
            raise TextExtractionError(f"Failed to extract text from file: {str(e)}")

    def extract_metadata(self, file_path: Path) -> Dict:
        """Extract metadata from text file."""
        try:
            stat = file_path.stat()

            # Try to detect if it's markdown
            is_markdown = file_path.suffix.lower() in [".md", ".markdown"]

            metadata = {
                "file_size": stat.st_size,
                "created": str(stat.st_ctime),
                "modified": str(stat.st_mtime),
                "is_markdown": is_markdown,
                "encoding": "utf-8",  # Default assumption
            }

            # For markdown files, try to extract title from first heading
            if is_markdown:
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        first_lines = f.read(1000)  # Read first 1000 chars

                    import re

                    # Look for markdown title (# Title)
                    title_match = re.search(r"^#\s+(.+)$", first_lines, re.MULTILINE)
                    if title_match:
                        metadata["title"] = title_match.group(1).strip()

                except Exception:
                    pass  # Ignore errors in title extraction

            return metadata

        except Exception as e:
            logger.warning(f"Failed to extract text file metadata: {e}")
            return {"error": str(e)}

    def get_supported_extensions(self) -> List[str]:
        """Get supported file extensions."""
        return [".txt", ".md", ".markdown"]


class HtmlExtractor(BaseContentExtractor):
    """Content extractor for HTML files."""

    def extract_text(self, file_path: Path) -> str:
        """Extract text content from HTML file."""
        try:
            from bs4 import BeautifulSoup

            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            soup = BeautifulSoup(content, "html.parser")

            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()

            # Extract text
            text = soup.get_text()

            # Clean up whitespace
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = " ".join(chunk for chunk in chunks if chunk)

            if not text.strip():
                raise TextExtractionError("No text content found in HTML file")

            return text

        except ImportError:
            raise ContentProcessingError(
                "beautifulsoup4 library not installed. Install with: pip install beautifulsoup4"
            )
        except Exception as e:
            raise TextExtractionError(f"Failed to extract text from HTML: {str(e)}")

    def extract_metadata(self, file_path: Path) -> Dict:
        """Extract metadata from HTML file."""
        try:
            from bs4 import BeautifulSoup

            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            soup = BeautifulSoup(content, "html.parser")

            metadata = {}

            # Extract title
            title_tag = soup.find("title")
            if title_tag:
                metadata["title"] = title_tag.get_text().strip()

            # Extract meta tags
            meta_tags = soup.find_all("meta")
            for meta in meta_tags:
                name = meta.get("name") or meta.get("property")
                content_attr = meta.get("content")

                if name and content_attr:
                    metadata[f"meta_{name}"] = content_attr

            # Extract headings
            headings = []
            for i in range(1, 7):  # h1 to h6
                for heading in soup.find_all(f"h{i}"):
                    headings.append({"level": i, "text": heading.get_text().strip()})

            if headings:
                metadata["headings"] = headings[:10]  # Limit to first 10 headings

            return metadata

        except ImportError:
            return {"error": "beautifulsoup4 library not installed"}
        except Exception as e:
            logger.warning(f"Failed to extract HTML metadata: {e}")
            return {"error": str(e)}

    def get_supported_extensions(self) -> List[str]:
        """Get supported file extensions."""
        return [".html", ".htm"]


class ContentExtractionService(IContentExtractionService):
    """Main service for content extraction from various file types."""

    def __init__(self, config=None):
        self.config = config or settings
        self.extractors = {
            ".docx": DocxExtractor(config),
            ".doc": DocxExtractor(
                config
            ),  # Note: .doc files need different handling in production
            ".txt": TextExtractor(config),
            ".md": TextExtractor(config),
            ".markdown": TextExtractor(config),
            ".html": HtmlExtractor(config),
            ".htm": HtmlExtractor(config),
        }
        logger.info(
            f"Content extraction service initialized with {len(self.extractors)} extractors"
        )

    async def process_file(
        self, file: UploadFile, resource: Resource, db: Session
    ) -> Tuple[str, int]:
        """Process and store a file with content extraction.

        Args:
            file: The uploaded file
            resource: The associated resource model
            db: Database session

        Returns:
            Tuple of (storage path, file size)

        Raises:
            HTTPException: If file processing fails
        """
        try:
            # Validate file extension
            file_extension = self._get_file_extension(file.filename)
            if file_extension not in self.extractors:
                raise FileFormatError(f"Unsupported file type: {file_extension}")

            # Read file content for validation
            content = await file.read()

            # Validate file size
            extractor = self.extractors[file_extension]
            extractor.validate_file_size(content)

        except (FileValidationError, FileSizeError, FileFormatError) as e:
            logger.error(f"File validation failed: {e}")
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            logger.error(f"Unexpected error during file validation: {e}")
            raise HTTPException(status_code=500, detail="File validation failed")

        filepath = None
        try:
            # Generate unique filename
            import uuid

            filename = f"{uuid.uuid4()}{file_extension}"
            filepath = Path(self.config.file_processing.storage_path) / filename

            # Ensure storage directory exists
            filepath.parent.mkdir(parents=True, exist_ok=True)

            # Save file (content already read for validation)
            with open(filepath, "wb") as f:
                f.write(content)

            # Extract text and process with vector search
            try:
                extractor = self.extractors[file_extension]
                text = extractor.extract_text(filepath)
                logger.info(
                    f"Extracted {len(text)} characters from {file_extension} file"
                )

                # Enhanced content processing for better indexing
                processed_content = extractor.process_content_for_indexing(text)

                # Use chunked indexing for better granularity if content is large
                use_chunking = (
                    len(processed_content) > 5000
                )  # Use chunking for large documents

                vector_service = get_vector_search_service()
                metadata = {
                    "content_type": resource.content_type,
                    "source_platform": resource.source_platform,
                    "author": resource.author,
                    "topics": [topic.name for topic in resource.topics],
                    "file_extension": file_extension,
                    "processing_timestamp": str(resource.created_at),
                }

                # Add file-specific metadata
                try:
                    file_metadata = extractor.extract_metadata(filepath)
                    metadata.update(file_metadata)
                except Exception as e:
                    logger.warning(f"Failed to extract metadata: {e}")

                if use_chunking:
                    # Split content into chunks for better indexing
                    chunks = extractor.chunk_content(processed_content)
                    await vector_service.index_resource_chunks(
                        resource.id,
                        resource.title,
                        resource.description,
                        chunks,
                        metadata,
                    )
                    logger.info(
                        f"Indexed {len(chunks)} chunks for resource {resource.id}"
                    )
                else:
                    # Use standard indexing for smaller documents
                    await vector_service.update_resource(
                        resource.id,
                        resource.title,
                        resource.description,
                        processed_content,
                        metadata,
                    )
                    logger.info(f"Indexed resource {resource.id} as single document")

                # Update resource with storage info
                resource.storage_path = str(filepath)
                resource.file_size = len(content)
                db.commit()

                logger.info(
                    f"Successfully processed {file_extension} file for resource {resource.id}"
                )
                return str(filepath), len(content)

            except TextExtractionError as e:
                logger.error(f"Text extraction failed: {e}")
                raise HTTPException(status_code=422, detail=str(e))
            except ContentProcessingError as e:
                logger.error(f"Content processing failed: {e}")
                raise HTTPException(status_code=422, detail=str(e))
            except Exception as e:
                logger.error(f"Vector indexing failed: {e}")
                raise HTTPException(
                    status_code=500, detail="Failed to index file content"
                )

        except Exception as e:
            # Clean up file if it was created
            if filepath and filepath.exists():
                filepath.unlink()
                logger.info(f"Cleaned up file after error: {filepath}")

            # Re-raise HTTPExceptions as-is
            if isinstance(e, HTTPException):
                raise e

            logger.error(f"Unexpected error processing file: {e}")
            raise HTTPException(
                status_code=500, detail=f"Failed to process file: {str(e)}"
            )

    def get_supported_file_types(self) -> List[str]:
        """Get list of supported file extensions."""
        return list(self.extractors.keys())

    def is_supported_file_type(self, filename: str) -> bool:
        """Check if file type is supported."""
        file_extension = self._get_file_extension(filename)
        return file_extension in self.extractors

    def _get_file_extension(self, filename: str) -> str:
        """Get file extension from filename."""
        if not filename:
            raise FileValidationError("Filename is required")

        return os.path.splitext(filename)[1].lower()

    async def extract_content_preview(
        self, file: UploadFile, max_length: int = 1000
    ) -> Dict:
        """Extract a preview of file content without storing the file.

        Args:
            file: The uploaded file
            max_length: Maximum length of preview text

        Returns:
            Dictionary with preview information
        """
        try:
            # Validate file type
            file_extension = self._get_file_extension(file.filename)
            if file_extension not in self.extractors:
                raise FileFormatError(f"Unsupported file type: {file_extension}")

            # Read file content
            content = await file.read()

            # Create temporary file for processing
            with tempfile.NamedTemporaryFile(
                suffix=file_extension, delete=False
            ) as temp_file:
                temp_file.write(content)
                temp_file.flush()
                temp_path = Path(temp_file.name)

            try:
                extractor = self.extractors[file_extension]

                # Extract text
                text = extractor.extract_text(temp_path)
                preview_text = text[:max_length] if len(text) > max_length else text

                # Extract metadata
                metadata = extractor.extract_metadata(temp_path)

                return {
                    "filename": file.filename,
                    "file_extension": file_extension,
                    "file_size": len(content),
                    "text_length": len(text),
                    "preview_text": preview_text,
                    "metadata": metadata,
                    "is_truncated": len(text) > max_length,
                }

            finally:
                # Clean up temporary file
                if temp_path.exists():
                    temp_path.unlink()

        except Exception as e:
            logger.error(f"Failed to extract content preview: {e}")
            raise HTTPException(
                status_code=500, detail=f"Failed to extract content preview: {str(e)}"
            )


# Global service instance
def get_content_extraction_service() -> ContentExtractionService:
    """Get the content extraction service instance."""
    return ContentExtractionService()
