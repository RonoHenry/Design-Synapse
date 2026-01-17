"""Tests for ProductBookmark model."""

from datetime import datetime
from decimal import Decimal

import pytest
from src.models.bookmark import ProductBookmark
from src.models.product import Product
from src.models.vendor import Vendor


class TestProductBookmarkModel:
    """Test ProductBookmark model functionality."""

    def test_create_bookmark(self):
        """Test creating a bookmark with valid data."""
        bookmark = ProductBookmark(
            user_id=1, product_id=10, notes="Want to use this in my living room design"
        )

        assert bookmark.user_id == 1
        assert bookmark.product_id == 10
        assert bookmark.notes == "Want to use this in my living room design"
        assert isinstance(bookmark.created_at, datetime)

    def test_bookmark_without_notes(self):
        """Test creating a bookmark without notes."""
        bookmark = ProductBookmark(user_id=1, product_id=10)

        assert bookmark.notes is None

    def test_bookmark_notes_validation(self):
        """Test bookmark notes validation."""
        # Notes too long
        long_notes = "A" * 1001
        with pytest.raises(ValueError, match="Notes cannot exceed 1000 characters"):
            ProductBookmark(user_id=1, product_id=10, notes=long_notes)

    def test_bookmark_notes_whitespace_trimming(self):
        """Test that bookmark notes are trimmed."""
        bookmark = ProductBookmark(
            user_id=1, product_id=10, notes="  Great for kitchen  "
        )

        assert bookmark.notes == "Great for kitchen"

    def test_bookmark_update_notes(self):
        """Test updating bookmark notes."""
        bookmark = ProductBookmark(user_id=1, product_id=10, notes="Original notes")

        bookmark.update_notes("Updated notes")
        assert bookmark.notes == "Updated notes"

        # Clear notes
        bookmark.update_notes(None)
        assert bookmark.notes is None

    def test_bookmark_repr(self):
        """Test bookmark string representation."""
        bookmark = ProductBookmark(user_id=1, product_id=10)

        repr_str = repr(bookmark)
        assert "user_id=1" in repr_str
        assert "product_id=10" in repr_str


class TestProductBookmarkDatabase:
    """Test ProductBookmark model with database."""

    def test_create_bookmark_in_db(self, db_session):
        """Test creating and persisting a bookmark."""
        # Create vendor and product first
        vendor = Vendor(
            user_id=1, company_name="Test Vendor", email="vendor@example.com"
        )
        db_session.add(vendor)
        db_session.commit()

        product = Product(
            vendor_id=vendor.id,
            name="Test Product",
            category="furniture",
            price=Decimal("299.99"),
        )
        db_session.add(product)
        db_session.commit()

        # Create bookmark
        bookmark = ProductBookmark(
            user_id=2, product_id=product.id, notes="Perfect for my project"
        )
        db_session.add(bookmark)
        db_session.commit()

        assert bookmark.id is not None

        # Retrieve from database
        retrieved = db_session.query(ProductBookmark).filter_by(user_id=2).first()
        assert retrieved is not None
        assert retrieved.product_id == product.id
        assert retrieved.notes == "Perfect for my project"

    def test_bookmark_unique_constraint(self, db_session):
        """Test that user cannot bookmark same product twice."""
        vendor = Vendor(
            user_id=1, company_name="Test Vendor", email="vendor@example.com"
        )
        db_session.add(vendor)
        db_session.commit()

        product = Product(
            vendor_id=vendor.id,
            name="Test Product",
            category="furniture",
            price=Decimal("299.99"),
        )
        db_session.add(product)
        db_session.commit()

        # Create first bookmark
        bookmark1 = ProductBookmark(user_id=2, product_id=product.id)
        db_session.add(bookmark1)
        db_session.commit()

        # Try to create duplicate bookmark
        bookmark2 = ProductBookmark(user_id=2, product_id=product.id)
        db_session.add(bookmark2)

        with pytest.raises(Exception):  # IntegrityError
            db_session.commit()

        db_session.rollback()

    def test_bookmark_cascade_delete_with_product(self, db_session):
        """Test that bookmarks are deleted when product is deleted."""
        vendor = Vendor(
            user_id=1, company_name="Test Vendor", email="vendor@example.com"
        )
        db_session.add(vendor)
        db_session.commit()

        product = Product(
            vendor_id=vendor.id,
            name="Test Product",
            category="furniture",
            price=Decimal("299.99"),
        )
        db_session.add(product)
        db_session.commit()

        bookmark = ProductBookmark(user_id=2, product_id=product.id)
        db_session.add(bookmark)
        db_session.commit()

        bookmark_id = bookmark.id

        # Delete product
        db_session.delete(product)
        db_session.commit()

        # Bookmark should be deleted
        deleted_bookmark = (
            db_session.query(ProductBookmark).filter_by(id=bookmark_id).first()
        )
        assert deleted_bookmark is None

    def test_user_multiple_bookmarks(self, db_session):
        """Test user can bookmark multiple products."""
        vendor = Vendor(
            user_id=1, company_name="Test Vendor", email="vendor@example.com"
        )
        db_session.add(vendor)
        db_session.commit()

        product1 = Product(
            vendor_id=vendor.id,
            name="Product 1",
            category="furniture",
            price=Decimal("299.99"),
        )
        product2 = Product(
            vendor_id=vendor.id,
            name="Product 2",
            category="fixtures",
            price=Decimal("199.99"),
        )
        db_session.add_all([product1, product2])
        db_session.commit()

        # User bookmarks both products
        bookmark1 = ProductBookmark(
            user_id=2, product_id=product1.id, notes="For living room"
        )
        bookmark2 = ProductBookmark(
            user_id=2, product_id=product2.id, notes="For kitchen"
        )
        db_session.add_all([bookmark1, bookmark2])
        db_session.commit()

        # Query user's bookmarks
        user_bookmarks = db_session.query(ProductBookmark).filter_by(user_id=2).all()
        assert len(user_bookmarks) == 2

    def test_product_multiple_bookmarks(self, db_session):
        """Test product can be bookmarked by multiple users."""
        vendor = Vendor(
            user_id=1, company_name="Test Vendor", email="vendor@example.com"
        )
        db_session.add(vendor)
        db_session.commit()

        product = Product(
            vendor_id=vendor.id,
            name="Popular Product",
            category="furniture",
            price=Decimal("299.99"),
        )
        db_session.add(product)
        db_session.commit()

        # Multiple users bookmark same product
        bookmark1 = ProductBookmark(user_id=2, product_id=product.id)
        bookmark2 = ProductBookmark(user_id=3, product_id=product.id)
        bookmark3 = ProductBookmark(user_id=4, product_id=product.id)
        db_session.add_all([bookmark1, bookmark2, bookmark3])
        db_session.commit()

        # Query product's bookmarks
        product_bookmarks = (
            db_session.query(ProductBookmark).filter_by(product_id=product.id).all()
        )
        assert len(product_bookmarks) == 3
