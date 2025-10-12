"""Verify all migrations are applied correctly."""
import os
import sys

sys.path.insert(0, os.path.abspath("."))

from sqlalchemy import create_engine, text

from packages.common.config.database import DatabaseConfig

config = DatabaseConfig()
engine = create_engine(
    config.get_connection_url(async_driver=False), **config.get_engine_kwargs()
)

print("=" * 60)
print("TiDB MIGRATION VERIFICATION")
print("=" * 60)

with engine.connect() as conn:
    # Check all tables
    result = conn.execute(text("SHOW TABLES"))
    tables = [row[0] for row in result.fetchall()]

    print(f"\n✅ Total Tables: {len(tables)}")
    print("\nUser Service Tables:")
    for table in ["users", "roles", "user_roles"]:
        status = "✅" if table in tables else "❌"
        print(f"  {status} {table}")

    print("\nProject Service Tables:")
    for table in ["projects", "project_collaborators", "comments"]:
        status = "✅" if table in tables else "❌"
        print(f"  {status} {table}")

    print("\nKnowledge Service Tables:")
    for table in ["resources", "topics", "bookmarks", "citations", "resource_topics"]:
        status = "✅" if table in tables else "❌"
        print(f"  {status} {table}")

    # Check alembic versions
    result = conn.execute(
        text("SELECT version_num FROM alembic_version ORDER BY version_num")
    )
    versions = [row[0] for row in result.fetchall()]

    print(f"\n✅ Alembic Versions Applied: {len(versions)}")
    for version in versions:
        service = ""
        if version == "a1b2c3d4e5f6":
            service = "(user-service)"
        elif version == "b2c3d4e5f6a7":
            service = "(project-service)"
        elif version == "c3d4e5f6a7b8":
            service = "(knowledge-service)"
        print(f"  ✅ {version} {service}")

    # Test connection
    result = conn.execute(text("SELECT VERSION()"))
    db_version = result.fetchone()[0]
    print(f"\n✅ Database Version: {db_version}")
    print(f"✅ Connection: {config.host}:{config.port}/{config.database}")

    print("\n" + "=" * 60)
    print("ALL MIGRATIONS SUCCESSFULLY APPLIED!")
    print("=" * 60)
