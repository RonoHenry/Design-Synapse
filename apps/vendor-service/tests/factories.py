"""
Factory classes for creating test data in the vendor service.
"""

import os
# Import the shared testing infrastructure
import sys
from datetime import datetime, timezone
from decimal import Decimal
from typing import List, Optional

import factory
from factory.alchemy import SQLAlchemyModelFactory

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", "..", "packages"))

from common.testing.base_factory import BaseFactory, FakerMixin, TimestampMixin


class VendorFactory(BaseFactory, FakerMixin, TimestampMixin):
    """Factory for creating Vendor instances."""

    class Meta:
        model = None  # Will be set dynamically
        sqlalchemy_session_persistence = "commit"
        abstract = False

    user_id = factory.Sequence(lambda n: n + 1)
    company_name = factory.Faker("company")
    email = factory.Faker("company_email")
    phone = factory.Faker("phone_number")
    address = factory.Faker("address")
    verification_status = "pending"
    rating = Decimal("0.0")

    class Params:
        """Traits for different vendor types."""

        verified = factory.Trait(verification_status="verified")
        suspended = factory.Trait(verification_status="suspended")


class ProductFactory(BaseFactory, FakerMixin, TimestampMixin):
    """Factory for creating Product instances."""

    class Meta:
        model = None  # Will be set dynamically
        sqlalchemy_session_persistence = "commit"
        abstract = False

    vendor_id = factory.Sequence(lambda n: n + 1)
    name = factory.Faker("catch_phrase")
    description = factory.Faker("text", max_nb_chars=500)
    category = "materials"
    price = factory.Faker("pydecimal", left_digits=4, right_digits=2, positive=True)
    inventory_quantity = factory.Faker("random_int", min=0, max=1000)
    is_active = True

    # Staging fields for 3D models
    model_url = factory.LazyAttribute(
        lambda obj: f"https://storage.example.com/models/{obj.name.replace(' ', '_').lower()}.glb"
    )
    dimensions = factory.LazyFunction(
        lambda: {"length": 10.5, "width": 5.2, "height": 2.1}
    )
    model_format = "glb"

    class Params:
        """Traits for different product types."""

        inactive = factory.Trait(is_active=False)
        out_of_stock = factory.Trait(inventory_quantity=0)


class OrderFactory(BaseFactory, TimestampMixin):
    """Factory for creating Order instances."""

    class Meta:
        model = None  # Will be set dynamically
        sqlalchemy_session_persistence = "commit"
        abstract = False

    customer_id = factory.Sequence(lambda n: n + 1)
    total_amount = factory.Faker(
        "pydecimal", left_digits=4, right_digits=2, positive=True
    )
    status = "pending"
    shipping_address = factory.Faker("address")

    class Params:
        """Traits for different order statuses."""

        confirmed = factory.Trait(status="confirmed")
        shipped = factory.Trait(status="shipped")
        delivered = factory.Trait(status="delivered")
        cancelled = factory.Trait(status="cancelled")


class OrderItemFactory(BaseFactory):
    """Factory for creating OrderItem instances."""

    class Meta:
        model = None  # Will be set dynamically
        sqlalchemy_session_persistence = "commit"
        abstract = False

    order_id = factory.Sequence(lambda n: n + 1)
    product_id = factory.Sequence(lambda n: n + 1)
    quantity = factory.Faker("random_int", min=1, max=10)
    unit_price = factory.Faker(
        "pydecimal", left_digits=3, right_digits=2, positive=True
    )


class ReviewFactory(BaseFactory, TimestampMixin):
    """Factory for creating Review instances."""

    class Meta:
        model = None  # Will be set dynamically
        sqlalchemy_session_persistence = "commit"
        abstract = False

    user_id = factory.Sequence(lambda n: n + 1)
    product_id = factory.Sequence(lambda n: n + 1)
    vendor_id = factory.Sequence(lambda n: n + 1)
    rating = factory.Faker("random_int", min=1, max=5)
    comment = factory.Faker("text", max_nb_chars=500)
    verified_purchase = False

    class Params:
        """Traits for different review types."""

        verified = factory.Trait(verified_purchase=True)


