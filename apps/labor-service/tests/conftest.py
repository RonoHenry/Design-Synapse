"""
Test Configuration and Fixtures for Labor Service

Provides database fixtures, test client setup, and common test utilities
following TDD principles.
"""

import asyncio
import os
from typing import AsyncGenerator, Generator

import httpx
import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from httpx import AsyncClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Set test environment before importing app modules
os.environ["ENVIRONMENT"] = "testing"
os.environ["DATABASE_URL"] = "sqlite:///./test_labor_service.db"
os.environ["JWT_SECRET_KEY"] = "test-secret-key-for-labor-service-testing-only"

from src.core.config import get_settings
from src.core.database import get_db
from src.main import app
# Import all models to ensure they're registered with Base
from src.models import (Booking, BookingMilestone, ProviderSkill, Quote,
                        Review, ServiceArea, ServiceProvider, ServiceRequest,
                        Skill, SkillCategory, SkillRequirement)
from src.models.base import Base

# Mock authentication functions for testing (defined early)
# Global variable to control which user is authenticated
_current_test_user_id = 1


def set_test_user_id(user_id: int):
    """Set the current test user ID for authentication mocks."""
    global _current_test_user_id
    _current_test_user_id = user_id


async def mock_get_current_user():
    """Mock authentication function for testing."""
    return {
        "id": _current_test_user_id,
        "email": "test@example.com",
        "role": "user",
        "auth_type": "test",
    }


async def mock_require_auth():
    """Mock require_auth dependency for testing."""
    return await mock_get_current_user()


async def mock_require_admin():
    """Mock require_admin dependency for testing."""
    return {
        "id": _current_test_user_id,
        "email": "admin@example.com",
        "role": "admin",
        "auth_type": "test",
    }


async def mock_require_provider():
    """Mock require_provider dependency for testing."""
    return {
        "id": _current_test_user_id,
        "email": "provider@example.com",
        "role": "provider",
        "auth_type": "test",
    }


async def mock_require_seeker():
    """Mock require_seeker dependency for testing."""
    return {
        "id": _current_test_user_id,
        "email": "seeker@example.com",
        "role": "seeker",
        "auth_type": "test",
    }


# Test database configuration
TEST_DATABASE_URL = "sqlite:///./test_labor_service.db"

# Create test engine with SQLite in-memory database
test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="function")
def db_session():
    """
    Create a fresh database session for each test.

    This fixture:
    1. Creates all tables
    2. Provides a clean database session
    3. Rolls back all changes after the test
    4. Drops all tables for cleanup
    """
    # Create tables
    Base.metadata.create_all(bind=test_engine, checkfirst=True)

    # Create session
    session = TestingSessionLocal()

    try:
        yield session
    finally:
        session.close()
        # Drop all tables for clean state
        Base.metadata.drop_all(bind=test_engine)


@pytest.fixture(scope="function")
def client(db_session) -> Generator[TestClient, None, None]:
    """
    Create a test client with database dependency override.

    This fixture provides a FastAPI test client with the database
    dependency overridden to use the test database session.
    """
    from src.api.dependencies import (get_current_user, require_admin,
                                      require_auth, require_provider,
                                      require_seeker)

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    # Override dependencies
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = mock_get_current_user
    app.dependency_overrides[require_auth] = mock_require_auth
    app.dependency_overrides[require_admin] = mock_require_admin
    app.dependency_overrides[require_provider] = mock_require_provider
    app.dependency_overrides[require_seeker] = mock_require_seeker

    with TestClient(app) as test_client:
        yield test_client

    # Clean up dependency override
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def async_client(db_session):
    """
    Create an async test client for testing async endpoints.

    This fixture provides an async HTTP client for testing
    async FastAPI endpoints with database dependency override.
    """
    from src.api.dependencies import (get_current_user, require_admin,
                                      require_auth, require_provider,
                                      require_seeker)

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    # Override dependencies
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = mock_get_current_user
    app.dependency_overrides[require_auth] = mock_require_auth
    app.dependency_overrides[require_admin] = mock_require_admin
    app.dependency_overrides[require_provider] = mock_require_provider
    app.dependency_overrides[require_seeker] = mock_require_seeker

    async with AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        yield client

    # Clean up dependency override
    app.dependency_overrides.clear()


@pytest.fixture
def test_settings():
    """
    Provide test-specific settings.

    Returns application settings configured for testing environment.
    """
    settings = get_settings()
    settings.environment = "testing"
    settings.debug = True
    return settings


# Common test data fixtures
@pytest.fixture
def sample_provider_data():
    """Sample service provider data for testing."""
    return {
        "user_id": 1,
        "individual_name": "John Smith",
        "business_name": "Smith Construction",
        "provider_type": "business",
        "description": "Professional construction services with 10+ years experience",
        "experience_years": 10,
        "verification_status": "pending",
    }


@pytest.fixture
def sample_skill_category_data():
    """Sample skill category data for testing."""
    return {
        "name": "Construction",
        "description": "General construction and building skills",
        "sort_order": 1,
        "is_active": True,
    }


@pytest.fixture
def sample_skill_data():
    """Sample skill data for testing."""
    return {
        "category_id": 1,
        "name": "Carpentry",
        "description": "Wood working and framing skills",
        "requires_certification": False,
        "is_active": True,
    }


@pytest.fixture
def sample_service_area_data():
    """Sample service area data for testing."""
    return {
        "provider_id": 1,
        "center_latitude": 40.7128,
        "center_longitude": -74.0060,
        "radius_miles": 25,
        "travel_rate": 0.50,
        "area_name": "New York Metro Area",
        "is_primary": True,
        "is_active": True,
    }


