"""
Base schemas for Labor Services Marketplace API

Provides common response models and base classes for API schemas.
"""

from datetime import datetime
from typing import Any, Dict, Generic, List, Optional, TypeVar, Union

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


class BaseResponse(BaseModel):
    """Base response model for all API responses."""

    model_config = ConfigDict(json_encoders={datetime: lambda v: v.isoformat() + "Z"})

    success: bool = True
    message: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ErrorResponse(BaseResponse):
    """Error response model."""

    success: bool = False
    error_code: Optional[str] = None
    detail: Optional[str] = None
    errors: Optional[Dict[str, List[str]]] = None


class SuccessResponse(BaseResponse, Generic[T]):
    """Generic success response with data."""

    data: T


class PaginatedResponse(BaseResponse, Generic[T]):
    """Paginated response model."""

    items: List[T]
    total: int
    page: int = Field(ge=1)
    size: int = Field(ge=1, le=100)
    pages: int
    has_next: bool
    has_prev: bool

    def __init__(self, **data):
        # Calculate derived fields
        if "pages" not in data:
            data["pages"] = max(1, (data["total"] + data["size"] - 1) // data["size"])

        if "has_next" not in data:
            data["has_next"] = data["page"] < data["pages"]

        if "has_prev" not in data:
            data["has_prev"] = data["page"] > 1

        super().__init__(**data)


class LocationSchema(BaseModel):
    """Location schema for addresses and coordinates."""

    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    postal_code: Optional[str] = None
    country: str = "US"
    latitude: Optional[float] = Field(None, ge=-90, le=90)
    longitude: Optional[float] = Field(None, ge=-180, le=180)


class ContactInfoSchema(BaseModel):
    """Contact information schema."""

    email: Optional[str] = Field(None, pattern=r"^[^@]+@[^@]+\.[^@]+$")
    phone: Optional[str] = None
    website: Optional[str] = None


class TimestampMixin(BaseModel):
    """Mixin for models with timestamps."""

    model_config = ConfigDict(json_encoders={datetime: lambda v: v.isoformat() + "Z"})

    created_at: datetime
    updated_at: datetime


class IDMixin(BaseModel):
    """Mixin for models with ID."""

    id: int = Field(..., gt=0)


class StatusMixin(BaseModel):
    """Mixin for models with status."""

    status: str
    is_active: bool = True


class RatingMixin(BaseModel):
    """Mixin for models with ratings."""

    rating: Optional[float] = Field(None, ge=1, le=5)
    total_reviews: int = Field(0, ge=0)


class PricingMixin(BaseModel):
    """Mixin for models with pricing information."""

    currency: str = "USD"
    labor_cost: Optional[float] = Field(None, ge=0)
    material_cost: Optional[float] = Field(None, ge=0)
    travel_cost: Optional[float] = Field(None, ge=0)
    total_cost: Optional[float] = Field(None, ge=0)


class SearchFilters(BaseModel):
    """Base search filters."""

    q: Optional[str] = Field(None, max_length=100, description="Search query")
    location: Optional[str] = Field(None, max_length=100, description="Location filter")
    radius: Optional[float] = Field(
        None, ge=0, le=500, description="Search radius in miles"
    )
    min_rating: Optional[float] = Field(None, ge=1, le=5, description="Minimum rating")
    max_price: Optional[float] = Field(None, ge=0, description="Maximum price")
    sort_by: str = Field("created_at", description="Sort field")
    sort_order: str = Field("desc", pattern="^(asc|desc)$", description="Sort order")


class PaginationParams(BaseModel):
    """Pagination parameters."""

    page: int = Field(1, ge=1, description="Page number")
    size: int = Field(10, ge=1, le=100, description="Page size")


class AnalyticsResponse(BaseModel):
    """Base analytics response."""

    period: str
    total_count: int = 0
    growth_rate: Optional[float] = None
    metrics: Dict[str, Union[int, float, str]] = {}


class HealthCheckResponse(BaseModel):
    """Health check response."""

    model_config = ConfigDict(json_encoders={datetime: lambda v: v.isoformat() + "Z"})

    status: str = "healthy"
    version: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    checks: Dict[str, str] = {}


class ValidationErrorDetail(BaseModel):
    """Validation error detail."""

    field: str
    message: str
    value: Any = None


class APIKeyInfo(BaseModel):
    """API key information."""

    model_config = ConfigDict(
        json_encoders={datetime: lambda v: v.isoformat() + "Z" if v else None}
    )

    key_id: str
    name: str
    permissions: List[str]
    expires_at: Optional[datetime] = None
    last_used: Optional[datetime] = None


# Common response types
MessageResponse = SuccessResponse[Dict[str, str]]
IDResponse = SuccessResponse[Dict[str, int]]
StatusResponse = SuccessResponse[Dict[str, str]]
