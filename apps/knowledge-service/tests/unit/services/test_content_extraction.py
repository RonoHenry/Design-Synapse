"""Unit tests for content extraction service."""
import io
from pathlib import Path
from unittest.mock import Mock, mock_open, patch

import pytest
from knowledge_service.services.content_extraction import (
    ContentExtractionError, ContentExtractionService,
    extract_metadata_from_file, extract_text_from_docx, extract_text_from_file,
    extract_text_from_pdf, extract_text_from_txt)


class TestContentExtractionService:
    """Test cases for ContentExtractionService."""

    @pytest.fixture
    def content_extraction_service(self):
        """Content extraction service fixture."""
        return ContentExtractionService()

    @pytest.fixture
    def sample_pdf_content(self):
        """Sample PDF content for testing."""
        return b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n"

    @pytest.fixture
    def sample_text_content(self):
        """Sample text content for testing."""
        return "This is a sample text document with multiple lines.\nIt contains various information for testing."

    def test_init(self):
        """Test service initialization."""
        service = ContentExtractionService()
        assert service.supported_formats == {".pdf", ".docx", ".txt", ".md", ".rtf"}
        assert service.max_file_size == 50 * 1024 * 1024  # 50MB

    def test_is_supported_format_true(self, content_extraction_service):
        """Test supported format detection."""
        assert content_extraction_service.is_supported_format("document.pdf") is True
        assert content_extraction_service.is_supported_format("document.docx") is True
        assert content_extraction_service.is_supported_format("document.txt") is True
        assert content_extraction_service.is_supported_format("document.md") is True

    def test_is_supported_format_false(self, content_extraction_service):
        """Test unsupported format detection."""
        assert content_extraction_service.is_supported_format("document.xlsx") is False
        assert content_extraction_service.is_supported_format("document.jpg") is False
        assert content_extraction_service.is_supported_format("document") is False

    def test_extract_text_from_bytes_pdf(
        self, content_extraction_service, sample_pdf_content
    ):
        """Test text extraction from PDF bytes."""
        with patch(
            "knowledge_service.services.content_extraction.extract_text_from_pdf"
        ) as mock_extract:
            mock_extract.return_value = "Extracted PDF text"

            result = content_extraction_service.extract_text_from_bytes(
                file_content=sample_pdf_content, filename="test.pdf"
            )

            assert result == "Extracted PDF text"
            mock_extract.assert_called_once_with(sample_pdf_content)

    def test_extract_text_from_bytes_txt(
        self, content_extraction_service, sample_text_content
    ):
        """Test text extraction from text bytes."""
        text_bytes = sample_text_content.encode("utf-8")

        result = content_extraction_service.extract_text_from_bytes(
            file_content=text_bytes, filename="test.txt"
        )

        assert result == sample_text_content

    def test_extract_text_from_bytes_unsupported(self, content_extraction_service):
        """Test text extraction from unsupported format."""
        with pytest.raises(ContentExtractionError, match="Unsupported file format"):
            content_extraction_service.extract_text_from_bytes(
                file_content=b"some content", filename="test.xlsx"
            )

    def test_extract_text_from_bytes_too_large(self, content_extraction_service):
        """Test text extraction from file too large."""
        large_content = b"x" * (51 * 1024 * 1024)  # 51MB

        with pytest.raises(ContentExtractionError, match="File too large"):
            content_extraction_service.extract_text_from_bytes(
                file_content=large_content, filename="test.txt"
            )

    def test_extract_text_from_file_success(
        self, content_extraction_service, sample_text_content
    ):
        """Test text extraction from file path."""
        with patch("builtins.open", mock_open(read_data=sample_text_content)):
            with patch("pathlib.Path.stat") as mock_stat:
                mock_stat.return_value.st_size = 1024  # 1KB

                result = content_extraction_service.extract_text_from_file("test.txt")

                assert result == sample_text_content

    def test_extract_text_from_file_not_found(self, content_extraction_service):
        """Test text extraction from non-existent file."""
        with pytest.raises(ContentExtractionError, match="File not found"):
            content_extraction_service.extract_text_from_file("nonexistent.txt")

    def test_extract_metadata_success(self, content_extraction_service):
        """Test metadata extraction."""
        file_content = b"Sample file content"

        with patch(
            "knowledge_service.services.content_extraction.extract_metadata_from_file"
        ) as mock_extract:
            mock_metadata = {
                "file_size": len(file_content),
                "file_type": "txt",
                "encoding": "utf-8",
                "created_date": "2023-01-01",
                "modified_date": "2023-01-02",
            }
            mock_extract.return_value = mock_metadata

            result = content_extraction_service.extract_metadata(
                file_content=file_content, filename="test.txt"
            )

            assert result == mock_metadata
            mock_extract.assert_called_once_with(file_content, "test.txt")

    def test_extract_text_and_metadata_success(
        self, content_extraction_service, sample_text_content
    ):
        """Test combined text and metadata extraction."""
        text_bytes = sample_text_content.encode("utf-8")

        with patch.object(
            content_extraction_service, "extract_text_from_bytes"
        ) as mock_text:
            mock_text.return_value = sample_text_content

            with patch.object(
                content_extraction_service, "extract_metadata"
            ) as mock_metadata:
                mock_metadata.return_value = {"file_size": len(text_bytes)}

                text, metadata = content_extraction_service.extract_text_and_metadata(
                    file_content=text_bytes, filename="test.txt"
                )

                assert text == sample_text_content
                assert metadata == {"file_size": len(text_bytes)}

    def test_batch_extract_text_success(self, content_extraction_service):
        """Test batch text extraction."""
        files = [
            {"content": b"First file content", "filename": "file1.txt"},
            {"content": b"Second file content", "filename": "file2.txt"},
        ]

        with patch.object(
            content_extraction_service, "extract_text_from_bytes"
        ) as mock_extract:
            mock_extract.side_effect = ["First file text", "Second file text"]

            results = content_extraction_service.batch_extract_text(files)

            assert len(results) == 2
            assert results[0]["filename"] == "file1.txt"
            assert results[0]["text"] == "First file text"
            assert results[1]["filename"] == "file2.txt"
            assert results[1]["text"] == "Second file text"

    def test_batch_extract_text_with_errors(self, content_extraction_service):
        """Test batch text extraction with some errors."""
        files = [
            {"content": b"Valid file content", "filename": "file1.txt"},
            {"content": b"Invalid content", "filename": "file2.xlsx"},  # Unsupported
        ]

        with patch.object(
            content_extraction_service, "extract_text_from_bytes"
        ) as mock_extract:
            mock_extract.side_effect = [
                "Valid file text",
                ContentExtractionError("Unsupported format"),
            ]

            results = content_extraction_service.batch_extract_text(files)

            assert len(results) == 2
            assert results[0]["text"] == "Valid file text"
            assert results[0]["error"] is None
            assert results[1]["text"] is None
            assert "Unsupported format" in results[1]["error"]

    def test_validate_file_content_success(self, content_extraction_service):
        """Test successful file content validation."""
        valid_content = b"Valid file content"

        # Should not raise exception
        content_extraction_service._validate_file_content(valid_content, "test.txt")

    def test_validate_file_content_empty(self, content_extraction_service):
        """Test file content validation with empty content."""
        with pytest.raises(ContentExtractionError, match="File content is empty"):
            content_extraction_service._validate_file_content(b"", "test.txt")

    def test_validate_file_content_too_large(self, content_extraction_service):
        """Test file content validation with oversized content."""
        large_content = b"x" * (51 * 1024 * 1024)  # 51MB

        with pytest.raises(ContentExtractionError, match="File too large"):
            content_extraction_service._validate_file_content(large_content, "test.txt")

    def test_clean_extracted_text(self, content_extraction_service):
        """Test text cleaning."""
        dirty_text = "  This is\n\n\ntext with   extra   spaces\t\tand\r\nnewlines  "
        clean_text = content_extraction_service._clean_extracted_text(dirty_text)

        assert clean_text == "This is text with extra spaces and newlines"

    def test_detect_encoding_utf8(self, content_extraction_service):
        """Test UTF-8 encoding detection."""
        utf8_content = "Hello, world! 🌍".encode("utf-8")
        encoding = content_extraction_service._detect_encoding(utf8_content)

        assert encoding.lower() in ["utf-8", "utf8"]

    def test_detect_encoding_latin1(self, content_extraction_service):
        """Test Latin-1 encoding detection."""
        latin1_content = "Café résumé".encode("latin-1")
        encoding = content_extraction_service._detect_encoding(latin1_content)

        assert encoding is not None
        assert isinstance(encoding, str)


