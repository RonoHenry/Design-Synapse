"""DesignVersion model for version history."""

from datetime import datetime
from typing import TYPE_CHECKING, Optional
from uuid import uuid4

from sqlalchemy import (JSON, Column, DateTime, ForeignKey, Index, Integer,
                        String, Text, UniqueConstraint)
from sqlalchemy.dialects.mysql import CHAR
from sqlalchemy.orm import Mapped, relationship
from src.core.database import Base

if TYPE_CHECKING:
    from src.models.design import Design


def generate_uuid() -> str:
    """Generate UUID as string for TiDB/MySQL compatibility."""
    return str(uuid4())


class DesignVersion(Base):
    """
    Version history for design documents.

    Stores complete snapshots of design data at each version,
    enabling version retrieval and audit trail.
    """

    __tablename__ = "design_versions"

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

    # Version information
    version = Column(
        String(20), nullable=False, comment="Version string (e.g., '1.0', '2.0')"
    )
    version_number = Column(
        Integer, nullable=False, comment="Numeric version number for ordering"
    )

    # Snapshot of design data at this version
    design_data = Column(
        JSON, nullable=False, comment="Complete snapshot of design data at this version"
    )

    # Change information
    change_summary = Column(
        Text, nullable=True, comment="Summary of changes in this version"
    )

    # Audit fields
    created_by = Column(
        CHAR(36), nullable=False, comment="User ID who created this version"
    )
    created_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        comment="Version creation timestamp",
    )

    # Relationship to design
    design: Mapped["Design"] = relationship("Design", back_populates="versions")

    # Table arguments for indexes and constraints
    __table_args__ = (
        Index("idx_design_version", "design_id", "version"),
        Index("idx_design_version_number", "design_id", "version_number"),
        UniqueConstraint(
            "design_id", "version_number", name="uq_design_version_number"
        ),
        {"comment": "Version history for design documents"},
    )

    def __repr__(self) -> str:
        """String representation."""
        return (
            f"<DesignVersion(id={self.id}, design_id={self.design_id}, "
            f"version={self.version})>"
        )
