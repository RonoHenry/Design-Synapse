"""Test configuration and fixtures for the project service."""

import asyncio
from typing import AsyncGenerator, Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool
from src.infrastructure.database import Base, get_db
from src.main import app

# Test database URL for SQLite in-memory database
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
TEST_ASYNC_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

# Create the SQLite engine for testing
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

# Create async engine for async tests
async_engine = create_async_engine(
    TEST_ASYNC_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

# Create test session factories
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
AsyncTestSessionLocal = sessionmaker(
    class_=AsyncSession, autocommit=False, autoflush=False, bind=async_engine
)


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create an event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="function")
async def async_db() -> AsyncGenerator[AsyncSession, None]:
    """Create tables and provide async session for testing."""
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncTestSessionLocal() as session:
        yield session

    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture(scope="function")
def db() -> Generator[Session, None, None]:
    """Create tables and provide session for testing."""
    Base.metadata.create_all(bind=engine)
    session = TestSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db: Session) -> Generator[TestClient, None, None]:
    """Create a test client with database session."""

    def override_get_db():
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        test_client.headers["Accept"] = "application/vnd.design-synapse.v1+json"
        yield test_client
    app.dependency_overrides.clear()