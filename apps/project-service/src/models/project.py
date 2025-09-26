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
from sqlalchemy.orm import Mapped, relationship
from src.core.config import settings
from src.infrastructure.database import Base

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

    id: Mapped[int] = Column(Integer, primary_key=True)
    name: Mapped[str] = Column(String(settings.MAX_PROJECT_NAME_LENGTH), nullable=False)
    description: Mapped[Optional[str]] = Column(Text, nullable=True)
    owner_id: Mapped[int] = Column(Integer, nullable=False)  # Reference to user ID in user service
    status: Mapped[str] = Column(
        String(50),
        nullable=False,
        default="draft",
        server_default="draft"
    )
    is_public: Mapped[bool] = Column(Boolean, default=False, server_default="false")
    is_archived: Mapped[bool] = Column(Boolean, default=False, server_default="false")
    version: Mapped[int] = Column(Integer, default=1, server_default="1")
    project_metadata: Mapped[dict] = Column(JSON, default=dict, server_default="{}")
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

    # Note: Relationships with User model are managed through the user service API
    # These relationships will be added when we implement comments and versioning
    # comments = relationship("Comment", back_populates="project", cascade="all, delete-orphan")
    # versions = relationship("ProjectVersion", back_populates="project", cascade="all, delete-orphan")

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