# Authentication fixtures for testing protected endpoints
@pytest.fixture
def auth_headers():
    """Sample authentication headers for testing protected endpoints."""
    return {
        "Authorization": "Bearer test_jwt_token",
        "Content-Type": "application/json",
    }


@pytest.fixture
def mock_user_data():
    """Mock user data for authentication testing."""
    return {
        "id": 1,
        "email": "test@example.com",
        "username": "testuser",
        "is_active": True,
        "roles": ["service_provider"],
    }


# Database helper fixtures
@pytest.fixture
def db_helpers(db_session):
    """
    Database helper functions for test setup.

    Provides utility functions for creating test data in the database.
    """

    class DBHelpers:
        def __init__(self, session):
            self.session = session

        def create_skill_category(self, **kwargs):
            """Create a skill category in the test database."""
            from src.models.service_provider import SkillCategory

            defaults = {
                "name": "Test Category",
                "description": "Test category description",
                "sort_order": 1,
                "is_active": True,
            }
            defaults.update(kwargs)

            category = SkillCategory(**defaults)
            self.session.add(category)
            self.session.commit()
            self.session.refresh(category)
            return category

        def create_skill(self, **kwargs):
            """Create a skill in the test database."""
            from src.models.service_provider import Skill

            # Ensure we have a category
            if "category_id" not in kwargs:
                category = self.create_skill_category()
                kwargs["category_id"] = category.id

            defaults = {
                "name": "Test Skill",
                "description": "Test skill description",
                "requires_certification": False,
                "is_active": True,
            }
            defaults.update(kwargs)

            skill = Skill(**defaults)
            self.session.add(skill)
            self.session.commit()
            self.session.refresh(skill)
            return skill

        def create_service_provider(self, **kwargs):
            """Create a service provider in the test database."""
            from src.models.service_provider import ServiceProvider

            defaults = {
                "user_id": 1,
                "individual_name": "Test Provider",
                "provider_type": "individual",
                "description": "Test provider description",
                "experience_years": 5,
                "verification_status": "pending",
            }
            defaults.update(kwargs)

            provider = ServiceProvider(**defaults)
            self.session.add(provider)
            self.session.commit()
            self.session.refresh(provider)
            return provider

    return DBHelpers(db_session)


# Factory configuration
@pytest.fixture(autouse=True)
def configure_factories(db_session):
    """Configure factory_boy to use the test database session."""
    import factory

    # Import all factories
    from tests.factories import (BookingFactory, BookingMilestoneFactory,
                                 ProviderSkillFactory, QuoteFactory,
                                 ReviewFactory, ServiceAreaFactory,
                                 ServiceProviderFactory, ServiceRequestFactory,
                                 SkillCategoryFactory, SkillFactory,
                                 SkillRequirementFactory)

    # Configure all SQLAlchemy factories to use the test session
    for factory_class in [
        ServiceProviderFactory,
        SkillCategoryFactory,
        SkillFactory,
        ProviderSkillFactory,
        ServiceAreaFactory,
        ServiceRequestFactory,
        SkillRequirementFactory,
        QuoteFactory,
        BookingFactory,
        BookingMilestoneFactory,
        ReviewFactory,
    ]:
        factory_class._meta.sqlalchemy_session = db_session


@pytest.fixture
def test_data(db_session):
    """Create basic test data for integration tests."""
    from decimal import Decimal

    from src.models.service_request import RequestStatus

    from tests.factories import (BookingFactory, QuoteFactory, ReviewFactory,
                                 ServiceProviderFactory, ServiceRequestFactory,
                                 SkillCategoryFactory, SkillFactory)

    # Create basic entities with predictable IDs
    skill_category = SkillCategoryFactory(id=1, name="Construction")
    skill = SkillFactory(id=1, category=skill_category, name="Electrical Work")

    provider = ServiceProviderFactory(id=1, user_id=1)
    # Create a second provider for existing quote to avoid conflicts
    provider2 = ServiceProviderFactory(id=2, user_id=2)
    service_request = ServiceRequestFactory(
        id=1,
        seeker_id=1,
        status=RequestStatus.ACTIVE,
        budget_min=Decimal("1000.00"),
        budget_max=Decimal("3000.00"),  # Allow for $2000 quote
    )

    # Create existing quote with provider2 to match booking
    quote = QuoteFactory(
        id=1,
        request_id=service_request.id,
        provider_id=provider2.id,  # Use provider2 to match booking
        total_cost=1500.00,
    )

    booking = BookingFactory(
        id=1,
        service_request_id=service_request.id,
        quote_id=quote.id,
        provider_id=2,  # Provider 2 provides the service (user 2 is the provider)
        client_id=1,  # User 1 is the client/seeker who can review the provider
        status="COMPLETED",  # Set to COMPLETED so reviews can be submitted
    )

    # Create a review for testing - user 1 can respond to this review since they are the reviewee
    review = ReviewFactory(
        id=1,
        booking_id=1,  # Use the same booking for consistency
        reviewer_id=2,  # Provider 2 reviews seeker (user 1)
        reviewee_id=1,  # User 1 is the reviewee, so they can respond to this review
    )

    db_session.commit()

    return {
        "provider": provider,
        "provider2": provider2,
        "service_request": service_request,
        "quote": quote,
        "booking": booking,
        "review": review,
        "skill_category": skill_category,
        "skill": skill,
    }


# Pytest configuration
def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line("markers", "unit: mark test as a unit test")
    config.addinivalue_line("markers", "integration: mark test as an integration test")
    config.addinivalue_line("markers", "tdd: mark test as following TDD principles")
    config.addinivalue_line("markers", "slow: mark test as slow running")
    config.addinivalue_line(
        "markers", "external: mark test as requiring external services"
    )
