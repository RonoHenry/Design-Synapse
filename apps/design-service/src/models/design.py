"""
Design model for storing architectural designs.

This model represents the core design entity with support for:
- AI-generated design specifications
- Version control and design history
- Building metadata and compliance tracking
- Relationships with validations, optimizations, files, and comments
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
)
import re
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..infrastructure.database import Base

if TYPE_CHECKING:
    from .design_validation import DesignValidation
    from .design_optimization import DesignOptimization
    from .design_file import DesignFile
    from .design_comment import DesignComment


class Design(Base):
    """
    Design model representing architectural designs in the system.
    
    Supports AI-generated designs, version control, validation, and optimization.
    """

    __tablename__ = "designs"

    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    
    # Foreign keys
    project_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    
    # Basic information
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Design specification (structured JSON)
    specification: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)

    # Metadata
    building_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    total_area: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    num_floors: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    materials: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)

    # AI generation metadata
    generation_prompt: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    confidence_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    ai_model_version: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Version control
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    parent_design_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("designs.id"),
        nullable=True
    )

    # Status and compliance
    status: Mapped[str] = mapped_column(
        String(50),
        default="draft",
        nullable=False,
        index=True
    )
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")

    # Visual output fields
    floor_plan_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    rendering_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    model_file_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    visual_generation_status: Mapped[str] = mapped_column(
        String(50),
        default="not_requested",
        nullable=False,
        index=True
    )
    visual_generation_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    visual_generated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Audit fields
    created_by: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # Relationships (will be added as related models are implemented)
    validations: Mapped[List["DesignValidation"]] = relationship(
        "DesignValidation",
        back_populates="design",
        cascade="all, delete-orphan"
    )
    optimizations: Mapped[List["DesignOptimization"]] = relationship(
        "DesignOptimization",
        back_populates="design",
        cascade="all, delete-orphan"
    )
    files: Mapped[List["DesignFile"]] = relationship(
        "DesignFile",
        back_populates="design",
        cascade="all, delete-orphan"
    )
    comments: Mapped[List["DesignComment"]] = relationship(
        "DesignComment",
        back_populates="design",
        cascade="all, delete-orphan"
    )
    versions: Mapped[List["Design"]] = relationship(
        "Design",
        backref="parent_design",
        remote_side=[id]
    )

    # Allowed status values
    ALLOWED_STATUSES = ["draft", "validated", "compliant", "non_compliant"]
    ALLOWED_VISUAL_STATUSES = ["not_requested", "pending", "processing", "completed", "failed"]

    def __init__(
        self,
        project_id: Optional[int] = None,
        name: Optional[str] = None,
        specification: Optional[Dict[str, Any]] = None,
        building_type: Optional[str] = None,
        created_by: Optional[int] = None,
        user_id: Optional[int] = None,  # Alias for created_by
        description: Optional[str] = None,
        total_area: Optional[float] = None,
        num_floors: Optional[int] = None,
        materials: Optional[List[str]] = None,
        generation_prompt: Optional[str] = None,
        confidence_score: Optional[float] = None,
        ai_model_version: Optional[str] = None,
        version: int = 1,
        parent_design_id: Optional[int] = None,
        status: str = "draft",
        is_archived: bool = False,
        floor_plan_url: Optional[str] = None,
        rendering_url: Optional[str] = None,
        model_file_url: Optional[str] = None,
        visual_generation_status: str = "not_requested",
        visual_generation_error: Optional[str] = None,
        visual_generated_at: Optional[datetime] = None,
    ):
        """
        Initialize a new design.

        Args:
            project_id: ID of the project this design belongs to
            name: Name of the design
            specification: JSON specification of the design
            building_type: Type of building (residential, commercial, etc.)
            created_by: ID of the user who created the design
            user_id: Alias for created_by (for backward compatibility)
            description: Optional description of the design
            total_area: Optional total area in square meters
            num_floors: Optional number of floors
            materials: Optional list of materials
            generation_prompt: Optional AI generation prompt
            confidence_score: Optional AI confidence score (0-100)
            ai_model_version: Optional AI model version used
            version: Version number (default: 1)
            parent_design_id: Optional parent design ID for versioning
            status: Design status (default: "draft")
            is_archived: Whether the design is archived (default: False)
            floor_plan_url: Optional URL to floor plan image
            rendering_url: Optional URL to 3D rendering image
            model_file_url: Optional URL to 3D model file
            visual_generation_status: Visual generation status (default: "pending")
            visual_generation_error: Optional error message from visual generation
            visual_generated_at: Optional timestamp when visuals were generated

        Raises:
            ValueError: If validation fails
        """
        # Validate name if provided
        if name is not None:
            if not name or len(name.strip()) == 0:
                raise ValueError("Design name cannot be empty")
            if len(name) > 255:
                raise ValueError("Design name cannot exceed 255 characters")

        # Validate status
        if status not in self.ALLOWED_STATUSES:
            raise ValueError(
                f"Status must be one of: {', '.join(self.ALLOWED_STATUSES)}"
            )
        
        # Validate visual generation status
        if visual_generation_status not in self.ALLOWED_VISUAL_STATUSES:
            raise ValueError(
                f"Invalid visual generation status: {visual_generation_status}. "
                f"Must be one of: {', '.join(self.ALLOWED_VISUAL_STATUSES)}"
            )

        # Handle user_id alias for created_by
        if user_id is not None and created_by is None:
            created_by = user_id
        elif user_id is not None and created_by is not None:
            raise ValueError("Cannot specify both user_id and created_by")

        # Set fields (SQLAlchemy will enforce NOT NULL constraints at commit time)
        if project_id is not None:
            self.project_id = project_id
        if name is not None:
            self.name = name
        if specification is not None:
            self.specification = specification
        if building_type is not None:
            self.building_type = building_type
        if created_by is not None:
            self.created_by = created_by
            
        self.description = description
        self.total_area = total_area
        self.num_floors = num_floors
        self.materials = materials
        self.generation_prompt = generation_prompt
        self.confidence_score = confidence_score
        self.ai_model_version = ai_model_version
        self.version = version
        self.parent_design_id = parent_design_id
        self.status = status
        self.is_archived = is_archived
        
        # Visual fields
        self.floor_plan_url = floor_plan_url
        self.rendering_url = rendering_url
        self.model_file_url = model_file_url
        self.visual_generation_status = visual_generation_status
        self.visual_generation_error = visual_generation_error
        self.visual_generated_at = visual_generated_at
        
        self.created_at = datetime.now(timezone.utc)
        self.updated_at = self.created_at

    def validate_visual_urls(self) -> None:
        """
        Validate URL format for visual fields.
        
        Raises:
            ValueError: If any URL has invalid format
        """
        url_pattern = re.compile(
            r'^https?://'  # http:// or https://
            r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
            r'localhost|'  # localhost...
            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
            r'(?::\d+)?'  # optional port
            r'(?:/?|[/?]\S+)$', re.IGNORECASE)
        
        urls_to_check = [
            ("floor_plan_url", self.floor_plan_url),
            ("rendering_url", self.rendering_url),
            ("model_file_url", self.model_file_url)
        ]
        
        for field_name, url in urls_to_check:
            if url is not None and not url_pattern.match(url):
                raise ValueError(f"Invalid URL format for {field_name}: {url}")

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert design to dictionary for serialization.
        
        Returns:
            Dictionary representation of the design
        """
        return {
            "id": self.id,
            "project_id": self.project_id,
            "name": self.name,
            "description": self.description,
            "specification": self.specification,
            "building_type": self.building_type,
            "total_area": self.total_area,
            "num_floors": self.num_floors,
            "materials": self.materials,
            "generation_prompt": self.generation_prompt,
            "confidence_score": self.confidence_score,
            "ai_model_version": self.ai_model_version,
            "version": self.version,
            "parent_design_id": self.parent_design_id,
            "status": self.status,
            "is_archived": self.is_archived,
            "floor_plan_url": self.floor_plan_url,
            "rendering_url": self.rendering_url,
            "model_file_url": self.model_file_url,
            "visual_generation_status": self.visual_generation_status,
            "visual_generation_error": self.visual_generation_error,
            "visual_generated_at": self.visual_generated_at,
            "created_by": self.created_by,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }

    def __repr__(self) -> str:
        """String representation of the design."""
        return (
            f"<Design(id={self.id}, name='{self.name}', "
            f"version={self.version}, status='{self.status}', "
            f"visual_status='{self.visual_generation_status}')>"
        )
