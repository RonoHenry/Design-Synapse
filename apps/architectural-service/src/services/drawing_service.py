"""Drawing service for architectural drawing management."""

import logging
from datetime import datetime
from typing import BinaryIO, Optional
from uuid import UUID, uuid4

from src.api.v1.schemas.drawing import (DrawingUploadRequest,
                                        validate_file_upload)
from src.core.exceptions import NotFoundError, ValidationError
from src.models.drawing import Drawing
from src.repositories.design_repository import DesignRepository
from src.repositories.drawing_repository import DrawingRepository

logger = logging.getLogger(__name__)


class DrawingService:
    """
    Service for managing architectural drawings.

    Handles drawing uploads, file validation, storage integration,
    and drawing retrieval operations.
    """

    def __init__(
        self,
        drawing_repository: DrawingRepository,
        design_repository: DesignRepository,
        storage_base_url: str = "https://storage.example.com/drawings",
    ):
        """
        Initialize DrawingService.

        Args:
            drawing_repository: Repository for drawing data access
            design_repository: Repository for design data access
            storage_base_url: Base URL for file storage
        """
        self.drawing_repository = drawing_repository
        self.design_repository = design_repository
        self.storage_base_url = storage_base_url

    async def upload_drawing(
        self,
        design_id: UUID,
        user_id: UUID,
        file_content: BinaryIO,
        file_name: str,
        file_size: int,
        mime_type: str,
        data: DrawingUploadRequest,
    ) -> Drawing:
        """
        Upload an architectural drawing.

        Validates file, stores it, and creates drawing record.

        Args:
            design_id: Design ID to associate drawing with
            user_id: User ID uploading the drawing
            file_content: File content as binary stream
            file_name: Original file name
            file_size: File size in bytes
            mime_type: MIME type of the file
            data: Drawing upload request data

        Returns:
            Created Drawing instance

        Raises:
            NotFoundError: If design doesn't exist
            ValidationError: If file validation fails
        """
        # Verify design exists
        design = await self.design_repository.get(str(design_id))
        if design is None:
            raise NotFoundError(
                f"Design {design_id} not found", details={"design_id": str(design_id)}
            )

        # Check if design is deleted
        if design.is_deleted:
            raise ValidationError(
                f"Cannot upload drawing to deleted design {design_id}",
                details={"design_id": str(design_id)},
            )

        # Validate file
        validation_error = validate_file_upload(
            file_size=file_size,
            mime_type=mime_type,
            file_name=file_name,
        )

        if validation_error is not None:
            raise ValidationError(
                validation_error.message,
                details={
                    "field": validation_error.field,
                    "code": validation_error.code,
                },
            )

        # Generate drawing ID
        drawing_id = str(uuid4())

        # Store file (simplified - in production would use actual storage service)
        # For now, just generate a URL
        file_url = f"{self.storage_base_url}/{drawing_id}/{file_name}"

        # Create drawing record
        # Handle both enum and string values for drawing_type
        drawing_type_value = (
            data.drawing_type.value
            if hasattr(data.drawing_type, "value")
            else data.drawing_type
        )

        # Save drawing
        drawing = await self.drawing_repository.create(
            id=drawing_id,
            design_id=str(design_id),
            design_version=design.current_version,
            drawing_type=drawing_type_value,
            file_url=file_url,
            file_size=file_size,
            mime_type=mime_type,
            scale=data.scale,
            sheet_number=data.sheet_number,
            metadata=data.metadata,
            created_by=str(user_id),
            created_at=datetime.utcnow(),
        )

        logger.info(
            f"Uploaded drawing {drawing.id} for design {design_id} "
            f"by user {user_id}"
        )

        return drawing

    async def list_drawings(
        self,
        design_id: UUID,
        drawing_type: Optional[str] = None,
    ) -> list[Drawing]:
        """
        List all drawings for a design.

        Args:
            design_id: Design ID to list drawings for
            drawing_type: Optional filter by drawing type

        Returns:
            List of Drawing instances

        Raises:
            NotFoundError: If design doesn't exist
        """
        # Verify design exists
        design = await self.design_repository.get(str(design_id))
        if design is None:
            raise NotFoundError(
                f"Design {design_id} not found", details={"design_id": str(design_id)}
            )

        # Get drawings
        drawings = await self.drawing_repository.list_by_design(
            str(design_id), drawing_type
        )

        return drawings

    async def get_drawing(
        self,
        drawing_id: UUID,
    ) -> Drawing:
        """
        Retrieve a specific drawing.

        Args:
            drawing_id: Drawing ID to retrieve

        Returns:
            Drawing instance

        Raises:
            NotFoundError: If drawing doesn't exist
        """
        drawing = await self.drawing_repository.get(str(drawing_id))
        if drawing is None:
            raise NotFoundError(
                f"Drawing {drawing_id} not found",
                details={"drawing_id": str(drawing_id)},
            )

        return drawing

    async def delete_drawing(
        self,
        drawing_id: UUID,
        user_id: UUID,
    ) -> None:
        """
        Delete a drawing.

        Removes drawing record and associated file from storage.

        Args:
            drawing_id: Drawing ID to delete
            user_id: User ID performing the deletion

        Raises:
            NotFoundError: If drawing doesn't exist
        """
        # Verify drawing exists
        drawing = await self.drawing_repository.get(str(drawing_id))
        if drawing is None:
            raise NotFoundError(
                f"Drawing {drawing_id} not found",
                details={"drawing_id": str(drawing_id)},
            )

        # Delete from storage (simplified - would use actual storage service)
        # In production, would call storage service to delete file

        # Delete drawing record
        await self.drawing_repository.delete(str(drawing_id))

        logger.info(f"Deleted drawing {drawing_id} by user {user_id}")
