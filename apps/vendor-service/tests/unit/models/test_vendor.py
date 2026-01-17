"""Tests for Vendor model."""

from datetime import datetime, timezone
from decimal import Decimal

import pytest
from src.models.vendor import Vendor


class TestVendorModel:
    """Test Vendor model functionality."""

    def test_create_vendor(self):
        """Test creating a vendor with valid data."""
        vendor = Vendor(
            user_id=1,
            company_name="Test Vendor Co",
            email="vendor@example.com",
            phone="+1234567890",
            address="123 Test St",
        )

        assert vendor.user_id == 1
        assert vendor.company_name == "Test Vendor Co"
        assert vendor.email == "vendor@example.com"
        assert vendor.phone == "+1234567890"
        assert vendor.address == "123 Test St"
        assert vendor.verification_status == "pending"
        assert vendor.rating == Decimal("0.0")
        assert isinstance(vendor.created_at, datetime)
        assert isinstance(vendor.updated_at, datetime)

    def test_vendor_email_validation(self):
        """Test email validation."""
        with pytest.raises(ValueError, match="Invalid email format"):
            Vendor(user_id=1, company_name="Test Vendor", email="invalid-email")

    def test_vendor_company_name_validation(self):
        """Test company name validation."""
        with pytest.raises(
            ValueError, match="Company name must be at least 2 characters"
        ):
            Vendor(user_id=1, company_name="A", email="vendor@example.com")

        with pytest.raises(
            ValueError, match="Company name cannot exceed 255 characters"
        ):
            Vendor(user_id=1, company_name="A" * 256, email="vendor@example.com")

    def test_vendor_verification_status_validation(self):
        """Test verification status validation."""
        with pytest.raises(ValueError, match="Invalid verification status"):
            Vendor(
                user_id=1,
                company_name="Test Vendor",
                email="vendor@example.com",
                verification_status="invalid_status",
            )

    def test_vendor_rating_validation(self):
        """Test rating validation."""
        vendor = Vendor(
            user_id=1, company_name="Test Vendor", email="vendor@example.com"
        )

        with pytest.raises(ValueError, match="Rating must be between 0.0 and 5.0"):
            vendor.rating = Decimal("6.0")

        with pytest.raises(ValueError, match="Rating must be between 0.0 and 5.0"):
            vendor.rating = Decimal("-1.0")

    def test_vendor_verify(self):
        """Test vendor verification."""
        vendor = Vendor(
            user_id=1, company_name="Test Vendor", email="vendor@example.com"
        )

        assert vendor.verification_status == "pending"
        assert not vendor.is_verified()

        vendor.verify()

        assert vendor.verification_status == "verified"
        assert vendor.is_verified()

    def test_vendor_suspend(self):
        """Test vendor suspension."""
        vendor = Vendor(
            user_id=1,
            company_name="Test Vendor",
            email="vendor@example.com",
            verification_status="verified",
        )

        assert vendor.is_active()

        vendor.suspend()

        assert vendor.verification_status == "suspended"
        assert not vendor.is_active()

    def test_vendor_update_rating(self):
        """Test updating vendor rating."""
        vendor = Vendor(
            user_id=1, company_name="Test Vendor", email="vendor@example.com"
        )

        assert vendor.rating == Decimal("0.0")

        vendor.update_rating(Decimal("4.5"))

        assert vendor.rating == Decimal("4.5")

    def test_vendor_repr(self):
        """Test vendor string representation."""
        vendor = Vendor(
            user_id=1, company_name="Test Vendor", email="vendor@example.com"
        )

        repr_str = repr(vendor)
        assert "Test Vendor" in repr_str
        assert "pending" in repr_str


class TestVendorModelDatabase:
    """Test Vendor model with database."""

    def test_create_vendor_in_db(self, db_session):
        """Test creating and persisting a vendor."""
        vendor = Vendor(
            user_id=1, company_name="DB Test Vendor", email="dbvendor@example.com"
        )

        db_session.add(vendor)
        db_session.commit()

        assert vendor.id is not None

        # Retrieve from database
        retrieved = db_session.query(Vendor).filter_by(user_id=1).first()
        assert retrieved is not None
        assert retrieved.company_name == "DB Test Vendor"
        assert retrieved.email == "dbvendor@example.com"

    def test_vendor_unique_user_id(self, db_session):
        """Test that user_id must be unique."""
        vendor1 = Vendor(
            user_id=1, company_name="Vendor 1", email="vendor1@example.com"
        )
        db_session.add(vendor1)
        db_session.commit()

        vendor2 = Vendor(
            user_id=1, company_name="Vendor 2", email="vendor2@example.com"
        )
        db_session.add(vendor2)

        with pytest.raises(Exception):  # SQLAlchemy will raise IntegrityError
            db_session.commit()
