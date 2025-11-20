"""Product service for business logic."""

from decimal import Decimal
from typing import Any, Dict, List, Optional

from src.models.product import Product
from src.repositories.product_repository import ProductRepository


class ProductService:
    """Service for product business logic."""

    def __init__(self, product_repository: ProductRepository):
        """Initialize product service."""
        self.product_repository = product_repository

    async def create_product(
        self,
        vendor_id: int,
        name: str,
        category: str,
        price: Decimal,
        description: Optional[str] = None,
        inventory_quantity: int = 0,
        images: Optional[Dict[str, Any]] = None,
        specifications: Optional[Dict[str, Any]] = None,
        model_url: Optional[str] = None,
        dimensions: Optional[Dict[str, Any]] = None,
        model_format: Optional[str] = None,
    ) -> Product:
        """Create a new product."""
        product = Product(
            vendor_id=vendor_id,
            name=name,
            category=category,
            price=price,
            description=description,
            inventory_quantity=inventory_quantity,
            images=images,
            specifications=specifications,
            model_url=model_url,
            dimensions=dimensions,
            model_format=model_format,
        )

        return await self.product_repository.create(product)

    async def get_product(self, product_id: int) -> Optional[Product]:
        """Get product by ID."""
        return await self.product_repository.get_by_id(product_id)

    async def update_product(
        self,
        product_id: int,
        name: Optional[str] = None,
        description: Optional[str] = None,
        category: Optional[str] = None,
        price: Optional[Decimal] = None,
        inventory_quantity: Optional[int] = None,
        images: Optional[Dict[str, Any]] = None,
        specifications: Optional[Dict[str, Any]] = None,
        model_url: Optional[str] = None,
        dimensions: Optional[Dict[str, Any]] = None,
        model_format: Optional[str] = None,
        is_active: Optional[bool] = None,
    ) -> Optional[Product]:
        """Update product."""
        product = await self.product_repository.get_by_id(product_id)
        if not product:
            return None

        if name is not None:
            product.name = product._validate_name(name)
        if description is not None:
            product.description = description
        if category is not None:
            product.category = product._validate_category(category)
        if price is not None:
            product.price = product._validate_price(price)
        if inventory_quantity is not None:
            product.inventory_quantity = product._validate_inventory(inventory_quantity)
        if images is not None:
            product.images = images
        if specifications is not None:
            product.specifications = specifications
        if model_url is not None:
            product.model_url = model_url
        if dimensions is not None:
            product.dimensions = product._validate_dimensions(dimensions)
        if model_format is not None:
            product.model_format = product._validate_model_format(model_format)
        if is_active is not None:
            product.is_active = is_active

        return await self.product_repository.update(product)

    async def delete_product(self, product_id: int) -> bool:
        """Delete a product."""
        product = await self.product_repository.get_by_id(product_id)
        if not product:
            return False

        await self.product_repository.delete(product_id)
        return True

    async def get_vendor_products(
        self,
        vendor_id: int,
        skip: int = 0,
        limit: int = 100,
        category: Optional[str] = None,
        is_active: Optional[bool] = None,
    ) -> List[Product]:
        """Get products for a vendor."""
        return await self.product_repository.get_by_vendor(
            vendor_id=vendor_id,
            skip=skip,
            limit=limit,
            category=category,
            is_active=is_active,
        )

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
        return await self.product_repository.search_products(
            query=query,
            category=category,
            min_price=min_price,
            max_price=max_price,
            in_stock_only=in_stock_only,
            has_3d_model=has_3d_model,
            skip=skip,
            limit=limit,
        )

    async def update_inventory(
        self, product_id: int, quantity: int
    ) -> Optional[Product]:
        """Update product inventory."""
        product = await self.product_repository.get_by_id(product_id)
        if not product:
            return None

        product.update_inventory(quantity)
        return await self.product_repository.update(product)

    async def adjust_inventory(
        self, product_id: int, adjustment: int
    ) -> Optional[Product]:
        """Adjust product inventory by delta."""
        product = await self.product_repository.get_by_id(product_id)
        if not product:
            return None

        product.adjust_inventory(adjustment)
        return await self.product_repository.update(product)

    async def check_availability(self, product_id: int, quantity: int = 1) -> bool:
        """Check if product is available in requested quantity."""
        product = await self.product_repository.get_by_id(product_id)
        if not product:
            return False

        return product.is_available() and product.inventory_quantity >= quantity

    async def activate_product(self, product_id: int) -> Optional[Product]:
        """Activate a product."""
        product = await self.product_repository.get_by_id(product_id)
        if not product:
            return None

        product.activate()
        return await self.product_repository.update(product)

    async def deactivate_product(self, product_id: int) -> Optional[Product]:
        """Deactivate a product."""
        product = await self.product_repository.get_by_id(product_id)
        if not product:
            return None

        product.deactivate()
        return await self.product_repository.update(product)

    async def get_products_with_3d_models(
        self,
        skip: int = 0,
        limit: int = 100,
        category: Optional[str] = None,
    ) -> List[Product]:
        """Get products that have 3D models for staging."""
        return await self.product_repository.get_products_with_3d_models(
            skip=skip,
            limit=limit,
            category=category,
        )
