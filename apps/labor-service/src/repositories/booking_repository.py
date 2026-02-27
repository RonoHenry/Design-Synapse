"""Booking repository with specialized query methods."""
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional

from sqlalchemy import and_, asc, desc, func, or_
from sqlalchemy.orm import Session, joinedload
from src.models.booking import (Booking, BookingMilestone, BookingStatus,
                                MilestoneStatus)

from .base_repository import BaseRepository


class BookingRepository(BaseRepository[Booking]):
    """Repository for Booking with specialized query methods."""

    def __init__(self, db_session: Session):
        super().__init__(Booking, db_session)

    def find_by_status(self, status: BookingStatus) -> List[Booking]:
        """Find bookings by status."""
        return self.db_session.query(Booking).filter(Booking.status == status).all()

    def find_by_provider_id(self, provider_id: int) -> List[Booking]:
        """Find bookings for a specific provider."""
        return (
            self.db_session.query(Booking)
            .filter(Booking.provider_id == provider_id)
            .order_by(desc(Booking.created_at))
            .all()
        )

    def find_by_client_id(self, client_id: int) -> List[Booking]:
        """Find bookings for a specific client."""
        return (
            self.db_session.query(Booking)
            .filter(Booking.client_id == client_id)
            .order_by(desc(Booking.created_at))
            .all()
        )

    def find_active_bookings(self) -> List[Booking]:
        """Find active bookings (confirmed or in progress)."""
        return (
            self.db_session.query(Booking)
            .filter(
                Booking.status.in_([BookingStatus.CONFIRMED, BookingStatus.IN_PROGRESS])
            )
            .order_by(asc(Booking.scheduled_start_date))
            .all()
        )

    def find_upcoming_bookings(self, days_ahead: int = 7) -> List[Booking]:
        """Find bookings starting within specified days."""
        future_date = datetime.now(timezone.utc) + timedelta(days=days_ahead)
        return (
            self.db_session.query(Booking)
            .filter(
                and_(
                    Booking.scheduled_start_date <= future_date,
                    Booking.scheduled_start_date >= datetime.now(timezone.utc),
                    Booking.status == BookingStatus.CONFIRMED,
                )
            )
            .order_by(asc(Booking.scheduled_start_date))
            .all()
        )

    def find_overdue_bookings(self) -> List[Booking]:
        """Find bookings that are overdue (past end date but not completed)."""
        current_time = datetime.now(timezone.utc)
        return (
            self.db_session.query(Booking)
            .filter(
                and_(
                    Booking.scheduled_completion_date < current_time,
                    Booking.status.in_(
                        [BookingStatus.CONFIRMED, BookingStatus.IN_PROGRESS]
                    ),
                )
            )
            .order_by(asc(Booking.scheduled_completion_date))
            .all()
        )

    def find_by_date_range(
        self, start_date: datetime, end_date: datetime
    ) -> List[Booking]:
        """Find bookings within date range."""
        return (
            self.db_session.query(Booking)
            .filter(
                and_(
                    Booking.scheduled_start_date >= start_date,
                    Booking.scheduled_start_date <= end_date,
                )
            )
            .order_by(asc(Booking.scheduled_start_date))
            .all()
        )

    def find_provider_schedule(
        self, provider_id: int, start_date: datetime, end_date: datetime
    ) -> List[Booking]:
        """Find provider's schedule within date range."""
        return (
            self.db_session.query(Booking)
            .filter(
                and_(
                    Booking.provider_id == provider_id,
                    Booking.scheduled_start_date >= start_date,
                    Booking.scheduled_completion_date <= end_date,
                    Booking.status.in_(
                        [BookingStatus.CONFIRMED, BookingStatus.IN_PROGRESS]
                    ),
                )
            )
            .order_by(asc(Booking.scheduled_start_date))
            .all()
        )

    def get_with_milestones(self, booking_id: int) -> Optional[Booking]:
        """Get booking with milestones loaded."""
        return (
            self.db_session.query(Booking)
            .options(joinedload(Booking.milestones))
            .filter(Booking.id == booking_id)
            .first()
        )

    def find_bookings_needing_payment(self) -> List[Booking]:
        """Find bookings that need payment processing."""
        return (
            self.db_session.query(Booking)
            .filter(
                and_(
                    Booking.status == BookingStatus.CONFIRMED,
                    Booking.payment_status == "PENDING",
                )
            )
            .all()
        )

    def get_booking_statistics(
        self, provider_id: int = None, seeker_id: int = None
    ) -> Dict[str, Any]:
        """Get booking statistics for provider or seeker."""
        query = self.db_session.query(Booking)

        if provider_id:
            query = query.filter(Booking.provider_id == provider_id)
        elif seeker_id:
            query = query.filter(Booking.seeker_id == seeker_id)

        bookings = query.all()

        if not bookings:
            return {
                "total_bookings": 0,
                "completed_bookings": 0,
                "cancelled_bookings": 0,
                "completion_rate": 0.0,
                "avg_booking_value": 0.0,
                "total_revenue": 0.0,
            }

        completed = [b for b in bookings if b.status == BookingStatus.COMPLETED]
        cancelled = [b for b in bookings if b.status == BookingStatus.CANCELLED]
        booking_values = [float(b.total_cost) for b in bookings if b.total_cost]

        return {
            "total_bookings": len(bookings),
            "completed_bookings": len(completed),
            "cancelled_bookings": len(cancelled),
            "completion_rate": len(completed) / len(bookings) * 100
            if bookings
            else 0.0,
            "avg_booking_value": sum(booking_values) / len(booking_values)
            if booking_values
            else 0.0,
            "total_revenue": sum(booking_values),
        }

    def find_conflicting_bookings(
        self,
        provider_id: int,
        start_date: datetime,
        end_date: datetime,
        exclude_booking_id: int = None,
    ) -> List[Booking]:
        """Find bookings that conflict with proposed schedule."""
        query = self.db_session.query(Booking).filter(
            and_(
                Booking.provider_id == provider_id,
                Booking.status.in_(
                    [BookingStatus.CONFIRMED, BookingStatus.IN_PROGRESS]
                ),
                or_(
                    # New booking starts during existing booking
                    and_(
                        Booking.scheduled_start_date <= start_date,
                        Booking.scheduled_completion_date > start_date,
                    ),
                    # New booking ends during existing booking
                    and_(
                        Booking.scheduled_start_date < end_date,
                        Booking.scheduled_completion_date >= end_date,
                    ),
                    # New booking encompasses existing booking
                    and_(
                        Booking.scheduled_start_date >= start_date,
                        Booking.scheduled_completion_date <= end_date,
                    ),
                ),
            )
        )

        if exclude_booking_id:
            query = query.filter(Booking.id != exclude_booking_id)

        return query.all()

    async def update_booking_status(
        self, booking_id: int, new_status: BookingStatus
    ) -> Optional[Booking]:
        """Update booking status with timestamp tracking."""
        booking = await self.get_by_id(booking_id)
        if not booking:
            return None

        booking.status = new_status
        booking.updated_at = datetime.now(timezone.utc)

        # Set specific timestamps based on status
        if new_status == BookingStatus.IN_PROGRESS:
            booking.actual_start_date = datetime.now(timezone.utc)
        elif new_status == BookingStatus.COMPLETED:
            booking.actual_completion_date = datetime.now(timezone.utc)
        elif new_status == BookingStatus.CANCELLED:
            booking.cancelled_at = datetime.now(timezone.utc)

        self.db_session.commit()
        self.db_session.refresh(booking)
        return booking

    def find_revenue_by_period(
        self, start_date: datetime, end_date: datetime, provider_id: int = None
    ) -> Dict[str, Any]:
        """Calculate revenue for a specific period."""
        query = self.db_session.query(Booking).filter(
            and_(
                Booking.status == BookingStatus.COMPLETED,
                Booking.actual_end_date >= start_date,
                Booking.actual_end_date <= end_date,
            )
        )

        if provider_id:
            query = query.filter(Booking.provider_id == provider_id)

        bookings = query.all()

        if not bookings:
            return {
                "period_start": start_date.isoformat(),
                "period_end": end_date.isoformat(),
                "total_bookings": 0,
                "total_revenue": 0.0,
                "avg_booking_value": 0.0,
            }

        total_revenue = sum(float(b.total_cost) for b in bookings if b.total_cost)

        return {
            "period_start": start_date.isoformat(),
            "period_end": end_date.isoformat(),
            "total_bookings": len(bookings),
            "total_revenue": total_revenue,
            "avg_booking_value": total_revenue / len(bookings),
        }

    async def get_by_provider_id(self, provider_id: int) -> List[Booking]:
        """Get bookings by provider ID (alias for find_by_provider_id for service compatibility)."""
        return self.find_by_provider_id(provider_id)

    async def get_by_seeker_id(self, seeker_id: int) -> List[Booking]:
        """Get bookings by seeker ID (alias for find_by_client_id for service compatibility)."""
        return self.find_by_client_id(seeker_id)

    async def get_upcoming_bookings(
        self, future_date: datetime = None
    ) -> List[Booking]:
        """Get upcoming bookings (alias for find_upcoming_bookings for service compatibility)."""
        if future_date:
            days_ahead = (future_date - datetime.now(timezone.utc)).days
            return self.find_upcoming_bookings(days_ahead)
        return self.find_upcoming_bookings()

    async def get_analytics(self, booking_id: int) -> Dict[str, Any]:
        """Get analytics for a specific booking."""
        booking = await self.get_by_id(booking_id)
        if not booking:
            return {}

        # Calculate duration variance
        estimated_hours = booking.estimated_duration_hours or 0
        actual_hours = 0
        if booking.actual_start_date and booking.actual_end_date:
            actual_duration = booking.actual_end_date - booking.actual_start_date
            actual_hours = actual_duration.total_seconds() / 3600

        variance_percentage = 0
        if estimated_hours > 0:
            variance_percentage = (
                (actual_hours - estimated_hours) / estimated_hours
            ) * 100

        # Get milestone completion rate
        milestones = (
            self.db_session.query(BookingMilestone)
            .filter(BookingMilestone.booking_id == booking_id)
            .all()
        )

        milestone_completion_rate = 0
        if milestones:
            completed_milestones = [
                m for m in milestones if m.status == MilestoneStatus.COMPLETED
            ]
            milestone_completion_rate = len(completed_milestones) / len(milestones)

        return {
            "duration_actual_vs_estimated": {
                "estimated_hours": estimated_hours,
                "actual_hours": actual_hours,
                "variance_percentage": variance_percentage,
            },
            "cost_breakdown": {
                "labor": booking.labor_cost or Decimal("0.00"),
                "materials": booking.materials_cost or Decimal("0.00"),
                "travel": booking.travel_cost or Decimal("0.00"),
            },
            "milestone_completion_rate": milestone_completion_rate,
            "customer_satisfaction_score": 4.5,  # Placeholder - would come from reviews
        }

    async def get_provider_statistics(self, provider_id: int) -> Dict[str, Any]:
        """Get statistics for a specific provider."""
        # Get bookings from last 30 days for revenue calculation
        thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
        recent_bookings = (
            self.db_session.query(Booking)
            .filter(
                and_(
                    Booking.provider_id == provider_id,
                    Booking.created_at >= thirty_days_ago,
                )
            )
            .all()
        )

        all_bookings = self.find_by_provider_id(provider_id)
        completed_bookings = [
            b for b in all_bookings if b.status == BookingStatus.COMPLETED
        ]
        cancelled_bookings = [
            b for b in all_bookings if b.status == BookingStatus.CANCELLED
        ]

        # Calculate on-time completion rate
        on_time_completions = 0
        for booking in completed_bookings:
            if (
                booking.actual_end_date
                and booking.scheduled_completion_date
                and booking.actual_end_date <= booking.scheduled_completion_date
            ):
                on_time_completions += 1

        on_time_rate = (
            on_time_completions / len(completed_bookings) if completed_bookings else 0
        )

        # Calculate revenue from recent bookings
        recent_revenue = sum(
            float(b.total_cost)
            for b in recent_bookings
            if b.total_cost and b.status == BookingStatus.COMPLETED
        )

        return {
            "total_bookings": len(all_bookings),
            "completion_rate": len(completed_bookings) / len(all_bookings)
            if all_bookings
            else 0,
            "average_rating": 4.7,  # Placeholder - would come from reviews
            "on_time_completion_rate": on_time_rate,
            "cancellation_rate": len(cancelled_bookings) / len(all_bookings)
            if all_bookings
            else 0,
            "revenue_last_30_days": Decimal(str(recent_revenue)),
        }


