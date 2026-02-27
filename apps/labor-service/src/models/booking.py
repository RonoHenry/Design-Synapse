"""
Booking and BookingMilestone Models - Labor Services Marketplace

This module implements the Booking and BookingMilestone models following TDD principles.
These models represent confirmed work engagements and payment milestones.
"""

from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional

from sqlalchemy import JSON, Boolean, Column, DateTime
from sqlalchemy import Enum as SQLEnum
from sqlalchemy import ForeignKey, Index, Integer, Numeric, String, Text
from sqlalchemy.orm import relationship, validates

from .base import Base


class BookingStatus(str, Enum):
    """Enumeration for booking status workflow."""

    CONFIRMED = "CONFIRMED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"
    DISPUTED = "DISPUTED"


class MilestoneStatus(str, Enum):
    """Enumeration for milestone status workflow."""

    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    PAID = "PAID"
    DISPUTED = "DISPUTED"


class Booking(Base):
    """
    Booking model representing confirmed work engagements.

    This model follows TDD principles and implements the behavior
    defined in the failing tests.
    """

    __tablename__ = "bookings"

    # Optimized composite indexes for high-performance queries
    __table_args__ = (
        # Core business logic indexes
        Index(
            "idx_provider_status_schedule",
            "provider_id",
            "status",
            "scheduled_start_date",
        ),
        Index(
            "idx_client_status_schedule", "client_id", "status", "scheduled_start_date"
        ),
        Index(
            "idx_schedule_range",
            "scheduled_start_date",
            "scheduled_completion_date",
            "status",
        ),
        # Performance optimization indexes
        Index(
            "idx_booking_status_created", "status", "created_at"
        ),  # For status-based queries
        Index(
            "idx_quote_booking", "quote_id", "status"
        ),  # For quote-to-booking tracking
        Index(
            "idx_service_request_booking", "service_request_id", "status"
        ),  # For request tracking
        # Calendar and scheduling optimization
        Index(
            "idx_active_schedule",
            "scheduled_start_date",
            "scheduled_completion_date",
            postgresql_where="status IN ('CONFIRMED', 'IN_PROGRESS')",
        ),
    )

    # Primary key
    id = Column(Integer, primary_key=True, index=True)

    # Relationships
    service_request_id = Column(
        Integer,
        ForeignKey("service_requests.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    quote_id = Column(
        Integer, ForeignKey("quotes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    provider_id = Column(
        Integer, nullable=False, index=True
    )  # References ServiceProvider
    client_id = Column(Integer, nullable=False, index=True)  # References User Service

    # Schedule information
    scheduled_start_date = Column(DateTime, nullable=False)
    scheduled_completion_date = Column(DateTime, nullable=False)
    actual_start_date = Column(DateTime, nullable=True)
    actual_completion_date = Column(DateTime, nullable=True)

    # Aliases for backward compatibility with tests
    @property
    def scheduled_end_date(self):
        """Alias for scheduled_completion_date for test compatibility."""
        return self.scheduled_completion_date

    @scheduled_end_date.setter
    def scheduled_end_date(self, value):
        """Setter for scheduled_end_date alias."""
        self.scheduled_completion_date = value

    @property
    def actual_end_date(self):
        """Alias for actual_completion_date for test compatibility."""
        return self.actual_completion_date

    @actual_end_date.setter
    def actual_end_date(self, value):
        """Setter for actual_end_date alias."""
        self.actual_completion_date = value
        self.scheduled_completion_date = value

    @property
    def scheduled_start(self):
        """Alias for scheduled_start_date for test compatibility."""
        return self.scheduled_start_date

    @scheduled_start.setter
    def scheduled_start(self, value):
        """Setter for scheduled_start alias."""
        self.scheduled_start_date = value

    @property
    def actual_end(self):
        """Alias for actual_completion_date for test compatibility."""
        return self.actual_completion_date

    @actual_end.setter
    def actual_end(self, value):
        """Setter for actual_end alias."""
        self.actual_completion_date = value

    @property
    def seeker_id(self):
        """Alias for client_id for test compatibility."""
        return self.client_id

    @seeker_id.setter
    def seeker_id(self, value):
        """Setter for seeker_id alias."""
        self.client_id = value

    @property
    def total_amount(self):
        """Alias for total_cost for test compatibility."""
        return self.total_cost

    @total_amount.setter
    def total_amount(self, value):
        """Setter for total_amount alias."""
        self.total_cost = value

    # Cost and payment information
    total_cost = Column(Numeric(10, 2), nullable=False)
    currency = Column(String(3), nullable=False, default="USD")
    payment_terms = Column(JSON, nullable=True)  # Structured payment terms

    # Status and workflow
    status = Column(
        SQLEnum(BookingStatus), nullable=False, default=BookingStatus.CONFIRMED
    )

    # Additional information
    notes = Column(Text, nullable=True)
    cancellation_reason = Column(String(500), nullable=True)
    cancellation_penalty = Column(
        Numeric(10, 2), nullable=True, default=Decimal("0.00")
    )

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    cancelled_at = Column(DateTime, nullable=True)

    # Optimized relationships with proper loading strategies
    service_request = relationship(
        "ServiceRequest", lazy="select"  # Explicit lazy loading
    )
    quote = relationship("Quote", lazy="select")  # Explicit lazy loading
    milestones = relationship(
        "BookingMilestone",
        back_populates="booking",
        cascade="all, delete-orphan",
        lazy="select",  # Explicit lazy loading for better control
        order_by="BookingMilestone.sequence_number",
    )

    # Virtual relationship to reviews
    reviews = relationship(
        "Review",
        foreign_keys="Review.booking_id",
        lazy="dynamic",  # Dynamic loading for optional data
        order_by="Review.created_at.desc()",
        overlaps="booking",  # Silence SQLAlchemy warning
    )

    @validates("total_cost")
    def validate_total_cost(self, key, value):
        """Validate total cost is positive."""
        if value is not None and value <= 0:
            raise ValueError("Total cost must be positive")
        return value

    @validates("scheduled_start_date", "scheduled_completion_date")
    def validate_schedule(self, key, value):
        """Validate schedule consistency."""
        if key == "scheduled_completion_date" and hasattr(self, "scheduled_start_date"):
            # Only validate if both dates are set and start date is not None
            if (
                self.scheduled_start_date
                and value
                and value <= self.scheduled_start_date
            ):
                raise ValueError("Completion date must be after start date")
        return value

    def start_work(self):
        """Mark booking as in progress."""
        if self.status != BookingStatus.CONFIRMED:
            raise ValueError("Only confirmed bookings can be started")

        self.status = BookingStatus.IN_PROGRESS
        self.actual_start_date = datetime.now(timezone.utc)

    def complete_work(self):
        """Mark booking as completed."""
        if self.status != BookingStatus.IN_PROGRESS:
            raise ValueError("Only in-progress bookings can be completed")

        self.status = BookingStatus.COMPLETED
        self.actual_completion_date = datetime.now(timezone.utc)

    def cancel_booking(self, reason: str):
        """Cancel the booking with a reason."""
        if self.status in [BookingStatus.COMPLETED, BookingStatus.CANCELLED]:
            raise ValueError("Cannot cancel completed or already cancelled booking")

        self.status = BookingStatus.CANCELLED
        self.cancellation_reason = reason
        self.cancelled_at = datetime.now(timezone.utc)

    def calculate_duration_hours(self) -> Optional[int]:
        """Calculate actual duration in hours if work is completed."""
        if self.actual_start_date and self.actual_completion_date:
            duration = self.actual_completion_date - self.actual_start_date
            return int(duration.total_seconds() / 3600)
        return None

    def get_milestone_summary(self) -> Dict[str, Any]:
        """Get summary of milestone progress with optimized calculation."""
        if not self.milestones:
            return {
                "total_milestones": 0,
                "completed": 0,
                "paid": 0,
                "completion_percentage": 0,
                "total_amount": 0.0,
                "paid_amount": 0.0,
            }

        total = len(self.milestones)
        completed = 0
        paid = 0
        total_amount = 0.0
        paid_amount = 0.0

        # Single pass through milestones for efficiency
        for milestone in self.milestones:
            total_amount += float(milestone.amount)
            if milestone.status == MilestoneStatus.COMPLETED:
                completed += 1
            elif milestone.status == MilestoneStatus.PAID:
                paid += 1
                paid_amount += float(milestone.amount)

        return {
            "total_milestones": total,
            "completed": completed,
            "paid": paid,
            "completion_percentage": (completed / total * 100) if total > 0 else 0,
            "payment_percentage": (paid_amount / total_amount * 100)
            if total_amount > 0
            else 0,
            "total_amount": total_amount,
            "paid_amount": paid_amount,
        }

    def to_dict(self) -> Dict[str, Any]:
        """Convert Booking to dictionary for API responses."""
        return {
            "id": self.id,
            "service_request_id": self.service_request_id,
            "quote_id": self.quote_id,
            "provider_id": self.provider_id,
            "client_id": self.client_id,
            "schedule": {
                "scheduled_start_date": self.scheduled_start_date.isoformat(),
                "scheduled_completion_date": self.scheduled_completion_date.isoformat(),
                "actual_start_date": self.actual_start_date.isoformat()
                if self.actual_start_date
                else None,
                "actual_completion_date": self.actual_completion_date.isoformat()
                if self.actual_completion_date
                else None,
                "duration_hours": self.calculate_duration_hours(),
            },
            "cost": {
                "total_cost": float(self.total_cost),
                "currency": self.currency,
                "payment_terms": self.payment_terms,
            },
            "status": self.status.value,
            "notes": self.notes,
            "cancellation_reason": self.cancellation_reason,
            "milestone_summary": self.get_milestone_summary(),
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "cancelled_at": self.cancelled_at.isoformat()
            if self.cancelled_at
            else None,
        }

    def __str__(self) -> str:
        """String representation of Booking."""
        return f"Booking(id={self.id}, status={self.status.value}, total_cost={self.total_cost})"

    def __repr__(self) -> str:
        """Developer representation of Booking."""
        return (
            f"Booking(id={self.id}, service_request_id={self.service_request_id}, "
            f"provider_id={self.provider_id}, status={self.status.value})"
        )


class BookingMilestone(Base):
    """
    BookingMilestone model representing payment milestones within a booking.

    This model tracks progress and payments for different phases of work.
    """

    __tablename__ = "booking_milestones"

    # Optimized composite indexes for milestone management
    __table_args__ = (
        # Core business logic indexes
        Index("idx_booking_sequence", "booking_id", "sequence_number"),
        Index("idx_booking_status_sequence", "booking_id", "status", "sequence_number"),
        Index("idx_status_due_date", "status", "due_date"),  # For overdue tracking
        # Performance optimization indexes
        Index(
            "idx_due_date_pending",
            "due_date",
            "status",
            postgresql_where="status = 'PENDING'",
        ),  # For pending milestones
        Index(
            "idx_completed_date", "completed_date", "status"
        ),  # For completion tracking
        # Unique constraint for sequence within booking
        Index(
            "idx_unique_booking_sequence", "booking_id", "sequence_number", unique=True
        ),
    )

    # Primary key
    id = Column(Integer, primary_key=True, index=True)

    # Relationships
    booking_id = Column(
        Integer,
        ForeignKey("bookings.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Milestone details
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    sequence_number = Column(Integer, nullable=False)  # Order within the booking

    # Aliases for backward compatibility with tests
    @property
    def sequence_order(self):
        """Alias for sequence_number for test compatibility."""
        return self.sequence_number

    @sequence_order.setter
    def sequence_order(self, value):
        """Setter for sequence_order alias."""
        self.sequence_number = value

    @property
    def completed_at(self):
        """Alias for completed_date for test compatibility."""
        return self.completed_date

    @completed_at.setter
    def completed_at(self, value):
        """Setter for completed_at alias."""
        self.completed_date = value

    # Payment information
    amount = Column(Numeric(10, 2), nullable=False)
    currency = Column(String(3), nullable=False, default="USD")

    # Status and dates
    status = Column(
        SQLEnum(MilestoneStatus), nullable=False, default=MilestoneStatus.PENDING
    )
    due_date = Column(DateTime, nullable=True)
    completed_date = Column(DateTime, nullable=True)
    paid_date = Column(DateTime, nullable=True)

    # Additional information
    notes = Column(Text, nullable=True)
    completion_evidence = Column(JSON, nullable=True)  # Photos, documents, etc.

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    booking = relationship("Booking", back_populates="milestones")

    @validates("amount")
    def validate_amount(self, key, value):
        """Validate amount is positive."""
        if value is not None and value <= 0:
            raise ValueError("Milestone amount must be positive")
        return value

    @validates("sequence_number")
    def validate_sequence_number(self, key, value):
        """Validate sequence number is positive."""
        if value is not None and value <= 0:
            raise ValueError("Sequence number must be positive")
        return value

    def mark_completed(self, evidence: Optional[Dict[str, Any]] = None):
        """Mark milestone as completed."""
        if self.status != MilestoneStatus.PENDING:
            raise ValueError("Only pending milestones can be marked as completed")

        self.status = MilestoneStatus.COMPLETED
        self.completed_date = datetime.now(timezone.utc)

        if evidence:
            self.completion_evidence = evidence

    def mark_paid(self):
        """Mark milestone as paid."""
        if self.status != MilestoneStatus.COMPLETED:
            raise ValueError("Only completed milestones can be marked as paid")

        self.status = MilestoneStatus.PAID
        self.paid_date = datetime.now(timezone.utc)

    def is_overdue(self) -> bool:
        """Check if milestone is overdue."""
        if not self.due_date or self.status in [
            MilestoneStatus.COMPLETED,
            MilestoneStatus.PAID,
        ]:
            return False

        return datetime.now(timezone.utc) > self.due_date

    def to_dict(self) -> Dict[str, Any]:
        """Convert BookingMilestone to dictionary for API responses."""
        return {
            "id": self.id,
            "booking_id": self.booking_id,
            "title": self.title,
            "description": self.description,
            "sequence_number": self.sequence_number,
            "amount": float(self.amount),
            "currency": self.currency,
            "status": self.status.value,
            "due_date": self.due_date.isoformat() if self.due_date else None,
            "completed_date": self.completed_date.isoformat()
            if self.completed_date
            else None,
            "paid_date": self.paid_date.isoformat() if self.paid_date else None,
            "is_overdue": self.is_overdue(),
            "notes": self.notes,
            "completion_evidence": self.completion_evidence,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    def __str__(self) -> str:
        """String representation of BookingMilestone."""
        return f"BookingMilestone(id={self.id}, title='{self.title}', status={self.status.value})"

    def __repr__(self) -> str:
        """Developer representation of BookingMilestone."""
        return (
            f"BookingMilestone(id={self.id}, booking_id={self.booking_id}, "
            f"sequence_number={self.sequence_number}, amount={self.amount})"
        )
