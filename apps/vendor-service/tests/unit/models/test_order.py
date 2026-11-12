"""Tests for Order and OrderItem models."""

from datetime import datetime
from decimal import Decimal

import pytest
from src.models.order import Order, OrderItem


class TestOrderModel:
    """Test Order model functionality."""

    def test_create_order(self):
        """Test creating an order with valid data."""
        order = Order(
            customer_id=1,
            total_amount=Decimal("199.99"),
            shipping_address="123 Main St, City, State 12345",
        )

        assert order.customer_id == 1
        assert order.total_amount == Decimal("199.99")
        assert order.shipping_address == "123 Main St, City, State 12345"
        assert order.status == "pending"
        assert isinstance(order.created_at, datetime)
        assert isinstance(order.updated_at, datetime)

    def test_order_default_status(self):
        """Test order default status is pending."""
        order = Order(customer_id=1, total_amount=Decimal("100.00"))

        assert order.status == "pending"
        assert order.is_pending() is True

    def test_order_total_amount_validation(self):
        """Test order total amount validation."""
        # Negative amount
        with pytest.raises(ValueError, match="Total amount cannot be negative"):
            Order(customer_id=1, total_amount=Decimal("-10.00"))

        # Exceeds maximum
        with pytest.raises(ValueError, match="Total amount exceeds maximum"):
            Order(customer_id=1, total_amount=Decimal("100000000.00"))

    def test_order_status_validation(self):
        """Test order status validation."""
        with pytest.raises(ValueError, match="Invalid order status"):
            Order(
                customer_id=1, total_amount=Decimal("100.00"), status="invalid_status"
            )

    def test_order_status_transitions(self):
        """Test order status transitions."""
        order = Order(customer_id=1, total_amount=Decimal("100.00"))

        # pending -> confirmed
        order.update_status("confirmed")
        assert order.status == "confirmed"
        assert order.is_confirmed() is True

        # confirmed -> processing
        order.update_status("processing")
        assert order.status == "processing"

        # processing -> shipped
        order.update_status("shipped")
        assert order.status == "shipped"

        # shipped -> delivered
        order.update_status("delivered")
        assert order.status == "delivered"
        assert order.is_completed() is True

    def test_order_cancellation(self):
        """Test order cancellation logic."""
        order = Order(customer_id=1, total_amount=Decimal("100.00"))

        # Can cancel pending order
        assert order.can_be_cancelled() is True
        order.cancel()
        assert order.is_cancelled() is True

        # Cannot cancel already cancelled order
        with pytest.raises(ValueError, match="Cannot cancel order with status"):
            order.cancel()

    def test_order_cannot_cancel_shipped(self):
        """Test that shipped orders cannot be cancelled."""
        order = Order(customer_id=1, total_amount=Decimal("100.00"), status="shipped")

        assert order.can_be_cancelled() is False
        with pytest.raises(ValueError, match="Cannot cancel order with status"):
            order.cancel()

    def test_order_status_checks(self):
        """Test order status check methods."""
        order = Order(customer_id=1, total_amount=Decimal("100.00"))

        assert order.is_pending() is True
        assert order.is_confirmed() is False
        assert order.is_completed() is False
        assert order.is_cancelled() is False

        order.update_status("delivered")
        assert order.is_pending() is False
        assert order.is_completed() is True

    def test_order_repr(self):
        """Test order string representation."""
        order = Order(customer_id=1, total_amount=Decimal("199.99"))

        repr_str = repr(order)
        assert "customer_id=1" in repr_str
        assert "pending" in repr_str
        assert "199.99" in repr_str


class TestOrderItemModel:
    """Test OrderItem model functionality."""

    def test_create_order_item(self):
        """Test creating an order item with valid data."""
        item = OrderItem(
            order_id=1, product_id=10, quantity=5, unit_price=Decimal("29.99")
        )

        assert item.order_id == 1
        assert item.product_id == 10
        assert item.quantity == 5
        assert item.unit_price == Decimal("29.99")

    def test_order_item_quantity_validation(self):
        """Test order item quantity validation."""
        # Zero quantity
        with pytest.raises(ValueError, match="Quantity must be positive"):
            OrderItem(
                order_id=1, product_id=10, quantity=0, unit_price=Decimal("10.00")
            )

        # Negative quantity
        with pytest.raises(ValueError, match="Quantity must be positive"):
            OrderItem(
                order_id=1, product_id=10, quantity=-5, unit_price=Decimal("10.00")
            )

        # Exceeds maximum
        with pytest.raises(ValueError, match="Quantity exceeds maximum"):
            OrderItem(
                order_id=1, product_id=10, quantity=10001, unit_price=Decimal("10.00")
            )

    def test_order_item_unit_price_validation(self):
        """Test order item unit price validation."""
        with pytest.raises(ValueError, match="Unit price cannot be negative"):
            OrderItem(
                order_id=1, product_id=10, quantity=1, unit_price=Decimal("-10.00")
            )

    def test_order_item_subtotal_calculation(self):
        """Test order item subtotal calculation."""
        item = OrderItem(
            order_id=1, product_id=10, quantity=5, unit_price=Decimal("29.99")
        )

        expected_subtotal = Decimal("29.99") * 5
        assert item.get_subtotal() == expected_subtotal

    def test_order_item_repr(self):
        """Test order item string representation."""
        item = OrderItem(
            order_id=1, product_id=10, quantity=3, unit_price=Decimal("15.00")
        )

        repr_str = repr(item)
        assert "product_id=10" in repr_str
        assert "quantity=3" in repr_str


