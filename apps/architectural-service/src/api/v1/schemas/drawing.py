"""Drawing schemas for API requests and responses."""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import Field, field_validator

from .base import BaseSchema
from .enums import DrawingType


class DrawingUploadRequest(BaseSchema):
    """Request schema for uploading a drawing (multipart form data)."""

    drawing_type: DrawingType = Field(..., description="Type of architectural drawing")
    scale: Optional[str] = Field(
        None, description="Drawing scale (e.g., '1/4\"=1\\'', '1:100')", max_length=50
    )
    sheet_number: Optional[str] = Field(
        None, description="Sheet number in drawing set", max_length=50
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional drawing metadata"
    )

    @field_validator("metadata")
    @classmethod
    def validate_metadata(cls, v: Dict[str, Any]) -> Dict[str, Any]:
        """Validate metadata is a valid dictionary."""
        if not isinstance(v, dict):
            raise ValueError("Metadata must be a dictionary")
        return v

    model_config = {
        "json_schema_extra": {
            "example": {
                "drawing_type": "floor_plan",
                "scale": "1/4\"=1'",
                "sheet_number": "A-101",
                "metadata": {
                    "level": "Ground Floor",
                    "revision": "A",
                    "date": "2024-01-15",
                },
            }
        }
    }


class DrawingResponse(BaseSchema):
    """Response schema for drawing."""

    id: UUID = Field(..., description="Drawing ID")
    design_id: UUID = Field(..., description="Associated design ID")
    design_version: str = Field(
        ..., description="Design version when drawing was added"
    )
    drawing_type: DrawingType = Field(..., description="Type of architectural drawing")
    file_url: str = Field(..., description="URL to access the drawing file")
    file_size: int = Field(..., description="File size in bytes", ge=0)
    mime_type: str = Field(..., description="MIME type of the file")
    scale: Optional[str] = Field(None, description="Drawing scale")
    sheet_number: Optional[str] = Field(None, description="Sheet number in drawing set")
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional drawing metadata"
    )
    created_by: UUID = Field(..., description="User ID who uploaded the drawing")
    created_at: datetime = Field(..., description="Upload timestamp")

    model_config = {
        "json_schema_extra": {
            "example": {
                "id": "990e8400-e29b-41d4-a716-446655440000",
                "design_id": "550e8400-e29b-41d4-a716-446655440000",
                "design_version": "1.0",
                "drawing_type": "floor_plan",
                "file_url": "https://storage.example.com/drawings/990e8400.pdf",
                "file_size": 2048576,
                "mime_type": "application/pdf",
                "scale": "1/4\"=1'",
                "sheet_number": "A-101",
                "metadata": {"level": "Ground Floor", "revision": "A"},
                "created_by": "770e8400-e29b-41d4-a716-446655440000",
                "created_at": "2024-01-15T10:30:00Z",
            }
        }
    }


class DrawingDetailResponse(DrawingResponse):
    """Detailed response schema for drawing with additional information."""

    file_name: Optional[str] = Field(None, description="Original file name")
    thumbnail_url: Optional[str] = Field(None, description="URL to thumbnail preview")


class DrawingListResponse(BaseSchema):
    """Response schema for list of drawings."""

    drawings: List[DrawingResponse] = Field(..., description="List of drawings")
    total: int = Field(..., description="Total number of drawings")


class FileValidationError(BaseSchema):
    """File validation error details."""

    field: str = Field(..., description="Field that failed validation")
    message: str = Field(..., description="Error message")
    code: str = Field(..., description="Error code")


# File upload validation constants
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100 MB
ALLOWED_MIME_TYPES = {
    "application/pdf",
    "image/png",
    "image/jpeg",
    "image/tiff",
    "application/vnd.ms-excel",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/dwg",
    "application/dxf",
    "image/vnd.dwg",
    "image/vnd.dxf",
}


def validate_file_upload(
    file_size: int, mime_type: str, file_name: str
) -> Optional[FileValidationError]:
    """
    Validate file upload parameters.

    Args:
        file_size: Size of the file in bytes
        mime_type: MIME type of the file
        file_name: Name of the file

    Returns:
        FileValidationError if validation fails, None otherwise
    """
    # Check file size
    if file_size > MAX_FILE_SIZE:
        return FileValidationError(
            field="file",
            message=f"File size exceeds maximum allowed size of {MAX_FILE_SIZE} bytes",
            code="file_too_large",
        )

    if file_size <= 0:
        return FileValidationError(
            field="file", message="File size must be greater than 0", code="empty_file"
        )

    # Check MIME type
    if mime_type not in ALLOWED_MIME_TYPES:
        return FileValidationError(
            field="file",
            message=f"File type '{mime_type}' is not allowed. "
            f"Allowed types: {', '.join(ALLOWED_MIME_TYPES)}",
            code="invalid_file_type",
        )

    # Check file extension matches MIME type
    extension = file_name.lower().split(".")[-1] if "." in file_name else ""
    mime_extension_map = {
        "application/pdf": ["pdf"],
        "image/png": ["png"],
        "image/jpeg": ["jpg", "jpeg"],
        "image/tiff": ["tif", "tiff"],
        "application/vnd.ms-excel": ["xls"],
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": ["xlsx"],
        "application/dwg": ["dwg"],
        "application/dxf": ["dxf"],
        "image/vnd.dwg": ["dwg"],
        "image/vnd.dxf": ["dxf"],
    }

    expected_extensions = mime_extension_map.get(mime_type, [])
    if expected_extensions and extension not in expected_extensions:
        return FileValidationError(
            field="file",
            message=f"File extension '{extension}' does not match MIME type '{mime_type}'",
            code="extension_mismatch",
        )

    return None