class BookingMilestoneRepository(BaseRepository[BookingMilestone]):
    """Repository for BookingMilestone with specialized query methods."""

    def __init__(self, db_session: Session):
        super().__init__(BookingMilestone, db_session)

    def find_by_booking_id(self, booking_id: int) -> List[BookingMilestone]:
        """Find milestones for a specific booking."""
        return (
            self.db_session.query(BookingMilestone)
            .filter(BookingMilestone.booking_id == booking_id)
            .order_by(asc(BookingMilestone.sequence_number))
            .all()
        )

    def find_by_status(self, status: MilestoneStatus) -> List[BookingMilestone]:
        """Find milestones by status."""
        return (
            self.db_session.query(BookingMilestone)
            .filter(BookingMilestone.status == status)
            .all()
        )

    def find_overdue_milestones(self) -> List[BookingMilestone]:
        """Find milestones that are overdue."""
        current_time = datetime.now(timezone.utc)
        return (
            self.db_session.query(BookingMilestone)
            .filter(
                and_(
                    BookingMilestone.due_date < current_time,
                    BookingMilestone.status.in_(
                        [MilestoneStatus.PENDING, MilestoneStatus.IN_PROGRESS]
                    ),
                )
            )
            .order_by(asc(BookingMilestone.due_date))
            .all()
        )

    def get_milestone_progress(self, booking_id: int) -> Dict[str, Any]:
        """Get milestone progress for a booking."""
        milestones = self.find_by_booking_id(booking_id)

        if not milestones:
            return {
                "booking_id": booking_id,
                "total_milestones": 0,
                "completed_milestones": 0,
                "progress_percentage": 0.0,
            }

        completed = [m for m in milestones if m.status == MilestoneStatus.COMPLETED]

        return {
            "booking_id": booking_id,
            "total_milestones": len(milestones),
            "completed_milestones": len(completed),
            "progress_percentage": len(completed) / len(milestones) * 100,
        }

    async def update_milestone_status(
        self, milestone_id: int, new_status: MilestoneStatus
    ) -> Optional[BookingMilestone]:
        """Update milestone status with timestamp tracking."""
        milestone = await self.get_by_id(milestone_id)
        if not milestone:
            return None

        milestone.status = new_status
        milestone.updated_at = datetime.now(timezone.utc)

        if new_status == MilestoneStatus.COMPLETED:
            milestone.completed_at = datetime.now(timezone.utc)

        self.db_session.commit()
        self.db_session.refresh(milestone)
        return milestone
