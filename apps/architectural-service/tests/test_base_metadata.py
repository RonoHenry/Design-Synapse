"""Test to debug Base.metadata registration."""

import pytest


def test_base_metadata_tables():
    """Check what tables are registered with Base.metadata."""
    from src.core.database import Base
    from src.models import Design, DesignVersion

    print(f"\nBase class: {Base}")
    print(f"Design.__table__: {Design.__table__}")
    print(f"Design.__table__.metadata: {Design.__table__.metadata}")
    print(f"Base.metadata: {Base.metadata}")
    print(f"Are they the same? {Design.__table__.metadata is Base.metadata}")

    print(f"\nTables in Base.metadata:")
    for table_name in Base.metadata.tables:
        print(f"  - {table_name}")

    print(f"\nTotal tables: {len(Base.metadata.tables)}")

    assert len(Base.metadata.tables) > 0, "No tables registered with Base.metadata"
