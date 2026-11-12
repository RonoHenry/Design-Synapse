"""Tests for BookmarkRepository."""

import pytest
from sqlalchemy.orm import Session
from src.models.bookmark import ProductBookmark
from src.models.product import Product
from src.models.vendor import Vendor
from src.repositories.bookmark_repository import BookmarkRepository
from tests.factories import (ProductBookmarkFactory, ProductFactory,
                             VendorFactory)


class TestBookmarkRepository:
    """Test cases for BookmarkRepository."""

    @pytest.fixture
    def repository(self, db_session: Session) -> BookmarkRepository:
        """Create repository instance."""
        return BookmarkRepository(db_session)

    @pytest.fixture
    def vendor(self, db_session: Session) -> Vendor:
        """Create a test vendor."""
        vendor = VendorFactory()
        db_session.add(vendor)
        db_session.commit()
        db_session.refresh(vendor)
        return vendor

    @pytest.fixture
    def product(self, db_session: Session, vendor: Vendor) -> Product:
        """Create a test product."""
        product = ProductFactory(vendor_id=vendor.id)
        db_session.add(product)
        db_session.commit()
        db_session.refresh(product)
        return product

    def test_create_bookmark(self, repository: BookmarkRepository, product: Product):
        """Test creating a new bookmark."""
        user_id = 1
        notes = "Great product for my design"

        bookmark = ProductBookmark(user_id=user_id, product_id=product.id, notes=notes)

        result = repository.create(bookmark)

        assert result.id is not None
        assert result.user_id == user_id
        assert result.product_id == product.id
        assert result.notes == notes
        assert result.created_at is not None

    def test_get_by_id(
        self, repository: BookmarkRepository, db_session: Session, product: Product
    ):
        """Test getting bookmark by ID."""
        bookmark = ProductBookmarkFactory(product_id=product.id)
        db_session.add(bookmark)
        db_session.commit()

        result = repository.get_by_id(bookmark.id)

        assert result is not None
        assert result.id == bookmark.id
        assert result.user_id == bookmark.user_id
        assert result.product_id == bookmark.product_id

    def test_get_by_id_not_found(self, repository: BookmarkRepository):
        """Test getting non-existent bookmark."""
        result = repository.get_by_id(999)
        assert result is None

    def test_get_by_user_id(
        self, repository: BookmarkRepository, db_session: Session, vendor: Vendor
    ):
        """Test getting bookmarks by user ID."""
        user_id = 1
        product1 = ProductFactory(vendor_id=vendor.id)
        product2 = ProductFactory(vendor_id=vendor.id)
        product3 = ProductFactory(vendor_id=vendor.id)
        db_session.add_all([product1, product2, product3])
        db_session.commit()

        bookmark1 = ProductBookmarkFactory(user_id=user_id, product_id=product1.id)
        bookmark2 = ProductBookmarkFactory(user_id=user_id, product_id=product2.id)
        bookmark3 = ProductBookmarkFactory(
            user_id=2, product_id=product3.id
        )  # Different user

        db_session.add_all([bookmark1, bookmark2, bookmark3])
        db_session.commit()

        result = repository.get_by_user_id(user_id)

        assert len(result) == 2
        assert all(b.user_id == user_id for b in result)

    def test_get_by_user_and_product(
        self, repository: BookmarkRepository, db_session: Session, product: Product
    ):
        """Test getting bookmark by user and product."""
        user_id = 1
        bookmark = ProductBookmarkFactory(user_id=user_id, product_id=product.id)
        db_session.add(bookmark)
        db_session.commit()

        result = repository.get_by_user_and_product(user_id, product.id)

        assert result is not None
        assert result.user_id == user_id
        assert result.product_id == product.id

    def test_get_by_user_and_product_not_found(
        self, repository: BookmarkRepository, product: Product
    ):
        """Test getting non-existent bookmark by user and product."""
        result = repository.get_by_user_and_product(999, product.id)
        assert result is None

    def test_exists_by_user_and_product(
        self, repository: BookmarkRepository, db_session: Session, product: Product
    ):
        """Test checking if bookmark exists."""
        user_id = 1
        bookmark = ProductBookmarkFactory(user_id=user_id, product_id=product.id)
        db_session.add(bookmark)
        db_session.commit()

        assert repository.exists_by_user_and_product(user_id, product.id) is True
        assert repository.exists_by_user_and_product(999, product.id) is False

    def test_update(
        self, repository: BookmarkRepository, db_session: Session, product: Product
    ):
        """Test updating bookmark."""
        bookmark = ProductBookmarkFactory(product_id=product.id, notes="Old notes")
        db_session.add(bookmark)
        db_session.commit()

        bookmark.notes = "Updated notes"
        result = repository.update(bookmark)

        assert result.notes == "Updated notes"

    def test_delete(
        self, repository: BookmarkRepository, db_session: Session, product: Product
    ):
        """Test deleting bookmark."""
        bookmark = ProductBookmarkFactory(product_id=product.id)
        db_session.add(bookmark)
        db_session.commit()
        bookmark_id = bookmark.id

        repository.delete(bookmark)

        # Verify deletion
        result = repository.get_by_id(bookmark_id)
        assert result is None

    def test_delete_by_id(
        self, repository: BookmarkRepository, db_session: Session, product: Product
    ):
        """Test deleting bookmark by ID."""
        bookmark = ProductBookmarkFactory(product_id=product.id)
        db_session.add(bookmark)
        db_session.commit()
        bookmark_id = bookmark.id

        success = repository.delete_by_id(bookmark_id)

        assert success is True
        result = repository.get_by_id(bookmark_id)
        assert result is None

    def test_delete_by_id_not_found(self, repository: BookmarkRepository):
        """Test deleting non-existent bookmark."""
        success = repository.delete_by_id(999)
        assert success is False

    def test_count_by_user(
        self, repository: BookmarkRepository, db_session: Session, vendor: Vendor
    ):
        """Test counting bookmarks by user."""
        user_id = 1
        product1 = ProductFactory(vendor_id=vendor.id)
        product2 = ProductFactory(vendor_id=vendor.id)
        product3 = ProductFactory(vendor_id=vendor.id)
        db_session.add_all([product1, product2, product3])
        db_session.commit()

        bookmark1 = ProductBookmarkFactory(user_id=user_id, product_id=product1.id)
        bookmark2 = ProductBookmarkFactory(user_id=user_id, product_id=product2.id)
        bookmark3 = ProductBookmarkFactory(
            user_id=2, product_id=product3.id
        )  # Different user

        db_session.add_all([bookmark1, bookmark2, bookmark3])
        db_session.commit()

        count = repository.count_by_user(user_id)
        assert count == 2

    def test_get_user_bookmarks_with_products(
        self, repository: BookmarkRepository, db_session: Session, vendor: Vendor
    ):
        """Test getting user bookmarks with product details."""
        user_id = 1
        product1 = ProductFactory(vendor_id=vendor.id, name="Product 1")
        product2 = ProductFactory(vendor_id=vendor.id, name="Product 2")
        db_session.add_all([product1, product2])
        db_session.commit()

        bookmark1 = ProductBookmarkFactory(user_id=user_id, product_id=product1.id)
        bookmark2 = ProductBookmarkFactory(user_id=user_id, product_id=product2.id)
        db_session.add_all([bookmark1, bookmark2])
        db_session.commit()

        result = repository.get_user_bookmarks_with_products(user_id)

        assert len(result) == 2
        # Each result should be a tuple of (bookmark, product)
        bookmarks, products = zip(*result)
        assert all(b.user_id == user_id for b in bookmarks)
        assert len(set(p.name for p in products)) == 2  # Both products present

    def test_get_popular_bookmarked_products(
        self, repository: BookmarkRepository, db_session: Session, vendor: Vendor
    ):
        """Test getting most bookmarked products."""
        product1 = ProductFactory(vendor_id=vendor.id, name="Popular Product")
        product2 = ProductFactory(vendor_id=vendor.id, name="Less Popular Product")
        db_session.add_all([product1, product2])
        db_session.commit()

        # Create multiple bookmarks for product1
        bookmarks = [
            ProductBookmarkFactory(user_id=1, product_id=product1.id),
            ProductBookmarkFactory(user_id=2, product_id=product1.id),
            ProductBookmarkFactory(user_id=3, product_id=product1.id),
            ProductBookmarkFactory(user_id=4, product_id=product2.id),
        ]
        db_session.add_all(bookmarks)
        db_session.commit()

        result = repository.get_popular_bookmarked_products(limit=2)

        assert len(result) <= 2
        # Should be ordered by bookmark count descending
        if len(result) >= 2:
            first_product, first_count = result[0]
            second_product, second_count = result[1]
            assert first_count >= second_count
            assert first_product.id == product1.id
            assert first_count == 3

    def test_pagination(
        self, repository: BookmarkRepository, db_session: Session, vendor: Vendor
    ):
        """Test pagination in get_by_user_id."""
        user_id = 1
        products = [ProductFactory(vendor_id=vendor.id) for _ in range(5)]
        db_session.add_all(products)
        db_session.commit()

        bookmarks = [
            ProductBookmarkFactory(user_id=user_id, product_id=products[i].id)
            for i in range(5)
        ]
        db_session.add_all(bookmarks)
        db_session.commit()

        # Test first page
        page1 = repository.get_by_user_id(user_id, skip=0, limit=2)
        assert len(page1) == 2

        # Test second page
        page2 = repository.get_by_user_id(user_id, skip=2, limit=2)
        assert len(page2) == 2

        # Test third page
        page3 = repository.get_by_user_id(user_id, skip=4, limit=2)
        assert len(page3) == 1

        # Ensure no overlap
        all_ids = [b.id for b in page1 + page2 + page3]
        assert len(all_ids) == len(set(all_ids))  # All unique
