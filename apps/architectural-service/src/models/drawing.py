"""Drawing model for architectural drawings."""

from datetime import datetime
from typing import TYPE_CHECKING, Optional
from uuid import uuid4

from sqlalchemy import (JSON, BigInteger, Column, DateTime, ForeignKey, Index,
                        String)
from sqlalchemy.dialects.mysql import CHAR
from sqlalchemy.orm import Mapped, relationship
from src.core.database import Base

if TYPE_CHECKING:
    from src.models.design import Design


def generate_uuid() -> str:
    """Generate UUID as string for TiDB/MySQL compatibility."""
    return str(uuid4())


class Drawing(Base):
    """
    Architectural drawings (floor plans, elevations, sections, etc.).

    Stores metadata and file references for architectural drawings
    associated with design documents.
    """

    __tablename__ = "drawings"

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
        String(20), nullable=False, comment="Design version when drawing was added"
    )

    # Drawing type
    drawing_type = Column(
        String(50),
        nullable=False,
        comment="Type of drawing (floor_plan, elevation, section, site_plan, detail)",
    )

    # File information
    file_url = Column(
        String(500), nullable=False, comment="URL or path to the drawing file"
    )
    file_size = Column(BigInteger, nullable=False, comment="File size in bytes")
    mime_type = Column(String(100), nullable=False, comment="MIME type of the file")

    # Drawing metadata
    scale = Column(
        String(50), nullable=True, comment="Drawing scale (e.g., '1/4\"=1\\'', '1:100')"
    )
    sheet_number = Column(
        String(50), nullable=True, comment="Sheet number in drawing set"
    )
    drawing_metadata = Column(
        JSON, nullable=False, default=dict, comment="Additional drawing metadata"
    )

    # Audit fields
    created_by = Column(
        CHAR(36), nullable=False, comment="User ID who uploaded the drawing"
    )
    created_at = Column(
        DateTime, nullable=False, default=datetime.utcnow, comment="Upload timestamp"
    )

    # Relationship to design
    design: Mapped["Design"] = relationship("Design", back_populates="drawings")

    # Table arguments for indexes
    __table_args__ = (
        Index("idx_design_drawings", "design_id", "drawing_type"),
        Index("idx_drawing_type", "drawing_type"),
        Index("idx_drawing_created", "created_at"),
        {"comment": "Architectural drawings associated with designs"},
    )

    def __repr__(self) -> str:
        """String representation."""
        return (
            f"<Drawing(id={self.id}, design_id={self.design_id}, "
            f"type={self.drawing_type})>"
        )
