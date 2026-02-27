"""
Service Request API Schemas
"""
from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator
from src.models.service_request import RequestStatus, UrgencyLevel


class ServiceRequestCreate(BaseModel):
    """Schema for creating a service request"""

    model_config = ConfigDict()

    title: str = Field(..., min_length=1, max_length=200)
    description: str = Field(..., min_length=10, max_length=2000)
    seeker_id: int = Field(..., gt=0)
    location_address: str = Field(..., min_length=5, max_length=500)
    location_latitude: Optional[float] = Field(None, ge=-90, le=90)
    location_longitude: Optional[float] = Field(None, ge=-180, le=180)
    budget_min: Optional[Decimal] = Field(None, gt=0)
    budget_max: Optional[Decimal] = Field(None, gt=0)
    budget_currency: str = Field(default="USD", max_length=3)
    urgency_level: UrgencyLevel = Field(default=UrgencyLevel.MEDIUM)
    preferred_start_date: Optional[datetime] = None
    estimated_duration_hours: Optional[int] = Field(None, gt=0)
    requirements: Optional[str] = Field(None, max_length=1000)
    images: Optional[List[str]] = Field(default_factory=list)
    project_id: Optional[int] = Field(None, gt=0)

    @field_validator("budget_max")
    @classmethod
    def validate_budget_range(cls, v, info):
        if v is not None and info.data.get("budget_min") is not None:
            if v < info.data["budget_min"]:
                raise ValueError(
                    "budget_max must be greater than or equal to budget_min"
                )
        return v


class ServiceRequestUpdate(BaseModel):
    """Schema for updating a service request"""

    model_config = ConfigDict(from_attributes=True)

    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, min_length=10, max_length=2000)
    location_address: Optional[str] = Field(None, min_length=5, max_length=500)
    location_latitude: Optional[float] = Field(None, ge=-90, le=90)
    location_longitude: Optional[float] = Field(None, ge=-180, le=180)
    budget_min: Optional[Decimal] = Field(None, gt=0)
    budget_max: Optional[Decimal] = Field(None, gt=0)
    urgency_level: Optional[UrgencyLevel] = None
    preferred_start_date: Optional[datetime] = None
    estimated_duration_hours: Optional[int] = Field(None, gt=0)
    requirements: Optional[str] = Field(None, max_length=1000)
    images: Optional[List[str]] = None


class ServiceRequestResponse(BaseModel):
    """Schema for service request response"""

    model_config = ConfigDict(from_attributes=True)
    id: int
    title: str
    description: str
    seeker_id: int
    location_address: str
    location_latitude: Optional[float]
    location_longitude: Optional[float]
    budget_min: Optional[Decimal]
    budget_max: Optional[Decimal]
    budget_currency: str
    urgency_level: UrgencyLevel
    preferred_start_date: Optional[datetime]
    estimated_duration_hours: Optional[int]
    status: RequestStatus
    requirements: Optional[str]
    images: Optional[List[str]]
    project_id: Optional[int]
    created_at: datetime
    updated_at: datetime
    expires_at: Optional[datetime]


class ServiceRequestSearch(BaseModel):
    """Schema for searching service requests"""

    model_config = ConfigDict()
    skills: Optional[List[str]] = Field(None, description="List of required skills")
    location_latitude: Optional[float] = Field(None, ge=-90, le=90)
    location_longitude: Optional[float] = Field(None, ge=-180, le=180)
    radius_km: Optional[int] = Field(50, gt=0, le=500)
    budget_min: Optional[Decimal] = Field(None, gt=0)
    budget_max: Optional[Decimal] = Field(None, gt=0)
    urgency_level: Optional[UrgencyLevel] = None
    provider_id: Optional[int] = Field(None, gt=0)
    page: int = Field(1, gt=0)
    size: int = Field(10, gt=0, le=100)


class CancelRequestRequest(BaseModel):
    """Schema for cancelling a service request"""

    reason: str = Field(..., min_length=5, max_length=500)


class ServiceRequestListResponse(BaseModel):
    """Schema for paginated service request list"""

    items: List[ServiceRequestResponse]
    total: int
    page: int
    size: int
    pages: int
