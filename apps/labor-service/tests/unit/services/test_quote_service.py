"""
RED Phase: Failing tests for QuoteService
Following TDD methodology - these tests define expected behavior before implementation
"""
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, Mock

import pytest
from src.core.exceptions import (BusinessLogicError, QuoteNotFoundError,
                                 ValidationError)
from src.models.quote import Quote, QuoteStatus
from src.models.service_provider import ServiceProvider
from src.models.service_request import RequestStatus, ServiceRequest


class TestQuoteService:
    """Test suite for QuoteService - RED phase (failing tests)"""

    @pytest.fixture
    def mock_quote_repository(self):
        """Mock quote repository for testing"""
        mock = Mock()
        mock.create = AsyncMock()
        mock.get_by_id = AsyncMock()
        mock.update = AsyncMock()
        mock.get_by_request_id = AsyncMock()
        mock.get_by_provider_id = AsyncMock()
        mock.get_by_request_and_provider = AsyncMock()
        mock.get_analytics = AsyncMock()
        mock.expire_quotes_before = AsyncMock()
        mock.get_provider_stats = AsyncMock()
        mock.get_provider_statistics = AsyncMock()
        mock.bulk_update_status = AsyncMock()
        mock.get_multiple_by_ids = AsyncMock()
        return mock

    @pytest.fixture
    def mock_request_repository(self):
        """Mock request repository for testing"""
        mock = Mock()
        mock.get_by_id = AsyncMock()
        return mock

    @pytest.fixture
    def mock_provider_repository(self):
        """Mock provider repository for testing"""
        mock = Mock()
        mock.get_by_id = AsyncMock()
        return mock

    @pytest.fixture
    def mock_notification_service(self):
        """Mock notification service for testing"""
        mock = Mock()
        mock.notify_quote_accepted = AsyncMock()
        return mock

    @pytest.fixture
    def quote_service(
        self,
        mock_quote_repository,
        mock_request_repository,
        mock_provider_repository,
        mock_notification_service,
    ):
        """Create QuoteService instance with mocked dependencies"""
        # This import will fail until QuoteService is implemented
        from src.services.quote_service import QuoteService

        return QuoteService(
            quote_repository=mock_quote_repository,
            request_repository=mock_request_repository,
            provider_repository=mock_provider_repository,
            notification_service=mock_notification_service,
        )

    @pytest.fixture
    def sample_quote_data(self):
        """Sample quote submission data"""
        return {
            "request_id": 1,
            "provider_id": 1,
            "labor_cost": Decimal("2000.00"),
            "material_cost": Decimal("500.00"),
            "travel_cost": Decimal("100.00"),
            "estimated_hours": 16,
            "start_availability": datetime.now(timezone.utc) + timedelta(days=3),
            "completion_estimate": datetime.now(timezone.utc) + timedelta(days=5),
            "terms": "Payment due upon completion. Materials included in quote.",
            "valid_until": datetime.now(timezone.utc) + timedelta(days=7),
            "notes": "Can start earlier if needed. Flexible on scheduling.",
        }

    @pytest.fixture
    def sample_request(self):
        """Sample service request for testing"""
        return ServiceRequest(
            id=1,
            seeker_id=2,
            title="Kitchen Electrical Work",
            status=RequestStatus.ACTIVE,
            budget_min=Decimal("1500.00"),
            budget_max=Decimal("3000.00"),
        )

    @pytest.fixture
    def sample_provider(self):
        """Sample service provider for testing"""
        return ServiceProvider(
            id=1, user_id=1, individual_name="John Smith", rating=4.5
        )

    # Quote Submission Tests
    @pytest.mark.asyncio
    async def test_submit_quote_success(
        self,
        quote_service,
        mock_quote_repository,
        mock_request_repository,
        mock_provider_repository,
        sample_quote_data,
        sample_request,
        sample_provider,
    ):
        """Test successful quote submission"""
        # This test will fail until QuoteService.submit_quote is implemented
        mock_request_repository.get_by_id.return_value = sample_request
        mock_provider_repository.get_by_id.return_value = sample_provider
        mock_quote_repository.get_by_request_and_provider.return_value = (
            None  # No existing quote
        )

        expected_quote = Quote(
            id=1,
            request_id=sample_quote_data["request_id"],
            provider_id=sample_quote_data["provider_id"],
            labor_cost=sample_quote_data["labor_cost"],
            material_cost=sample_quote_data["material_cost"],
            travel_cost=sample_quote_data["travel_cost"],
            total_cost=Decimal("2600.00"),  # Sum of all costs
            status=QuoteStatus.SUBMITTED,
            created_at=datetime.now(timezone.utc),
        )
        mock_quote_repository.create.return_value = expected_quote

        result = await quote_service.submit_quote(sample_quote_data)

        assert result is not None
        assert result.total_cost == Decimal("2600.00")
        assert result.status == QuoteStatus.SUBMITTED
        mock_quote_repository.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_submit_quote_for_inactive_request(
        self, quote_service, mock_request_repository, sample_quote_data
    ):
        """Test quote submission for inactive request fails"""
        inactive_request = ServiceRequest(id=1, status=RequestStatus.CANCELLED)
        mock_request_repository.get_by_id.return_value = inactive_request

        with pytest.raises(
            BusinessLogicError, match="Cannot submit quote for inactive request"
        ):
            await quote_service.submit_quote(sample_quote_data)

    @pytest.mark.asyncio
    async def test_submit_quote_exceeds_budget(
        self,
        quote_service,
        mock_request_repository,
        mock_provider_repository,
        sample_quote_data,
        sample_provider,
    ):
        """Test quote submission that exceeds request budget"""
        high_budget_request = ServiceRequest(
            id=1,
            status=RequestStatus.ACTIVE,
            budget_max=Decimal("2000.00"),  # Lower than quote total
        )
        mock_request_repository.get_by_id.return_value = high_budget_request
        mock_provider_repository.get_by_id.return_value = sample_provider

        # Mock no existing quote to avoid duplicate error
        mock_quote_repository = quote_service.quote_repository
        mock_quote_repository.get_by_request_and_provider.return_value = None

        sample_quote_data["labor_cost"] = Decimal("2500.00")  # Will exceed budget

        with pytest.raises(ValidationError, match="Quote exceeds maximum budget"):
            await quote_service.submit_quote(sample_quote_data)

    @pytest.mark.asyncio
    async def test_submit_duplicate_quote(
        self,
        quote_service,
        mock_quote_repository,
        mock_request_repository,
        mock_provider_repository,
        sample_quote_data,
        sample_request,
        sample_provider,
    ):
        """Test that provider cannot submit duplicate quotes"""
        mock_request_repository.get_by_id.return_value = sample_request
        mock_provider_repository.get_by_id.return_value = sample_provider

        # Existing quote from same provider
        existing_quote = Quote(
            id=1, request_id=1, provider_id=1, status=QuoteStatus.SUBMITTED
        )
        mock_quote_repository.get_by_request_and_provider.return_value = existing_quote

        with pytest.raises(
            BusinessLogicError, match="Provider has already submitted a quote"
        ):
            await quote_service.submit_quote(sample_quote_data)

    # Quote Management Tests
    @pytest.mark.asyncio
    async def test_get_quote_success(self, quote_service, mock_quote_repository):
        """Test successful quote retrieval"""
        expected_quote = Quote(
            id=1,
            request_id=1,
            provider_id=1,
            total_cost=Decimal("2500.00"),
            status=QuoteStatus.SUBMITTED,
        )
        mock_quote_repository.get_by_id.return_value = expected_quote

        result = await quote_service.get_quote(1)

        assert result == expected_quote
        mock_quote_repository.get_by_id.assert_called_once_with(1)

    @pytest.mark.asyncio
    async def test_get_quote_not_found(self, quote_service, mock_quote_repository):
        """Test quote retrieval when quote doesn't exist"""
        mock_quote_repository.get_by_id.return_value = None

        with pytest.raises(QuoteNotFoundError):
            await quote_service.get_quote(999)

    @pytest.mark.asyncio
    async def test_update_quote(self, quote_service, mock_quote_repository):
        """Test updating an existing quote"""
        existing_quote = Quote(
            id=1,
            request_id=1,
            provider_id=1,
            labor_cost=Decimal("2000.00"),
            status=QuoteStatus.DRAFT,
        )
        mock_quote_repository.get_by_id.return_value = existing_quote

        update_data = {
            "labor_cost": Decimal("2200.00"),
            "notes": "Updated pricing based on site visit",
        }

        updated_quote = Quote(
            id=1,
            request_id=1,
            provider_id=1,
            labor_cost=Decimal("2200.00"),
            total_cost=Decimal("2200.00"),
            status=QuoteStatus.DRAFT,
        )
        mock_quote_repository.update.return_value = updated_quote

        result = await quote_service.update_quote(1, update_data)

        assert result.labor_cost == Decimal("2200.00")
        mock_quote_repository.update.assert_called_once()

    @pytest.mark.asyncio
    async def test_cannot_update_accepted_quote(
        self, quote_service, mock_quote_repository
    ):
        """Test that accepted quotes cannot be updated"""
        accepted_quote = Quote(
            id=1, request_id=1, provider_id=1, status=QuoteStatus.ACCEPTED
        )
        mock_quote_repository.get_by_id.return_value = accepted_quote

        with pytest.raises(BusinessLogicError, match="Cannot update accepted quote"):
            await quote_service.update_quote(1, {"labor_cost": Decimal("2500.00")})

    # Quote Acceptance Tests
    @pytest.mark.asyncio
    async def test_accept_quote(
        self,
        quote_service,
        mock_quote_repository,
        mock_request_repository,
        mock_notification_service,
    ):
        """Test accepting a quote"""
        submitted_quote = Quote(
            id=1, request_id=1, provider_id=1, status=QuoteStatus.SUBMITTED
        )
        mock_quote_repository.get_by_id.return_value = submitted_quote

        request = ServiceRequest(id=1, seeker_id=2, status=RequestStatus.ACTIVE)
        mock_request_repository.get_by_id.return_value = request

        accepted_quote = Quote(
            id=1, request_id=1, provider_id=1, status=QuoteStatus.ACCEPTED
        )
        mock_quote_repository.update.return_value = accepted_quote

        result = await quote_service.accept_quote(1, seeker_id=2)

        assert result.status == QuoteStatus.ACCEPTED
        mock_quote_repository.update.assert_called_once()
        mock_notification_service.notify_quote_accepted.assert_called_once()

    @pytest.mark.asyncio
    async def test_accept_quote_unauthorized(
        self, quote_service, mock_quote_repository, mock_request_repository
    ):
        """Test that only request owner can accept quotes"""
        quote = Quote(id=1, request_id=1, provider_id=1, status=QuoteStatus.SUBMITTED)
        mock_quote_repository.get_by_id.return_value = quote

        request = ServiceRequest(id=1, seeker_id=2, status=RequestStatus.ACTIVE)
        mock_request_repository.get_by_id.return_value = request

        # Different user trying to accept
        with pytest.raises(
            BusinessLogicError, match="Only request owner can accept quotes"
        ):
            await quote_service.accept_quote(1, seeker_id=3)

    @pytest.mark.asyncio
    async def test_reject_other_quotes_on_acceptance(
        self, quote_service, mock_quote_repository, mock_request_repository
    ):
        """Test that other quotes are rejected when one is accepted"""
        accepted_quote = Quote(
            id=1, request_id=1, provider_id=1, status=QuoteStatus.SUBMITTED
        )
        mock_quote_repository.get_by_id.return_value = accepted_quote

        request = ServiceRequest(id=1, seeker_id=2, status=RequestStatus.ACTIVE)
        mock_request_repository.get_by_id.return_value = request

        other_quotes = [
            Quote(id=2, request_id=1, provider_id=2, status=QuoteStatus.SUBMITTED),
            Quote(id=3, request_id=1, provider_id=3, status=QuoteStatus.SUBMITTED),
        ]
        mock_quote_repository.get_by_request_id.return_value = other_quotes

        await quote_service.accept_quote(1, seeker_id=2)

        # Should reject other quotes
        mock_quote_repository.bulk_update_status.assert_called_once()

    # Quote Comparison Tests
    @pytest.mark.asyncio
    async def test_get_quotes_for_request(self, quote_service, mock_quote_repository):
        """Test retrieving all quotes for a request"""
        request_id = 1
        expected_quotes = [
            Quote(id=1, request_id=1, provider_id=1, total_cost=Decimal("2500.00")),
            Quote(id=2, request_id=1, provider_id=2, total_cost=Decimal("2800.00")),
            Quote(id=3, request_id=1, provider_id=3, total_cost=Decimal("2200.00")),
        ]
        mock_quote_repository.get_by_request_id.return_value = expected_quotes

        result = await quote_service.get_quotes_for_request(request_id)

        assert len(result) == 3
        assert all(quote.request_id == request_id for quote in result)
        mock_quote_repository.get_by_request_id.assert_called_once_with(request_id)

    @pytest.mark.asyncio
    async def test_compare_quotes(self, quote_service, mock_quote_repository):
        """Test quote comparison functionality"""
        quote_ids = [1, 2, 3]
        quotes = [
            Quote(
                id=1, provider_id=1, total_cost=Decimal("2500.00"), estimated_hours=16
            ),
            Quote(
                id=2, provider_id=2, total_cost=Decimal("2800.00"), estimated_hours=14
            ),
            Quote(
                id=3, provider_id=3, total_cost=Decimal("2200.00"), estimated_hours=18
            ),
        ]
        mock_quote_repository.get_multiple_by_ids.return_value = quotes

        result = await quote_service.compare_quotes(quote_ids)

        assert "comparison_matrix" in result
        assert "recommendations" in result
        assert len(result["comparison_matrix"]) == 3
        mock_quote_repository.get_multiple_by_ids.assert_called_once_with(quote_ids)

    @pytest.mark.asyncio
    async def test_rank_quotes_by_value(
        self, quote_service, mock_quote_repository, mock_provider_repository
    ):
        """Test ranking quotes by value proposition"""
        request_id = 1
        quotes = [
            Quote(id=1, provider_id=1, total_cost=Decimal("2500.00")),
            Quote(id=2, provider_id=2, total_cost=Decimal("2800.00")),
            Quote(id=3, provider_id=3, total_cost=Decimal("2200.00")),
        ]
        mock_quote_repository.get_by_request_id.return_value = quotes

        # Mock provider ratings for value calculation
        providers = [
            ServiceProvider(id=1, rating=4.5, total_reviews=25),
            ServiceProvider(id=2, rating=4.8, total_reviews=40),
            ServiceProvider(id=3, rating=4.2, total_reviews=15),
        ]
        mock_provider_repository.get_multiple_by_ids.return_value = providers

        result = await quote_service.rank_quotes_by_value(request_id)

        assert len(result["ranked_quotes"]) == 3
        assert all("value_score" in quote for quote in result["ranked_quotes"])
        # Should be sorted by value score
        value_scores = [quote["value_score"] for quote in result["ranked_quotes"]]
        assert value_scores == sorted(value_scores, reverse=True)

    # Quote Expiration Tests
    @pytest.mark.asyncio
    async def test_expire_old_quotes(self, quote_service, mock_quote_repository):
        """Test expiring quotes that have passed their valid_until date"""
        # Mock the repository method to return the count of expired quotes
        mock_quote_repository.expire_quotes_before.return_value = 2

        result = await quote_service.expire_old_quotes()

        assert result == 2  # Number of expired quotes
        mock_quote_repository.expire_quotes_before.assert_called_once()

    @pytest.mark.asyncio
    async def test_extend_quote_validity(self, quote_service, mock_quote_repository):
        """Test extending quote validity period"""
        quote = Quote(
            id=1,
            provider_id=1,
            valid_until=datetime.now(timezone.utc) + timedelta(days=1),
            status=QuoteStatus.SUBMITTED,
        )
        mock_quote_repository.get_by_id.return_value = quote

        new_expiry = datetime.now(timezone.utc) + timedelta(days=7)
        extended_quote = Quote(
            id=1, provider_id=1, valid_until=new_expiry, status=QuoteStatus.SUBMITTED
        )
        mock_quote_repository.update.return_value = extended_quote

        result = await quote_service.extend_quote_validity(1, new_expiry, provider_id=1)

        assert result.valid_until == new_expiry
        mock_quote_repository.update.assert_called_once()

    # Quote Analytics Tests
    @pytest.mark.asyncio
    async def test_get_quote_analytics(self, quote_service, mock_quote_repository):
        """Test retrieving quote performance analytics"""
        quote_id = 1
        expected_analytics = {
            "views": 25,
            "seeker_interest_score": 0.75,
            "time_since_submission": 120,  # minutes
            "competitor_count": 4,
            "price_ranking": 2,
            "acceptance_probability": 0.65,
        }
        mock_quote_repository.get_analytics.return_value = expected_analytics

        result = await quote_service.get_quote_analytics(quote_id)

        assert result["views"] == 25
        assert result["acceptance_probability"] == 0.65
        mock_quote_repository.get_analytics.assert_called_once_with(quote_id)

    @pytest.mark.asyncio
    async def test_get_provider_quote_statistics(
        self, quote_service, mock_quote_repository
    ):
        """Test retrieving provider's quote statistics"""
        provider_id = 1
        expected_stats = {
            "total_quotes_submitted": 45,
            "acceptance_rate": 0.32,
            "average_quote_amount": Decimal("2750.00"),
            "average_response_time": 180,  # minutes
            "win_rate_by_price_range": {
                "under_2000": 0.45,
                "2000_to_5000": 0.28,
                "over_5000": 0.15,
            },
        }
        mock_quote_repository.get_provider_statistics.return_value = expected_stats

        result = await quote_service.get_provider_quote_statistics(provider_id)

        assert result["total_quotes_submitted"] == 45
        assert result["acceptance_rate"] == 0.32
        mock_quote_repository.get_provider_statistics.assert_called_once_with(
            provider_id
        )

    # Counter-Proposal Tests
    @pytest.mark.asyncio
    async def test_submit_counter_proposal(
        self, quote_service, mock_quote_repository, mock_notification_service
    ):
        """Test submitting counter-proposal to existing quote"""
        original_quote = Quote(
            id=1,
            request_id=1,
            provider_id=1,
            total_cost=Decimal("2500.00"),
            status=QuoteStatus.SUBMITTED,
        )
        mock_quote_repository.get_by_id.return_value = original_quote

        counter_data = {
            "total_cost": Decimal("2200.00"),
            "notes": "Counter-offer with reduced scope",
        }

        counter_quote = Quote(
            id=2,
            request_id=1,
            provider_id=1,
            total_cost=Decimal("2200.00"),
            status=QuoteStatus.SUBMITTED,
            parent_quote_id=1,
        )
        mock_quote_repository.create.return_value = counter_quote
        mock_notification_service.notify_counter_proposal = AsyncMock()

        result = await quote_service.submit_counter_proposal(
            1, counter_data, provider_id=1
        )

        assert result.total_cost == Decimal("2200.00")
        assert result.parent_quote_id == 1
        mock_notification_service.notify_counter_proposal.assert_called_once()

    # Error Handling Tests
    @pytest.mark.asyncio
    async def test_quote_service_handles_repository_errors(
        self, quote_service, mock_quote_repository
    ):
        """Test that service properly handles repository errors"""
        mock_quote_repository.get_by_id.side_effect = Exception(
            "Database connection failed"
        )

        with pytest.raises(Exception, match="Database connection failed"):
            await quote_service.get_quote(1)

    @pytest.mark.asyncio
    async def test_validation_error_on_invalid_quote_data(self, quote_service):
        """Test validation errors for invalid quote data"""
        invalid_data = {
            "request_id": None,  # Required field missing
            "provider_id": None,  # Required field missing
            "labor_cost": Decimal("-100.00"),  # Negative cost
            "estimated_hours": -5,  # Invalid negative hours
        }

        with pytest.raises(ValidationError):
            await quote_service.submit_quote(invalid_data)
