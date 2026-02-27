"""Tests for BookingRepository."""
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
from src.models.booking import (Booking, BookingMilestone, BookingStatus,
                                MilestoneStatus)
from src.repositories.booking_repository import (BookingMilestoneRepository,
                                                 BookingRepository)

from tests.factories import BookingFactory, BookingMilestoneFactory


class TestBookingRepository:
    """Test cases for BookingRepository."""

    def test_create_repository(self, db_session):
        """Test repository creation."""
        repo = BookingRepository(db_session)
        assert repo.model == Booking
        assert repo.db_session == db_session

    def test_find_by_status(self, db_session):
        """Test finding bookings by status."""
        repo = BookingRepository(db_session)

        # Create test data
        confirmed_booking = BookingFactory.create(
            status=BookingStatus.CONFIRMED, notes="Confirmed Booking"
        )
        completed_booking = BookingFactory.create(
            status=BookingStatus.COMPLETED, notes="Completed Booking"
        )
        db_session.commit()

        # Test finding by status
        confirmed_bookings = repo.find_by_status(BookingStatus.CONFIRMED)
        assert len(confirmed_bookings) == 1
        assert confirmed_bookings[0].notes == "Confirmed Booking"

        completed_bookings = repo.find_by_status(BookingStatus.COMPLETED)
        assert len(completed_bookings) == 1
        assert completed_bookings[0].notes == "Completed Booking"

    def test_find_by_provider_id(self, db_session):
        """Test finding bookings by provider ID."""
        repo = BookingRepository(db_session)

        # Create test data with different creation times
        older_booking = BookingFactory.create(
            provider_id=2001,
            notes="Older Booking",
            created_at=datetime.now(timezone.utc) - timedelta(days=2),
        )
        newer_booking = BookingFactory.create(
            provider_id=2001,
            notes="Newer Booking",
            created_at=datetime.now(timezone.utc) - timedelta(days=1),
        )
        other_provider_booking = BookingFactory.create(
            provider_id=2002, notes="Other Provider"
        )
        db_session.commit()

        # Test finding by provider ID (should be ordered by creation date desc)
        provider_bookings = repo.find_by_provider_id(2001)
        assert len(provider_bookings) == 2
        assert provider_bookings[0].notes == "Newer Booking"  # Most recent first
        assert provider_bookings[1].notes == "Older Booking"

    def test_find_by_client_id(self, db_session):
        """Test finding bookings by seeker ID."""
        repo = BookingRepository(db_session)

        # Create test data
        seeker_booking_1 = BookingFactory.create(
            client_id=3001, notes="Seeker Booking 1"
        )
        seeker_booking_2 = BookingFactory.create(
            client_id=3001, notes="Seeker Booking 2"
        )
        other_seeker_booking = BookingFactory.create(
            client_id=3002, notes="Other Seeker"
        )
        db_session.commit()

        # Test finding by seeker ID
        seeker_bookings = repo.find_by_client_id(3001)
        assert len(seeker_bookings) == 2

    def test_find_active_bookings(self, db_session):
        """Test finding active bookings."""
        repo = BookingRepository(db_session)

        # Create test data
        confirmed_booking = BookingFactory.create(
            status=BookingStatus.CONFIRMED,
            scheduled_start_date=datetime.now(timezone.utc) + timedelta(days=1),
            notes="Confirmed",
        )
        in_progress_booking = BookingFactory.create(
            status=BookingStatus.IN_PROGRESS,
            scheduled_start_date=datetime.now(timezone.utc) - timedelta(days=1),
            notes="In Progress",
        )
        completed_booking = BookingFactory.create(
            status=BookingStatus.COMPLETED, notes="Completed"
        )
        db_session.commit()

        # Test finding active bookings
        active_bookings = repo.find_active_bookings()
        assert len(active_bookings) == 2
        # Should be ordered by scheduled start date
        assert active_bookings[0].notes == "In Progress"  # Earlier start date
        assert active_bookings[1].notes == "Confirmed"

    def test_find_upcoming_bookings(self, db_session):
        """Test finding upcoming bookings."""
        repo = BookingRepository(db_session)

        # Create test data
        upcoming_booking = BookingFactory.create(
            status=BookingStatus.CONFIRMED,
            scheduled_start_date=datetime.now(timezone.utc) + timedelta(days=3),
            notes="Upcoming",
        )
        far_future_booking = BookingFactory.create(
            status=BookingStatus.CONFIRMED,
            scheduled_start_date=datetime.now(timezone.utc) + timedelta(days=10),
            notes="Far Future",
        )
        past_booking = BookingFactory.create(
            status=BookingStatus.CONFIRMED,
            scheduled_start_date=datetime.now(timezone.utc) - timedelta(days=1),
            notes="Past",
        )
        db_session.commit()

        # Test finding upcoming bookings within 7 days
        upcoming_bookings = repo.find_upcoming_bookings(7)
        assert len(upcoming_bookings) == 1
        assert upcoming_bookings[0].notes == "Upcoming"

    def test_find_overdue_bookings(self, db_session):
        """Test finding overdue bookings."""
        repo = BookingRepository(db_session)

        # Create test data
        overdue_confirmed = BookingFactory.create(
            status=BookingStatus.CONFIRMED,
            scheduled_start_date=datetime.now(timezone.utc) - timedelta(days=3),
            scheduled_completion_date=datetime.now(timezone.utc) - timedelta(days=1),
            notes="Overdue Confirmed",
        )
        overdue_in_progress = BookingFactory.create(
            status=BookingStatus.IN_PROGRESS,
            scheduled_start_date=datetime.now(timezone.utc) - timedelta(days=4),
            scheduled_completion_date=datetime.now(timezone.utc) - timedelta(days=2),
            notes="Overdue In Progress",
        )
        completed_past = BookingFactory.create(
            status=BookingStatus.COMPLETED,
            scheduled_start_date=datetime.now(timezone.utc) - timedelta(days=3),
            scheduled_completion_date=datetime.now(timezone.utc) - timedelta(days=1),
            notes="Completed Past",
        )
        future_booking = BookingFactory.create(
            status=BookingStatus.CONFIRMED,
            scheduled_start_date=datetime.now(timezone.utc) - timedelta(days=1),
            scheduled_completion_date=datetime.now(timezone.utc) + timedelta(days=1),
            notes="Future",
        )
        db_session.commit()

        # Test finding overdue bookings
        overdue_bookings = repo.find_overdue_bookings()
        assert len(overdue_bookings) == 2
        # Should be ordered by scheduled end date
        assert overdue_bookings[0].notes == "Overdue In Progress"  # Earlier end date
        assert overdue_bookings[1].notes == "Overdue Confirmed"

    def test_find_by_date_range(self, db_session):
        """Test finding bookings within date range."""
        repo = BookingRepository(db_session)

        # Create test data
        start_date = datetime.now(timezone.utc)
        end_date = start_date + timedelta(days=7)

        in_range_booking = BookingFactory.create(
            scheduled_start_date=start_date + timedelta(days=3), notes="In Range"
        )
        before_range_booking = BookingFactory.create(
            scheduled_start_date=start_date - timedelta(days=1), notes="Before Range"
        )
        after_range_booking = BookingFactory.create(
            scheduled_start_date=end_date + timedelta(days=1), notes="After Range"
        )
        db_session.commit()

        # Test finding within date range
        range_bookings = repo.find_by_date_range(start_date, end_date)
        assert len(range_bookings) == 1
        assert range_bookings[0].notes == "In Range"

    def test_find_provider_schedule(self, db_session):
        """Test finding provider schedule within date range."""
        repo = BookingRepository(db_session)

        # Create test data
        start_date = datetime.now(timezone.utc)
        end_date = start_date + timedelta(days=7)

        provider_booking = BookingFactory.create(
            provider_id=2001,
            status=BookingStatus.CONFIRMED,
            scheduled_start_date=start_date + timedelta(days=2),
            scheduled_completion_date=start_date + timedelta(days=3),
            notes="Provider Schedule",
        )
        other_provider_booking = BookingFactory.create(
            provider_id=2002,
            status=BookingStatus.CONFIRMED,
            scheduled_start_date=start_date + timedelta(days=2),
            scheduled_completion_date=start_date + timedelta(days=3),
            notes="Other Provider",
        )
        cancelled_booking = BookingFactory.create(
            provider_id=2001,
            status=BookingStatus.CANCELLED,
            scheduled_start_date=start_date + timedelta(days=2),
            scheduled_completion_date=start_date + timedelta(days=3),
            notes="Cancelled",
        )
        db_session.commit()

        # Test finding provider schedule
        schedule = repo.find_provider_schedule(2001, start_date, end_date)
        assert len(schedule) == 1
        assert schedule[0].notes == "Provider Schedule"

    def test_find_conflicting_bookings(self, db_session):
        """Test finding conflicting bookings."""
        repo = BookingRepository(db_session)

        # Create test data
        base_time = datetime.now(timezone.utc)

        # Existing booking: 10:00 - 14:00
        existing_booking = BookingFactory.create(
            provider_id=2001,
            status=BookingStatus.CONFIRMED,
            scheduled_start_date=base_time + timedelta(hours=10),
            scheduled_completion_date=base_time + timedelta(hours=14),
            notes="Existing",
        )

        # Non-conflicting booking: 16:00 - 18:00
        non_conflicting = BookingFactory.create(
            provider_id=2001,
            status=BookingStatus.CONFIRMED,
            scheduled_start_date=base_time + timedelta(hours=16),
            scheduled_completion_date=base_time + timedelta(hours=18),
            notes="Non-conflicting",
        )
        db_session.commit()

        # Test for conflict: 12:00 - 16:00 (overlaps with existing)
        conflicts = repo.find_conflicting_bookings(
            provider_id=2001,
            start_date=base_time + timedelta(hours=12),
            end_date=base_time + timedelta(hours=16),
        )
        assert len(conflicts) == 1
        assert conflicts[0].notes == "Existing"

        # Test for no conflict: 15:00 - 16:00 (no overlap)
        no_conflicts = repo.find_conflicting_bookings(
            provider_id=2001,
            start_date=base_time + timedelta(hours=15),
            end_date=base_time + timedelta(hours=16),
        )
        assert len(no_conflicts) == 0

    @pytest.mark.asyncio
    async def test_update_booking_status(self, db_session):
        """Test updating booking status with timestamps."""
        repo = BookingRepository(db_session)

        # Create test data
        booking = BookingFactory.create(
            status=BookingStatus.CONFIRMED, notes="Test Booking"
        )
        db_session.commit()

        # Test updating to IN_PROGRESS
        updated_booking = await repo.update_booking_status(
            booking.id, BookingStatus.IN_PROGRESS
        )
        assert updated_booking.status == BookingStatus.IN_PROGRESS
        assert updated_booking.actual_start_date is not None

        # Test updating to COMPLETED
        updated_booking = await repo.update_booking_status(
            booking.id, BookingStatus.COMPLETED
        )
        assert updated_booking.status == BookingStatus.COMPLETED
        assert updated_booking.actual_end_date is not None

    def test_get_booking_statistics(self, db_session):
        """Test getting booking statistics."""
        repo = BookingRepository(db_session)

        # Create test data
        completed_booking = BookingFactory.create(
            provider_id=2001,
            status=BookingStatus.COMPLETED,
            total_cost=Decimal("500.00"),
        )
        cancelled_booking = BookingFactory.create(
            provider_id=2001,
            status=BookingStatus.CANCELLED,
            total_cost=Decimal("300.00"),
        )
        confirmed_booking = BookingFactory.create(
            provider_id=2001,
            status=BookingStatus.CONFIRMED,
            total_cost=Decimal("400.00"),
        )
        db_session.commit()

        # Test getting provider statistics
        stats = repo.get_booking_statistics(provider_id=2001)
        assert stats["total_bookings"] == 3
        assert stats["completed_bookings"] == 1
        assert stats["cancelled_bookings"] == 1
        assert (
            abs(stats["completion_rate"] - 33.333333333333336) < 0.0001
        )  # 1/3 * 100 (floating point precision)
        assert stats["avg_booking_value"] == 400.0  # (500 + 300 + 400) / 3
        assert stats["total_revenue"] == 1200.0


