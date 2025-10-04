"""
Test configuration and shared fixtures for the user service tests.
"""
import pytest
import asyncio
import os
import sys
from typing import Generator
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

# Add packages to path for shared testing infrastructure
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..', 'packages'))

from common.testing.database import create_test_engine, create_test_session
from common.testing.fixtures import event_loop, mock_llm_service, mock_vector_service
from src.infrastructure.database import Base, get_db
from factories import UserFactory, RoleFactory, create_test_user, create_test_role


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
    # Use SQLite in-memory for fast, isolated tests
    engine = create_test_engine("sqlite:///:memory:", echo=False)
    
    # Enable foreign key constraints for SQLite
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()
    
    return engine


@pytest.fixture
def db_session(db_engine):
    """Create a database session with proper cleanup and isolation."""
    with create_test_session(db_engine, Base) as session:
        # Configure factories to use this session
        UserFactory._meta.sqlalchemy_session = session
        RoleFactory._meta.sqlalchemy_session = session
        
        yield session


@pytest.fixture
def client(db_session):
    """Create a FastAPI test client with database session override."""
    # Import app here to avoid loading it during conftest import
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
def test_user(db_session):
    """Create a test user for authentication tests."""
    return create_test_user(
        db_session,
        email="test@example.com",
        username="testuser",
        password="testpass123",
        first_name="Test",
        last_name="User"
    )


@pytest.fixture
def test_admin_user(db_session):
    """Create a test admin user."""
    from .factories import create_test_admin_user
    return create_test_admin_user(
        db_session,
        email="admin@example.com",
        username="adminuser",
        password="adminpass123",
        first_name="Admin",
        last_name="User"
    )


@pytest.fixture
def test_role(db_session):
    """Create a test role."""
    return create_test_role(
        db_session,
        name="test_role",
        description="Test role for testing"
    )


@pytest.fixture
def auth_headers(test_user):
    """Create authorization headers for testing."""
    # This would normally create a JWT token, but for testing we'll use a simple approach
    # In a real implementation, you'd use your JWT creation logic here
    return {"Authorization": f"Bearer test-token-{test_user.id}"}


@pytest.fixture
def admin_auth_headers(test_admin_user):
    """Create admin authorization headers for testing."""
    return {"Authorization": f"Bearer admin-token-{test_admin_user.id}"}


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
    SessionLocal = sessionmaker(bind=db_engine, autoflush=False, autocommit=False)
    session = SessionLocal()
    
    # Configure factories
    UserFactory._meta.sqlalchemy_session = session
    RoleFactory._meta.sqlalchemy_session = session
    
    try:
        yield session
    finally:
        session.close()


# Batch data creation fixtures
@pytest.fixture
def batch_users(db_session):
    """Create a batch of test users."""
    from .factories import create_batch_users
    return create_batch_users(db_session, count=10)


@pytest.fixture
def batch_roles(db_session):
    """Create a batch of test roles."""
    from .factories import create_batch_roles
    return create_batch_roles(db_session, count=5)
