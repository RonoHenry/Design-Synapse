"""Vendor API schemas."""

from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, validator


class VendorBase(BaseModel):
    """Base vendor schema."""

    company_name: str = Field(..., min_length=2, max_length=255)
    email: EmailStr
    phone: Optional[str] = Field(None, max_length=50)
    address: Optional[str] = None


class VendorCreate(VendorBase):
    """Schema for creating a vendor."""

    pass


class VendorUpdate(BaseModel):
    """Schema for updating a vendor."""

    company_name: Optional[str] = Field(None, min_length=2, max_length=255)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, max_length=50)
    address: Optional[str] = None


class VendorResponse(VendorBase):
    """Schema for vendor response."""

    id: int
    user_id: int
    verification_status: str
    rating: Decimal
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class VendorListResponse(BaseModel):
    """Schema for vendor list response."""

    vendors: list[VendorResponse]
    total: int
    skip: int
    limit: int
