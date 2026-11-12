"""Test configuration for security hardening tests."""

from unittest.mock import AsyncMock, Mock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from packages.common.security.middleware import SecurityHardeningMiddleware


@pytest.fixture
def app():
    """Create FastAPI app for testing."""
    app = FastAPI()

    @app.get("/test")
    async def test_endpoint():
        return {"message": "test"}

    @app.post("/test-input")
    async def test_input_endpoint(data: dict):
        return {"received": data}

    @app.get("/admin")
    async def admin_endpoint():
        return {"message": "admin"}

    @app.post("/auth/login")
    async def auth_login_endpoint(data: dict):
        # Always return failure for testing
        return {"error": "invalid_credentials"}, 401

    @app.get("/health")
    async def health_endpoint():
        return {"status": "ok"}

    return app


@pytest.fixture
def client(app):
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def security_middleware():
    """Create security middleware for testing."""
    return SecurityHardeningMiddleware(
        app=Mock(),
        enable_input_validation=True,
        enable_threat_detection=True,
        enable_audit_logging=True,
    )


@pytest.fixture
def mock_redis():
    """Mock Redis client for testing."""
    redis_mock = Mock()
    redis_mock.get = AsyncMock(return_value=None)
    redis_mock.set = AsyncMock(return_value=True)
    redis_mock.incr = AsyncMock(return_value=1)
    redis_mock.expire = AsyncMock(return_value=True)
    redis_mock.delete = AsyncMock(return_value=1)
    return redis_mock


@pytest.fixture
def malicious_payloads():
    """Common malicious payloads for testing."""
    return {
        "sql_injection": [
            "'; DROP TABLE users; --",
            "1' OR '1'='1",
            "admin'--",
            "' UNION SELECT * FROM users --",
        ],
        "xss": [
            "<script>alert('xss')</script>",
            "javascript:alert('xss')",
            "<img src=x onerror=alert('xss')>",
            "';alert(String.fromCharCode(88,83,83))//';alert(String.fromCharCode(88,83,83))//",
        ],
        "command_injection": ["; rm -rf /", "| cat /etc/passwd", "&& whoami", "`id`"],
        "path_traversal": [
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32\\config\\sam",
            "%2e%2e%2f%2e%2e%2f%2e%2e%2fetc%2fpasswd",
        ],
    }


@pytest.fixture
def suspicious_patterns():
    """Suspicious activity patterns for testing."""
    return {
        "brute_force": {"failed_attempts": 10, "time_window": 300},  # 5 minutes
        "rate_abuse": {"requests_per_minute": 1000, "threshold": 100},
        "suspicious_user_agents": ["sqlmap", "nikto", "nmap", "burp", "w3af"],
        "blocked_countries": ["XX", "YY"],  # Test country codes
        "tor_exit_nodes": ["192.168.1.100", "10.0.0.1"],  # Test IPs
    }
