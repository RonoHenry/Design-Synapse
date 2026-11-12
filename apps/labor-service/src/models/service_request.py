"""
ServiceRequest Model - Labor Services Marketplace

This module implements the ServiceRequest model following TDD principles.
The model represents job postings from clients seeking labor services.
"""

from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional

from sqlalchemy import JSON, Boolean, Column, DateTime
from sqlalchemy import Enum as SQLEnum
from sqlalchemy import ForeignKey, Index, Integer, Numeric, String, Text
from sqlalchemy.orm import relationship, validates

from .base import Base


class UrgencyLevel(str, Enum):
    """Enumeration for service request urgency levels."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    EMERGENCY = "EMERGENCY"


class RequestStatus(str, Enum):
    """Enumeration for service request status workflow."""

    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    QUOTED = "QUOTED"
    BOOKED = "BOOKED"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class ServiceRequest(Base):
    """
    ServiceRequest model representing job postings from clients.

    This model follows TDD principles and implements the behavior
    defined in the failing tests.
    """

    __tablename__ = "service_requests"

    # Optimized composite indexes for high-performance queries
    __table_args__ = (
        # Core business logic indexes
        Index("idx_seeker_status", "seeker_id", "status"),
        Index(
            "idx_status_created", "status", "created_at"
        ),  # For active requests by date
        Index(
            "idx_location_urgency",
            "location_latitude",
            "location_longitude",
            "urgency_level",
        ),
        Index(
            "idx_budget_range_status", "budget_min", "budget_max", "status"
        ),  # For budget filtering
        # Performance optimization indexes
        Index("idx_project_status", "project_id", "status"),  # For project integration
        Index(
            "idx_urgency_created", "urgency_level", "created_at"
        ),  # For urgent requests
        Index("idx_expires_status", "expires_at", "status"),  # For expiration cleanup
        # Geospatial optimization (if using spatial queries)
        Index("idx_location_coords", "location_latitude", "location_longitude"),
    )

    # Primary key
    id = Column(Integer, primary_key=True, index=True)

    # Basic request information
    title = Column(String(200), nullable=False, index=True)
    description = Column(Text, nullable=False)

    # Client information (references User Service)
    seeker_id = Column(Integer, nullable=False, index=True)

    # Location information
    location_address = Column(String(500), nullable=False)
    location_latitude = Column(Numeric(10, 8), nullable=True)
    location_longitude = Column(Numeric(11, 8), nullable=True)

    # Budget information
    budget_min = Column(Numeric(10, 2), nullable=True)
    budget_max = Column(Numeric(10, 2), nullable=True)
    budget_currency = Column(String(3), nullable=False, default="USD")

    # Timing and urgency
    urgency_level = Column(
        SQLEnum(UrgencyLevel), nullable=False, default=UrgencyLevel.MEDIUM
    )
    preferred_start_date = Column(DateTime, nullable=True)
    estimated_duration_hours = Column(Integer, nullable=True)

    # Status and workflow
    status = Column(SQLEnum(RequestStatus), nullable=False, default=RequestStatus.DRAFT)

    # Additional information stored as JSON
    requirements = Column(
        JSON, nullable=True
    )  # Detailed requirements as structured data
    images = Column(JSON, nullable=True)  # Array of image URLs

    # Project integration (optional)
    project_id = Column(Integer, nullable=True, index=True)

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    expires_at = Column(DateTime, nullable=True)

    # Optimized relationships with lazy loading strategies
    skill_requirements = relationship(
        "SkillRequirement",
        back_populates="service_request",
        cascade="all, delete-orphan",
        lazy="select",  # Explicit lazy loading for better control
        order_by="SkillRequirement.importance_weight.desc()",  # Order by importance
    )

    # Virtual relationship to quotes (for convenience)
    quotes = relationship(
        "Quote",
        foreign_keys="Quote.request_id",
        lazy="dynamic",  # Dynamic loading for large collections
        order_by="Quote.created_at.desc()",
        overlaps="service_request",  # Silence SQLAlchemy warning
    )

    @validates("budget_min", "budget_max")
    def validate_budget(self, key, value):
        """Validate budget values are positive and reasonable."""
        if value is not None:
            if value < 0:
                raise ValueError(f"{key} must be positive")
            if value > 1000000:  # $1M limit for sanity
                raise ValueError(f"{key} cannot exceed $1,000,000")

        # Cross-field validation for budget range
        if key == "budget_max" and hasattr(self, "budget_min") and self.budget_min:
            if value and value < self.budget_min:
                raise ValueError(
                    "budget_max must be greater than or equal to budget_min"
                )

        return value

    @validates("estimated_duration_hours")
    def validate_duration(self, key, value):
        """Validate duration is positive."""
        if value is not None and value <= 0:
            raise ValueError("Duration must be positive")
        return value

    def to_dict(self) -> Dict[str, Any]:
        """Convert ServiceRequest to dictionary for API responses."""
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "seeker_id": self.seeker_id,
            "location": {
                "address": self.location_address,
                "latitude": float(self.location_latitude)
                if self.location_latitude
                else None,
                "longitude": float(self.location_longitude)
                if self.location_longitude
                else None,
            },
            "budget": {
                "min": float(self.budget_min) if self.budget_min else None,
                "max": float(self.budget_max) if self.budget_max else None,
                "currency": self.budget_currency,
            },
            "urgency_level": self.urgency_level.value,
            "preferred_start_date": self.preferred_start_date.isoformat()
            if self.preferred_start_date
            else None,
            "estimated_duration_hours": self.estimated_duration_hours,
            "status": self.status.value,
            "requirements": self.requirements,
            "images": self.images,
            "project_id": self.project_id,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
        }

    def __str__(self) -> str:
        """String representation of ServiceRequest."""
        return f"ServiceRequest(id={self.id}, title='{self.title}', status={self.status.value})"

    def __repr__(self) -> str:
        """Developer representation of ServiceRequest."""
        return (
            f"ServiceRequest(id={self.id}, title='{self.title}', "
            f"seeker_id={self.seeker_id}, status={self.status.value})"
        )

    # Utility methods for better code organization
    def is_active(self) -> bool:
        """Check if the service request is active and accepting quotes."""
        return self.status == RequestStatus.ACTIVE

    def is_expired(self) -> bool:
        """Check if the service request has expired."""
        return self.expires_at and datetime.now(timezone.utc) > self.expires_at

    def has_budget_range(self) -> bool:
        """Check if the service request has a defined budget range."""
        return self.budget_min is not None and self.budget_max is not None

    def get_location_dict(self) -> Dict[str, Any]:
        """Get location information as a dictionary."""
        return {
            "address": self.location_address,
            "latitude": float(self.location_latitude)
            if self.location_latitude
            else None,
            "longitude": float(self.location_longitude)
            if self.location_longitude
            else None,
        }


class SkillRequirement(Base):
    """
    SkillRequirement model representing required skills for a service request.

    This is a junction table that links ServiceRequest to Skills with
    additional attributes like proficiency level and importance.
    """

    __tablename__ = "skill_requirements"

    # Primary key
    id = Column(Integer, primary_key=True, index=True)

    # Foreign keys
    service_request_id = Column(
        Integer,
        ForeignKey("service_requests.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    skill_id = Column(
        Integer, nullable=False, index=True
    )  # References Skills from ServiceProvider

    # Requirement details
    proficiency_level = Column(
        String(20), nullable=False, default="INTERMEDIATE"
    )  # BEGINNER, INTERMEDIATE, ADVANCED, EXPERT
    is_required = Column(
        Boolean, nullable=False, default=True
    )  # Required vs. preferred
    importance_weight = Column(
        Integer, nullable=False, default=5
    )  # 1-10 scale for matching algorithms

    # Additional notes
    notes = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Relationships
    service_request = relationship(
        "ServiceRequest", back_populates="skill_requirements"
    )

    @validates("importance_weight")
    def validate_importance_weight(self, key, value):
        """Validate importance weight is between 1 and 10."""
        if value < 1 or value > 10:
            raise ValueError("Importance weight must be between 1 and 10")
        return value

    @validates("proficiency_level")
    def validate_proficiency_level(self, key, value):
        """Validate proficiency level is valid."""
        valid_levels = ["BEGINNER", "INTERMEDIATE", "ADVANCED", "EXPERT"]
        if value not in valid_levels:
            raise ValueError(f"Proficiency level must be one of: {valid_levels}")
        return value

    def to_dict(self) -> Dict[str, Any]:
        """Convert SkillRequirement to dictionary for API responses."""
        return {
            "id": self.id,
            "service_request_id": self.service_request_id,
            "skill_id": self.skill_id,
            "proficiency_level": self.proficiency_level,
            "is_required": self.is_required,
            "importance_weight": self.importance_weight,
            "notes": self.notes,
            "created_at": self.created_at.isoformat(),
        }

    def __str__(self) -> str:
        """String representation of SkillRequirement."""
        return f"SkillRequirement(skill_id={self.skill_id}, level={self.proficiency_level})"

    def __repr__(self) -> str:
        """Developer representation of SkillRequirement."""
        return (
            f"SkillRequirement(id={self.id}, service_request_id={self.service_request_id}, "
            f"skill_id={self.skill_id}, proficiency_level='{self.proficiency_level}')"
        )
