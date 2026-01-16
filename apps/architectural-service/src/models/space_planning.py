"""SpacePlanning model for space planning analysis."""

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


class SpacePlanning(Base):
    """
    Space planning analysis results.

    Stores results of space planning and layout optimization
    including metrics, recommendations, and space programs.
    """

    __tablename__ = "space_planning"

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

    # Analysis status
    status = Column(
        String(50),
        nullable=False,
        default="pending",
        comment="Analysis status (pending, in_progress, completed, failed)",
    )

    # Input requirements
    requirements = Column(
        JSON, nullable=False, comment="Space requirements and constraints"
    )

    # Results
    recommendations = Column(
        JSON, nullable=False, default=list, comment="Layout recommendations"
    )
    metrics = Column(
        JSON,
        nullable=False,
        default=dict,
        comment="Space utilization metrics (area efficiency, circulation, density)",
    )
    space_program = Column(
        JSON,
        nullable=False,
        default=dict,
        comment="Space program document with areas and relationships",
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

    # Table arguments for indexes
    __table_args__ = (
        Index("idx_design_space_planning", "design_id", "status"),
        Index("idx_space_planning_status", "status"),
        {"comment": "Space planning analysis results"},
    )

    def __repr__(self) -> str:
        """String representation."""
        return (
            f"<SpacePlanning(id={self.id}, design_id={self.design_id}, "
            f"status={self.status})>"
        )
