"""Test configuration and fixtures for the project service.

Environment Variables:
    TEST_DATABASE_URL: Optional database URL for integration testing.
                      If not set, uses SQLite in-memory for fast unit tests.
                      Example: mysql+pymysql://user:pass@host:port/db?charset=utf8mb4
"""

import asyncio
import os
from typing import Any, AsyncGenerator, Dict, Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool
from src.infrastructure.database import Base, get_db
from src.main import app
from src.models.comment import Comment
from src.models.project import Project

# Test database URL for SQLite in-memory database (default)
SQLALCHEMY_DATABASE_URL = os.getenv("TEST_DATABASE_URL", "sqlite:///:memory:")
TEST_ASYNC_DATABASE_URL = os.getenv(
    "TEST_ASYNC_DATABASE_URL", "sqlite+aiosqlite:///:memory:"
)

# Create the test engine with appropriate configuration
if "sqlite" in SQLALCHEMY_DATABASE_URL:
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
else:
    # MySQL/TiDB configuration
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL,
        pool_pre_ping=True,
        pool_recycle=3600,
    )

# Create async engine for async tests
if "sqlite" in TEST_ASYNC_DATABASE_URL:
    async_engine = create_async_engine(
        TEST_ASYNC_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
else:
    # MySQL/TiDB async configuration
    async_engine = create_async_engine(
        TEST_ASYNC_DATABASE_URL,
        pool_pre_ping=True,
        pool_recycle=3600,
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


@pytest.fixture
def test_project(db: Session) -> Project:
    """Create a test project."""
    project = Project(
        name="Test Project",
        description="Test project description",
        owner_id=1,
        status="active",
    )
    db.add(project)
    db.commit()
    return project  # No refresh needed as the object is still attached


@pytest.fixture
def test_comment(db: Session, test_project: Project) -> Comment:
    """Create a test comment."""
    comment = Comment(
        content="Test comment",
        project_id=test_project.id,
        author_id=1,
    )
    db.add(comment)
    db.commit()
    return comment  # No refresh needed as the object is still attached
