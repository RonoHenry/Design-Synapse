"""Reset alembic version table."""
import os
import sys

sys.path.insert(0, os.path.abspath("."))

from sqlalchemy import create_engine, text

from packages.common.config.database import DatabaseConfig

config = DatabaseConfig()
engine = create_engine(
    config.get_connection_url(async_driver=False), **config.get_engine_kwargs()
)

with engine.connect() as conn:
    conn.execute(text("DROP TABLE IF EXISTS alembic_version"))
    conn.commit()
    print("✅ Dropped alembic_version table")
