"""Repository for Review model operations."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import desc, func
from sqlalchemy.orm import Session
from src.models.review import Review


class ReviewRepository:
    """Repository for managing Review entities."""

    def __init__(self, session: Session):
        """Initialize repository with database session."""
        self.session = session

    def create(self, **kwargs) -> Review:
        """Create a new review."""
        review = Review(**kwargs)
        self.session.add(review)
        self.session.commit()
        self.session.refresh(review)
        return review

    def get_by_id(self, review_id: int) -> Optional[Review]:
        """Get review by ID."""
        return self.session.query(Review).filter(Review.id == review_id).first()

    def get_by_product(self, product_id: int) -> List[Review]:
        """Get all reviews for a specific product."""
        return (
            self.session.query(Review)
            .filter(Review.product_id == product_id)
            .order_by(desc(Review.created_at))
            .all()
        )

    def get_by_vendor(self, vendor_id: int) -> List[Review]:
        """Get all reviews for a specific vendor."""
        return (
            self.session.query(Review)
            .filter(Review.vendor_id == vendor_id)
            .order_by(desc(Review.created_at))
            .all()
        )

    def get_by_user(self, user_id: int) -> List[Review]:
        """Get all reviews by a specific user."""
        return (
            self.session.query(Review)
            .filter(Review.user_id == user_id)
            .order_by(desc(Review.created_at))
            .all()
        )

    def get_verified_reviews(self) -> List[Review]:
        """Get all verified purchase reviews."""
        return (
            self.session.query(Review)
            .filter(Review.verified_purchase == True)
            .order_by(desc(Review.created_at))
            .all()
        )

    def get_by_rating_range(self, min_rating: int, max_rating: int) -> List[Review]:
        """Get reviews within a specific rating range."""
        return (
            self.session.query(Review)
            .filter(Review.rating >= min_rating, Review.rating <= max_rating)
            .order_by(desc(Review.created_at))
            .all()
        )

    def calculate_average_rating_for_product(self, product_id: int) -> float:
        """Calculate average rating for a product."""
        result = (
            self.session.query(func.avg(Review.rating))
            .filter(Review.product_id == product_id)
            .scalar()
        )
        return float(result) if result is not None else 0.0

    def calculate_average_rating_for_vendor(self, vendor_id: int) -> float:
        """Calculate average rating for a vendor."""
        result = (
            self.session.query(func.avg(Review.rating))
            .filter(Review.vendor_id == vendor_id)
            .scalar()
        )
        return float(result) if result is not None else 0.0

    def get_rating_distribution_for_product(self, product_id: int) -> Dict[int, int]:
        """Get rating distribution for a product."""
        results = (
            self.session.query(Review.rating, func.count(Review.rating))
            .filter(Review.product_id == product_id)
            .group_by(Review.rating)
            .all()
        )

        # Initialize all ratings to 0
        distribution = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}

        # Fill in actual counts
        for rating, count in results:
            distribution[rating] = count

        return distribution

    def get_rating_distribution_for_vendor(self, vendor_id: int) -> Dict[int, int]:
        """Get rating distribution for a vendor."""
        results = (
            self.session.query(Review.rating, func.count(Review.rating))
            .filter(Review.vendor_id == vendor_id)
            .group_by(Review.rating)
            .all()
        )

        # Initialize all ratings to 0
        distribution = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}

        # Fill in actual counts
        for rating, count in results:
            distribution[rating] = count

        return distribution

    def update(self, review_id: int, **kwargs) -> Optional[Review]:
        """Update review by ID."""
        review = self.get_by_id(review_id)
        if not review:
            return None

        for key, value in kwargs.items():
            if hasattr(review, key):
                setattr(review, key, value)

        self.session.commit()
        self.session.refresh(review)
        return review

    def delete(self, review_id: int) -> bool:
        """Delete review by ID."""
        review = self.get_by_id(review_id)
        if not review:
            return False

        self.session.delete(review)
        self.session.commit()
        return True

    def count(self) -> int:
        """Count total number of reviews."""
        return self.session.query(Review).count()

    def count_by_product(self, product_id: int) -> int:
        """Count reviews for a specific product."""
        return (
            self.session.query(Review).filter(Review.product_id == product_id).count()
        )

    def count_by_vendor(self, vendor_id: int) -> int:
        """Count reviews for a specific vendor."""
        return self.session.query(Review).filter(Review.vendor_id == vendor_id).count()

    def get_recent_reviews(self, limit: int = 10) -> List[Review]:
        """Get most recent reviews."""
        return (
            self.session.query(Review)
            .order_by(desc(Review.created_at))
            .limit(limit)
            .all()
        )

    def get_by_date_range(
        self, start_date: datetime, end_date: datetime
    ) -> List[Review]:
        """Get reviews within a date range."""
        return (
            self.session.query(Review)
            .filter(Review.created_at >= start_date, Review.created_at <= end_date)
            .order_by(desc(Review.created_at))
            .all()
        )

    def mark_as_verified(self, review_id: int) -> Optional[Review]:
        """Mark review as verified purchase."""
        review = self.get_by_id(review_id)
        if not review:
            return None

        review.verified_purchase = True
        self.session.commit()
        self.session.refresh(review)
        return review

    def get_top_rated_products(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get top rated products based on average review ratings."""
        results = (
            self.session.query(
                Review.product_id,
                func.avg(Review.rating).label("avg_rating"),
                func.count(Review.id).label("review_count"),
            )
            .group_by(Review.product_id)
            .order_by(desc("avg_rating"))
            .limit(limit)
            .all()
        )

        return [
            {
                "product_id": result.product_id,
                "avg_rating": float(result.avg_rating),
                "review_count": result.review_count,
            }
            for result in results
        ]

    def get_top_rated_vendors(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get top rated vendors based on average review ratings."""
        results = (
            self.session.query(
                Review.vendor_id,
                func.avg(Review.rating).label("avg_rating"),
                func.count(Review.id).label("review_count"),
            )
            .group_by(Review.vendor_id)
            .order_by(desc("avg_rating"))
            .limit(limit)
            .all()
        )

        return [
            {
                "vendor_id": result.vendor_id,
                "avg_rating": float(result.avg_rating),
                "review_count": result.review_count,
            }
            for result in results
        ]
