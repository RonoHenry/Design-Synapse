"""Design model for architectural documents."""

from datetime import datetime
from typing import TYPE_CHECKING, List, Optional
from uuid import uuid4

from sqlalchemy import (JSON, BigInteger, Boolean, Column, DateTime, Index,
                        Integer, String, Text)
from sqlalchemy.dialects.mysql import CHAR
from sqlalchemy.orm import Mapped, mapped_column, relationship
from src.core.database import Base

if TYPE_CHECKING:
    from src.models.compliance_check import ComplianceCheck
    from src.models.design_version import DesignVersion
    from src.models.drawing import Drawing
    from src.models.material_specification import MaterialSpecification
    from src.models.structural_analysis import StructuralAnalysis


def generate_uuid() -> str:
    """Generate UUID as string for TiDB/MySQL compatibility."""
    return str(uuid4())


class Design(Base):
    """
    Main architectural design document.

    Represents a complete architectural design with version control,
    status tracking, and relationships to drawings, materials, and analyses.
    """

    __tablename__ = "designs"

    # Primary key - using CHAR(36) for UUID compatibility with TiDB/MySQL
    id = Column(CHAR(36), primary_key=True, default=generate_uuid, nullable=False)

    # Project association
    project_id = Column(
        CHAR(36), nullable=False, index=True, comment="Associated project ID"
    )

    # Basic information
    name = Column(String(255), nullable=False, comment="Design document name")
    description = Column(Text, nullable=True, comment="Design description")
    building_type = Column(
        String(50),
        nullable=False,
        comment="Building type (residential, commercial, industrial, etc.)",
    )

    # Location data stored as JSON
    location_data = Column(
        JSON,
        nullable=False,
        comment="Location information including address, coordinates, jurisdiction",
    )

    # Version control fields
    current_version = Column(
        String(20),
        nullable=False,
        default="1.0",
        comment="Current version string (e.g., '1.0', '2.0')",
    )
    version_number = Column(
        Integer,
        nullable=False,
        default=1,
        comment="Numeric version for optimistic locking",
    )

    # Status tracking
    status = Column(
        String(50),
        nullable=False,
        default="draft",
        comment="Design status (draft, in_review, approved, archived)",
    )
    is_deleted = Column(
        Boolean, nullable=False, default=False, index=True, comment="Soft delete flag"
    )

    # Metadata stored as JSON
    design_metadata = Column(
        JSON,
        nullable=False,
        default=dict,
        comment="Additional metadata and custom fields",
    )

    # Audit fields
    created_by = Column(
        CHAR(36), nullable=False, comment="User ID who created the design"
    )
    created_at = Column(
        DateTime, nullable=False, default=datetime.utcnow, comment="Creation timestamp"
    )
    updated_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        comment="Last update timestamp",
    )
    deleted_at = Column(DateTime, nullable=True, comment="Soft delete timestamp")

    # Relationships (using string references to avoid circular imports)
    versions: Mapped[List["DesignVersion"]] = relationship(
        "DesignVersion",
        back_populates="design",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    drawings: Mapped[List["Drawing"]] = relationship(
        "Drawing",
        back_populates="design",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    materials: Mapped[List["MaterialSpecification"]] = relationship(
        "MaterialSpecification",
        back_populates="design",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    compliance_checks: Mapped[List["ComplianceCheck"]] = relationship(
        "ComplianceCheck",
        back_populates="design",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    structural_analyses: Mapped[List["StructuralAnalysis"]] = relationship(
        "StructuralAnalysis",
        back_populates="design",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    # Table arguments for indexes
    __table_args__ = (
        Index("idx_design_project", "project_id"),
        Index("idx_design_deleted", "is_deleted"),
        Index("idx_design_status", "status"),
        Index("idx_design_created", "created_at"),
        {"comment": "Architectural design documents with version control"},
    )

    def __repr__(self) -> str:
        """String representation."""
        return (
            f"<Design(id={self.id}, name={self.name}, "
            f"version={self.current_version}, status={self.status})>"
        )
