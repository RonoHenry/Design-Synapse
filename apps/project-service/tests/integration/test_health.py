"""Integration tests for health endpoints."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from src.main import app


@pytest.fixture
def client(db_session: Session) -> TestClient:
    """Create a test client with database session override."""
    from src.infrastructure.database import get_db

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    yield TestClient(app)
    app.dependency_overrides.clear()


def test_basic_health_check(client: TestClient):
    """Test basic health check endpoint."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "project-service"
    assert "timestamp" in data
    assert data["version"] == "1.0.0"


def test_readiness_check(client: TestClient):
    """Test readiness check endpoint."""
    response = client.get("/api/v1/ready")
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "ready"
    assert data["service"] == "project-service"
    assert "timestamp" in data
    assert "checks" in data
    assert "database" in data["checks"]
    assert data["checks"]["database"]["status"] == "healthy"


def test_detailed_health_check(client: TestClient):
    """Test detailed health check endpoint."""
    response = client.get("/api/v1/health/detailed")
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "project-service"
    assert "timestamp" in data
    assert data["version"] == "1.0.0"
    assert "checks" in data

    # Check that database check is present
    assert "database" in data["checks"]
    assert data["checks"]["database"]["status"] == "healthy"

    # Check that database config check is present
    assert "database_config" in data["checks"]


def test_metrics_endpoint(client: TestClient):
    """Test metrics endpoint."""
    response = client.get("/api/v1/metrics")
    assert response.status_code == 200

    data = response.json()
    assert data["service"] == "project-service"
    assert "timestamp" in data
    assert "metrics" in data
    assert "projects_total" in data["metrics"]
    assert "comments_total" in data["metrics"]
    assert isinstance(data["metrics"]["projects_total"], int)
    assert isinstance(data["metrics"]["comments_total"], int)
