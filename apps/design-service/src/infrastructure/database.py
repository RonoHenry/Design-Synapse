"""
Database configuration and session management for Design Service.

This module provides database connectivity using TiDB with proper connection
pooling, session management, and dependency injection for FastAPI.
"""

from contextlib import contextmanager
from typing import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from ..core.config import get_settings

# Create declarative base for models
Base = declarative_base()


def create_db_engine():
    """
    Create a database engine with TiDB connection and pooling configuration.

    Returns:
        SQLAlchemy Engine configured for TiDB
    """
    settings = get_settings()

    # Get connection URL and engine kwargs from config
    database_url = settings.get_database_url(async_driver=False)
    engine_kwargs = settings.get_database_engine_kwargs()

    return create_engine(database_url, **engine_kwargs)


# Global engine and session factory (lazy initialization)
_engine = None
_SessionLocal = None


def get_engine():
    """Get or create the global database engine."""
    global _engine
    if _engine is None:
        _engine = create_db_engine()
    return _engine


def get_session_local():
    """Get or create the global session factory."""
    global _SessionLocal
    if _SessionLocal is None:
        engine = get_engine()
        _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return _SessionLocal


def get_db() -> Iterator[Session]:
    """
    FastAPI dependency for database session management.

    Provides a database session that is automatically closed after use.
    Use with FastAPI's Depends() for automatic dependency injection.

    Yields:
        Database session

    Example:
        @app.get("/designs")
        def get_designs(db: Session = Depends(get_db)):
            return db.query(Design).all()
    """
    SessionLocal = get_session_local()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def get_db_context() -> Iterator[Session]:
    """
    Context manager for database session management.

    Use this for non-FastAPI contexts where you need a database session.

    Yields:
        Database session

    Example:
        with get_db_context() as db:
            designs = db.query(Design).all()
    """
    SessionLocal = get_session_local()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
