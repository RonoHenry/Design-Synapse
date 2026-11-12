"""Async repository for vendor data access."""

from decimal import Decimal
from typing import List, Optional

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from src.models.vendor import Vendor


class VendorRepository:
    """Async repository for vendor CRUD operations."""

    def __init__(self, db: AsyncSession):
        """Initialize repository with database session."""
        self.db = db

    async def create(self, vendor: Vendor) -> Vendor:
        """Create a new vendor."""
        self.db.add(vendor)
        await self.db.commit()
        await self.db.refresh(vendor)
        return vendor

    async def get_by_id(self, vendor_id: int) -> Optional[Vendor]:
        """Get vendor by ID."""
        result = await self.db.execute(select(Vendor).filter(Vendor.id == vendor_id))
        return result.scalar_one_or_none()

    async def get_by_user_id(self, user_id: int) -> Optional[Vendor]:
        """Get vendor by user ID."""
        result = await self.db.execute(select(Vendor).filter(Vendor.user_id == user_id))
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> Optional[Vendor]:
        """Get vendor by email."""
        result = await self.db.execute(
            select(Vendor).filter(Vendor.email == email.lower())
        )
        return result.scalar_one_or_none()

    async def get_all(
        self,
        skip: int = 0,
        limit: int = 100,
        verification_status: Optional[str] = None,
    ) -> List[Vendor]:
        """Get all vendors with pagination and optional filtering."""
        stmt = select(Vendor)

        if verification_status:
            stmt = stmt.filter(Vendor.verification_status == verification_status)

        stmt = stmt.offset(skip).limit(limit)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def search_by_name(
        self, name: str, skip: int = 0, limit: int = 100
    ) -> List[Vendor]:
        """Search vendors by company name."""
        search_pattern = f"%{name}%"
        stmt = (
            select(Vendor)
            .filter(Vendor.company_name.ilike(search_pattern))
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def update(self, vendor: Vendor) -> Vendor:
        """Update vendor."""
        await self.db.commit()
        await self.db.refresh(vendor)
        return vendor

    async def delete(self, vendor_id: int) -> bool:
        """Delete vendor by ID."""
        vendor = await self.get_by_id(vendor_id)
        if vendor:
            await self.db.delete(vendor)
            await self.db.commit()
            return True
        return False
