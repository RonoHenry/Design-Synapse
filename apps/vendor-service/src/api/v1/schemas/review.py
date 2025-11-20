"""Review API schemas."""

from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel, Field, validator


class ReviewBase(BaseModel):
    """Base review schema."""

    rating: int = Field(..., ge=1, le=5)
    comment: Optional[str] = Field(None, max_length=1000)

    @validator("comment")
    def validate_comment(cls, v):
        """Validate comment content."""
        if v is not None:
            v = v.strip()
            if len(v) == 0:
                return None
        return v


class ReviewCreate(ReviewBase):
    """Schema for creating a review."""

    product_id: int = Field(..., gt=0)


class ReviewUpdate(BaseModel):
    """Schema for updating a review."""

    rating: Optional[int] = Field(None, ge=1, le=5)
    comment: Optional[str] = Field(None, max_length=1000)

    @validator("comment")
    def validate_comment(cls, v):
        """Validate comment content."""
        if v is not None:
            v = v.strip()
            if len(v) == 0:
                return None
        return v


class ReviewResponse(ReviewBase):
    """Schema for review response."""

    id: int
    user_id: int
    product_id: int
    vendor_id: int
    verified_purchase: bool
    created_at: datetime

    class Config:
        from_attributes = True


class ReviewListResponse(BaseModel):
    """Schema for review list response."""

    reviews: List[ReviewResponse]
    total: int
    skip: int
    limit: int


class ReviewSearch(BaseModel):
    """Schema for review search parameters."""

    product_id: Optional[int] = None
    vendor_id: Optional[int] = None
    user_id: Optional[int] = None
    min_rating: Optional[int] = Field(None, ge=1, le=5)
    max_rating: Optional[int] = Field(None, ge=1, le=5)
    verified_only: bool = False
    skip: int = Field(0, ge=0)
    limit: int = Field(100, ge=1, le=1000)

    @validator("max_rating")
    def validate_rating_range(cls, v, values):
        """Validate rating range."""
        if (
            v is not None
            and "min_rating" in values
            and values["min_rating"] is not None
        ):
            if v < values["min_rating"]:
                raise ValueError(
                    "max_rating must be greater than or equal to min_rating"
                )
        return v


class RatingSummary(BaseModel):
    """Schema for rating summary."""

    average_rating: Optional[float]
    total_reviews: int
    rating_distribution: Dict[str, int]  # {"1": count, "2": count, ...}


class ProductRatingSummary(RatingSummary):
    """Schema for product rating summary."""

    product_id: int


class VendorRatingSummary(RatingSummary):
    """Schema for vendor rating summary."""

    vendor_id: int


class ReviewModeration(BaseModel):
    """Schema for review moderation."""

    action: str = Field(..., pattern="^(approve|hide|flag)$")
    reason: Optional[str] = Field(None, max_length=500)


class TopRatedItem(BaseModel):
    """Schema for top-rated items."""

    id: int
    name: str
    average_rating: float
    total_reviews: int


class TopRatedProductsResponse(BaseModel):
    """Schema for top-rated products response."""

    products: List[TopRatedItem]
    limit: int
    min_reviews: int


class TopRatedVendorsResponse(BaseModel):
    """Schema for top-rated vendors response."""

    vendors: List[TopRatedItem]
    limit: int
    min_reviews: int
