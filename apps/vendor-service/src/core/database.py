"""
Database configuration and session management for Vendor Service.

This module provides database connectivity using SQLAlchemy with TiDB compatibility.
"""

import sys
from pathlib import Path
from typing import AsyncGenerator, Generator

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import (AsyncSession, async_sessionmaker,
                                    create_async_engine)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session, sessionmaker

# Add the packages directory to the Python path
packages_path = Path(__file__).parent.parent.parent.parent.parent / "packages"
sys.path.insert(0, str(packages_path))

from src.core.config import get_settings

# Create declarative base for models
Base = declarative_base()

# Database engine and session
engine = None
async_engine = None
SessionLocal = None
AsyncSessionLocal = None


async def init_db() -> None:
    """Initialize database connection and create tables."""
    global engine, async_engine, SessionLocal, AsyncSessionLocal

    settings = get_settings()

    # Create sync engine with TiDB-compatible settings
    engine = create_engine(
        settings.get_database_url(), **settings.get_database_engine_kwargs()
    )

    # Create async engine
    async_engine = create_async_engine(
        settings.get_database_url(async_driver=True),
        **settings.get_database_engine_kwargs()
    )

    # Create session factories
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    AsyncSessionLocal = async_sessionmaker(
        bind=async_engine, class_=AsyncSession, expire_on_commit=False
    )

    # Import all models to ensure they're registered with Base
    from src.models import order, product, review, vendor  # noqa: F401

    # Create all tables (sync operation)
    Base.metadata.create_all(bind=engine)


def get_db() -> Generator[Session, None, None]:
    """
    Get database session.

    Yields:
        Database session
    """
    if SessionLocal is None:
        raise RuntimeError("Database not initialized. Call init_db() first.")

    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Get async database session.

    Yields:
        Async database session
    """
    if AsyncSessionLocal is None:
        raise RuntimeError("Database not initialized. Call init_db() first.")

    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


def get_engine():
    """Get the database engine."""
    if engine is None:
        raise RuntimeError("Database not initialized. Call init_db() first.")
    return engine


def get_async_engine():
    """Get the async database engine."""
    if async_engine is None:
        raise RuntimeError("Database not initialized. Call init_db() first.")
    return async_engine
