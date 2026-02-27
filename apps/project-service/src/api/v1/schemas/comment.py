"""Comment schemas for request/response validation."""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class CommentBase(BaseModel):
    """Base schema for comment data."""

    content: str = Field(
        ...,
        description="The content of the comment",
        examples=[
            "This design looks great! I especially like the sustainable features.",
            "We should consider adding more natural lighting to the main lobby area.",
            "The structural calculations need to be reviewed for the upper floors.",
            "Great work on the material selection for this project.",
        ],
    )
    parent_id: Optional[int] = Field(
        None,
        description="ID of the parent comment if this is a reply",
        examples=[1, 5, 15, None],
    )


class CommentCreate(CommentBase):
    """Schema for creating a new comment."""

    pass


class CommentUpdate(BaseModel):
    """Schema for updating an existing comment."""

    content: str = Field(
        ...,
        description="The updated content of the comment",
        examples=[
            "Updated: This design looks great! I especially like the sustainable features and the new lighting plan.",
            "Revised: We should consider adding more natural lighting to the main lobby area and the conference rooms.",
            "Updated: The structural calculations have been reviewed and approved for the upper floors.",
        ],
    )


class Comment(CommentBase):
    """Schema for comment responses."""

    id: int = Field(examples=[1, 15, 42, 123])
    author_id: int = Field(examples=[1, 5, 23, 42])
    project_id: int = Field(examples=[1, 8, 25, 67])
    created_at: datetime = Field(
        examples=["2024-01-15T10:30:00Z", "2024-02-20T14:45:30Z"]
    )
    updated_at: datetime = Field(
        examples=["2024-01-15T10:30:00Z", "2024-03-10T09:15:45Z"]
    )
    replies: List["Comment"] = []

    model_config = ConfigDict(from_attributes=True)


# Update forward reference for nested comments
Comment.model_rebuild()
