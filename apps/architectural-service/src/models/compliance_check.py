"""ComplianceCheck model for building code compliance."""

from datetime import datetime
from typing import TYPE_CHECKING, Optional
from uuid import uuid4

from sqlalchemy import (JSON, Boolean, Column, DateTime, ForeignKey, Index,
                        String)
from sqlalchemy.dialects.mysql import CHAR
from sqlalchemy.orm import Mapped, relationship
from src.core.database import Base

if TYPE_CHECKING:
    from src.models.design import Design


def generate_uuid() -> str:
    """Generate UUID as string for TiDB/MySQL compatibility."""
    return str(uuid4())


class ComplianceCheck(Base):
    """
    Building code compliance check results.

    Stores results of automated compliance checking against
    building codes and standards.
    """

    __tablename__ = "compliance_checks"

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

    # Version association
    design_version = Column(
        String(20), nullable=False, comment="Design version that was checked"
    )

    # Check configuration
    code_standards = Column(
        JSON,
        nullable=False,
        comment="List of code standards checked (e.g., ['IBC-2021', 'ADA'])",
    )
    jurisdiction = Column(
        String(100), nullable=True, comment="Jurisdiction for local code requirements"
    )

    # Check status
    status = Column(
        String(50),
        nullable=False,
        default="pending",
        comment="Check status (pending, in_progress, completed, failed)",
    )
    passed = Column(
        Boolean,
        nullable=True,
        comment="Overall pass/fail status (null if not completed)",
    )

    # Results
    violations = Column(
        JSON, nullable=False, default=list, comment="List of code violations found"
    )
    warnings = Column(
        JSON,
        nullable=False,
        default=list,
        comment="List of warnings (non-critical issues)",
    )
    recommendations = Column(
        JSON,
        nullable=False,
        default=list,
        comment="List of recommendations for improvement",
    )

    # Report
    report_url = Column(
        String(500), nullable=True, comment="URL to detailed compliance report"
    )

    # Timestamps
    started_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        comment="Check start timestamp",
    )
    completed_at = Column(DateTime, nullable=True, comment="Check completion timestamp")

    # Relationship to design
    design: Mapped["Design"] = relationship(
        "Design", back_populates="compliance_checks"
    )

    # Table arguments for indexes
    __table_args__ = (
        Index("idx_design_compliance", "design_id", "status"),
        Index("idx_compliance_status", "status"),
        Index("idx_compliance_started", "started_at"),
        {"comment": "Building code compliance check results"},
    )

    def __repr__(self) -> str:
        """String representation."""
        return (
            f"<ComplianceCheck(id={self.id}, design_id={self.design_id}, "
            f"status={self.status}, passed={self.passed})>"
        )
