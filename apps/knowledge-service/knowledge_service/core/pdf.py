"""Dependencies for PDF processing service."""

from functools import lru_cache
from pathlib import Path
from src.services.pdf_processing import PDFProcessingService

@lru_cache()
def get_pdf_service() -> PDFProcessingService:
    """Get or create PDF processing service instance."""
    storage_path = Path(__file__).parent.parent.parent / "storage" / "pdfs"
    return PDFProcessingService(str(storage_path))