class BookmarkFactory(BaseFactory, TimestampMixin):
    """Factory for creating ProductBookmark instances."""

    class Meta:
        model = None  # Will be set dynamically
        sqlalchemy_session_persistence = "commit"
        abstract = False

    user_id = factory.Sequence(lambda n: n + 1)
    product_id = factory.Sequence(lambda n: n + 1)
    notes = factory.Faker("sentence")


class StagingFactory(BaseFactory, TimestampMixin):
    """Factory for creating DesignStaging instances."""

    class Meta:
        model = None  # Will be set dynamically
        sqlalchemy_session_persistence = "commit"
        abstract = False

    design_id = factory.Sequence(lambda n: n + 1)
    product_id = factory.Sequence(lambda n: n + 1)
    position = factory.LazyFunction(lambda: {"x": 10.5, "y": 20.3, "z": 5.1})
    rotation = factory.LazyFunction(lambda: {"x": 0.0, "y": 90.0, "z": 0.0})
    scale = factory.LazyFunction(lambda: {"x": 1.0, "y": 1.0, "z": 1.0})
    quantity = factory.Faker("random_int", min=1, max=10)


# Convenience functions for common test scenarios
def create_test_vendor(session, **kwargs):
    """Create a test vendor with the given session."""
    from src.models.vendor import Vendor

    VendorFactory._meta.model = Vendor
    VendorFactory._meta.sqlalchemy_session = session
    return VendorFactory(**kwargs)


def create_test_product(session, **kwargs):
    """Create a test product with the given session."""
    from src.models.product import Product

    ProductFactory._meta.model = Product
    ProductFactory._meta.sqlalchemy_session = session
    return ProductFactory(**kwargs)


def create_test_order(session, product_ids: Optional[List[int]] = None, **kwargs):
    """Create a test order with items."""
    from src.models.order import Order, OrderItem

    OrderFactory._meta.model = Order
    OrderItemFactory._meta.model = OrderItem
    OrderFactory._meta.sqlalchemy_session = session
    OrderItemFactory._meta.sqlalchemy_session = session

    order = OrderFactory(**kwargs)
    session.add(order)
    session.commit()

    # Create order items if product_ids provided
    if product_ids:
        for product_id in product_ids:
            item = OrderItemFactory(order_id=order.id, product_id=product_id)
            session.add(item)
        session.commit()

    return order


def create_test_review(session, **kwargs):
    """Create a test review with the given session."""
    from src.models.review import Review

    ReviewFactory._meta.model = Review
    ReviewFactory._meta.sqlalchemy_session = session
    return ReviewFactory(**kwargs)


def create_test_bookmark(session, **kwargs):
    """Create a test bookmark with the given session."""
    from src.models.bookmark import ProductBookmark

    BookmarkFactory._meta.model = ProductBookmark
    BookmarkFactory._meta.sqlalchemy_session = session
    return BookmarkFactory(**kwargs)


def create_test_staging(session, **kwargs):
    """Create a test staging entry with the given session."""
    from src.models.staging import DesignStaging

    StagingFactory._meta.model = DesignStaging
    StagingFactory._meta.sqlalchemy_session = session
    return StagingFactory(**kwargs)


def create_batch_vendors(session, count=5, **kwargs):
    """Create a batch of test vendors."""
    from src.models.vendor import Vendor

    VendorFactory._meta.model = Vendor
    VendorFactory._meta.sqlalchemy_session = session
    return VendorFactory.create_batch(count, **kwargs)


def create_batch_products(session, count=10, **kwargs):
    """Create a batch of test products."""
    from src.models.product import Product

    ProductFactory._meta.model = Product
    ProductFactory._meta.sqlalchemy_session = session
    return ProductFactory.create_batch(count, **kwargs)


def create_batch_orders(session, count=5, **kwargs):
    """Create a batch of test orders."""
    from src.models.order import Order

    OrderFactory._meta.model = Order
    OrderFactory._meta.sqlalchemy_session = session
    return OrderFactory.create_batch(count, **kwargs)


def create_batch_reviews(session, count=10, **kwargs):
    """Create a batch of test reviews."""
    from src.models.review import Review

    ReviewFactory._meta.model = Review
    ReviewFactory._meta.sqlalchemy_session = session
    return ReviewFactory.create_batch(count, **kwargs)


# Aliases for consistency with test files
ProductBookmarkFactory = BookmarkFactory
DesignStagingFactory = StagingFactory
