"""Order API schemas."""

from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, Field, validator


class OrderItemBase(BaseModel):
    """Base order item schema."""

    product_id: int = Field(..., gt=0)
    quantity: int = Field(..., gt=0)


class OrderItemCreate(OrderItemBase):
    """Schema for creating an order item."""

    pass


class OrderItemResponse(OrderItemBase):
    """Schema for order item response."""

    id: int
    order_id: int
    unit_price: Decimal
    subtotal: Decimal

    class Config:
        from_attributes = True


class OrderBase(BaseModel):
    """Base order schema."""

    shipping_address: Optional[str] = None


class OrderCreate(OrderBase):
    """Schema for creating an order."""

    items: List[OrderItemCreate] = Field(..., min_items=1)

    @validator("items")
    def validate_items(cls, v):
        """Validate order items."""
        if not v:
            raise ValueError("Order must have at least one item")

        # Check for duplicate products
        product_ids = [item.product_id for item in v]
        if len(product_ids) != len(set(product_ids)):
            raise ValueError("Duplicate products in order items")

        return v


class OrderUpdate(BaseModel):
    """Schema for updating an order."""

    shipping_address: Optional[str] = None


class OrderStatusUpdate(BaseModel):
    """Schema for updating order status."""

    status: str = Field(
        ..., pattern="^(pending|confirmed|processing|shipped|delivered|cancelled)$"
    )


class OrderResponse(OrderBase):
    """Schema for order response."""

    id: int
    customer_id: int
    total_amount: Decimal
    status: str
    items: List[OrderItemResponse] = []
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class OrderListResponse(BaseModel):
    """Schema for order list response."""

    orders: List[OrderResponse]
    total: int
    skip: int
    limit: int


class OrderSearch(BaseModel):
    """Schema for order search parameters."""

    customer_id: Optional[int] = None
    vendor_id: Optional[int] = None
    status: Optional[str] = Field(
        None, pattern="^(pending|confirmed|processing|shipped|delivered|cancelled)$"
    )
    min_total: Optional[Decimal] = Field(None, ge=0)
    max_total: Optional[Decimal] = Field(None, ge=0)
    skip: int = Field(0, ge=0)
    limit: int = Field(100, ge=1, le=1000)

    @validator("max_total")
    def validate_total_range(cls, v, values):
        """Validate total range."""
        if v is not None and "min_total" in values and values["min_total"] is not None:
            if v < values["min_total"]:
                raise ValueError("max_total must be greater than or equal to min_total")
        return v


class AddItemToOrder(BaseModel):
    """Schema for adding item to existing order."""

    product_id: int = Field(..., gt=0)
    quantity: int = Field(..., gt=0)


class PaymentData(BaseModel):
    """Schema for payment processing."""

    payment_method: str = Field(
        ..., pattern="^(credit_card|debit_card|paypal|bank_transfer)$"
    )
    amount: Decimal = Field(..., gt=0)
    currency: str = Field("USD", pattern="^[A-Z]{3}$")
    # In a real implementation, you'd have more payment-specific fields
    # but we'll keep it simple for this example


class OrderSummary(BaseModel):
    """Schema for order summary statistics."""

    total_orders: int
    total_amount: Decimal
    orders_by_status: dict
    recent_orders: List[OrderResponse]
