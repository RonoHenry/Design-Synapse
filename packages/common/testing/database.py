"""
Database isolation utilities for testing across services.
"""

import asyncio
from contextlib import asynccontextmanager, contextmanager
from typing import Any, AsyncGenerator, Dict, Generator, Optional

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.ext.asyncio import (AsyncEngine, AsyncSession,
                                    create_async_engine)
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool


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
            connect_args={"check_same_thread": False}
            if "sqlite" in database_url
            else {},
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
    def setup_async_test_database(
        cls, database_url: str, echo: bool = False
    ) -> AsyncEngine:
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
            connect_args={"check_same_thread": False}
            if "sqlite" in database_url
            else {},
            poolclass=StaticPool if "sqlite" in database_url else None,
        )

        return engine


def create_test_engine(
    database_url: Optional[str] = None, echo: bool = False, **engine_kwargs
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
            connect_args["ssl"] = {"ssl_mode": "VERIFY_IDENTITY"}

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
    database_url: Optional[str] = None, echo: bool = False, **engine_kwargs
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
        "connect_args": {"check_same_thread": False}
        if "sqlite" in database_url
        else {},
    }

    if "sqlite" in database_url:
        default_kwargs["poolclass"] = StaticPool

    # Merge with user-provided kwargs
    default_kwargs.update(engine_kwargs)

    return create_async_engine(database_url, **default_kwargs)


@contextmanager
def create_test_session(
    engine: Engine, base_class, autocommit: bool = False, autoflush: bool = False
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
    SessionLocal = sessionmaker(bind=engine, autocommit=autocommit, autoflush=autoflush)
    session = SessionLocal()

    try:
        yield session
    finally:
        session.close()
        # Drop all tables for cleanup
        base_class.metadata.drop_all(bind=engine)


@asynccontextmanager
async def create_async_test_session(
    engine: AsyncEngine, base_class, autocommit: bool = False, autoflush: bool = False
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
        class_=AsyncSession, bind=engine, autocommit=autocommit, autoflush=autoflush
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
        if hasattr(self, "transaction"):
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


class DatabaseTestManager:
    """Manages test database connections and isolation for integration testing."""

    def __init__(self):
        self.engines = {}
        self.session_makers = {}
        self._setup_test_databases()

    def _setup_test_databases(self):
        """Set up test database connections for each service."""
        # Use in-memory SQLite for testing
        test_db_url = "sqlite:///:memory:"

        # Create engines for each service
        for service in ["user", "knowledge", "project"]:
            engine = create_test_engine(test_db_url)
            self.engines[service] = engine
            self.session_makers[service] = sessionmaker(bind=engine)

    def get_session(self, service: str) -> Session:
        """Get a database session for the specified service."""
        return self.session_makers[service]()

    def get_user_session(self) -> Session:
        """Get a user service database session."""
        return self.get_session("user")

    def get_knowledge_session(self) -> Session:
        """Get a knowledge service database session."""
        return self.get_session("knowledge")

    def get_project_session(self) -> Session:
        """Get a project service database session."""
        return self.get_session("project")

    def get_connection_pool_info(self, service: str = "knowledge") -> Dict[str, Any]:
        """Get connection pool information for monitoring."""
        engine = self.engines[service]
        pool = engine.pool

        return {
            "pool_size": getattr(pool, "size", lambda: 5)(),
            "checked_out_connections": getattr(pool, "checkedout", lambda: 0)(),
            "overflow_connections": getattr(pool, "overflow", lambda: 0)(),
            "active_connections": getattr(pool, "checkedin", lambda: 0)(),
        }

    def create_tables(self, service: str):
        """Create tables for the specified service."""
        # Import models and create tables
        try:
            if service == "user":
                from apps.user_service.src.models.role import Role
                from apps.user_service.src.models.user import Base

                Base.metadata.create_all(self.engines[service])

                # Create default role for testing
                session = self.get_session(service)
                try:
                    default_role = Role(
                        name="default", description="Default role for testing"
                    )
                    session.add(default_role)
                    session.commit()
                except Exception:
                    session.rollback()
                finally:
                    session.close()

            elif service == "knowledge":
                from apps.knowledge_service.knowledge_service.models.resource import \
                    Base

                Base.metadata.create_all(self.engines[service])

            elif service == "project":
                from apps.project_service.src.models.project import Base

                Base.metadata.create_all(self.engines[service])
        except ImportError:
            # Skip table creation if models can't be imported
            pass

    def drop_tables(self, service: str):
        """Drop tables for the specified service."""
        try:
            if service == "user":
                from apps.user_service.src.models.user import Base

                Base.metadata.drop_all(self.engines[service])
            elif service == "knowledge":
                from apps.knowledge_service.knowledge_service.models.resource import \
                    Base

                Base.metadata.drop_all(self.engines[service])
            elif service == "project":
                from apps.project_service.src.models.project import Base

                Base.metadata.drop_all(self.engines[service])
        except ImportError:
            # Skip table cleanup if models can't be imported
            pass

    def execute_with_retry(
        self, session: Session, operation, max_retries: int = 3
    ) -> Any:
        """Execute database operation with retry logic for deadlock recovery."""
        import time

        from sqlalchemy.exc import OperationalError

        for attempt in range(max_retries):
            try:
                return operation()
            except OperationalError as e:
                if "deadlock" in str(e).lower() and attempt < max_retries - 1:
                    # Exponential backoff for deadlock retry
                    wait_time = (2**attempt) * 0.1
                    time.sleep(wait_time)
                    session.rollback()
                    continue
                else:
                    raise
            except Exception as e:
                session.rollback()
                raise

    def test_connection_health(self, service: str) -> bool:
        """Test if database connection is healthy."""
        try:
            from sqlalchemy import text

            session = self.get_session(service)
            session.execute(text("SELECT 1"))
            session.close()
            return True
        except Exception:
            return False


@pytest.fixture
def db_test_manager():
    """Provide a database test manager for integration tests."""
    manager = DatabaseTestManager()

    # Create tables for all services
    for service in ["user", "knowledge", "project"]:
        manager.create_tables(service)

    yield manager

    # Clean up tables after test
    for service in ["user", "knowledge", "project"]:
        try:
            manager.drop_tables(service)
        except Exception:
            pass  # Ignore cleanup errors


@pytest.fixture
def user_db_session(db_test_manager):
    """Provide a user service database session."""
    session = db_test_manager.get_session("user")
    yield session
    try:
        session.rollback()
        session.close()
    except Exception:
        pass


@pytest.fixture
def knowledge_db_session(db_test_manager):
    """Provide a knowledge service database session."""
    session = db_test_manager.get_session("knowledge")
    yield session
    try:
        session.rollback()
        session.close()
    except Exception:
        pass


@pytest.fixture
def project_db_session(db_test_manager):
    """Provide a project service database session."""
    session = db_test_manager.get_session("project")
    yield session
    try:
        session.rollback()
        session.close()
    except Exception:
        pass


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
