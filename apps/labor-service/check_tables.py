"""Check if tables exist in the database."""
import os

from sqlalchemy import create_engine, text

# Get DATABASE_URL from environment
db_url = os.environ.get("DATABASE_URL")
if not db_url:
    print("ERROR: DATABASE_URL not set")
    exit(1)

print(f"Connecting to: {db_url.split('@')[1] if '@' in db_url else db_url}")

engine = create_engine(db_url)

with engine.connect() as conn:
    result = conn.execute(text("SHOW TABLES"))
    tables = [row[0] for row in result]

    print(f"\nFound {len(tables)} tables:")
    for table in sorted(tables):
        print(f"  - {table}")

    # Check for specific labor-service tables
    expected_tables = [
        "service_providers",
        "service_requests",
        "quotes",
        "bookings",
        "reviews",
        "skills",
        "skill_categories",
    ]

    print("\nExpected tables:")
    for table in expected_tables:
        status = "✓" if table in tables else "✗"
        print(f"  {status} {table}")
