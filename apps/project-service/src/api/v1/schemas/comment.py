"""Comment schemas for request/response validation."""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class CommentBase(BaseModel):
    """Base schema for comment data."""

    content: str = Field(..., description="The content of the comment")
    parent_id: Optional[int] = Field(None, description="ID of the parent comment if this is a reply")


class CommentCreate(CommentBase):
    """Schema for creating a new comment."""

    pass


class CommentUpdate(BaseModel):
    """Schema for updating an existing comment."""

    content: str = Field(..., description="The updated content of the comment")


class Comment(CommentBase):
    """Schema for comment responses."""

    id: int
    author_id: int
    project_id: int
    created_at: datetime
    updated_at: datetime
    replies: List["Comment"] = []

    class Config:
        """Pydantic model config."""

        from_attributes = True


# Update forward reference for nested comments
Comment.model_rebuild()