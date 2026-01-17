#!/usr/bin/env python3
"""
Apply Labor Service Database Migration

This script applies the database migration and optionally seeds the database
with initial data for development and testing.
"""

import sys
import os
from pathlib import Path

# Add the src directory to the path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from alembic.config import Config
from alembic import command
from utils.database_seeder import seed_database
from utils.database_cleanup import clean_test_data, vacuum_database


def apply_migration():
    """Apply the database migration."""
    print("🔄 Applying Labor Service database migration...")
    
    # Configure Alembic
    alembic_cfg = Config("alembic.ini")
    
    try:
        # Apply migration
        command.upgrade(alembic_cfg, "head")
        print("✅ Migration applied successfully!")
        return True
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        return False


def main():
    """Main function."""
    print("🚀 Labor Service Database Setup")
    print("=" * 40)
    
    # Apply migration
    if not apply_migration():
        sys.exit(1)
    
    # Check if we should seed data
    if len(sys.argv) > 1 and sys.argv[1] == "--seed":
        print("\n🌱 Seeding database with initial data...")
        try:
            summary = seed_database()
            print(f"✅ Seeding completed: {summary}")
        except Exception as e:
            print(f"❌ Seeding failed: {e}")
            sys.exit(1)
    
    # Check if we should clean test data
    elif len(sys.argv) > 1 and sys.argv[1] == "--clean-test":
        print("\n🧹 Cleaning test data...")
        try:
            summary = clean_test_data()
            print(f"✅ Cleanup completed: {summary}")
        except Exception as e:
            print(f"❌ Cleanup failed: {e}")
            sys.exit(1)
    
    # Check if we should vacuum
    elif len(sys.argv) > 1 and sys.argv[1] == "--vacuum":
        print("\n🗜️  Vacuuming database...")
        try:
            vacuum_database()
            print("✅ Vacuum completed")
        except Exception as e:
            print(f"❌ Vacuum failed: {e}")
            sys.exit(1)
    
    print("\n🎉 Labor Service database setup completed!")
    print("\nUsage:")
    print("  python apply_migration.py           # Apply migration only")
    print("  python apply_migration.py --seed    # Apply migration and seed data")
    print("  python apply_migration.py --clean-test  # Clean test data")
    print("  python apply_migration.py --vacuum  # Vacuum database")


if __name__ == "__main__":
    main()