"""StructuralDesign model for storing structural engineering designs."""

from datetime import datetime
from typing import Any, Dict, Optional

from sqlalchemy import (JSON, Column, DateTime, ForeignKey, Integer, String,
                        Text)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..core.database import Base


class StructuralDesign(Base):
    """Model for storing structural engineering designs.

    Structural designs include beams, columns, foundations, and other
    structural elements with their loads, material properties, and results.
    """

    __tablename__ = "structural_designs"

    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Project association
    project_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)

    # Link to calculation sheet
    calculation_sheet_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("calculation_sheets.id"), nullable=True, index=True
    )

    # Design metadata
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    design_type: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True
    )  # beam, column, foundation, slab, wall

    # Design parameters (stored as JSON)
    loads: Mapped[Dict[str, Any]] = mapped_column(
        JSON, nullable=False
    )  # dead, live, wind, seismic
    material_properties: Mapped[Dict[str, Any]] = mapped_column(
        JSON, nullable=False
    )  # type, grade, strength
    geometry: Mapped[Dict[str, Any]] = mapped_column(
        JSON, nullable=False
    )  # dimensions, shape

    # Design results (stored as JSON)
    design_results: Mapped[Dict[str, Any]] = mapped_column(
        JSON, nullable=False
    )  # required sections, reinforcement
    stress_ratios: Mapped[Dict[str, Any]] = mapped_column(
        JSON, nullable=False
    )  # utilization ratios

    # Code compliance
    code_references: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON, nullable=True
    )  # applicable codes

    # Units system
    units: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True, default="imperial"
    )

    # Status
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="draft"
    )  # draft, approved, rejected

    # Audit fields
    created_by: Mapped[str] = mapped_column(String(255), nullable=False)
    updated_by: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    def __repr__(self) -> str:
        """String representation of StructuralDesign."""
        return (
            f"<StructuralDesign(id={self.id}, title='{self.title}', "
            f"type='{self.design_type}', status='{self.status}')>"
        )

    def __str__(self) -> str:
        """Human-readable string representation."""
        return f"{self.title} ({self.design_type}) - {self.status}"
