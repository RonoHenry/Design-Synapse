"""
Project API schemas.
"""

from datetime import datetime
from typing import Dict, Optional

from pydantic import BaseModel, Field, constr

from src.core.config import settings


class ProjectBase(BaseModel):
    """Base schema for project data common to both input and output."""

    name: constr(min_length=1, max_length=settings.MAX_PROJECT_NAME_LENGTH)
    description: Optional[str] = Field(None, max_length=settings.MAX_PROJECT_DESCRIPTION_LENGTH)
    is_public: bool = False


class ProjectCreate(ProjectBase):
    """Schema for creating a new project."""

    owner_id: int


class ProjectUpdate(ProjectBase):
    """Schema for updating an existing project."""

    status: str = Field(
        ...,  # Required field
        description="Project status",
        pattern=f"^({'|'.join(settings.ALLOWED_PROJECT_STATUSES)})$"
    )


class ProjectStatusUpdate(BaseModel):
    """Schema for updating just the project status."""

    status: str = Field(
        ...,  # Required field
        description="Project status",
        pattern=f"^({'|'.join(settings.ALLOWED_PROJECT_STATUSES)})$"
    )


class Project(ProjectBase):
    """Schema for project responses."""

    id: int
    owner_id: int
    status: str
    version: int
    project_metadata: Dict = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime
    is_archived: bool

    class Config:
        """Pydantic configuration."""

        from_attributes = True  # Allow converting SQLAlchemy model to Pydantic model