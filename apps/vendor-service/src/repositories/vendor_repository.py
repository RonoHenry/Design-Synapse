"""Repository for vendor data access operations."""

from datetime import datetime, timezone
from decimal import Decimal
from typing import List, Optional

from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from src.models.vendor import Vendor


class VendorRepository:
    """Repository for vendor CRUD operations and queries."""

    def __init__(self, db_session: Session):
        """Initialize repository with database session."""
        self.db = db_session

    def create(
        self,
        user_id: int,
        company_name: str,
        email: str,
        phone: Optional[str] = None,
        address: Optional[str] = None,
        verification_status: str = "pending",
    ) -> Vendor:
        """Create a new vendor."""
        vendor = Vendor(
            user_id=user_id,
            company_name=company_name,
            email=email,
            phone=phone,
            address=address,
            verification_status=verification_status,
        )

        self.db.add(vendor)
        self.db.commit()
        self.db.refresh(vendor)
        return vendor

    def get_by_id(self, vendor_id: int) -> Optional[Vendor]:
        """Get vendor by ID."""
        return self.db.query(Vendor).filter(Vendor.id == vendor_id).first()

    def get_by_user_id(self, user_id: int) -> Optional[Vendor]:
        """Get vendor by user ID."""
        return self.db.query(Vendor).filter(Vendor.user_id == user_id).first()

    def update(self, vendor_id: int, **kwargs) -> Optional[Vendor]:
        """Update vendor information."""
        vendor = self.get_by_id(vendor_id)
        if not vendor:
            return None

        # Update allowed fields
        allowed_fields = [
            "company_name",
            "email",
            "phone",
            "address",
            "verification_status",
            "rating",
        ]

        for field, value in kwargs.items():
            if field in allowed_fields and hasattr(vendor, field):
                setattr(vendor, field, value)

        vendor.updated_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(vendor)
        return vendor

    def delete(self, vendor_id: int) -> bool:
        """Delete vendor by ID."""
        vendor = self.get_by_id(vendor_id)
        if not vendor:
            return False

        self.db.delete(vendor)
        self.db.commit()
        return True

    def get_all(
        self, limit: Optional[int] = None, offset: Optional[int] = None
    ) -> List[Vendor]:
        """Get all vendors with optional pagination."""
        query = self.db.query(Vendor).order_by(Vendor.created_at.desc())

        if offset:
            query = query.offset(offset)
        if limit:
            query = query.limit(limit)

        return query.all()

    def get_verified_vendors(
        self, limit: Optional[int] = None, offset: Optional[int] = None
    ) -> List[Vendor]:
        """Get all verified vendors."""
        query = (
            self.db.query(Vendor)
            .filter(Vendor.verification_status == "verified")
            .order_by(Vendor.created_at.desc())
        )

        if offset:
            query = query.offset(offset)
        if limit:
            query = query.limit(limit)

        return query.all()

    def get_by_status(
        self, status: str, limit: Optional[int] = None, offset: Optional[int] = None
    ) -> List[Vendor]:
        """Get vendors by verification status."""
        query = (
            self.db.query(Vendor)
            .filter(Vendor.verification_status == status)
            .order_by(Vendor.created_at.desc())
        )

        if offset:
            query = query.offset(offset)
        if limit:
            query = query.limit(limit)

        return query.all()

    def search_by_name(
        self,
        search_term: str,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> List[Vendor]:
        """Search vendors by company name."""
        query = (
            self.db.query(Vendor)
            .filter(Vendor.company_name.ilike(f"%{search_term}%"))
            .order_by(Vendor.company_name)
        )

        if offset:
            query = query.offset(offset)
        if limit:
            query = query.limit(limit)

        return query.all()

    def count(self) -> int:
        """Count total number of vendors."""
        return self.db.query(Vendor).count()

    def count_by_status(self, status: str) -> int:
        """Count vendors by verification status."""
        return (
            self.db.query(Vendor).filter(Vendor.verification_status == status).count()
        )

    def exists_by_user_id(self, user_id: int) -> bool:
        """Check if vendor exists by user ID."""
        return (
            self.db.query(Vendor).filter(Vendor.user_id == user_id).first() is not None
        )

    def exists_by_email(self, email: str) -> bool:
        """Check if vendor exists by email."""
        return (
            self.db.query(Vendor).filter(Vendor.email == email.lower()).first()
            is not None
        )

    def get_top_rated_vendors(
        self, limit: int = 10, min_rating: Optional[Decimal] = None
    ) -> List[Vendor]:
        """Get top-rated vendors."""
        query = self.db.query(Vendor).filter(Vendor.verification_status == "verified")

        if min_rating:
            query = query.filter(Vendor.rating >= min_rating)

        return query.order_by(Vendor.rating.desc()).limit(limit).all()

    def get_recently_joined(self, limit: int = 10) -> List[Vendor]:
        """Get recently joined vendors."""
        return (
            self.db.query(Vendor)
            .filter(Vendor.verification_status == "verified")
            .order_by(Vendor.created_at.desc())
            .limit(limit)
            .all()
        )
