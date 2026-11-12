"""Check alembic version in the database."""
import os

from sqlalchemy import create_engine, text

db_url = os.environ.get("DATABASE_URL")
engine = create_engine(db_url)

with engine.connect() as conn:
    result = conn.execute(text("SELECT * FROM alembic_version"))
    versions = list(result)

    print(f"Alembic versions in database:")
    for row in versions:
        print(f"  {row[0]}")
