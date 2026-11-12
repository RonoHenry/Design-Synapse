"""Tests for OrderRepository using TDD approach."""

from datetime import datetime, timedelta
from decimal import Decimal

import pytest
from src.models.order import Order, OrderItem
from src.repositories.order_repository import OrderRepository
from tests.factories import (OrderFactory, OrderItemFactory, ProductFactory,
                             VendorFactory)


class TestOrderRepository:
    """Test cases for OrderRepository CRUD operations."""

    def test_create_order(self, db_session):
        """Test creating a new order."""
        repo = OrderRepository(db_session)
        order_data = {
            "customer_id": 1,
            "total_amount": Decimal("99.99"),
            "shipping_address": "123 Test St, Test City",
            "status": "pending",
        }

        order = repo.create(**order_data)

        assert order.id is not None
        assert order.customer_id == 1
        assert order.total_amount == Decimal("99.99")
        assert order.shipping_address == "123 Test St, Test City"
        assert order.status == "pending"
        assert order.created_at is not None
        assert order.updated_at is not None

    def test_create_order_with_items(self, db_session):
        """Test creating order with order items."""
        repo = OrderRepository(db_session)

        order_items = [
            {"product_id": 1, "quantity": 2, "unit_price": Decimal("10.00")},
            {"product_id": 2, "quantity": 1, "unit_price": Decimal("20.00")},
        ]

        order = repo.create_with_items(
            customer_id=1, shipping_address="123 Test St", items=order_items
        )

        assert order.id is not None
        assert len(order.items) == 2
        assert order.total_amount == Decimal("40.00")  # (2*10) + (1*20)

    def test_get_by_id_existing_order(self, db_session):
        """Test retrieving order by ID when order exists."""
        repo = OrderRepository(db_session)
        order = OrderFactory(customer_id=1, total_amount=Decimal("50.00"))
        db_session.add(order)
        db_session.commit()

        result = repo.get_by_id(order.id)

        assert result is not None
        assert result.id == order.id
        assert result.customer_id == 1
        assert result.total_amount == Decimal("50.00")

    def test_get_by_id_nonexistent_order(self, db_session):
        """Test retrieving order by ID when order doesn't exist."""
        repo = OrderRepository(db_session)

        result = repo.get_by_id(999)

        assert result is None

    def test_get_by_customer_id(self, db_session):
        """Test retrieving orders by customer ID."""
        repo = OrderRepository(db_session)
        orders = [
            OrderFactory(customer_id=1, total_amount=Decimal("10.00")),
            OrderFactory(customer_id=1, total_amount=Decimal("20.00")),
            OrderFactory(customer_id=2, total_amount=Decimal("30.00")),
        ]
        for order in orders:
            db_session.add(order)
        db_session.commit()

        customer_1_orders = repo.get_by_customer(1)
        customer_2_orders = repo.get_by_customer(2)

        assert len(customer_1_orders) == 2
        assert len(customer_2_orders) == 1
        assert all(order.customer_id == 1 for order in customer_1_orders)

    def test_get_by_vendor(self, db_session):
        """Test retrieving orders by vendor (through products)."""
        repo = OrderRepository(db_session)

        # Set up factories with models
        from src.models.order import OrderItem
        from src.models.product import Product
        from src.models.vendor import Vendor

        VendorFactory._meta.model = Vendor
        VendorFactory._meta.sqlalchemy_session = db_session
        ProductFactory._meta.model = Product
        ProductFactory._meta.sqlalchemy_session = db_session
        OrderItemFactory._meta.model = OrderItem
        OrderItemFactory._meta.sqlalchemy_session = db_session

        # Create vendor and products
        vendor1 = VendorFactory(id=1)
        vendor2 = VendorFactory(id=2)
        product1 = ProductFactory(id=1, vendor_id=1)
        product2 = ProductFactory(id=2, vendor_id=2)
        db_session.add_all([vendor1, vendor2, product1, product2])

        # Create orders with items
        order1 = OrderFactory(customer_id=1)
        order2 = OrderFactory(customer_id=2)
        db_session.add_all([order1, order2])
        db_session.commit()

        # Add items to orders
        item1 = OrderItemFactory(order_id=order1.id, product_id=1)
        item2 = OrderItemFactory(order_id=order2.id, product_id=2)
        db_session.add_all([item1, item2])
        db_session.commit()

        vendor_1_orders = repo.get_by_vendor(1)
        vendor_2_orders = repo.get_by_vendor(2)

        assert len(vendor_1_orders) == 1
        assert len(vendor_2_orders) == 1

    def test_update_order_status(self, db_session):
        """Test updating order status."""
        repo = OrderRepository(db_session)
        order = OrderFactory(customer_id=1, status="pending")
        db_session.add(order)
        db_session.commit()

        updated_order = repo.update_status(order.id, "confirmed")

        assert updated_order is not None
        assert updated_order.status == "confirmed"
        assert updated_order.updated_at > updated_order.created_at

    def test_update_nonexistent_order_status(self, db_session):
        """Test updating status of nonexistent order."""
        repo = OrderRepository(db_session)

        result = repo.update_status(999, "confirmed")

        assert result is None

    def test_delete_order(self, db_session):
        """Test deleting order."""
        repo = OrderRepository(db_session)
        order = OrderFactory(customer_id=1)
        db_session.add(order)
        db_session.commit()
        order_id = order.id

        success = repo.delete(order_id)

        assert success is True
        assert repo.get_by_id(order_id) is None

    def test_delete_nonexistent_order(self, db_session):
        """Test deleting order that doesn't exist."""
        repo = OrderRepository(db_session)

        success = repo.delete(999)

        assert success is False

    def test_get_orders_by_status(self, db_session):
        """Test retrieving orders by status."""
        repo = OrderRepository(db_session)
        orders = [
            OrderFactory(customer_id=1, status="pending"),
            OrderFactory(customer_id=2, status="pending"),
            OrderFactory(customer_id=3, status="confirmed"),
            OrderFactory(customer_id=4, status="shipped"),
        ]
        for order in orders:
            db_session.add(order)
        db_session.commit()

        pending_orders = repo.get_by_status("pending")
        confirmed_orders = repo.get_by_status("confirmed")
        shipped_orders = repo.get_by_status("shipped")

        assert len(pending_orders) == 2
        assert len(confirmed_orders) == 1
        assert len(shipped_orders) == 1

    def test_count_orders(self, db_session):
        """Test counting total orders."""
        repo = OrderRepository(db_session)
        orders = [OrderFactory(customer_id=i) for i in range(1, 4)]
        for order in orders:
            db_session.add(order)
        db_session.commit()

        count = repo.count()

        assert count == 3

    def test_count_orders_by_status(self, db_session):
        """Test counting orders by status."""
        repo = OrderRepository(db_session)
        orders = [
            OrderFactory(customer_id=1, status="pending"),
            OrderFactory(customer_id=2, status="pending"),
            OrderFactory(customer_id=3, status="confirmed"),
            OrderFactory(customer_id=4, status="shipped"),
        ]
        for order in orders:
            db_session.add(order)
        db_session.commit()

        pending_count = repo.count_by_status("pending")
        confirmed_count = repo.count_by_status("confirmed")

        assert pending_count == 2
        assert confirmed_count == 1

    def test_get_order_with_items(self, db_session):
        """Test retrieving order with its items."""
        repo = OrderRepository(db_session)

        # Set up factory with model
        from src.models.order import OrderItem

        OrderItemFactory._meta.model = OrderItem
        OrderItemFactory._meta.sqlalchemy_session = db_session

        order = OrderFactory(customer_id=1)
        db_session.add(order)
        db_session.commit()

        items = [
            OrderItemFactory(order_id=order.id, product_id=1, quantity=2),
            OrderItemFactory(order_id=order.id, product_id=2, quantity=1),
        ]
        for item in items:
            db_session.add(item)
        db_session.commit()

        result = repo.get_with_items(order.id)

        assert result is not None
        assert len(result.items) == 2

    def test_add_item_to_order(self, db_session):
        """Test adding item to existing order."""
        repo = OrderRepository(db_session)

        order = OrderFactory(customer_id=1, total_amount=Decimal("0.00"))
        db_session.add(order)
        db_session.commit()

        item_data = {"product_id": 1, "quantity": 2, "unit_price": Decimal("15.00")}

        updated_order = repo.add_item(order.id, **item_data)

        assert updated_order is not None
        assert len(updated_order.items) == 1
        assert updated_order.total_amount == Decimal("30.00")

    def test_remove_item_from_order(self, db_session):
        """Test removing item from order."""
        repo = OrderRepository(db_session)

        # Set up factory with model
        from src.models.order import OrderItem

        OrderItemFactory._meta.model = OrderItem
        OrderItemFactory._meta.sqlalchemy_session = db_session

        order = OrderFactory(customer_id=1)
        db_session.add(order)
        db_session.commit()

        item = OrderItemFactory(
            order_id=order.id, product_id=1, quantity=2, unit_price=Decimal("10.00")
        )
        db_session.add(item)
        db_session.commit()

        success = repo.remove_item(order.id, item.id)

        assert success is True
        updated_order = repo.get_with_items(order.id)
        assert len(updated_order.items) == 0

    def test_get_recent_orders(self, db_session):
        """Test retrieving recent orders."""
        repo = OrderRepository(db_session)
        orders = [OrderFactory(customer_id=i) for i in range(1, 6)]  # Create 5 orders
        for order in orders:
            db_session.add(order)
        db_session.commit()

        recent_orders = repo.get_recent_orders(limit=3)

        assert len(recent_orders) == 3

    def test_get_orders_by_total_range(self, db_session):
        """Test retrieving orders by total amount range."""
        repo = OrderRepository(db_session)
        orders = [
            OrderFactory(customer_id=1, total_amount=Decimal("10.00")),
            OrderFactory(customer_id=2, total_amount=Decimal("50.00")),
            OrderFactory(customer_id=3, total_amount=Decimal("100.00")),
            OrderFactory(customer_id=4, total_amount=Decimal("200.00")),
        ]
        for order in orders:
            db_session.add(order)
        db_session.commit()

        mid_range_orders = repo.get_by_total_range(
            min_amount=Decimal("25.00"), max_amount=Decimal("150.00")
        )

        assert len(mid_range_orders) == 2  # $50 and $100 orders
