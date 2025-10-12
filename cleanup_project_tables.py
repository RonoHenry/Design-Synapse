"""Cleanup failed project tables."""
import sys
import os

sys.path.insert(0, os.path.abspath('.'))

from packages.common.config.database import DatabaseConfig
from sqlalchemy import create_engine, text

config = DatabaseConfig()
engine = create_engine(
    config.get_connection_url(async_driver=False),
    **config.get_engine_kwargs()
)

with engine.connect() as conn:
    # Drop tables if they exist
    conn.execute(text("DROP TABLE IF EXISTS comments"))
    conn.execute(text("DROP TABLE IF EXISTS project_collaborators"))
    conn.execute(text("DROP TABLE IF EXISTS projects"))
    conn.execute(text("DELETE FROM alembic_version WHERE version_num = 'b2c3d4e5f6a7'"))
    conn.commit()
    print("✅ Cleaned up project tables")
