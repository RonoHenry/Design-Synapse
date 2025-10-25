"""Apply design service migration."""
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

# Now run alembic upgrade
print("\nApplying migration...")
result = subprocess.run(
    ['alembic', 'upgrade', 'head'],
    cwd=design_service_dir,
    capture_output=True,
    text=True
)
print(result.stdout)
if result.stderr:
    print(result.stderr)

# Get the new version that was applied
with engine.connect() as conn:
    result_query = conn.execute(text("SELECT version_num FROM alembic_version"))
    new_versions = [row[0] for row in result_query.fetchall()]
    print(f"\nNew version applied: {new_versions}")

# Restore the backed up versions (add them back)
print("\nRestoring previous alembic_version entries...")
with engine.connect() as conn:
    for version in backup_versions:
        # Check if version already exists
        result_check = conn.execute(
            text("SELECT COUNT(*) FROM alembic_version WHERE version_num = :version"),
            {"version": version}
        )
        if result_check.scalar() == 0:
            conn.execute(
                text("INSERT INTO alembic_version (version_num) VALUES (:version)"),
                {"version": version}
            )
    conn.commit()
    print(f"Restored versions: {backup_versions}")

# Show final state
with engine.connect() as conn:
    result_query = conn.execute(text("SELECT version_num FROM alembic_version"))
    final_versions = [row[0] for row in result_query.fetchall()]
    print(f"\nFinal alembic_version state: {final_versions}")

if result.returncode == 0:
    print("\nMigration applied successfully!")
else:
    print("\nMigration failed!")
    sys.exit(1)
