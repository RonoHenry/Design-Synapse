"""
Booking API Schemas
"""
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

from pydantic import (BaseModel, ConfigDict, Field, field_serializer,
                      field_validator)
from src.models.booking import BookingStatus


class BookingMilestoneCreate(BaseModel):
    """Schema for creating a booking milestone"""

    model_config = ConfigDict()

    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=500)
    due_date: datetime
    amount: Decimal = Field(..., gt=0)

    @field_serializer("amount")
    def serialize_amount(self, value: Decimal) -> str:
        return str(value)


class BookingCreate(BaseModel):
    """Schema for creating a booking from a quote"""

    model_config = ConfigDict(populate_by_name=True)

    quote_id: int = Field(..., gt=0)
    scheduled_start_date: Optional[datetime] = Field(None, alias="scheduled_start")
    scheduled_completion_date: Optional[datetime] = Field(None, alias="scheduled_end")
    notes: Optional[str] = Field(None, alias="special_instructions", max_length=1000)
    milestones: Optional[List[BookingMilestoneCreate]] = None

    @field_validator("scheduled_completion_date")
    @classmethod
    def validate_completion_after_start(cls, v, info):
        if (
            info.data.get("scheduled_start_date")
            and v
            and v <= info.data["scheduled_start_date"]
        ):
            raise ValueError(
                "scheduled_completion_date must be after " "scheduled_start_date"
            )
        return v


class BookingUpdate(BaseModel):
    """Schema for updating a booking"""

    model_config = ConfigDict()

    scheduled_start_date: Optional[datetime] = None
    scheduled_completion_date: Optional[datetime] = None
    total_cost: Optional[Decimal] = Field(None, gt=0)
    payment_terms: Optional[str] = Field(None, max_length=500)
    notes: Optional[str] = Field(None, max_length=1000)


class BookingStatusUpdate(BaseModel):
    """Schema for updating booking status"""

    status: BookingStatus
    notes: Optional[str] = Field(None, max_length=500)

    @field_validator("status", mode="before")
    @classmethod
    def normalize_status(cls, v):
        """Normalize status to uppercase for enum matching"""
        if isinstance(v, str):
            return v.upper()
        return v


class BookingResponse(BaseModel):
    """Schema for booking response"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    service_request_id: int
    quote_id: int
    provider_id: int
    client_id: int
    scheduled_start_date: datetime
    scheduled_completion_date: datetime
    actual_start_date: Optional[datetime]
    actual_completion_date: Optional[datetime]
    total_cost: Decimal
    currency: str
    payment_terms: Optional[Dict[str, Any]]
    status: BookingStatus
    notes: Optional[str]
    cancellation_reason: Optional[str]
    cancellation_penalty: Optional[Decimal]
    created_at: datetime
    updated_at: datetime
    cancelled_at: Optional[datetime]

    # Add milestones to response if needed, but keeping it simple for now
    # milestones: List[BookingMilestoneResponse] = []


class BookingCancelRequest(BaseModel):
    """Schema for cancelling a booking"""

    model_config = ConfigDict()

    reason: str = Field(..., min_length=5, max_length=500)
    penalty_amount: Optional[Decimal] = Field(None, ge=0)


class BookingRescheduleRequest(BaseModel):
    """Schema for rescheduling a booking"""

    new_start_date: datetime
    new_completion_date: datetime
    reason: str = Field(..., min_length=5, max_length=500)

    @field_validator("new_completion_date")
    @classmethod
    def validate_completion_after_start(cls, v, info):
        if info.data.get("new_start_date") and v <= info.data["new_start_date"]:
            raise ValueError("new_completion_date must be after new_start_date")
        return v


class MilestoneUpdate(BaseModel):
    """Schema for milestone updates"""

    milestone_name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=500)
    completion_percentage: int = Field(..., ge=0, le=100)
    notes: Optional[str] = Field(None, max_length=500)


class BookingUpdateRequest(BaseModel):
    """Schema for adding booking updates"""

    update_type: str = Field(..., min_length=1, max_length=50)
    description: str = Field(..., min_length=5, max_length=1000)
    images: Optional[List[str]] = Field(default_factory=list)
    completion_percentage: Optional[int] = Field(None, ge=0, le=100)


class BookingListResponse(BaseModel):
    """Schema for paginated booking list"""

    items: List[BookingResponse]
    total: int
    page: int
    size: int
    pages: int
