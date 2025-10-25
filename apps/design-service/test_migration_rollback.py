"""Test migration rollback for visual output fields."""
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
    """Test migration rollback."""
    # Get database connection
    config = DatabaseConfig()
    engine = create_engine(
        config.get_connection_url(async_driver=False), **config.get_engine_kwargs()
    )

    print("Testing migration rollback...")
    
    # Check current state
    with engine.connect() as conn:
        result = conn.execute(text("DESCRIBE designs"))
        columns_before = [row[0] for row in result.fetchall()]
        print(f"Columns before rollback: {len(columns_before)} columns")
        
        visual_fields = ['floor_plan_url', 'rendering_url', 'model_file_url', 'visual_generation_status', 'visual_generation_error', 'visual_generated_at']
        existing_visual_fields = [field for field in visual_fields if field in columns_before]
        print(f"Visual fields present: {existing_visual_fields}")

    # Rollback migration
    print("\nRolling back migration...")
    result = subprocess.run(
        ['alembic', 'downgrade', 'b6576f89ece0'],
        cwd=design_service_dir,
        capture_output=True,
        text=True
    )
    
    print(result.stdout)
    if result.stderr:
        print("STDERR:", result.stderr)

    if result.returncode == 0:
        print("✅ Rollback successful!")
        
        # Verify rollback
        with engine.connect() as conn:
            result = conn.execute(text("DESCRIBE designs"))
            columns_after = [row[0] for row in result.fetchall()]
            print(f"Columns after rollback: {len(columns_after)} columns")
            
            visual_fields = ['floor_plan_url', 'rendering_url', 'model_file_url', 'visual_generation_status', 'visual_generation_error', 'visual_generated_at']
            remaining_visual_fields = [field for field in visual_fields if field in columns_after]
            
            if remaining_visual_fields:
                print(f"❌ ERROR: Visual fields still present: {remaining_visual_fields}")
            else:
                print("✅ All visual fields removed successfully!")
                
        # Re-apply migration
        print("\nRe-applying migration...")
        result = subprocess.run(
            ['alembic', 'upgrade', 'head'],
            cwd=design_service_dir,
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            print("✅ Migration re-applied successfully!")
            
            # Final verification
            with engine.connect() as conn:
                result = conn.execute(text("DESCRIBE designs"))
                columns_final = [row[0] for row in result.fetchall()]
                
                visual_fields = ['floor_plan_url', 'rendering_url', 'model_file_url', 'visual_generation_status', 'visual_generation_error', 'visual_generated_at']
                final_visual_fields = [field for field in visual_fields if field in columns_final]
                
                if len(final_visual_fields) == len(visual_fields):
                    print("✅ All visual fields restored successfully!")
                else:
                    print(f"❌ ERROR: Missing visual fields: {set(visual_fields) - set(final_visual_fields)}")
        else:
            print("❌ Failed to re-apply migration")
            
    else:
        print("❌ Rollback failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()