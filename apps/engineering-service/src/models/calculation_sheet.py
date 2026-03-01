"""CalculationSheet model for storing engineering calculations."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import JSON, Column, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..core.database import Base


class CalculationSheet(Base):
    """Model for storing engineering calculation sheets.

    Calculation sheets store inputs, outputs, formulas, and metadata
    for engineering calculations across all disciplines (structural, MEP, civil).
    """

    __tablename__ = "calculation_sheets"

    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Project association
    project_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)

    # Calculation metadata
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    calculation_type: Mapped[str] = mapped_column(
        String(100), nullable=False, index=True
    )  # structural, mep, civil

    # Calculation data (stored as JSON)
    inputs: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)
    outputs: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)
    formulas: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)
    references: Mapped[Optional[List[str]]] = mapped_column(
        JSON, nullable=True
    )  # Code references

    # Units system
    units: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True, default="imperial"
    )  # imperial or metric

    # Versioning
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    parent_id: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True, index=True
    )  # For version history

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

    # Status
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="draft"
    )  # draft, approved, archived

    def __repr__(self) -> str:
        """String representation of CalculationSheet."""
        return (
            f"<CalculationSheet(id={self.id}, title='{self.title}', "
            f"type='{self.calculation_type}', version={self.version})>"
        )

    def __str__(self) -> str:
        """Human-readable string representation."""
        return f"{self.title} ({self.calculation_type}) - v{self.version}"
