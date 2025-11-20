"""
Database configuration and session management for Vendor Service.

This module provides database connectivity using SQLAlchemy with TiDB compatibility.
"""

import sys
from pathlib import Path
from typing import Generator

from sqlalchemy import create_engine
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
SessionLocal = None


def init_db() -> None:
    """Initialize database connection and create tables."""
    global engine, SessionLocal

    settings = get_settings()

    # Create engine with TiDB-compatible settings
    engine = create_engine(
        settings.get_database_url(), **settings.get_database_engine_kwargs()
    )

    # Create session factory
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    # Import all models to ensure they're registered with Base
    # This will be uncommented as models are created
    # from src.models import vendor, product, order, review  # noqa: F401

    # Create all tables
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


def get_engine():
    """Get the database engine."""
    if engine is None:
        raise RuntimeError("Database not initialized. Call init_db() first.")
    return engine
