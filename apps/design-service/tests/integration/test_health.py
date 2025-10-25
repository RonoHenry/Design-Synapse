"""Integration tests for health and readiness endpoints."""

import os
from unittest.mock import Mock, patch, MagicMock

import pytest
from fastapi.testclient import TestClient

from src.main import app


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


def create_mock_config():
    """Create a mock config that doesn't have circular references."""
    # Create a simple class to avoid Mock circular references
    class SimpleDatabase:
        ssl_ca = None
    
    mock_config = MagicMock()
    mock_config.get_database_url.return_value = "mysql+pymysql://user:pass@localhost/db"
    mock_config.database = SimpleDatabase()
    
    return mock_config


def create_db_health_result(is_healthy=True, message="", **kwargs):
    """Create a database health result object without Mock circular references."""
    class HealthResult:
        pass
    
    result = HealthResult()
    result.is_healthy = is_healthy
    result.message = message
    result.response_time_ms = kwargs.get('response_time_ms')
    result.database_version = kwargs.get('database_version')
    result.ssl_enabled = kwargs.get('ssl_enabled')
    result.error = kwargs.get('error')
    
    return result


class TestHealthEndpoint:
    """Tests for GET /health endpoint."""

    def test_health_returns_service_status(self, client):
        """Test that /health returns service status."""
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "healthy"
        assert data["service"] == "design-service"
        assert data["version"] == "1.0.0"

    def test_health_endpoint_always_returns_200(self, client):
        """Test that /health always returns 200 regardless of dependencies."""
        # Health should return 200 even if other services are down
        response = client.get("/health")
        assert response.status_code == 200


