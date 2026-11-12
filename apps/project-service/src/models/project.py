"""Project model definition."""

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    JSON,
    String,
    Table,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, relationship, mapped_column
from ..core.config import settings
from ..infrastructure.database import Base

# Project collaborators association table
project_collaborators = Table(
    "project_collaborators",
    Base.metadata,
    Column("project_id", Integer, ForeignKey("projects.id", ondelete="CASCADE"), primary_key=True),
    Column("user_id", Integer, primary_key=True),  # Reference to user ID in user service
)


class Project(Base):
    """Project model representing design projects in the system."""

    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(settings.MAX_PROJECT_NAME_LENGTH), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    owner_id: Mapped[int] = mapped_column(Integer, nullable=False)  # Reference to user ID in user service
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="draft",
        server_default="draft"
    )
    is_public: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    version: Mapped[int] = mapped_column(Integer, default=1, server_default="1")
    project_metadata: Mapped[dict] = mapped_column(JSON, default=dict, server_default="{}")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False
    )

    # Note: Relationships with User model are managed through the user service API
    # Relationships
    comments: Mapped[list["Comment"]] = relationship("Comment", back_populates="project", cascade="all, delete-orphan")
    # versions: Mapped[list["ProjectVersion"]] = relationship("ProjectVersion", back_populates="project", cascade="all, delete-orphan")

    def __init__(self, **kwargs):
        """Initialize a project with defaults and validation."""
        # Set default status if not provided
        if "status" not in kwargs:
            kwargs["status"] = "draft"
        
        # Validate status
        if kwargs["status"] not in settings.ALLOWED_PROJECT_STATUSES:
            raise ValueError(f"Invalid status. Must be one of: {settings.ALLOWED_PROJECT_STATUSES}")

        # Validate name length
        if "name" in kwargs and len(kwargs["name"]) > settings.MAX_PROJECT_NAME_LENGTH:
            raise ValueError(
                f"Project name cannot exceed {settings.MAX_PROJECT_NAME_LENGTH} characters"
            )

        # Set default values for other fields
        kwargs.setdefault("is_public", False)
        kwargs.setdefault("is_archived", False)
        kwargs.setdefault("version", 1)
        kwargs.setdefault("project_metadata", {})
        
        super().__init__(**kwargs)