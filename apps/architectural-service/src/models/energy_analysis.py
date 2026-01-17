"""EnergyAnalysis model for energy efficiency analysis."""

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


class EnergyAnalysis(Base):
    """
    Energy efficiency analysis results.

    Stores results of energy efficiency analysis including
    envelope performance, consumption estimates, and recommendations.
    """

    __tablename__ = "energy_analyses"

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
    standards = Column(
        JSON,
        nullable=False,
        comment="List of energy standards (e.g., ['ASHRAE-90.1', 'LEED'])",
    )
    climate_zone = Column(
        String(50), nullable=False, comment="Climate zone for analysis"
    )

    # Analysis status
    status = Column(
        String(50),
        nullable=False,
        default="pending",
        comment="Analysis status (pending, in_progress, completed, failed)",
    )

    # Results
    envelope_performance = Column(
        JSON,
        nullable=False,
        default=dict,
        comment="Building envelope performance (R-values, U-factors)",
    )
    energy_consumption = Column(
        JSON,
        nullable=False,
        default=dict,
        comment="Estimated annual energy consumption",
    )
    recommendations = Column(
        JSON,
        nullable=False,
        default=list,
        comment="Recommendations for efficiency improvements",
    )

    # Certificate
    certificate_url = Column(
        String(500), nullable=True, comment="URL to energy performance certificate"
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
        Index("idx_design_energy", "design_id", "status"),
        Index("idx_energy_status", "status"),
        {"comment": "Energy efficiency analysis results"},
    )

    def __repr__(self) -> str:
        """String representation."""
        return (
            f"<EnergyAnalysis(id={self.id}, design_id={self.design_id}, "
            f"status={self.status})>"
        )
