"""DesignComment model for comments and annotations on designs."""

from datetime import datetime, timezone
from typing import Optional, TYPE_CHECKING

from sqlalchemy import Boolean, Integer, Float, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.infrastructure.database import Base

if TYPE_CHECKING:
    from src.models.design import Design


class DesignComment(Base):
    """Comments and annotations on designs.
    
    Supports general comments and spatial annotations with optional
    3D coordinates for precise positioning on design elements.
    """
    __tablename__ = "design_comments"

    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    
    # Foreign key to Design
    design_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("designs.id", ondelete="CASCADE"),
        nullable=False
    )

    # Comment content
    content: Mapped[str] = mapped_column(Text, nullable=False)

    # Optional spatial positioning (for annotations on specific design elements)
    position_x: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    position_y: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    position_z: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Audit fields
    created_by: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    is_edited: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default="false",
        nullable=False
    )

    # Relationship
    design: Mapped["Design"] = relationship(
        "Design",
        back_populates="comments"
    )

    def __init__(
        self,
        design_id: Optional[int] = None,
        content: Optional[str] = None,
        created_by: Optional[int] = None,
        position_x: Optional[float] = None,
        position_y: Optional[float] = None,
        position_z: Optional[float] = None,
        is_edited: bool = False,
    ):
        """
        Initialize a new design comment.

        Args:
            design_id: ID of the design this comment belongs to
            content: Comment text content
            created_by: ID of the user who created the comment
            position_x: Optional X coordinate for spatial annotation
            position_y: Optional Y coordinate for spatial annotation
            position_z: Optional Z coordinate for spatial annotation
            is_edited: Whether the comment has been edited (default: False)

        Raises:
            ValueError: If validation fails
        """
        # Validate content
        if content is not None:
            if not content or len(content.strip()) == 0:
                raise ValueError("Comment content cannot be empty")

        # Set fields (SQLAlchemy will enforce NOT NULL constraints at commit time)
        if design_id is not None:
            self.design_id = design_id
        if content is not None:
            self.content = content
        if created_by is not None:
            self.created_by = created_by
        
        # Set optional spatial positioning
        self.position_x = position_x
        self.position_y = position_y
        self.position_z = position_z
        
        # Set audit fields
        self.is_edited = is_edited
        self.created_at = datetime.now(timezone.utc)
        self.updated_at = self.created_at

    def __repr__(self) -> str:
        """String representation of DesignComment."""
        return (
            f"<DesignComment(id={self.id}, "
            f"design_id={self.design_id}, "
            f"created_by={self.created_by}, "
            f"is_edited={self.is_edited})>"
        )
