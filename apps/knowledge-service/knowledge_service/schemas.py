"""Pydantic schemas for API request/response validation."""

from datetime import datetime
from typing import Annotated, List, Optional

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator


class TopicBase(BaseModel):
    """Base schema for Topic."""

    name: Annotated[
        str,
        Field(
            min_length=1,
            max_length=100,
            examples=[
                "Machine Learning",
                "Architecture",
                "Sustainable Design",
                "Building Codes",
            ],
        ),
    ]
    description: Annotated[
        str,
        Field(
            min_length=1,
            max_length=500,
            examples=[
                "Resources related to machine learning and AI applications",
                "Architectural design principles and methodologies",
                "Sustainable building practices and green technologies",
            ],
        ),
    ]
    parent_id: Optional[int] = Field(None, examples=[1, 5, None])


class TopicCreate(TopicBase):
    """Schema for creating a Topic."""

    pass


class TopicUpdate(TopicBase):
    """Schema for updating a Topic."""

    pass


class TopicResponse(TopicBase):
    """Schema for Topic response."""

    id: int = Field(examples=[1, 2, 15, 42])

    model_config = ConfigDict(from_attributes=True)


class ResourceBase(BaseModel):
    """Base schema for Resource."""

    title: Annotated[
        str,
        Field(
            min_length=1,
            max_length=255,
            examples=[
                "Sustainable Architecture Principles",
                "Machine Learning in Construction",
                "Building Code Compliance Guide",
                "Green Building Materials Research",
            ],
        ),
    ]
    description: Annotated[
        str,
        Field(
            min_length=1,
            max_length=1000,
            examples=[
                "A comprehensive guide to sustainable architecture principles and their practical applications in modern construction projects.",
                "Research paper exploring the use of machine learning algorithms for optimizing construction processes and material selection.",
                "Official documentation covering building code compliance requirements for commercial and residential projects.",
            ],
        ),
    ]
    content_type: Annotated[
        str,
        Field(
            pattern=r"^(pdf|text|url|image)$", examples=["pdf", "text", "url", "image"]
        ),
    ]
    source_url: HttpUrl = Field(
        examples=[
            "https://example.com/sustainable-architecture.pdf",
            "https://research.org/ml-construction-paper.pdf",
            "https://buildingcodes.gov/compliance-guide",
        ]
    )
    source_platform: Optional[str] = Field(
        None, examples=["ResearchGate", "ArXiv", "IEEE", "Government Portal", None]
    )
    author: Optional[str] = Field(
        None,
        examples=[
            "Dr. Jane Smith",
            "John Doe, P.E.",
            "Building Standards Committee",
            None,
        ],
    )
    publication_date: Optional[datetime] = Field(
        None, examples=["2024-01-15T00:00:00Z", "2023-12-20T00:00:00Z", None]
    )
    doi: Optional[str] = Field(
        None, examples=["10.1000/182", "10.1038/nature12373", None]
    )
    license_type: Optional[str] = Field(
        None, examples=["MIT", "Creative Commons", "Public Domain", "Proprietary", None]
    )
    storage_path: Annotated[
        str,
        Field(
            min_length=1,
            max_length=500,
            examples=[
                "/storage/resources/2024/01/sustainable-architecture.pdf",
                "/storage/resources/2024/02/ml-construction.pdf",
                "/storage/resources/2024/03/building-codes.pdf",
            ],
        ),
    ]
    file_size: Optional[int] = Field(None, examples=[1024000, 2048576, 512000, None])

    @field_validator("file_size")
    @classmethod
    def validate_file_size(cls, v):
        """Validate file size is non-negative."""
        if v is not None and v < 0:
            raise ValueError("File size cannot be negative")
        return v


class ResourceCreate(ResourceBase):
    """Schema for creating a Resource."""

    topic_ids: List[int] = Field(
        default_factory=list, examples=[[1, 3, 5], [2], [1, 2, 4, 7], []]
    )


class ResourceUpdate(ResourceBase):
    """Schema for updating a Resource."""

    topic_ids: Optional[List[int]] = Field(
        None, examples=[[1, 3, 5], [2], [1, 2, 4, 7], [], None]
    )


class ResourceResponse(ResourceBase):
    """Schema for Resource response."""

    id: int = Field(examples=[1, 42, 123, 456])
    created_at: datetime = Field(
        examples=["2024-01-15T10:30:00Z", "2024-02-20T14:45:30Z"]
    )
    updated_at: datetime = Field(
        examples=["2024-01-15T10:30:00Z", "2024-03-10T09:15:45Z"]
    )
    topics: List[TopicResponse]
    vector_embedding: Optional[List[float]] = Field(
        None, examples=[[0.1, 0.2, 0.3, 0.4, 0.5], [-0.1, 0.8, -0.3, 0.9, 0.2], None]
    )

    model_config = ConfigDict(from_attributes=True)


class BookmarkBase(BaseModel):
    """Base schema for Bookmark."""

    resource_id: int = Field(examples=[1, 42, 123])
    notes: Optional[str] = Field(
        None,
        examples=[
            "Important resource for project planning",
            "Reference for sustainable design principles",
            "Good example of ML applications",
            None,
        ],
    )


class BookmarkCreate(BookmarkBase):
    """Schema for creating a Bookmark."""

    pass


class BookmarkResponse(BookmarkBase):
    """Schema for Bookmark response."""

    id: int = Field(examples=[1, 15, 42])
    user_id: int = Field(examples=[1, 5, 23])
    created_at: datetime = Field(
        examples=["2024-01-15T10:30:00Z", "2024-02-20T14:45:30Z"]
    )

    model_config = ConfigDict(from_attributes=True)


class CitationBase(BaseModel):
    """Base schema for Citation."""

    resource_id: int = Field(examples=[1, 42, 123])
    project_id: int = Field(examples=[1, 15, 67])
    context: str = Field(
        examples=[
            "This resource provides the foundation for our sustainable design approach",
            "Referenced for building code compliance requirements in section 3.2",
            "Used as basis for material selection criteria",
        ]
    )


class CitationCreate(CitationBase):
    """Schema for creating a Citation."""

    pass


class CitationResponse(CitationBase):
    """Schema for Citation response."""

    id: int = Field(examples=[1, 25, 78])
    created_at: datetime = Field(
        examples=["2024-01-15T10:30:00Z", "2024-02-20T14:45:30Z"]
    )
    created_by: int = Field(examples=[1, 5, 23])

    model_config = ConfigDict(from_attributes=True)
