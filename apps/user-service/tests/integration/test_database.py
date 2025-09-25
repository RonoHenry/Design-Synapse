"""
Integration tests for the database.
"""
import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

def test_database_connection(db_session: Session):
    """Test that the database connection is working."""
    result = db_session.execute(text("SELECT 1"))
    assert result.scalar() == 1

def test_user_table_exists(db_session: Session):
    """Test that the users table exists."""
    query = text("SELECT to_regclass('public.users')")
    result = db_session.execute(query)
    assert result.scalar() == 'users'