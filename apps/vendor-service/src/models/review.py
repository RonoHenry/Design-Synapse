"""Review model for product and vendor reviews."""

from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

from sqlalchemy import (Boolean, CheckConstraint, DateTime, ForeignKey,
                        Integer, String, Text, func)
from sqlalchemy.orm import Mapped, mapped_column, validates
from src.infrastructure.database import Base


class Review(Base):
    """Review model representing customer reviews for products and vendors."""

    __tablename__ = "reviews"
    __table_args__ = (
        CheckConstraint("rating >= 1 AND rating <= 5", name="rating_range_check"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    product_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    vendor_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("vendors.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    rating: Mapped[int] = mapped_column(Integer, nullable=False)
    comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    verified_purchase: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    def __init__(
        self,
        user_id: int,
        product_id: int,
        vendor_id: int,
        rating: int,
        comment: Optional[str] = None,
        verified_purchase: bool = False,
        **kwargs,
    ):
        """Initialize a new review."""
        self.user_id = user_id
        self.product_id = product_id
        self.vendor_id = vendor_id
        self.rating = self._validate_rating(rating)
        self.comment = self._validate_comment(comment) if comment else None
        self.verified_purchase = verified_purchase
        self.created_at = datetime.now(timezone.utc)

    @staticmethod
    def _validate_rating(rating: int) -> int:
        """Validate rating value."""
        if not isinstance(rating, int):
            raise ValueError("Rating must be an integer")
        if rating < 1 or rating > 5:
            raise ValueError("Rating must be between 1 and 5")
        return rating

    @staticmethod
    def _validate_comment(comment: str) -> str:
        """Validate review comment."""
        if comment and len(comment.strip()) > 5000:
            raise ValueError("Comment cannot exceed 5000 characters")
        return comment.strip() if comment else None

    @validates("rating")
    def validate_rating_update(self, key: str, value: int) -> int:
        """Validate rating on update."""
        return self._validate_rating(value)

    def is_verified(self) -> bool:
        """Check if review is from a verified purchase."""
        return self.verified_purchase

    def is_positive(self) -> bool:
        """Check if review is positive (4-5 stars)."""
        return self.rating >= 4

    def is_negative(self) -> bool:
        """Check if review is negative (1-2 stars)."""
        return self.rating <= 2

    def is_neutral(self) -> bool:
        """Check if review is neutral (3 stars)."""
        return self.rating == 3

    def mark_as_verified(self) -> None:
        """Mark review as from a verified purchase."""
        self.verified_purchase = True

    def __repr__(self) -> str:
        """String representation of review."""
        verified_str = " (verified)" if self.verified_purchase else ""
        return f"<Review(id={self.id}, user_id={self.user_id}, product_id={self.product_id}, rating={self.rating}{verified_str})>"
