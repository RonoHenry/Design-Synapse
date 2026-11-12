"""DesignStaging model for placing products in designs."""

from datetime import datetime, timezone
from typing import Any, Dict, Optional

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, func
from sqlalchemy.orm import Mapped, mapped_column, validates
from src.infrastructure.database import Base


class DesignStaging(Base):
    """DesignStaging model for placing products in design visualizations."""

    __tablename__ = "design_staging"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    design_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    product_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    position: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)
    rotation: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)
    scale: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    def __init__(
        self,
        design_id: int,
        product_id: int,
        position: Dict[str, Any],
        rotation: Dict[str, Any],
        scale: Dict[str, Any],
        quantity: int = 1,
        **kwargs,
    ):
        """Initialize a new design staging entry."""
        self.design_id = design_id
        self.product_id = product_id
        self.position = self._validate_position(position)
        self.rotation = self._validate_rotation(rotation)
        self.scale = self._validate_scale(scale)
        self.quantity = self._validate_quantity(quantity)
        self.created_at = datetime.now(timezone.utc)

    @staticmethod
    def _validate_position(position: Dict[str, Any]) -> Dict[str, Any]:
        """Validate position coordinates."""
        required_keys = ["x", "y", "z"]
        for key in required_keys:
            if key not in position:
                raise ValueError(f"Position must include {key} coordinate")
            if not isinstance(position[key], (int, float)):
                raise ValueError(f"Position {key} must be a number")
        return position

    @staticmethod
    def _validate_rotation(rotation: Dict[str, Any]) -> Dict[str, Any]:
        """Validate rotation angles."""
        required_keys = ["x", "y", "z"]
        for key in required_keys:
            if key not in rotation:
                raise ValueError(f"Rotation must include {key} angle")
            if not isinstance(rotation[key], (int, float)):
                raise ValueError(f"Rotation {key} must be a number")
        return rotation

    @staticmethod
    def _validate_scale(scale: Dict[str, Any]) -> Dict[str, Any]:
        """Validate scale factors."""
        required_keys = ["x", "y", "z"]
        for key in required_keys:
            if key not in scale:
                raise ValueError(f"Scale must include {key} factor")
            if not isinstance(scale[key], (int, float)):
                raise ValueError(f"Scale {key} must be a number")
            if scale[key] <= 0:
                raise ValueError(f"Scale {key} must be positive")
        return scale

    @staticmethod
    def _validate_quantity(quantity: int) -> int:
        """Validate quantity."""
        if quantity <= 0:
            raise ValueError("Quantity must be positive")
        if quantity > 10000:
            raise ValueError("Quantity exceeds maximum allowed value")
        return quantity

    @validates("quantity")
    def validate_quantity_update(self, key: str, value: int) -> int:
        """Validate quantity on update."""
        return self._validate_quantity(value)

    def update_position(self, position: Dict[str, Any]) -> None:
        """Update product position in design."""
        self.position = self._validate_position(position)

    def update_rotation(self, rotation: Dict[str, Any]) -> None:
        """Update product rotation in design."""
        self.rotation = self._validate_rotation(rotation)

    def update_scale(self, scale: Dict[str, Any]) -> None:
        """Update product scale in design."""
        self.scale = self._validate_scale(scale)

    def update_quantity(self, quantity: int) -> None:
        """Update product quantity in design."""
        self.quantity = self._validate_quantity(quantity)

    def get_transform_matrix(self) -> Dict[str, Dict[str, Any]]:
        """Get complete transformation matrix."""
        return {
            "position": self.position,
            "rotation": self.rotation,
            "scale": self.scale,
        }

    def __repr__(self) -> str:
        """String representation of design staging."""
        return f"<DesignStaging(id={self.id}, design_id={self.design_id}, product_id={self.product_id}, quantity={self.quantity})>"
