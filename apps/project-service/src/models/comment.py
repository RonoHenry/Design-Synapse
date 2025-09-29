"""Comment model definition."""

from datetime import datetime
from typing import Optional

from sqlalchemy import Column, DateTime, ForeignKey, Integer, Text, func
from sqlalchemy.orm import Mapped, relationship

from src.infrastructure.database import Base


class Comment(Base):
    """Comment model representing project comments in the system."""

    __tablename__ = "comments"

    id: Mapped[int] = Column(Integer, primary_key=True)
    content: Mapped[str] = Column(Text, nullable=False)
    author_id: Mapped[int] = Column(Integer, nullable=False)  # Reference to user ID in user service
    project_id: Mapped[int] = Column(
        Integer,
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False
    )
    parent_id: Mapped[Optional[int]] = Column(
        Integer,
        ForeignKey("comments.id", ondelete="CASCADE"),
        nullable=True
    )
    created_at: Mapped[datetime] = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    updated_at: Mapped[datetime] = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False
    )

    # Relationships
    project = relationship("Project", back_populates="comments")
    parent = relationship("Comment", remote_side=[id], backref="replies")  # self-referential relationship

    def __init__(self, **kwargs):
        """Initialize a comment."""
        # Validate required fields
        if "content" not in kwargs or not kwargs["content"].strip():
            raise ValueError("Comment content is required")
        if "author_id" not in kwargs:
            raise ValueError("Author ID is required")
        if "project_id" not in kwargs:
            raise ValueError("Project ID is required")

        super().__init__(**kwargs)