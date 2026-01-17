"""Product API schemas."""

from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field, validator


class ProductBase(BaseModel):
    """Base product schema."""

    name: str = Field(..., min_length=2, max_length=255)
    description: Optional[str] = None
    category: str = Field(
        ..., pattern="^(materials|tools|equipment|services|furniture|fixtures)$"
    )
    price: Decimal = Field(..., ge=0, le=99999999.99)
    inventory_quantity: int = Field(..., ge=0)
    images: Optional[Dict[str, Any]] = None
    specifications: Optional[Dict[str, Any]] = None
    model_url: Optional[str] = Field(None, max_length=500)
    dimensions: Optional[Dict[str, Any]] = None
    model_format: Optional[str] = Field(None, pattern="^(glb|gltf|obj|fbx)$")

    @validator("dimensions")
    def validate_dimensions(cls, v):
        """Validate dimensions structure."""
        if v is not None:
            required_keys = ["length", "width", "height"]
            for key in required_keys:
                if key not in v:
                    raise ValueError(f"Dimensions must include {key}")
                if not isinstance(v[key], (int, float)) or v[key] <= 0:
                    raise ValueError(f"Dimension {key} must be a positive number")
        return v


class ProductCreate(ProductBase):
    """Schema for creating a product."""

    pass


class ProductUpdate(BaseModel):
    """Schema for updating a product."""

    name: Optional[str] = Field(None, min_length=2, max_length=255)
    description: Optional[str] = None
    category: Optional[str] = Field(
        None, pattern="^(materials|tools|equipment|services|furniture|fixtures)$"
    )
    price: Optional[Decimal] = Field(None, ge=0, le=99999999.99)
    inventory_quantity: Optional[int] = Field(None, ge=0)
    images: Optional[Dict[str, Any]] = None
    specifications: Optional[Dict[str, Any]] = None
    model_url: Optional[str] = Field(None, max_length=500)
    dimensions: Optional[Dict[str, Any]] = None
    model_format: Optional[str] = Field(None, pattern="^(glb|gltf|obj|fbx)$")
    is_active: Optional[bool] = None

    @validator("dimensions")
    def validate_dimensions(cls, v):
        """Validate dimensions structure."""
        if v is not None:
            required_keys = ["length", "width", "height"]
            for key in required_keys:
                if key not in v:
                    raise ValueError(f"Dimensions must include {key}")
                if not isinstance(v[key], (int, float)) or v[key] <= 0:
                    raise ValueError(f"Dimension {key} must be a positive number")
        return v


class ProductResponse(ProductBase):
    """Schema for product response."""

    id: int
    vendor_id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ProductSearch(BaseModel):
    """Schema for product search parameters."""

    query: Optional[str] = None
    category: Optional[str] = Field(
        None, pattern="^(materials|tools|equipment|services|furniture|fixtures)$"
    )
    min_price: Optional[Decimal] = Field(None, ge=0)
    max_price: Optional[Decimal] = Field(None, ge=0)
    in_stock_only: bool = False
    has_3d_model: Optional[bool] = None
    skip: int = Field(0, ge=0)
    limit: int = Field(100, ge=1, le=1000)


class ProductListResponse(BaseModel):
    """Schema for product list response."""

    products: list[ProductResponse]
    total: int
    skip: int
    limit: int


class InventoryUpdate(BaseModel):
    """Schema for inventory update."""

    quantity: int = Field(..., ge=0)


class InventoryAdjustment(BaseModel):
    """Schema for inventory adjustment."""

    adjustment: int
