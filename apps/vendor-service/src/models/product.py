"""Product model for product catalog management."""

import json
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, Optional

from sqlalchemy import (JSON, Boolean, DateTime, ForeignKey, Integer, Numeric,
                        String, Text, func)
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates
from src.infrastructure.database import Base


class Product(Base):
    """Product model representing items in the vendor catalog."""

    __tablename__ = "products"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    vendor_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("vendors.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    category: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    inventory_quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Product media and specifications
    images: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    specifications: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON, nullable=True
    )

    # 3D staging fields for design visualization
    model_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    dimensions: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    model_format: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default="true"
    )
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
    vendor: Mapped["Vendor"] = relationship("Vendor", back_populates="products")

    def __init__(
        self,
        vendor_id: int,
        name: str,
        category: str,
        price: Decimal,
        description: Optional[str] = None,
        inventory_quantity: int = 0,
        images: Optional[Dict[str, Any]] = None,
        specifications: Optional[Dict[str, Any]] = None,
        model_url: Optional[str] = None,
        dimensions: Optional[Dict[str, Any]] = None,
        model_format: Optional[str] = None,
        is_active: bool = True,
        **kwargs,
    ):
        """Initialize a new product."""
        self.vendor_id = vendor_id
        self.name = self._validate_name(name)
        self.category = self._validate_category(category)
        self.price = self._validate_price(price)
        self.description = description
        self.inventory_quantity = self._validate_inventory(inventory_quantity)
        self.images = images or {}
        self.specifications = specifications or {}
        self.model_url = model_url
        self.dimensions = self._validate_dimensions(dimensions) if dimensions else None
        self.model_format = (
            self._validate_model_format(model_format) if model_format else None
        )
        self.is_active = is_active
        self.created_at = datetime.now(timezone.utc)
        self.updated_at = self.created_at

    @staticmethod
    def _validate_name(name: str) -> str:
        """Validate product name."""
        if not name or len(name.strip()) < 2:
            raise ValueError("Product name must be at least 2 characters long")
        if len(name) > 255:
            raise ValueError("Product name cannot exceed 255 characters")
        return name.strip()

    @staticmethod
    def _validate_category(category: str) -> str:
        """Validate product category."""
        allowed_categories = [
            "materials",
            "tools",
            "equipment",
            "services",
            "furniture",
            "fixtures",
        ]
        if category not in allowed_categories:
            raise ValueError(f"Invalid category. Must be one of: {allowed_categories}")
        return category

    @staticmethod
    def _validate_price(price: Decimal) -> Decimal:
        """Validate product price."""
        if price < Decimal("0.0"):
            raise ValueError("Price cannot be negative")
        if price > Decimal("99999999.99"):
            raise ValueError("Price exceeds maximum allowed value")
        return price

    @staticmethod
    def _validate_inventory(quantity: int) -> int:
        """Validate inventory quantity."""
        if quantity < 0:
            raise ValueError("Inventory quantity cannot be negative")
        return quantity

    @staticmethod
    def _validate_dimensions(dimensions: Dict[str, Any]) -> Dict[str, Any]:
        """Validate product dimensions for 3D staging."""
        required_keys = ["length", "width", "height"]
        for key in required_keys:
            if key not in dimensions:
                raise ValueError(f"Dimensions must include {key}")
            if not isinstance(dimensions[key], (int, float)) or dimensions[key] <= 0:
                raise ValueError(f"Dimension {key} must be a positive number")
        return dimensions

    @staticmethod
    def _validate_model_format(model_format: str) -> str:
        """Validate 3D model format."""
        allowed_formats = ["glb", "gltf", "obj", "fbx"]
        if model_format.lower() not in allowed_formats:
            raise ValueError(f"Invalid model format. Must be one of: {allowed_formats}")
        return model_format.lower()

    @validates("price")
    def validate_price_update(self, key: str, value: Decimal) -> Decimal:
        """Validate price on update."""
        return self._validate_price(value)

    @validates("inventory_quantity")
    def validate_inventory_update(self, key: str, value: int) -> int:
        """Validate inventory on update."""
        return self._validate_inventory(value)

    def update_inventory(self, quantity: int) -> None:
        """Update product inventory."""
        self.inventory_quantity = quantity
        self.updated_at = datetime.now(timezone.utc)

    def adjust_inventory(self, adjustment: int) -> None:
        """Adjust inventory by a delta amount."""
        new_quantity = self.inventory_quantity + adjustment
        if new_quantity < 0:
            raise ValueError("Insufficient inventory")
        self.inventory_quantity = new_quantity
        self.updated_at = datetime.now(timezone.utc)

    def is_available(self) -> bool:
        """Check if product is available for purchase."""
        return self.is_active and self.inventory_quantity > 0

    def is_in_stock(self) -> bool:
        """Check if product has inventory."""
        return self.inventory_quantity > 0

    def has_3d_model(self) -> bool:
        """Check if product has 3D model data for staging."""
        return bool(self.model_url and self.dimensions and self.model_format)

    def activate(self) -> None:
        """Activate product."""
        self.is_active = True
        self.updated_at = datetime.now(timezone.utc)

    def deactivate(self) -> None:
        """Deactivate product."""
        self.is_active = False
        self.updated_at = datetime.now(timezone.utc)

    def get_dimensions_dict(self) -> Optional[Dict[str, float]]:
        """Get dimensions as a dictionary."""
        return self.dimensions if self.dimensions else None

    def __repr__(self) -> str:
        """String representation of product."""
        return f"<Product(id={self.id}, name='{self.name}', category='{self.category}', price={self.price})>"
