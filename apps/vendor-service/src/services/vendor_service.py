"""Vendor service for business logic."""

from decimal import Decimal
from typing import List, Optional

from src.models.vendor import Vendor
from src.repositories.vendor_repository import VendorRepository


class VendorService:
    """Service for vendor business logic."""

    def __init__(self, vendor_repository: VendorRepository):
        """Initialize vendor service."""
        self.vendor_repository = vendor_repository

    async def register_vendor(
        self,
        user_id: int,
        company_name: str,
        email: str,
        phone: Optional[str] = None,
        address: Optional[str] = None,
    ) -> Vendor:
        """Register a new vendor."""
        # Check if user already has a vendor profile
        existing_vendor = await self.vendor_repository.get_by_user_id(user_id)
        if existing_vendor:
            raise ValueError("User already has a vendor profile")

        # Create new vendor
        vendor = Vendor(
            user_id=user_id,
            company_name=company_name,
            email=email,
            phone=phone,
            address=address,
        )

        return await self.vendor_repository.create(vendor)

    async def get_vendor(self, vendor_id: int) -> Optional[Vendor]:
        """Get vendor by ID."""
        return await self.vendor_repository.get_by_id(vendor_id)

    async def get_vendor_by_user_id(self, user_id: int) -> Optional[Vendor]:
        """Get vendor by user ID."""
        return await self.vendor_repository.get_by_user_id(user_id)

    async def update_vendor_profile(
        self,
        vendor_id: int,
        company_name: Optional[str] = None,
        email: Optional[str] = None,
        phone: Optional[str] = None,
        address: Optional[str] = None,
    ) -> Optional[Vendor]:
        """Update vendor profile."""
        vendor = await self.vendor_repository.get_by_id(vendor_id)
        if not vendor:
            return None

        if company_name is not None:
            vendor.company_name = vendor._validate_company_name(company_name)
        if email is not None:
            vendor.email = vendor._validate_email(email)
        if phone is not None:
            vendor.phone = phone
        if address is not None:
            vendor.address = address

        return await self.vendor_repository.update(vendor)

    async def verify_vendor(self, vendor_id: int) -> Optional[Vendor]:
        """Verify a vendor."""
        vendor = await self.vendor_repository.get_by_id(vendor_id)
        if not vendor:
            return None

        vendor.verify()
        return await self.vendor_repository.update(vendor)

    async def suspend_vendor(self, vendor_id: int) -> Optional[Vendor]:
        """Suspend a vendor."""
        vendor = await self.vendor_repository.get_by_id(vendor_id)
        if not vendor:
            return None

        vendor.suspend()
        return await self.vendor_repository.update(vendor)

    async def update_vendor_rating(
        self, vendor_id: int, new_rating: Decimal
    ) -> Optional[Vendor]:
        """Update vendor rating."""
        vendor = await self.vendor_repository.get_by_id(vendor_id)
        if not vendor:
            return None

        vendor.update_rating(new_rating)
        return await self.vendor_repository.update(vendor)

    async def list_vendors(
        self,
        skip: int = 0,
        limit: int = 100,
        verification_status: Optional[str] = None,
    ) -> List[Vendor]:
        """List vendors with optional filtering."""
        return await self.vendor_repository.get_all(
            skip=skip,
            limit=limit,
            verification_status=verification_status,
        )

    async def delete_vendor(self, vendor_id: int) -> bool:
        """Delete a vendor."""
        vendor = await self.vendor_repository.get_by_id(vendor_id)
        if not vendor:
            return False

        await self.vendor_repository.delete(vendor_id)
        return True
