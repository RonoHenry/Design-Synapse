"""
Review API Schemas
"""
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator
from src.models.review import ReviewStatus, ReviewType


class ReviewCreate(BaseModel):
    """Schema for creating a review"""

    booking_id: int = Field(..., gt=0)
    reviewer_id: int = Field(..., gt=0)
    reviewee_id: int = Field(..., gt=0)
    review_type: str = Field(..., pattern="^(provider_review|seeker_review)$")
    rating: int = Field(..., ge=1, le=5)  # Changed from overall_rating to rating
    title: Optional[str] = Field(None, min_length=5, max_length=200)
    comment: str = Field(..., min_length=10, max_length=2000)
    categories: Optional[dict] = Field(
        default_factory=dict
    )  # Changed from individual fields to dict
    would_recommend: Optional[bool] = Field(default=True)
    photos: Optional[List[str]] = Field(
        default_factory=list
    )  # Changed from images to photos

    @field_validator("categories")
    @classmethod
    def validate_categories(cls, v):
        if v:
            for key, rating in v.items():
                if not isinstance(rating, int) or rating < 1 or rating > 5:
                    raise ValueError(f"Category rating {key} must be between 1 and 5")
        return v


class ReviewUpdate(BaseModel):
    """Schema for updating a review"""

    overall_rating: Optional[int] = Field(None, ge=1, le=5)
    quality_rating: Optional[int] = Field(None, ge=1, le=5)
    timeliness_rating: Optional[int] = Field(None, ge=1, le=5)
    communication_rating: Optional[int] = Field(None, ge=1, le=5)
    title: Optional[str] = Field(None, min_length=5, max_length=200)
    comment: Optional[str] = Field(None, min_length=10, max_length=2000)
    images: Optional[List[str]] = None


class ReviewResponse(BaseModel):
    """Schema for review response"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    booking_id: int
    reviewer_id: int
    reviewee_id: int
    review_type: str  # Changed from ReviewType enum to string
    rating: int  # Changed from overall_rating to rating
    title: Optional[str]
    comment: str
    categories: Optional[dict] = Field(default_factory=dict)  # Added categories
    would_recommend: Optional[bool] = Field(default=True)  # Added would_recommend
    photos: Optional[List[str]] = Field(
        default_factory=list
    )  # Changed from images to photos
    is_verified: bool
    response: Optional[str]
    response_date: Optional[datetime]
    status: str  # Changed from ReviewStatus enum to string
    moderated_at: Optional[datetime]
    moderated_by: Optional[int]
    helpful_votes: int
    created_at: datetime
    updated_at: datetime
    # Add reviewer and reviewee info for test compatibility
    reviewer: Optional[dict] = None
    reviewee: Optional[dict] = None


class ReviewResponseRequest(BaseModel):
    """Schema for responding to a review"""

    response: str = Field(..., min_length=10, max_length=1000)


class ReviewFlagRequest(BaseModel):
    """Schema for flagging a review"""

    reason: str = Field(..., min_length=5, max_length=500)
    details: Optional[str] = Field(None, max_length=1000)  # Make details optional


class ReviewModerationRequest(BaseModel):
    """Schema for moderating a review"""

    action: str = Field(..., pattern="^(approve|reject|flag)$")
    reason: Optional[str] = Field(None, max_length=500)
    moderator_notes: Optional[str] = Field(
        None, max_length=1000
    )  # Add moderator_notes field


class ReviewSearch(BaseModel):
    """Schema for searching reviews"""

    q: Optional[str] = Field(None, min_length=2, max_length=100)
    rating_min: Optional[int] = Field(None, ge=1, le=5)
    rating_max: Optional[int] = Field(None, ge=1, le=5)
    review_type: Optional[ReviewType] = None
    provider_id: Optional[int] = Field(None, gt=0)
    seeker_id: Optional[int] = Field(None, gt=0)
    category: Optional[str] = Field(None, max_length=50)
    location: Optional[str] = Field(None, max_length=100)
    page: int = Field(1, gt=0)
    size: int = Field(10, gt=0, le=100)
    sort_by: str = Field("created_at", pattern="^(created_at|rating|helpful_votes)$")
    order: str = Field("desc", pattern="^(asc|desc)$")

    @field_validator("rating_max")
    @classmethod
    def validate_rating_range(cls, v, info):
        if v is not None and info.data.get("rating_min") is not None:
            if v < info.data["rating_min"]:
                raise ValueError(
                    "rating_max must be greater than or equal to rating_min"
                )
        return v


class ReviewListResponse(BaseModel):
    """Schema for paginated review list"""

    items: List[ReviewResponse]
    total: int
    page: int
    size: int
    pages: int


class ReviewAnalyticsResponse(BaseModel):
    """Schema for review analytics"""

    total_reviews: int
    average_rating: float
    rating_distribution: dict
    recent_reviews: List[ReviewResponse]
    top_keywords: List[str]


class BulkRatingUpdateRequest(BaseModel):
    """Schema for bulk rating updates"""

    provider_ids: List[int] = Field(..., min_length=1, max_length=100)
    recalculate_all: bool = Field(default=False)

    @field_validator("provider_ids")
    @classmethod
    def validate_unique_ids(cls, v):
        if len(v) != len(set(v)):
            raise ValueError("provider_ids must be unique")
        return v
