"""StructuralAnalysis model for structural engineering analysis."""

from datetime import datetime
from typing import TYPE_CHECKING, Optional
from uuid import uuid4

from sqlalchemy import JSON, Column, DateTime, ForeignKey, Index, String
from sqlalchemy.dialects.mysql import CHAR
from sqlalchemy.orm import Mapped, relationship
from src.core.database import Base

if TYPE_CHECKING:
    from src.models.design import Design


def generate_uuid() -> str:
    """Generate UUID as string for TiDB/MySQL compatibility."""
    return str(uuid4())


class StructuralAnalysis(Base):
    """
    Structural analysis results.

    Stores results of structural engineering calculations
    including load analysis and structural integrity checks.
    """

    __tablename__ = "structural_analyses"

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
        String(20), nullable=False, comment="Design version that was analyzed"
    )

    # Analysis configuration
    structural_system = Column(
        String(100),
        nullable=False,
        comment="Structural system type (steel_frame, concrete, wood_frame, masonry)",
    )
    analysis_type = Column(
        String(50), nullable=False, comment="Type of analysis performed"
    )

    # Analysis status
    status = Column(
        String(50),
        nullable=False,
        default="pending",
        comment="Analysis status (pending, in_progress, completed, failed)",
    )

    # Results
    load_calculations = Column(
        JSON,
        nullable=False,
        default=dict,
        comment="Load calculations (dead, live, wind, seismic)",
    )
    issues = Column(
        JSON,
        nullable=False,
        default=list,
        comment="List of structural issues identified",
    )
    recommendations = Column(
        JSON,
        nullable=False,
        default=list,
        comment="List of recommendations for structural improvements",
    )

    # Report
    report_url = Column(
        String(500), nullable=True, comment="URL to detailed structural analysis report"
    )

    # Timestamps
    started_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        comment="Analysis start timestamp",
    )
    completed_at = Column(
        DateTime, nullable=True, comment="Analysis completion timestamp"
    )

    # Relationship to design
    design: Mapped["Design"] = relationship(
        "Design", back_populates="structural_analyses"
    )

    # Table arguments for indexes
    __table_args__ = (
        Index("idx_design_structural", "design_id", "status"),
        Index("idx_structural_status", "status"),
        Index("idx_structural_started", "started_at"),
        {"comment": "Structural analysis results"},
    )

    def __repr__(self) -> str:
        """String representation."""
        return (
            f"<StructuralAnalysis(id={self.id}, design_id={self.design_id}, "
            f"status={self.status})>"
        )
