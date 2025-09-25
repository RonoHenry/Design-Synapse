"""
Test configuration and shared fixtures for the user service tests.
"""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from src.infrastructure.database import Base
from src.models.user import User

@pytest.fixture(scope="session")
def db_engine():
    """Create a test database engine."""
    DATABASE_URL = "postgresql://design_synapse_user:design_synapse_password@localhost:5432/design_synapse_user_db"
    engine = create_engine(DATABASE_URL)
    
    # Create all tables
    Base.metadata.create_all(engine)
    
    yield engine
    
    # Drop all tables
    Base.metadata.drop_all(engine)

@pytest.fixture
def db_session(db_engine):
    """Create a new database session for a test, with a transaction that's rolled back."""
    connection = db_engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection)

    yield session

    session.close()
    transaction.rollback()
    connection.close()