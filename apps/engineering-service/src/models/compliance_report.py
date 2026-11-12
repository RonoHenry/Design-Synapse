"""ComplianceReport model for storing code compliance verification results."""

from datetime import datetime
from typing import Any, Dict, Optional

from sqlalchemy import (JSON, Column, DateTime, ForeignKey, Integer, String,
                        Text)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..core.database import Base


class ComplianceReport(Base):
    """Model for storing code compliance reports.

    Compliance reports document verification of designs against
    applicable building codes and standards.
    """

    __tablename__ = "compliance_reports"

    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Link to calculation sheet
    calculation_sheet_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("calculation_sheets.id"), nullable=True, index=True
    )

    # Project association
    project_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)

    # Report metadata
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Code information
    code_type: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True
    )  # structural, mep, energy, fire
    jurisdiction: Mapped[str] = mapped_column(String(100), nullable=False)
    code_version: Mapped[str] = mapped_column(String(50), nullable=False)

    # Compliance results (stored as JSON)
    checks_performed: Mapped[Dict[str, Any]] = mapped_column(
        JSON, nullable=False
    )  # list of checks with results
    violations: Mapped[Dict[str, Any]] = mapped_column(
        JSON, nullable=False
    )  # code violations found
    recommendations: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON, nullable=True
    )  # suggested corrections

    # Overall status
    overall_status: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # compliant, non_compliant, review_required

    # Audit fields
    generated_by: Mapped[str] = mapped_column(String(255), nullable=False)
    generated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )
    reviewed_by: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    def __repr__(self) -> str:
        """String representation of ComplianceReport."""
        return (
            f"<ComplianceReport(id={self.id}, code_type='{self.code_type}', "
            f"status='{self.overall_status}')>"
        )

    def __str__(self) -> str:
        """Human-readable string representation."""
        return (
            f"{self.title} - {self.code_type} "
            f"({self.jurisdiction}) - {self.overall_status}"
        )
