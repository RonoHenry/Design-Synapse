"""Test TiDB connection."""
import sys
import os

# Add packages to path
sys.path.insert(0, os.path.abspath('.'))

from packages.common.config.database import DatabaseConfig

# Load config
config = DatabaseConfig()

print(f"Database Type: {config.database_type}")
print(f"Host: {config.host}")
print(f"Port: {config.port}")
print(f"Database: {config.database}")
print(f"Username: {config.username}")
print(f"\nConnection URL: {config.get_connection_url(async_driver=False)}")

# Try to connect
from sqlalchemy import create_engine, text

try:
    engine = create_engine(
        config.get_connection_url(async_driver=False),
        **config.get_engine_kwargs()
    )
    
    with engine.connect() as conn:
        result = conn.execute(text("SELECT 1 as test"))
        print(f"\n✅ Connection successful! Result: {result.fetchone()}")
        
except Exception as e:
    print(f"\n❌ Connection failed: {e}")
