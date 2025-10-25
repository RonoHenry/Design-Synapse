"""Test migration rollback."""
import os
import sys
import subprocess
from dotenv import load_dotenv

# Save current directory
design_service_dir = os.path.dirname(os.path.abspath(__file__))

# Load environment variables from project root
project_root = os.path.abspath(os.path.join(design_service_dir, "..", ".."))
load_dotenv(os.path.join(project_root, ".env"))

sys.path.insert(0, project_root)

from sqlalchemy import create_engine, text
from packages.common.config.database import DatabaseConfig

# Get database connection
config = DatabaseConfig()
engine = create_engine(
    config.get_connection_url(async_driver=False), **config.get_engine_kwargs()
)

print("Backing up alembic_version table...")
with engine.connect() as conn:
    # Backup current versions
    result = conn.execute(text("SELECT version_num FROM alembic_version"))
    backup_versions = [row[0] for row in result.fetchall()]
    print(f"Backed up versions: {backup_versions}")
    
    # Keep only design service version
    conn.execute(text("DELETE FROM alembic_version WHERE version_num != 'b6576f89ece0'"))
    conn.commit()
    print("Cleared other service versions temporarily")

# Now run alembic downgrade
print("\nTesting rollback (downgrade -1)...")
result = subprocess.run(
    ['alembic', 'downgrade', '-1'],
    cwd=design_service_dir,
    capture_output=True,
    text=True
)
print(result.stdout)
if result.stderr:
    print(result.stderr)

# Check if tables were dropped
print("\nChecking if design tables were dropped...")
with engine.connect() as conn:
    result_query = conn.execute(text("SHOW TABLES LIKE 'design%'"))
    remaining_tables = [row[0] for row in result_query.fetchall()]
    if remaining_tables:
        print(f"ERROR: Tables still exist: {remaining_tables}")
    else:
        print("SUCCESS: All design tables were dropped")

# Restore the backed up versions
print("\nRestoring alembic_version table...")
with engine.connect() as conn:
    # Clear all versions first
    conn.execute(text("DELETE FROM alembic_version"))
    # Restore all backed up versions
    for version in backup_versions:
        conn.execute(
            text("INSERT INTO alembic_version (version_num) VALUES (:version)"),
            {"version": version}
        )
    conn.commit()
    print(f"Restored versions: {backup_versions}")

if result.returncode == 0:
    print("\nRollback test completed successfully!")
else:
    print("\nRollback test failed!")
    sys.exit(1)
