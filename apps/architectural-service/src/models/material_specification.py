"""MaterialSpecification model for construction materials."""

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Optional
from uuid import uuid4

from sqlalchemy import (JSON, Column, DateTime, ForeignKey, Index, Numeric,
                        String)
from sqlalchemy.dialects.mysql import CHAR
from sqlalchemy.orm import Mapped, relationship
from src.core.database import Base

if TYPE_CHECKING:
    from src.models.design import Design


def generate_uuid() -> str:
    """Generate UUID as string for TiDB/MySQL compatibility."""
    return str(uuid4())


class MaterialSpecification(Base):
    """
    Material specifications for design.

    Stores detailed specifications for construction materials
    including properties, vendor information, and cost estimates.
    """

    __tablename__ = "material_specifications"

    # Primary key
    id = Column(CHAR(36), primary_key=True, default=generate_uuid, nullable=False)

    # Foreign key to design
    design_id = Column(
        CHAR(36),
        ForeignKey("designs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Associated design ID",
    )

    # Material information
    category = Column(
        String(100),
        nullable=False,
        comment="Material category (structural, finishes, mechanical, electrical, plumbing)",
    )
    material_type = Column(
        String(100), nullable=False, comment="Specific material type"
    )
    properties = Column(
        JSON,
        nullable=False,
        comment="Material properties (type, grade, dimensions, finish, etc.)",
    )

    # Vendor integration
    vendor_material_id = Column(
        CHAR(36), nullable=True, comment="Material ID from Vendor Service"
    )
    vendor_info = Column(
        JSON, nullable=True, comment="Vendor information and supplier details"
    )
    cost_estimate = Column(
        Numeric(12, 2), nullable=True, comment="Cost estimate per unit"
    )

    # Design element associations
    design_elements = Column(
        JSON,
        nullable=False,
        default=list,
        comment="List of design element IDs using this material",
    )

    # Timestamps
    created_at = Column(
        DateTime, nullable=False, default=datetime.utcnow, comment="Creation timestamp"
    )
    updated_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        comment="Last update timestamp",
    )

    # Relationship to design
    design: Mapped["Design"] = relationship("Design", back_populates="materials")

    # Table arguments for indexes
    __table_args__ = (
        Index("idx_design_materials", "design_id", "category"),
        Index("idx_material_category", "category"),
        Index("idx_material_type", "material_type"),
        {"comment": "Material specifications for designs"},
    )

    def __repr__(self) -> str:
        """String representation."""
        return (
            f"<MaterialSpecification(id={self.id}, design_id={self.design_id}, "
            f"category={self.category}, type={self.material_type})>"
        )
