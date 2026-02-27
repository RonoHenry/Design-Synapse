"""Drawing management API endpoints."""

import logging
from typing import List, Optional
from uuid import UUID

from fastapi import (APIRouter, Depends, File, Form, HTTPException, Query,
                     UploadFile, status)
from sqlalchemy.ext.asyncio import AsyncSession
from src.api.v1.dependencies import require_authentication
from src.api.v1.schemas.drawing import (DrawingDetailResponse,
                                        DrawingListResponse, DrawingResponse,
                                        DrawingUploadRequest)
from src.api.v1.schemas.enums import DrawingType
from src.core.database import get_db
from src.core.exceptions import (ArchitecturalServiceException, NotFoundError,
                                 ValidationError)
from src.repositories.design_repository import DesignRepository
from src.repositories.drawing_repository import DrawingRepository
from src.services.drawing_service import DrawingService

logger = logging.getLogger(__name__)

router = APIRouter()


# Dependency to get drawing service
async def get_drawing_service(
    db: AsyncSession = Depends(get_db),
) -> DrawingService:
    """Get drawing service instance."""
    drawing_repository = DrawingRepository(db)
    design_repository = DesignRepository(db)
    return DrawingService(drawing_repository, design_repository)


@router.post(
    "/designs/{design_id}/drawings",
    response_model=DrawingResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a drawing",
    description="Upload an architectural drawing file to a design document",
)
async def upload_drawing(
    design_id: UUID,
    file: UploadFile = File(..., description="Drawing file to upload"),
    drawing_type: DrawingType = Form(..., description="Type of architectural drawing"),
    scale: Optional[str] = Form(None, description="Drawing scale"),
    sheet_number: Optional[str] = Form(None, description="Sheet number"),
    metadata: Optional[str] = Form(
        None, description="Additional metadata as JSON string"
    ),
    user_id: UUID = Depends(require_authentication),
    drawing_service: DrawingService = Depends(get_drawing_service),
) -> DrawingResponse:
    """
    Upload an architectural drawing.

    Validates file type and size, stores the file, and creates a drawing record.
    """
    try:
        # Parse metadata if provided
        import json

        parsed_metadata = {}
        if metadata:
            try:
                parsed_metadata = json.loads(metadata)
            except json.JSONDecodeError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={"error": "Invalid JSON in metadata field"},
                )

        # Create upload request
        upload_request = DrawingUploadRequest(
            drawing_type=drawing_type,
            scale=scale,
            sheet_number=sheet_number,
            metadata=parsed_metadata,
        )

        # Upload drawing
        drawing = await drawing_service.upload_drawing(
            design_id=design_id,
            user_id=user_id,
            file_content=file.file,
            file_name=file.filename or "unknown",
            file_size=file.size or 0,
            mime_type=file.content_type or "application/octet-stream",
            data=upload_request,
        )

        return DrawingResponse(
            id=UUID(drawing.id),
            design_id=UUID(drawing.design_id),
            design_version=drawing.design_version,
            drawing_type=drawing.drawing_type,
            file_url=drawing.file_url,
            file_size=drawing.file_size,
            mime_type=drawing.mime_type,
            scale=drawing.scale,
            sheet_number=drawing.sheet_number,
            metadata=drawing.metadata,
            created_by=UUID(drawing.created_by),
            created_at=drawing.created_at,
        )

    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": e.message, "details": e.details},
        )
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": e.message, "details": e.details},
        )
    except ArchitecturalServiceException as e:
        raise HTTPException(
            status_code=e.status_code,
            detail={"error": e.message, "details": e.details},
        )
    except Exception as e:
        logger.error(f"Unexpected error uploading drawing: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "Internal server error"},
        )


@router.get(
    "/designs/{design_id}/drawings",
    response_model=DrawingListResponse,
    summary="List drawings for a design",
    description="List all drawings associated with a design document",
)
async def list_drawings(
    design_id: UUID,
    drawing_type: Optional[DrawingType] = Query(
        None, description="Filter by drawing type"
    ),
    drawing_service: DrawingService = Depends(get_drawing_service),
) -> DrawingListResponse:
    """
    List all drawings for a design document.

    Optionally filter by drawing type.
    """
    try:
        # Convert enum to string if provided
        drawing_type_str = drawing_type.value if drawing_type else None

        drawings = await drawing_service.list_drawings(
            design_id=design_id,
            drawing_type=drawing_type_str,
        )

        drawing_responses = [
            DrawingResponse(
                id=UUID(drawing.id),
                design_id=UUID(drawing.design_id),
                design_version=drawing.design_version,
                drawing_type=drawing.drawing_type,
                file_url=drawing.file_url,
                file_size=drawing.file_size,
                mime_type=drawing.mime_type,
                scale=drawing.scale,
                sheet_number=drawing.sheet_number,
                metadata=drawing.metadata,
                created_by=UUID(drawing.created_by),
                created_at=drawing.created_at,
            )
            for drawing in drawings
        ]

        return DrawingListResponse(
            drawings=drawing_responses,
            total=len(drawing_responses),
        )

    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": e.message, "details": e.details},
        )
    except ArchitecturalServiceException as e:
        raise HTTPException(
            status_code=e.status_code,
            detail={"error": e.message, "details": e.details},
        )
    except Exception as e:
        logger.error(f"Unexpected error listing drawings for design {design_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "Internal server error"},
        )


@router.get(
    "/drawings/{drawing_id}",
    response_model=DrawingDetailResponse,
    summary="Get a drawing",
    description="Retrieve a specific drawing with detailed information",
)
async def get_drawing(
    drawing_id: UUID,
    drawing_service: DrawingService = Depends(get_drawing_service),
) -> DrawingDetailResponse:
    """
    Retrieve a specific drawing.

    Returns detailed drawing information including file metadata.
    """
    try:
        drawing = await drawing_service.get_drawing(drawing_id)

        # Extract file name from URL (simplified)
        file_name = drawing.file_url.split("/")[-1] if drawing.file_url else None

        return DrawingDetailResponse(
            id=UUID(drawing.id),
            design_id=UUID(drawing.design_id),
            design_version=drawing.design_version,
            drawing_type=drawing.drawing_type,
            file_url=drawing.file_url,
            file_size=drawing.file_size,
            mime_type=drawing.mime_type,
            scale=drawing.scale,
            sheet_number=drawing.sheet_number,
            metadata=drawing.metadata,
            created_by=UUID(drawing.created_by),
            created_at=drawing.created_at,
            file_name=file_name,
            thumbnail_url=None,  # TODO: Generate thumbnail URL
        )

    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": e.message, "details": e.details},
        )
    except ArchitecturalServiceException as e:
        raise HTTPException(
            status_code=e.status_code,
            detail={"error": e.message, "details": e.details},
        )
    except Exception as e:
        logger.error(f"Unexpected error retrieving drawing {drawing_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "Internal server error"},
        )


@router.delete(
    "/drawings/{drawing_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a drawing",
    description="Delete a drawing and its associated file",
)
async def delete_drawing(
    drawing_id: UUID,
    user_id: UUID = Depends(require_authentication),
    drawing_service: DrawingService = Depends(get_drawing_service),
) -> None:
    """
    Delete a drawing.

    Removes the drawing record and associated file from storage.
    """
    try:
        await drawing_service.delete_drawing(drawing_id, user_id)

    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": e.message, "details": e.details},
        )
    except ArchitecturalServiceException as e:
        raise HTTPException(
            status_code=e.status_code,
            detail={"error": e.message, "details": e.details},
        )
    except Exception as e:
        logger.error(f"Unexpected error deleting drawing {drawing_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "Internal server error"},
        )
