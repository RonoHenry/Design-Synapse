"""Pydantic schemas for API request/response validation."""

from datetime import datetime
from typing import Annotated, List, Optional
from pydantic import BaseModel, Field, HttpUrl, ConfigDict, field_validator

class TopicBase(BaseModel):
    """Base schema for Topic."""
    name: Annotated[str, Field(min_length=1, max_length=100)]
    description: Annotated[str, Field(min_length=1, max_length=500)]
    parent_id: Optional[int] = None

class TopicCreate(TopicBase):
    """Schema for creating a Topic."""
    pass

class TopicUpdate(TopicBase):
    """Schema for updating a Topic."""
    pass

class TopicResponse(TopicBase):
    """Schema for Topic response."""
    id: int
    
    model_config = ConfigDict(from_attributes=True)

class ResourceBase(BaseModel):
    """Base schema for Resource."""
    title: Annotated[str, Field(min_length=1, max_length=255)]
    description: Annotated[str, Field(min_length=1, max_length=1000)]
    content_type: Annotated[str, Field(pattern=r'^(pdf|text|url|image)$')]
    source_url: HttpUrl
    source_platform: Optional[str] = None
    author: Optional[str] = None
    publication_date: Optional[datetime] = None
    doi: Optional[str] = None
    license_type: Optional[str] = None
    storage_path: Annotated[str, Field(min_length=1, max_length=500)]
    file_size: Optional[int] = None

    @field_validator('file_size')
    @classmethod
    def validate_file_size(cls, v):
        """Validate file size is non-negative."""
        if v is not None and v < 0:
            raise ValueError("File size cannot be negative")
        return v

class ResourceCreate(ResourceBase):
    """Schema for creating a Resource."""
    topic_ids: List[int] = Field(default_factory=list)

class ResourceUpdate(ResourceBase):
    """Schema for updating a Resource."""
    topic_ids: Optional[List[int]] = None

class ResourceResponse(ResourceBase):
    """Schema for Resource response."""
    id: int
    created_at: datetime
    updated_at: datetime
    topics: List[TopicResponse]
    vector_embedding: Optional[List[float]] = None

    model_config = ConfigDict(from_attributes=True)

class BookmarkBase(BaseModel):
    """Base schema for Bookmark."""
    resource_id: int
    notes: Optional[str] = None

class BookmarkCreate(BookmarkBase):
    """Schema for creating a Bookmark."""
    pass

class BookmarkResponse(BookmarkBase):
    """Schema for Bookmark response."""
    id: int
    user_id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class CitationBase(BaseModel):
    """Base schema for Citation."""
    resource_id: int
    project_id: int
    context: str

class CitationCreate(CitationBase):
    """Schema for creating a Citation."""
    pass

class CitationResponse(CitationBase):
    """Schema for Citation response."""
    id: int
    created_at: datetime
    created_by: int

    model_config = ConfigDict(from_attributes=True)