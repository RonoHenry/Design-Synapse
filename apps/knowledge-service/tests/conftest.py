"""Test configuration and fixtures.

Environment Variables:
    TEST_DATABASE_URL: Optional database URL for integration testing.
                      If not set, uses SQLite in-memory for fast unit tests.
                      Example: mysql+pymysql://user:pass@host:port/db?charset=utf8mb4
"""

import asyncio
import os
import sys
import pytest
from sqlalchemy import Column, Integer, String, Boolean, create_engine, event
from sqlalchemy.orm import sessionmaker, Session
from fastapi.testclient import TestClient

# Add knowledge_service directory to Python path
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

# Set dummy OpenAI key for tests
os.environ["OPENAI_API_KEY"] = "dummy-key-for-testing"

from knowledge_service.infrastructure.database import Base, get_db

# Import all models first to register them with Base.metadata
from knowledge_service.models.resource import Resource, Topic, resource_topics, Citation
from knowledge_service.models.bookmark import Bookmark
from knowledge_service.main import app

# Define User model after importing other models
class User(Base):
    """Mock User class for testing."""
    __tablename__ = "users"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True)
    email = Column(String)
    full_name = Column(String)
    hashed_password = Column(String)
    is_active = Column(Boolean, default=True)

# This ensures all models are loaded and registered before table creation
all_models_loaded = True

@pytest.fixture
def event_loop():
    """Create an event loop for each test case."""
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()

def create_access_token(data):
    """Mock token creation."""
    return data['sub']

# Test database URL - check environment variable or use SQLite default
SQLALCHEMY_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "sqlite:///file:memdb?mode=memory&cache=shared&uri=true"
)

@pytest.fixture(scope="function")
def db_engine():
    """Create a test database engine for each test."""
    if "sqlite" in SQLALCHEMY_DATABASE_URL:
        engine = create_engine(
            SQLALCHEMY_DATABASE_URL,
            echo=False,
            connect_args={
                "check_same_thread": False,
                "uri": True
            }
        )
        
        # Register event listener to enable foreign key support in SQLite
        @event.listens_for(engine, "connect")
        def set_sqlite_pragma(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()
    else:
        # MySQL/TiDB configuration
        engine = create_engine(
            SQLALCHEMY_DATABASE_URL,
            echo=False,
            pool_pre_ping=True,
            pool_recycle=3600,
        )
        
        # Set MySQL/TiDB specific session variables
        @event.listens_for(engine, "connect")
        def set_mysql_pragma(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("SET NAMES utf8mb4")
            cursor.execute("SET CHARACTER SET utf8mb4")
            cursor.execute("SET character_set_connection=utf8mb4")
            cursor.close()
    
    # Create all tables first
    Base.metadata.create_all(bind=engine)
    
    yield engine
    
    # Clean up after test
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db_session(db_engine):
    """Create tables and return a test database session."""
    SessionLocal = sessionmaker(bind=db_engine)
    session = SessionLocal()
    
    yield session
    
    # Close session after test
    session.close()

@pytest.fixture
def client(db_session):
    """Create a test client."""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()

@pytest.fixture
def test_user(db_session):
    """Create a test user."""
    user = User(
        email="test@example.com",
        hashed_password="test_hashed_password",
        full_name="Test User",
        is_active=True
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user

@pytest.fixture
def auth_headers(test_user):
    """Create authorization headers for testing."""
    return {"Authorization": f"Bearer {test_user.id}"}