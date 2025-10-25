"""Apply visual output fields migration for design service."""
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

def main():
    """Apply the visual fields migration."""
    # Get database connection
    config = DatabaseConfig()
    engine = create_engine(
        config.get_connection_url(async_driver=False), **config.get_engine_kwargs()
    )

    print("Checking current database state...")
    
    # Check if alembic_version table exists and what's in it
    with engine.connect() as conn:
        try:
            result = conn.execute(text("SELECT version_num FROM alembic_version"))
            current_versions = [row[0] for row in result.fetchall()]
            print(f"Current alembic versions: {current_versions}")
            
            # Check if designs table exists and its structure
            result = conn.execute(text("DESCRIBE designs"))
            columns = [row[0] for row in result.fetchall()]
            print(f"Current designs table columns: {columns}")
            
            # Check if visual fields already exist
            visual_fields = ['floor_plan_url', 'rendering_url', 'model_file_url', 'visual_generation_status']
            existing_visual_fields = [field for field in visual_fields if field in columns]
            
            if existing_visual_fields:
                print(f"Visual fields already exist: {existing_visual_fields}")
                print("Migration may have already been applied.")
                return
            
        except Exception as e:
            print(f"Error checking database state: {e}")
            return

    # Set the correct alembic version if needed
    print("\nSetting alembic version to b6576f89ece0...")
    with engine.connect() as conn:
        # Clear and set the correct version
        conn.execute(text("DELETE FROM alembic_version"))
        conn.execute(text("INSERT INTO alembic_version (version_num) VALUES ('b6576f89ece0')"))
        conn.commit()
        print("Set alembic version to b6576f89ece0")

    # Now run the migration
    print("\nApplying visual fields migration...")
    result = subprocess.run(
        ['alembic', 'upgrade', 'head'],
        cwd=design_service_dir,
        capture_output=True,
        text=True
    )
    
    print(result.stdout)
    if result.stderr:
        print("STDERR:", result.stderr)

    if result.returncode == 0:
        print("\nMigration applied successfully!")
        
        # Verify the migration
        print("\nVerifying migration...")
        with engine.connect() as conn:
            result = conn.execute(text("DESCRIBE designs"))
            columns = [row[0] for row in result.fetchall()]
            
            visual_fields = ['floor_plan_url', 'rendering_url', 'model_file_url', 'visual_generation_status', 'visual_generation_error', 'visual_generated_at']
            missing_fields = [field for field in visual_fields if field not in columns]
            
            if missing_fields:
                print(f"ERROR: Missing visual fields: {missing_fields}")
            else:
                print("✅ All visual fields added successfully!")
                
            # Check index
            result = conn.execute(text("SHOW INDEX FROM designs WHERE Key_name = 'ix_designs_visual_generation_status'"))
            index_exists = len(list(result.fetchall())) > 0
            
            if index_exists:
                print("✅ Visual generation status index created successfully!")
            else:
                print("⚠️  Visual generation status index not found")
                
    else:
        print("\nMigration failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()