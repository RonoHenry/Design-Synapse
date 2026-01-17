"""Pytest configuration and fixtures."""

import asyncio
from typing import AsyncGenerator, Generator

import pytest
# Then import all models to register them with Base.metadata
import src.models  # noqa: F401
from httpx import AsyncClient
from hypothesis import settings as hypothesis_settings
from sqlalchemy.ext.asyncio import (AsyncSession, async_sessionmaker,
                                    create_async_engine)
from sqlalchemy.pool import NullPool
# Import Base first
from src.core.database import Base, get_db
from src.main import app

hypothesis_settings.register_profile("dev", max_examples=10)
hypothesis_settings.register_profile("ci", max_examples=100, deadline=10000)
hypothesis_settings.load_profile("dev")


@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="function")
async def test_engine():
    """Create a test database engine."""
    # Import models to register them with Base.metadata
    from src.models import AccessibilityCheck  # noqa: F401
    from src.models import (CollaborationSession, ComplianceCheck, Design,
                            DesignVersion, Drawing, EnergyAnalysis,
                            MaterialSpecification, SpacePlanning,
                            StructuralAnalysis)

    # Use file-based SQLite for tests (async in-memory has issues)
    test_database_url = "sqlite+aiosqlite:///test_architectural.db"

    engine = create_async_engine(
        test_database_url,
        echo=False,
        poolclass=NullPool,
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()

    # Clean up test database file
    import os

    if os.path.exists("test_architectural.db"):
        os.remove("test_architectural.db")


@pytest.fixture(scope="function")
async def test_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create a test database session."""
    # Ensure tables are created before creating session
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async_session = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with async_session() as session:
        yield session

    # Clean up tables after session
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture(scope="function")
async def client(test_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Create a test HTTP client."""

    async def override_get_db():
        yield test_session

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest.fixture
def sample_uuid():
    """Generate a sample UUID for testing."""
    from uuid import uuid4

    return uuid4()
