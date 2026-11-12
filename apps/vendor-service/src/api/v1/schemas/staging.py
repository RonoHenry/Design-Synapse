"""Staging and bookmark API schemas."""

from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel, Field, validator


class BookmarkBase(BaseModel):
    """Base bookmark schema."""

    product_id: int = Field(..., gt=0)
    notes: Optional[str] = Field(None, max_length=500)

    @validator("notes")
    def validate_notes(cls, v):
        """Validate notes content."""
        if v is not None:
            v = v.strip()
            if len(v) == 0:
                return None
        return v


class BookmarkCreate(BookmarkBase):
    """Schema for creating a bookmark."""

    pass


class BookmarkUpdate(BaseModel):
    """Schema for updating a bookmark."""

    notes: Optional[str] = Field(None, max_length=500)

    @validator("notes")
    def validate_notes(cls, v):
        """Validate notes content."""
        if v is not None:
            v = v.strip()
            if len(v) == 0:
                return None
        return v


class BookmarkResponse(BookmarkBase):
    """Schema for bookmark response."""

    id: int
    user_id: int
    created_at: datetime

    class Config:
        from_attributes = True


class BookmarkListResponse(BaseModel):
    """Schema for bookmark list response."""

    bookmarks: List[BookmarkResponse]
    total: int
    skip: int
    limit: int


class Position3D(BaseModel):
    """Schema for 3D position."""

    x: float
    y: float
    z: float


class Rotation3D(BaseModel):
    """Schema for 3D rotation."""

    x: float = Field(0.0, ge=-360, le=360)
    y: float = Field(0.0, ge=-360, le=360)
    z: float = Field(0.0, ge=-360, le=360)


class Scale3D(BaseModel):
    """Schema for 3D scale."""

    x: float = Field(1.0, gt=0)
    y: float = Field(1.0, gt=0)
    z: float = Field(1.0, gt=0)


class StagingBase(BaseModel):
    """Base staging schema."""

    product_id: int = Field(..., gt=0)
    position: Position3D
    rotation: Optional[Rotation3D] = None
    scale: Optional[Scale3D] = None
    quantity: int = Field(1, gt=0)


class StagingCreate(StagingBase):
    """Schema for creating a staging."""

    design_id: int = Field(..., gt=0)


class StagingUpdate(BaseModel):
    """Schema for updating a staging."""

    position: Optional[Position3D] = None
    rotation: Optional[Rotation3D] = None
    scale: Optional[Scale3D] = None
    quantity: Optional[int] = Field(None, gt=0)


class StagingResponse(StagingBase):
    """Schema for staging response."""

    id: int
    design_id: int
    created_at: datetime

    class Config:
        from_attributes = True


class StagingListResponse(BaseModel):
    """Schema for staging list response."""

    stagings: List[StagingResponse]
    total: int
    skip: int
    limit: int


class ProcurementItem(BaseModel):
    """Schema for procurement list item."""

    product_id: int
    product_name: str
    vendor_id: int
    vendor_name: str
    quantity: int
    unit_price: float
    total_cost: float
    availability: bool


class VendorProcurement(BaseModel):
    """Schema for vendor-specific procurement."""

    vendor_id: int
    vendor_name: str
    products: List[ProcurementItem]
    vendor_total: float


class ProcurementSummary(BaseModel):
    """Schema for procurement summary."""

    total_cost: float
    total_items: int
    total_quantity: int
    vendor_count: int


class ProcurementListResponse(BaseModel):
    """Schema for procurement list response."""

    design_id: int
    summary: ProcurementSummary
    vendors: List[VendorProcurement]
    items: List[ProcurementItem]


class AvailabilityIssue(BaseModel):
    """Schema for availability issue."""

    product_id: int
    product_name: Optional[str] = None
    issue: str
    requested_quantity: int
    available_quantity: Optional[int] = None


class AvailabilityCheck(BaseModel):
    """Schema for availability check response."""

    design_id: int
    total_products: int
    available_products: int
    availability_rate: float
    issues: List[AvailabilityIssue]
    all_available: bool


class PopularProduct(BaseModel):
    """Schema for popular product."""

    product_id: int
    product_name: str
    bookmark_count: Optional[int] = None
    staging_count: Optional[int] = None
    category: Optional[str] = None


class PopularProductsResponse(BaseModel):
    """Schema for popular products response."""

    products: List[PopularProduct]
    limit: int
    category: Optional[str] = None


class ProductValidation(BaseModel):
    """Schema for product staging validation."""

    valid: bool
    issues: List[str]
    product_info: Optional[Dict] = None


class Product3DInfo(BaseModel):
    """Schema for 3D product information."""

    id: int
    name: str
    has_3d_model: bool
    dimensions: Optional[Dict] = None
    model_format: Optional[str] = None
    model_url: Optional[str] = None


class Products3DResponse(BaseModel):
    """Schema for 3D products response."""

    products: List[Product3DInfo]
    total: int
    skip: int
    limit: int
