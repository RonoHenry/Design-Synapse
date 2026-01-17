"""Tests for ReviewRepository."""
import pytest
from datetime import datetime, timedelta, timezone

from src.models.review import Review, ReviewType, ReviewStatus
from src.repositories.review_repository import ReviewRepository
from tests.factories import ReviewFactory

class TestReviewRepository:
    """Test cases for ReviewRepository."""
    
    def test_create_repository(self, db_session):
        """Test repository creation."""
        repo = ReviewRepository(db_session)
        assert repo.model == Review
        assert repo.db_session == db_session
    
    def test_find_by_booking_id(self, db_session):
        """Test finding reviews by booking ID."""
        repo = ReviewRepository(db_session)
        
        # Create test data
        review_1 = ReviewFactory.create(
            booking_id=1001,
            title="Review 1",
            created_at=datetime.now(timezone.utc) - timedelta(days=1)
        )
        review_2 = ReviewFactory.create(
            booking_id=1001,
            title="Review 2",
            created_at=datetime.now(timezone.utc)
        )
        other_booking_review = ReviewFactory.create(
            booking_id=1002,
            title="Other Booking"
        )
        db_session.commit()
        
        # Test finding by booking ID (should be ordered by creation date desc)
        booking_reviews = repo.find_by_booking_id(1001)
        assert len(booking_reviews) == 2
        assert booking_reviews[0].title == "Review 2"  # Most recent first
        assert booking_reviews[1].title == "Review 1"
    
    def test_find_by_reviewer_id(self, db_session):
        """Test finding reviews by reviewer ID."""
        repo = ReviewRepository(db_session)
        
        # Create test data
        reviewer_review_1 = ReviewFactory.create(
            reviewer_id=3001,
            title="Reviewer Review 1"
        )
        reviewer_review_2 = ReviewFactory.create(
            reviewer_id=3001,
            title="Reviewer Review 2"
        )
        other_reviewer_review = ReviewFactory.create(
            reviewer_id=3002,
            title="Other Reviewer"
        )
        db_session.commit()
        
        # Test finding by reviewer ID
        reviewer_reviews = repo.find_by_reviewer_id(3001)
        assert len(reviewer_reviews) == 2
    
    def test_find_by_reviewee_id(self, db_session):
        """Test finding reviews by reviewee ID."""
        repo = ReviewRepository(db_session)
        
        # Create test data
        reviewee_review_1 = ReviewFactory.create(
            reviewee_id=4001,
            title="About User 1"
        )
        reviewee_review_2 = ReviewFactory.create(
            reviewee_id=4001,
            title="About User 2"
        )
        other_reviewee_review = ReviewFactory.create(
            reviewee_id=4002,
            title="About Other User"
        )
        db_session.commit()
        
        # Test finding by reviewee ID
        reviewee_reviews = repo.find_by_reviewee_id(4001)
        assert len(reviewee_reviews) == 2
    
    def test_find_by_review_type(self, db_session):
        """Test finding reviews by type."""
        repo = ReviewRepository(db_session)
        
        # Create test data
        provider_review = ReviewFactory.create(
            review_type=ReviewType.SEEKER_TO_PROVIDER,
            title="Provider Review"
        )
        seeker_review = ReviewFactory.create(
            review_type=ReviewType.SEEKER_REVIEW,
            title="Seeker Review"
        )
        db_session.commit()
        
        # Test finding by review type
        provider_reviews = repo.find_by_review_type(ReviewType.SEEKER_TO_PROVIDER)
        assert len(provider_reviews) == 1
        assert provider_reviews[0].title == "Provider Review"
        
        seeker_reviews = repo.find_by_review_type(ReviewType.PROVIDER_TO_SEEKER)
        assert len(seeker_reviews) == 1
        assert seeker_reviews[0].title == "Seeker Review"
    
    def test_find_by_status(self, db_session):
        """Test finding reviews by status."""
        repo = ReviewRepository(db_session)
        
        # Create test data
        published_review = ReviewFactory.create(
            status=ReviewStatus.PUBLISHED,
            title="Published Review"
        )
        pending_review = ReviewFactory.create(
            status=ReviewStatus.PENDING,
            title="Pending Review"
        )
        db_session.commit()
        
        # Test finding by status
        published_reviews = repo.find_by_status(ReviewStatus.PUBLISHED)
        assert len(published_reviews) == 1
        assert published_reviews[0].title == "Published Review"
        
        pending_reviews = repo.find_by_status(ReviewStatus.PENDING)
        assert len(pending_reviews) == 1
        assert pending_reviews[0].title == "Pending Review"
    
    def test_find_by_rating_range(self, db_session):
        """Test finding reviews by rating range."""
        repo = ReviewRepository(db_session)
        
        # Create test data
        high_rating_review = ReviewFactory.create(
            rating=5,
            title="Excellent"
        )
        mid_rating_review = ReviewFactory.create(
            rating=3,
            title="Average"
        )
        low_rating_review = ReviewFactory.create(
            rating=1,
            title="Poor"
        )
        db_session.commit()
        
        # Test finding high ratings
        high_ratings = repo.find_by_rating_range(4, 5)
        assert len(high_ratings) == 1
        assert high_ratings[0].title == "Excellent"
        
        # Test finding all ratings
        all_ratings = repo.find_by_rating_range(1, 5)
        assert len(all_ratings) == 3
    
    def test_find_provider_reviews(self, db_session):
        """Test finding provider reviews."""
        repo = ReviewRepository(db_session)
        
        # Create test data
        provider_review = ReviewFactory.create(
            reviewee_id=2001,
            review_type=ReviewType.PROVIDER_REVIEW,
            status=ReviewStatus.PUBLISHED,
            title="Provider Review"
        )
        seeker_review_about_provider = ReviewFactory.create(
            reviewee_id=2001,
            review_type=ReviewType.SEEKER_REVIEW,  # Wrong type
            status=ReviewStatus.PUBLISHED,
            title="Wrong Type"
        )
        pending_provider_review = ReviewFactory.create(
            reviewee_id=2001,
            review_type=ReviewType.PROVIDER_REVIEW,
            status=ReviewStatus.PENDING,  # Wrong status
            title="Pending"
        )
        db_session.commit()
        
        # Test finding provider reviews
        provider_reviews = repo.find_provider_reviews(2001)
        assert len(provider_reviews) == 1
        assert provider_reviews[0].title == "Provider Review"
    
    def test_get_provider_rating_summary(self, db_session):
        """Test getting provider rating summary."""
        repo = ReviewRepository(db_session)
        
        # Create test data
        review_5 = ReviewFactory.create(
            reviewee_id=2001,
            review_type=ReviewType.PROVIDER_REVIEW,
            status=ReviewStatus.PUBLISHED,
            rating=5,
            created_at=datetime.now(timezone.utc) - timedelta(days=15)  # Recent
        )
        review_4 = ReviewFactory.create(
            reviewee_id=2001,
            review_type=ReviewType.PROVIDER_REVIEW,
            status=ReviewStatus.PUBLISHED,
            rating=4,
            created_at=datetime.now(timezone.utc) - timedelta(days=45)  # Not recent
        )
        review_3 = ReviewFactory.create(
            reviewee_id=2001,
            review_type=ReviewType.PROVIDER_REVIEW,
            status=ReviewStatus.PUBLISHED,
            rating=3,
            created_at=datetime.now(timezone.utc) - timedelta(days=10)  # Recent
        )
        db_session.commit()
        
        # Test getting rating summary
        summary = repo.get_provider_rating_summary(2001)
        assert summary["provider_id"] == 2001
        assert summary["total_reviews"] == 3
        assert summary["average_rating"] == 4.0  # (5 + 4 + 3) / 3
        assert summary["rating_distribution"][5] == 1
        assert summary["rating_distribution"][4] == 1
        assert summary["rating_distribution"][3] == 1
        assert summary["rating_distribution"][2] == 0
        assert summary["rating_distribution"][1] == 0
        assert summary["recent_reviews_count"] == 2  # Within last 30 days
    
    def test_find_pending_reviews(self, db_session):
        """Test finding pending reviews."""
        repo = ReviewRepository(db_session)
        
        # Create test data
        pending_old = ReviewFactory.create(
            status=ReviewStatus.PENDING,
            title="Pending Old",
            created_at=datetime.now(timezone.utc) - timedelta(days=2)
        )
        pending_new = ReviewFactory.create(
            status=ReviewStatus.PENDING,
            title="Pending New",
            created_at=datetime.now(timezone.utc) - timedelta(days=1)
        )
        published_review = ReviewFactory.create(
            status=ReviewStatus.PUBLISHED,
            title="Published"
        )
        db_session.commit()
        
        # Test finding pending reviews (should be ordered by creation date asc)
        pending_reviews = repo.find_pending_reviews()
        assert len(pending_reviews) == 2
        assert pending_reviews[0].title == "Pending Old"  # Oldest first
        assert pending_reviews[1].title == "Pending New"
    
    def test_find_recent_reviews(self, db_session):
        """Test finding recent reviews."""
        repo = ReviewRepository(db_session)
        
        # Create test data
        recent_review = ReviewFactory.create(
            status=ReviewStatus.PUBLISHED,
            title="Recent",
            created_at=datetime.now(timezone.utc) - timedelta(days=3)
        )
        old_review = ReviewFactory.create(
            status=ReviewStatus.PUBLISHED,
            title="Old",
            created_at=datetime.now(timezone.utc) - timedelta(days=10)
        )
        pending_recent = ReviewFactory.create(
            status=ReviewStatus.PENDING,
            title="Pending Recent",
            created_at=datetime.now(timezone.utc) - timedelta(days=1)
        )
        db_session.commit()
        
        # Test finding recent reviews (last 7 days, published only)
        recent_reviews = repo.find_recent_reviews(7)
        assert len(recent_reviews) == 1
        assert recent_reviews[0].title == "Recent"
    
    def test_search_reviews(self, db_session):
        """Test searching reviews by content."""
        repo = ReviewRepository(db_session)
        
        # Create test data
        title_match = ReviewFactory.create(
            status=ReviewStatus.PUBLISHED,
            title="Excellent plumbing work",
            comment="Great job overall"
        )
        comment_match = ReviewFactory.create(
            status=ReviewStatus.PUBLISHED,
            title="Good service",
            comment="The plumbing was done professionally"
        )
        no_match = ReviewFactory.create(
            status=ReviewStatus.PUBLISHED,
            title="Electrical work",
            comment="Great electrical installation"
        )
        pending_match = ReviewFactory.create(
            status=ReviewStatus.PENDING,
            title="Plumbing review",
            comment="Good work"
        )
        db_session.commit()
        
        # Test searching for "plumbing"
        search_results = repo.search_reviews("plumbing")
        assert len(search_results) == 2  # Only published reviews
        titles = [r.title for r in search_results]
        assert "Excellent plumbing work" in titles
        assert "Good service" in titles
    
    def test_get_review_statistics(self, db_session):
        """Test getting review statistics."""
        repo = ReviewRepository(db_session)
        
        # Create test data
        published_provider = ReviewFactory.create(
            status=ReviewStatus.PUBLISHED,
            review_type=ReviewType.PROVIDER_REVIEW,
            rating=4
        )
        published_seeker = ReviewFactory.create(
            status=ReviewStatus.PUBLISHED,
            review_type=ReviewType.SEEKER_REVIEW,
            rating=5
        )
        pending_review = ReviewFactory.create(
            status=ReviewStatus.PENDING,
            review_type=ReviewType.PROVIDER_REVIEW,
            rating=3
        )
        flagged_review = ReviewFactory.create(
            status=ReviewStatus.FLAGGED,
            review_type=ReviewType.PROVIDER_REVIEW,
            rating=2
        )
        db_session.commit()
        
        # Test getting statistics
        stats = repo.get_review_statistics()
        assert stats["total_reviews"] == 4
        assert stats["published_reviews"] == 2
        assert stats["pending_reviews"] == 1
        assert stats["flagged_reviews"] == 1
        assert stats["average_rating"] == 4.5  # (4 + 5) / 2 (only published)
        assert stats["provider_reviews"] == 3
        assert stats["seeker_reviews"] == 1
    
    def test_find_mutual_reviews(self, db_session):
        """Test finding mutual reviews between users."""
        repo = ReviewRepository(db_session)
        
        # Create test data
        user_1_about_2 = ReviewFactory.create(
            reviewer_id=1001,
            reviewee_id=1002,
            title="User 1 about User 2"
        )
        user_2_about_1 = ReviewFactory.create(
            reviewer_id=1002,
            reviewee_id=1001,
            title="User 2 about User 1"
        )
        unrelated_review = ReviewFactory.create(
            reviewer_id=1003,
            reviewee_id=1004,
            title="Unrelated"
        )
        db_session.commit()
        
        # Test finding mutual reviews
        mutual_reviews = repo.find_mutual_reviews(1001, 1002)
        assert len(mutual_reviews) == 2
        titles = [r.title for r in mutual_reviews]
        assert "User 1 about User 2" in titles
        assert "User 2 about User 1" in titles
    
    @pytest.mark.asyncio
    async def test_update_review_status(self, db_session):
        """Test updating review status."""
        repo = ReviewRepository(db_session)
        
        # Create test data
        review = ReviewFactory.create(
            status=ReviewStatus.PENDING,
            title="Test Review"
        )
        db_session.commit()
        
        # Test updating to PUBLISHED
        updated_review = await repo.update_review_status(
            review.id, 
            ReviewStatus.PUBLISHED, 
            "Approved by moderator"
        )
        assert updated_review.status == ReviewStatus.PUBLISHED
        assert updated_review.moderator_notes == "Approved by moderator"
        assert updated_review.published_at is not None
    
    def test_get_top_reviewers(self, db_session):
        """Test getting top reviewers."""
        repo = ReviewRepository(db_session)
        
        # Create test data
        # Reviewer 1: 6 reviews, avg rating 4.0
        for i in range(6):
            ReviewFactory.create(
                reviewer_id=1001,
                status=ReviewStatus.PUBLISHED,
                rating=4
            )
        
        # Reviewer 2: 5 reviews, avg rating 5.0
        for i in range(5):
            ReviewFactory.create(
                reviewer_id=1002,
                status=ReviewStatus.PUBLISHED,
                rating=5
            )
        
        # Reviewer 3: 3 reviews (below minimum)
        for i in range(3):
            ReviewFactory.create(
                reviewer_id=1003,
                status=ReviewStatus.PUBLISHED,
                rating=3
            )
        
        db_session.commit()
        
        # Test getting top reviewers (minimum 5 reviews)
        top_reviewers = repo.get_top_reviewers(limit=10, min_reviews=5)
        assert len(top_reviewers) == 2
        
        # Should be ordered by review count (descending)
        assert top_reviewers[0]["reviewer_id"] == 1001
        assert top_reviewers[0]["review_count"] == 6
        assert top_reviewers[0]["avg_rating_given"] == 4.0
        
        assert top_reviewers[1]["reviewer_id"] == 1002
        assert top_reviewers[1]["review_count"] == 5
        assert top_reviewers[1]["avg_rating_given"] == 5.0