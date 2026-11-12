"""
Test configuration and shared fixtures for the vendor service tests.

Environment Variables:
    TEST_DATABASE_URL: Optional database URL for integration testing.
                      If not set, uses SQLite in-memory for fast unit tests.
                      Example: mysql+pymysql://user:pass@host:port/db?charset=utf8mb4
"""
import asyncio
import os
import sys
from typing import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

# Add packages to path for shared testing infrastructure
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", "..", "packages"))

from common.testing.database import create_test_engine, create_test_session


# Configure factories at module level
def configure_factories():
    """Configure factory models."""
    from src.models.bookmark import ProductBookmark
    from src.models.order import Order, OrderItem
    from src.models.product import Product
    from src.models.review import Review
    from src.models.staging import DesignStaging
    from src.models.vendor import Vendor
    from tests.factories import (BookmarkFactory, OrderFactory,
                                 OrderItemFactory, ProductFactory,
                                 ReviewFactory, StagingFactory, VendorFactory)

    # Set models and make factories non-abstract
    VendorFactory._meta.model = Vendor
    VendorFactory._meta.abstract = False
    ProductFactory._meta.model = Product
    ProductFactory._meta.abstract = False
    OrderFactory._meta.model = Order
    OrderFactory._meta.abstract = False
    OrderItemFactory._meta.model = OrderItem
    OrderItemFactory._meta.abstract = False
    ReviewFactory._meta.model = Review
    ReviewFactory._meta.abstract = False
    BookmarkFactory._meta.model = ProductBookmark
    BookmarkFactory._meta.abstract = False
    StagingFactory._meta.model = DesignStaging
    StagingFactory._meta.abstract = False


# Configure factories when module is imported
configure_factories()


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create an event loop for async tests."""
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="function")
def db_engine():
    """Create a test database engine with proper isolation."""
    # Check if TiDB integration testing is enabled
    test_db_url = os.getenv("TEST_DATABASE_URL")

    if test_db_url:
        # Use TiDB for integration testing
        engine = create_test_engine(test_db_url, echo=False)
    else:
        # Use SQLite in-memory for fast, isolated tests (default)
        engine = create_test_engine("sqlite:///:memory:", echo=False)

    return engine


@pytest.fixture
def db_session(db_engine):
    """Create a database session with proper cleanup and isolation."""
    from src.infrastructure.database import Base
    from tests.factories import (BookmarkFactory, OrderFactory,
                                 OrderItemFactory, ProductFactory,
                                 ReviewFactory, StagingFactory, VendorFactory)

    with create_test_session(db_engine, Base) as session:
        # Configure factories with session
        VendorFactory._meta.sqlalchemy_session = session
        ProductFactory._meta.sqlalchemy_session = session
        OrderFactory._meta.sqlalchemy_session = session
        OrderItemFactory._meta.sqlalchemy_session = session
        ReviewFactory._meta.sqlalchemy_session = session
        BookmarkFactory._meta.sqlalchemy_session = session
        StagingFactory._meta.sqlalchemy_session = session

        yield session


@pytest.fixture
def client(db_session):
    """Create a FastAPI test client with database session override."""
    # Import app here to avoid loading it during conftest import
    from src.infrastructure.database import get_db
    from src.main import app

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


@pytest.fixture
def test_vendor(db_session):
    """Create a test vendor."""
    from tests.factories import create_test_vendor

    return create_test_vendor(
        db_session, user_id=1, company_name="Test Vendor Co", email="vendor@example.com"
    )


@pytest.fixture
def test_product(db_session, test_vendor):
    """Create a test product."""
    from tests.factories import create_test_product

    return create_test_product(
        db_session, vendor_id=test_vendor.id, name="Test Product", price=99.99
    )


@pytest.fixture
def test_order(db_session, test_product):
    """Create a test order."""
    from tests.factories import create_test_order

    return create_test_order(db_session, customer_id=1, product_ids=[test_product.id])


@pytest.fixture
def auth_headers():
    """Create authorization headers for testing."""
    # This would normally create a JWT token
    return {"Authorization": "Bearer test-token-user-1"}


@pytest.fixture
def vendor_auth_headers(test_vendor):
    """Create vendor authorization headers for testing."""
    return {"Authorization": f"Bearer test-token-vendor-{test_vendor.user_id}"}


# Database cleanup fixture for integration tests
@pytest.fixture(scope="function")
def clean_db(db_session):
    """Ensure clean database state for each test."""
    yield db_session

    # Clean up any remaining data
    db_session.rollback()


# Performance testing fixture
@pytest.fixture
def performance_db_session(db_engine):
    """Create a session for performance testing with different configuration."""
    from src.infrastructure.database import Base
    from tests.factories import ProductFactory, VendorFactory

    SessionLocal = sessionmaker(bind=db_engine, autoflush=False, autocommit=False)

    # Create tables
    Base.metadata.create_all(bind=db_engine)

    session = SessionLocal()

    # Configure factories
    VendorFactory._meta.sqlalchemy_session = session
    ProductFactory._meta.sqlalchemy_session = session

    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=db_engine)


# Batch data creation fixtures
@pytest.fixture
def batch_vendors(db_session):
    """Create a batch of test vendors."""
    from tests.factories import create_batch_vendors

    return create_batch_vendors(db_session, count=10)


@pytest.fixture
def batch_products(db_session, test_vendor):
    """Create a batch of test products."""
    from tests.factories import create_batch_products

    return create_batch_products(db_session, vendor_id=test_vendor.id, count=20)
