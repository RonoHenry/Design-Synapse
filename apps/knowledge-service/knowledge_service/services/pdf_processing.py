"""Service for processing and storing PDF resources."""

import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import uuid
import fitz  # PyMuPDF
from fastapi import HTTPException, UploadFile
from sqlalchemy.orm import Session

from ..models import Resource
from ..core.vector_search import get_vector_search_service


class PDFProcessingService:
    """Service for handling PDF document processing."""

    def __init__(self, storage_path: str):
        """Initialize the service.
        
        Args:
            storage_path: Base path for storing PDF files
        """
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
    
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
            HTTPException: If file processing fails
        """
        if not file.filename.lower().endswith('.pdf'):
            raise HTTPException(
                status_code=400,
                detail="File must be a PDF"
            )
        
        try:
            # Generate unique filename
            filename = f"{uuid.uuid4()}.pdf"
            filepath = self.storage_path / filename
            
            # Save file
            content = await file.read()
            with open(filepath, "wb") as f:
                f.write(content)
            
            # Extract text and process with vector search
            text = self._extract_text(filepath)
            await get_vector_search_service().update_resource(
                resource.id,
                resource.title,
                resource.description,
                text,
                {
                    "content_type": resource.content_type,
                    "source_platform": resource.source_platform,
                    "author": resource.author,
                    "topics": [topic.name for topic in resource.topics]
                }
            )
            
            # Update resource with storage info
            resource.storage_path = str(filepath)
            resource.file_size = len(content)
            db.commit()
            
            return str(filepath), len(content)
        
        except Exception as e:
            if filepath.exists():
                filepath.unlink()
            raise HTTPException(
                status_code=500,
                detail=f"Failed to process PDF: {str(e)}"
            )
    
    def _extract_text(self, filepath: Path) -> str:
        """Extract text content from a PDF file.
        
        Args:
            filepath: Path to the PDF file
        
        Returns:
            Extracted text content
        """
        text = []
        with fitz.open(filepath) as doc:
            for page in doc:
                text.append(page.get_text())
        return "\n".join(text)
    
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