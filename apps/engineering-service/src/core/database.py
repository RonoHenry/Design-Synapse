"""Database configuration and session management for Engineering Service."""

from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (AsyncEngine, AsyncSession,
                                    async_sessionmaker, create_async_engine)
from sqlalchemy.orm import declarative_base
from sqlalchemy.pool import NullPool

from .config import settings

# Base class for SQLAlchemy models
Base = declarative_base()

# Global engine instance
_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def get_engine() -> AsyncEngine:
    """Get or create the database engine.

    Returns:
        AsyncEngine: SQLAlchemy async engine instance
    """
    global _engine
    if _engine is None:
        _engine = create_async_engine(
            settings.database_url,
            echo=settings.debug,
            pool_size=settings.database_pool_size,
            max_overflow=settings.database_max_overflow,
            pool_timeout=settings.database_pool_timeout,
            pool_recycle=settings.database_pool_recycle,
            pool_pre_ping=True,  # Verify connections before using
            # TiDB/MySQL specific settings
            connect_args={
                "charset": "utf8mb4",
                "ssl": {"ssl_mode": "PREFERRED"},
            },
        )
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Get or create the session factory.

    Returns:
        async_sessionmaker: Session factory for creating database sessions
    """
    global _session_factory
    if _session_factory is None:
        engine = get_engine()
        _session_factory = async_sessionmaker(
            engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autocommit=False,
            autoflush=False,
        )
    return _session_factory


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for getting database sessions.

    Yields:
        AsyncSession: Database session
    """
    session_factory = get_session_factory()
    async with session_factory() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db() -> None:
    """Initialize database connection and create tables if needed."""
    engine = get_engine()
    # Import all models to ensure they're registered with Base
    from ..models import calculation_sheet  # noqa: F401
    from ..models import civil_design  # noqa: F401
    from ..models import compliance_report  # noqa: F401
    from ..models import audit_log, mep_design, structural_design  # noqa: F401

    async with engine.begin() as conn:
        # Create all tables (in production, use Alembic migrations)
        await conn.run_sync(Base.metadata.create_all)


async def close_db() -> None:
    """Close database connections."""
    global _engine, _session_factory
    if _engine is not None:
        await _engine.dispose()
        _engine = None
        _session_factory = None


def get_test_engine() -> AsyncEngine:
    """Create a test database engine with NullPool.

    Returns:
        AsyncEngine: Test database engine
    """
    return create_async_engine(
        settings.database_url,
        echo=settings.debug,
        poolclass=NullPool,  # No connection pooling for tests
        connect_args={
            "charset": "utf8mb4",
        },
    )


async def get_test_session() -> AsyncGenerator[AsyncSession, None]:
    """Get a test database session.

    Yields:
        AsyncSession: Test database session
    """
    engine = get_test_engine()
    session_factory = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with session_factory() as session:
        try:
            yield session
        finally:
            await session.close()
            await engine.dispose()
