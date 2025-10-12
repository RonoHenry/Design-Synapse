"""
Database isolation utilities for testing across services.
"""

import asyncio
from typing import Generator, AsyncGenerator, Optional, Dict, Any
from contextlib import contextmanager, asynccontextmanager
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine, AsyncSession
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool
import pytest


class DatabaseTestMixin:
    """
    Mixin class providing database testing utilities.
    
    This mixin can be used by test classes to get consistent database
    isolation and session management patterns.
    """
    
    @classmethod
    def setup_test_database(cls, database_url: str, echo: bool = False) -> Engine:
        """
        Set up a test database engine with proper configuration.
        
        Args:
            database_url: Database URL for testing
            echo: Whether to echo SQL statements
            
        Returns:
            Configured SQLAlchemy engine
        """
        engine = create_engine(
            database_url,
            echo=echo,
            connect_args={"check_same_thread": False} if "sqlite" in database_url else {},
            poolclass=StaticPool if "sqlite" in database_url else None,
        )
        
        # Enable foreign key constraints for SQLite
        if "sqlite" in database_url:
            @event.listens_for(engine, "connect")
            def set_sqlite_pragma(dbapi_connection, connection_record):
                cursor = dbapi_connection.cursor()
                cursor.execute("PRAGMA foreign_keys=ON")
                cursor.close()
        
        return engine
    
    @classmethod
    def setup_async_test_database(cls, database_url: str, echo: bool = False) -> AsyncEngine:
        """
        Set up an async test database engine.
        
        Args:
            database_url: Async database URL for testing
            echo: Whether to echo SQL statements
            
        Returns:
            Configured async SQLAlchemy engine
        """
        engine = create_async_engine(
            database_url,
            echo=echo,
            connect_args={"check_same_thread": False} if "sqlite" in database_url else {},
            poolclass=StaticPool if "sqlite" in database_url else None,
        )
        
        return engine


