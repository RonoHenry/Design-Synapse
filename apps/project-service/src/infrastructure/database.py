"""
Database configuration and connection pooling.
"""
from contextlib import contextmanager
from functools import lru_cache
from typing import Iterator

from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import QueuePool


class DatabaseSettings(BaseSettings):
    """Database configuration settings."""

    # Service identification
    service_name: str = "project"

    # Database connection
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_user: str = "design_synapse_user"
    postgres_password: str = "design_synapse_password"
    postgres_db: str = ""  # Will be set based on service_name

    # Connection pool settings
    pool_size: int = 5
    max_overflow: int = 10
    pool_timeout: int = 30
    pool_recycle: int = 1800  # Recycle connections after 30 minutes

    model_config = SettingsConfigDict(env_file=".env", extra="allow")

    def __init__(self, **kwargs):
        """Initialize settings and set postgres_db based on service name."""
        super().__init__(**kwargs)
        self.postgres_db = f"design_synapse_{self.service_name}_db"

    @property
    def database_url(self) -> str:
        """Get the database URL with the service-specific database name."""
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


@lru_cache
def get_database_settings() -> DatabaseSettings:
    """Get database settings singleton."""
    return DatabaseSettings()


def create_db_engine():
    """Create a database engine with connection pooling."""
    settings = get_database_settings()

    return create_engine(
        settings.database_url,
        poolclass=QueuePool,
        pool_size=settings.pool_size,
        max_overflow=settings.max_overflow,
        pool_timeout=settings.pool_timeout,
        pool_recycle=settings.pool_recycle,
        pool_pre_ping=True,  # Verify connections before using them
        echo_pool=True,  # Log pool checkouts/checkins
    )


engine = create_db_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


@contextmanager
def get_db() -> Iterator[Session]:
    """Get a database session with automatic cleanup."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()