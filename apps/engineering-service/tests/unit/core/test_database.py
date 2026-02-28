"""Unit tests for database configuration."""

import pytest
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession
from src.core.database import (close_db, get_db, get_engine,
                               get_session_factory, get_test_engine)


@pytest.mark.unit
class TestDatabaseConfiguration:
    """Test database configuration and connection management."""

    def test_get_engine_returns_engine(self):
        """Test that get_engine returns an AsyncEngine instance."""
        engine = get_engine()
        assert isinstance(engine, AsyncEngine)
        assert engine is not None

    def test_get_engine_returns_same_instance(self):
        """Test that get_engine returns the same instance (singleton)."""
        engine1 = get_engine()
        engine2 = get_engine()
        assert engine1 is engine2

    def test_get_session_factory_returns_factory(self):
        """Test that get_session_factory returns a session factory."""
        factory = get_session_factory()
        assert factory is not None
        assert callable(factory)

    @pytest.mark.asyncio
    async def test_get_db_yields_session(self):
        """Test that get_db yields an AsyncSession."""
        async for session in get_db():
            assert isinstance(session, AsyncSession)
            assert session is not None
            break

    @pytest.mark.asyncio
    async def test_get_db_session_lifecycle(self):
        """Test that get_db manages session lifecycle correctly."""
        # Test that we can use the session within the context
        async for session in get_db():
            assert isinstance(session, AsyncSession)
            # Session should be usable
            assert session.bind is not None
            break

    def test_get_test_engine_returns_engine(self):
        """Test that get_test_engine returns an AsyncEngine."""
        engine = get_test_engine()
        assert isinstance(engine, AsyncEngine)
        assert engine is not None

    def test_get_test_engine_returns_new_instance(self):
        """Test that get_test_engine returns new instances."""
        engine1 = get_test_engine()
        engine2 = get_test_engine()
        # Test engines should be different instances (no singleton)
        assert engine1 is not engine2

    @pytest.mark.asyncio
    async def test_close_db_disposes_engine(self):
        """Test that close_db properly disposes the engine."""
        # Get engine to initialize it
        engine = get_engine()
        assert engine is not None

        # Close database
        await close_db()

        # After closing, getting engine should create a new instance
        new_engine = get_engine()
        assert new_engine is not engine


@pytest.mark.unit
class TestDatabaseConnectionSettings:
    """Test database connection settings."""

    def test_engine_has_pool_configuration(self):
        """Test that engine is configured with connection pool."""
        engine = get_engine()
        pool = engine.pool

        # Verify pool is configured (not NullPool)
        assert pool is not None
        assert hasattr(pool, "size")

    def test_test_engine_has_null_pool(self):
        """Test that test engine uses NullPool."""
        from sqlalchemy.pool import NullPool

        engine = get_test_engine()
        assert isinstance(engine.pool, NullPool)
