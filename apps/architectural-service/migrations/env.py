"""Alembic environment configuration for async migrations."""

import asyncio
import ssl
from logging.config import fileConfig
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import create_async_engine
from src.core.config import settings
# Import the Base and all models
from src.core.database import Base
# Import all models to ensure they're registered with Base.metadata
from src.models import CollaborationSession  # noqa: F401
from src.models import StructuralAnalysis  # noqa: F401
from src.models import (AccessibilityCheck, ComplianceCheck, Design,
                        DesignVersion, Drawing, EnergyAnalysis,
                        MaterialSpecification, SpacePlanning)

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)


def _build_asyncmy_url_and_connect_args(database_url: str):
    """Parse a DATABASE_URL and return (clean_url, connect_args) for asyncmy.

    asyncmy does not accept ssl_verify_cert / ssl_verify_identity as URL
    query parameters — it only accepts an ``ssl`` dict via connect_args.
    This helper strips those params from the URL and builds the correct
    connect_args dict instead.
    """
    parsed = urlparse(database_url)
    query_params = parse_qs(parsed.query, keep_blank_values=True)

    ssl_ca = None
    # Extract SSL-related query params that asyncmy doesn't understand
    for key in ("ssl_ca", "ssl_verify_cert", "ssl_verify_identity"):
        val = query_params.pop(key, None)
        if key == "ssl_ca" and val:
            ssl_ca = val[0]

    # Rebuild the URL without the stripped SSL params
    new_query = urlencode({k: v[0] for k, v in query_params.items()}, doseq=False)
    clean_parsed = parsed._replace(query=new_query)
    clean_url = urlunparse(clean_parsed)

    connect_args = {}
    if ssl_ca:
        ssl_ctx = ssl.create_default_context(cafile=ssl_ca)
        connect_args["ssl"] = ssl_ctx

    return clean_url, connect_args


# Build the URL and connect_args for asyncmy
_raw_url = settings.database_url
if _raw_url.startswith("mysql+asyncmy://"):
    _db_url, _connect_args = _build_asyncmy_url_and_connect_args(_raw_url)
else:
    _db_url = _raw_url
    _connect_args = {}

# Set the SQLAlchemy URL from settings (cleaned of asyncmy-incompatible params)
config.set_main_option("sqlalchemy.url", _db_url)

# add your model's MetaData object here
# for 'autogenerate' support
target_metadata = Base.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """Run migrations with the given connection."""
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Run migrations in 'online' mode with async engine."""
    connectable = create_async_engine(
        _db_url,
        poolclass=pool.NullPool,
        connect_args=_connect_args,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    On Windows, asyncio defaults to ProactorEventLoop which does not support
    SSL with asyncmy. We switch to SelectorEventLoop for the migration run.
    """
    import sys

    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
