"""Schemas for knowledge resource management."""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field, HttpUrl, ConfigDict


class TopicBase(BaseModel):
    """Base schema for topics."""
    
    name: str = Field(..., description="The name of the topic")
    description: str = Field(..., description="Description of the topic")
    parent_id: Optional[int] = Field(None, description="ID of the parent topic")


class TopicCreate(TopicBase):
    """Schema for creating a new topic."""
    pass


class TopicUpdate(TopicBase):
    """Schema for updating a topic."""
    pass


class Topic(TopicBase):
    """Schema for topic responses."""
    
    id: int
    children: List["Topic"] = []

    model_config = ConfigDict(from_attributes=True)


class ResourceBase(BaseModel):
    """Base schema for resources."""
    
    title: str = Field(..., description="The title of the resource")
    description: str = Field(..., description="Description of the resource")
    content_type: str = Field(..., description="Type of content (pdf, html, etc.)")
    source_url: HttpUrl = Field(..., description="URL where the resource was found")
    source_platform: str = Field(..., description="Platform where resource was found")
    author: Optional[str] = Field(None, description="Author of the resource")
    publication_date: Optional[datetime] = Field(None, description="Publication date")
    doi: Optional[str] = Field(None, description="Digital Object Identifier")
    license_type: str = Field(..., description="License type of the resource")
    topic_ids: List[int] = Field(..., description="IDs of associated topics")


class ResourceCreate(ResourceBase):
    """Schema for creating a new resource."""
    pass


class ResourceUpdate(BaseModel):
    """Schema for updating a resource."""
    
    title: Optional[str] = None
    description: Optional[str] = None
    author: Optional[str] = None
    publication_date: Optional[datetime] = None
    doi: Optional[str] = None
    license_type: Optional[str] = None
    topic_ids: Optional[List[int]] = None


class Resource(ResourceBase):
    """Schema for resource responses."""
    
    id: int
    summary: Optional[str] = None
    key_takeaways: Optional[List[str]] = None
    keywords: Optional[List[str]] = None
    file_size: int
    created_at: datetime
    updated_at: datetime
    topics: List[Topic] = []

    model_config = ConfigDict(from_attributes=True)


class BookmarkBase(BaseModel):
    """Base schema for bookmarks."""
    
    resource_id: int = Field(..., description="ID of the bookmarked resource")
    notes: Optional[str] = Field(None, description="User notes about the resource")


class BookmarkCreate(BookmarkBase):
    """Schema for creating a new bookmark."""
    pass


class BookmarkUpdate(BaseModel):
    """Schema for updating a bookmark."""
    
    notes: Optional[str] = None


class Bookmark(BookmarkBase):
    """Schema for bookmark responses."""
    
    id: int
    user_id: int
    created_at: datetime
    resource: Resource

    model_config = ConfigDict(from_attributes=True)


class CitationBase(BaseModel):
    """Base schema for citations."""
    
    resource_id: int = Field(..., description="ID of the cited resource")
    project_id: int = Field(..., description="ID of the project where resource is cited")
    context: str = Field(..., description="Context where resource is cited")


class CitationCreate(CitationBase):
    """Schema for creating a new citation."""
    pass


class Citation(CitationBase):
    """Schema for citation responses."""
    
    id: int
    created_at: datetime
    created_by: int
    resource: Resource

    model_config = ConfigDict(from_attributes=True)


# Update forward references
Topic.model_rebuild()