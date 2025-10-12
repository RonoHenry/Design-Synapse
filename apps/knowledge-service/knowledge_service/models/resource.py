"""Knowledge resource models."""

from datetime import datetime
from typing import Dict, List, Optional
import re
from sqlalchemy import Column, DateTime, ForeignKey, Integer, JSON, String, Table, event, CheckConstraint, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, relationship, mapped_column, validates

from ..infrastructure.database import Base

# Association table for resource-topic relationship
resource_topics = Table(
    'resource_topics',
    Base.metadata,
    Column('resource_id', Integer, ForeignKey('resources.id'), primary_key=True),
    Column('topic_id', Integer, ForeignKey('topics.id'), primary_key=True),
    extend_existing=True
)

class Resource(Base):
    __table_args__ = {'extend_existing': True}
    """Model for knowledge resources (papers, articles, etc.)."""
    
    __tablename__ = "resources"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(String(1000), nullable=False)
    content_type: Mapped[str] = mapped_column(String(50), nullable=False)  # pdf, html, etc.
    source_url: Mapped[str] = mapped_column(String(500), nullable=False)
    source_platform: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)  # SSRN, MDPI, etc.
    vector_embedding: Mapped[Optional[Dict]] = mapped_column(JSON, nullable=True)
    
    # Additional metadata
    author: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    publication_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    doi: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    license_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    # Generated content
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    key_takeaways: Mapped[Optional[List]] = mapped_column(JSON, nullable=True)
    keywords: Mapped[Optional[List]] = mapped_column(JSON, nullable=True)
    
    # Storage info
    storage_path: Mapped[str] = mapped_column(String(500), nullable=False)
    file_size: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # in bytes
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, 
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )

    # Relationships
    topics: Mapped[List["Topic"]] = relationship(
        "Topic",
        secondary=resource_topics,
        back_populates="resources"
    )
    bookmarks: Mapped[List["Bookmark"]] = relationship("Bookmark", back_populates="resource", cascade="all, delete-orphan")
    citations: Mapped[List["Citation"]] = relationship("Citation", back_populates="resource", cascade="all, delete-orphan")

    @validates('source_url')
    def validate_url(self, key, url):
        """Validate URL format."""
        if not url:
            return url
        url_pattern = re.compile(
            r'^https?://'  # http:// or https://
            r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
            r'localhost|'  # localhost...
            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
            r'(?::\d+)?'  # optional port
            r'(?:/?|[/?]\S+)$',  # path
            re.IGNORECASE)
        if not url_pattern.match(url):
            raise ValueError(f"Invalid URL format: {url}")
        return url

    @validates('file_size')
    def validate_file_size(self, key, size):
        """Validate file size is non-negative."""
        if size is not None and size < 0:
            raise ValueError("File size cannot be negative")
        return size

    def __repr__(self):
        """String representation."""
        return f"<Resource {self.id}: {self.title}>"


class Topic(Base):
    __table_args__ = {'extend_existing': True}
    """Model for knowledge topics/categories."""
    
    __tablename__ = "topics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    parent_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("topics.id"),
        nullable=True
    )
    
    # Self-referential relationship for hierarchical topics
    children: Mapped[List["Topic"]] = relationship("Topic")
    resources: Mapped[List["Resource"]] = relationship(
        "Resource",
        secondary=resource_topics,
        back_populates="topics"
    )

    def __repr__(self):
        """String representation."""
        return f"<Topic {self.id}: {self.name}>"


class Citation(Base):
    __table_args__ = {'extend_existing': True}
    """Model for resource citations in projects."""
    
    __tablename__ = "citations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    resource_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("resources.id", ondelete="CASCADE"),
        nullable=False
    )
    project_id: Mapped[int] = mapped_column(Integer, nullable=False)  # Foreign key to project service
    context: Mapped[str] = mapped_column(Text, nullable=False)  # Where/how it's cited
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    created_by: Mapped[int] = mapped_column(Integer, nullable=False, default=1)  # User who created the citation
    
    resource: Mapped["Resource"] = relationship("Resource", back_populates="citations")

    def __repr__(self):
        """String representation."""
        return f"<Citation {self.id}: Resource {self.resource_id} in Project {self.project_id}>"