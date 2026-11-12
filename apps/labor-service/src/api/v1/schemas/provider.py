"""Provider API schemas."""
from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel, EmailStr, Field

from .base import LocationSchema


class ProviderCreateRequest(BaseModel):
    """Provider creation request schema."""

    user_id: int
    business_name: Optional[str] = Field(None, min_length=1, max_length=255)
    individual_name: str = Field(..., min_length=1, max_length=255)
    provider_type: str = Field(..., pattern="^(INDIVIDUAL|BUSINESS|TEAM)$")
    description: Optional[str] = Field(None, max_length=1000)
    experience_years: int = Field(0, ge=0, le=50)


class ProviderUpdateRequest(BaseModel):
    """Provider update request schema."""

    business_name: Optional[str] = Field(None, min_length=1, max_length=255)
    individual_name: Optional[str] = Field(None, min_length=1, max_length=255)
    provider_type: Optional[str] = Field(None, pattern="^(INDIVIDUAL|BUSINESS|TEAM)$")
    description: Optional[str] = Field(None, max_length=1000)
    experience_years: Optional[int] = Field(None, ge=0, le=50)


class SkillSchema(BaseModel):
    """Skill schema."""

    id: int
    name: str
    category: str
    proficiency_level: str
    years_experience: int
    certifications: List[str]


class ServiceAreaSchema(BaseModel):
    """Service area schema."""

    id: int
    city: str
    state: str
    zip_code: str
    travel_cost: float


class ProviderResponse(BaseModel):
    """Provider response schema."""

    id: int
    user_id: int
    business_name: Optional[str]
    individual_name: str
    provider_type: str
    description: Optional[str]
    experience_years: int
    verification_status: str
    rating: float
    total_reviews: int
    total_jobs_completed: int
    is_active: bool
    is_available: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ProviderSkillRequest(BaseModel):
    """Provider skill addition request."""

    skill_id: int
    proficiency_level: str = Field(
        ..., pattern="^(beginner|intermediate|advanced|expert)$"
    )
    years_experience: int = Field(..., ge=0, le=50)
    certifications: List[str] = []


class ProviderAvailabilityRequest(BaseModel):
    """Provider availability update request."""

    available: bool
    available_from: Optional[datetime] = None
    available_until: Optional[datetime] = None
    weekly_schedule: Optional[Dict[str, Dict[str, str]]] = None


class ProviderAnalyticsResponse(BaseModel):
    """Provider analytics response."""

    total_jobs: int
    completed_jobs: int
    average_rating: float
    total_earnings: float
    completion_rate: float
    response_rate: float
    repeat_clients: int


class ProviderSearchParams(BaseModel):
    """Provider search parameters."""

    skills: Optional[str] = None
    location: Optional[str] = None
    radius: Optional[float] = Field(None, gt=0, le=500)
    min_rating: Optional[float] = Field(None, ge=0, le=5)
    max_hourly_rate: Optional[float] = Field(None, gt=0)
    available: Optional[bool] = None
    verified: Optional[bool] = None
    page: int = Field(1, ge=1)
    size: int = Field(10, ge=1, le=100)
    sort_by: str = Field("rating", pattern="^(rating|distance|hourly_rate|experience)$")
    order: str = Field("desc", pattern="^(asc|desc)$")
