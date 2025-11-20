"""Order and OrderItem models for order management."""

from datetime import datetime, timezone
from decimal import Decimal
from typing import List, Optional

from sqlalchemy import (DateTime, ForeignKey, Integer, Numeric, String, Text,
                        func)
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates
from src.infrastructure.database import Base


class Order(Base):
    """Order model representing customer purchase orders."""

    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    customer_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    total_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="pending",
        server_default="pending",
        index=True,
    )
    shipping_address: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    items: Mapped[List["OrderItem"]] = relationship(
        "OrderItem", back_populates="order", cascade="all, delete-orphan"
    )

    def __init__(
        self,
        customer_id: int,
        total_amount: Decimal,
        shipping_address: Optional[str] = None,
        status: str = "pending",
        **kwargs,
    ):
        """Initialize a new order."""
        self.customer_id = customer_id
        self.total_amount = self._validate_total_amount(total_amount)
        self.shipping_address = shipping_address
        self.status = self._validate_status(status)
        self.created_at = datetime.now(timezone.utc)
        self.updated_at = self.created_at

    @staticmethod
    def _validate_total_amount(amount: Decimal) -> Decimal:
        """Validate order total amount."""
        if amount < Decimal("0.0"):
            raise ValueError("Total amount cannot be negative")
        if amount > Decimal("99999999.99"):
            raise ValueError("Total amount exceeds maximum allowed value")
        return amount

    @staticmethod
    def _validate_status(status: str) -> str:
        """Validate order status."""
        allowed_statuses = [
            "pending",
            "confirmed",
            "processing",
            "shipped",
            "delivered",
            "cancelled",
        ]
        if status not in allowed_statuses:
            raise ValueError(
                f"Invalid order status. Must be one of: {allowed_statuses}"
            )
        return status

    @validates("status")
    def validate_status_update(self, key: str, value: str) -> str:
        """Validate status on update."""
        return self._validate_status(value)

    @validates("total_amount")
    def validate_total_amount_update(self, key: str, value: Decimal) -> Decimal:
        """Validate total amount on update."""
        return self._validate_total_amount(value)

    def update_status(self, new_status: str) -> None:
        """Update order status."""
        self.status = new_status
        self.updated_at = datetime.now(timezone.utc)

    def calculate_total(self) -> Decimal:
        """Calculate total from order items."""
        if not self.items:
            return Decimal("0.0")
        return sum(item.get_subtotal() for item in self.items)

    def recalculate_total(self) -> None:
        """Recalculate and update total amount from items."""
        self.total_amount = self.calculate_total()
        self.updated_at = datetime.now(timezone.utc)

    def is_pending(self) -> bool:
        """Check if order is pending."""
        return self.status == "pending"

    def is_confirmed(self) -> bool:
        """Check if order is confirmed."""
        return self.status == "confirmed"

    def is_completed(self) -> bool:
        """Check if order is delivered."""
        return self.status == "delivered"

    def is_cancelled(self) -> bool:
        """Check if order is cancelled."""
        return self.status == "cancelled"

    def can_be_cancelled(self) -> bool:
        """Check if order can be cancelled."""
        return self.status in ["pending", "confirmed"]

    def cancel(self) -> None:
        """Cancel the order."""
        if not self.can_be_cancelled():
            raise ValueError(f"Cannot cancel order with status: {self.status}")
        self.status = "cancelled"
        self.updated_at = datetime.now(timezone.utc)

    def __repr__(self) -> str:
        """String representation of order."""
        return f"<Order(id={self.id}, customer_id={self.customer_id}, status='{self.status}', total={self.total_amount})>"


class OrderItem(Base):
    """OrderItem model representing individual items in an order."""

    __tablename__ = "order_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    order_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, index=True
    )
    product_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)

    # Relationships
    order: Mapped["Order"] = relationship("Order", back_populates="items")

    def __init__(
        self,
        order_id: int,
        product_id: int,
        quantity: int,
        unit_price: Decimal,
        **kwargs,
    ):
        """Initialize a new order item."""
        self.order_id = order_id
        self.product_id = product_id
        self.quantity = self._validate_quantity(quantity)
        self.unit_price = self._validate_unit_price(unit_price)

    @staticmethod
    def _validate_quantity(quantity: int) -> int:
        """Validate order item quantity."""
        if quantity <= 0:
            raise ValueError("Quantity must be positive")
        if quantity > 10000:
            raise ValueError("Quantity exceeds maximum allowed value")
        return quantity

    @staticmethod
    def _validate_unit_price(price: Decimal) -> Decimal:
        """Validate unit price."""
        if price < Decimal("0.0"):
            raise ValueError("Unit price cannot be negative")
        return price

    @validates("quantity")
    def validate_quantity_update(self, key: str, value: int) -> int:
        """Validate quantity on update."""
        return self._validate_quantity(value)

    @validates("unit_price")
    def validate_unit_price_update(self, key: str, value: Decimal) -> Decimal:
        """Validate unit price on update."""
        return self._validate_unit_price(value)

    def get_subtotal(self) -> Decimal:
        """Calculate subtotal for this order item."""
        return self.unit_price * self.quantity

    def __repr__(self) -> str:
        """String representation of order item."""
        return f"<OrderItem(id={self.id}, product_id={self.product_id}, quantity={self.quantity}, subtotal={self.get_subtotal()})>"
