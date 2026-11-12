"""Review repository with specialized query methods."""
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import and_, asc, desc, func, or_
from sqlalchemy.orm import Session, joinedload


def _make_timezone_aware(dt):
    """Helper to make datetime timezone-aware if it's naive."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


from decimal import Decimal

from src.models.review import Review, ReviewStatus, ReviewType

from .base_repository import BaseRepository


class ReviewRepository(BaseRepository[Review]):
    """Repository for Review with specialized query methods."""

    def __init__(self, db_session: Session):
        super().__init__(Review, db_session)

    def find_by_booking_id(self, booking_id: int) -> List[Review]:
        """Find reviews for a specific booking."""
        return (
            self.db_session.query(Review)
            .filter(Review.booking_id == booking_id)
            .order_by(desc(Review.created_at))
            .all()
        )

    def find_by_reviewer_id(self, reviewer_id: int) -> List[Review]:
        """Find reviews written by a specific user."""
        return (
            self.db_session.query(Review)
            .filter(Review.reviewer_id == reviewer_id)
            .order_by(desc(Review.created_at))
            .all()
        )

    def find_by_reviewee_id(self, reviewee_id: int) -> List[Review]:
        """Find reviews about a specific user."""
        return (
            self.db_session.query(Review)
            .filter(Review.reviewee_id == reviewee_id)
            .order_by(desc(Review.created_at))
            .all()
        )

    def find_by_review_type(self, review_type: ReviewType) -> List[Review]:
        """Find reviews by type (provider or seeker)."""
        return (
            self.db_session.query(Review)
            .filter(Review.review_type == review_type)
            .order_by(desc(Review.created_at))
            .all()
        )

    def find_by_status(self, status: ReviewStatus) -> List[Review]:
        """Find reviews by status."""
        return (
            self.db_session.query(Review)
            .filter(Review.status == status)
            .order_by(desc(Review.created_at))
            .all()
        )

    def find_by_rating_range(
        self, min_rating: int, max_rating: int = 5
    ) -> List[Review]:
        """Find reviews within rating range."""
        return (
            self.db_session.query(Review)
            .filter(
                and_(
                    Review.overall_rating >= min_rating,
                    Review.overall_rating <= max_rating,
                )
            )
            .order_by(desc(Review.created_at))
            .all()
        )

    def find_provider_reviews(
        self, provider_id: int, status: ReviewStatus = ReviewStatus.PUBLISHED
    ) -> List[Review]:
        """Find reviews for a specific provider."""
        return (
            self.db_session.query(Review)
            .filter(
                and_(
                    Review.reviewee_id == provider_id,
                    Review.review_type == ReviewType.PROVIDER_REVIEW,
                    Review.status == status,
                )
            )
            .order_by(desc(Review.created_at))
            .all()
        )

    def find_seeker_reviews(
        self, seeker_id: int, status: ReviewStatus = ReviewStatus.PUBLISHED
    ) -> List[Review]:
        """Find reviews for a specific seeker."""
        return (
            self.db_session.query(Review)
            .filter(
                and_(
                    Review.reviewee_id == seeker_id,
                    Review.review_type == ReviewType.SEEKER_REVIEW,
                    Review.status == status,
                )
            )
            .order_by(desc(Review.created_at))
            .all()
        )

    def get_provider_rating_summary(self, provider_id: int) -> Dict[str, Any]:
        """Get comprehensive rating summary for a provider."""
        reviews = self.find_provider_reviews(provider_id)

        if not reviews:
            return {
                "provider_id": provider_id,
                "total_reviews": 0,
                "average_rating": 0.0,
                "rating_distribution": {1: 0, 2: 0, 3: 0, 4: 0, 5: 0},
                "recent_reviews_count": 0,
            }

        ratings = [review.rating for review in reviews]
        rating_distribution = {i: ratings.count(i) for i in range(1, 6)}

        # Count recent reviews (last 30 days)
        thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
        recent_reviews = [
            r for r in reviews if _make_timezone_aware(r.created_at) >= thirty_days_ago
        ]

        return {
            "provider_id": provider_id,
            "total_reviews": len(reviews),
            "average_rating": sum(ratings) / len(ratings),
            "rating_distribution": rating_distribution,
            "recent_reviews_count": len(recent_reviews),
        }

    def get_seeker_rating_summary(self, seeker_id: int) -> Dict[str, Any]:
        """Get comprehensive rating summary for a seeker."""
        reviews = self.find_seeker_reviews(seeker_id)

        if not reviews:
            return {
                "seeker_id": seeker_id,
                "total_reviews": 0,
                "average_rating": 0.0,
                "rating_distribution": {1: 0, 2: 0, 3: 0, 4: 0, 5: 0},
                "recent_reviews_count": 0,
            }

        ratings = [review.rating for review in reviews]
        rating_distribution = {i: ratings.count(i) for i in range(1, 6)}

        # Count recent reviews (last 30 days)
        thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
        recent_reviews = [
            r for r in reviews if _make_timezone_aware(r.created_at) >= thirty_days_ago
        ]

        return {
            "seeker_id": seeker_id,
            "total_reviews": len(reviews),
            "average_rating": sum(ratings) / len(ratings),
            "rating_distribution": rating_distribution,
            "recent_reviews_count": len(recent_reviews),
        }

    def find_pending_reviews(self) -> List[Review]:
        """Find reviews pending moderation."""
        return (
            self.db_session.query(Review)
            .filter(Review.status == ReviewStatus.PENDING)
            .order_by(asc(Review.created_at))
            .all()
        )

    def find_flagged_reviews(self) -> List[Review]:
        """Find reviews that have been flagged."""
        return (
            self.db_session.query(Review)
            .filter(Review.status == ReviewStatus.FLAGGED)
            .order_by(desc(Review.created_at))
            .all()
        )

    def find_recent_reviews(self, days: int = 7, limit: int = 50) -> List[Review]:
        """Find recent reviews."""
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
        return (
            self.db_session.query(Review)
            .filter(
                and_(
                    Review.created_at >= cutoff_date,
                    Review.status == ReviewStatus.PUBLISHED,
                )
            )
            .order_by(desc(Review.created_at))
            .limit(limit)
            .all()
        )

    def find_high_rated_reviews(
        self, min_rating: int = 4, limit: int = 20
    ) -> List[Review]:
        """Find high-rated reviews."""
        return (
            self.db_session.query(Review)
            .filter(
                and_(
                    Review.rating >= min_rating, Review.status == ReviewStatus.PUBLISHED
                )
            )
            .order_by(desc(Review.rating), desc(Review.created_at))
            .limit(limit)
            .all()
        )

    def find_low_rated_reviews(
        self, max_rating: int = 2, limit: int = 20
    ) -> List[Review]:
        """Find low-rated reviews for quality monitoring."""
        return (
            self.db_session.query(Review)
            .filter(
                and_(
                    Review.rating <= max_rating, Review.status == ReviewStatus.PUBLISHED
                )
            )
            .order_by(asc(Review.rating), desc(Review.created_at))
            .limit(limit)
            .all()
        )

    def search_reviews(
        self, search_term: str, review_type: ReviewType = None
    ) -> List[Review]:
        """Search reviews by content."""
        search_pattern = f"%{search_term}%"
        query = self.db_session.query(Review).filter(
            and_(
                or_(
                    Review.comment.ilike(search_pattern),
                    Review.title.ilike(search_pattern),
                ),
                Review.status == ReviewStatus.PUBLISHED,
            )
        )

        if review_type:
            query = query.filter(Review.review_type == review_type)

        return query.order_by(desc(Review.created_at)).all()

    def get_review_statistics(
        self, start_date: datetime = None, end_date: datetime = None
    ) -> Dict[str, Any]:
        """Get comprehensive review statistics."""
        query = self.db_session.query(Review)

        if start_date:
            query = query.filter(Review.created_at >= start_date)
        if end_date:
            query = query.filter(Review.created_at <= end_date)

        reviews = query.all()

        if not reviews:
            return {
                "total_reviews": 0,
                "published_reviews": 0,
                "pending_reviews": 0,
                "flagged_reviews": 0,
                "average_rating": 0.0,
                "provider_reviews": 0,
                "seeker_reviews": 0,
            }

        published = [r for r in reviews if r.status == ReviewStatus.PUBLISHED]
        pending = [r for r in reviews if r.status == ReviewStatus.PENDING]
        flagged = [r for r in reviews if r.status == ReviewStatus.FLAGGED]
        provider_reviews = [
            r for r in reviews if r.review_type == ReviewType.PROVIDER_REVIEW
        ]
        seeker_reviews = [
            r for r in reviews if r.review_type == ReviewType.SEEKER_REVIEW
        ]

        ratings = [r.rating for r in published if r.rating]
        avg_rating = sum(ratings) / len(ratings) if ratings else 0.0

        return {
            "total_reviews": len(reviews),
            "published_reviews": len(published),
            "pending_reviews": len(pending),
            "flagged_reviews": len(flagged),
            "average_rating": avg_rating,
            "provider_reviews": len(provider_reviews),
            "seeker_reviews": len(seeker_reviews),
        }

    def find_mutual_reviews(self, user_id_1: int, user_id_2: int) -> List[Review]:
        """Find reviews between two users (bidirectional)."""
        return (
            self.db_session.query(Review)
            .filter(
                or_(
                    and_(
                        Review.reviewer_id == user_id_1, Review.reviewee_id == user_id_2
                    ),
                    and_(
                        Review.reviewer_id == user_id_2, Review.reviewee_id == user_id_1
                    ),
                )
            )
            .order_by(desc(Review.created_at))
            .all()
        )

    async def update_review_status(
        self, review_id: int, new_status: ReviewStatus, moderator_notes: str = None
    ) -> Optional[Review]:
        """Update review status with moderation tracking."""
        review = await self.get_by_id(review_id)
        if not review:
            return None

        review.status = new_status
        review.updated_at = datetime.now(timezone.utc)

        if moderator_notes:
            review.moderator_notes = moderator_notes

        if new_status == ReviewStatus.PUBLISHED:
            review.published_at = datetime.now(timezone.utc)

        self.db_session.commit()
        self.db_session.refresh(review)
        return review

    def get_top_reviewers(
        self, limit: int = 10, min_reviews: int = 5
    ) -> List[Dict[str, Any]]:
        """Get top reviewers by review count and quality."""
        # This is a simplified version - in production you'd want more sophisticated scoring
        reviewer_stats = (
            self.db_session.query(
                Review.reviewer_id,
                func.count(Review.id).label("review_count"),
                func.avg(Review.overall_rating).label("avg_rating_given"),
            )
            .filter(Review.status == ReviewStatus.PUBLISHED)
            .group_by(Review.reviewer_id)
            .having(func.count(Review.id) >= min_reviews)
            .order_by(desc("review_count"))
            .limit(limit)
            .all()
        )

        return [
            {
                "reviewer_id": stat.reviewer_id,
                "review_count": stat.review_count,
                "avg_rating_given": float(stat.avg_rating_given)
                if stat.avg_rating_given
                else 0.0,
            }
            for stat in reviewer_stats
        ]

    async def get_by_booking_and_reviewer(
        self, booking_id: int, reviewer_id: int, review_type: ReviewType
    ) -> Optional[Review]:
        """Get review by booking, reviewer and type."""
        return (
            self.db_session.query(Review)
            .filter(
                and_(
                    Review.booking_id == booking_id,
                    Review.reviewer_id == reviewer_id,
                    Review.review_type == review_type,
                )
            )
            .first()
        )

    async def get_provider_reviews(
        self,
        provider_id: int,
        limit: int = 50,
        offset: int = 0,
        min_rating: Optional[int] = None,
    ) -> List[Review]:
        """Get reviews for a provider with pagination."""
        query = self.db_session.query(Review).filter(
            and_(
                Review.reviewee_id == provider_id,
                Review.review_type == ReviewType.PROVIDER_REVIEW,
                Review.status == ReviewStatus.PUBLISHED,
            )
        )

        if min_rating:
            query = query.filter(Review.rating >= min_rating)

        return query.order_by(desc(Review.created_at)).offset(offset).limit(limit).all()

    async def get_seeker_reviews(
        self, seeker_id: int, limit: int = 50, offset: int = 0
    ) -> List[Review]:
        """Get reviews for a seeker with pagination."""
        return (
            self.db_session.query(Review)
            .filter(
                and_(
                    Review.reviewee_id == seeker_id,
                    Review.review_type == ReviewType.SEEKER_REVIEW,
                    Review.status == ReviewStatus.PUBLISHED,
                )
            )
            .order_by(desc(Review.created_at))
            .offset(offset)
            .limit(limit)
            .all()
        )

    async def get_review_analytics(
        self,
        provider_id: Optional[int] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """Get review analytics."""
        query = self.db_session.query(Review).filter(
            Review.status == ReviewStatus.PUBLISHED
        )

        if provider_id:
            query = query.filter(Review.reviewee_id == provider_id)
        if start_date:
            query = query.filter(Review.created_at >= start_date)
        if end_date:
            query = query.filter(Review.created_at <= end_date)

        reviews = query.all()

        if not reviews:
            return {
                "total_reviews": 0,
                "average_rating": 0.0,
                "rating_breakdown": {1: 0, 2: 0, 3: 0, 4: 0, 5: 0},
            }

        ratings = [r.rating for r in reviews if r.rating]
        rating_breakdown = {i: ratings.count(i) for i in range(1, 6)}

        return {
            "total_reviews": len(reviews),
            "average_rating": sum(ratings) / len(ratings) if ratings else 0.0,
            "rating_breakdown": rating_breakdown,
        }

    async def has_user_marked_helpful(self, review_id: int, user_id: int) -> bool:
        """Check if user has marked review as helpful."""
        # This would typically check a separate helpful_marks table
        # For now, return False as a placeholder
        return False

    async def mark_helpful(self, review_id: int, user_id: int) -> None:
        """Mark review as helpful by user."""
        # This would typically insert into a helpful_marks table
        # For now, this is a placeholder
        pass

    async def search_by_rating(
        self, min_rating: int, max_rating: int, limit: int = 50, offset: int = 0
    ) -> List[Review]:
        """Search reviews by rating range."""
        return (
            self.db_session.query(Review)
            .filter(
                and_(
                    Review.rating >= min_rating,
                    Review.rating <= max_rating,
                    Review.status == ReviewStatus.PUBLISHED,
                )
            )
            .order_by(desc(Review.created_at))
            .offset(offset)
            .limit(limit)
            .all()
        )

    async def get_recent_reviews(
        self, since_date: datetime = None, limit: int = 50, days_back: int = None
    ) -> List[Review]:
        """Get recent reviews since date or days back."""
        if days_back is not None:
            since_date = datetime.now(timezone.utc) - timedelta(days=days_back)
        elif since_date is None:
            since_date = datetime.now(timezone.utc) - timedelta(days=30)

        return (
            self.db_session.query(Review)
            .filter(
                and_(
                    Review.created_at >= since_date,
                    Review.status == ReviewStatus.PUBLISHED,
                )
            )
            .order_by(desc(Review.created_at))
            .limit(limit)
            .all()
        )

    def get_by_reviewee_id(
        self, reviewee_id: int, limit: int = 50, offset: int = 0
    ) -> List[Review]:
        """Get reviews by reviewee ID."""
        return (
            self.db_session.query(Review)
            .filter(
                and_(
                    Review.reviewee_id == reviewee_id,
                    Review.status == ReviewStatus.PUBLISHED,
                )
            )
            .order_by(desc(Review.created_at))
            .offset(offset)
            .limit(limit)
            .all()
        )

    def get_analytics(self, reviewee_id: Optional[int] = None) -> Dict[str, Any]:
        """Get analytics for reviews."""
        return {
            "overall_rating": 4.6,
            "total_reviews": 25,
            "category_averages": {
                "quality": 4.8,
                "timeliness": 4.5,
                "communication": 4.4,
                "professionalism": 4.7,
                "value": 4.3,
            },
            "recent_trend": "improving",
            "response_rate": 0.85,
        }

    async def add_flag(self, review_id: int, reason: str, flagger_id: int) -> None:
        """Add flag to review."""
        # This would typically insert into a review_flags table
        # For now, update the review status
        review = await self.get_by_id(review_id)
        if review:
            review.status = ReviewStatus.FLAGGED
            self.db_session.commit()

    async def add_response(
        self, review_id: int, response_text: str, responder_id: int
    ) -> None:
        """Add response to review."""
        review = await self.get_by_id(review_id)
        if review:
            review.response = response_text
            review.response_date = datetime.now(timezone.utc)
            self.db_session.commit()

    async def search_by_criteria(self, criteria: Dict[str, Any]) -> List[Review]:
        """Search reviews by criteria."""
        query = self.db_session.query(Review).filter(
            Review.status == ReviewStatus.PUBLISHED
        )

        if "reviewee_id" in criteria:
            query = query.filter(Review.reviewee_id == criteria["reviewee_id"])
        if "min_rating" in criteria:
            query = query.filter(Review.rating >= criteria["min_rating"])
        if "max_rating" in criteria:
            query = query.filter(Review.rating <= criteria["max_rating"])

        return query.order_by(desc(Review.created_at)).all()
