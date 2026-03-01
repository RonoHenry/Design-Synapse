"""MEPDesign model for storing MEP (Mechanical, Electrical, Plumbing) designs."""

from datetime import datetime
from typing import Any, Dict, Optional

from sqlalchemy import (JSON, Column, DateTime, ForeignKey, Integer, String,
                        Text)
from sqlalchemy.orm import Mapped, mapped_column

from ..core.database import Base


class MEPDesign(Base):
    """Model for storing MEP engineering designs.

    MEP designs include HVAC, electrical, plumbing, and fire protection
    systems with their loads, equipment, and distribution parameters.
    """

    __tablename__ = "mep_designs"

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
    system_type: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True
    )  # hvac, electrical, plumbing, fire_protection

    # Design parameters (stored as JSON)
    loads: Mapped[Dict[str, Any]] = mapped_column(
        JSON, nullable=False
    )  # heating, cooling, electrical, water
    equipment: Mapped[Dict[str, Any]] = mapped_column(
        JSON, nullable=False
    )  # equipment specifications
    distribution: Mapped[Dict[str, Any]] = mapped_column(
        JSON, nullable=False
    )  # ductwork, conduit, piping

    # Design results (stored as JSON)
    sizing_results: Mapped[Dict[str, Any]] = mapped_column(
        JSON, nullable=False
    )  # equipment sizes, pipe/duct sizes

    # Code compliance
    code_references: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON, nullable=True
    )  # NEC, IPC, IMC, NFPA references

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
        """String representation of MEPDesign."""
        return (
            f"<MEPDesign(id={self.id}, title='{self.title}', "
            f"system='{self.system_type}', status='{self.status}')>"
        )

    def __str__(self) -> str:
        """Human-readable string representation."""
        return f"{self.title} ({self.system_type}) - {self.status}"
