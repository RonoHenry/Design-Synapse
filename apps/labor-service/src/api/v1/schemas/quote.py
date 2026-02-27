"""
Quote API Schemas
"""
from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator
from src.models.quote import QuoteStatus


class QuoteCreate(BaseModel):
    """Schema for creating a quote"""

    model_config = ConfigDict()
    request_id: int = Field(..., gt=0)
    provider_id: int = Field(..., gt=0)
    # Support both detailed cost breakdown and simple total amount
    labor_cost: Optional[Decimal] = Field(None, ge=0)
    material_cost: Optional[Decimal] = Field(Decimal("0"), ge=0)
    travel_cost: Optional[Decimal] = Field(Decimal("0"), ge=0)
    total_amount: Optional[Decimal] = Field(None, gt=0)  # Alternative to detailed costs
    currency: str = Field(default="USD", max_length=3)
    start_availability: Optional[datetime] = None
    completion_estimate: Optional[datetime] = None
    estimated_hours: Optional[int] = Field(None, gt=0)
    timeline_days: Optional[int] = Field(
        None, gt=0
    )  # Alternative to completion_estimate
    description: Optional[str] = Field(None, max_length=1000)
    terms_and_conditions: Optional[str] = Field(None, max_length=2000)
    terms_conditions: Optional[str] = Field(
        None, max_length=2000
    )  # Alternative field name
    notes: Optional[str] = Field(None, max_length=500)
    valid_until: Optional[datetime] = None
    cost_breakdown_details: Optional[str] = Field(None, max_length=1000)
    cost_breakdown: Optional[List[dict]] = Field(
        None
    )  # Alternative structured breakdown

    @field_validator("completion_estimate")
    @classmethod
    def validate_completion_after_start(cls, v, info):
        if v is not None and info.data.get("start_availability") is not None:
            if v <= info.data["start_availability"]:
                raise ValueError("completion_estimate must be after start_availability")
        return v


class QuoteUpdate(BaseModel):
    """Schema for updating a quote"""

    model_config = ConfigDict()
    labor_cost: Optional[Decimal] = Field(None, ge=0)
    material_cost: Optional[Decimal] = Field(None, ge=0)
    travel_cost: Optional[Decimal] = Field(None, ge=0)
    total_amount: Optional[Decimal] = Field(None, gt=0)  # Alternative to detailed costs
    timeline_days: Optional[int] = Field(
        None, gt=0
    )  # Alternative to completion_estimate
    start_availability: Optional[datetime] = None
    completion_estimate: Optional[datetime] = None
    estimated_hours: Optional[int] = Field(None, gt=0)
    description: Optional[str] = Field(None, max_length=1000)
    terms_and_conditions: Optional[str] = Field(None, max_length=2000)
    notes: Optional[str] = Field(None, max_length=500)
    valid_until: Optional[datetime] = None
    cost_breakdown_details: Optional[str] = Field(None, max_length=1000)


class QuoteResponse(BaseModel):
    """Schema for quote response"""

    model_config = ConfigDict(
        from_attributes=True, populate_by_name=True  # Allow both field name and alias
    )
    id: int
    request_id: int
    provider_id: int
    parent_quote_id: Optional[int]
    labor_cost: Decimal
    material_cost: Optional[Decimal]
    travel_cost: Optional[Decimal]
    total_amount: Decimal = Field(alias="total_cost")
    currency: str
    start_availability: Optional[datetime]
    completion_estimate: Optional[datetime]
    estimated_hours: Optional[int]
    description: Optional[str]
    terms_and_conditions: Optional[str]
    notes: Optional[str]
    status: QuoteStatus
    valid_until: Optional[datetime]
    cost_breakdown: Optional[str] = Field(alias="cost_breakdown_details")
    created_at: datetime
    updated_at: datetime
    submitted_at: Optional[datetime]
    # Related objects (will be populated by service layer)
    provider: Optional[dict] = None
    request: Optional[dict] = None


class QuoteAcceptRequest(BaseModel):
    """Schema for accepting a quote"""

    seeker_id: int = Field(..., gt=0)


class QuoteRejectRequest(BaseModel):
    """Schema for rejecting a quote"""

    reason: str = Field(..., min_length=5, max_length=500)


class QuoteCompareRequest(BaseModel):
    """Schema for comparing quotes"""

    quote_ids: List[int] = Field(..., min_length=2, max_length=10)

    @field_validator("quote_ids")
    @classmethod
    def validate_unique_ids(cls, v):
        if len(v) != len(set(v)):
            raise ValueError("quote_ids must be unique")
        return v


class CounterProposalRequest(BaseModel):
    """Schema for submitting a counter proposal"""

    model_config = ConfigDict()
    original_quote_id: Optional[int] = Field(None, gt=0)
    total_amount: Optional[Decimal] = Field(None, gt=0)
    total_cost: Optional[Decimal] = Field(None, gt=0)
    timeline_days: Optional[int] = Field(None, gt=0)
    message: Optional[str] = Field(None, max_length=500)
    notes: Optional[str] = Field(None, max_length=500)
    estimated_hours: Optional[int] = Field(None, gt=0)
    completion_estimate: Optional[datetime] = None


class QuoteListResponse(BaseModel):
    """Schema for paginated quote list"""

    items: List[QuoteResponse]
    total: int
    page: int
    size: int
    pages: int


class QuoteComparisonResponse(BaseModel):
    """Schema for quote comparison response"""

    comparison_matrix: List[dict]
    recommendations: List[str]
