"""
Service Provider Models

Models for service providers, their skills, certifications, and service areas.
"""

from datetime import datetime
from decimal import Decimal
from enum import Enum as PyEnum
from typing import Any, Dict, List, Optional

from sqlalchemy import (JSON, Boolean, Column, DateTime, Enum, ForeignKey,
                        Index, Integer, Numeric, String, Text)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from .base import Base, BaseModel


class ProviderType(PyEnum):
    """Types of service providers"""

    INDIVIDUAL = "individual"
    BUSINESS = "business"
    TEAM = "team"


class VerificationStatus(PyEnum):
    """Provider verification status"""

    PENDING = "pending"
    VERIFIED = "verified"
    REJECTED = "rejected"
    SUSPENDED = "suspended"


class ProficiencyLevel(PyEnum):
    """Skill proficiency levels"""

    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    EXPERT = "expert"


class ServiceProvider(BaseModel):
    """Service provider model"""

    __tablename__ = "service_providers"

    # User reference (from User Service)
    user_id = Column(
        Integer,
        nullable=False,
        unique=True,
        comment="Reference to user in User Service",
    )

    # Basic information
    business_name = Column(
        String(255), nullable=True, comment="Business name (for business providers)"
    )

    individual_name = Column(
        String(255), nullable=False, comment="Individual or contact person name"
    )

    provider_type = Column(
        Enum(ProviderType),
        nullable=False,
        default=ProviderType.INDIVIDUAL,
        comment="Type of provider",
    )

    description = Column(Text, nullable=True, comment="Provider description and bio")

    # Experience and qualifications
    experience_years = Column(
        Integer, default=0, nullable=False, comment="Years of experience"
    )

    # Verification and trust
    verification_status = Column(
        Enum(VerificationStatus),
        default=VerificationStatus.PENDING,
        nullable=False,
        comment="Verification status",
    )

    verification_date = Column(
        DateTime(timezone=True), nullable=True, comment="Date of verification"
    )

    # Ratings and performance
    rating = Column(
        Numeric(3, 2),
        default=0.00,
        nullable=False,
        comment="Average rating (0.00-5.00)",
    )

    total_reviews = Column(
        Integer, default=0, nullable=False, comment="Total number of reviews"
    )

    total_jobs_completed = Column(
        Integer, default=0, nullable=False, comment="Total jobs completed"
    )

    response_time_avg = Column(
        Integer, default=0, nullable=False, comment="Average response time in minutes"
    )

    # Insurance and bonding
    insurance_info = Column(JSON, nullable=True, comment="Insurance information (JSON)")

    # Portfolio and media
    portfolio_images = Column(
        JSON, nullable=True, comment="Portfolio image URLs (JSON array)"
    )

    # Status
    is_active = Column(
        Boolean, default=True, nullable=False, comment="Provider active status"
    )

    is_available = Column(
        Boolean, default=True, nullable=False, comment="Current availability status"
    )

    # Relationships
    skills = relationship(
        "ProviderSkill", back_populates="provider", cascade="all, delete-orphan"
    )

    service_areas = relationship(
        "ServiceArea", back_populates="provider", cascade="all, delete-orphan"
    )

    # Indexes
    __table_args__ = (
        Index("idx_user_id", "user_id"),
        Index("idx_verification_status", "verification_status"),
        Index("idx_rating", "rating"),
        Index("idx_active_available", "is_active", "is_available"),
        Index("idx_provider_type", "provider_type"),
    )

    def __repr__(self):
        return f"<ServiceProvider(id={self.id}, name='{self.individual_name}')>"

    def __str__(self):
        """Human-readable string representation including the provider name"""
        return f"ServiceProvider(id={self.id}, name={self.individual_name})"


class SkillCategory(BaseModel):
    """Skill categories for organizing skills"""

    __tablename__ = "skill_categories"

    name = Column(String(100), nullable=False, unique=True, comment="Category name")

    description = Column(Text, nullable=True, comment="Category description")

    sort_order = Column(
        Integer, default=0, nullable=False, comment="Display sort order"
    )

    is_active = Column(
        Boolean, default=True, nullable=False, comment="Category active status"
    )

    # Relationships
    skills = relationship("Skill", back_populates="category")

    def __repr__(self):
        return f"<SkillCategory(id={self.id}, name='{self.name}')>"