class TestStandaloneFunctions:
    """Test cases for standalone extraction functions."""

    def test_extract_text_from_file_pdf(self, sample_pdf_content):
        """Test PDF text extraction via standalone function."""
        with patch(
            "knowledge_service.services.content_extraction.extract_text_from_pdf"
        ) as mock_extract:
            mock_extract.return_value = "PDF text content"

            result = extract_text_from_file(sample_pdf_content, "test.pdf")

            assert result == "PDF text content"
            mock_extract.assert_called_once_with(sample_pdf_content)

    def test_extract_text_from_file_docx(self):
        """Test DOCX text extraction via standalone function."""
        docx_content = b"PK\x03\x04"  # DOCX file signature

        with patch(
            "knowledge_service.services.content_extraction.extract_text_from_docx"
        ) as mock_extract:
            mock_extract.return_value = "DOCX text content"

            result = extract_text_from_file(docx_content, "test.docx")

            assert result == "DOCX text content"
            mock_extract.assert_called_once_with(docx_content)

    def test_extract_text_from_file_txt(self):
        """Test text file extraction via standalone function."""
        text_content = "Plain text content"
        text_bytes = text_content.encode("utf-8")

        result = extract_text_from_file(text_bytes, "test.txt")

        assert result == text_content

    def test_extract_text_from_file_unsupported(self):
        """Test unsupported file format via standalone function."""
        with pytest.raises(ContentExtractionError, match="Unsupported file format"):
            extract_text_from_file(b"content", "test.xlsx")

    @patch("PyPDF2.PdfReader")
    def test_extract_text_from_pdf_success(self, mock_pdf_reader):
        """Test successful PDF text extraction."""
        # Mock PDF reader
        mock_page = Mock()
        mock_page.extract_text.return_value = "Page text content"
        mock_reader_instance = Mock()
        mock_reader_instance.pages = [mock_page]
        mock_pdf_reader.return_value = mock_reader_instance

        result = extract_text_from_pdf(b"pdf content")

        assert result == "Page text content"

    @patch("PyPDF2.PdfReader")
    def test_extract_text_from_pdf_error(self, mock_pdf_reader):
        """Test PDF text extraction with error."""
        mock_pdf_reader.side_effect = Exception("PDF parsing error")

        with pytest.raises(
            ContentExtractionError, match="Failed to extract text from PDF"
        ):
            extract_text_from_pdf(b"invalid pdf content")

    @patch("docx.Document")
    def test_extract_text_from_docx_success(self, mock_document):
        """Test successful DOCX text extraction."""
        # Mock document paragraphs
        mock_paragraph1 = Mock()
        mock_paragraph1.text = "First paragraph"
        mock_paragraph2 = Mock()
        mock_paragraph2.text = "Second paragraph"

        mock_doc_instance = Mock()
        mock_doc_instance.paragraphs = [mock_paragraph1, mock_paragraph2]
        mock_document.return_value = mock_doc_instance

        result = extract_text_from_docx(b"docx content")

        assert result == "First paragraph\nSecond paragraph"

    @patch("docx.Document")
    def test_extract_text_from_docx_error(self, mock_document):
        """Test DOCX text extraction with error."""
        mock_document.side_effect = Exception("DOCX parsing error")

        with pytest.raises(
            ContentExtractionError, match="Failed to extract text from DOCX"
        ):
            extract_text_from_docx(b"invalid docx content")

    def test_extract_text_from_txt_utf8(self):
        """Test text extraction from UTF-8 encoded text."""
        text_content = "Hello, world! 🌍"
        text_bytes = text_content.encode("utf-8")

        result = extract_text_from_txt(text_bytes)

        assert result == text_content

    def test_extract_text_from_txt_latin1(self):
        """Test text extraction from Latin-1 encoded text."""
        text_content = "Café résumé"
        text_bytes = text_content.encode("latin-1")

        with patch("chardet.detect") as mock_detect:
            mock_detect.return_value = {"encoding": "latin-1", "confidence": 0.9}

            result = extract_text_from_txt(text_bytes)

            assert result == text_content

    def test_extract_text_from_txt_encoding_error(self):
        """Test text extraction with encoding error."""
        # Invalid UTF-8 bytes
        invalid_bytes = b"\xff\xfe\x00\x00"

        with patch("chardet.detect") as mock_detect:
            mock_detect.return_value = {"encoding": None, "confidence": 0.0}

            with pytest.raises(
                ContentExtractionError, match="Failed to decode text file"
            ):
                extract_text_from_txt(invalid_bytes)

    def test_extract_metadata_from_file_basic(self):
        """Test basic metadata extraction."""
        file_content = b"Sample file content"
        filename = "test.txt"

        metadata = extract_metadata_from_file(file_content, filename)

        assert "file_size" in metadata
        assert "file_type" in metadata
        assert "encoding" in metadata
        assert metadata["file_size"] == len(file_content)
        assert metadata["file_type"] == "txt"

    def test_extract_metadata_from_file_pdf(self):
        """Test metadata extraction from PDF."""
        pdf_content = b"%PDF-1.4 content"
        filename = "test.pdf"

        with patch("PyPDF2.PdfReader") as mock_reader:
            mock_metadata = {
                "/Title": "Test Document",
                "/Author": "Test Author",
                "/CreationDate": "D:20230101120000",
            }
            mock_reader_instance = Mock()
            mock_reader_instance.metadata = mock_metadata
            mock_reader.return_value = mock_reader_instance

            metadata = extract_metadata_from_file(pdf_content, filename)

            assert metadata["file_type"] == "pdf"
            assert "title" in metadata
            assert "author" in metadata

    def test_extract_metadata_from_file_error_handling(self):
        """Test metadata extraction with error handling."""
        file_content = b"content"
        filename = "test.pdf"

        with patch("PyPDF2.PdfReader") as mock_reader:
            mock_reader.side_effect = Exception("PDF error")

            # Should not raise exception, just return basic metadata
            metadata = extract_metadata_from_file(file_content, filename)

            assert "file_size" in metadata
            assert "file_type" in metadata
            assert metadata["file_type"] == "pdf"

    def test_content_extraction_error_creation(self):
        """Test ContentExtractionError creation."""
        error = ContentExtractionError("Test error message")

        assert str(error) == "Test error message"
        assert isinstance(error, Exception)

    def test_content_extraction_error_with_cause(self):
        """Test ContentExtractionError with underlying cause."""
        original_error = ValueError("Original error")
        error = ContentExtractionError("Extraction failed", original_error)

        assert str(error) == "Extraction failed"
        assert error.__cause__ == original_error
