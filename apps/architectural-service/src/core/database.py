"""Database configuration and session management."""

import ssl
from typing import AsyncGenerator
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

from sqlalchemy.ext.asyncio import (AsyncSession, async_sessionmaker,
                                    create_async_engine)
from sqlalchemy.orm import declarative_base
from sqlalchemy.pool import NullPool
from src.core.config import settings


def _prepare_engine_args(database_url: str) -> tuple[str, dict]:
    """Return (clean_url, connect_args) for the given database URL.

    For mysql+asyncmy URLs, strips pymysql-specific SSL query params
    (ssl_verify_cert, ssl_verify_identity) and converts ssl_ca into an
    ssl.SSLContext passed via connect_args, which is what asyncmy expects.
    """
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


_db_url, _connect_args = _prepare_engine_args(settings.database_url)

# Create async engine
engine = create_async_engine(
    _db_url,
    echo=settings.debug,
    pool_size=settings.database_pool_size,
    max_overflow=settings.database_max_overflow,
    pool_timeout=settings.database_pool_timeout,
    pool_recycle=settings.database_pool_recycle,
    pool_pre_ping=True,
    poolclass=NullPool if "sqlite" in settings.database_url else None,
    connect_args=_connect_args,
)

# Create async session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

# Base class for models
Base = declarative_base()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency for getting async database sessions.

    Yields:
        AsyncSession: Database session
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db() -> None:
    """No-op: schema is managed by Alembic migrations."""
    pass


async def close_db() -> None:
    """Close database connections."""
    await engine.dispose()
