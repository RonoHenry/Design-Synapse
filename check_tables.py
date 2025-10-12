"""Check if tables exist in TiDB."""
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
    result = conn.execute(text("SHOW TABLES"))
    tables = result.fetchall()

    if tables:
        print("Tables in database:")
        for table in tables:
            print(f"  - {table[0]}")
    else:
        print("No tables found in database")

    # Check alembic_version table
    result = conn.execute(text("SELECT * FROM alembic_version"))
    versions = result.fetchall()

    if versions:
        print("\nAlembic versions:")
        for version in versions:
            print(f"  - {version[0]}")
    else:
        print("\nNo alembic version found")
