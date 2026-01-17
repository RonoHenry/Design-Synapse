"""Tests for VendorRepository using TDD approach."""

from decimal import Decimal

import pytest
from sqlalchemy.exc import IntegrityError
from src.models.vendor import Vendor
from src.repositories.vendor_repository import VendorRepository
from tests.factories import VendorFactory


class TestVendorRepository:
    """Test cases for VendorRepository CRUD operations."""

    def test_create_vendor(self, db_session):
        """Test creating a new vendor."""
        repo = VendorRepository(db_session)
        vendor_data = {
            "user_id": 1,
            "company_name": "Test Company",
            "email": "test@company.com",
            "phone": "+1234567890",
            "address": "123 Test St",
        }

        vendor = repo.create(**vendor_data)

        assert vendor.id is not None
        assert vendor.user_id == 1
        assert vendor.company_name == "Test Company"
        assert vendor.email == "test@company.com"
        assert vendor.phone == "+1234567890"
        assert vendor.address == "123 Test St"
        assert vendor.verification_status == "pending"
        assert vendor.rating == Decimal("0.0")
        assert vendor.created_at is not None
        assert vendor.updated_at is not None

    def test_create_vendor_duplicate_user_id_raises_error(self, db_session):
        """Test that creating vendor with duplicate user_id raises error."""
        repo = VendorRepository(db_session)

        # Create first vendor
        repo.create(user_id=1, company_name="Company 1", email="test1@company.com")

        # Try to create second vendor with same user_id
        with pytest.raises(IntegrityError):
            repo.create(user_id=1, company_name="Company 2", email="test2@company.com")

    def test_get_by_id_existing_vendor(self, db_session):
        """Test retrieving vendor by ID when vendor exists."""
        repo = VendorRepository(db_session)
        vendor = VendorFactory(user_id=1, company_name="Test Company")
        db_session.add(vendor)
        db_session.commit()

        result = repo.get_by_id(vendor.id)

        assert result is not None
        assert result.id == vendor.id
        assert result.company_name == "Test Company"

    def test_get_by_id_nonexistent_vendor(self, db_session):
        """Test retrieving vendor by ID when vendor doesn't exist."""
        repo = VendorRepository(db_session)

        result = repo.get_by_id(999)

        assert result is None

    def test_get_by_user_id_existing_vendor(self, db_session):
        """Test retrieving vendor by user_id when vendor exists."""
        repo = VendorRepository(db_session)
        vendor = VendorFactory(user_id=123, company_name="User Company")
        db_session.add(vendor)
        db_session.commit()

        result = repo.get_by_user_id(123)

        assert result is not None
        assert result.user_id == 123
        assert result.company_name == "User Company"

    def test_get_by_user_id_nonexistent_vendor(self, db_session):
        """Test retrieving vendor by user_id when vendor doesn't exist."""
        repo = VendorRepository(db_session)

        result = repo.get_by_user_id(999)

        assert result is None

    def test_update_vendor(self, db_session):
        """Test updating vendor information."""
        repo = VendorRepository(db_session)
        vendor = VendorFactory(
            user_id=1, company_name="Original Company", email="original@company.com"
        )
        db_session.add(vendor)
        db_session.commit()

        updated_vendor = repo.update(
            vendor.id,
            company_name="Updated Company",
            email="updated@company.com",
            phone="+9876543210",
        )

        assert updated_vendor is not None
        assert updated_vendor.company_name == "Updated Company"
        assert updated_vendor.email == "updated@company.com"
        assert updated_vendor.phone == "+9876543210"
        assert updated_vendor.updated_at > updated_vendor.created_at

    def test_update_nonexistent_vendor(self, db_session):
        """Test updating vendor that doesn't exist."""
        repo = VendorRepository(db_session)

        result = repo.update(999, company_name="New Name")

        assert result is None

    def test_delete_vendor(self, db_session):
        """Test deleting vendor."""
        repo = VendorRepository(db_session)
        vendor = VendorFactory(user_id=1, company_name="To Delete")
        db_session.add(vendor)
        db_session.commit()
        vendor_id = vendor.id

        success = repo.delete(vendor_id)

        assert success is True
        assert repo.get_by_id(vendor_id) is None

    def test_delete_nonexistent_vendor(self, db_session):
        """Test deleting vendor that doesn't exist."""
        repo = VendorRepository(db_session)

        success = repo.delete(999)

        assert success is False

    def test_get_all_vendors(self, db_session):
        """Test retrieving all vendors."""
        repo = VendorRepository(db_session)
        vendors = [
            VendorFactory(user_id=1, company_name="Company 1"),
            VendorFactory(user_id=2, company_name="Company 2"),
            VendorFactory(user_id=3, company_name="Company 3"),
        ]
        for vendor in vendors:
            db_session.add(vendor)
        db_session.commit()

        result = repo.get_all()

        assert len(result) == 3
        company_names = [v.company_name for v in result]
        assert "Company 1" in company_names
        assert "Company 2" in company_names
        assert "Company 3" in company_names

    def test_get_all_vendors_with_limit(self, db_session):
        """Test retrieving vendors with limit."""
        repo = VendorRepository(db_session)
        vendors = [
            VendorFactory(user_id=i, company_name=f"Company {i}")
            for i in range(1, 6)  # Create 5 vendors
        ]
        for vendor in vendors:
            db_session.add(vendor)
        db_session.commit()

        result = repo.get_all(limit=3)

        assert len(result) == 3

    def test_get_all_vendors_with_offset(self, db_session):
        """Test retrieving vendors with offset."""
        repo = VendorRepository(db_session)
        vendors = [
            VendorFactory(user_id=i, company_name=f"Company {i}")
            for i in range(1, 6)  # Create 5 vendors
        ]
        for vendor in vendors:
            db_session.add(vendor)
        db_session.commit()

        result = repo.get_all(offset=2, limit=2)

        assert len(result) == 2

    def test_get_verified_vendors(self, db_session):
        """Test retrieving only verified vendors."""
        repo = VendorRepository(db_session)
        vendors = [
            VendorFactory(
                user_id=1, company_name="Pending Company", verification_status="pending"
            ),
            VendorFactory(
                user_id=2,
                company_name="Verified Company 1",
                verification_status="verified",
            ),
            VendorFactory(
                user_id=3,
                company_name="Verified Company 2",
                verification_status="verified",
            ),
            VendorFactory(
                user_id=4,
                company_name="Suspended Company",
                verification_status="suspended",
            ),
        ]
        for vendor in vendors:
            db_session.add(vendor)
        db_session.commit()

        result = repo.get_verified_vendors()

        assert len(result) == 2
        for vendor in result:
            assert vendor.verification_status == "verified"

    def test_get_vendors_by_status(self, db_session):
        """Test retrieving vendors by verification status."""
        repo = VendorRepository(db_session)
        vendors = [
            VendorFactory(
                user_id=1, company_name="Pending 1", verification_status="pending"
            ),
            VendorFactory(
                user_id=2, company_name="Pending 2", verification_status="pending"
            ),
            VendorFactory(
                user_id=3, company_name="Verified", verification_status="verified"
            ),
            VendorFactory(
                user_id=4, company_name="Suspended", verification_status="suspended"
            ),
        ]
        for vendor in vendors:
            db_session.add(vendor)
        db_session.commit()

        pending_vendors = repo.get_by_status("pending")
        verified_vendors = repo.get_by_status("verified")
        suspended_vendors = repo.get_by_status("suspended")

        assert len(pending_vendors) == 2
        assert len(verified_vendors) == 1
        assert len(suspended_vendors) == 1

        for vendor in pending_vendors:
            assert vendor.verification_status == "pending"

    def test_search_vendors_by_company_name(self, db_session):
        """Test searching vendors by company name."""
        repo = VendorRepository(db_session)
        vendors = [
            VendorFactory(user_id=1, company_name="Tech Solutions Inc"),
            VendorFactory(user_id=2, company_name="Tech Innovations LLC"),
            VendorFactory(user_id=3, company_name="Building Materials Co"),
            VendorFactory(user_id=4, company_name="Advanced Tech Systems"),
        ]
        for vendor in vendors:
            db_session.add(vendor)
        db_session.commit()

        result = repo.search_by_name("Tech")

        assert len(result) == 3
        for vendor in result:
            assert "Tech" in vendor.company_name

    def test_count_vendors(self, db_session):
        """Test counting total vendors."""
        repo = VendorRepository(db_session)
        vendors = [
            VendorFactory(user_id=i, company_name=f"Company {i}") for i in range(1, 4)
        ]
        for vendor in vendors:
            db_session.add(vendor)
        db_session.commit()

        count = repo.count()

        assert count == 3

    def test_count_vendors_by_status(self, db_session):
        """Test counting vendors by status."""
        repo = VendorRepository(db_session)
        vendors = [
            VendorFactory(user_id=1, verification_status="pending"),
            VendorFactory(user_id=2, verification_status="pending"),
            VendorFactory(user_id=3, verification_status="verified"),
            VendorFactory(user_id=4, verification_status="suspended"),
        ]
        for vendor in vendors:
            db_session.add(vendor)
        db_session.commit()

        pending_count = repo.count_by_status("pending")
        verified_count = repo.count_by_status("verified")
        suspended_count = repo.count_by_status("suspended")

        assert pending_count == 2
        assert verified_count == 1
        assert suspended_count == 1

    def test_exists_by_user_id(self, db_session):
        """Test checking if vendor exists by user_id."""
        repo = VendorRepository(db_session)
        vendor = VendorFactory(user_id=123)
        db_session.add(vendor)
        db_session.commit()

        assert repo.exists_by_user_id(123) is True
        assert repo.exists_by_user_id(999) is False

    def test_exists_by_email(self, db_session):
        """Test checking if vendor exists by email."""
        repo = VendorRepository(db_session)
        vendor = VendorFactory(email="test@company.com")
        db_session.add(vendor)
        db_session.commit()

        assert repo.exists_by_email("test@company.com") is True
        assert repo.exists_by_email("nonexistent@company.com") is False
