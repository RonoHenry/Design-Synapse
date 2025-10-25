"""Check CASCADE constraints on foreign keys."""
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

with engine.connect() as conn:
    # Check foreign keys for design_comments
    result = conn.execute(text("""
        SELECT 
            TABLE_NAME,
            COLUMN_NAME,
            CONSTRAINT_NAME,
            REFERENCED_TABLE_NAME,
            REFERENCED_COLUMN_NAME
        FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE
        WHERE TABLE_SCHEMA = :db_name
        AND TABLE_NAME IN ('design_comments', 'design_files', 'design_optimizations', 'design_validations')
        AND REFERENCED_TABLE_NAME IS NOT NULL
    """), {"db_name": config.database})
    
    print("Foreign Key Constraints:")
    print("=" * 80)
    for row in result:
        print(f"Table: {row[0]}")
        print(f"  Column: {row[1]}")
        print(f"  Constraint: {row[2]}")
        print(f"  References: {row[3]}.{row[4]}")
        print()
    
    # Check referential constraints for CASCADE
    result = conn.execute(text("""
        SELECT 
            TABLE_NAME,
            CONSTRAINT_NAME,
            UPDATE_RULE,
            DELETE_RULE
        FROM INFORMATION_SCHEMA.REFERENTIAL_CONSTRAINTS
        WHERE CONSTRAINT_SCHEMA = :db_name
        AND TABLE_NAME IN ('design_comments', 'design_files', 'design_optimizations', 'design_validations')
    """), {"db_name": config.database})
    
    print("\nReferential Constraint Rules:")
    print("=" * 80)
    for row in result:
        print(f"Table: {row[0]}")
        print(f"  Constraint: {row[1]}")
        print(f"  ON UPDATE: {row[2]}")
        print(f"  ON DELETE: {row[3]}")
        print()
