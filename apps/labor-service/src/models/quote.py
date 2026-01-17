"""
Quote Model - Labor Services Marketplace

This module implements the Quote model following TDD principles.
The model represents proposals from service providers for service requests.
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from enum import Enum
from typing import Dict, Any, Optional
from sqlalchemy import (
    Column, Integer, String, Text, DateTime, Numeric, 
    ForeignKey, JSON, Boolean, Enum as SQLEnum, Index
)
from sqlalchemy.orm import relationship, validates
from .base import Base


class QuoteStatus(str, Enum):
    """Enumeration for quote status workflow."""
    DRAFT = "DRAFT"
    SUBMITTED = "SUBMITTED"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"
    WITHDRAWN = "WITHDRAWN"


class Quote(Base):
    """
    Quote model representing proposals from service providers.
    
    This model follows TDD principles and implements the behavior
    defined in the failing tests.
    """
    __tablename__ = "quotes"
    
    # Optimized composite indexes for high-performance queries
    __table_args__ = (
        # Core business logic indexes
        Index('idx_request_provider', 'request_id', 'provider_id'),
        Index('idx_provider_status_created', 'provider_id', 'status', 'created_at'),
        Index('idx_request_status_cost', 'request_id', 'status', 'total_cost'),
        
        # Performance optimization indexes
        Index('idx_status_expiration', 'status', 'valid_until'),  # For expiration cleanup
        Index('idx_cost_range_status', 'total_cost', 'status'),  # For cost-based filtering
        Index('idx_submitted_date', 'submitted_at', 'status'),  # For submission tracking
        
        # Unique constraint to prevent duplicate quotes
        Index('idx_unique_active_quote', 'request_id', 'provider_id', 'status', unique=True,
              postgresql_where="status IN ('DRAFT', 'SUBMITTED')"),
    )

    # Primary key
    id = Column(Integer, primary_key=True, index=True)
    
    # Relationships
    request_id = Column(
        Integer, 
        ForeignKey("service_requests.id", ondelete="CASCADE"), 
        nullable=False,
        index=True
    )
    provider_id = Column(Integer, nullable=False, index=True)  # References ServiceProvider
    parent_quote_id = Column(Integer, ForeignKey("quotes.id"), nullable=True, index=True)  # For counter-proposals
    
    # Cost breakdown
    labor_cost = Column(Numeric(10, 2), nullable=False)
    material_cost = Column(Numeric(10, 2), nullable=False, default=0)
    travel_cost = Column(Numeric(10, 2), nullable=False, default=0)
    total_cost = Column(Numeric(10, 2), nullable=False)
    currency = Column(String(3), nullable=False, default="USD")
    
    # Timeline
    start_availability = Column(DateTime, nullable=False)
    completion_estimate = Column(DateTime, nullable=False)
    estimated_hours = Column(Integer, nullable=False)
    
    # Quote details
    description = Column(Text, nullable=False)
    terms_and_conditions = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
    
    # Status and expiration
    status = Column(SQLEnum(QuoteStatus), nullable=False, default=QuoteStatus.DRAFT)
    valid_until = Column(DateTime, nullable=False)
    
    # Additional structured data
    cost_breakdown_details = Column(JSON, nullable=True)  # Detailed cost breakdown
    
    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    submitted_at = Column(DateTime, nullable=True)
    
    # Relationships
    service_request = relationship(
        "ServiceRequest",
        overlaps="quotes"  # Silence SQLAlchemy warning
    )
    
    def __init__(self, **kwargs):
        """Initialize Quote with automatic total cost calculation."""
        super().__init__(**kwargs)
        
        # Set default expiration if not provided (7 days from creation)
        if not self.valid_until:
            self.valid_until = datetime.now(timezone.utc) + timedelta(days=7)
        
        # Calculate total cost if components are provided but total_cost wasn't explicitly set
        if (hasattr(self, 'labor_cost') and hasattr(self, 'material_cost') and hasattr(self, 'travel_cost') 
            and ('total_cost' not in kwargs or kwargs.get('total_cost') is None)):
            self._calculate_total_cost()
    
    def _calculate_total_cost(self):
        """Calculate total cost from components."""
        labor = self.labor_cost or Decimal('0')
        material = self.material_cost or Decimal('0')
        travel = self.travel_cost or Decimal('0')
        self.total_cost = labor + material + travel
    
    @validates('labor_cost', 'material_cost', 'travel_cost', 'total_cost')
    def validate_costs(self, key, value):
        """Validate cost values are non-negative and reasonable."""
        if value is not None:
            if value < 0:
                raise ValueError(f"{key} must be non-negative")
            if value > 1000000:  # $1M limit for sanity
                raise ValueError(f"{key} cannot exceed $1,000,000")
        return value
    
    @validates('estimated_hours')
    def validate_duration(self, key, value):
        """Validate duration is positive."""
        if value is not None and value <= 0:
            raise ValueError("Duration must be positive")
        return value
    
    @validates('start_availability', 'completion_estimate')
    def validate_timeline(self, key, value):
        """Validate timeline consistency."""
        if key == 'completion_estimate' and hasattr(self, 'start_availability'):
            if self.start_availability and value <= self.start_availability:
                raise ValueError("Completion date must be after start date")
        return value
    
    def calculate_total_cost(self) -> Decimal:
        """Calculate and return total cost from components."""
        self._calculate_total_cost()
        return self.total_cost
    
    def is_expired(self) -> bool:
        """Check if quote has expired."""
        now = datetime.now(timezone.utc)
        # Handle both timezone-aware and timezone-naive valid_until
        if self.valid_until.tzinfo is None:
            # If valid_until is naive, assume it's UTC
            valid_until_utc = self.valid_until.replace(tzinfo=timezone.utc)
        else:
            valid_until_utc = self.valid_until
        return now > valid_until_utc
    
    def get_cost_breakdown(self) -> Dict[str, Any]:
        """Get detailed cost breakdown."""
        return {
            "labor_cost": float(self.labor_cost),
            "material_cost": float(self.material_cost),
            "travel_cost": float(self.travel_cost),
            "total_cost": float(self.total_cost),
            "currency": self.currency,
            "breakdown_details": self.cost_breakdown_details,
        }
    
    def submit_quote(self):
        """Submit the quote (change status from DRAFT to SUBMITTED)."""
        if self.status != QuoteStatus.DRAFT:
            raise ValueError("Only draft quotes can be submitted")
        
        self.status = QuoteStatus.SUBMITTED
        self.submitted_at = datetime.now(timezone.utc)
    
    def accept_quote(self):
        """Accept the quote."""
        if self.status != QuoteStatus.SUBMITTED:
            raise ValueError("Only submitted quotes can be accepted")
        
        if self.is_expired():
            raise ValueError("Cannot accept expired quote")
        
        self.status = QuoteStatus.ACCEPTED
    
    def reject_quote(self):
        """Reject the quote."""
        if self.status != QuoteStatus.SUBMITTED:
            raise ValueError("Only submitted quotes can be rejected")
        
        self.status = QuoteStatus.REJECTED
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert Quote to dictionary for API responses."""
        return {
            "id": self.id,
            "request_id": self.request_id,
            "provider_id": self.provider_id,
            "labor_cost": self.labor_cost,
            "material_cost": self.material_cost,
            "travel_cost": self.travel_cost,
            "total_cost": self.total_cost,
            "currency": self.currency,
            "cost_breakdown": self.get_cost_breakdown(),
            "timeline": {
                "start_availability": self.start_availability.isoformat(),
                "completion_estimate": self.completion_estimate.isoformat(),
                "estimated_hours": self.estimated_hours,
            },
            "description": self.description,
            "terms_and_conditions": self.terms_and_conditions,
            "notes": self.notes,
            "status": self.status.value,
            "valid_until": self.valid_until.isoformat(),
            "is_expired": self.is_expired(),
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "submitted_at": self.submitted_at.isoformat() if self.submitted_at else None,
        }
    
    def __str__(self) -> str:
        """String representation of Quote."""
        return f"Quote(id={self.id}, total_cost={self.total_cost}, status={self.status.value})"
    
    def __repr__(self) -> str:
        """Developer representation of Quote."""
        return (
            f"Quote(id={self.id}, request_id={self.request_id}, "
            f"provider_id={self.provider_id}, total_cost={self.total_cost})"
        )
    
    # Utility methods for better code organization
    def is_submittable(self) -> bool:
        """Check if quote can be submitted."""
        return self.status == QuoteStatus.DRAFT and not self.is_expired()
    
    def is_actionable(self) -> bool:
        """Check if quote can be accepted or rejected."""
        return self.status == QuoteStatus.SUBMITTED and not self.is_expired()
    
    def get_cost_summary(self) -> str:
        """Get a formatted cost summary string."""
        return f"${self.total_cost:.2f} (Labor: ${self.labor_cost:.2f}, Materials: ${self.material_cost:.2f}, Travel: ${self.travel_cost:.2f})"
    
    def days_until_expiration(self) -> int:
        """Get number of days until quote expires."""
        if self.is_expired():
            return 0
        delta = self.valid_until - datetime.now(timezone.utc)
        return max(0, delta.days)