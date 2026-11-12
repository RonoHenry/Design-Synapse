"""
Review Model - Labor Services Marketplace

This module implements the Review model following TDD principles.
The model represents bidirectional feedback between clients and service providers.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from sqlalchemy import JSON, Boolean, Column, DateTime
from sqlalchemy import Enum as SQLEnum
from sqlalchemy import ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import relationship, validates

from .base import Base


class ReviewType(str, Enum):
    """Enumeration for review types (bidirectional)."""

    SEEKER_TO_PROVIDER = "SEEKER_TO_PROVIDER"
    PROVIDER_TO_SEEKER = "PROVIDER_TO_SEEKER"
    # Aliases for test compatibility
    PROVIDER_REVIEW = "SEEKER_TO_PROVIDER"
    SEEKER_REVIEW = "PROVIDER_TO_SEEKER"
    # Additional aliases
    SEEKER = "PROVIDER_TO_SEEKER"
    PROVIDER = "SEEKER_TO_PROVIDER"


# Alias for test compatibility
ReviewerType = ReviewType


class ReviewStatus(str, Enum):
    """Enumeration for review status workflow."""

    PUBLISHED = "PUBLISHED"
    PENDING_MODERATION = "PENDING_MODERATION"
    REJECTED = "REJECTED"
    HIDDEN = "HIDDEN"
    FLAGGED = "FLAGGED"
    # Alias for backward compatibility with tests
    PENDING = "PENDING_MODERATION"


class Review(Base):
    """
    Review model representing bidirectional feedback between users.

    This model follows TDD principles and implements the behavior
    defined in the failing tests.
    """

    __tablename__ = "reviews"

    # Optimized composite indexes for review system performance
    __table_args__ = (
        # Core business logic indexes
        Index(
            "idx_reviewee_type_status_rating",
            "reviewee_id",
            "review_type",
            "status",
            "overall_rating",
        ),
        Index("idx_reviewer_type_created", "reviewer_id", "review_type", "created_at"),
        Index("idx_booking_type_status", "booking_id", "review_type", "status"),
        # Performance optimization indexes
        Index(
            "idx_review_status_rating_created", "status", "overall_rating", "created_at"
        ),  # For public reviews
        Index(
            "idx_helpful_votes_status", "helpful_votes", "status"
        ),  # For popular reviews
        Index(
            "idx_moderation_queue",
            "status",
            "created_at",
            postgresql_where="status = 'PENDING_MODERATION'",
        ),  # For moderation
        # Unique constraint to prevent duplicate reviews
        Index(
            "idx_unique_booking_reviewer_type",
            "booking_id",
            "reviewer_id",
            "review_type",
            unique=True,
        ),
    )

    # Primary key
    id = Column(Integer, primary_key=True, index=True)

    # Relationships
    booking_id = Column(
        Integer,
        ForeignKey("bookings.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    reviewer_id = Column(
        Integer, nullable=False, index=True
    )  # Who is writing the review
    reviewee_id = Column(Integer, nullable=False, index=True)  # Who is being reviewed

    # Review type and direction
    review_type = Column(SQLEnum(ReviewType), nullable=False)

    # Rating system (1-5 scale)
    overall_rating = Column(Integer, nullable=False)
    quality_rating = Column(Integer, nullable=False)
    timeliness_rating = Column(Integer, nullable=False)
    communication_rating = Column(Integer, nullable=False)

    # Review content
    title = Column(String(200), nullable=True)  # Optional review title
    comment = Column(Text, nullable=False)
    images = Column(JSON, nullable=True)  # Array of image URLs
    categories = Column(JSON, nullable=True)  # Category ratings
    would_recommend = Column(Boolean, nullable=True, default=True)  # Recommendation
    is_verified = Column(Boolean, nullable=False, default=True)  # Verification status

    # Aliases for backward compatibility with tests
    @property
    def rating(self):
        """Alias for overall_rating for test compatibility."""
        return self.overall_rating

    @rating.setter
    def rating(self, value):
        """Setter for rating alias."""
        self.overall_rating = value

    @property
    def reviewer_type(self):
        """Alias for review_type for test compatibility."""
        return self.review_type

    @reviewer_type.setter
    def reviewer_type(self, value):
        """Setter for reviewer_type alias."""
        self.review_type = value

    @property
    def content(self):
        """Alias for comment for test compatibility."""
        return self.comment

    @content.setter
    def content(self, value):
        """Setter for content alias."""
        self.comment = value

    @property
    def photos(self):
        """Alias for images for API compatibility."""
        return self.images or []

    @photos.setter
    def photos(self, value):
        """Setter for photos alias."""
        self.images = value

    def content(self, value):
        """Setter for content alias."""
        self.comment = value

    # Response functionality
    response = Column(Text, nullable=True)  # Response from reviewee
    response_date = Column(DateTime, nullable=True)

    # Status and moderation
    status = Column(
        SQLEnum(ReviewStatus), nullable=False, default=ReviewStatus.PUBLISHED
    )
    moderated_at = Column(DateTime, nullable=True)
    moderated_by = Column(Integer, nullable=True)  # Admin user ID

    # Community features
    helpful_votes = Column(Integer, nullable=False, default=0)

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    booking = relationship("Booking", overlaps="reviews")  # Silence SQLAlchemy warning

    @validates(
        "overall_rating", "quality_rating", "timeliness_rating", "communication_rating"
    )
    def validate_ratings(self, key, value):
        """Validate rating values are between 1 and 5."""
        if value is not None and (value < 1 or value > 5):
            raise ValueError(f"{key} must be between 1 and 5")
        return value

    @validates("helpful_votes")
    def validate_helpful_votes(self, key, value):
        """Validate helpful votes is non-negative."""
        if value is not None and value < 0:
            raise ValueError("Helpful votes must be non-negative")
        return value

    def calculate_average_rating(self) -> float:
        """Calculate average rating from component ratings."""
        ratings = [
            self.quality_rating,
            self.timeliness_rating,
            self.communication_rating,
        ]
        return sum(ratings) / len(ratings)

    def add_response(self, response_text: str):
        """Add a response from the reviewee."""
        if self.response:
            raise ValueError("Review already has a response")

        self.response = response_text
        self.response_date = datetime.now(timezone.utc)

    def moderate_review(self, moderator_id: int, status: ReviewStatus):
        """Moderate the review (approve, reject, etc.)."""
        if status not in [
            ReviewStatus.PUBLISHED,
            ReviewStatus.REJECTED,
            ReviewStatus.HIDDEN,
        ]:
            raise ValueError("Invalid moderation status")

        self.status = status
        self.moderated_at = datetime.now(timezone.utc)
        self.moderated_by = moderator_id

    def add_helpful_vote(self):
        """Add a helpful vote to the review."""
        self.helpful_votes += 1

    def remove_helpful_vote(self):
        """Remove a helpful vote from the review."""
        if self.helpful_votes > 0:
            self.helpful_votes -= 1

    def is_positive_review(self) -> bool:
        """Check if review is generally positive (average rating >= 4)."""
        return self.calculate_average_rating() >= 4.0

    def get_sentiment_score(self) -> float:
        """Get sentiment score based on ratings (0.0 to 1.0)."""
        avg_rating = self.calculate_average_rating()
        return (avg_rating - 1) / 4  # Normalize 1-5 scale to 0-1

    @classmethod
    def get_provider_rating_summary(
        cls, provider_id: int, db_session
    ) -> Dict[str, Any]:
        """Get aggregated rating summary for a provider with optimized query."""
        from sqlalchemy import func

        # Use aggregation functions for better performance
        rating_stats = (
            db_session.query(
                func.avg(cls.overall_rating).label("avg_rating"),
                func.count(cls.id).label("total_reviews"),
                func.avg(cls.quality_rating).label("avg_quality"),
                func.avg(cls.timeliness_rating).label("avg_timeliness"),
                func.avg(cls.communication_rating).label("avg_communication"),
            )
            .filter(
                cls.reviewee_id == provider_id,
                cls.review_type == ReviewType.SEEKER_TO_PROVIDER,
                cls.status == ReviewStatus.PUBLISHED,
            )
            .first()
        )

        if not rating_stats.total_reviews:
            return {
                "average_rating": 0.0,
                "total_reviews": 0,
                "rating_breakdown": {1: 0, 2: 0, 3: 0, 4: 0, 5: 0},
                "category_averages": {
                    "quality": 0.0,
                    "timeliness": 0.0,
                    "communication": 0.0,
                },
            }

        # Get rating breakdown with a separate optimized query
        rating_breakdown_query = (
            db_session.query(cls.overall_rating, func.count(cls.id).label("count"))
            .filter(
                cls.reviewee_id == provider_id,
                cls.review_type == ReviewType.SEEKER_TO_PROVIDER,
                cls.status == ReviewStatus.PUBLISHED,
            )
            .group_by(cls.overall_rating)
            .all()
        )

        rating_breakdown = {i: 0 for i in range(1, 6)}
        for rating, count in rating_breakdown_query:
            rating_breakdown[rating] = count

        return {
            "average_rating": round(float(rating_stats.avg_rating), 2),
            "total_reviews": rating_stats.total_reviews,
            "rating_breakdown": rating_breakdown,
            "category_averages": {
                "quality": round(float(rating_stats.avg_quality), 2),
                "timeliness": round(float(rating_stats.avg_timeliness), 2),
                "communication": round(float(rating_stats.avg_communication), 2),
            },
        }

    def to_dict(self) -> Dict[str, Any]:
        """Convert Review to dictionary for API responses."""
        return {
            "id": self.id,
            "booking_id": self.booking_id,
            "reviewer_id": self.reviewer_id,
            "reviewee_id": self.reviewee_id,
            "review_type": self.review_type.value,
            "ratings": {
                "overall": self.overall_rating,
                "quality": self.quality_rating,
                "timeliness": self.timeliness_rating,
                "communication": self.communication_rating,
                "average": round(self.calculate_average_rating(), 2),
            },
            "comment": self.comment,
            "images": self.images,
            "response": self.response,
            "response_date": self.response_date.isoformat()
            if self.response_date
            else None,
            "status": self.status.value,
            "helpful_votes": self.helpful_votes,
            "is_positive": self.is_positive_review(),
            "sentiment_score": round(self.get_sentiment_score(), 2),
            "moderated_at": self.moderated_at.isoformat()
            if self.moderated_at
            else None,
            "moderated_by": self.moderated_by,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    def __str__(self) -> str:
        """String representation of Review."""
        return f"Review(id={self.id}, overall_rating={self.overall_rating}, type={self.review_type.value})"

    def __repr__(self) -> str:
        """Developer representation of Review."""
        return (
            f"Review(id={self.id}, booking_id={self.booking_id}, "
            f"reviewer_id={self.reviewer_id}, reviewee_id={self.reviewee_id})"
        )
