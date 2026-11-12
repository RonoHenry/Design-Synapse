"""Integration tests for PDF processing service."""

import os
import pytest
from fastapi import UploadFile
from knowledge_service.services.pdf_processing import PDFProcessingService


@pytest.fixture
def sample_pdf_path(tmpdir):
    """Create a sample PDF file for testing."""
    pdf_path = os.path.join(tmpdir, "test.pdf")
    # TODO: Create a simple PDF file using a PDF generation library
    # For now, this would need a real PDF file for testing
    return pdf_path


@pytest.fixture
def pdf_processor(tmpdir):
    """Create a PDFProcessingService instance for testing."""
    return PDFProcessingService(str(tmpdir))


def test_extract_text_from_pdf(sample_pdf_path):
    """Test PDF text extraction."""
    text = extract_text_from_pdf(sample_pdf_path)
    assert isinstance(text, str)
    assert len(text) > 0  # Assuming the sample PDF has content


def test_process_pdf_upload(pdf_processor, sample_pdf_path):
    """Test processing an uploaded PDF file."""
    with open(sample_pdf_path, 'rb') as f:
        file = UploadFile(filename="test.pdf", file=f)
        result = pdf_processor.process_upload(file)
        assert result["storage_path"]
        assert result["file_size"] > 0
        assert result["text_content"]
        assert result["num_pages"] > 0


def test_process_invalid_pdf(pdf_processor, tmpdir):
    """Test processing an invalid PDF file."""
    invalid_path = os.path.join(tmpdir, "invalid.pdf")
    with open(invalid_path, 'w') as f:
        f.write("Not a PDF file")
    
    with open(invalid_path, 'rb') as f:
        file = UploadFile(filename="invalid.pdf", file=f)
        with pytest.raises(Exception):  # Should specify exact exception
            pdf_processor.process_upload(file)


def test_extract_metadata(pdf_processor, sample_pdf_path):
    """Test extracting metadata from PDF."""
    metadata = pdf_processor.extract_metadata(sample_pdf_path)
    assert isinstance(metadata, dict)
    # Check for common metadata fields
    expected_fields = ["title", "author", "creation_date"]
    assert any(field in metadata for field in expected_fields)


def test_generate_thumbnails(pdf_processor, sample_pdf_path):
    """Test thumbnail generation for PDF pages."""
    thumbnails = pdf_processor.generate_thumbnails(sample_pdf_path)
    assert isinstance(thumbnails, list)
    assert len(thumbnails) > 0
    # Verify thumbnail properties (size, format, etc.)


def test_extract_text_with_layout(pdf_processor, sample_pdf_path):
    """Test extracting text while preserving layout information."""
    layout_text = pdf_processor.extract_text_with_layout(sample_pdf_path)
    assert isinstance(layout_text, dict)
    assert "pages" in layout_text
    assert len(layout_text["pages"]) > 0


def test_cleanup_temporary_files(pdf_processor, sample_pdf_path):
    """Test cleanup of temporary files after processing."""
    with open(sample_pdf_path, 'rb') as f:
        file = UploadFile(filename="test.pdf", file=f)
        result = pdf_processor.process_upload(file)
        temp_path = result.get("temp_path")
        assert not os.path.exists(temp_path)  # Should be cleaned up


def test_concurrent_processing(pdf_processor, sample_pdf_path):
    """Test processing multiple PDFs concurrently."""
    import concurrent.futures
    
    def process_file():
        with open(sample_pdf_path, 'rb') as f:
            file = UploadFile(filename="test.pdf", file=f)
            return pdf_processor.process_upload(file)
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        futures = [executor.submit(process_file) for _ in range(3)]
        results = [f.result() for f in futures]
        
        assert len(results) == 3
        assert all(r["storage_path"] for r in results)


def test_large_pdf_handling(pdf_processor, tmpdir):
    """Test handling of large PDF files."""
    # Create or use a large PDF file (>10MB)
    large_pdf_path = os.path.join(tmpdir, "large.pdf")
    # TODO: Generate large PDF file
    
    with open(large_pdf_path, 'rb') as f:
        file = UploadFile(filename="large.pdf", file=f)
        result = pdf_processor.process_upload(file)
        assert result["file_size"] > 10 * 1024 * 1024  # >10MB


def test_pdf_text_extraction_accuracy(pdf_processor, sample_pdf_path):
    """Test accuracy of text extraction."""
    # This would require a PDF with known content
    extracted_text = pdf_processor.extract_text(sample_pdf_path)
    # Compare with expected text content
    # assert expected_text in extracted_text


def test_error_handling_corrupt_pdf(pdf_processor, tmpdir):
    """Test handling of corrupt PDF files."""
    corrupt_path = os.path.join(tmpdir, "corrupt.pdf")
    with open(corrupt_path, 'wb') as f:
        f.write(b'%PDF-1.7\nCorrupt content')
    
    with open(corrupt_path, 'rb') as f:
        file = UploadFile(filename="corrupt.pdf", file=f)
        with pytest.raises(Exception):  # Should specify exact exception
            pdf_processor.process_upload(file)