"""Integration tests for knowledge service health endpoints."""

from unittest.mock import Mock, patch

import pytest
from fastapi.testclient import TestClient
from knowledge_service.main import app
from sqlalchemy import text


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


class TestHealthEndpoints:
    """Test health check endpoints."""

    def test_basic_health_check(self, client):
        """Test basic health check endpoint."""
        response = client.get("/api/v1/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "knowledge-service"
        assert "timestamp" in data
        assert data["version"] == "1.0.0"

    def test_detailed_health_check_healthy(self, client, db_session):
        """Test detailed health check when all services are healthy."""
        # Mock database connection to be healthy
        with patch.object(db_session, "execute") as mock_execute:
            mock_execute.return_value = None

            response = client.get("/api/v1/health/detailed")

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"
            assert data["service"] == "knowledge-service"
            assert "checks" in data
            assert data["checks"]["database"]["status"] == "healthy"

    def test_detailed_health_check_database_failure(self, client):
        """Test detailed health check when database fails."""
        with patch("knowledge_service.infrastructure.database.get_db") as mock_get_db:
            mock_session = Mock()
            mock_session.execute.side_effect = Exception("Database connection failed")
            mock_get_db.return_value = mock_session

            response = client.get("/api/v1/health/detailed")

            assert response.status_code == 503
            data = response.json()["detail"]
            assert data["status"] == "unhealthy"
            assert data["checks"]["database"]["status"] == "unhealthy"
            assert "Database connection failed" in data["checks"]["database"]["message"]

    def test_detailed_health_check_vector_search_configured(self, client, db_session):
        """Test detailed health check with vector search configured."""
        with patch("knowledge_service.core.config.settings") as mock_settings:
            mock_settings.vector.provider = Mock()
            mock_settings.vector.provider.value = "pinecone"
            mock_settings.vector.api_key = "test-key"
            mock_settings.vector.environment = "test-env"

            response = client.get("/api/v1/health/detailed")

            assert response.status_code == 200
            data = response.json()
            assert data["checks"]["pinecone"]["status"] == "healthy"
            assert data["checks"]["pinecone"]["provider"] == "pinecone"

    def test_detailed_health_check_llm_service_configured(self, client, db_session):
        """Test detailed health check with LLM service configured."""
        with patch("knowledge_service.core.config.settings") as mock_settings:
            mock_settings.llm.primary_provider = Mock()
            mock_settings.llm.primary_provider.value = "openai"
            mock_settings.llm.fallback_providers = []
            mock_settings.llm.get_provider_config.return_value = {"api_key": "test-key"}

            response = client.get("/api/v1/health/detailed")

            assert response.status_code == 200
            data = response.json()
            assert data["checks"]["llm_service"]["status"] == "healthy"
            assert data["checks"]["llm_service"]["primary_provider"] == "openai"

    def test_detailed_health_check_file_storage_accessible(self, client, db_session):
        """Test detailed health check with accessible file storage."""
        with patch("os.path.exists", return_value=True):
            with patch("os.access", return_value=True):
                response = client.get("/api/v1/health/detailed")

                assert response.status_code == 200
                data = response.json()
                assert data["checks"]["file_storage"]["status"] == "healthy"

    def test_detailed_health_check_file_storage_not_accessible(
        self, client, db_session
    ):
        """Test detailed health check with inaccessible file storage."""
        with patch("os.path.exists", return_value=False):
            response = client.get("/api/v1/health/detailed")

            assert response.status_code == 503
            data = response.json()["detail"]
            assert data["status"] == "unhealthy"
            assert data["checks"]["file_storage"]["status"] == "unhealthy"

    def test_readiness_check_ready(self, client, db_session):
        """Test readiness check when service is ready."""
        with patch("knowledge_service.core.config.settings") as mock_settings:
            mock_settings.file_processing.storage_path = "/tmp/storage"
            mock_settings.file_processing.temp_path = "/tmp/temp"

            with patch("os.path.exists", return_value=True):
                with patch("os.makedirs") as mock_makedirs:
                    response = client.get("/api/v1/ready")

                    assert response.status_code == 200
                    data = response.json()
                    assert data["status"] == "ready"
                    assert data["checks"]["database"]["status"] == "ready"
                    assert data["checks"]["file_storage"]["status"] == "ready"

    def test_readiness_check_not_ready_database(self, client):
        """Test readiness check when database is not ready."""
        with patch("knowledge_service.infrastructure.database.get_db") as mock_get_db:
            mock_session = Mock()
            mock_session.execute.side_effect = Exception("Database not ready")
            mock_get_db.return_value = mock_session

            response = client.get("/api/v1/ready")

            assert response.status_code == 503
            data = response.json()["detail"]
            assert data["status"] == "not_ready"
            assert data["checks"]["database"]["status"] == "not_ready"

    def test_liveness_check(self, client):
        """Test liveness check endpoint."""
        response = client.get("/api/v1/health/live")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "alive"
        assert data["service"] == "knowledge-service"
        assert "timestamp" in data

    def test_metrics_endpoint(self, client, db_session):
        """Test metrics endpoint."""
        # Mock database queries for metrics
        with patch.object(db_session, "execute") as mock_execute:
            mock_execute.side_effect = [
                Mock(scalar=lambda: 10),  # resources count
                Mock(scalar=lambda: 5),  # topics count
                Mock(scalar=lambda: 3),  # bookmarks count
            ]

            response = client.get("/api/v1/metrics")

            assert response.status_code == 200
            data = response.json()
            assert data["service"] == "knowledge-service"
            assert data["metrics"]["resources_total"] == 10
            assert data["metrics"]["topics_total"] == 5
            assert data["metrics"]["bookmarks_total"] == 3

    def test_metrics_endpoint_database_error(self, client):
        """Test metrics endpoint when database fails."""
        with patch("knowledge_service.infrastructure.database.get_db") as mock_get_db:
            mock_session = Mock()
            mock_session.execute.side_effect = Exception("Database error")
            mock_get_db.return_value = mock_session

            response = client.get("/api/v1/metrics")

            assert response.status_code == 500
            assert "Failed to retrieve metrics" in response.json()["detail"]

    def test_dependencies_check_success(self, client):
        """Test dependencies check when all services are healthy."""
        with patch(
            "packages.common.monitoring.health.get_health_aggregator"
        ) as mock_get_aggregator:
            mock_aggregator.return_value.check_all_services_health.return_value = Mock(
                overall_status=Mock(value="healthy"),
                services=[
                    Mock(
                        service_name="user-service",
                        status=Mock(value="healthy"),
                        message="Service is healthy",
                        response_time_ms=50,
                        timestamp=Mock(isoformat=lambda: "2023-01-01T00:00:00"),
                    )
                ],
            )

            response = client.get("/api/v1/health/dependencies")

            assert response.status_code == 200
            data = response.json()
            assert data["dependencies"]["overall_status"] == "healthy"
            assert len(data["dependencies"]["services"]) == 1

    def test_dependencies_check_error(self, client):
        """Test dependencies check when there's an error."""
        with patch(
            "packages.common.monitoring.health.get_health_aggregator"
        ) as mock_get_aggregator:
            mock_get_aggregator.return_value.check_all_services_health.side_effect = (
                Exception("Service error")
            )

            response = client.get("/api/v1/health/dependencies")

            assert response.status_code == 200
            data = response.json()
            assert data["dependencies"]["overall_status"] == "error"
            assert "Service error" in data["dependencies"]["error"]
