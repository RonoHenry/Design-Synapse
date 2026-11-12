"""Design schemas for request/response validation."""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import Field, field_validator, model_validator

from .base import BaseSchema, LocationData, PaginatedResponse, TimestampMixin
from .enums import BuildingType, DesignStatus


class CreateDesignRequest(BaseSchema):
    """Request schema for creating a new design document."""

    project_id: UUID = Field(
        ..., description="ID of the project this design belongs to"
    )
    name: str = Field(
        ..., description="Design document name", min_length=1, max_length=255
    )
    description: Optional[str] = Field(
        None, description="Design description", max_length=5000
    )
    building_type: BuildingType = Field(..., description="Type of building")
    location: LocationData = Field(..., description="Location information")
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata and custom fields"
    )

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate design name is not empty after stripping."""
        if not v.strip():
            raise ValueError("Design name cannot be empty or whitespace only")
        return v.strip()

    model_config = {
        "json_schema_extra": {
            "example": {
                "project_id": "550e8400-e29b-41d4-a716-446655440000",
                "name": "Downtown Office Building",
                "description": "10-story commercial office building with ground floor retail",
                "building_type": "commercial",
                "location": {
                    "address": "123 Main Street",
                    "city": "San Francisco",
                    "state": "California",
                    "country": "United States",
                    "postal_code": "94102",
                    "latitude": 37.7749,
                    "longitude": -122.4194,
                    "jurisdiction": "City and County of San Francisco",
                },
                "metadata": {
                    "floors": 10,
                    "total_area_sqft": 150000,
                    "parking_spaces": 50,
                },
            }
        }
    }


class UpdateDesignRequest(BaseSchema):
    """Request schema for updating a design document."""

    name: Optional[str] = Field(
        None, description="Design document name", min_length=1, max_length=255
    )
    description: Optional[str] = Field(
        None, description="Design description", max_length=5000
    )
    building_type: Optional[BuildingType] = Field(None, description="Type of building")
    location: Optional[LocationData] = Field(None, description="Location information")
    status: Optional[DesignStatus] = Field(None, description="Design status")
    metadata: Optional[Dict[str, Any]] = Field(
        None, description="Additional metadata and custom fields"
    )

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: Optional[str]) -> Optional[str]:
        """Validate design name is not empty after stripping."""
        if v is not None and not v.strip():
            raise ValueError("Design name cannot be empty or whitespace only")
        return v.strip() if v else v

    @model_validator(mode="after")
    def validate_at_least_one_field(self) -> "UpdateDesignRequest":
        """Ensure at least one field is provided for update."""
        if all(
            getattr(self, field) is None
            for field in [
                "name",
                "description",
                "building_type",
                "location",
                "status",
                "metadata",
            ]
        ):
            raise ValueError("At least one field must be provided for update")
        return self

    model_config = {
        "json_schema_extra": {
            "example": {
                "name": "Downtown Office Building - Revised",
                "description": "Updated design with client feedback incorporated",
                "status": "in_review",
                "metadata": {
                    "floors": 12,
                    "total_area_sqft": 180000,
                    "parking_spaces": 60,
                    "revision_notes": "Added 2 floors per client request",
                },
            }
        }
    }


class DesignResponse(BaseSchema, TimestampMixin):
    """Response schema for design document (summary)."""

    id: UUID = Field(..., description="Unique design identifier")
    project_id: UUID = Field(..., description="Associated project ID")
    name: str = Field(..., description="Design document name")
    building_type: BuildingType = Field(..., description="Type of building")
    current_version: str = Field(
        ..., description="Current version string (e.g., '1.0', '2.0')"
    )
    version_number: int = Field(
        ..., description="Numeric version for optimistic locking"
    )
    status: DesignStatus = Field(..., description="Design status")
    created_by: UUID = Field(..., description="User ID who created the design")

    model_config = {
        "json_schema_extra": {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "project_id": "660e8400-e29b-41d4-a716-446655440000",
                "name": "Downtown Office Building",
                "building_type": "commercial",
                "current_version": "2.0",
                "version_number": 2,
                "status": "in_review",
                "created_by": "770e8400-e29b-41d4-a716-446655440000",
                "created_at": "2024-01-15T10:00:00Z",
                "updated_at": "2024-01-16T14:30:00Z",
            }
        }
    }


class DesignDetailResponse(DesignResponse):
    """Response schema for design document (detailed)."""

    description: Optional[str] = Field(None, description="Design description")
    location: LocationData = Field(..., description="Location information")
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata and custom fields"
    )
    is_deleted: bool = Field(..., description="Soft delete flag")
    deleted_at: Optional[datetime] = Field(None, description="Soft delete timestamp")

    # Counts for related entities
    drawing_count: int = Field(
        default=0, description="Number of drawings associated with this design"
    )
    material_count: int = Field(
        default=0, description="Number of material specifications"
    )
    compliance_check_count: int = Field(
        default=0, description="Number of compliance checks performed"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "project_id": "660e8400-e29b-41d4-a716-446655440000",
                "name": "Downtown Office Building",
                "description": "10-story commercial office building with ground floor retail",
                "building_type": "commercial",
                "location": {
                    "address": "123 Main Street",
                    "city": "San Francisco",
                    "state": "California",
                    "country": "United States",
                    "postal_code": "94102",
                    "latitude": 37.7749,
                    "longitude": -122.4194,
                    "jurisdiction": "City and County of San Francisco",
                },
                "current_version": "2.0",
                "version_number": 2,
                "status": "in_review",
                "metadata": {
                    "floors": 10,
                    "total_area_sqft": 150000,
                    "parking_spaces": 50,
                },
                "is_deleted": False,
                "deleted_at": None,
                "drawing_count": 15,
                "material_count": 42,
                "compliance_check_count": 3,
                "created_by": "770e8400-e29b-41d4-a716-446655440000",
                "created_at": "2024-01-15T10:00:00Z",
                "updated_at": "2024-01-16T14:30:00Z",
            }
        }
    }


class DesignVersionResponse(BaseSchema):
    """Response schema for design version history."""

    id: UUID = Field(..., description="Version record ID")
    design_id: UUID = Field(..., description="Associated design ID")
    version: str = Field(..., description="Version string (e.g., '1.0', '2.0')")
    version_number: int = Field(..., description="Numeric version number")
    change_summary: Optional[str] = Field(
        None, description="Summary of changes in this version"
    )
    created_by: UUID = Field(..., description="User ID who created this version")
    created_at: datetime = Field(..., description="Version creation timestamp")

    model_config = {
        "json_schema_extra": {
            "example": {
                "id": "880e8400-e29b-41d4-a716-446655440000",
                "design_id": "550e8400-e29b-41d4-a716-446655440000",
                "version": "2.0",
                "version_number": 2,
                "change_summary": "Added 2 floors and updated parking requirements",
                "created_by": "770e8400-e29b-41d4-a716-446655440000",
                "created_at": "2024-01-16T14:30:00Z",
            }
        }
    }


class DesignVersionDetailResponse(DesignVersionResponse):
    """Response schema for design version with full snapshot data."""

    design_data: Dict[str, Any] = Field(
        ..., description="Complete snapshot of design data at this version"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "id": "880e8400-e29b-41d4-a716-446655440000",
                "design_id": "550e8400-e29b-41d4-a716-446655440000",
                "version": "2.0",
                "version_number": 2,
                "change_summary": "Added 2 floors and updated parking requirements",
                "design_data": {
                    "name": "Downtown Office Building",
                    "description": "12-story commercial office building",
                    "building_type": "commercial",
                    "location": {
                        "address": "123 Main Street",
                        "city": "San Francisco",
                        "state": "California",
                        "country": "United States",
                    },
                    "metadata": {
                        "floors": 12,
                        "total_area_sqft": 180000,
                        "parking_spaces": 60,
                    },
                },
                "created_by": "770e8400-e29b-41d4-a716-446655440000",
                "created_at": "2024-01-16T14:30:00Z",
            }
        }
    }


class DesignListResponse(PaginatedResponse):
    """Paginated response for design list."""

    items: List[DesignResponse] = Field(..., description="List of design documents")

    model_config = {
        "json_schema_extra": {
            "example": {
                "items": [
                    {
                        "id": "550e8400-e29b-41d4-a716-446655440000",
                        "project_id": "660e8400-e29b-41d4-a716-446655440000",
                        "name": "Downtown Office Building",
                        "building_type": "commercial",
                        "current_version": "2.0",
                        "version_number": 2,
                        "status": "in_review",
                        "created_by": "770e8400-e29b-41d4-a716-446655440000",
                        "created_at": "2024-01-15T10:00:00Z",
                        "updated_at": "2024-01-16T14:30:00Z",
                    }
                ],
                "has_next": True,
                "next_cursor": "eyJpZCI6IjU1MGU4NDAwLWUyOWItNDFkNC1hNzE2LTQ0NjY1NTQ0MDAwMCJ9",
                "total_count": 42,
                "page_info": {
                    "limit": 20,
                    "sort_field": "created_at",
                    "sort_direction": "desc",
                },
            }
        }
    }
