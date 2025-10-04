"""
Pytest plugins and fixtures for common test patterns.
"""

import pytest
import asyncio
from typing import Generator, AsyncGenerator, Dict, Any
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import Session, sessionmaker
from fastapi.testclient import TestClient

from .database import (
    create_test_engine,
    create_async_test_engine,
    create_test_session,
    create_async_test_session
)
from .mocks import (
    MockLLMService,
    MockVectorService,
    MockHTTPService
)


class CommonTestFixtures:
    """
    Collection of common test fixtures that can be used across services.
    
    Services can inherit from this class or use individual fixtures
    as needed for their specific testing requirements.
    """
    
    @pytest.fixture(scope="session")
    def event_loop(self) -> Generator[asyncio.AbstractEventLoop, None, None]:
        """Create an event loop for async tests."""
        policy = asyncio.get_event_loop_policy()
        loop = policy.new_event_loop()
        yield loop
        loop.close()
    
    @pytest.fixture(scope="function")
    def test_db_engine(self):
        """Create a test database engine."""
        return create_test_engine()
    
    @pytest.fixture(scope="function")
    def async_test_db_engine(self):
        """Create an async test database engine."""
        return create_async_test_engine()
    
    @pytest.fixture
    def mock_llm_service(self) -> MockLLMService:
        """Provide a mock LLM service."""
        return MockLLMService()
    
    @pytest.fixture
    def mock_vector_service(self) -> MockVectorService:
        """Provide a mock vector service."""
        return MockVectorService()
    
    @pytest.fixture
    def mock_http_service(self) -> MockHTTPService:
        """Provide a mock HTTP service."""
        return MockHTTPService()
    
    @pytest.fixture
    def mock_external_services(
        self,
        mock_llm_service,
        mock_vector_service,
        mock_http_service
    ) -> Dict[str, Any]:
        """Provide all mock external services."""
        return {
            "llm": mock_llm_service,
            "vector": mock_vector_service,
            "http": mock_http_service
        }


# Individual fixture functions that can be imported directly
@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
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


@pytest.fixture
def mock_llm_service() -> MockLLMService:
    """Provide a mock LLM service."""
    return MockLLMService()


@pytest.fixture
def mock_vector_service() -> MockVectorService:
    """Provide a mock vector service."""
    return MockVectorService()


@pytest.fixture
def mock_http_service() -> MockHTTPService:
    """Provide a mock HTTP service."""
    return MockHTTPService()


@pytest.fixture
def mock_external_services(
    mock_llm_service,
    mock_vector_service,
    mock_http_service
) -> Dict[str, Any]:
    """Provide all mock external services."""
    return {
        "llm": mock_llm_service,
        "vector": mock_vector_service,
        "http": mock_http_service
    }


def create_service_test_session_fixture(base_class, engine_fixture_name="test_db_engine"):
    """
    Factory function to create a database session fixture for a specific service.
    
    Args:
        base_class: SQLAlchemy Base class for the service
        engine_fixture_name: Name of the engine fixture to use
        
    Returns:
        Pytest fixture function for database sessions
    """
    
    @pytest.fixture
    def db_session(request):
        """Create a database session for testing."""
        engine = request.getfixturevalue(engine_fixture_name)
        with create_test_session(engine, base_class) as session:
            yield session
    
    return db_session


def create_service_async_test_session_fixture(base_class, engine_fixture_name="async_test_db_engine"):
    """
    Factory function to create an async database session fixture for a specific service.
    
    Args:
        base_class: SQLAlchemy Base class for the service
        engine_fixture_name: Name of the async engine fixture to use
        
    Returns:
        Pytest fixture function for async database sessions
    """
    
    @pytest.fixture
    async def async_db_session(request):
        """Create an async database session for testing."""
        engine = request.getfixturevalue(engine_fixture_name)
        async with create_async_test_session(engine, base_class) as session:
            yield session
    
    return async_db_session


def create_fastapi_test_client_fixture(
    app,
    db_dependency,
    session_fixture_name="db_session"
):
    """
    Factory function to create a FastAPI test client fixture.
    
    Args:
        app: FastAPI application instance
        db_dependency: Database dependency function to override
        session_fixture_name: Name of the session fixture to use
        
    Returns:
        Pytest fixture function for FastAPI test client
    """
    
    @pytest.fixture
    def client(request):
        """Create a FastAPI test client."""
        db_session = request.getfixturevalue(session_fixture_name)
        
        def override_get_db():
            try:
                yield db_session
            finally:
                pass
        
        app.dependency_overrides[db_dependency] = override_get_db
        
        with TestClient(app) as test_client:
            yield test_client
        
        app.dependency_overrides.clear()
    
    return client


class TestDataMixin:
    """
    Mixin providing common test data creation patterns.
    
    Test classes can inherit from this to get access to
    standardized test data creation methods.
    """
    
    def create_test_user_data(self, **overrides) -> Dict[str, Any]:
        """Create test user data."""
        default_data = {
            "email": "test@example.com",
            "username": "testuser",
            "first_name": "Test",
            "last_name": "User",
            "is_active": True
        }
        default_data.update(overrides)
        return default_data
    
    def create_test_project_data(self, **overrides) -> Dict[str, Any]:
        """Create test project data."""
        default_data = {
            "name": "Test Project",
            "description": "Test project description",
            "status": "active",
            "owner_id": 1
        }
        default_data.update(overrides)
        return default_data
    
    def create_test_resource_data(self, **overrides) -> Dict[str, Any]:
        """Create test resource data."""
        default_data = {
            "title": "Test Resource",
            "description": "Test resource description",
            "content_type": "pdf",
            "source_url": "https://example.com/test.pdf",
            "storage_path": "/test/path/test.pdf"
        }
        default_data.update(overrides)
        return default_data


# Plugin configuration for pytest
pytest_plugins = [
    "packages.common.testing.fixtures"
]


def pytest_configure(config):
    """Configure pytest with common markers and settings."""
    config.addinivalue_line(
        "markers", "unit: mark test as a unit test"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as an integration test"
    )
    config.addinivalue_line(
        "markers", "async_test: mark test as requiring async support"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )
    config.addinivalue_line(
        "markers", "external: mark test as requiring external services"
    )