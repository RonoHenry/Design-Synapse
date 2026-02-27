"""
Property-based tests for BookingService
Testing universal properties that should hold across all inputs
"""
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, Mock

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st
from src.core.exceptions import (BusinessLogicError, NotFoundError,
                                 UnauthorizedError)
from src.models.booking import BookingStatus
from src.services.booking_service import BookingService


class TestBookingServiceProperties:
    """Property-based tests for BookingService"""

    @pytest.fixture(scope="session")
    def mock_booking_repository(self):
        """Mock booking repository for property testing"""
        mock = Mock()
        mock.get_by_id = AsyncMock()
        mock.update_booking_status = AsyncMock()
        mock.update = AsyncMock()
        mock.save = AsyncMock()
        mock.create = AsyncMock()
        mock.create_with_milestones = AsyncMock()
        return mock

    @pytest.fixture(scope="session")
    def mock_quote_repository(self):
        """Mock quote repository for property testing"""
        mock = Mock()
        mock.get_by_id = AsyncMock()
        return mock

    @pytest.fixture(scope="session")
    def mock_request_repository(self):
        """Mock request repository for property testing"""
        mock = Mock()
        mock.get_by_id = AsyncMock()
        return mock

    @pytest.fixture(scope="session")
    def mock_notification_service(self):
        """Mock notification service for property testing"""
        mock = Mock()
        mock.notify_booking_started = Mock()
        mock.notify_booking_completed = Mock()
        mock.notify_booking_cancelled = Mock()
        return mock

    @pytest.fixture(scope="session")
    def booking_service(
        self,
        mock_booking_repository,
        mock_quote_repository,
        mock_request_repository,
        mock_notification_service,
    ):
        """Create BookingService instance with mocked dependencies"""
        return BookingService(
            booking_repository=mock_booking_repository,
            quote_repository=mock_quote_repository,
            request_repository=mock_request_repository,
            notification_service=mock_notification_service,
        )

    def create_mock_booking(
        self, booking_id: int, status: BookingStatus, provider_id: int, client_id: int
    ):
        """Create a mock booking object"""
        mock_booking = Mock()
        mock_booking.id = booking_id
        mock_booking.status = status
        mock_booking.provider_id = provider_id
        mock_booking.client_id = client_id
        mock_booking.total_cost = Decimal("1000.00")
        mock_booking.scheduled_start_date = datetime.now(timezone.utc) + timedelta(
            hours=2
        )
        mock_booking.notes = ""
        return mock_booking

    @given(
        booking_id=st.integers(min_value=1, max_value=10000),
        provider_id=st.integers(min_value=1, max_value=1000),
        client_id=st.integers(
            min_value=1001, max_value=2000
        ),  # Ensure different from provider
    )
    @settings(
        suppress_health_check=[HealthCheck.function_scoped_fixture], max_examples=20
    )
    @pytest.mark.asyncio
    async def test_property_booking_state_transitions_follow_business_rules(
        self,
        booking_service,
        mock_booking_repository,
        booking_id,
        provider_id,
        client_id,
    ):
        """
        **Feature: labor-service-fixes, Property 3: Booking state transitions follow business rules**
        **Validates: Requirements 2.1, 2.2, 2.3, 5.2**

        For any booking, state transitions should follow the defined state machine rules:
        - CONFIRMED → IN_PROGRESS (only by provider)
        - CONFIRMED → CANCELLED (by provider or client)
        - IN_PROGRESS → COMPLETED (only by provider)
        - IN_PROGRESS → CANCELLED (by provider or client)
        - COMPLETED → (no transitions allowed)
        - CANCELLED → (no transitions allowed)
        """
        # Test CONFIRMED → IN_PROGRESS transition
        confirmed_booking = self.create_mock_booking(
            booking_id, BookingStatus.CONFIRMED, provider_id, client_id
        )
        mock_booking_repository.get_by_id.return_value = confirmed_booking
        mock_booking_repository.update_booking_status.return_value = confirmed_booking

        # Property: Provider can start confirmed booking
        try:
            result = await booking_service.start_booking(booking_id, provider_id)
            # Should succeed without exception
            assert result is not None
        except Exception as e:
            # Should not raise exceptions for valid transitions
            pytest.fail(f"Valid transition CONFIRMED → IN_PROGRESS failed: {e}")

        # Property: Client cannot start booking (should raise UnauthorizedError)
        with pytest.raises((UnauthorizedError, BusinessLogicError)):
            await booking_service.start_booking(booking_id, client_id)

        # Test IN_PROGRESS → COMPLETED transition
        in_progress_booking = self.create_mock_booking(
            booking_id, BookingStatus.IN_PROGRESS, provider_id, client_id
        )
        mock_booking_repository.get_by_id.return_value = in_progress_booking

        # Property: Provider can complete in-progress booking
        try:
            result = await booking_service.complete_booking(booking_id, provider_id)
            assert result is not None
        except Exception as e:
            pytest.fail(f"Valid transition IN_PROGRESS → COMPLETED failed: {e}")

        # Property: Client cannot complete booking
        with pytest.raises((UnauthorizedError, BusinessLogicError)):
            await booking_service.complete_booking(booking_id, client_id)

    @given(
        booking_id=st.integers(min_value=1, max_value=10000),
        provider_id=st.integers(min_value=1, max_value=1000),
        client_id=st.integers(min_value=1001, max_value=2000),
        cancellation_reason=st.text(min_size=1, max_size=100),
    )
    @settings(
        suppress_health_check=[HealthCheck.function_scoped_fixture], max_examples=15
    )
    @pytest.mark.asyncio
    async def test_property_cancellation_allowed_from_valid_states(
        self,
        booking_service,
        mock_booking_repository,
        booking_id,
        provider_id,
        client_id,
        cancellation_reason,
    ):
        """
        **Feature: labor-service-fixes, Property 3: Booking state transitions follow business rules**
        **Validates: Requirements 2.1, 2.2, 2.3, 5.2**

        For any booking in CONFIRMED or IN_PROGRESS state, both provider and client
        should be able to cancel the booking.
        """
        # Test cancellation from CONFIRMED state
        confirmed_booking = self.create_mock_booking(
            booking_id, BookingStatus.CONFIRMED, provider_id, client_id
        )
        mock_booking_repository.get_by_id.return_value = confirmed_booking
        mock_booking_repository.update_booking_status.return_value = confirmed_booking
        mock_booking_repository.update.return_value = confirmed_booking

        # Property: Both provider and client can cancel confirmed booking
        try:
            result = await booking_service.cancel_booking(
                booking_id, cancellation_reason, provider_id
            )
            assert result is not None
        except Exception as e:
            pytest.fail(f"Provider cancellation from CONFIRMED failed: {e}")

        try:
            result = await booking_service.cancel_booking(
                booking_id, cancellation_reason, client_id
            )
            assert result is not None
        except Exception as e:
            pytest.fail(f"Client cancellation from CONFIRMED failed: {e}")

        # Test cancellation from IN_PROGRESS state
        in_progress_booking = self.create_mock_booking(
            booking_id, BookingStatus.IN_PROGRESS, provider_id, client_id
        )
        mock_booking_repository.get_by_id.return_value = in_progress_booking

        # Property: Both provider and client can cancel in-progress booking
        try:
            result = await booking_service.cancel_booking(
                booking_id, cancellation_reason, provider_id
            )
            assert result is not None
        except Exception as e:
            pytest.fail(f"Provider cancellation from IN_PROGRESS failed: {e}")

    @given(
        booking_id=st.integers(min_value=1, max_value=10000),
        user_id=st.integers(min_value=1, max_value=2000),
    )
    @settings(
        suppress_health_check=[HealthCheck.function_scoped_fixture], max_examples=10
    )
    @pytest.mark.asyncio
    async def test_property_terminal_states_prevent_transitions(
        self, booking_service, mock_booking_repository, booking_id, user_id
    ):
        """
        **Feature: labor-service-fixes, Property 3: Booking state transitions follow business rules**
        **Validates: Requirements 2.1, 2.2, 2.3, 5.2**

        For any booking in COMPLETED or CANCELLED state (terminal states),
        no further state transitions should be allowed.
        """
        # Test COMPLETED state (terminal)
        completed_booking = self.create_mock_booking(
            booking_id, BookingStatus.COMPLETED, user_id, user_id + 1000
        )
        mock_booking_repository.get_by_id.return_value = completed_booking

        # Property: Cannot transition from COMPLETED to any other state
        with pytest.raises((BusinessLogicError, UnauthorizedError)):
            await booking_service.cancel_booking(booking_id, "test reason", user_id)

        # Test CANCELLED state (terminal)
        cancelled_booking = self.create_mock_booking(
            booking_id, BookingStatus.CANCELLED, user_id, user_id + 1000
        )
        mock_booking_repository.get_by_id.return_value = cancelled_booking

        # Property: Cannot start cancelled booking
        with pytest.raises((BusinessLogicError, UnauthorizedError)):
            await booking_service.start_booking(booking_id, user_id)

        # Property: Cannot complete cancelled booking
        with pytest.raises((BusinessLogicError, UnauthorizedError)):
            await booking_service.complete_booking(booking_id, user_id)

    @given(
        booking_id=st.integers(min_value=1, max_value=10000),
        provider_id=st.integers(min_value=1, max_value=1000),
        client_id=st.integers(min_value=1001, max_value=2000),
        unauthorized_user_id=st.integers(min_value=2001, max_value=3000),
    )
    @settings(
        suppress_health_check=[HealthCheck.function_scoped_fixture], max_examples=10
    )
    @pytest.mark.asyncio
    async def test_property_unauthorized_users_cannot_transition_states(
        self,
        booking_service,
        mock_booking_repository,
        booking_id,
        provider_id,
        client_id,
        unauthorized_user_id,
    ):
        """
        **Feature: labor-service-fixes, Property 3: Booking state transitions follow business rules**
        **Validates: Requirements 2.1, 2.2, 2.3, 5.2**

        For any booking, users who are neither the provider nor the client
        should not be able to perform state transitions.
        """
        confirmed_booking = self.create_mock_booking(
            booking_id, BookingStatus.CONFIRMED, provider_id, client_id
        )
        mock_booking_repository.get_by_id.return_value = confirmed_booking

        # Property: Unauthorized user cannot start booking
        with pytest.raises((UnauthorizedError, BusinessLogicError)):
            await booking_service.start_booking(booking_id, unauthorized_user_id)

        # Property: Unauthorized user cannot cancel booking
        with pytest.raises((UnauthorizedError, BusinessLogicError)):
            await booking_service.cancel_booking(
                booking_id, "test reason", unauthorized_user_id
            )

        in_progress_booking = self.create_mock_booking(
            booking_id, BookingStatus.IN_PROGRESS, provider_id, client_id
        )
        mock_booking_repository.get_by_id.return_value = in_progress_booking

        # Property: Unauthorized user cannot complete booking
        with pytest.raises((UnauthorizedError, BusinessLogicError)):
            await booking_service.complete_booking(booking_id, unauthorized_user_id)

    @pytest.mark.asyncio
    async def test_property_state_machine_consistency(self, booking_service):
        """
        **Feature: labor-service-fixes, Property 3: Booking state transitions follow business rules**
        **Validates: Requirements 2.1, 2.2, 2.3, 5.2**

        The state machine transition rules should be consistent and well-defined.
        """
        # Property: All states should have defined transition rules
        all_states = [
            BookingStatus.CONFIRMED,
            BookingStatus.IN_PROGRESS,
            BookingStatus.COMPLETED,
            BookingStatus.CANCELLED,
        ]

        for current_state in all_states:
            for target_state in all_states:
                if current_state != target_state:
                    # This should not raise an exception - just return True or False
                    result = booking_service._is_valid_status_transition(
                        current_state, target_state
                    )
                    assert isinstance(result, bool)

        # Property: Terminal states should have no valid outgoing transitions
        terminal_states = [BookingStatus.COMPLETED, BookingStatus.CANCELLED]
        for terminal_state in terminal_states:
            for target_state in all_states:
                if terminal_state != target_state:
                    assert not booking_service._is_valid_status_transition(
                        terminal_state, target_state
                    )

        # Property: CONFIRMED state should allow transitions to IN_PROGRESS and CANCELLED
        assert booking_service._is_valid_status_transition(
            BookingStatus.CONFIRMED, BookingStatus.IN_PROGRESS
        )
        assert booking_service._is_valid_status_transition(
            BookingStatus.CONFIRMED, BookingStatus.CANCELLED
        )
        assert not booking_service._is_valid_status_transition(
            BookingStatus.CONFIRMED, BookingStatus.COMPLETED
        )

        # Property: IN_PROGRESS state should allow transitions to COMPLETED and CANCELLED
        assert booking_service._is_valid_status_transition(
            BookingStatus.IN_PROGRESS, BookingStatus.COMPLETED
        )
        assert booking_service._is_valid_status_transition(
            BookingStatus.IN_PROGRESS, BookingStatus.CANCELLED
        )
        assert not booking_service._is_valid_status_transition(
            BookingStatus.IN_PROGRESS, BookingStatus.CONFIRMED
        )