class TestReadinessEndpoint:
    """Tests for GET /ready endpoint."""

    def test_ready_checks_database_connectivity(self, client):
        """Test that /ready checks database connectivity."""
        with patch("src.main.check_database_health") as mock_health, \
             patch("src.main.get_settings") as mock_settings, \
             patch("src.main.check_ai_service_health") as mock_ai_health:
            
            # Mock settings
            mock_settings.return_value = create_mock_config()
            
            # Mock successful database connection
            mock_health.return_value = create_db_health_result(
                is_healthy=True,
                message="Database connection successful",
                response_time_ms=15.5,
                database_version="8.0.11-TiDB-v7.5.0",
                ssl_enabled=True,
            )
            
            # Mock AI service healthy
            mock_ai_health.return_value = {
                "healthy": True,
                "message": "AI service available",
            }
            
            response = client.get("/ready")
            
            assert response.status_code == 200
            data = response.json()
            
            assert data["status"] == "ready"
            assert data["service"] == "design-service"
            assert "checks" in data
            assert "database" in data["checks"]
            assert data["checks"]["database"]["healthy"] is True

    def test_ready_checks_ai_service_availability(self, client):
        """Test that /ready checks AI service availability."""
        with patch("src.main.check_database_health") as mock_db_health, \
             patch("src.main.check_ai_service_health") as mock_ai_health, \
             patch("src.main.get_settings") as mock_settings:
            
            # Mock settings
            mock_settings.return_value = create_mock_config()
            
            # Mock successful checks
            mock_db_health.return_value = create_db_health_result(
                is_healthy=True,
                message="Database connection successful",
            )
            mock_ai_health.return_value = {
                "healthy": True,
                "message": "AI service available",
            }
            
            response = client.get("/ready")
            
            assert response.status_code == 200
            data = response.json()
            
            assert "checks" in data
            assert "ai_service" in data["checks"]
            assert data["checks"]["ai_service"]["healthy"] is True

    def test_ready_returns_unhealthy_when_database_down(self, client):
        """Test that /ready returns unhealthy status when database is down."""
        with patch("src.main.check_database_health") as mock_health, \
             patch("src.main.get_settings") as mock_settings, \
             patch("src.main.check_ai_service_health") as mock_ai_health:
            
            # Mock settings
            mock_settings.return_value = create_mock_config()
            
            # Mock failed database connection
            mock_health.return_value = create_db_health_result(
                is_healthy=False,
                message="Database connection failed after 3 attempts",
                error="Connection refused",
            )
            
            # Mock AI service healthy
            mock_ai_health.return_value = {
                "healthy": True,
                "message": "AI service available",
            }
            
            response = client.get("/ready")
            
            assert response.status_code == 503
            data = response.json()
            
            assert data["status"] == "unhealthy"
            assert data["service"] == "design-service"
            assert "checks" in data
            assert "database" in data["checks"]
            assert data["checks"]["database"]["healthy"] is False
            assert "error" in data["checks"]["database"]

    def test_ready_returns_unhealthy_when_ai_service_unavailable(self, client):
        """Test that /ready returns unhealthy when AI service is unavailable."""
        with patch("src.main.check_database_health") as mock_db_health, \
             patch("src.main.check_ai_service_health") as mock_ai_health, \
             patch("src.main.get_settings") as mock_settings:
            
            # Mock settings
            mock_settings.return_value = create_mock_config()
            
            # Mock database healthy but AI service down
            mock_db_health.return_value = create_db_health_result(
                is_healthy=True,
                message="Database connection successful",
            )
            mock_ai_health.return_value = {
                "healthy": False,
                "message": "AI service unavailable",
                "error": "API key not configured",
            }
            
            response = client.get("/ready")
            
            assert response.status_code == 503
            data = response.json()
            
            assert data["status"] == "unhealthy"
            assert "checks" in data
            assert "ai_service" in data["checks"]
            assert data["checks"]["ai_service"]["healthy"] is False

    def test_ready_returns_unhealthy_when_all_services_down(self, client):
        """Test that /ready returns unhealthy when all services are down."""
        with patch("src.main.check_database_health") as mock_db_health, \
             patch("src.main.check_ai_service_health") as mock_ai_health, \
             patch("src.main.get_settings") as mock_settings:
            
            # Mock settings
            mock_settings.return_value = create_mock_config()
            
            # Mock all services down
            mock_db_health.return_value = create_db_health_result(
                is_healthy=False,
                message="Database connection failed",
                error="Connection timeout",
            )
            mock_ai_health.return_value = {
                "healthy": False,
                "message": "AI service unavailable",
                "error": "Network error",
            }
            
            response = client.get("/ready")
            
            assert response.status_code == 503
            data = response.json()
            
            assert data["status"] == "unhealthy"
            assert data["checks"]["database"]["healthy"] is False
            assert data["checks"]["ai_service"]["healthy"] is False

    def test_ready_includes_response_time_metrics(self, client):
        """Test that /ready includes response time metrics."""
        with patch("src.main.check_database_health") as mock_db_health, \
             patch("src.main.check_ai_service_health") as mock_ai_health, \
             patch("src.main.get_settings") as mock_settings:
            
            # Mock settings
            mock_settings.return_value = create_mock_config()
            
            mock_db_health.return_value = create_db_health_result(
                is_healthy=True,
                message="Database connection successful",
                response_time_ms=12.34,
            )
            mock_ai_health.return_value = {
                "healthy": True,
                "message": "AI service available",
            }
            
            response = client.get("/ready")
            
            assert response.status_code == 200
            data = response.json()
            
            assert "checks" in data
            assert "database" in data["checks"]
            assert "response_time_ms" in data["checks"]["database"]
            assert data["checks"]["database"]["response_time_ms"] == 12.34

    def test_ready_includes_database_version(self, client):
        """Test that /ready includes database version information."""
        with patch("src.main.check_database_health") as mock_db_health, \
             patch("src.main.check_ai_service_health") as mock_ai_health, \
             patch("src.main.get_settings") as mock_settings:
            
            # Mock settings
            mock_settings.return_value = create_mock_config()
            
            mock_db_health.return_value = create_db_health_result(
                is_healthy=True,
                message="Database connection successful",
                database_version="8.0.11-TiDB-v7.5.0",
                ssl_enabled=True,
            )
            mock_ai_health.return_value = {
                "healthy": True,
                "message": "AI service available",
            }
            
            response = client.get("/ready")
            
            assert response.status_code == 200
            data = response.json()
            
            assert "checks" in data
            assert "database" in data["checks"]
            assert "database_version" in data["checks"]["database"]
            assert "TiDB" in data["checks"]["database"]["database_version"]
            assert data["checks"]["database"]["ssl_enabled"] is True
