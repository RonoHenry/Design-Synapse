"""Property-based tests for DrawingService."""

from datetime import datetime
from io import BytesIO
from unittest.mock import AsyncMock
from uuid import UUID, uuid4

import pytest
from hypothesis import given
from hypothesis import strategies as st
from src.api.v1.schemas.drawing import DrawingUploadRequest
from src.api.v1.schemas.enums import DrawingType
from src.models.design import Design
from src.models.drawing import Drawing
from src.repositories.design_repository import DesignRepository
from src.repositories.drawing_repository import DrawingRepository
from src.services.drawing_service import DrawingService


class TestDrawingServiceProperties:
    """Property-based tests for DrawingService."""

    @pytest.mark.asyncio
    @given(
        design_id=st.uuids(),
        user_id=st.uuids(),
        drawing_type=st.sampled_from(DrawingType),
    )
    async def test_property_5_drawing_type_support(
        self,
        design_id: UUID,
        user_id: UUID,
        drawing_type: DrawingType,
    ):
        """
        Property 5: Drawing type support.

        For any valid drawing type (floor_plan, elevation, section, site_plan,
        detail), creating a drawing of that type should succeed and be
        retrievable.

        Validates: Requirements 1.5
        """
        # Setup mocks
        mock_drawing_repo = AsyncMock(spec=DrawingRepository)
        mock_design_repo = AsyncMock(spec=DesignRepository)

        # Create existing design
        design = Design(
            id=str(design_id),
            project_id=str(uuid4()),
            name="Test Design",
            description="Test",
            building_type="commercial",
            location_data={},
            current_version="1.0",
            version_number=1,
            status="draft",
            metadata={},
            created_by=str(user_id),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            is_deleted=False,
        )

        mock_design_repo.get.return_value = design

        # Mock drawing creation
        def create_side_effect(drawing):
            drawing.id = str(uuid4())
            return drawing

        mock_drawing_repo.create.side_effect = create_side_effect

        service = DrawingService(
            mock_drawing_repo,
            mock_design_repo,
            storage_base_url="https://storage.example.com/drawings",
        )

        # Create drawing upload request
        upload_request = DrawingUploadRequest(
            drawing_type=drawing_type,
            scale="1/4\"=1'",
            sheet_number="A-101",
            metadata={"test": "data"},
        )

        # Create file content
        file_content = BytesIO(b"test file content")
        file_name = f"test_drawing.pdf"
        file_size = 1024
        mime_type = "application/pdf"

        # Execute
        drawing = await service.upload_drawing(
            design_id=design_id,
            user_id=user_id,
            file_content=file_content,
            file_name=file_name,
            file_size=file_size,
            mime_type=mime_type,
            data=upload_request,
        )

        # Verify Property 5: Drawing type support
        # Handle both enum and string values
        expected_drawing_type = (
            drawing_type.value if hasattr(drawing_type, "value") else drawing_type
        )

        assert drawing.id is not None, "Drawing must have unique identifier"
        assert (
            drawing.drawing_type == expected_drawing_type
        ), f"Drawing type must be {expected_drawing_type}"
        assert drawing.design_id == str(
            design_id
        ), "Drawing must be associated with design"
        assert drawing.file_url is not None, "Drawing must have file URL"
        assert drawing.file_size == file_size, "File size must match uploaded size"
        assert drawing.mime_type == mime_type, "MIME type must match uploaded type"
        assert drawing.created_by == str(user_id), "created_by must match user_id"
        assert drawing.created_at is not None, "created_at must be populated"

        # Verify drawing can be retrieved
        mock_drawing_repo.get.return_value = drawing
        retrieved_drawing = await service.get_drawing(UUID(drawing.id))

        assert (
            retrieved_drawing.id == drawing.id
        ), "Retrieved drawing must match created drawing"
        assert (
            retrieved_drawing.drawing_type == expected_drawing_type
        ), "Retrieved drawing type must match"
