"""Async repository for product data access."""

from decimal import Decimal
from typing import List, Optional

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from src.models.product import Product


class ProductRepository:
    """Async repository for product CRUD operations."""

    def __init__(self, db: AsyncSession):
        """Initialize repository with database session."""
        self.db = db

    async def create(self, product: Product) -> Product:
        """Create a new product."""
        self.db.add(product)
        await self.db.commit()
        await self.db.refresh(product)
        return product

    async def get_by_id(self, product_id: int) -> Optional[Product]:
        """Get product by ID."""
        result = await self.db.execute(select(Product).filter(Product.id == product_id))
        return result.scalar_one_or_none()

    async def update(self, product: Product) -> Product:
        """Update product."""
        await self.db.commit()
        await self.db.refresh(product)
        return product

    async def delete(self, product_id: int) -> bool:
        """Delete product by ID."""
        product = await self.get_by_id(product_id)
        if product:
            await self.db.delete(product)
            await self.db.commit()
            return True
        return False

    async def get_by_vendor(
        self,
        vendor_id: int,
        skip: int = 0,
        limit: int = 100,
        category: Optional[str] = None,
        is_active: Optional[bool] = None,
    ) -> List[Product]:
        """Get products for a vendor with optional filters."""
        query = select(Product).filter(Product.vendor_id == vendor_id)

        if category:
            query = query.filter(Product.category == category)

        if is_active is not None:
            query = query.filter(Product.is_active == is_active)

        query = query.offset(skip).limit(limit)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def search_products(
        self,
        query: Optional[str] = None,
        category: Optional[str] = None,
        min_price: Optional[Decimal] = None,
        max_price: Optional[Decimal] = None,
        in_stock_only: bool = False,
        has_3d_model: Optional[bool] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[Product]:
        """Search products with filters."""
        stmt = select(Product).filter(Product.is_active == True)

        # Search term filter
        if query:
            search_pattern = f"%{query}%"
            stmt = stmt.filter(
                or_(
                    Product.name.ilike(search_pattern),
                    Product.description.ilike(search_pattern),
                )
            )

        # Category filter
        if category:
            stmt = stmt.filter(Product.category == category)

        # Price range filters
        if min_price is not None:
            stmt = stmt.filter(Product.price >= min_price)
        if max_price is not None:
            stmt = stmt.filter(Product.price <= max_price)

        # Stock filter
        if in_stock_only:
            stmt = stmt.filter(Product.inventory_quantity > 0)

        # 3D model filter
        if has_3d_model is not None:
            if has_3d_model:
                stmt = stmt.filter(
                    and_(
                        Product.model_url.isnot(None),
                        Product.dimensions.isnot(None),
                        Product.model_format.isnot(None),
                    )
                )
            else:
                stmt = stmt.filter(
                    or_(
                        Product.model_url.is_(None),
                        Product.dimensions.is_(None),
                        Product.model_format.is_(None),
                    )
                )

        stmt = stmt.offset(skip).limit(limit)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_products_with_3d_models(
        self,
        skip: int = 0,
        limit: int = 100,
        category: Optional[str] = None,
    ) -> List[Product]:
        """Get products that have 3D model data for staging."""
        stmt = select(Product).filter(
            and_(
                Product.model_url.isnot(None),
                Product.dimensions.isnot(None),
                Product.model_format.isnot(None),
                Product.is_active == True,
            )
        )

        if category:
            stmt = stmt.filter(Product.category == category)

        stmt = stmt.offset(skip).limit(limit)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def check_availability(self, product_id: int, quantity: int = 1) -> bool:
        """Check if product has sufficient inventory."""
        product = await self.get_by_id(product_id)
        if not product:
            return False
        return product.is_available() and product.inventory_quantity >= quantity
