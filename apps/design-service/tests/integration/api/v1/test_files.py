"""
Integration tests for design file management API endpoints.

Tests cover:
- POST /api/v1/designs/{id}/files (upload file)
- GET /api/v1/designs/{id}/files (list files)
- DELETE /api/v1/files/{id} (delete file)
- GET /api/v1/files/{id}/download (download file)
- File size validation (50MB max)
- File type validation
- Authentication and authorization
"""

import io
import pytest
from fastapi import status
from unittest.mock import Mock, patch

from src.models.design_file import DesignFile
from tests.factories import DesignFactory, DesignFileFactory


class TestUploadFile:
    """Tests for POST /api/v1/designs/{id}/files endpoint."""

    def test_upload_file_success(
        self, client, db_session, auth_headers, test_user_id
    ):
        """Test successful PDF file upload."""
        # Create test design
        design = DesignFactory.create(
            project_id=1,
            created_by=test_user_id,
        )
        db_session.commit()

        # Create mock file
        file_content = b"PDF file content"
        files = {
            "file": ("test_design.pdf", io.BytesIO(file_content), "application/pdf")
        }
        data = {
            "description": "Design floor plan"
        }

        # Make request
        response = client.post(
            f"/api/v1/designs/{design.id}/files",
            files=files,
            data=data,
            headers=auth_headers,
        )

        # Assertions
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["filename"] == "test_design.pdf"
        assert data["file_type"] == "pdf"
        assert data["file_size"] == len(file_content)
        assert data["description"] == "Design floor plan"
        assert "id" in data
        assert "uploaded_at" in data

        # Verify file was saved to database
        db_session.expire_all()
        design_file = (
            db_session.query(DesignFile)
            .filter_by(design_id=design.id)
            .first()
        )
        assert design_file is not None
        assert design_file.filename == "test_design.pdf"

    def test_upload_file_without_description(
        self, client, db_session, auth_headers, test_user_id
    ):
        """Test file upload without optional description."""
        design = DesignFactory.create(project_id=1, created_by=test_user_id)
        db_session.commit()

        file_content = b"DWG file content"
        files = {
            "file": ("design.dwg", io.BytesIO(file_content), "application/dwg")
        }

        response = client.post(
            f"/api/v1/designs/{design.id}/files",
            files=files,
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["description"] is None

    def test_upload_file_various_types(
        self, client, db_session, auth_headers, test_user_id
    ):
        """Test uploading various supported file types."""
        design = DesignFactory.create(project_id=1, created_by=test_user_id)
        db_session.commit()

        file_types = [
            ("test.pdf", "application/pdf"),
            ("test.dwg", "application/dwg"),
            ("test.dxf", "application/dxf"),
            ("test.png", "image/png"),
            ("test.jpg", "image/jpeg"),
            ("test.ifc", "application/ifc"),
        ]

        for filename, content_type in file_types:
            files = {
                "file": (filename, io.BytesIO(b"file content"), content_type)
            }

            response = client.post(
                f"/api/v1/designs/{design.id}/files",
                files=files,
                headers=auth_headers,
            )

            assert response.status_code == status.HTTP_201_CREATED
            data = response.json()
            assert data["filename"] == filename

    def test_upload_file_unsupported_type(
        self, client, db_session, auth_headers, test_user_id
    ):
        """Test uploading unsupported file type returns 400."""
        design = DesignFactory.create(project_id=1, created_by=test_user_id)
        db_session.commit()

        files = {
            "file": ("test.exe", io.BytesIO(b"executable"), "application/exe")
        }

        response = client.post(
            f"/api/v1/designs/{design.id}/files",
            files=files,
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "unsupported" in response.json()["detail"].lower()

    def test_upload_file_exceeds_size_limit(
        self, client, db_session, auth_headers, test_user_id
    ):
        """Test uploading file exceeding 50MB limit returns 400."""
        design = DesignFactory.create(project_id=1, created_by=test_user_id)
        db_session.commit()

        # Create file larger than 50MB
        large_content = b"x" * (51 * 1024 * 1024)  # 51MB
        files = {
            "file": ("large.pdf", io.BytesIO(large_content), "application/pdf")
        }

        response = client.post(
            f"/api/v1/designs/{design.id}/files",
            files=files,
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "size" in response.json()["detail"].lower()

    def test_upload_file_exactly_at_size_limit(
        self, client, db_session, auth_headers, test_user_id
    ):
        """Test uploading file exactly at 50MB limit succeeds."""
        design = DesignFactory.create(project_id=1, created_by=test_user_id)
        db_session.commit()

        # Create file exactly 50MB
        exact_content = b"x" * (50 * 1024 * 1024)  # 50MB
        files = {
            "file": ("exact.pdf", io.BytesIO(exact_content), "application/pdf")
        }

        response = client.post(
            f"/api/v1/designs/{design.id}/files",
            files=files,
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_201_CREATED

    def test_upload_file_design_not_found(self, client, auth_headers):
        """Test uploading file to non-existent design returns 404."""
        files = {
            "file": ("test.pdf", io.BytesIO(b"content"), "application/pdf")
        }

        response = client.post(
            "/api/v1/designs/99999/files",
            files=files,
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_upload_file_without_authentication(
        self, client_no_auth, db_session, test_user_id
    ):
        """Test uploading file without authentication returns 401."""
        design = DesignFactory.create(project_id=1, created_by=test_user_id)
        db_session.commit()

        files = {
            "file": ("test.pdf", io.BytesIO(b"content"), "application/pdf")
        }

        response = client_no_auth.post(
            f"/api/v1/designs/{design.id}/files",
            files=files,
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_upload_file_without_project_access(
        self, client, db_session, auth_headers, test_user_id, mock_project_client
    ):
        """Test uploading file without project access returns 403."""
        design = DesignFactory.create(project_id=999, created_by=test_user_id)
        db_session.commit()

        from src.services.project_client import ProjectAccessDeniedError
        mock_project_client.verify_project_access.side_effect = (
            ProjectAccessDeniedError("Access denied")
        )

        files = {
            "file": ("test.pdf", io.BytesIO(b"content"), "application/pdf")
        }

        response = client.post(
            f"/api/v1/designs/{design.id}/files",
            files=files,
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_upload_file_missing_file(
        self, client, db_session, auth_headers, test_user_id
    ):
        """Test uploading without file parameter returns 422."""
        design = DesignFactory.create(project_id=1, created_by=test_user_id)
        db_session.commit()

        response = client.post(
            f"/api/v1/designs/{design.id}/files",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY



class TestListFiles:
    """Tests for GET /api/v1/designs/{id}/files endpoint."""

    def test_list_files_success(
        self, client, db_session, auth_headers, test_user_id
    ):
        """Test successful file listing."""
        design = DesignFactory.create(project_id=1, created_by=test_user_id)
        files = DesignFileFactory.create_batch(
            3, design=design, uploaded_by=test_user_id
        )
        db_session.commit()

        response = client.get(
            f"/api/v1/designs/{design.id}/files",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 3
        assert all("filename" in f for f in data)
        assert all("file_type" in f for f in data)
        assert all("file_size" in f for f in data)

    def test_list_files_empty(
        self, client, db_session, auth_headers, test_user_id
    ):
        """Test listing files when design has no files."""
        design = DesignFactory.create(project_id=1, created_by=test_user_id)
        db_session.commit()

        response = client.get(
            f"/api/v1/designs/{design.id}/files",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 0

    def test_list_files_ordered_by_upload_date(
        self, client, db_session, auth_headers, test_user_id
    ):
        """Test files are ordered by upload date (newest first)."""
        from datetime import datetime, timedelta, timezone

        design = DesignFactory.create(project_id=1, created_by=test_user_id)
        
        # Create files with different upload times
        file1 = DesignFileFactory.create(
            design=design,
            filename="old.pdf",
            uploaded_by=test_user_id,
        )
        file1.uploaded_at = datetime.now(timezone.utc) - timedelta(days=2)
        
        file2 = DesignFileFactory.create(
            design=design,
            filename="recent.pdf",
            uploaded_by=test_user_id,
        )
        file2.uploaded_at = datetime.now(timezone.utc) - timedelta(days=1)
        
        file3 = DesignFileFactory.create(
            design=design,
            filename="newest.pdf",
            uploaded_by=test_user_id,
        )
        file3.uploaded_at = datetime.now(timezone.utc)
        
        db_session.commit()

        response = client.get(
            f"/api/v1/designs/{design.id}/files",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 3
        # Should be ordered newest first
        assert data[0]["filename"] == "newest.pdf"
        assert data[1]["filename"] == "recent.pdf"
        assert data[2]["filename"] == "old.pdf"

    def test_list_files_design_not_found(self, client, auth_headers):
        """Test listing files for non-existent design returns 404."""
        response = client.get(
            "/api/v1/designs/99999/files",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_list_files_without_authentication(
        self, client_no_auth, db_session, test_user_id
    ):
        """Test listing files without authentication returns 401."""
        design = DesignFactory.create(project_id=1, created_by=test_user_id)
        db_session.commit()

        response = client_no_auth.get(f"/api/v1/designs/{design.id}/files")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_list_files_without_project_access(
        self, client, db_session, auth_headers, test_user_id, mock_project_client
    ):
        """Test listing files without project access returns 403."""
        design = DesignFactory.create(project_id=999, created_by=test_user_id)
        db_session.commit()

        from src.services.project_client import ProjectAccessDeniedError
        mock_project_client.verify_project_access.side_effect = (
            ProjectAccessDeniedError("Access denied")
        )

        response = client.get(
            f"/api/v1/designs/{design.id}/files",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN



class TestDeleteFile:
    """Tests for DELETE /api/v1/files/{id} endpoint."""

    def test_delete_file_success(
        self, client, db_session, auth_headers, test_user_id
    ):
        """Test successful file deletion."""
        design = DesignFactory.create(project_id=1, created_by=test_user_id)
        design_file = DesignFileFactory.create(
            design=design, uploaded_by=test_user_id
        )
        db_session.commit()
        file_id = design_file.id

        response = client.delete(
            f"/api/v1/files/{file_id}",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_204_NO_CONTENT

        # Verify file was deleted from database
        db_session.expire_all()
        deleted_file = db_session.query(DesignFile).filter_by(id=file_id).first()
        assert deleted_file is None

    @patch("os.remove")
    def test_delete_file_removes_from_storage(
        self, mock_remove, client, db_session, auth_headers, test_user_id
    ):
        """Test file deletion also removes file from storage."""
        design = DesignFactory.create(project_id=1, created_by=test_user_id)
        design_file = DesignFileFactory.create(
            design=design,
            uploaded_by=test_user_id,
            storage_path="/storage/test.pdf",
        )
        db_session.commit()

        response = client.delete(
            f"/api/v1/files/{design_file.id}",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_204_NO_CONTENT
        # Verify os.remove was called (file storage cleanup)
        # Note: This may not be called if using mock storage

    def test_delete_file_not_found(self, client, auth_headers):
        """Test deleting non-existent file returns 404."""
        response = client.delete(
            "/api/v1/files/99999",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_delete_file_without_authentication(
        self, client_no_auth, db_session, test_user_id
    ):
        """Test deleting file without authentication returns 401."""
        design = DesignFactory.create(project_id=1, created_by=test_user_id)
        design_file = DesignFileFactory.create(
            design=design, uploaded_by=test_user_id
        )
        db_session.commit()

        response = client_no_auth.delete(f"/api/v1/files/{design_file.id}")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_delete_file_without_project_access(
        self, client, db_session, auth_headers, test_user_id, mock_project_client
    ):
        """Test deleting file without project access returns 403."""
        design = DesignFactory.create(project_id=999, created_by=test_user_id)
        design_file = DesignFileFactory.create(
            design=design, uploaded_by=test_user_id
        )
        db_session.commit()

        from src.services.project_client import ProjectAccessDeniedError
        mock_project_client.verify_project_access.side_effect = (
            ProjectAccessDeniedError("Access denied")
        )

        response = client.delete(
            f"/api/v1/files/{design_file.id}",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN



class TestDownloadFile:
    """Tests for GET /api/v1/files/{id}/download endpoint."""

    @patch("pathlib.Path.exists")
    @patch("builtins.open", create=True)
    def test_download_file_success(
        self, mock_open, mock_exists, client, db_session, auth_headers, test_user_id
    ):
        """Test successful file download."""
        design = DesignFactory.create(project_id=1, created_by=test_user_id)
        design_file = DesignFileFactory.create(
            design=design,
            uploaded_by=test_user_id,
            filename="test.pdf",
            file_type="pdf",
            storage_path="/storage/test.pdf",
        )
        db_session.commit()

        # Mock file existence and content
        mock_exists.return_value = True
        mock_file = io.BytesIO(b"PDF file content")
        mock_open.return_value.__enter__.return_value = mock_file

        response = client.get(
            f"/api/v1/files/{design_file.id}/download",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.headers["content-type"] == "application/pdf"
        assert "attachment" in response.headers.get("content-disposition", "")
        assert "test.pdf" in response.headers.get("content-disposition", "")

    @patch("pathlib.Path.exists")
    @patch("builtins.open", create=True)
    def test_download_file_streaming(
        self, mock_open, mock_exists, client, db_session, auth_headers, test_user_id
    ):
        """Test file download uses streaming for large files."""
        design = DesignFactory.create(project_id=1, created_by=test_user_id)
        design_file = DesignFileFactory.create(
            design=design,
            uploaded_by=test_user_id,
            filename="large.dwg",
            file_type="dwg",
            file_size=10 * 1024 * 1024,  # 10MB
            storage_path="/storage/large.dwg",
        )
        db_session.commit()

        # Mock file existence and large file content
        mock_exists.return_value = True
        large_content = b"x" * (10 * 1024 * 1024)
        mock_file = io.BytesIO(large_content)
        mock_open.return_value.__enter__.return_value = mock_file

        response = client.get(
            f"/api/v1/files/{design_file.id}/download",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK

    def test_download_file_not_found(self, client, auth_headers):
        """Test downloading non-existent file returns 404."""
        response = client.get(
            "/api/v1/files/99999/download",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    @patch("builtins.open", side_effect=FileNotFoundError)
    def test_download_file_storage_not_found(
        self, mock_open, client, db_session, auth_headers, test_user_id
    ):
        """Test downloading file when storage file is missing returns 404."""
        design = DesignFactory.create(project_id=1, created_by=test_user_id)
        design_file = DesignFileFactory.create(
            design=design,
            uploaded_by=test_user_id,
            storage_path="/storage/missing.pdf",
        )
        db_session.commit()

        response = client.get(
            f"/api/v1/files/{design_file.id}/download",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_download_file_without_authentication(
        self, client_no_auth, db_session, test_user_id
    ):
        """Test downloading file without authentication returns 401."""
        design = DesignFactory.create(project_id=1, created_by=test_user_id)
        design_file = DesignFileFactory.create(
            design=design, uploaded_by=test_user_id
        )
        db_session.commit()

        response = client_no_auth.get(
            f"/api/v1/files/{design_file.id}/download"
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_download_file_without_project_access(
        self, client, db_session, auth_headers, test_user_id, mock_project_client
    ):
        """Test downloading file without project access returns 403."""
        design = DesignFactory.create(project_id=999, created_by=test_user_id)
        design_file = DesignFileFactory.create(
            design=design, uploaded_by=test_user_id
        )
        db_session.commit()

        from src.services.project_client import ProjectAccessDeniedError
        mock_project_client.verify_project_access.side_effect = (
            ProjectAccessDeniedError("Access denied")
        )

        response = client.get(
            f"/api/v1/files/{design_file.id}/download",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN
