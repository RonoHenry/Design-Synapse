"""Generate initial migration for design service."""
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
    
    # Clear alembic_version table temporarily
    conn.execute(text("DELETE FROM alembic_version"))
    conn.commit()
    print("Cleared alembic_version table")

# Now run alembic revision from the design-service directory
print("\nGenerating migration...")
result = subprocess.run(
    ['alembic', 'revision', '--autogenerate', '-m', 'Initial design service schema'],
    cwd=design_service_dir,
    capture_output=True,
    text=True
)
print(result.stdout)
if result.stderr:
    print(result.stderr)

# Restore the backed up versions
print("\nRestoring alembic_version table...")
with engine.connect() as conn:
    for version in backup_versions:
        conn.execute(
            text("INSERT INTO alembic_version (version_num) VALUES (:version)"),
            {"version": version}
        )
    conn.commit()
    print(f"Restored versions: {backup_versions}")

if result.returncode == 0:
    print("\nMigration generation complete!")
else:
    print("\nMigration generation failed!")
    sys.exit(1)
