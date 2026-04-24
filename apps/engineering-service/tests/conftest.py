"""Pytest configuration and fixtures for Engineering Service tests."""

import asyncio
import os
from typing import AsyncGenerator

import pytest
from hypothesis import Verbosity, settings
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool
from src.core.config import settings as app_settings
from src.core.database import Base

# Configure Hypothesis settings
settings.register_profile("dev", max_examples=10, verbosity=Verbosity.verbose)
settings.register_profile("ci", max_examples=100, verbosity=Verbosity.normal)
settings.register_profile("debug", max_examples=10, verbosity=Verbosity.debug)

# Load the appropriate profile
settings.load_profile("dev")


@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="function")
async def test_db_engine():
    """Create a test database engine."""
    test_db_url = os.environ.get("TEST_DATABASE_URL", "sqlite+aiosqlite:///:memory:")

    engine_kwargs = {"echo": False}
    if test_db_url != "sqlite+aiosqlite:///:memory:":
        engine_kwargs["poolclass"] = NullPool

    engine = create_async_engine(test_db_url, **engine_kwargs)

    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    # Drop all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest.fixture(scope="function")
async def test_db_session(
    test_db_engine,
) -> AsyncGenerator[AsyncSession, None]:
    """Create a test database session."""
    async_session = sessionmaker(
        test_db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with async_session() as session:
        yield session
        await session.rollback()


@pytest.fixture(scope="function")
def override_get_db(test_db_session):
    """Override the get_db dependency for testing."""

    async def _override_get_db():
        yield test_db_session

    return _override_get_db
