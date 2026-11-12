"""
RED Phase: Failing tests for ReviewService
Following TDD methodology - these tests define expected behavior before implementation
"""
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, Mock

import pytest
from src.core.exceptions import (AuthorizationError, BusinessLogicError,
                                 ReviewNotFoundError, ValidationError)
from src.models.booking import Booking, BookingStatus
from src.models.review import Review, ReviewerType


class TestReviewService:
    """Test suite for ReviewService - RED phase (failing tests)"""

    @pytest.fixture
    def mock_review_repository(self):
        """Mock review repository for testing"""
        mock = Mock()
        mock.create = AsyncMock()
        mock.save = AsyncMock()  # Add AsyncMock for save method
        mock.get_by_id = AsyncMock()
        mock.update = AsyncMock()
        mock.get_by_booking_id = AsyncMock()
        mock.get_by_booking_and_reviewer = AsyncMock()
        mock.get_by_reviewee_id = Mock(return_value=[])
        mock.get_provider_reviews = Mock(return_value=[])
        mock.search_by_criteria = AsyncMock()
        mock.get_analytics = Mock()
        mock.add_flag = Mock()
        mock.moderate = AsyncMock()
        mock.add_response = Mock()
        mock.mark_helpful = AsyncMock()
        mock.has_user_marked_helpful = AsyncMock()
        mock.get_recent_reviews = AsyncMock()
        mock.calculate_aggregate_ratings = Mock()
        return mock

    @pytest.fixture
    def mock_booking_repository(self):
        """Mock booking repository for testing"""
        mock = Mock()
        mock.get_by_id = AsyncMock()
        return mock

    @pytest.fixture
    def mock_provider_repository(self):
        """Mock provider repository for testing"""
        mock = Mock()
        mock.get_by_id = AsyncMock()
        mock.update = AsyncMock()
        mock.save = AsyncMock()  # Add AsyncMock for save methodLiterally
        mock.bulk_update_ratings = AsyncMock()
        return mock

    @pytest.fixture
    def mock_notification_service(self):
        """Mock notification service for testing"""
        return Mock()

    @pytest.fixture
    def review_service(
        self,
        mock_review_repository,
        mock_booking_repository,
        mock_provider_repository,
        mock_notification_service,
    ):
        """Create ReviewService instance with mocked dependencies"""
        # This import will fail until ReviewService is implemented
        from src.services.review_service import ReviewService

        return ReviewService(
            review_repository=mock_review_repository,
            booking_repository=mock_booking_repository,
            provider_repository=mock_provider_repository,
            notification_service=mock_notification_service,
        )

    @pytest.fixture
    def completed_booking(self):
        """Sample completed booking for review testing"""
        return Booking(
            id=1,
            service_request_id=1,
            provider_id=1,
            client_id=2,
            quote_id=1,
            status=BookingStatus.COMPLETED,
            scheduled_start_date=datetime.now(timezone.utc) - timedelta(days=2),
            scheduled_completion_date=datetime.now(timezone.utc) - timedelta(days=1),
            actual_completion_date=datetime.now(timezone.utc) - timedelta(days=1),
            total_cost=Decimal("1000.00"),
        )

    @pytest.fixture
    def sample_provider_review_data(self):
        """Sample review data for provider"""
        return {
            "booking_id": 1,
            "reviewer_id": 2,  # Seeker reviewing provider
            "reviewee_id": 1,  # Provider being reviewed
            "reviewer_type": ReviewerType.PROVIDER,  # SEEKER_TO_PROVIDER
            "rating": 5,
            "title": "Excellent electrical work",
            "content": "John did outstanding work on our kitchen electrical. Professional, on time, and clean work.",
            "categories": {
                "quality": 5,
                "timeliness": 5,
                "communication": 4,
                "professionalism": 5,
                "value": 4,
            },
        }

    @pytest.fixture
    def sample_seeker_review_data(self):
        """Sample review data for seeker"""
        return {
            "booking_id": 1,
            "reviewer_id": 1,  # Provider reviewing seeker
            "reviewee_id": 2,  # Seeker being reviewed
            "reviewer_type": ReviewerType.SEEKER,  # PROVIDER_TO_SEEKER
            "rating": 4,
            "title": "Good client to work with",
            "content": "Clear requirements, prompt payment, and respectful throughout the project.",
            "categories": {
                "communication": 4,
                "payment_promptness": 5,
                "project_clarity": 4,
                "respectfulness": 5,
            },
        }

    # Review Submission Tests
    @pytest.mark.asyncio
    async def test_submit_provider_review(
        self,
        review_service,
        mock_review_repository,
        mock_booking_repository,
        mock_provider_repository,
        completed_booking,
        sample_provider_review_data,
    ):
        """Test submitting review for provider"""
        # This test will fail until ReviewService.submit_review is implemented
        mock_booking_repository.get_by_id.return_value = completed_booking
        mock_review_repository.get_by_booking_and_reviewer.return_value = (
            None  # No existing review
        )
        mock_review_repository.get_provider_reviews.return_value = (
            []
        )  # No existing reviews for rating calculation
        mock_review_repository.get_by_reviewee_id.return_value = (
            []
        )  # No existing reviews for rating calculation

        # Mock provider for rating update
        from src.models.service_provider import ServiceProvider

        mock_provider = ServiceProvider(id=1, user_id=1, business_name="Test Provider")
        mock_provider_repository.get_by_id.return_value = mock_provider
        mock_provider_repository.update.return_value = mock_provider

        expected_review = Review(
            id=1,
            booking_id=sample_provider_review_data["booking_id"],
            reviewer_id=sample_provider_review_data["reviewer_id"],
            reviewee_id=sample_provider_review_data["reviewee_id"],
            reviewer_type=sample_provider_review_data["reviewer_type"],
            rating=sample_provider_review_data["rating"],
            title=sample_provider_review_data["title"],
            content=sample_provider_review_data["content"],
            is_verified=True,
            created_at=datetime.now(timezone.utc),
        )
        mock_review_repository.create.return_value = expected_review

        result = await review_service.submit_review(sample_provider_review_data)

        assert result is not None
        assert result.rating == 5
        assert result.reviewer_type == ReviewerType.SEEKER
        assert result.is_verified is True
        mock_review_repository.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_submit_seeker_review(
        self,
        review_service,
        mock_review_repository,
        mock_booking_repository,
        completed_booking,
        sample_seeker_review_data,
    ):
        """Test submitting review for seeker"""
        mock_booking_repository.get_by_id.return_value = completed_booking
        mock_review_repository.get_by_booking_and_reviewer.return_value = (
            None  # No existing review
        )

        expected_review = Review(
            id=2,
            booking_id=sample_seeker_review_data["booking_id"],
            reviewer_id=sample_seeker_review_data["reviewer_id"],
            reviewee_id=sample_seeker_review_data["reviewee_id"],
            reviewer_type=sample_seeker_review_data["reviewer_type"],
            rating=sample_seeker_review_data["rating"],
            is_verified=True,
        )
        mock_review_repository.create.return_value = expected_review

        result = await review_service.submit_review(sample_seeker_review_data)

        assert result.rating == 4
        assert result.reviewer_type == ReviewerType.PROVIDER
        mock_review_repository.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_cannot_review_incomplete_booking(
        self, review_service, mock_booking_repository, sample_provider_review_data
    ):
        """Test that reviews cannot be submitted for incomplete bookings"""
        incomplete_booking = Booking(
            id=1, status=BookingStatus.IN_PROGRESS  # Not completed
        )
        mock_booking_repository.get_by_id.return_value = incomplete_booking

        with pytest.raises(
            BusinessLogicError, match="Can only review completed bookings"
        ):
            await review_service.submit_review(sample_provider_review_data)

    @pytest.mark.asyncio
    async def test_cannot_submit_duplicate_review(
        self,
        review_service,
        mock_review_repository,
        mock_booking_repository,
        completed_booking,
        sample_provider_review_data,
    ):
        """Test that duplicate reviews cannot be submitted"""
        mock_booking_repository.get_by_id.return_value = completed_booking

        # Existing review from same reviewer for same booking
        existing_review = Review(
            id=1,
            booking_id=1,
            reviewer_id=2,
            reviewee_id=1,
            reviewer_type=ReviewerType.SEEKER,
        )
        mock_review_repository.get_by_booking_and_reviewer.return_value = (
            existing_review
        )

        with pytest.raises(
            BusinessLogicError, match="Review already submitted for this booking"
        ):
            await review_service.submit_review(sample_provider_review_data)

    @pytest.mark.asyncio
    async def test_review_validation(self, review_service, sample_provider_review_data):
        """Test review data validation"""
        # Invalid rating
        sample_provider_review_data["rating"] = 6  # Rating must be 1-5

        with pytest.raises(ValidationError, match="Rating must be between 1 and 5"):
            await review_service.submit_review(sample_provider_review_data)

    # Review Retrieval Tests
    @pytest.mark.asyncio
    async def test_get_review_success(self, review_service, mock_review_repository):
        """Test successful review retrieval"""
        expected_review = Review(
            id=1,
            booking_id=1,
            reviewer_id=2,
            reviewee_id=1,
            rating=5,
            title="Great work",
        )
        mock_review_repository.get_by_id.return_value = expected_review

        result = await review_service.get_review(1)

        assert result == expected_review
        mock_review_repository.get_by_id.assert_called_once_with(1)

    @pytest.mark.asyncio
    async def test_get_review_not_found(self, review_service, mock_review_repository):
        """Test review retrieval when review doesn't exist"""
        mock_review_repository.get_by_id.return_value = None

        with pytest.raises(ReviewNotFoundError):
            await review_service.get_review(999)

    @pytest.mark.asyncio
    async def test_get_reviews_for_provider(
        self, review_service, mock_review_repository
    ):
        """Test retrieving all reviews for a provider"""
        provider_id = 1
        expected_reviews = [
            Review(id=1, reviewee_id=1, rating=5, title="Excellent work"),
            Review(id=2, reviewee_id=1, rating=4, title="Good service"),
            Review(id=3, reviewee_id=1, rating=5, title="Professional"),
        ]
        mock_review_repository.get_by_reviewee_id.return_value = expected_reviews

        result = await review_service.get_reviews_for_provider(provider_id)

        assert len(result) == 3
        assert all(review.reviewee_id == provider_id for review in result)
        mock_review_repository.get_by_reviewee_id.assert_called_once_with(provider_id)

    @pytest.mark.asyncio
    async def test_get_reviews_for_seeker(self, review_service, mock_review_repository):
        """Test retrieving all reviews for a seeker"""
        seeker_id = 2
        expected_reviews = [
            Review(id=4, reviewee_id=2, rating=4, title="Good client"),
            Review(id=5, reviewee_id=2, rating=5, title="Easy to work with"),
        ]
        mock_review_repository.get_by_reviewee_id.return_value = expected_reviews

        result = await review_service.get_reviews_for_seeker(seeker_id)

        assert len(result) == 2
        assert all(review.reviewee_id == seeker_id for review in result)
        mock_review_repository.get_by_reviewee_id.assert_called_once_with(seeker_id)

    # Review Analytics Tests
    @pytest.mark.asyncio
    async def test_calculate_provider_rating(
        self, review_service, mock_review_repository
    ):
        """Test calculating aggregate rating for provider"""
        provider_id = 1
        provider_reviews = [
            Review(id=1, reviewee_id=1, rating=5),
            Review(id=2, reviewee_id=1, rating=4),
            Review(id=3, reviewee_id=1, rating=5),
            Review(id=4, reviewee_id=1, rating=3),
            Review(id=5, reviewee_id=1, rating=4),
        ]
        mock_review_repository.get_by_reviewee_id.return_value = provider_reviews

        result = await review_service.calculate_aggregate_rating(provider_id)

        # Average: (5+4+5+3+4)/5 = 4.2
        assert result["average_rating"] == 4.2
        assert result["total_reviews"] == 5
        assert result["rating_distribution"] == {5: 2, 4: 2, 3: 1, 2: 0, 1: 0}

    @pytest.mark.asyncio
    async def test_get_review_analytics(self, review_service, mock_review_repository):
        """Test retrieving detailed review analytics"""
        reviewee_id = 1
        expected_analytics = {
            "overall_rating": 4.6,
            "total_reviews": 25,
            "category_averages": {
                "quality": 4.8,
                "timeliness": 4.5,
                "communication": 4.4,
                "professionalism": 4.7,
                "value": 4.3,
            },
            "recent_trend": "improving",  # Last 10 reviews vs previous 10
            "response_rate": 0.85,  # Percentage of bookings that received reviews
        }
        mock_review_repository.get_analytics.return_value = expected_analytics

        result = await review_service.get_review_analytics(reviewee_id)

        assert result["overall_rating"] == 4.6
        assert result["category_averages"]["quality"] == 4.8
        assert result["recent_trend"] == "improving"
        mock_review_repository.get_analytics.assert_called_once_with(reviewee_id)

    # Review Moderation Tests
    @pytest.mark.asyncio
    async def test_flag_inappropriate_review(
        self, review_service, mock_review_repository, mock_notification_service
    ):
        """Test flagging review for inappropriate content"""
        review = Review(
            id=1,
            content="This review contains inappropriate language",
            is_verified=True,
        )
        mock_review_repository.get_by_id.return_value = review

        result = await review_service.flag_review(
            1, "inappropriate_language", flagger_id=3
        )

        assert result is True
        mock_review_repository.add_flag.assert_called_once()
        mock_notification_service.notify_review_flagged.assert_called_once()

    @pytest.mark.asyncio
    async def test_moderate_review(self, review_service, mock_review_repository):
        """Test moderating a flagged review"""
        flagged_review = Review(id=1, content="Flagged content", is_verified=True)
        mock_review_repository.get_by_id.return_value = flagged_review

        moderated_review = Review(
            id=1, content="[Content removed by moderator]", is_verified=False
        )
        mock_review_repository.update.return_value = moderated_review

        result = await review_service.moderate_review(
            1, "content_removed", moderator_id=100
        )

        assert result.is_verified is False
        mock_review_repository.update.assert_called_once()

    # Review Responses Tests
    @pytest.mark.asyncio
    async def test_respond_to_review(
        self, review_service, mock_review_repository, mock_notification_service
    ):
        """Test provider responding to a review"""
        review = Review(
            id=1,
            reviewee_id=1,  # Provider being reviewed
            reviewer_id=2,
            content="Good work but could be faster",
        )
        mock_review_repository.get_by_id.return_value = review

        response_data = {
            "content": "Thank you for the feedback. We'll work on improving our timeline efficiency.",
            "responder_id": 1,  # Provider responding
        }

        result = await review_service.respond_to_review(1, response_data)

        assert result is True
        mock_review_repository.add_response.assert_called_once()
        mock_notification_service.notify_review_response.assert_called_once()

    @pytest.mark.asyncio
    async def test_cannot_respond_to_own_review(
        self, review_service, mock_review_repository
    ):
        """Test that reviewers cannot respond to their own reviews"""
        review = Review(id=1, reviewer_id=2, reviewee_id=1)
        mock_review_repository.get_by_id.return_value = review

        response_data = {
            "content": "Thanks for the review!",
            "responder_id": 2,  # Same as reviewer_id
        }

        with pytest.raises(
            AuthorizationError, match="Only reviewee can respond to review"
        ):
            await review_service.respond_to_review(1, response_data)

    # Review Helpfulness Tests
    @pytest.mark.asyncio
    async def test_mark_review_helpful(self, review_service, mock_review_repository):
        """Test marking a review as helpful"""
        review = Review(id=1, helpful_votes=5)
        mock_review_repository.get_by_id.return_value = review
        mock_review_repository.has_user_marked_helpful.return_value = (
            False  # User hasn't marked it yet
        )

        updated_review = Review(id=1, helpful_votes=6)
        mock_review_repository.update.return_value = updated_review

        result = await review_service.mark_helpful(1, user_id=3)

        assert result.helpful_votes == 6
        mock_review_repository.update.assert_called_once()

    @pytest.mark.asyncio
    async def test_cannot_mark_own_review_helpful(
        self, review_service, mock_review_repository
    ):
        """Test that users cannot mark their own reviews as helpful"""
        review = Review(id=1, reviewer_id=2, helpful_votes=5)
        mock_review_repository.get_by_id.return_value = review

        with pytest.raises(
            BusinessLogicError, match="Cannot mark your own review as helpful"
        ):
            await review_service.mark_helpful(1, user_id=2)

    # Review Search and Filtering Tests
    @pytest.mark.asyncio
    async def test_search_reviews_by_rating(
        self, review_service, mock_review_repository
    ):
        """Test searching reviews by rating range"""
        search_criteria = {"reviewee_id": 1, "min_rating": 4, "max_rating": 5}

        expected_reviews = [
            Review(id=1, reviewee_id=1, rating=5),
            Review(id=2, reviewee_id=1, rating=4),
            Review(id=3, reviewee_id=1, rating=5),
        ]
        mock_review_repository.search_by_criteria.return_value = expected_reviews

        result = await review_service.search_reviews(search_criteria)

        assert len(result) == 3
        assert all(4 <= review.rating <= 5 for review in result)
        mock_review_repository.search_by_criteria.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_recent_reviews(self, review_service, mock_review_repository):
        """Test retrieving recent reviews"""
        days_back = 30
        expected_reviews = [
            Review(id=1, created_at=datetime.now(timezone.utc) - timedelta(days=5)),
            Review(id=2, created_at=datetime.now(timezone.utc) - timedelta(days=15)),
            Review(id=3, created_at=datetime.now(timezone.utc) - timedelta(days=25)),
        ]
        mock_review_repository.get_recent_reviews.return_value = expected_reviews

        result = await review_service.get_recent_reviews(days_back)

        assert len(result) == 3
        mock_review_repository.get_recent_reviews.assert_called_once_with(days_back)

    # Review Verification Tests
    @pytest.mark.asyncio
    async def test_verify_review_authenticity(
        self, review_service, mock_review_repository, mock_booking_repository
    ):
        """Test verifying that review comes from actual booking"""
        review = Review(
            id=1, booking_id=1, reviewer_id=2, reviewee_id=1, is_verified=False
        )
        mock_review_repository.get_by_id.return_value = review

        # Verify booking exists and reviewer was participant
        booking = Booking(
            id=1,
            seeker_id=2,  # Matches reviewer_id
            provider_id=1,  # Matches reviewee_id
            status=BookingStatus.COMPLETED,
        )
        mock_booking_repository.get_by_id.return_value = booking

        verified_review = Review(
            id=1, booking_id=1, reviewer_id=2, reviewee_id=1, is_verified=True
        )
        mock_review_repository.update.return_value = verified_review

        result = await review_service.verify_review(1)

        assert result.is_verified is True
        mock_review_repository.update.assert_called_once()

    @pytest.mark.asyncio
    async def test_bulk_update_provider_ratings(
        self, review_service, mock_review_repository, mock_provider_repository
    ):
        """Test bulk updating provider ratings after new reviews"""
        provider_ids = [1, 2, 3]

        # Mock aggregated ratings for each provider
        rating_updates = [
            {"provider_id": 1, "new_rating": 4.6, "total_reviews": 25},
            {"provider_id": 2, "new_rating": 4.2, "total_reviews": 18},
            {"provider_id": 3, "new_rating": 4.8, "total_reviews": 32},
        ]
        mock_review_repository.calculate_aggregate_ratings.return_value = rating_updates

        result = await review_service.update_provider_ratings(provider_ids)

        assert result == 3  # Number of providers updated
        mock_provider_repository.bulk_update_ratings.assert_called_once_with(
            rating_updates
        )

    # Error Handling Tests
    @pytest.mark.asyncio
    async def test_review_service_handles_repository_errors(
        self, review_service, mock_review_repository
    ):
        """Test that service properly handles repository errors"""
        mock_review_repository.get_by_id.side_effect = Exception(
            "Database connection failed"
        )

        with pytest.raises(Exception, match="Database connection failed"):
            await review_service.get_review(1)

    @pytest.mark.asyncio
    async def test_validation_error_on_invalid_review_data(self, review_service):
        """Test validation errors for invalid review data"""
        invalid_data = {
            "booking_id": None,  # Required field missing
            "reviewer_id": None,  # Required field missing
            "rating": 0,  # Invalid rating
            "content": "",  # Empty content
        }

        with pytest.raises(ValidationError):
            await review_service.submit_review(invalid_data)
