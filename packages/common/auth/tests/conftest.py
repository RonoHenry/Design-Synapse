"""Pytest configuration and fixtures for authentication tests."""

import os
from datetime import datetime, timedelta, timezone

import pytest
from jose import jwt

from ..models import TokenPayload, UserContext
from ..service_auth import ServiceAuthenticator
from ..validator import JWTValidator


@pytest.fixture(scope="session")
def test_secret_key():
    """Test secret key for JWT operations."""
    return "test-secret-key-for-authentication-tests"


@pytest.fixture(scope="session")
def test_service_secret():
    """Test secret key for service authentication."""
    return "test-service-secret-key-for-auth-tests"


@pytest.fixture
def jwt_validator(test_secret_key):
    """JWT validator instance for tests."""
    return JWTValidator(secret_key=test_secret_key)


@pytest.fixture
def service_authenticator(test_service_secret):
    """Service authenticator instance for tests."""
    return ServiceAuthenticator(secret_key=test_service_secret)


@pytest.fixture
def sample_user_context():
    """Sample user context for testing."""
    return UserContext(
        user_id="test-user-123",
        email="test@example.com",
        roles=["designer", "viewer"],
        permissions=["read:projects", "write:designs", "read:knowledge"],
    )


@pytest.fixture
def admin_user_context():
    """Admin user context for testing."""
    return UserContext(
        user_id="admin-user-456",
        email="admin@example.com",
        roles=["admin"],
        permissions=["read:all", "write:all", "manage:users", "manage:projects"],
    )


@pytest.fixture
def service_user_context():
    """Service user context for testing."""
    return UserContext(
        user_id="service:test-service",
        email="test-service@internal.service",
        roles=["service"],
        permissions=["service:internal", "read:all", "write:all"],
        service_name="test-service",
    )


@pytest.fixture
def viewer_user_context():
    """Viewer user context for testing."""
    return UserContext(
        user_id="viewer-user-789",
        email="viewer@example.com",
        roles=["viewer"],
        permissions=["read:projects", "read:designs", "read:knowledge"],
    )


@pytest.fixture
def valid_jwt_token(test_secret_key, sample_user_context):
    """Valid JWT token for testing."""
    now = datetime.now(timezone.utc)
    payload = {
        "sub": sample_user_context.user_id,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(hours=1)).timestamp()),
        "roles": sample_user_context.roles,
        "permissions": sample_user_context.permissions,
    }
    return jwt.encode(payload, test_secret_key, algorithm="HS256")


@pytest.fixture
def expired_jwt_token(test_secret_key):
    """Expired JWT token for testing."""
    past_time = datetime.now(timezone.utc) - timedelta(hours=2)
    payload = {
        "sub": "expired-user",
        "iat": int((past_time - timedelta(hours=1)).timestamp()),
        "exp": int(past_time.timestamp()),  # Expired
        "roles": ["viewer"],
        "permissions": ["read:projects"],
    }
    return jwt.encode(payload, test_secret_key, algorithm="HS256")


@pytest.fixture
def admin_jwt_token(test_secret_key, admin_user_context):
    """Admin JWT token for testing."""
    now = datetime.now(timezone.utc)
    payload = {
        "sub": admin_user_context.user_id,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(hours=1)).timestamp()),
        "roles": admin_user_context.roles,
        "permissions": admin_user_context.permissions,
    }
    return jwt.encode(payload, test_secret_key, algorithm="HS256")


@pytest.fixture
def service_jwt_token(test_service_secret, service_user_context):
    """Service JWT token for testing."""
    now = datetime.now(timezone.utc)
    payload = {
        "sub": service_user_context.service_name,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(hours=24)).timestamp()),
        "service": service_user_context.service_name,
        "type": "service",
        "roles": service_user_context.roles,
        "permissions": service_user_context.permissions,
    }
    return jwt.encode(payload, test_service_secret, algorithm="HS256")


@pytest.fixture(autouse=True)
def setup_test_environment(monkeypatch, test_secret_key, test_service_secret):
    """Setup test environment variables."""
    monkeypatch.setenv("SECRET_KEY", test_secret_key)
    monkeypatch.setenv("SERVICE_SECRET_KEY", test_service_secret)
    monkeypatch.setenv("SERVICE_TOKEN_EXPIRY_HOURS", "24")


@pytest.fixture
def mock_request():
    """Mock FastAPI request object."""
    from unittest.mock import Mock

    from fastapi import Request

    request = Mock(spec=Request)
    request.state = Mock()
    request.headers = {}
    request.url = Mock()
    request.url.path = "/api/v1/test"
    request.method = "GET"
    request.client = Mock()
    request.client.host = "127.0.0.1"

    return request


# Test data constants
TEST_ENDPOINTS = {
    "public": ["/health", "/docs", "/redoc", "/openapi.json"],
    "admin": ["/api/v1/admin/users", "/api/v1/admin/settings"],
    "projects": ["/api/v1/projects", "/api/v1/projects/123"],
    "designs": ["/api/v1/designs", "/api/v1/designs/456"],
    "knowledge": ["/api/v1/knowledge/search", "/api/v1/knowledge/resources"],
}


TEST_ROLES = {
    "admin": ["admin"],
    "project_manager": ["project_manager"],
    "designer": ["designer"],
    "viewer": ["viewer"],
    "service": ["service"],
    "multi_role": ["designer", "viewer"],
}


TEST_PERMISSIONS = {
    "admin": ["read:all", "write:all", "manage:users", "manage:projects"],
    "designer": ["read:projects", "write:designs", "read:knowledge", "write:knowledge"],
    "viewer": ["read:projects", "read:designs", "read:knowledge"],
    "service": ["service:internal", "read:all", "write:all"],
}
