"""Tests for QuoteRepository."""
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
from src.models.quote import Quote, QuoteStatus
from src.repositories.quote_repository import QuoteRepository

from tests.factories import QuoteFactory


class TestQuoteRepository:
    """Test cases for QuoteRepository."""

    def test_create_repository(self, db_session):
        """Test repository creation."""
        repo = QuoteRepository(db_session)
        assert repo.model == Quote
        assert repo.db_session == db_session

    def test_find_by_status(self, db_session):
        """Test finding quotes by status."""
        repo = QuoteRepository(db_session)

        # Create test data
        submitted_quote = QuoteFactory.create(
            status=QuoteStatus.SUBMITTED, description="Submitted Quote"
        )
        draft_quote = QuoteFactory.create(
            status=QuoteStatus.DRAFT, description="Draft Quote"
        )
        db_session.commit()

        # Test finding by status
        submitted_quotes = repo.find_by_status(QuoteStatus.SUBMITTED)
        assert len(submitted_quotes) == 1
        assert submitted_quotes[0].description == "Submitted Quote"

        draft_quotes = repo.find_by_status(QuoteStatus.DRAFT)
        assert len(draft_quotes) == 1
        assert draft_quotes[0].description == "Draft Quote"

    def test_find_by_request_id(self, db_session):
        """Test finding quotes by request ID."""
        repo = QuoteRepository(db_session)

        # Create test data
        request_1_quote_1 = QuoteFactory.create(
            request_id=1001,
            total_cost=Decimal("500.00"),
            description="Request 1 Quote 1",
        )
        request_1_quote_2 = QuoteFactory.create(
            request_id=1001,
            total_cost=Decimal("750.00"),
            description="Request 1 Quote 2",
        )
        request_2_quote = QuoteFactory.create(
            request_id=1002, total_cost=Decimal("600.00"), description="Request 2 Quote"
        )
        db_session.commit()

        # Test finding by request ID (should be ordered by cost)
        request_1_quotes = repo.find_by_request_id(1001)
        assert len(request_1_quotes) == 2
        assert (
            request_1_quotes[0].description == "Request 1 Quote 1"
        )  # Lower cost first
        assert request_1_quotes[1].description == "Request 1 Quote 2"

        request_2_quotes = repo.find_by_request_id(1002)
        assert len(request_2_quotes) == 1
        assert request_2_quotes[0].description == "Request 2 Quote"

    def test_find_by_provider_id(self, db_session):
        """Test finding quotes by provider ID."""
        repo = QuoteRepository(db_session)

        # Create test data with different creation times
        older_quote = QuoteFactory.create(
            provider_id=2001,
            description="Older Quote",
            created_at=datetime.now(timezone.utc) - timedelta(days=2),
        )
        newer_quote = QuoteFactory.create(
            provider_id=2001,
            description="Newer Quote",
            created_at=datetime.now(timezone.utc) - timedelta(days=1),
        )
        other_provider_quote = QuoteFactory.create(
            provider_id=2002, description="Other Provider Quote"
        )
        db_session.commit()

        # Test finding by provider ID (should be ordered by creation date desc)
        provider_quotes = repo.find_by_provider_id(2001)
        assert len(provider_quotes) == 2
        assert provider_quotes[0].description == "Newer Quote"  # Most recent first
        assert provider_quotes[1].description == "Older Quote"

    def test_find_by_cost_range(self, db_session):
        """Test finding quotes within cost range."""
        repo = QuoteRepository(db_session)

        # Create test data
        low_cost_quote = QuoteFactory.create(
            total_cost=Decimal("300.00"), description="Low Cost"
        )
        mid_cost_quote = QuoteFactory.create(
            total_cost=Decimal("750.00"), description="Mid Cost"
        )
        high_cost_quote = QuoteFactory.create(
            total_cost=Decimal("1200.00"), description="High Cost"
        )
        db_session.commit()

        # Test finding within range
        mid_range_quotes = repo.find_by_cost_range(500.0, 1000.0)
        assert len(mid_range_quotes) == 1
        assert mid_range_quotes[0].description == "Mid Cost"

        all_range_quotes = repo.find_by_cost_range(200.0, 1500.0)
        assert len(all_range_quotes) == 3

    def test_find_pending_quotes(self, db_session):
        """Test finding pending quotes."""
        repo = QuoteRepository(db_session)

        # Create test data
        pending_quote_1 = QuoteFactory.create(
            status=QuoteStatus.SUBMITTED,
            description="Pending 1",
            created_at=datetime.now(timezone.utc) - timedelta(hours=2),
        )
        pending_quote_2 = QuoteFactory.create(
            status=QuoteStatus.SUBMITTED,
            description="Pending 2",
            created_at=datetime.now(timezone.utc) - timedelta(hours=1),
        )
        accepted_quote = QuoteFactory.create(
            status=QuoteStatus.ACCEPTED, description="Accepted"
        )
        db_session.commit()

        # Test finding pending quotes (should be ordered by creation time)
        pending_quotes = repo.find_pending_quotes()
        assert len(pending_quotes) == 2
        assert pending_quotes[0].description == "Pending 1"  # Oldest first
        assert pending_quotes[1].description == "Pending 2"

    def test_find_expired_quotes(self, db_session):
        """Test finding expired quotes."""
        repo = QuoteRepository(db_session)

        # Create test data
        expired_quote = QuoteFactory.create(
            status=QuoteStatus.SUBMITTED,
            valid_until=datetime.now(timezone.utc) - timedelta(hours=1),
            description="Expired Quote",
        )
        valid_quote = QuoteFactory.create(
            status=QuoteStatus.SUBMITTED,
            valid_until=datetime.now(timezone.utc) + timedelta(hours=1),
            description="Valid Quote",
        )
        accepted_quote = QuoteFactory.create(
            status=QuoteStatus.ACCEPTED,
            valid_until=datetime.now(timezone.utc) - timedelta(hours=1),
            description="Accepted Quote",
        )
        db_session.commit()

        # Test finding expired quotes
        expired_quotes = repo.find_expired_quotes()
        assert len(expired_quotes) == 1
        assert expired_quotes[0].description == "Expired Quote"

    def test_find_expiring_soon(self, db_session):
        """Test finding quotes expiring soon."""
        repo = QuoteRepository(db_session)

        # Create test data
        expiring_soon = QuoteFactory.create(
            status=QuoteStatus.SUBMITTED,
            valid_until=datetime.now(timezone.utc) + timedelta(hours=12),
            description="Expiring Soon",
        )
        expiring_later = QuoteFactory.create(
            status=QuoteStatus.SUBMITTED,
            valid_until=datetime.now(timezone.utc) + timedelta(hours=48),
            description="Expiring Later",
        )
        already_expired = QuoteFactory.create(
            status=QuoteStatus.SUBMITTED,
            valid_until=datetime.now(timezone.utc) - timedelta(hours=1),
            description="Already Expired",
        )
        db_session.commit()

        # Test finding quotes expiring within 24 hours
        expiring_quotes = repo.find_expiring_soon(24)
        assert len(expiring_quotes) == 1
        assert expiring_quotes[0].description == "Expiring Soon"

    def test_find_competitive_quotes(self, db_session):
        """Test finding competitive quotes for comparison."""
        repo = QuoteRepository(db_session)

        # Create test data
        quote_1 = QuoteFactory.create(
            request_id=1001,
            status=QuoteStatus.SUBMITTED,
            total_cost=Decimal("500.00"),
            description="Quote 1",
        )
        quote_2 = QuoteFactory.create(
            request_id=1001,
            status=QuoteStatus.SUBMITTED,
            total_cost=Decimal("750.00"),
            description="Quote 2",
        )
        quote_3 = QuoteFactory.create(
            request_id=1001,
            status=QuoteStatus.DRAFT,
            total_cost=Decimal("600.00"),
            description="Draft Quote",
        )
        other_request_quote = QuoteFactory.create(
            request_id=1002,
            status=QuoteStatus.SUBMITTED,
            total_cost=Decimal("400.00"),
            description="Other Request",
        )
        db_session.commit()

        # Test finding competitive quotes
        competitive_quotes = repo.find_competitive_quotes(1001)
        assert len(competitive_quotes) == 2  # Only submitted quotes
        assert competitive_quotes[0].description == "Quote 1"  # Lower cost first
        assert competitive_quotes[1].description == "Quote 2"

        # Test excluding specific quote
        competitive_excluding = repo.find_competitive_quotes(
            1001, exclude_quote_id=quote_1.id
        )
        assert len(competitive_excluding) == 1
        assert competitive_excluding[0].description == "Quote 2"

    def test_get_quote_statistics(self, db_session):
        """Test getting quote statistics for a request."""
        repo = QuoteRepository(db_session)

        # Create test data
        quote_1 = QuoteFactory.create(
            request_id=1001,
            status=QuoteStatus.SUBMITTED,
            total_cost=Decimal("500.00"),
            estimated_hours=20,
        )
        quote_2 = QuoteFactory.create(
            request_id=1001,
            status=QuoteStatus.SUBMITTED,
            total_cost=Decimal("800.00"),
            estimated_hours=30,
        )
        draft_quote = QuoteFactory.create(
            request_id=1001,
            status=QuoteStatus.DRAFT,
            total_cost=Decimal("600.00"),
            estimated_hours=25,
        )
        db_session.commit()

        # Test getting statistics
        stats = repo.get_quote_statistics(1001)
        assert stats["request_id"] == 1001
        assert stats["quote_count"] == 2  # Only submitted quotes
        assert stats["avg_cost"] == 650.0  # (500 + 800) / 2
        assert stats["min_cost"] == 500.0
        assert stats["max_cost"] == 800.0
        assert stats["avg_hours"] == 25.0  # (20 + 30) / 2

        # Test with no quotes
        empty_stats = repo.get_quote_statistics(9999)
        assert empty_stats["quote_count"] == 0
        assert empty_stats["avg_cost"] == 0.0

    def test_find_provider_quote_history(self, db_session):
        """Test finding provider quote history."""
        repo = QuoteRepository(db_session)

        # Create test data
        recent_quote = QuoteFactory.create(
            provider_id=2001,
            description="Recent Quote",
            created_at=datetime.now(timezone.utc) - timedelta(days=1),
        )
        older_quote = QuoteFactory.create(
            provider_id=2001,
            description="Older Quote",
            created_at=datetime.now(timezone.utc) - timedelta(days=5),
        )
        db_session.commit()

        # Test finding quote history
        history = repo.find_provider_quote_history(2001, limit=10)
        assert len(history) == 2
        assert history[0].description == "Recent Quote"  # Most recent first
        assert history[1].description == "Older Quote"

    def test_find_accepted_quotes_by_provider(self, db_session):
        """Test finding accepted quotes for a provider."""
        repo = QuoteRepository(db_session)

        # Create test data
        accepted_quote = QuoteFactory.create(
            provider_id=2001, status=QuoteStatus.ACCEPTED, description="Accepted Quote"
        )
        submitted_quote = QuoteFactory.create(
            provider_id=2001,
            status=QuoteStatus.SUBMITTED,
            description="Submitted Quote",
        )
        db_session.commit()

        # Test finding accepted quotes
        accepted_quotes = repo.find_accepted_quotes_by_provider(2001)
        assert len(accepted_quotes) == 1
        assert accepted_quotes[0].description == "Accepted Quote"

    def test_get_provider_quote_stats(self, db_session):
        """Test getting provider quote statistics."""
        repo = QuoteRepository(db_session)

        # Create test data
        accepted_quote = QuoteFactory.create(
            provider_id=2001,
            status=QuoteStatus.ACCEPTED,
            total_cost=Decimal("800.00"),
            created_at=datetime.now(timezone.utc) - timedelta(hours=2),
            submitted_at=datetime.now(timezone.utc) - timedelta(hours=1),
        )
        rejected_quote = QuoteFactory.create(
            provider_id=2001,
            status=QuoteStatus.REJECTED,
            total_cost=Decimal("600.00"),
            created_at=datetime.now(timezone.utc) - timedelta(hours=4),
            submitted_at=datetime.now(timezone.utc) - timedelta(hours=3),
        )
        db_session.commit()

        # Test getting provider statistics
        stats = repo.get_provider_quote_stats(2001)
        assert stats["provider_id"] == 2001
        assert stats["total_quotes"] == 2
        assert stats["accepted_quotes"] == 1
        assert stats["acceptance_rate"] == 50.0  # 1/2 * 100
        assert stats["avg_quote_value"] == 700.0  # (800 + 600) / 2
        assert (
            abs(stats["avg_response_time"] - 1.0) < 0.1
        )  # 1 hour average (with tolerance)

    def test_update_expired_quotes(self, db_session):
        """Test updating expired quotes to EXPIRED status."""
        repo = QuoteRepository(db_session)

        # Create test data
        expired_submitted = QuoteFactory.create(
            status=QuoteStatus.SUBMITTED,
            valid_until=datetime.now(timezone.utc) - timedelta(hours=1),
        )
        expired_draft = QuoteFactory.create(
            status=QuoteStatus.DRAFT,
            valid_until=datetime.now(timezone.utc) - timedelta(hours=1),
        )
        expired_accepted = QuoteFactory.create(
            status=QuoteStatus.ACCEPTED,
            valid_until=datetime.now(timezone.utc) - timedelta(hours=1),
        )
        valid_quote = QuoteFactory.create(
            status=QuoteStatus.SUBMITTED,
            valid_until=datetime.now(timezone.utc) + timedelta(hours=1),
        )
        db_session.commit()

        # Test updating expired quotes
        updated_count = repo.update_expired_quotes()
        assert updated_count == 2  # Only submitted and draft quotes should be updated

        # Verify the updates
        db_session.refresh(expired_submitted)
        db_session.refresh(expired_draft)
        db_session.refresh(expired_accepted)
        db_session.refresh(valid_quote)

        assert expired_submitted.status == QuoteStatus.EXPIRED
        assert expired_draft.status == QuoteStatus.EXPIRED
        assert expired_accepted.status == QuoteStatus.ACCEPTED  # Should not change
        assert valid_quote.status == QuoteStatus.SUBMITTED  # Should not change