class TestOrderModelDatabase:
    """Test Order model with database."""

    def test_create_order_in_db(self, db_session):
        """Test creating and persisting an order."""
        order = Order(
            customer_id=1,
            total_amount=Decimal("299.99"),
            shipping_address="456 Oak Ave",
        )
        db_session.add(order)
        db_session.commit()

        assert order.id is not None

        # Retrieve from database
        retrieved = db_session.query(Order).filter_by(customer_id=1).first()
        assert retrieved is not None
        assert retrieved.total_amount == Decimal("299.99")
        assert retrieved.shipping_address == "456 Oak Ave"

    def test_order_item_relationship(self, db_session):
        """Test order-item relationship."""
        order = Order(customer_id=1, total_amount=Decimal("100.00"))
        db_session.add(order)
        db_session.commit()

        # Add items to order
        item1 = OrderItem(
            order_id=order.id, product_id=1, quantity=2, unit_price=Decimal("25.00")
        )
        item2 = OrderItem(
            order_id=order.id, product_id=2, quantity=1, unit_price=Decimal("50.00")
        )
        db_session.add(item1)
        db_session.add(item2)
        db_session.commit()

        # Test relationship
        assert len(order.items) == 2
        assert item1 in order.items
        assert item2 in order.items
        assert item1.order == order
        assert item2.order == order

    def test_order_calculate_total_from_items(self, db_session):
        """Test calculating order total from items."""
        order = Order(customer_id=1, total_amount=Decimal("0.00"))
        db_session.add(order)
        db_session.commit()

        # Add items
        item1 = OrderItem(
            order_id=order.id, product_id=1, quantity=2, unit_price=Decimal("25.00")
        )
        item2 = OrderItem(
            order_id=order.id, product_id=2, quantity=3, unit_price=Decimal("10.00")
        )
        db_session.add(item1)
        db_session.add(item2)
        db_session.commit()

        # Calculate total
        calculated_total = order.calculate_total()
        expected_total = (Decimal("25.00") * 2) + (Decimal("10.00") * 3)
        assert calculated_total == expected_total

        # Recalculate and update
        order.recalculate_total()
        assert order.total_amount == expected_total

    def test_order_cascade_delete(self, db_session):
        """Test that order items are deleted when order is deleted."""
        order = Order(customer_id=1, total_amount=Decimal("100.00"))
        db_session.add(order)
        db_session.commit()

        item = OrderItem(
            order_id=order.id, product_id=1, quantity=1, unit_price=Decimal("100.00")
        )
        db_session.add(item)
        db_session.commit()

        item_id = item.id

        # Delete order
        db_session.delete(order)
        db_session.commit()

        # Item should be deleted
        deleted_item = db_session.query(OrderItem).filter_by(id=item_id).first()
        assert deleted_item is None

    def test_order_empty_items_total(self, db_session):
        """Test calculating total for order with no items."""
        order = Order(customer_id=1, total_amount=Decimal("100.00"))
        db_session.add(order)
        db_session.commit()

        # No items added
        calculated_total = order.calculate_total()
        assert calculated_total == Decimal("0.00")

    def test_order_status_update_in_db(self, db_session):
        """Test updating order status in database."""
        order = Order(customer_id=1, total_amount=Decimal("100.00"))
        db_session.add(order)
        db_session.commit()

        original_updated_at = order.updated_at

        # Update status
        order.update_status("confirmed")
        db_session.commit()

        # Verify update
        retrieved = db_session.query(Order).filter_by(id=order.id).first()
        assert retrieved.status == "confirmed"
        assert retrieved.updated_at >= original_updated_at

    def test_multiple_items_same_product(self, db_session):
        """Test order with multiple items of the same product."""
        order = Order(customer_id=1, total_amount=Decimal("0.00"))
        db_session.add(order)
        db_session.commit()

        # Add same product twice (different order items)
        item1 = OrderItem(
            order_id=order.id, product_id=1, quantity=2, unit_price=Decimal("25.00")
        )
        item2 = OrderItem(
            order_id=order.id, product_id=1, quantity=3, unit_price=Decimal("25.00")
        )
        db_session.add(item1)
        db_session.add(item2)
        db_session.commit()

        # Both items should exist
        assert len(order.items) == 2

        # Total should include both
        calculated_total = order.calculate_total()
        expected_total = (Decimal("25.00") * 2) + (Decimal("25.00") * 3)
        assert calculated_total == expected_total
