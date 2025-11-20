"""Repository for order data access operations."""

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional

from sqlalchemy import and_, func
from sqlalchemy.orm import Session, joinedload
from src.models.order import Order, OrderItem
from src.models.product import Product


class OrderRepository:
    """Repository for order CRUD operations and queries."""

    def __init__(self, db_session: Session):
        """Initialize repository with database session."""
        self.db = db_session

    def create(
        self,
        customer_id: int,
        total_amount: Decimal,
        shipping_address: Optional[str] = None,
        status: str = "pending",
    ) -> Order:
        """Create a new order."""
        order = Order(
            customer_id=customer_id,
            total_amount=total_amount,
            shipping_address=shipping_address,
            status=status,
        )

        self.db.add(order)
        self.db.commit()
        self.db.refresh(order)
        return order

    def create_with_items(
        self,
        customer_id: int,
        shipping_address: Optional[str] = None,
        items: List[Dict[str, Any]] = None,
        status: str = "pending",
    ) -> Order:
        """Create order with items and calculate total."""
        if not items:
            items = []

        # Calculate total from items
        total_amount = sum(
            Decimal(str(item["quantity"])) * Decimal(str(item["unit_price"]))
            for item in items
        )

        # Create order
        order = Order(
            customer_id=customer_id,
            total_amount=total_amount,
            shipping_address=shipping_address,
            status=status,
        )

        self.db.add(order)
        self.db.flush()  # Get order ID without committing

        # Create order items
        for item_data in items:
            order_item = OrderItem(
                order_id=order.id,
                product_id=item_data["product_id"],
                quantity=item_data["quantity"],
                unit_price=item_data["unit_price"],
            )
            self.db.add(order_item)

        self.db.commit()
        self.db.refresh(order)
        return order

    def get_by_id(self, order_id: int) -> Optional[Order]:
        """Get order by ID."""
        return self.db.query(Order).filter(Order.id == order_id).first()

    def get_with_items(self, order_id: int) -> Optional[Order]:
        """Get order by ID with its items loaded."""
        return (
            self.db.query(Order)
            .options(joinedload(Order.items))
            .filter(Order.id == order_id)
            .first()
        )

    def get_by_customer(
        self,
        customer_id: int,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> List[Order]:
        """Get orders by customer ID."""
        query = (
            self.db.query(Order)
            .filter(Order.customer_id == customer_id)
            .order_by(Order.created_at.desc())
        )

        if offset:
            query = query.offset(offset)
        if limit:
            query = query.limit(limit)

        return query.all()

    def get_by_vendor(
        self, vendor_id: int, limit: Optional[int] = None, offset: Optional[int] = None
    ) -> List[Order]:
        """Get orders that contain products from a specific vendor."""
        query = (
            self.db.query(Order)
            .join(OrderItem, Order.id == OrderItem.order_id)
            .join(Product, OrderItem.product_id == Product.id)
            .filter(Product.vendor_id == vendor_id)
            .distinct()
            .order_by(Order.created_at.desc())
        )

        if offset:
            query = query.offset(offset)
        if limit:
            query = query.limit(limit)

        return query.all()

    def update_status(self, order_id: int, new_status: str) -> Optional[Order]:
        """Update order status."""
        order = self.get_by_id(order_id)
        if not order:
            return None

        order.update_status(new_status)
        self.db.commit()
        self.db.refresh(order)
        return order

    def delete(self, order_id: int) -> bool:
        """Delete order by ID."""
        order = self.get_by_id(order_id)
        if not order:
            return False

        self.db.delete(order)
        self.db.commit()
        return True

    def get_by_status(
        self, status: str, limit: Optional[int] = None, offset: Optional[int] = None
    ) -> List[Order]:
        """Get orders by status."""
        query = (
            self.db.query(Order)
            .filter(Order.status == status)
            .order_by(Order.created_at.desc())
        )

        if offset:
            query = query.offset(offset)
        if limit:
            query = query.limit(limit)

        return query.all()

    def get_by_date_range(
        self,
        start_date: datetime,
        end_date: datetime,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> List[Order]:
        """Get orders within date range."""
        query = (
            self.db.query(Order)
            .filter(and_(Order.created_at >= start_date, Order.created_at <= end_date))
            .order_by(Order.created_at.desc())
        )

        if offset:
            query = query.offset(offset)
        if limit:
            query = query.limit(limit)

        return query.all()

    def get_by_total_range(
        self,
        min_amount: Decimal,
        max_amount: Decimal,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> List[Order]:
        """Get orders within total amount range."""
        query = (
            self.db.query(Order)
            .filter(
                and_(Order.total_amount >= min_amount, Order.total_amount <= max_amount)
            )
            .order_by(Order.total_amount.desc())
        )

        if offset:
            query = query.offset(offset)
        if limit:
            query = query.limit(limit)

        return query.all()

    def count(self) -> int:
        """Count total number of orders."""
        return self.db.query(Order).count()

    def count_by_status(self, status: str) -> int:
        """Count orders by status."""
        return self.db.query(Order).filter(Order.status == status).count()

    def count_by_customer(self, customer_id: int) -> int:
        """Count orders by customer."""
        return self.db.query(Order).filter(Order.customer_id == customer_id).count()

    def get_recent_orders(self, limit: int = 10) -> List[Order]:
        """Get recent orders."""
        return self.db.query(Order).order_by(Order.created_at.desc()).limit(limit).all()

    def add_item(
        self, order_id: int, product_id: int, quantity: int, unit_price: Decimal
    ) -> Optional[Order]:
        """Add item to existing order."""
        order = self.get_with_items(order_id)
        if not order:
            return None

        # Create new order item
        order_item = OrderItem(
            order_id=order_id,
            product_id=product_id,
            quantity=quantity,
            unit_price=unit_price,
        )

        self.db.add(order_item)
        self.db.commit()

        # Get fresh order with items and recalculate total
        order = self.get_with_items(order_id)
        order.recalculate_total()

        self.db.commit()
        self.db.refresh(order)
        return order

    def remove_item(self, order_id: int, item_id: int) -> bool:
        """Remove item from order."""
        order_item = (
            self.db.query(OrderItem)
            .filter(and_(OrderItem.id == item_id, OrderItem.order_id == order_id))
            .first()
        )

        if not order_item:
            return False

        self.db.delete(order_item)

        # Recalculate order total
        order = self.get_with_items(order_id)
        if order:
            order.recalculate_total()

        self.db.commit()
        return True

    def get_order_statistics(self) -> Dict[str, Any]:
        """Get order statistics."""
        total_orders = self.count()

        status_counts = {}
        for status in [
            "pending",
            "confirmed",
            "processing",
            "shipped",
            "delivered",
            "cancelled",
        ]:
            status_counts[status] = self.count_by_status(status)

        # Calculate total revenue
        total_revenue = self.db.query(func.sum(Order.total_amount)).filter(
            Order.status.in_(["delivered", "shipped"])
        ).scalar() or Decimal("0.0")

        return {
            "total_orders": total_orders,
            "status_counts": status_counts,
            "total_revenue": total_revenue,
        }

    def get_top_customers(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get top customers by order count and total spent."""
        results = (
            self.db.query(
                Order.customer_id,
                func.count(Order.id).label("order_count"),
                func.sum(Order.total_amount).label("total_spent"),
            )
            .group_by(Order.customer_id)
            .order_by(func.sum(Order.total_amount).desc())
            .limit(limit)
            .all()
        )

        return [
            {
                "customer_id": result.customer_id,
                "order_count": result.order_count,
                "total_spent": result.total_spent,
            }
            for result in results
        ]