class TestBookingMilestoneRepository:
    """Test cases for BookingMilestoneRepository."""

    def test_create_repository(self, db_session):
        """Test repository creation."""
        repo = BookingMilestoneRepository(db_session)
        assert repo.model == BookingMilestone
        assert repo.db_session == db_session

    def test_find_by_booking_id(self, db_session):
        """Test finding milestones by booking ID."""
        repo = BookingMilestoneRepository(db_session)

        # Create test data
        milestone_1 = BookingMilestoneFactory.create(
            booking_id=1001, sequence_number=1, title="First Milestone"
        )
        milestone_2 = BookingMilestoneFactory.create(
            booking_id=1001, sequence_number=2, title="Second Milestone"
        )
        other_booking_milestone = BookingMilestoneFactory.create(
            booking_id=1002, sequence_number=1, title="Other Booking"
        )
        db_session.commit()

        # Test finding by booking ID (should be ordered by sequence)
        milestones = repo.find_by_booking_id(1001)
        assert len(milestones) == 2
        assert milestones[0].title == "First Milestone"
        assert milestones[1].title == "Second Milestone"

    def test_find_by_status(self, db_session):
        """Test finding milestones by status."""
        repo = BookingMilestoneRepository(db_session)

        # Create test data
        pending_milestone = BookingMilestoneFactory.create(
            status=MilestoneStatus.PENDING, title="Pending"
        )
        completed_milestone = BookingMilestoneFactory.create(
            status=MilestoneStatus.COMPLETED, title="Completed"
        )
        db_session.commit()

        # Test finding by status
        pending_milestones = repo.find_by_status(MilestoneStatus.PENDING)
        assert len(pending_milestones) == 1
        assert pending_milestones[0].title == "Pending"

    def test_find_overdue_milestones(self, db_session):
        """Test finding overdue milestones."""
        repo = BookingMilestoneRepository(db_session)

        # Create test data
        overdue_pending = BookingMilestoneFactory.create(
            status=MilestoneStatus.PENDING,
            due_date=datetime.now(timezone.utc) - timedelta(days=1),
            title="Overdue Pending",
        )
        overdue_in_progress = BookingMilestoneFactory.create(
            status=MilestoneStatus.IN_PROGRESS,
            due_date=datetime.now(timezone.utc) - timedelta(days=2),
            title="Overdue In Progress",
        )
        completed_overdue = BookingMilestoneFactory.create(
            status=MilestoneStatus.COMPLETED,
            due_date=datetime.now(timezone.utc) - timedelta(days=1),
            title="Completed Overdue",
        )
        future_milestone = BookingMilestoneFactory.create(
            status=MilestoneStatus.PENDING,
            due_date=datetime.now(timezone.utc) + timedelta(days=1),
            title="Future",
        )
        db_session.commit()

        # Test finding overdue milestones
        overdue_milestones = repo.find_overdue_milestones()
        assert len(overdue_milestones) == 2
        # Should be ordered by due date
        assert overdue_milestones[0].title == "Overdue In Progress"  # Earlier due date
        assert overdue_milestones[1].title == "Overdue Pending"

    def test_get_milestone_progress(self, db_session):
        """Test getting milestone progress."""
        repo = BookingMilestoneRepository(db_session)

        # Create test data
        completed_milestone = BookingMilestoneFactory.create(
            booking_id=1001, status=MilestoneStatus.COMPLETED
        )
        pending_milestone = BookingMilestoneFactory.create(
            booking_id=1001, status=MilestoneStatus.PENDING
        )
        in_progress_milestone = BookingMilestoneFactory.create(
            booking_id=1001, status=MilestoneStatus.IN_PROGRESS
        )
        db_session.commit()

        # Test getting progress
        progress = repo.get_milestone_progress(1001)
        assert progress["booking_id"] == 1001
        assert progress["total_milestones"] == 3
        assert progress["completed_milestones"] == 1
        assert (
            abs(progress["progress_percentage"] - 33.333333333333336) < 0.0001
        )  # 1/3 * 100 (floating point precision)

    @pytest.mark.asyncio
    async def test_update_milestone_status(self, db_session):
        """Test updating milestone status."""
        repo = BookingMilestoneRepository(db_session)

        # Create test data
        milestone = BookingMilestoneFactory.create(
            status=MilestoneStatus.PENDING, title="Test Milestone"
        )
        db_session.commit()

        # Test updating to COMPLETED
        updated_milestone = await repo.update_milestone_status(
            milestone.id, MilestoneStatus.COMPLETED
        )
        assert updated_milestone.status == MilestoneStatus.COMPLETED
        assert updated_milestone.completed_at is not None
