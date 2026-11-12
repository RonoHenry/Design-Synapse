"""Repository for product data access."""

from decimal import Decimal
from typing import List, Optional

from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session
from src.models.product import Product


class ProductRepository:
    """Repository for product CRUD operations."""

    def __init__(self, db: Session):
        """Initialize repository with database session."""
        self.db = db

    def create(self, product: Product) -> Product:
        """Create a new product."""
        self.db.add(product)
        self.db.commit()
        self.db.refresh(product)
        return product

    def get_by_id(self, product_id: int) -> Optional[Product]:
        """Get product by ID."""
        return self.db.query(Product).filter(Product.id == product_id).first()

    def get_all(self, skip: int = 0, limit: int = 100) -> List[Product]:
        """Get all products with pagination."""
        return self.db.query(Product).offset(skip).limit(limit).all()

    def get_by_vendor(
        self, vendor_id: int, skip: int = 0, limit: int = 100
    ) -> List[Product]:
        """Get all products for a specific vendor."""
        return (
            self.db.query(Product)
            .filter(Product.vendor_id == vendor_id)
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_active_by_vendor(
        self, vendor_id: int, skip: int = 0, limit: int = 100
    ) -> List[Product]:
        """Get active products for a specific vendor."""
        return (
            self.db.query(Product)
            .filter(and_(Product.vendor_id == vendor_id, Product.is_active == True))
            .offset(skip)
            .limit(limit)
            .all()
        )

    def filter_by_category(
        self, category: str, skip: int = 0, limit: int = 100
    ) -> List[Product]:
        """Get products by category."""
        return (
            self.db.query(Product)
            .filter(Product.category == category)
            .offset(skip)
            .limit(limit)
            .all()
        )

    def filter_by_category_and_vendor(
        self, category: str, vendor_id: int, skip: int = 0, limit: int = 100
    ) -> List[Product]:
        """Get products by category for a specific vendor."""
        return (
            self.db.query(Product)
            .filter(and_(Product.category == category, Product.vendor_id == vendor_id))
            .offset(skip)
            .limit(limit)
            .all()
        )

    def search_products(
        self,
        search_term: str,
        category: Optional[str] = None,
        min_price: Optional[Decimal] = None,
        max_price: Optional[Decimal] = None,
        in_stock_only: bool = False,
        active_only: bool = True,
        skip: int = 0,
        limit: int = 100,
    ) -> List[Product]:
        """
        Search products with multiple filters.

        Args:
            search_term: Search in product name and description
            category: Filter by category
            min_price: Minimum price filter
            max_price: Maximum price filter
            in_stock_only: Only return products with inventory > 0
            active_only: Only return active products
            skip: Pagination offset
            limit: Pagination limit
        """
        query = self.db.query(Product)

        # Search term filter
        if search_term:
            search_pattern = f"%{search_term}%"
            query = query.filter(
                or_(
                    Product.name.ilike(search_pattern),
                    Product.description.ilike(search_pattern),
                )
            )

        # Category filter
        if category:
            query = query.filter(Product.category == category)

        # Price range filters
        if min_price is not None:
            query = query.filter(Product.price >= min_price)
        if max_price is not None:
            query = query.filter(Product.price <= max_price)

        # Stock filter
        if in_stock_only:
            query = query.filter(Product.inventory_quantity > 0)

        # Active filter
        if active_only:
            query = query.filter(Product.is_active == True)

        return query.offset(skip).limit(limit).all()

    def get_products_with_3d_models(
        self, skip: int = 0, limit: int = 100
    ) -> List[Product]:
        """Get products that have 3D model data for staging."""
        return (
            self.db.query(Product)
            .filter(
                and_(
                    Product.model_url.isnot(None),
                    Product.dimensions.isnot(None),
                    Product.model_format.isnot(None),
                )
            )
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_low_stock_products(
        self,
        threshold: int = 10,
        vendor_id: Optional[int] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[Product]:
        """Get products with inventory below threshold."""
        query = self.db.query(Product).filter(
            and_(
                Product.inventory_quantity <= threshold,
                Product.inventory_quantity > 0,
                Product.is_active == True,
            )
        )

        if vendor_id:
            query = query.filter(Product.vendor_id == vendor_id)

        return query.offset(skip).limit(limit).all()

    def get_out_of_stock_products(
        self, vendor_id: Optional[int] = None, skip: int = 0, limit: int = 100
    ) -> List[Product]:
        """Get products that are out of stock."""
        query = self.db.query(Product).filter(Product.inventory_quantity == 0)

        if vendor_id:
            query = query.filter(Product.vendor_id == vendor_id)

        return query.offset(skip).limit(limit).all()

    def update(self, product: Product) -> Product:
        """Update product."""
        self.db.commit()
        self.db.refresh(product)
        return product

    def update_inventory(self, product_id: int, quantity: int) -> Optional[Product]:
        """Update product inventory quantity."""
        product = self.get_by_id(product_id)
        if product:
            product.update_inventory(quantity)
            return self.update(product)
        return None

    def adjust_inventory(self, product_id: int, adjustment: int) -> Optional[Product]:
        """Adjust product inventory by delta amount."""
        product = self.get_by_id(product_id)
        if product:
            product.adjust_inventory(adjustment)
            return self.update(product)
        return None

    def check_availability(self, product_id: int, quantity: int = 1) -> bool:
        """Check if product has sufficient inventory."""
        product = self.get_by_id(product_id)
        if not product:
            return False
        return product.is_available() and product.inventory_quantity >= quantity

    def activate_product(self, product_id: int) -> Optional[Product]:
        """Activate a product."""
        product = self.get_by_id(product_id)
        if product:
            product.activate()
            return self.update(product)
        return None

    def deactivate_product(self, product_id: int) -> Optional[Product]:
        """Deactivate a product."""
        product = self.get_by_id(product_id)
        if product:
            product.deactivate()
            return self.update(product)
        return None

    def delete(self, product_id: int) -> bool:
        """Delete product by ID."""
        product = self.get_by_id(product_id)
        if product:
            self.db.delete(product)
            self.db.commit()
            return True
        return False

    def count(self) -> int:
        """Count total products."""
        return self.db.query(Product).count()

    def count_by_vendor(self, vendor_id: int) -> int:
        """Count products for a specific vendor."""
        return self.db.query(Product).filter(Product.vendor_id == vendor_id).count()

    def count_by_category(self, category: str) -> int:
        """Count products in a category."""
        return self.db.query(Product).filter(Product.category == category).count()

    def count_active(self) -> int:
        """Count active products."""
        return self.db.query(Product).filter(Product.is_active == True).count()

    def count_in_stock(self) -> int:
        """Count products with inventory."""
        return self.db.query(Product).filter(Product.inventory_quantity > 0).count()
