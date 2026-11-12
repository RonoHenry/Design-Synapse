"""Repository for bookmark data access."""

from typing import List, Optional, Tuple

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session, joinedload
from src.models.bookmark import ProductBookmark
from src.models.product import Product


class BookmarkRepository:
    """Repository for bookmark CRUD operations."""

    def __init__(self, db: Session):
        """Initialize repository with database session."""
        self.db = db

    def create(self, bookmark: ProductBookmark) -> ProductBookmark:
        """Create a new bookmark."""
        self.db.add(bookmark)
        self.db.commit()
        self.db.refresh(bookmark)
        return bookmark

    def get_by_id(self, bookmark_id: int) -> Optional[ProductBookmark]:
        """Get bookmark by ID."""
        return (
            self.db.query(ProductBookmark)
            .filter(ProductBookmark.id == bookmark_id)
            .first()
        )

    def get_by_user_id(
        self, user_id: int, skip: int = 0, limit: int = 100
    ) -> List[ProductBookmark]:
        """Get all bookmarks for a specific user."""
        return (
            self.db.query(ProductBookmark)
            .filter(ProductBookmark.user_id == user_id)
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_by_user_and_product(
        self, user_id: int, product_id: int
    ) -> Optional[ProductBookmark]:
        """Get bookmark by user and product."""
        return (
            self.db.query(ProductBookmark)
            .filter(
                ProductBookmark.user_id == user_id,
                ProductBookmark.product_id == product_id,
            )
            .first()
        )

    def exists_by_user_and_product(self, user_id: int, product_id: int) -> bool:
        """Check if bookmark exists for user and product."""
        return (
            self.db.query(ProductBookmark)
            .filter(
                ProductBookmark.user_id == user_id,
                ProductBookmark.product_id == product_id,
            )
            .first()
        ) is not None

    def update(self, bookmark: ProductBookmark) -> ProductBookmark:
        """Update an existing bookmark."""
        self.db.commit()
        self.db.refresh(bookmark)
        return bookmark

    def delete(self, bookmark: ProductBookmark) -> None:
        """Delete a bookmark."""
        self.db.delete(bookmark)
        self.db.commit()

    def delete_by_id(self, bookmark_id: int) -> bool:
        """Delete bookmark by ID. Returns True if deleted, False if not found."""
        bookmark = self.get_by_id(bookmark_id)
        if bookmark:
            self.delete(bookmark)
            return True
        return False

    def count_by_user(self, user_id: int) -> int:
        """Count bookmarks for a user."""
        return (
            self.db.query(ProductBookmark)
            .filter(ProductBookmark.user_id == user_id)
            .count()
        )

    def get_user_bookmarks_with_products(
        self, user_id: int, skip: int = 0, limit: int = 100
    ) -> List[Tuple[ProductBookmark, Product]]:
        """Get user bookmarks with product details."""
        return (
            self.db.query(ProductBookmark, Product)
            .join(Product, ProductBookmark.product_id == Product.id)
            .filter(ProductBookmark.user_id == user_id)
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_popular_bookmarked_products(
        self, limit: int = 10
    ) -> List[Tuple[Product, int]]:
        """Get most bookmarked products with bookmark counts."""
        return (
            self.db.query(
                Product, func.count(ProductBookmark.id).label("bookmark_count")
            )
            .join(ProductBookmark, Product.id == ProductBookmark.product_id)
            .group_by(Product.id)
            .order_by(func.count(ProductBookmark.id).desc())
            .limit(limit)
            .all()
        )
