"""Integration tests for drawing management endpoints."""

import io
from datetime import datetime
from uuid import UUID, uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from src.models.design import Design
from src.models.drawing import Drawing


class TestDrawingEndpoints:
    """Test drawing management endpoints."""

    @pytest.fixture
    async def sample_design(self, test_session: AsyncSession):
        """Create a sample design for testing."""
        design_id = str(uuid4())
        project_id = str(uuid4())
        user_id = str(uuid4())

        design = Design(
            id=design_id,
            project_id=project_id,
            name="Test Design",
            description="Test design for drawing tests",
            building_type="commercial",
            location_data={
                "address": "123 Test St",
                "city": "Test City",
                "state": "Test State",
                "country": "Test Country",
            },
            current_version="1.0",
            version_number=1,
            status="draft",
            metadata={},
            created_by=user_id,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            is_deleted=False,
        )

        test_session.add(design)
        await test_session.commit()
        return design

    @pytest.fixture
    def auth_headers(self):
        """Authentication headers for testing."""
        return {"Authorization": "Bearer test-token"}

    @pytest.fixture
    def sample_pdf_file(self):
        """Create a sample PDF file for testing."""
        # Create a minimal PDF content
        pdf_content = b"""%PDF-1.4
1 0 obj
<<
/Type /Catalog
/Pages 2 0 R
>>
endobj
2 0 obj
<<
/Type /Pages
/Kids [3 0 R]
/Count 1
>>
endobj
3 0 obj
<<
/Type /Page
/Parent 2 0 R
/MediaBox [0 0 612 792]
>>
endobj
xref
0 4
0000000000 65535 f
0000000009 00000 n
0000000058 00000 n
0000000115 00000 n
trailer
<<
/Size 4
/Root 1 0 R
>>
startxref
181
%%EOF"""
        return io.BytesIO(pdf_content)

    async def test_upload_drawing_success(
        self,
        client: AsyncClient,
        sample_design: Design,
        sample_pdf_file: io.BytesIO,
        auth_headers: dict,
    ):
        """Test successful drawing upload."""
        files = {"file": ("test_drawing.pdf", sample_pdf_file, "application/pdf")}
        data = {
            "drawing_type": "floor_plan",
            "scale": "1/4\"=1'",
            "sheet_number": "A-101",
            "metadata": '{"level": "Ground Floor", "revision": "A"}',
        }

        response = await client.post(
            f"/api/v1/designs/{sample_design.id}/drawings",
            files=files,
            data=data,
            headers=auth_headers,
        )

        assert response.status_code == 201
        result = response.json()

        assert "id" in result
        assert result["design_id"] == sample_design.id
        assert result["design_version"] == "1.0"
        assert result["drawing_type"] == "floor_plan"
        assert result["scale"] == "1/4\"=1'"
        assert result["sheet_number"] == "A-101"
        assert result["metadata"]["level"] == "Ground Floor"
        assert result["metadata"]["revision"] == "A"
        assert result["mime_type"] == "application/pdf"
        assert result["file_size"] > 0
        assert "file_url" in result
        assert "created_by" in result
        assert "created_at" in result

    async def test_upload_drawing_invalid_file_type(
        self,
        client: AsyncClient,
        sample_design: Design,
        auth_headers: dict,
    ):
        """Test drawing upload with invalid file type."""
        # Create a text file instead of a valid drawing file
        text_file = io.BytesIO(b"This is not a valid drawing file")

        files = {"file": ("test.txt", text_file, "text/plain")}
        data = {
            "drawing_type": "floor_plan",
        }

        response = await client.post(
            f"/api/v1/designs/{sample_design.id}/drawings",
            files=files,
            data=data,
            headers=auth_headers,
        )

        assert response.status_code == 400
        result = response.json()
        assert "error" in result

    async def test_upload_drawing_invalid_metadata(
        self,
        client: AsyncClient,
        sample_design: Design,
        sample_pdf_file: io.BytesIO,
        auth_headers: dict,
    ):
        """Test drawing upload with invalid JSON metadata."""
        files = {"file": ("test_drawing.pdf", sample_pdf_file, "application/pdf")}
        data = {
            "drawing_type": "floor_plan",
            "metadata": "invalid json",  # Invalid JSON
        }

        response = await client.post(
            f"/api/v1/designs/{sample_design.id}/drawings",
            files=files,
            data=data,
            headers=auth_headers,
        )

        assert response.status_code == 400
        result = response.json()
        assert "Invalid JSON in metadata field" in result["error"]

    async def test_upload_drawing_design_not_found(
        self,
        client: AsyncClient,
        sample_pdf_file: io.BytesIO,
        auth_headers: dict,
    ):
        """Test drawing upload to non-existent design."""
        non_existent_id = str(uuid4())

        files = {"file": ("test_drawing.pdf", sample_pdf_file, "application/pdf")}
        data = {
            "drawing_type": "floor_plan",
        }

        response = await client.post(
            f"/api/v1/designs/{non_existent_id}/drawings",
            files=files,
            data=data,
            headers=auth_headers,
        )

        assert response.status_code == 404

    async def test_list_drawings_success(
        self,
        client: AsyncClient,
        sample_design: Design,
        test_session: AsyncSession,
    ):
        """Test successful drawing listing."""
        # Create some drawings
        drawing1 = Drawing(
            id=str(uuid4()),
            design_id=sample_design.id,
            design_version="1.0",
            drawing_type="floor_plan",
            file_url="https://storage.example.com/drawing1.pdf",
            file_size=1024,
            mime_type="application/pdf",
            scale="1/4\"=1'",
            sheet_number="A-101",
            metadata={"level": "Ground Floor"},
            created_by=str(uuid4()),
            created_at=datetime.utcnow(),
        )

        drawing2 = Drawing(
            id=str(uuid4()),
            design_id=sample_design.id,
            design_version="1.0",
            drawing_type="elevation",
            file_url="https://storage.example.com/drawing2.pdf",
            file_size=2048,
            mime_type="application/pdf",
            scale="1/8\"=1'",
            sheet_number="A-201",
            metadata={"view": "North Elevation"},
            created_by=str(uuid4()),
            created_at=datetime.utcnow(),
        )

        test_session.add_all([drawing1, drawing2])
        await test_session.commit()

        response = await client.get(f"/api/v1/designs/{sample_design.id}/drawings")

        assert response.status_code == 200
        result = response.json()

        assert result["total"] == 2
        assert len(result["drawings"]) == 2

        # Check first drawing
        drawing_data = result["drawings"][0]
        assert drawing_data["drawing_type"] == "floor_plan"
        assert drawing_data["scale"] == "1/4\"=1'"
        assert drawing_data["sheet_number"] == "A-101"
        assert drawing_data["metadata"]["level"] == "Ground Floor"

    async def test_list_drawings_with_filter(
        self,
        client: AsyncClient,
        sample_design: Design,
        test_session: AsyncSession,
    ):
        """Test drawing listing with type filter."""
        # Create drawings of different types
        drawing1 = Drawing(
            id=str(uuid4()),
            design_id=sample_design.id,
            design_version="1.0",
            drawing_type="floor_plan",
            file_url="https://storage.example.com/drawing1.pdf",
            file_size=1024,
            mime_type="application/pdf",
            created_by=str(uuid4()),
            created_at=datetime.utcnow(),
        )

        drawing2 = Drawing(
            id=str(uuid4()),
            design_id=sample_design.id,
            design_version="1.0",
            drawing_type="elevation",
            file_url="https://storage.example.com/drawing2.pdf",
            file_size=2048,
            mime_type="application/pdf",
            created_by=str(uuid4()),
            created_at=datetime.utcnow(),
        )

        test_session.add_all([drawing1, drawing2])
        await test_session.commit()

        # Filter by floor_plan type
        response = await client.get(
            f"/api/v1/designs/{sample_design.id}/drawings?drawing_type=floor_plan"
        )

        assert response.status_code == 200
        result = response.json()

        assert result["total"] == 1
        assert len(result["drawings"]) == 1
        assert result["drawings"][0]["drawing_type"] == "floor_plan"

    async def test_list_drawings_design_not_found(self, client: AsyncClient):
        """Test drawing listing for non-existent design."""
        non_existent_id = str(uuid4())

        response = await client.get(f"/api/v1/designs/{non_existent_id}/drawings")

        assert response.status_code == 404

    async def test_get_drawing_success(
        self,
        client: AsyncClient,
        sample_design: Design,
        test_session: AsyncSession,
    ):
        """Test successful drawing retrieval."""
        drawing_id = str(uuid4())
        drawing = Drawing(
            id=drawing_id,
            design_id=sample_design.id,
            design_version="1.0",
            drawing_type="floor_plan",
            file_url="https://storage.example.com/drawings/test.pdf",
            file_size=1024,
            mime_type="application/pdf",
            scale="1/4\"=1'",
            sheet_number="A-101",
            metadata={"level": "Ground Floor", "revision": "A"},
            created_by=str(uuid4()),
            created_at=datetime.utcnow(),
        )

        test_session.add(drawing)
        await test_session.commit()

        response = await client.get(f"/api/v1/drawings/{drawing_id}")

        assert response.status_code == 200
        result = response.json()

        assert result["id"] == drawing_id
        assert result["design_id"] == sample_design.id
        assert result["design_version"] == "1.0"
        assert result["drawing_type"] == "floor_plan"
        assert result["file_url"] == "https://storage.example.com/drawings/test.pdf"
        assert result["file_size"] == 1024
        assert result["mime_type"] == "application/pdf"
        assert result["scale"] == "1/4\"=1'"
        assert result["sheet_number"] == "A-101"
        assert result["metadata"]["level"] == "Ground Floor"
        assert result["metadata"]["revision"] == "A"
        assert result["file_name"] == "test.pdf"  # Extracted from URL
        assert result["thumbnail_url"] is None

    async def test_get_drawing_not_found(self, client: AsyncClient):
        """Test drawing retrieval with non-existent ID."""
        non_existent_id = str(uuid4())

        response = await client.get(f"/api/v1/drawings/{non_existent_id}")

        assert response.status_code == 404

    async def test_delete_drawing_success(
        self,
        client: AsyncClient,
        sample_design: Design,
        test_session: AsyncSession,
        auth_headers: dict,
    ):
        """Test successful drawing deletion."""
        drawing_id = str(uuid4())
        drawing = Drawing(
            id=drawing_id,
            design_id=sample_design.id,
            design_version="1.0",
            drawing_type="floor_plan",
            file_url="https://storage.example.com/drawings/test.pdf",
            file_size=1024,
            mime_type="application/pdf",
            created_by=str(uuid4()),
            created_at=datetime.utcnow(),
        )

        test_session.add(drawing)
        await test_session.commit()

        response = await client.delete(
            f"/api/v1/drawings/{drawing_id}",
            headers=auth_headers,
        )

        assert response.status_code == 204

        # Verify drawing is deleted from database
        from sqlalchemy import select

        result = await test_session.execute(
            select(Drawing).where(Drawing.id == drawing_id)
        )
        deleted_drawing = result.scalar_one_or_none()
        assert deleted_drawing is None

    async def test_delete_drawing_not_found(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test drawing deletion with non-existent ID."""
        non_existent_id = str(uuid4())

        response = await client.delete(
            f"/api/v1/drawings/{non_existent_id}",
            headers=auth_headers,
        )

        assert response.status_code == 404

    async def test_upload_drawing_large_file(
        self,
        client: AsyncClient,
        sample_design: Design,
        auth_headers: dict,
    ):
        """Test drawing upload with large file (should be rejected)."""
        # Create a large file (simulate file larger than allowed)
        large_content = b"x" * (100 * 1024 * 1024 + 1)  # 100MB + 1 byte
        large_file = io.BytesIO(large_content)

        files = {"file": ("large_drawing.pdf", large_file, "application/pdf")}
        data = {
            "drawing_type": "floor_plan",
        }

        response = await client.post(
            f"/api/v1/designs/{sample_design.id}/drawings",
            files=files,
            data=data,
            headers=auth_headers,
        )

        assert response.status_code == 400
        result = response.json()
        assert "file size" in result["error"].lower()

    async def test_upload_drawing_without_auth(
        self,
        client: AsyncClient,
        sample_design: Design,
        sample_pdf_file: io.BytesIO,
    ):
        """Test drawing upload without authentication."""
        files = {"file": ("test_drawing.pdf", sample_pdf_file, "application/pdf")}
        data = {
            "drawing_type": "floor_plan",
        }

        response = await client.post(
            f"/api/v1/designs/{sample_design.id}/drawings",
            files=files,
            data=data,
        )

        # Should still work with mock authentication
        assert response.status_code == 201

    async def test_upload_drawing_to_deleted_design(
        self,
        client: AsyncClient,
        test_session: AsyncSession,
        sample_pdf_file: io.BytesIO,
        auth_headers: dict,
    ):
        """Test drawing upload to a soft-deleted design."""
        # Create a deleted design
        design_id = str(uuid4())
        deleted_design = Design(
            id=design_id,
            project_id=str(uuid4()),
            name="Deleted Design",
            building_type="commercial",
            location_data={},
            current_version="1.0",
            version_number=1,
            status="draft",
            metadata={},
            created_by=str(uuid4()),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            is_deleted=True,  # Soft deleted
            deleted_at=datetime.utcnow(),
        )

        test_session.add(deleted_design)
        await test_session.commit()

        files = {"file": ("test_drawing.pdf", sample_pdf_file, "application/pdf")}
        data = {
            "drawing_type": "floor_plan",
        }

        response = await client.post(
            f"/api/v1/designs/{design_id}/drawings",
            files=files,
            data=data,
            headers=auth_headers,
        )

        assert response.status_code == 400
        result = response.json()
        assert "deleted design" in result["error"].lower()
