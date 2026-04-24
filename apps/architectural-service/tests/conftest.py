"""Pytest configuration and fixtures."""

import asyncio
import os
import ssl
from typing import AsyncGenerator, Generator
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

import httpx
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


def _prepare_test_engine_args(database_url: str) -> tuple[str, dict]:
    """Return (clean_url, connect_args) for asyncmy SSL handling."""
    if not database_url.startswith("mysql+asyncmy://"):
        return database_url, {}

    parsed = urlparse(database_url)
    query_params = parse_qs(parsed.query, keep_blank_values=True)

    ssl_ca = None
    for key in ("ssl_ca", "ssl_verify_cert", "ssl_verify_identity"):
        val = query_params.pop(key, None)
        if key == "ssl_ca" and val:
            ssl_ca = val[0]

    new_query = urlencode({k: v[0] for k, v in query_params.items()}, doseq=False)
    clean_url = urlunparse(parsed._replace(query=new_query))

    connect_args = {}
    if ssl_ca:
        ssl_ctx = ssl.create_default_context(cafile=ssl_ca)
        connect_args["ssl"] = ssl_ctx

    return clean_url, connect_args


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

    # Use TEST_DATABASE_URL if set (e.g. TiDB), otherwise fall back to SQLite
    test_database_url = os.environ.get(
        "TEST_DATABASE_URL", "sqlite+aiosqlite:///test_architectural.db"
    )
    using_sqlite = test_database_url.startswith("sqlite")

    clean_url, connect_args = _prepare_test_engine_args(test_database_url)

    engine = create_async_engine(
        clean_url,
        echo=False,
        poolclass=NullPool,
        connect_args=connect_args,
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()

    # Clean up test database file only when using SQLite
    if using_sqlite and os.path.exists("test_architectural.db"):
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

    async with AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest.fixture
def sample_uuid():
    """Generate a sample UUID for testing."""
    from uuid import uuid4

    return uuid4()


@pytest.fixture
def db_session(test_session):
    """Alias for test_session to match property test expectations."""
    return test_session


@pytest.fixture
def design_repository_factory():
    """Factory for creating DesignRepository instances."""
    from src.repositories.design_repository import DesignRepository

    def _create_repository(session):
        return DesignRepository(session)

    return _create_repository


@pytest.fixture
def mock_project_client():
    """Mock ProjectServiceClient for testing."""
    from unittest.mock import AsyncMock, MagicMock

    from src.infrastructure.project_service_client import ProjectValidation

    mock_client = AsyncMock()

    # Mock validate_project to always return valid
    validation = ProjectValidation(
        exists=True, user_has_access=True, project_status="active"
    )
    mock_client.validate_project.return_value = validation

    # Mock log_activity to succeed
    mock_client.log_activity.return_value = None

    return mock_client
