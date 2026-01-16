"""Debug script to check what tables are registered."""

import src.models
from src.core.database import Base

print("Tables registered with Base.metadata:")
for table in Base.metadata.tables:
    print(f"  - {table}")

print(f"\nTotal tables: {len(Base.metadata.tables)}")
