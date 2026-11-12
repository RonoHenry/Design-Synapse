"""Order service for business logic."""

from decimal import Decimal
from typing import List, Optional

from src.models.order import Order, OrderItem
from src.repositories.order_repository import OrderRepository
from src.repositories.product_repository import ProductRepository


class OrderService:
    """Service for order business logic."""

    def __init__(
        self,
        order_repository: OrderRepository,
        product_repository: ProductRepository,
    ):
        """Initialize order service."""
        self.order_repository = order_repository
        self.product_repository = product_repository

    async def create_order(
        self,
        customer_id: int,
        items: List[dict],
        shipping_address: Optional[str] = None,
    ) -> Order:
        """Create a new order with items."""
        # Validate all products exist and have sufficient inventory
        total_amount = Decimal("0.00")
        validated_items = []

        for item_data in items:
            product_id = item_data["product_id"]
            quantity = item_data["quantity"]

            # Get product and validate
            product = await self.product_repository.get_by_id(product_id)
            if not product:
                raise ValueError(f"Product {product_id} not found")

            if not product.is_active:
                raise ValueError(f"Product {product_id} is not active")

            if product.inventory_quantity < quantity:
                raise ValueError(
                    f"Insufficient inventory for product {product_id}. "
                    f"Available: {product.inventory_quantity}, Requested: {quantity}"
                )

            # Calculate item total
            unit_price = product.price
            subtotal = unit_price * quantity
            total_amount += subtotal

            validated_items.append(
                {
                    "product_id": product_id,
                    "quantity": quantity,
                    "unit_price": unit_price,
                    "subtotal": subtotal,
                }
            )

        # Create order
        order = Order(
            customer_id=customer_id,
            total_amount=total_amount,
            shipping_address=shipping_address,
        )

        # Create order with items
        created_order = await self.order_repository.create_order_with_items(
            order, validated_items
        )

        # Update product inventory
        for item_data in validated_items:
            await self.product_repository.adjust_inventory(
                item_data["product_id"], -item_data["quantity"]
            )

        return created_order

    async def get_order(self, order_id: int) -> Optional[Order]:
        """Get order by ID with items."""
        return await self.order_repository.get_order_with_items(order_id)

    async def get_customer_orders(
        self,
        customer_id: int,
        skip: int = 0,
        limit: int = 100,
        status: Optional[str] = None,
    ) -> List[Order]:
        """Get orders for a customer."""
        return await self.order_repository.get_by_customer_id(
            customer_id=customer_id,
            skip=skip,
            limit=limit,
            status=status,
        )

    async def get_vendor_orders(
        self,
        vendor_id: int,
        skip: int = 0,
        limit: int = 100,
        status: Optional[str] = None,
    ) -> List[Order]:
        """Get orders for a vendor."""
        return await self.order_repository.get_by_vendor(
            vendor_id=vendor_id,
            skip=skip,
            limit=limit,
            status=status,
        )

    async def update_order_status(
        self,
        order_id: int,
        new_status: str,
        updated_by: Optional[int] = None,
    ) -> Optional[Order]:
        """Update order status."""
        order = await self.order_repository.get_by_id(order_id)
        if not order:
            return None

        # Validate status transition
        valid_transitions = {
            "pending": ["confirmed", "cancelled"],
            "confirmed": ["processing", "cancelled"],
            "processing": ["shipped", "cancelled"],
            "shipped": ["delivered"],
            "delivered": [],
            "cancelled": [],
        }

        if new_status not in valid_transitions.get(order.status, []):
            raise ValueError(
                f"Invalid status transition from {order.status} to {new_status}"
            )

        # Handle inventory restoration for cancelled orders
        if new_status == "cancelled" and order.status in ["pending", "confirmed"]:
            await self._restore_inventory(order_id)

        return await self.order_repository.update_status(order_id, new_status)

    async def cancel_order(
        self, order_id: int, cancelled_by: Optional[int] = None
    ) -> Optional[Order]:
        """Cancel an order and restore inventory."""
        return await self.update_order_status(order_id, "cancelled")

    async def process_payment(
        self, order_id: int, payment_data: dict
    ) -> Optional[Order]:
        """Process payment for an order."""
        order = await self.order_repository.get_by_id(order_id)
        if not order:
            return None

        if order.status != "pending":
            raise ValueError(
                f"Cannot process payment for order with status {order.status}"
            )

        # In a real implementation, this would integrate with a payment processor
        # For now, we'll just update the status to confirmed
        return await self.update_order_status(order_id, "confirmed")

    async def get_order_total(self, order_id: int) -> Optional[Decimal]:
        """Calculate order total from items."""
        order = await self.order_repository.get_order_with_items(order_id)
        if not order:
            return None

        total = sum(item.subtotal for item in order.items)
        return total

    async def add_item_to_order(
        self,
        order_id: int,
        product_id: int,
        quantity: int,
    ) -> Optional[Order]:
        """Add item to existing order."""
        order = await self.order_repository.get_by_id(order_id)
        if not order:
            return None

        if order.status not in ["pending"]:
            raise ValueError(f"Cannot modify order with status {order.status}")

        # Validate product
        product = await self.product_repository.get_by_id(product_id)
        if not product:
            raise ValueError(f"Product {product_id} not found")

        if not product.is_active:
            raise ValueError(f"Product {product_id} is not active")

        if product.inventory_quantity < quantity:
            raise ValueError(
                f"Insufficient inventory for product {product_id}. "
                f"Available: {product.inventory_quantity}, Requested: {quantity}"
            )

        # Add item to order
        item_data = {
            "product_id": product_id,
            "quantity": quantity,
            "unit_price": product.price,
        }

        updated_order = await self.order_repository.add_item_to_order(
            order_id, item_data
        )

        # Update inventory
        await self.product_repository.adjust_inventory(product_id, -quantity)

        return updated_order

    async def remove_item_from_order(
        self,
        order_id: int,
        product_id: int,
    ) -> Optional[Order]:
        """Remove item from existing order."""
        order = await self.order_repository.get_by_id(order_id)
        if not order:
            return None

        if order.status not in ["pending"]:
            raise ValueError(f"Cannot modify order with status {order.status}")

        # Get item to restore inventory
        order_with_items = await self.order_repository.get_order_with_items(order_id)
        item_to_remove = None
        for item in order_with_items.items:
            if item.product_id == product_id:
                item_to_remove = item
                break

        if not item_to_remove:
            raise ValueError(f"Product {product_id} not found in order")

        # Remove item from order
        updated_order = await self.order_repository.remove_item_from_order(
            order_id, product_id
        )

        # Restore inventory
        await self.product_repository.adjust_inventory(
            product_id, item_to_remove.quantity
        )

        return updated_order

    async def _restore_inventory(self, order_id: int) -> None:
        """Restore inventory for cancelled order."""
        order = await self.order_repository.get_order_with_items(order_id)
        if not order:
            return

        for item in order.items:
            await self.product_repository.adjust_inventory(
                item.product_id, item.quantity
            )

    async def get_recent_orders(
        self,
        limit: int = 10,
        customer_id: Optional[int] = None,
    ) -> List[Order]:
        """Get recent orders."""
        return await self.order_repository.get_recent_orders(
            limit=limit,
            customer_id=customer_id,
        )

    async def get_orders_by_total_range(
        self,
        min_total: Optional[Decimal] = None,
        max_total: Optional[Decimal] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[Order]:
        """Get orders within total amount range."""
        return await self.order_repository.get_orders_by_total_range(
            min_total=min_total,
            max_total=max_total,
            skip=skip,
            limit=limit,
        )

    async def count_orders(
        self,
        customer_id: Optional[int] = None,
        status: Optional[str] = None,
    ) -> int:
        """Count orders with optional filters."""
        return await self.order_repository.count_orders(
            customer_id=customer_id,
            status=status,
        )
