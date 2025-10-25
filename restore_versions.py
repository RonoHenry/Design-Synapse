"""Restore all alembic versions."""
import os
import sys
from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, os.path.abspath("."))

from sqlalchemy import create_engine, text
from packages.common.config.database import DatabaseConfig

config = DatabaseConfig()
engine = create_engine(
    config.get_connection_url(async_driver=False), **config.get_engine_kwargs()
)

# All service versions
all_versions = ['a1b2c3d4e5f6', 'b2c3d4e5f6a7', 'b6576f89ece0', 'c3d4e5f6a7b8']

with engine.connect() as conn:
    for version in all_versions:
        # Check if version already exists
        result = conn.execute(
            text("SELECT COUNT(*) FROM alembic_version WHERE version_num = :version"),
            {"version": version}
        )
        if result.scalar() == 0:
            conn.execute(
                text("INSERT INTO alembic_version (version_num) VALUES (:version)"),
                {"version": version}
            )
            print(f"Added version: {version}")
        else:
            print(f"Version already exists: {version}")
    conn.commit()

print("\nFinal alembic versions:")
with engine.connect() as conn:
    result = conn.execute(text("SELECT version_num FROM alembic_version ORDER BY version_num"))
    for row in result:
        print(f"  - {row[0]}")
