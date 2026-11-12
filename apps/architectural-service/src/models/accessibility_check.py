"""AccessibilityCheck model for accessibility compliance."""

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


class AccessibilityCheck(Base):
    """
    Accessibility compliance check results.

    Stores results of accessibility compliance checking against
    ADA, ANSI A117.1, and other accessibility standards.
    """

    __tablename__ = "accessibility_checks"

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
    standards = Column(
        JSON,
        nullable=False,
        comment="List of accessibility standards checked (e.g., ['ADA', 'ANSI-A117.1'])",
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
        JSON,
        nullable=False,
        default=list,
        comment="List of accessibility violations found",
    )
    accessible_routes = Column(
        JSON, nullable=False, default=list, comment="Validated accessible routes"
    )

    # Timestamps
    started_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        comment="Check start timestamp",
    )
    completed_at = Column(DateTime, nullable=True, comment="Check completion timestamp")

    # Table arguments for indexes
    __table_args__ = (
        Index("idx_design_accessibility", "design_id", "status"),
        Index("idx_accessibility_status", "status"),
        {"comment": "Accessibility compliance check results"},
    )

    def __repr__(self) -> str:
        """String representation."""
        return (
            f"<AccessibilityCheck(id={self.id}, design_id={self.design_id}, "
            f"status={self.status}, passed={self.passed})>"
        )
