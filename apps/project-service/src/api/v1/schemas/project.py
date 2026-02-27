"""
Project API schemas.
"""

from datetime import datetime
from typing import Annotated, Dict, Optional

from pydantic import BaseModel, ConfigDict, Field

from ....core.config import settings


class ProjectBase(BaseModel):
    """Base schema for project data common to both input and output."""

    name: Annotated[
        str,
        Field(
            min_length=1,
            max_length=settings.MAX_PROJECT_NAME_LENGTH,
            examples=[
                "Sustainable Office Building",
                "Residential Complex Phase 1",
                "Green Energy Research Center",
                "Urban Planning Initiative",
            ],
        ),
    ]
    description: Optional[str] = Field(
        None,
        max_length=settings.MAX_PROJECT_DESCRIPTION_LENGTH,
        examples=[
            "A modern office building incorporating sustainable design principles and energy-efficient systems",
            "Multi-unit residential development with focus on affordable housing and community spaces",
            "Research facility dedicated to renewable energy technologies and sustainable practices",
            None,
        ],
    )
    is_public: bool = Field(False, examples=[True, False])


class ProjectCreate(ProjectBase):
    """Schema for creating a new project."""

    owner_id: int = Field(examples=[1, 5, 23, 42])


class ProjectUpdate(ProjectBase):
    """Schema for updating an existing project."""

    status: Annotated[
        str,
        Field(
            description="Project status",
            pattern=f"^({'|'.join(settings.ALLOWED_PROJECT_STATUSES)})$",
            examples=["active", "completed", "on_hold", "cancelled"],
        ),
    ]


class ProjectStatusUpdate(BaseModel):
    """Schema for updating just the project status."""

    status: Annotated[
        str,
        Field(
            description="Project status",
            pattern=f"^({'|'.join(settings.ALLOWED_PROJECT_STATUSES)})$",
            examples=["active", "completed", "on_hold", "cancelled"],
        ),
    ]


class Project(ProjectBase):
    """Schema for project responses."""

    id: int = Field(examples=[1, 15, 42, 123])
    owner_id: int = Field(examples=[1, 5, 23, 42])
    status: str = Field(examples=["active", "completed", "on_hold", "cancelled"])
    version: int = Field(examples=[1, 2, 5, 10])
    project_metadata: Dict = Field(
        default_factory=dict,
        examples=[
            {"budget": 500000, "timeline": "12 months"},
            {"location": "Downtown", "building_type": "commercial"},
            {},
        ],
    )
    created_at: datetime = Field(
        examples=["2024-01-15T10:30:00Z", "2024-02-20T14:45:30Z"]
    )
    updated_at: datetime = Field(
        examples=["2024-01-15T10:30:00Z", "2024-03-10T09:15:45Z"]
    )
    is_archived: bool = Field(examples=[True, False])

    model_config = ConfigDict(from_attributes=True)
