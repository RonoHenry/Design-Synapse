"""
RED Phase: Failing tests for BookingService
Following TDD methodology - these tests define expected behavior before implementation
"""
import pytest
from unittest.mock import Mock, AsyncMock
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from src.models.booking import Booking, BookingStatus, BookingMilestone, MilestoneStatus
from src.models.quote import Quote, QuoteStatus
from src.models.service_request import ServiceRequest
from src.core.exceptions import BookingNotFoundError, ValidationError, BusinessLogicError


class TestBookingService:
    """Test suite for BookingService - RED phase (failing tests)"""
    
    @pytest.fixture
    def mock_booking_repository(self):
        """Mock booking repository for testing"""
        mock = Mock()
        mock.create = AsyncMock()
        mock.get_by_id = AsyncMock()
        mock.update = AsyncMock()
        mock.get_by_provider_id = AsyncMock()
        mock.get_by_seeker_id = AsyncMock()
        mock.get_upcoming_bookings = AsyncMock()
        mock.get_analytics = AsyncMock()
        mock.get_provider_statistics = AsyncMock()
        mock.create_with_milestones = AsyncMock()
        mock.update_milestone = AsyncMock()
        mock.add_progress_update = AsyncMock()
        return mock
    
    @pytest.fixture
    def mock_quote_repository(self):
        """Mock quote repository for testing"""
        mock = Mock()
        mock.get_by_id = AsyncMock()
        return mock
    
    @pytest.fixture
    def mock_request_repository(self):
        """Mock request repository for testing"""
        mock = Mock()
        mock.get_by_id = AsyncMock()
        return mock
    
    @pytest.fixture
    def mock_notification_service(self):
        """Mock notification service for testing"""
        return Mock()
    
    @pytest.fixture
    def mock_payment_service(self):
        """Mock payment service for testing"""
        return Mock()
    
    @pytest.fixture
    def booking_service(self, mock_booking_repository, mock_quote_repository, mock_request_repository, 
                       mock_notification_service, mock_payment_service):
        """Create BookingService instance with mocked dependencies"""
        # This import will fail until BookingService is implemented
        from src.services.booking_service import BookingService
        return BookingService(
            booking_repository=mock_booking_repository,
            quote_repository=mock_quote_repository,
            request_repository=mock_request_repository,
            notification_service=mock_notification_service,
            payment_service=mock_payment_service
        )
    
    @pytest.fixture
    def sample_accepted_quote(self):
        """Sample accepted quote for booking creation"""
        return Quote(
            id=1,
            request_id=1,
            provider_id=1,
            total_cost=Decimal("2500.00"),
            estimated_hours=16,
            start_availability=datetime.now(timezone.utc) + timedelta(days=3),
            completion_estimate=datetime.now(timezone.utc) + timedelta(days=5),
            status=QuoteStatus.ACCEPTED
        )
    
    @pytest.fixture
    def sample_request(self):
        """Sample service request for testing"""
        return ServiceRequest(
            id=1,
            seeker_id=2,
            title="Kitchen Electrical Work"
        )

    # Booking Creation Tests
    @pytest.mark.asyncio
    async def test_create_booking_from_accepted_quote(self, booking_service, mock_booking_repository, 
                                                    mock_quote_repository, mock_request_repository,
                                                    sample_accepted_quote, sample_request):
        """Test creating booking from accepted quote"""
        # This test will fail until BookingService.create_booking is implemented
        mock_quote_repository.get_by_id.return_value = sample_accepted_quote
        mock_request_repository.get_by_id.return_value = sample_request
        
        expected_booking = Booking(
            id=1,
            service_request_id=sample_accepted_quote.request_id,
            provider_id=sample_accepted_quote.provider_id,
            client_id=sample_request.seeker_id,
            quote_id=sample_accepted_quote.id,
            status=BookingStatus.CONFIRMED,
            scheduled_start_date=sample_accepted_quote.start_availability,
            scheduled_completion_date=sample_accepted_quote.completion_estimate,
            total_cost=sample_accepted_quote.total_cost,
            created_at=datetime.now(timezone.utc)
        )
        mock_booking_repository.create.return_value = expected_booking
        
        result = await booking_service.create_booking(sample_accepted_quote.id)
        
        assert result is not None
        assert result.quote_id == sample_accepted_quote.id
        assert result.status == BookingStatus.CONFIRMED
        assert result.total_cost == sample_accepted_quote.total_cost
        mock_booking_repository.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_booking_from_unaccepted_quote(self, booking_service, mock_quote_repository):
        """Test that booking cannot be created from unaccepted quote"""
        unaccepted_quote = Quote(
            id=1,
            request_id=1,
            provider_id=1,
            status=QuoteStatus.SUBMITTED  # Not accepted
        )
        mock_quote_repository.get_by_id.return_value = unaccepted_quote
        
        with pytest.raises(BusinessLogicError, match="Can only create booking from accepted quote"):
            await booking_service.create_booking(1)

    @pytest.mark.asyncio
    async def test_create_booking_with_milestones(self, booking_service, mock_booking_repository, 
                                                mock_quote_repository, mock_request_repository,
                                                sample_accepted_quote, sample_request):
        """Test creating booking with payment milestones"""
        mock_quote_repository.get_by_id.return_value = sample_accepted_quote
        mock_request_repository.get_by_id.return_value = sample_request
        
        milestone_data = [
            {
                "description": "Project start - 25%",
                "percentage": 25,
                "due_date": datetime.now(timezone.utc) + timedelta(days=3)
            },
            {
                "description": "Midpoint - 50%",
                "percentage": 50,
                "due_date": datetime.now(timezone.utc) + timedelta(days=4)
            },
            {
                "description": "Completion - 25%",
                "percentage": 25,
                "due_date": datetime.now(timezone.utc) + timedelta(days=5)
            }
        ]
        
        booking_with_milestones = Booking(
            id=1,
            quote_id=1,
            status=BookingStatus.CONFIRMED,
            milestones=[
                BookingMilestone(
                    id=1,
                    booking_id=1,
                    title=milestone["description"],
                    description=milestone["description"],
                    sequence_number=i+1,
                    amount=sample_accepted_quote.total_cost * milestone["percentage"] / 100,
                    due_date=milestone["due_date"],
                    status=MilestoneStatus.PENDING
                ) for i, milestone in enumerate(milestone_data)
            ]
        )
        mock_booking_repository.create_with_milestones.return_value = booking_with_milestones
        
        result = await booking_service.create_booking_with_milestones(1, milestone_data)
        
        assert len(result.milestones) == 3
        assert sum(m.amount for m in result.milestones) == sample_accepted_quote.total_cost
        mock_booking_repository.create_with_milestones.assert_called_once()

    # Booking Management Tests
    @pytest.mark.asyncio
    async def test_get_booking_success(self, booking_service, mock_booking_repository):
        """Test successful booking retrieval"""
        expected_booking = Booking(
            id=1,
            service_request_id=1,
            provider_id=1,
            client_id=2,
            quote_id=1,
            status=BookingStatus.CONFIRMED,
            scheduled_start_date=datetime.now(timezone.utc),
            scheduled_completion_date=datetime.now(timezone.utc) + timedelta(hours=8),
            total_cost=Decimal("1000.00")
        )
        mock_booking_repository.get_by_id.return_value = expected_booking
        
        result = await booking_service.get_booking(1, user_id=2)
        
        assert result == expected_booking
        mock_booking_repository.get_by_id.assert_called_once_with(1)

    @pytest.mark.asyncio
    async def test_get_booking_not_found(self, booking_service, mock_booking_repository):
        """Test booking retrieval when booking doesn't exist"""
        mock_booking_repository.get_by_id.return_value = None
        
        result = await booking_service.get_booking(999, user_id=1)
        assert result is None

    @pytest.mark.asyncio
    async def test_update_booking_status(self, booking_service, mock_booking_repository, mock_notification_service):
        """Test updating booking status"""
        existing_booking = Booking(
            id=1,
            service_request_id=1,
            provider_id=1,
            client_id=2,
            quote_id=1,
            status=BookingStatus.CONFIRMED,
            scheduled_start_date=datetime.now(timezone.utc),
            scheduled_completion_date=datetime.now(timezone.utc) + timedelta(hours=8),
            total_cost=Decimal("1000.00")
        )
        mock_booking_repository.get_by_id.return_value = existing_booking
        
        updated_booking = Booking(
            id=1,
            service_request_id=1,
            provider_id=1,
            client_id=2,
            quote_id=1,
            status=BookingStatus.IN_PROGRESS,
            scheduled_start_date=datetime.now(timezone.utc),
            scheduled_completion_date=datetime.now(timezone.utc) + timedelta(hours=8),
            total_cost=Decimal("1000.00"),
            actual_start_date=datetime.now(timezone.utc)
        )
        mock_booking_repository.update.return_value = updated_booking
        
        result = await booking_service.update_booking_status(1, BookingStatus.IN_PROGRESS, user_id=2)
        
        assert result.status == BookingStatus.IN_PROGRESS
        mock_booking_repository.update.assert_called_once()

    @pytest.mark.asyncio
    async def test_start_booking(self, booking_service, mock_booking_repository, mock_notification_service):
        """Test starting a confirmed booking"""
        confirmed_booking = Booking(
            id=1,
            service_request_id=1,
            provider_id=1,
            client_id=2,
            quote_id=1,
            status=BookingStatus.CONFIRMED,
            scheduled_start_date=datetime.now(timezone.utc) - timedelta(hours=1),
            scheduled_completion_date=datetime.now(timezone.utc) + timedelta(hours=8),
            total_cost=Decimal("1000.00")
        )
        mock_booking_repository.get_by_id.return_value = confirmed_booking
        
        started_booking = Booking(
            id=1,
            service_request_id=1,
            provider_id=1,
            client_id=2,
            quote_id=1,
            status=BookingStatus.IN_PROGRESS,
            scheduled_start_date=datetime.now(timezone.utc) - timedelta(hours=1),
            scheduled_completion_date=datetime.now(timezone.utc) + timedelta(hours=8),
            actual_start_date=datetime.now(timezone.utc),
            total_cost=Decimal("1000.00")
        )
        mock_booking_repository.update.return_value = started_booking
        
        result = await booking_service.start_booking(1, provider_id=1)
        
        assert result.status == BookingStatus.IN_PROGRESS
        assert result.actual_start_date is not None
        mock_notification_service.notify_booking_started.assert_called_once()

    @pytest.mark.asyncio
    async def test_complete_booking(self, booking_service, mock_booking_repository, mock_notification_service):
        """Test completing a booking"""
        in_progress_booking = Booking(
            id=1,
            service_request_id=1,
            provider_id=1,
            client_id=2,
            quote_id=1,
            status=BookingStatus.IN_PROGRESS,
            scheduled_start_date=datetime.now(timezone.utc) - timedelta(hours=8),
            scheduled_completion_date=datetime.now(timezone.utc),
            actual_start_date=datetime.now(timezone.utc) - timedelta(hours=8),
            total_cost=Decimal("1000.00")
        )
        mock_booking_repository.get_by_id.return_value = in_progress_booking
        
        completed_booking = Booking(
            id=1,
            service_request_id=1,
            provider_id=1,
            client_id=2,
            quote_id=1,
            status=BookingStatus.COMPLETED,
            scheduled_start_date=datetime.now(timezone.utc) - timedelta(hours=8),
            scheduled_completion_date=datetime.now(timezone.utc),
            actual_start_date=in_progress_booking.actual_start_date,
            actual_completion_date=datetime.now(timezone.utc),
            total_cost=Decimal("1000.00")
        )
        mock_booking_repository.update.return_value = completed_booking
        
        result = await booking_service.complete_booking(1, provider_id=1)
        
        assert result.status == BookingStatus.COMPLETED
        assert result.actual_end is not None
        mock_notification_service.notify_booking_completed.assert_called_once()

    # Milestone Management Tests
    @pytest.mark.asyncio
    async def test_complete_milestone(self, booking_service, mock_booking_repository, mock_payment_service):
        """Test completing a booking milestone"""
        booking = Booking(
            id=1,
            status=BookingStatus.IN_PROGRESS,
            milestones=[
                BookingMilestone(
                    id=1,
                    booking_id=1,
                    title="First milestone",
                    description="First milestone",
                    sequence_number=1,
                    amount=Decimal("1250.00"),
                    status=MilestoneStatus.PENDING
                )
            ]
        )
        mock_booking_repository.get_by_id.return_value = booking
        
        completed_milestone = BookingMilestone(
            id=1,
            booking_id=1,
            status=MilestoneStatus.COMPLETED,
            completed_at=datetime.now(timezone.utc)
        )
        mock_booking_repository.update_milestone.return_value = completed_milestone
        
        result = await booking_service.complete_milestone(1, 1, provider_id=1)
        
        assert result.status == MilestoneStatus.COMPLETED
        assert result.completed_at is not None
        mock_payment_service.process_milestone_payment.assert_called_once()

    @pytest.mark.asyncio
    async def test_cannot_complete_future_milestone(self, booking_service, mock_booking_repository):
        """Test that future milestones cannot be completed out of order"""
        booking = Booking(
            id=1,
            milestones=[
                BookingMilestone(id=1, sequence_order=1, status=MilestoneStatus.PENDING),
                BookingMilestone(id=2, sequence_order=2, status=MilestoneStatus.PENDING)
            ]
        )
        mock_booking_repository.get_by_id.return_value = booking
        
        # Try to complete milestone 2 before milestone 1
        with pytest.raises(BusinessLogicError, match="Must complete milestones in order"):
            await booking_service.complete_milestone(1, 2, provider_id=1)

    # Scheduling Tests
    @pytest.mark.asyncio
    async def test_reschedule_booking(self, booking_service, mock_booking_repository, mock_notification_service):
        """Test rescheduling a booking"""
        existing_booking = Booking(
            id=1,
            status=BookingStatus.CONFIRMED,
            scheduled_start=datetime.now(timezone.utc) + timedelta(days=3),
            scheduled_completion_date=datetime.now(timezone.utc) + timedelta(days=5)
        )
        mock_booking_repository.get_by_id.return_value = existing_booking
        
        new_schedule = {
            "scheduled_start": datetime.now(timezone.utc) + timedelta(days=7),
            "scheduled_completion_date": datetime.now(timezone.utc) + timedelta(days=9),
            "reason": "Client requested later start date"
        }
        
        rescheduled_booking = Booking(
            id=1,
            status=BookingStatus.CONFIRMED,
            scheduled_start=new_schedule["scheduled_start"],
            scheduled_completion_date=new_schedule["scheduled_completion_date"]
        )
        mock_booking_repository.update.return_value = rescheduled_booking
        
        result = await booking_service.reschedule_booking(1, new_schedule, requester_id=2)
        
        assert result.scheduled_start == new_schedule["scheduled_start"]
        mock_notification_service.notify_booking_rescheduled.assert_called_once()

    @pytest.mark.asyncio
    async def test_cannot_reschedule_completed_booking(self, booking_service, mock_booking_repository):
        """Test that completed bookings cannot be rescheduled"""
        completed_booking = Booking(
            id=1,
            status=BookingStatus.COMPLETED
        )
        mock_booking_repository.get_by_id.return_value = completed_booking
        
        new_schedule = {
            "scheduled_start": datetime.now(timezone.utc) + timedelta(days=7)
        }
        
        with pytest.raises(BusinessLogicError, match="Cannot reschedule completed booking"):
            await booking_service.reschedule_booking(1, new_schedule, requester_id=2)

    # Cancellation Tests
    @pytest.mark.asyncio
    async def test_cancel_booking(self, booking_service, mock_booking_repository, mock_notification_service, mock_payment_service):
        """Test cancelling a booking"""
        active_booking = Booking(
            id=1,
            status=BookingStatus.CONFIRMED,
            total_amount=Decimal("2500.00")
        )
        mock_booking_repository.get_by_id.return_value = active_booking
        
        cancelled_booking = Booking(
            id=1,
            status=BookingStatus.CANCELLED,
            cancellation_reason="Client changed requirements"
        )
        mock_booking_repository.update.return_value = cancelled_booking
        
        result = await booking_service.cancel_booking(1, "Client changed requirements", requester_id=2)
        
        assert result.status == BookingStatus.CANCELLED
        assert result.cancellation_reason == "Client changed requirements"
        mock_payment_service.process_cancellation_refund.assert_called_once()
        mock_notification_service.notify_booking_cancelled.assert_called_once()

    @pytest.mark.asyncio
    async def test_cancel_booking_with_penalty(self, booking_service, mock_booking_repository, mock_payment_service):
        """Test cancelling booking with cancellation penalty"""
        # Booking scheduled to start soon (within 24 hours)
        near_start_booking = Booking(
            id=1,
            status=BookingStatus.CONFIRMED,
            scheduled_start=datetime.now(timezone.utc) + timedelta(hours=12),
            total_amount=Decimal("2500.00")
        )
        mock_booking_repository.get_by_id.return_value = near_start_booking
        
        result = await booking_service.cancel_booking(1, "Emergency cancellation", requester_id=2)
        
        # Should apply cancellation penalty for short notice
        mock_payment_service.process_cancellation_refund.assert_called_once()
        call_args = mock_payment_service.process_cancellation_refund.call_args[1]
        assert "penalty_amount" in call_args
        assert call_args["penalty_amount"] > 0

    # Booking Search and Filtering Tests
    @pytest.mark.asyncio
    async def test_get_bookings_by_provider(self, booking_service, mock_booking_repository):
        """Test retrieving bookings for a provider"""
        provider_id = 1
        expected_bookings = [
            Booking(id=1, provider_id=1, status=BookingStatus.CONFIRMED),
            Booking(id=2, provider_id=1, status=BookingStatus.IN_PROGRESS),
            Booking(id=3, provider_id=1, status=BookingStatus.COMPLETED)
        ]
        mock_booking_repository.get_by_provider_id.return_value = expected_bookings
        
        result = await booking_service.get_bookings_by_provider(provider_id)
        
        assert len(result) == 3
        assert all(booking.provider_id == provider_id for booking in result)
        mock_booking_repository.get_by_provider_id.assert_called_once_with(provider_id)

    @pytest.mark.asyncio
    async def test_get_bookings_by_seeker(self, booking_service, mock_booking_repository):
        """Test retrieving bookings for a seeker"""
        seeker_id = 2
        expected_bookings = [
            Booking(id=1, seeker_id=2, status=BookingStatus.CONFIRMED),
            Booking(id=2, seeker_id=2, status=BookingStatus.COMPLETED)
        ]
        mock_booking_repository.get_by_seeker_id.return_value = expected_bookings
        
        result = await booking_service.get_bookings_by_seeker(seeker_id)
        
        assert len(result) == 2
        assert all(booking.seeker_id == seeker_id for booking in result)
        mock_booking_repository.get_by_seeker_id.assert_called_once_with(seeker_id)

    @pytest.mark.asyncio
    async def test_get_upcoming_bookings(self, booking_service, mock_booking_repository):
        """Test retrieving upcoming bookings"""
        upcoming_date = datetime.now(timezone.utc) + timedelta(days=7)
        expected_bookings = [
            Booking(id=1, scheduled_start=datetime.now(timezone.utc) + timedelta(days=2)),
            Booking(id=2, scheduled_start=datetime.now(timezone.utc) + timedelta(days=5))
        ]
        mock_booking_repository.get_upcoming_bookings.return_value = expected_bookings
        
        result = await booking_service.get_upcoming_bookings(upcoming_date)
        
        assert len(result) == 2
        mock_booking_repository.get_upcoming_bookings.assert_called_once_with(upcoming_date)

    # Booking Analytics Tests
    @pytest.mark.asyncio
    async def test_get_booking_analytics(self, booking_service, mock_booking_repository):
        """Test retrieving booking performance analytics"""
        booking_id = 1
        expected_analytics = {
            "duration_actual_vs_estimated": {
                "estimated_hours": 16,
                "actual_hours": 18,
                "variance_percentage": 12.5
            },
            "cost_breakdown": {
                "labor": Decimal("2000.00"),
                "materials": Decimal("400.00"),
                "travel": Decimal("100.00")
            },
            "milestone_completion_rate": 1.0,
            "customer_satisfaction_score": 4.5
        }
        mock_booking_repository.get_analytics.return_value = expected_analytics
        
        result = await booking_service.get_booking_analytics(booking_id)
        
        assert result["duration_actual_vs_estimated"]["variance_percentage"] == 12.5
        assert result["milestone_completion_rate"] == 1.0
        mock_booking_repository.get_analytics.assert_called_once_with(booking_id)

    @pytest.mark.asyncio
    async def test_get_provider_booking_statistics(self, booking_service, mock_booking_repository):
        """Test retrieving provider's booking statistics"""
        provider_id = 1
        expected_stats = {
            "total_bookings": 25,
            "completion_rate": 0.96,
            "average_rating": 4.7,
            "on_time_completion_rate": 0.88,
            "cancellation_rate": 0.04,
            "revenue_last_30_days": Decimal("12500.00")
        }
        mock_booking_repository.get_provider_statistics.return_value = expected_stats
        
        result = await booking_service.get_provider_booking_statistics(provider_id)
        
        assert result["total_bookings"] == 25
        assert result["completion_rate"] == 0.96
        mock_booking_repository.get_provider_statistics.assert_called_once_with(provider_id)

    # Communication and Updates Tests
    @pytest.mark.asyncio
    async def test_add_booking_update(self, booking_service, mock_booking_repository, mock_notification_service):
        """Test adding progress update to booking"""
        booking = Booking(id=1, status=BookingStatus.IN_PROGRESS)
        mock_booking_repository.get_by_id.return_value = booking
        
        update_data = {
            "message": "Completed electrical rough-in, starting drywall prep",
            "progress_percentage": 60,
            "images": ["progress_photo_1.jpg", "progress_photo_2.jpg"]
        }
        
        result = await booking_service.add_progress_update(1, update_data, provider_id=1)
        
        assert result is True
        mock_booking_repository.add_progress_update.assert_called_once()
        mock_notification_service.notify_progress_update.assert_called_once()

    # Error Handling Tests
    @pytest.mark.asyncio
    async def test_booking_service_handles_repository_errors(self, booking_service, mock_booking_repository):
        """Test that service properly handles repository errors"""
        mock_booking_repository.get_by_id.side_effect = Exception("Database connection failed")
        
        with pytest.raises(Exception, match="Database connection failed"):
            await booking_service.get_booking(1, user_id=123)

    @pytest.mark.asyncio
    async def test_validation_error_on_invalid_booking_data(self, booking_service, mock_quote_repository, mock_request_repository):
        """Test validation errors for invalid booking data"""
        # Set up mocks for accepted quote and request
        accepted_quote = Quote(
            id=1,
            request_id=1,
            provider_id=1,
            status=QuoteStatus.ACCEPTED,
            total_cost=Decimal("1000.00")
        )
        mock_quote_repository.get_by_id.return_value = accepted_quote
        
        service_request = ServiceRequest(
            id=1,
            seeker_id=1,
            title="Test Request"
        )
        mock_request_repository.get_by_id.return_value = service_request
        
        invalid_milestone_data = [
            {
                "description": "",  # Empty description
                "percentage": 150,  # Invalid percentage > 100
                "due_date": datetime.now(timezone.utc) - timedelta(days=1)  # Past date
            }
        ]
        
        with pytest.raises(ValidationError):
            await booking_service.create_booking_with_milestones(1, invalid_milestone_data)