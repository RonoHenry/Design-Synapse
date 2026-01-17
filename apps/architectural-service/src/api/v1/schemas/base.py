"""Base schemas for API requests and responses."""

from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class BaseSchema(BaseModel):
    """Base schema with common configuration."""

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        use_enum_values=True,
        str_strip_whitespace=True,
        validate_assignment=True,
    )


class TimestampMixin(BaseModel):
    """Mixin for timestamp fields."""

    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")


class LocationData(BaseModel):
    """Location information for designs."""

    address: Optional[str] = Field(None, description="Street address", max_length=500)
    city: Optional[str] = Field(None, description="City name", max_length=100)
    state: Optional[str] = Field(None, description="State or province", max_length=100)
    country: str = Field(..., description="Country name", max_length=100)
    postal_code: Optional[str] = Field(
        None, description="Postal or ZIP code", max_length=20
    )
    latitude: Optional[float] = Field(
        None, description="Latitude coordinate", ge=-90, le=90
    )
    longitude: Optional[float] = Field(
        None, description="Longitude coordinate", ge=-180, le=180
    )
    jurisdiction: Optional[str] = Field(
        None, description="Local jurisdiction or municipality", max_length=200
    )

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "address": "123 Main Street",
                "city": "San Francisco",
                "state": "California",
                "country": "United States",
                "postal_code": "94102",
                "latitude": 37.7749,
                "longitude": -122.4194,
                "jurisdiction": "City and County of San Francisco",
            }
        },
    )


class PaginationParams(BaseModel):
    """Pagination parameters for list endpoints."""

    cursor: Optional[str] = Field(None, description="Cursor for pagination")
    limit: int = Field(20, description="Number of items per page", ge=1, le=100)


class PaginatedResponse(BaseModel):
    """Paginated response wrapper."""

    items: list = Field(..., description="List of items")
    next_cursor: Optional[str] = Field(None, description="Cursor for next page")
    has_more: bool = Field(..., description="Whether more items are available")
    total: Optional[int] = Field(None, description="Total count (if available)")


class ErrorDetail(BaseModel):
    """Error detail information."""

    field: Optional[str] = Field(None, description="Field name that caused the error")
    message: str = Field(..., description="Error message")
    code: Optional[str] = Field(None, description="Error code")


class ErrorResponse(BaseModel):
    """Standard error response format."""

    error: Dict[str, Any] = Field(..., description="Error information")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "Invalid input data",
                    "details": [
                        {
                            "field": "name",
                            "message": "Field required",
                            "code": "required",
                        }
                    ],
                    "timestamp": "2024-01-15T10:30:00Z",
                    "request_id": "550e8400-e29b-41d4-a716-446655440000",
                }
            }
        }
    )