class Skill(BaseModel):
    """Individual skills that providers can have"""

    __tablename__ = "skills"

    category_id = Column(
        Integer,
        ForeignKey("skill_categories.id"),
        nullable=False,
        comment="Reference to skill category",
    )

    name = Column(String(100), nullable=False, comment="Skill name")

    description = Column(Text, nullable=True, comment="Skill description")

    requires_certification = Column(
        Boolean,
        default=False,
        nullable=False,
        comment="Whether skill requires certification",
    )

    is_active = Column(
        Boolean, default=True, nullable=False, comment="Skill active status"
    )

    # Relationships
    category = relationship("SkillCategory", back_populates="skills")

    provider_skills = relationship("ProviderSkill", back_populates="skill")

    # Indexes
    __table_args__ = (
        Index("idx_category_id", "category_id"),
        Index("idx_skill_name", "name"),
        Index("idx_requires_cert", "requires_certification"),
    )

    def __repr__(self):
        return f"<Skill(id={self.id}, name='{self.name}')>"


class ProviderSkill(BaseModel):
    """Junction table for provider skills with proficiency and rates"""

    __tablename__ = "provider_skills"

    provider_id = Column(
        Integer,
        ForeignKey("service_providers.id", ondelete="CASCADE"),
        nullable=False,
        comment="Reference to service provider",
    )

    skill_id = Column(
        Integer, ForeignKey("skills.id"), nullable=False, comment="Reference to skill"
    )

    proficiency_level = Column(
        Enum(ProficiencyLevel),
        nullable=False,
        comment="Provider's proficiency level in this skill",
    )

    years_experience = Column(
        Integer,
        default=0,
        nullable=False,
        comment="Years of experience with this skill",
    )

    hourly_rate = Column(
        Numeric(8, 2), nullable=True, comment="Hourly rate for this skill"
    )

    certifications = Column(
        JSON, nullable=True, comment="Certifications for this skill (JSON array)"
    )

    is_primary = Column(
        Boolean,
        default=False,
        nullable=False,
        comment="Whether this is a primary skill",
    )

    # Relationships
    provider = relationship("ServiceProvider", back_populates="skills")

    skill = relationship("Skill", back_populates="provider_skills")

    # Indexes and constraints
    __table_args__ = (
        Index("idx_provider_skill_provider_id", "provider_id"),
        Index("idx_provider_skill_skill_id", "skill_id"),
        Index("idx_provider_skill_proficiency", "proficiency_level"),
        Index("idx_provider_skill_primary", "is_primary"),
        # Unique constraint to prevent duplicate provider-skill combinations
        Index("unique_provider_skill", "provider_id", "skill_id", unique=True),
    )

    def __repr__(self):
        return (
            f"<ProviderSkill(provider_id={self.provider_id}, skill_id={self.skill_id})>"
        )


class ServiceArea(BaseModel):
    """Geographic service areas for providers"""

    __tablename__ = "service_areas"

    provider_id = Column(
        Integer,
        ForeignKey("service_providers.id", ondelete="CASCADE"),
        nullable=False,
        comment="Reference to service provider",
    )

    # Geographic center point
    center_latitude = Column(
        Numeric(10, 8), nullable=False, comment="Center latitude coordinate"
    )

    center_longitude = Column(
        Numeric(11, 8), nullable=False, comment="Center longitude coordinate"
    )

    # Service radius
    radius_miles = Column(Integer, nullable=False, comment="Service radius in miles")

    # Travel costs
    travel_rate = Column(Numeric(8, 2), nullable=True, comment="Travel rate per mile")

    # Area details
    area_name = Column(
        String(255), nullable=True, comment="Friendly name for service area"
    )

    is_primary = Column(
        Boolean,
        default=False,
        nullable=False,
        comment="Whether this is the primary service area",
    )

    is_active = Column(
        Boolean, default=True, nullable=False, comment="Service area active status"
    )

    # Relationships
    provider = relationship("ServiceProvider", back_populates="service_areas")

    # Indexes
    __table_args__ = (
        Index("idx_service_area_provider_id", "provider_id"),
        Index("idx_service_area_location", "center_latitude", "center_longitude"),
        Index("idx_service_area_primary", "is_primary"),
        Index("idx_service_area_active", "is_active"),
    )

    def __repr__(self):
        return f"<ServiceArea(id={self.id}, provider_id={self.provider_id})>"
