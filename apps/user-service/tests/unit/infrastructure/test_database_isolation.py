"""
Tests for database isolation between services.
"""
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError
from src.infrastructure.database import DatabaseSettings, get_database_settings

def test_database_settings_isolation():
    """Test that database settings are properly isolated per service."""
    settings = get_database_settings()
    assert settings.postgres_db == "design_synapse_user_db"  # Should be specific to user service
    assert "user" in settings.postgres_db  # Database name should reflect the service

def test_cannot_access_other_service_tables():
    """Test that a service cannot access tables from other services."""
    settings = get_database_settings()
    
    # Try to connect to marketplace database
    marketplace_url = (
        f"postgresql://{settings.postgres_user}:{settings.postgres_password}"
        f"@{settings.postgres_host}:{settings.postgres_port}/design_synapse_marketplace_db"
    )
    
    with pytest.raises(OperationalError) as exc_info:
        engine = create_engine(marketplace_url)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    
    error_message = str(exc_info.value).lower()
    assert "permission denied" in error_message or "does not exist" in error_message

def test_service_database_exists():
    """Test that the service's own database exists and is accessible."""
    settings = get_database_settings()
    engine = create_engine(settings.database_url)
    
    with engine.connect() as conn:
        result = conn.execute(text("SELECT current_database()")).scalar()
        assert result == "design_synapse_user_db"

def test_database_schema_isolation():
    """Test that database schemas are isolated."""
    settings = get_database_settings()
    engine = create_engine(settings.database_url)
    
    with engine.connect() as conn:
        # Check that only our service's schema exists
        schemas = conn.execute(
            text("SELECT schema_name FROM information_schema.schemata")
        ).scalars().all()
        
        assert "public" in schemas  # Default schema should exist
        assert len([s for s in schemas if "marketplace" in s]) == 0
        assert len([s for s in schemas if "design" in s]) == 0