def create_test_engine(
    database_url: Optional[str] = None,
    echo: bool = False,
    **engine_kwargs
) -> Engine:
    """
    Create a test database engine with sensible defaults.
    
    Args:
        database_url: Database URL (defaults to in-memory SQLite)
        echo: Whether to echo SQL statements
        **engine_kwargs: Additional engine configuration
        
    Returns:
        Configured SQLAlchemy engine
    """
    if database_url is None:
        database_url = "sqlite:///:memory:"
    
    default_kwargs = {
        "echo": echo,
    }
    
    # Configure connection args based on database type
    if "sqlite" in database_url:
        default_kwargs["connect_args"] = {"check_same_thread": False}
        default_kwargs["poolclass"] = StaticPool
    elif "mysql" in database_url or "tidb" in database_url:
        # MySQL/TiDB specific configuration
        connect_args = {}
        
        # Handle SSL configuration for TiDB
        if "ssl_ca=" in database_url:
            import ssl
            # SSL parameters are in the URL, pymysql will handle them
            connect_args["ssl"] = {
                "ssl_mode": "VERIFY_IDENTITY"
            }
        
        if connect_args:
            default_kwargs["connect_args"] = connect_args
        
        # Use connection pooling for MySQL/TiDB
        default_kwargs["pool_pre_ping"] = True
        default_kwargs["pool_recycle"] = 3600
    
    # Merge with user-provided kwargs
    default_kwargs.update(engine_kwargs)
    
    engine = create_engine(database_url, **default_kwargs)
    
    # Enable foreign key constraints for SQLite
    if "sqlite" in database_url:
        @event.listens_for(engine, "connect")
        def set_sqlite_pragma(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()
    
    # Set MySQL/TiDB specific session variables
    if "mysql" in database_url or "tidb" in database_url:
        @event.listens_for(engine, "connect")
        def set_mysql_pragma(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            # Ensure UTF-8 encoding
            cursor.execute("SET NAMES utf8mb4")
            cursor.execute("SET CHARACTER SET utf8mb4")
            cursor.execute("SET character_set_connection=utf8mb4")
            cursor.close()
    
    return engine


def create_async_test_engine(
    database_url: Optional[str] = None,
    echo: bool = False,
    **engine_kwargs
) -> AsyncEngine:
    """
    Create an async test database engine with sensible defaults.
    
    Args:
        database_url: Async database URL (defaults to in-memory SQLite)
        echo: Whether to echo SQL statements
        **engine_kwargs: Additional engine configuration
        
    Returns:
        Configured async SQLAlchemy engine
    """
    if database_url is None:
        database_url = "sqlite+aiosqlite:///:memory:"
    
    default_kwargs = {
        "echo": echo,
        "connect_args": {"check_same_thread": False} if "sqlite" in database_url else {},
    }
    
    if "sqlite" in database_url:
        default_kwargs["poolclass"] = StaticPool
    
    # Merge with user-provided kwargs
    default_kwargs.update(engine_kwargs)
    
    return create_async_engine(database_url, **default_kwargs)


@contextmanager
def create_test_session(
    engine: Engine,
    base_class,
    autocommit: bool = False,
    autoflush: bool = False
) -> Generator[Session, None, None]:
    """
    Create a test database session with proper cleanup.
    
    Args:
        engine: SQLAlchemy engine
        base_class: SQLAlchemy Base class for metadata
        autocommit: Whether to autocommit transactions
        autoflush: Whether to autoflush changes
        
    Yields:
        Database session
    """
    # Create all tables
    base_class.metadata.create_all(bind=engine)
    
    # Create session
    SessionLocal = sessionmaker(
        bind=engine,
        autocommit=autocommit,
        autoflush=autoflush
    )
    session = SessionLocal()
    
    try:
        yield session
    finally:
        session.close()
        # Drop all tables for cleanup
        base_class.metadata.drop_all(bind=engine)


@asynccontextmanager
async def create_async_test_session(
    engine: AsyncEngine,
    base_class,
    autocommit: bool = False,
    autoflush: bool = False
) -> AsyncGenerator[AsyncSession, None]:
    """
    Create an async test database session with proper cleanup.
    
    Args:
        engine: Async SQLAlchemy engine
        base_class: SQLAlchemy Base class for metadata
        autocommit: Whether to autocommit transactions
        autoflush: Whether to autoflush changes
        
    Yields:
        Async database session
    """
    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(base_class.metadata.create_all)
    
    # Create session
    AsyncSessionLocal = sessionmaker(
        class_=AsyncSession,
        bind=engine,
        autocommit=autocommit,
        autoflush=autoflush
    )
    
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            # Drop all tables for cleanup
            async with engine.begin() as conn:
                await conn.run_sync(base_class.metadata.drop_all)


class TransactionalTestCase:
    """
    Base test case class that provides transactional test isolation.
    
    Each test method runs in its own transaction that is rolled back
    after the test completes, ensuring test isolation.
    """
    
    def setup_method(self, method):
        """Set up a new transaction for each test method."""
        self.transaction = self.db_session.begin()
    
    def teardown_method(self, method):
        """Roll back the transaction after each test method."""
        if hasattr(self, 'transaction'):
            self.transaction.rollback()


def pytest_configure_database_fixtures():
    """
    Configure pytest fixtures for database testing.
    
    This function returns fixture definitions that can be used
    by services to set up their database testing.
    """
    
    @pytest.fixture(scope="session")
    def event_loop():
        """Create an event loop for async tests."""
        policy = asyncio.get_event_loop_policy()
        loop = policy.new_event_loop()
        yield loop
        loop.close()
    
    @pytest.fixture(scope="function")
    def test_db_engine():
        """Create a test database engine."""
        return create_test_engine()
    
    @pytest.fixture(scope="function")
    def async_test_db_engine():
        """Create an async test database engine."""
        return create_async_test_engine()
    
    return {
        "event_loop": event_loop,
        "test_db_engine": test_db_engine,
        "async_test_db_engine": async_test_db_engine,
    }


# Database URL configurations for different testing scenarios
TEST_DATABASE_URLS = {
    "sqlite_memory": "sqlite:///:memory:",
    "sqlite_file": "sqlite:///test.db",
    "sqlite_async_memory": "sqlite+aiosqlite:///:memory:",
    "sqlite_async_file": "sqlite+aiosqlite:///test.db",
    "postgresql_test": "postgresql://test_user:test_pass@localhost:5432/test_db",
    "postgresql_async_test": "postgresql+asyncpg://test_user:test_pass@localhost:5432/test_db",
    "mysql_test": "mysql+pymysql://test_user:test_pass@localhost:3306/test_db?charset=utf8mb4",
    "tidb_test": "mysql+pymysql://test_user:test_pass@gateway.tidbcloud.com:4000/test_db?charset=utf8mb4&ssl_ca=/path/to/ca.pem&ssl_verify_cert=true&ssl_verify_identity=true",
}
