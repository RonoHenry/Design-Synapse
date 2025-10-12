"""API request and response schemas."""

from pydantic import BaseModel


class CitationCreate(BaseModel):
    """Schema for creating a citation."""
    resource_id: int
    project_id: int
    context: str


class BookmarkCreate(BaseModel):
    """Schema for creating a bookmark."""
    resource_id: int
    notes: str