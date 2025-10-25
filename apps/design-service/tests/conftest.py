"""
Test configuration and shared fixtures for the design service tests.

Environment Variables:
    TEST_DATABASE_URL: Optional database URL for integration testing.
                      If not set, uses SQLite in-memory for fast unit tests.
                      Example: mysql+pymysql://user:pass@host:port/db?charset=utf8mb4
"""

import asyncio
import os
import sys
from typing import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

# Add packages to path for shared testing infrastructure
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..', 'packages'))

from common.testing.database import create_test_engine, create_test_session
from common.testing.fixtures import event_loop, mock_llm_service, mock_http_service
from src.infrastructure.database import Base, get_db


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create an event loop for async tests."""
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="function")
def db_engine():
    """Create a test database engine with proper isolation."""
    # Check if TiDB integration testing is enabled
    test_db_url = os.getenv("TEST_DATABASE_URL")
    
    if test_db_url:
        # Use TiDB for integration testing
        engine = create_test_engine(test_db_url, echo=False)
    else:
        # Use SQLite in-memory for fast, isolated tests (default)
        engine = create_test_engine("sqlite:///:memory:", echo=False)
    
    return engine


@pytest.fixture
def db_session(db_engine):
    """Create a database session with proper cleanup and isolation."""
    with create_test_session(db_engine, Base) as session:
        # Import factories here to avoid circular imports
        from .factories import (
            DesignFactory,
            DesignValidationFactory,
            DesignOptimizationFactory,
            DesignFileFactory,
            DesignCommentFactory
        )
        
        # Configure factories to use this session
        DesignFactory._meta.sqlalchemy_session = session
        DesignValidationFactory._meta.sqlalchemy_session = session
        DesignOptimizationFactory._meta.sqlalchemy_session = session
        DesignFileFactory._meta.sqlalchemy_session = session
        DesignCommentFactory._meta.sqlalchemy_session = session
        
        yield session


@pytest.fixture
def client(db_session, test_user_id, mock_llm_client, mock_project_client):
    """Create a FastAPI test client with database session and auth override."""
    # Mock Celery configuration for testing
    import os
    os.environ.setdefault('CELERY_BROKER_URL', 'redis://localhost:6379/0')
    
    # Import app and dependencies here to avoid loading during conftest import
    from src.main import app
    from src.api.dependencies import get_current_user_id
    from src.api.v1.routes.designs import get_llm_client, get_project_client
    from src.api.v1.routes.validations import get_project_client as get_project_client_validations
    from src.api.v1.routes.optimizations import (
        get_llm_client as get_llm_client_optimizations,
        get_project_client as get_project_client_optimizations
    )
    from src.api.v1.routes.comments import get_project_client as get_project_client_comments
    from src.api.v1.routes.export import get_project_client as get_project_client_export
    from src.api.v1.routes.files import get_project_client as get_project_client_files
    
    def override_get_db():
        try:
            yield db_session
        finally:
            pass
    
    def override_get_current_user_id():
        """Override authentication to return test user ID."""
        return test_user_id
    
    def override_get_llm_client():
        """Override LLM client with mock."""
        return mock_llm_client
    
    def override_get_project_client():
        """Override project client with mock."""
        return mock_project_client

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user_id] = override_get_current_user_id
    app.dependency_overrides[get_llm_client] = override_get_llm_client
    app.dependency_overrides[get_project_client] = override_get_project_client
    app.dependency_overrides[get_project_client_validations] = override_get_project_client
    app.dependency_overrides[get_llm_client_optimizations] = override_get_llm_client
    app.dependency_overrides[get_project_client_optimizations] = override_get_project_client
    app.dependency_overrides[get_project_client_comments] = override_get_project_client
    app.dependency_overrides[get_project_client_export] = override_get_project_client
    app.dependency_overrides[get_project_client_files] = override_get_project_client
    
    with TestClient(app) as test_client:
        yield test_client
    
    app.dependency_overrides.clear()


@pytest.fixture
def client_no_auth(db_session, mock_llm_client, mock_project_client):
    """Create a FastAPI test client without authentication override (for testing auth failures)."""
    # Import app and dependencies here to avoid loading during conftest import
    from src.main import app
    from src.api.v1.routes.designs import get_llm_client, get_project_client
    from src.api.v1.routes.validations import get_project_client as get_project_client_validations
    from src.api.v1.routes.optimizations import (
        get_llm_client as get_llm_client_optimizations,
        get_project_client as get_project_client_optimizations
    )
    from src.api.v1.routes.files import get_project_client as get_project_client_files
    
    def override_get_db():
        try:
            yield db_session
        finally:
            pass
    
    def override_get_llm_client():
        """Override LLM client with mock."""
        return mock_llm_client
    
    def override_get_project_client():
        """Override project client with mock."""
        return mock_project_client

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_llm_client] = override_get_llm_client
    app.dependency_overrides[get_project_client] = override_get_project_client
    app.dependency_overrides[get_project_client_validations] = override_get_project_client
    app.dependency_overrides[get_llm_client_optimizations] = override_get_llm_client
    app.dependency_overrides[get_project_client_optimizations] = override_get_project_client
    app.dependency_overrides[get_project_client_files] = override_get_project_client
    # Note: NOT overriding get_current_user_id to test authentication
    
    with TestClient(app) as test_client:
        yield test_client
    
    app.dependency_overrides.clear()


@pytest.fixture
def client_no_project_access(db_session, test_user_id, mock_llm_client, mock_project_client_access_denied):
    """Create a FastAPI test client with authentication but no project access."""
    # Import app and dependencies here to avoid loading during conftest import
    from src.main import app
    from src.api.dependencies import get_current_user_id
    from src.api.v1.routes.designs import get_llm_client, get_project_client
    from src.api.v1.routes.validations import get_project_client as get_project_client_validations
    from src.api.v1.routes.optimizations import (
        get_llm_client as get_llm_client_optimizations,
        get_project_client as get_project_client_optimizations
    )
    from src.api.v1.routes.comments import get_project_client as get_project_client_comments
    from src.api.v1.routes.export import get_project_client as get_project_client_export
    from src.api.v1.routes.files import get_project_client as get_project_client_files
    
    def override_get_db():
        try:
            yield db_session
        finally:
            pass
    
    def override_get_current_user_id():
        """Override authentication to return test user ID."""
        return test_user_id
    
    def override_get_llm_client():
        """Override LLM client with mock."""
        return mock_llm_client
    
    def override_get_project_client_denied():
        """Override project client with mock that denies access."""
        return mock_project_client_access_denied

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user_id] = override_get_current_user_id
    app.dependency_overrides[get_llm_client] = override_get_llm_client
    app.dependency_overrides[get_project_client] = override_get_project_client_denied
    app.dependency_overrides[get_project_client_validations] = override_get_project_client_denied
    app.dependency_overrides[get_llm_client_optimizations] = override_get_llm_client
    app.dependency_overrides[get_project_client_optimizations] = override_get_project_client_denied
    app.dependency_overrides[get_project_client_comments] = override_get_project_client_denied
    app.dependency_overrides[get_project_client_export] = override_get_project_client_denied
    app.dependency_overrides[get_project_client_files] = override_get_project_client_denied
    
    with TestClient(app) as test_client:
        yield test_client
    
    app.dependency_overrides.clear()


@pytest.fixture
def mock_llm_client():
    """Create a mock LLM client for testing."""
    from unittest.mock import Mock, AsyncMock
    
    mock_client = Mock()
    
    # Mock design generation response (async)
    mock_client.generate_design_specification = AsyncMock(return_value={
        "specification": {
            "building_info": {
                "type": "residential",
                "subtype": "single_family",
                "total_area": 250.5,
                "num_floors": 2,
                "height": 7.5
            },
            "structure": {
                "foundation_type": "slab",
                "wall_material": "concrete_block",
                "roof_type": "pitched",
                "roof_material": "clay_tiles"
            },
            "spaces": [
                {
                    "name": "Living Room",
                    "area": 35.0,
                    "floor": 1,
                    "dimensions": {"length": 7.0, "width": 5.0, "height": 3.0}
                }
            ]
        },
        "confidence_score": 85.5,
        "model_version": "gpt-4"
    })
    
    # Mock optimization generation response (async)
    mock_client.generate_optimizations = AsyncMock(return_value={
        "optimizations": [
            {
                "optimization_type": "cost",
                "title": "Use local materials",
                "description": "Replace imported materials with locally sourced alternatives",
                "estimated_cost_impact": -15.0,
                "implementation_difficulty": "easy",
                "priority": "high"
            },
            {
                "optimization_type": "structural",
                "title": "Optimize foundation depth",
                "description": "Reduce foundation depth based on soil analysis",
                "estimated_cost_impact": -8.0,
                "implementation_difficulty": "medium",
                "priority": "medium"
            },
            {
                "optimization_type": "sustainability",
                "title": "Add solar panels",
                "description": "Install rooftop solar panels for energy efficiency",
                "estimated_cost_impact": 5.0,
                "implementation_difficulty": "medium",
                "priority": "high"
            }
        ],
        "token_usage": {
            "prompt_tokens": 300,
            "completion_tokens": 500,
            "total_tokens": 800
        }
    })
    
    return mock_client


@pytest.fixture
def mock_project_client():
    """Create a mock project service client for testing."""
    from unittest.mock import Mock, AsyncMock
    
    mock_client = Mock()
    
    # Mock project access verification
    mock_client.verify_project_access = AsyncMock(return_value=True)
    
    # Mock project details retrieval
    mock_client.get_project_details = AsyncMock(return_value={
        "id": 1,
        "name": "Test Project",
        "description": "Test project description",
        "owner_id": 1,
        "status": "active"
    })
    
    return mock_client


@pytest.fixture
def mock_project_client_access_denied():
    """Create a mock project service client that denies access."""
    from unittest.mock import Mock, AsyncMock
    from src.services.project_client import ProjectAccessDeniedError
    
    mock_client = Mock()
    
    # Mock project access verification to raise access denied error
    mock_client.verify_project_access = AsyncMock(
        side_effect=ProjectAccessDeniedError("Access denied to project")
    )
    
    # Mock project details retrieval
    mock_client.get_project_details = AsyncMock(return_value={
        "id": 1,
        "name": "Test Project",
        "description": "Test project description",
        "owner_id": 1,
        "status": "active"
    })
    
    return mock_client


@pytest.fixture
def mock_user_client():
    """Create a mock user service client for testing."""
    from unittest.mock import Mock, AsyncMock
    
    mock_client = Mock()
    
    # Mock user details retrieval
    mock_client.get_user_details = AsyncMock(return_value={
        "id": 1,
        "email": "test@example.com",
        "username": "testuser",
        "first_name": "Test",
        "last_name": "User",
        "is_active": True
    })
    
    # Mock user verification
    mock_client.verify_user = AsyncMock(return_value=True)
    
    return mock_client


@pytest.fixture
def mock_external_services(mock_llm_client, mock_project_client, mock_user_client):
    """Provide all mock external services."""
    return {
        "llm": mock_llm_client,
        "project": mock_project_client,
        "user": mock_user_client
    }


@pytest.fixture
def test_user_id():
    """Provide a test user ID."""
    return 1


@pytest.fixture
def test_project_id():
    """Provide a test project ID."""
    return 1


@pytest.fixture
def auth_headers(test_user_id):
    """Create authorization headers for testing."""
    return {"Authorization": f"Bearer test-token-{test_user_id}"}


@pytest.fixture
def mock_auth_user(monkeypatch):
    """Mock authentication to return a test user."""
    from src.api.dependencies import get_current_user_id
    
    def mock_get_current_user_id():
        return 1
    
    monkeypatch.setattr("src.api.dependencies.get_current_user_id", mock_get_current_user_id)
    return 1


@pytest.fixture
def mock_project_access(monkeypatch):
    """Mock project access verification to allow access."""
    from unittest.mock import AsyncMock
    
    async def mock_verify_project_access(project_id: int, user_id: int):
        return True
    
    monkeypatch.setattr(
        "src.services.project_client.ProjectClient.verify_project_access",
        AsyncMock(return_value=True)
    )


@pytest.fixture
def mock_project_access_denied(monkeypatch):
    """Mock project access verification to deny access."""
    from unittest.mock import AsyncMock
    from src.services.project_client import ProjectAccessDeniedError
    
    async def mock_verify_project_access_denied(project_id: int, user_id: int):
        raise ProjectAccessDeniedError(f"Access denied to project {project_id}")
    
    monkeypatch.setattr(
        "src.services.project_client.ProjectClient.verify_project_access",
        AsyncMock(side_effect=ProjectAccessDeniedError("Access denied"))
    )


# Database cleanup fixture for integration tests
@pytest.fixture(scope="function")
def clean_db(db_session):
    """Ensure clean database state for each test."""
    yield db_session
    
    # Clean up any remaining data
    db_session.rollback()


# Performance testing fixture
@pytest.fixture
def performance_db_session(db_engine):
    """Create a session for performance testing with different configuration."""
    SessionLocal = sessionmaker(bind=db_engine, autoflush=False, autocommit=False)
    session = SessionLocal()
    
    # Import and configure factories
    from .factories import (
        DesignFactory,
        DesignValidationFactory,
        DesignOptimizationFactory,
        DesignFileFactory,
        DesignCommentFactory
    )
    
    DesignFactory._meta.sqlalchemy_session = session
    DesignValidationFactory._meta.sqlalchemy_session = session
    DesignOptimizationFactory._meta.sqlalchemy_session = session
    DesignFileFactory._meta.sqlalchemy_session = session
    DesignCommentFactory._meta.sqlalchemy_session = session
    
    try:
        yield session
    finally:
        session.close()
