"""Verify design service schema."""
import os
import sys
from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, os.path.abspath("."))

from sqlalchemy import create_engine, text, inspect
from packages.common.config.database import DatabaseConfig

config = DatabaseConfig()
engine = create_engine(
    config.get_connection_url(async_driver=False), **config.get_engine_kwargs()
)

inspector = inspect(engine)

# Check designs table
print("=" * 60)
print("DESIGNS TABLE")
print("=" * 60)
columns = inspector.get_columns('designs')
print("\nColumns:")
for col in columns:
    print(f"  - {col['name']}: {col['type']} (nullable={col['nullable']})")

indexes = inspector.get_indexes('designs')
print("\nIndexes:")
for idx in indexes:
    print(f"  - {idx['name']}: {idx['column_names']}")

fks = inspector.get_foreign_keys('designs')
print("\nForeign Keys:")
for fk in fks:
    print(f"  - {fk['constrained_columns']} -> {fk['referred_table']}.{fk['referred_columns']}")

# Check design_comments table
print("\n" + "=" * 60)
print("DESIGN_COMMENTS TABLE")
print("=" * 60)
columns = inspector.get_columns('design_comments')
print("\nColumns:")
for col in columns:
    print(f"  - {col['name']}: {col['type']} (nullable={col['nullable']})")

fks = inspector.get_foreign_keys('design_comments')
print("\nForeign Keys:")
for fk in fks:
    print(f"  - {fk['constrained_columns']} -> {fk['referred_table']}.{fk['referred_columns']} (ondelete={fk.get('ondelete', 'N/A')})")

# Check design_files table
print("\n" + "=" * 60)
print("DESIGN_FILES TABLE")
print("=" * 60)
columns = inspector.get_columns('design_files')
print("\nColumns:")
for col in columns:
    print(f"  - {col['name']}: {col['type']} (nullable={col['nullable']})")

fks = inspector.get_foreign_keys('design_files')
print("\nForeign Keys:")
for fk in fks:
    print(f"  - {fk['constrained_columns']} -> {fk['referred_table']}.{fk['referred_columns']} (ondelete={fk.get('ondelete', 'N/A')})")

# Check design_optimizations table
print("\n" + "=" * 60)
print("DESIGN_OPTIMIZATIONS TABLE")
print("=" * 60)
columns = inspector.get_columns('design_optimizations')
print("\nColumns:")
for col in columns:
    print(f"  - {col['name']}: {col['type']} (nullable={col['nullable']})")

fks = inspector.get_foreign_keys('design_optimizations')
print("\nForeign Keys:")
for fk in fks:
    print(f"  - {fk['constrained_columns']} -> {fk['referred_table']}.{fk['referred_columns']} (ondelete={fk.get('ondelete', 'N/A')})")

# Check design_validations table
print("\n" + "=" * 60)
print("DESIGN_VALIDATIONS TABLE")
print("=" * 60)
columns = inspector.get_columns('design_validations')
print("\nColumns:")
for col in columns:
    print(f"  - {col['name']}: {col['type']} (nullable={col['nullable']})")

fks = inspector.get_foreign_keys('design_validations')
print("\nForeign Keys:")
for fk in fks:
    print(f"  - {fk['constrained_columns']} -> {fk['referred_table']}.{fk['referred_columns']} (ondelete={fk.get('ondelete', 'N/A')})")

print("\n" + "=" * 60)
print("Schema verification complete!")
print("=" * 60)
