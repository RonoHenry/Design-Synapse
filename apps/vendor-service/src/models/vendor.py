"""Vendor model for vendor management."""

import re
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

from sqlalchemy import DateTime, Integer, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates
from src.infrastructure.database import Base


class Vendor(Base):
    """Vendor model representing suppliers on the platform."""

    __tablename__ = "vendors"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        Integer, nullable=False, unique=True, index=True
    )
    company_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    phone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    address: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    verification_status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="pending",
        server_default="pending",
        index=True,
    )
    rating: Mapped[Decimal] = mapped_column(
        Numeric(3, 2), nullable=False, default=Decimal("0.0"), server_default="0.0"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    products: Mapped[list["Product"]] = relationship(
        "Product", back_populates="vendor", cascade="all, delete-orphan"
    )

    def __init__(
        self,
        user_id: int,
        company_name: str,
        email: str,
        phone: Optional[str] = None,
        address: Optional[str] = None,
        verification_status: str = "pending",
        **kwargs,
    ):
        """Initialize a new vendor."""
        self.user_id = user_id
        self.company_name = self._validate_company_name(company_name)
        self.email = self._validate_email(email)
        self.phone = phone
        self.address = address
        self.verification_status = self._validate_verification_status(
            verification_status
        )
        self.rating = Decimal("0.0")
        self.created_at = datetime.now(timezone.utc)
        self.updated_at = self.created_at

    @staticmethod
    def _validate_email(email: str) -> str:
        """Validate email format."""
        pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        email_pattern = re.compile(pattern)
        if not email_pattern.match(email):
            raise ValueError("Invalid email format")
        return email.lower()

    @staticmethod
    def _validate_company_name(company_name: str) -> str:
        """Validate company name."""
        if not company_name or len(company_name.strip()) < 2:
            raise ValueError("Company name must be at least 2 characters long")
        if len(company_name) > 255:
            raise ValueError("Company name cannot exceed 255 characters")
        return company_name.strip()

    @staticmethod
    def _validate_verification_status(status: str) -> str:
        """Validate verification status."""
        allowed_statuses = ["pending", "verified", "suspended", "inactive"]
        if status not in allowed_statuses:
            raise ValueError(
                f"Invalid verification status. Must be one of: {allowed_statuses}"
            )
        return status

    @validates("verification_status")
    def validate_verification_status_update(self, key: str, value: str) -> str:
        """Validate verification status on update."""
        return self._validate_verification_status(value)

    @validates("rating")
    def validate_rating(self, key: str, value: Decimal) -> Decimal:
        """Validate rating value."""
        if value < Decimal("0.0") or value > Decimal("5.0"):
            raise ValueError("Rating must be between 0.0 and 5.0")
        return value

    def update_rating(self, new_rating: Decimal) -> None:
        """Update vendor rating."""
        self.rating = new_rating
        self.updated_at = datetime.now(timezone.utc)

    def verify(self) -> None:
        """Mark vendor as verified."""
        self.verification_status = "verified"
        self.updated_at = datetime.now(timezone.utc)

    def suspend(self) -> None:
        """Suspend vendor account."""
        self.verification_status = "suspended"
        self.updated_at = datetime.now(timezone.utc)

    def is_verified(self) -> bool:
        """Check if vendor is verified."""
        return self.verification_status == "verified"

    def is_active(self) -> bool:
        """Check if vendor is active (verified and not suspended)."""
        return self.verification_status == "verified"

    def __repr__(self) -> str:
        """String representation of vendor."""
        return f"<Vendor(id={self.id}, company_name='{self.company_name}', status='{self.verification_status}')>"
