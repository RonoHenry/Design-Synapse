"""
TDD Tests for PDF Processing Service - RED Phase (Failing Tests)

Following TDD methodology:
1. RED: Write failing tests first
2. GREEN: Implement minimal code to pass tests
3. REFACTOR: Improve code while keeping tests green
"""

import tempfile
from io import BytesIO
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi import HTTPException, UploadFile
from knowledge_service.models.resource import Resource
from knowledge_service.services.pdf_processing import PDFProcessingService


class TestPDFProcessingServiceTDD:
    """TDD tests for PDF processing functionality."""

    @pytest.fixture
    def pdf_service(self):
        """Create PDF processing service with temp storage."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield PDFProcessingService(storage_path=temp_dir)

    @pytest.fixture
    def mock_pdf_file(self):
        """Create a mock PDF file for testing."""
        pdf_content = (
            b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n"
        )
        file_obj = BytesIO(pdf_content)

        mock_file = Mock(spec=UploadFile)
        mock_file.filename = "test.pdf"
        mock_file.read = AsyncMock(return_value=pdf_content)
        mock_file.content_type = "application/pdf"

        return mock_file

    @pytest.fixture
    def mock_resource(self, db_session):
        """Create a mock resource for testing."""
        resource = Resource(
            title="Test Resource",
            description="Test Description",
            content_type="pdf",
            source_url="https://example.com/test.pdf",
            storage_path="",
            file_size=0,
        )
        db_session.add(resource)
        db_session.commit()
        return resource

    # RED PHASE: Write failing tests first

    @pytest.mark.asyncio
    async def test_process_pdf_validates_file_extension(self, pdf_service, db_session):
        """Test that PDF processing validates file extensions - SHOULD FAIL initially."""
        # Create a non-PDF file
        non_pdf_file = Mock(spec=UploadFile)
        non_pdf_file.filename = "test.txt"
        non_pdf_file.content_type = "text/plain"

        resource = Mock()

        # This test should FAIL until we implement proper validation
        with pytest.raises(HTTPException) as exc_info:
            await pdf_service.process_pdf(non_pdf_file, resource, db_session)

        assert exc_info.value.status_code == 400
        assert "must be a PDF" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_process_pdf_validates_file_size_limit(self, pdf_service, db_session):
        """Test that PDF processing validates file size limits - SHOULD FAIL initially."""
        # Create a large mock file (>50MB)
        large_file = Mock(spec=UploadFile)
        large_file.filename = "large.pdf"
        large_file.read = AsyncMock(return_value=b"x" * (51 * 1024 * 1024))  # 51MB

        resource = Mock()

        # This test should FAIL until we implement size validation
        with pytest.raises(HTTPException) as exc_info:
            await pdf_service.process_pdf(large_file, resource, db_session)

        assert exc_info.value.status_code == 413  # Payload Too Large
        assert "file too large" in str(exc_info.value.detail).lower()

    @pytest.mark.asyncio
    async def test_process_pdf_validates_file_content_type(
        self, pdf_service, db_session
    ):
        """Test that PDF processing validates actual file content - SHOULD FAIL initially."""
        # Create a file with PDF extension but non-PDF content
        fake_pdf = Mock(spec=UploadFile)
        fake_pdf.filename = "fake.pdf"
        fake_pdf.read = AsyncMock(return_value=b"This is not a PDF file")
        fake_pdf.content_type = "application/pdf"

        resource = Mock()

        # This test should FAIL until we implement content validation
        with pytest.raises(HTTPException) as exc_info:
            await pdf_service.process_pdf(fake_pdf, resource, db_session)

        assert exc_info.value.status_code == 400
        assert "invalid PDF" in str(exc_info.value.detail).lower()

    @pytest.mark.asyncio
    async def test_process_pdf_extracts_text_content(
        self, pdf_service, mock_pdf_file, mock_resource, db_session
    ):
        """Test that PDF processing extracts text content - SHOULD FAIL initially."""
        # Mock the text extraction to return expected content
        expected_text = "This is extracted PDF text content"

        with patch.object(pdf_service, "_extract_text", return_value=expected_text):
            with patch(
                "knowledge_service.core.vector_search.get_vector_search_service"
            ) as mock_vector:
                mock_vector_service = Mock()
                mock_vector_service.update_resource = AsyncMock()
                mock_vector.return_value = mock_vector_service

                storage_path, file_size = await pdf_service.process_pdf(
                    mock_pdf_file, mock_resource, db_session
                )

                # This assertion should FAIL until we properly integrate text extraction
                mock_vector_service.update_resource.assert_called_once()
                call_args = mock_vector_service.update_resource.call_args[0]
                assert (
                    call_args[2] == expected_text
                )  # Third argument should be extracted text

    @pytest.mark.asyncio
    async def test_process_pdf_handles_corrupted_files(self, pdf_service, db_session):
        """Test that PDF processing handles corrupted files gracefully - SHOULD FAIL initially."""
        # Create a corrupted PDF file
        corrupted_pdf = Mock(spec=UploadFile)
        corrupted_pdf.filename = "corrupted.pdf"
        corrupted_pdf.read = AsyncMock(return_value=b"%PDF-1.4\ncorrupted content")

        resource = Mock()

        # This test should FAIL until we implement proper error handling
        with pytest.raises(HTTPException) as exc_info:
            await pdf_service.process_pdf(corrupted_pdf, resource, db_session)

        assert exc_info.value.status_code == 422  # Unprocessable Entity
        assert "corrupted" in str(exc_info.value.detail).lower()

    @pytest.mark.asyncio
    async def test_process_pdf_updates_resource_metadata(
        self, pdf_service, mock_pdf_file, mock_resource, db_session
    ):
        """Test that PDF processing updates resource with metadata - SHOULD FAIL initially."""
        with patch.object(pdf_service, "_extract_text", return_value="test content"):
            with patch(
                "knowledge_service.core.vector_search.get_vector_search_service"
            ) as mock_vector:
                mock_vector_service = Mock()
                mock_vector_service.update_resource = AsyncMock()
                mock_vector.return_value = mock_vector_service

                initial_storage_path = mock_resource.storage_path
                initial_file_size = mock_resource.file_size

                await pdf_service.process_pdf(mock_pdf_file, mock_resource, db_session)

                # These assertions should FAIL until we properly update resource metadata
                assert mock_resource.storage_path != initial_storage_path
                assert mock_resource.file_size > initial_file_size
                assert Path(mock_resource.storage_path).exists()

    def test_extract_metadata_returns_comprehensive_info(self, pdf_service):
        """Test that metadata extraction returns comprehensive PDF info - SHOULD FAIL initially."""
        # This test should FAIL until we implement comprehensive metadata extraction
        test_pdf_path = "test.pdf"  # This file doesn't exist yet

        # Mock the PDF opening to return expected metadata
        with patch("fitz.open") as mock_fitz:
            mock_pdf = Mock()
            mock_pdf.metadata = {
                "title": "Test Document",
                "author": "Test Author",
                "subject": "Test Subject",
                "keywords": "test, keywords",
                "creator": "Test Creator",
                "producer": "Test Producer",
                "creationDate": "D:20231201120000Z",
                "modDate": "D:20231201120000Z",
            }
            mock_pdf.__len__ = Mock(return_value=5)  # 5 pages
            mock_fitz.return_value.__enter__.return_value = mock_pdf

            metadata = pdf_service.extract_metadata(test_pdf_path)

            # These assertions should FAIL until we implement proper metadata extraction
            assert metadata["title"] == "Test Document"
            assert metadata["author"] == "Test Author"
            assert metadata["page_count"] == 5
            assert "creation_date" in metadata
            assert "modification_date" in metadata

    def test_extract_text_with_layout_preserves_structure(self, pdf_service):
        """Test that text extraction preserves layout information - SHOULD FAIL initially."""
        test_pdf_path = "test.pdf"

        # Mock the PDF structure
        with patch("fitz.open") as mock_fitz:
            mock_page = Mock()
            mock_page.get_text.return_value = {
                "blocks": [
                    {
                        "type": 0,  # Text block
                        "bbox": [100, 100, 200, 120],
                        "lines": [{"text": "Sample text line"}],
                    },
                    {"type": 1, "bbox": [100, 150, 300, 250]},  # Image block
                ]
            }
            mock_page.rect.width = 612
            mock_page.rect.height = 792

            mock_pdf = Mock()
            mock_pdf.__iter__ = Mock(return_value=iter([mock_page]))
            mock_fitz.return_value.__enter__.return_value = mock_pdf

            layout_data = pdf_service.extract_text_with_layout(test_pdf_path)

            # These assertions should FAIL until we implement layout preservation
            assert "pages" in layout_data
            assert len(layout_data["pages"]) == 1
            assert layout_data["pages"][0]["width"] == 612
            assert layout_data["pages"][0]["height"] == 792
            assert len(layout_data["pages"][0]["blocks"]) == 2
            assert layout_data["pages"][0]["blocks"][0]["type"] == "text"
            assert layout_data["pages"][0]["blocks"][1]["type"] == "image"

    @pytest.mark.asyncio
    async def test_generate_thumbnails_creates_preview_images(self, pdf_service):
        """Test that thumbnail generation creates preview images - SHOULD FAIL initially."""
        test_pdf_path = "test.pdf"

        # Mock the PDF and image generation
        with patch("fitz.open") as mock_fitz:
            with patch("PIL.Image.frombytes") as mock_image:
                mock_page = Mock()
                mock_pixmap = Mock()
                mock_pixmap.width = 200
                mock_pixmap.height = 300
                mock_pixmap.samples = b"mock_image_data"
                mock_page.get_pixmap.return_value = mock_pixmap

                mock_pdf = Mock()
                mock_pdf.__iter__ = Mock(
                    return_value=iter([mock_page, mock_page])
                )  # 2 pages
                mock_fitz.return_value.__enter__.return_value = mock_pdf

                mock_img = Mock()
                mock_img.thumbnail = Mock()
                mock_img.save = Mock()
                mock_image.return_value = mock_img

                thumbnails = await pdf_service.generate_thumbnails(test_pdf_path)

                # These assertions should FAIL until we implement thumbnail generation
                assert len(thumbnails) == 2  # Should have 2 thumbnails for 2 pages
                assert all(isinstance(thumb, bytes) for thumb in thumbnails)
                mock_img.thumbnail.assert_called()
                mock_img.save.assert_called()

    @pytest.mark.asyncio
    async def test_process_pdf_cleans_up_on_failure(self, pdf_service, db_session):
        """Test that PDF processing cleans up files on failure - SHOULD FAIL initially."""
        # Create a file that will cause processing to fail
        failing_file = Mock(spec=UploadFile)
        failing_file.filename = "test.pdf"
        failing_file.read = AsyncMock(return_value=b"valid pdf content")

        resource = Mock()

        # Mock vector service to raise an exception
        with patch(
            "knowledge_service.core.vector_search.get_vector_search_service"
        ) as mock_vector:
            mock_vector_service = Mock()
            mock_vector_service.update_resource = AsyncMock(
                side_effect=Exception("Vector service failed")
            )
            mock_vector.return_value = mock_vector_service

            with pytest.raises(HTTPException):
                await pdf_service.process_pdf(failing_file, resource, db_session)

            # This assertion should FAIL until we implement proper cleanup
            # Check that no files were left behind in storage
            storage_files = list(Path(pdf_service.storage_path).glob("*.pdf"))
            assert len(storage_files) == 0, "Files should be cleaned up on failure"

    def test_get_pdf_path_handles_missing_files(self, pdf_service):
        """Test that get_pdf_path handles missing files gracefully - SHOULD FAIL initially."""
        # Create a resource with a non-existent file path
        resource = Mock()
        resource.storage_path = "/non/existent/path.pdf"

        # This should FAIL until we implement proper file existence checking
        result = pdf_service.get_pdf_path(resource)
        assert result is None

    def test_get_pdf_path_returns_valid_path(self, pdf_service):
        """Test that get_pdf_path returns valid path for existing files - SHOULD FAIL initially."""
        # Create a temporary file
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as temp_file:
            temp_path = temp_file.name

        try:
            resource = Mock()
            resource.storage_path = temp_path

            # This should FAIL until we implement proper path validation
            result = pdf_service.get_pdf_path(resource)
            assert result is not None
            assert isinstance(result, Path)
            assert result.exists()

        finally:
            Path(temp_path).unlink(missing_ok=True)


class TestPDFProcessingServicePerformance:
    """Performance-focused TDD tests - these should FAIL initially."""

    @pytest.mark.asyncio
    async def test_process_large_pdf_within_time_limit(self, pdf_service):
        """Test that large PDF processing completes within acceptable time - SHOULD FAIL initially."""
        import time

        # Create a mock large PDF file
        large_pdf = Mock(spec=UploadFile)
        large_pdf.filename = "large.pdf"
        large_pdf.read = AsyncMock(return_value=b"x" * (10 * 1024 * 1024))  # 10MB

        resource = Mock()
        db_session = Mock()

        with patch.object(pdf_service, "_extract_text", return_value="large content"):
            with patch(
                "knowledge_service.core.vector_search.get_vector_search_service"
            ):
                start_time = time.time()
                await pdf_service.process_pdf(large_pdf, resource, db_session)
                processing_time = time.time() - start_time

                # This should FAIL until we optimize processing performance
                assert (
                    processing_time < 30.0
                ), f"Processing took {processing_time:.2f}s, should be under 30s"

    @pytest.mark.asyncio
    async def test_concurrent_pdf_processing(self, pdf_service):
        """Test that concurrent PDF processing works correctly - SHOULD FAIL initially."""
        import asyncio

        # Create multiple mock PDF files
        pdf_files = []
        for i in range(5):
            mock_file = Mock(spec=UploadFile)
            mock_file.filename = f"test_{i}.pdf"
            mock_file.read = AsyncMock(return_value=b"pdf content")
            pdf_files.append(mock_file)

        resources = [Mock() for _ in range(5)]
        db_session = Mock()

        with patch.object(pdf_service, "_extract_text", return_value="content"):
            with patch(
                "knowledge_service.core.vector_search.get_vector_search_service"
            ):
                # Process files concurrently
                tasks = [
                    pdf_service.process_pdf(pdf_file, resource, db_session)
                    for pdf_file, resource in zip(pdf_files, resources)
                ]

                # This should FAIL until we implement proper concurrent processing
                results = await asyncio.gather(*tasks, return_exceptions=True)

                # All should succeed
                assert all(not isinstance(result, Exception) for result in results)
                assert len(results) == 5


# Note: These tests are designed to FAIL initially.
# The next step in TDD is to implement the minimal code to make them pass (GREEN phase).
# Then refactor the implementation while keeping tests green (REFACTOR phase).
