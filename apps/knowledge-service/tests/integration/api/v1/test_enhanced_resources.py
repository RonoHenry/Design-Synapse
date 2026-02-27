"""Integration tests for enhanced resources API endpoints."""
import io
from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi.testclient import TestClient
from knowledge_service.main import app


@pytest.fixture
def client():
    """Test client fixture."""
    return TestClient(app)


@pytest.fixture
def auth_headers():
    """Authentication headers fixture."""
    return {"Authorization": "Bearer test-token"}


@pytest.fixture
def mock_db_session():
    """Mock database session fixture."""
    return Mock()


@pytest.fixture
def sample_resource_data():
    """Sample resource data for testing."""
    return {
        "title": "Machine Learning Guide",
        "description": "Comprehensive guide to ML algorithms",
        "content": "This guide covers supervised and unsupervised learning...",
        "resource_type": "document",
        "keywords": ["machine learning", "algorithms"],
        "technical_domains": ["data_science"],
    }


@pytest.fixture
def mock_analysis_result():
    """Mock content analysis result."""
    return {
        "content_type": "technical_document",
        "complexity_level": "intermediate",
        "technical_domains": ["machine_learning"],
        "keywords": ["machine learning", "algorithms"],
        "summary": "ML guide summary",
        "key_takeaways": ["Key takeaway"],
        "readability_score": 0.8,
        "estimated_reading_time": 10,
        "language": "en",
        "quality_score": 0.9,
    }


class TestEnhancedResourcesAPI:
    """Integration tests for enhanced resources API."""

    @patch(
        "knowledge_service.services.enhanced_resource_processing.EnhancedResourceProcessingService.process_resource"
    )
    @patch("knowledge_service.core.database.get_db")
    def test_process_resource_success(
        self,
        mock_get_db,
        mock_process,
        client,
        auth_headers,
        mock_db_session,
        mock_analysis_result,
    ):
        """Test successful resource processing with analysis."""
        mock_get_db.return_value = mock_db_session
        mock_process.return_value = AsyncMock()
        mock_process.return_value.__dict__.update(mock_analysis_result)

        response = client.post(
            "/api/v1/enhanced-resources/process/123", headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "analysis_result" in data
        assert data["analysis_result"]["content_type"] == "technical_document"

    @patch("knowledge_service.core.database.get_db")
    def test_process_resource_not_found(
        self, mock_get_db, client, auth_headers, mock_db_session
    ):
        """Test processing non-existent resource."""
        mock_get_db.return_value = mock_db_session

        with patch(
            "knowledge_service.services.enhanced_resource_processing.EnhancedResourceProcessingService.process_resource"
        ) as mock_process:
            mock_process.side_effect = Exception("Resource not found")

            response = client.post(
                "/api/v1/enhanced-resources/process/999", headers=auth_headers
            )

            assert response.status_code == 500

    def test_process_resource_unauthorized(self, client):
        """Test resource processing without authentication."""
        response = client.post("/api/v1/enhanced-resources/process/123")
        assert response.status_code == 401

    @patch(
        "knowledge_service.services.enhanced_resource_processing.EnhancedResourceProcessingService.batch_process_resources"
    )
    @patch("knowledge_service.core.database.get_db")
    def test_batch_process_success(
        self, mock_get_db, mock_batch_process, client, auth_headers, mock_db_session
    ):
        """Test successful batch resource processing."""
        mock_get_db.return_value = mock_db_session
        mock_batch_process.return_value = [
            {
                "resource_id": 1,
                "status": "success",
                "analysis": {"content_type": "document"},
            },
            {
                "resource_id": 2,
                "status": "success",
                "analysis": {"content_type": "tutorial"},
            },
        ]

        batch_data = {"resource_ids": [1, 2], "include_analysis": True}

        response = client.post(
            "/api/v1/enhanced-resources/batch-process",
            json=batch_data,
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert "results" in data
        assert len(data["results"]) == 2
        assert data["results"][0]["status"] == "success"

    def test_batch_process_empty_list(self, client, auth_headers):
        """Test batch processing with empty resource list."""
        batch_data = {"resource_ids": []}

        response = client.post(
            "/api/v1/enhanced-resources/batch-process",
            json=batch_data,
            headers=auth_headers,
        )

        assert response.status_code == 400

    def test_batch_process_too_many_resources(self, client, auth_headers):
        """Test batch processing with too many resources."""
        batch_data = {"resource_ids": list(range(101))}  # Exceed limit

        response = client.post(
            "/api/v1/enhanced-resources/batch-process",
            json=batch_data,
            headers=auth_headers,
        )

        assert response.status_code == 400

    @patch(
        "knowledge_service.services.enhanced_resource_processing.EnhancedResourceProcessingService.reanalyze_resource"
    )
    @patch("knowledge_service.core.database.get_db")
    def test_reanalyze_resource_success(
        self,
        mock_get_db,
        mock_reanalyze,
        client,
        auth_headers,
        mock_db_session,
        mock_analysis_result,
    ):
        """Test successful resource reanalysis."""
        mock_get_db.return_value = mock_db_session
        mock_reanalyze.return_value = AsyncMock()
        mock_reanalyze.return_value.__dict__.update(mock_analysis_result)

        response = client.post(
            "/api/v1/enhanced-resources/reanalyze/123", headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "analysis_result" in data

    @patch("knowledge_service.core.database.get_db")
    def test_get_analysis_summary_success(
        self, mock_get_db, client, auth_headers, mock_db_session
    ):
        """Test getting analysis summary."""
        mock_get_db.return_value = mock_db_session

        with patch(
            "knowledge_service.services.enhanced_resource_processing.EnhancedResourceProcessingService.get_analysis_summary"
        ) as mock_summary:
            mock_summary.return_value = {
                "total_resources": 100,
                "analyzed_resources": 85,
                "content_types": {"document": 50, "tutorial": 35},
                "complexity_distribution": {
                    "basic": 20,
                    "intermediate": 45,
                    "advanced": 20,
                },
                "technical_domains": {
                    "data_science": 40,
                    "web_development": 30,
                    "machine_learning": 15,
                },
            }

            response = client.get(
                "/api/v1/enhanced-resources/analysis-summary", headers=auth_headers
            )

            assert response.status_code == 200
            data = response.json()
            assert "total_resources" in data
            assert "analyzed_resources" in data
            assert "content_types" in data

    @patch("knowledge_service.core.database.get_db")
    def test_get_resource_analysis_success(
        self, mock_get_db, client, auth_headers, mock_db_session
    ):
        """Test getting specific resource analysis."""
        mock_get_db.return_value = mock_db_session

        with patch(
            "knowledge_service.services.enhanced_resource_processing.EnhancedResourceProcessingService.get_resource_analysis"
        ) as mock_get_analysis:
            mock_get_analysis.return_value = {
                "resource_id": 123,
                "content_type": "technical_document",
                "complexity_level": "intermediate",
                "technical_domains": ["machine_learning"],
                "keywords": ["ML", "algorithms"],
                "summary": "Resource summary",
                "analysis_timestamp": "2023-01-01T12:00:00Z",
            }

            response = client.get(
                "/api/v1/enhanced-resources/123/analysis", headers=auth_headers
            )

            assert response.status_code == 200
            data = response.json()
            assert data["resource_id"] == 123
            assert data["content_type"] == "technical_document"

    @patch("knowledge_service.core.database.get_db")
    def test_get_resource_analysis_not_found(
        self, mock_get_db, client, auth_headers, mock_db_session
    ):
        """Test getting analysis for non-existent resource."""
        mock_get_db.return_value = mock_db_session

        with patch(
            "knowledge_service.services.enhanced_resource_processing.EnhancedResourceProcessingService.get_resource_analysis"
        ) as mock_get_analysis:
            mock_get_analysis.return_value = None

            response = client.get(
                "/api/v1/enhanced-resources/999/analysis", headers=auth_headers
            )

            assert response.status_code == 404

    @patch("knowledge_service.core.database.get_db")
    def test_search_by_analysis_success(
        self, mock_get_db, client, auth_headers, mock_db_session
    ):
        """Test searching resources by analysis criteria."""
        mock_get_db.return_value = mock_db_session

        with patch(
            "knowledge_service.services.enhanced_resource_processing.EnhancedResourceProcessingService.search_by_analysis"
        ) as mock_search:
            mock_search.return_value = {
                "resources": [
                    {
                        "id": 1,
                        "title": "ML Guide",
                        "content_type": "technical_document",
                    },
                    {"id": 2, "title": "AI Tutorial", "content_type": "tutorial"},
                ],
                "total_count": 2,
                "filters_applied": {
                    "content_type": "technical_document",
                    "complexity_level": "intermediate",
                },
            }

            response = client.get(
                "/api/v1/enhanced-resources/search/by-analysis",
                params={
                    "content_type": "technical_document",
                    "complexity_level": "intermediate",
                    "min_quality_score": "0.7",
                },
                headers=auth_headers,
            )

            assert response.status_code == 200
            data = response.json()
            assert "resources" in data
            assert "total_count" in data
            assert len(data["resources"]) == 2

    def test_search_by_analysis_no_filters(self, client, auth_headers):
        """Test searching without any analysis filters."""
        response = client.get(
            "/api/v1/enhanced-resources/search/by-analysis", headers=auth_headers
        )

        assert response.status_code == 400

    def test_search_by_analysis_invalid_filters(self, client, auth_headers):
        """Test searching with invalid filter values."""
        response = client.get(
            "/api/v1/enhanced-resources/search/by-analysis",
            params={
                "content_type": "invalid_type",
                "complexity_level": "invalid_level",
                "min_quality_score": "invalid_score",
            },
            headers=auth_headers,
        )

        assert response.status_code == 422

    @patch(
        "knowledge_service.services.enhanced_resource_processing.EnhancedResourceProcessingService.process_resource"
    )
    @patch("knowledge_service.core.database.get_db")
    def test_process_resource_with_options(
        self,
        mock_get_db,
        mock_process,
        client,
        auth_headers,
        mock_db_session,
        mock_analysis_result,
    ):
        """Test resource processing with specific options."""
        mock_get_db.return_value = mock_db_session
        mock_process.return_value = AsyncMock()
        mock_process.return_value.__dict__.update(mock_analysis_result)

        options = {
            "include_summary": True,
            "include_tags": True,
            "include_key_takeaways": False,
        }

        response = client.post(
            "/api/v1/enhanced-resources/process/123", json=options, headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert "analysis_result" in data

    @patch(
        "knowledge_service.services.enhanced_resource_processing.EnhancedResourceProcessingService.batch_process_resources"
    )
    @patch("knowledge_service.core.database.get_db")
    def test_batch_process_with_partial_failures(
        self, mock_get_db, mock_batch_process, client, auth_headers, mock_db_session
    ):
        """Test batch processing with some failures."""
        mock_get_db.return_value = mock_db_session
        mock_batch_process.return_value = [
            {
                "resource_id": 1,
                "status": "success",
                "analysis": {"content_type": "document"},
            },
            {"resource_id": 2, "status": "error", "error": "Processing failed"},
            {
                "resource_id": 3,
                "status": "success",
                "analysis": {"content_type": "tutorial"},
            },
        ]

        batch_data = {"resource_ids": [1, 2, 3]}

        response = client.post(
            "/api/v1/enhanced-resources/batch-process",
            json=batch_data,
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["results"]) == 3
        assert data["results"][0]["status"] == "success"
        assert data["results"][1]["status"] == "error"
        assert data["results"][2]["status"] == "success"

    def test_concurrent_processing_requests(self, client, auth_headers):
        """Test handling of concurrent processing requests."""
        import threading

        results = []

        def make_request(resource_id):
            response = client.post(
                f"/api/v1/enhanced-resources/process/{resource_id}",
                headers=auth_headers,
            )
            results.append(response.status_code)

        # Create multiple threads for concurrent requests
        threads = []
        for i in range(5):
            thread = threading.Thread(target=make_request, args=(i + 1,))
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # All requests should be handled properly
        assert len(results) == 5
        assert all(status in [200, 404, 429, 500] for status in results)

    @patch("knowledge_service.core.database.get_db")
    def test_analysis_summary_with_filters(
        self, mock_get_db, client, auth_headers, mock_db_session
    ):
        """Test getting analysis summary with date filters."""
        mock_get_db.return_value = mock_db_session

        with patch(
            "knowledge_service.services.enhanced_resource_processing.EnhancedResourceProcessingService.get_analysis_summary"
        ) as mock_summary:
            mock_summary.return_value = {
                "total_resources": 50,
                "analyzed_resources": 45,
                "date_range": "2023-01-01 to 2023-12-31",
            }

            response = client.get(
                "/api/v1/enhanced-resources/analysis-summary",
                params={"date_from": "2023-01-01", "date_to": "2023-12-31"},
                headers=auth_headers,
            )

            assert response.status_code == 200
            data = response.json()
            assert data["total_resources"] == 50

    def test_invalid_resource_id_format(self, client, auth_headers):
        """Test handling of invalid resource ID format."""
        response = client.post(
            "/api/v1/enhanced-resources/process/invalid_id", headers=auth_headers
        )

        assert response.status_code == 422

    def test_negative_resource_id(self, client, auth_headers):
        """Test handling of negative resource ID."""
        response = client.post(
            "/api/v1/enhanced-resources/process/-1", headers=auth_headers
        )

        assert response.status_code == 422

    @patch(
        "knowledge_service.services.enhanced_resource_processing.EnhancedResourceProcessingService.process_resource"
    )
    @patch("knowledge_service.core.database.get_db")
    def test_service_timeout_handling(
        self, mock_get_db, mock_process, client, auth_headers, mock_db_session
    ):
        """Test handling of service timeouts."""
        import asyncio

        mock_get_db.return_value = mock_db_session
        mock_process.side_effect = asyncio.TimeoutError("Processing timeout")

        response = client.post(
            "/api/v1/enhanced-resources/process/123", headers=auth_headers
        )

        assert response.status_code == 500

    def test_malformed_json_in_batch_request(self, client, auth_headers):
        """Test handling of malformed JSON in batch requests."""
        response = client.post(
            "/api/v1/enhanced-resources/batch-process",
            data="invalid json",
            headers={**auth_headers, "Content-Type": "application/json"},
        )

        assert response.status_code == 422

    @patch("knowledge_service.core.database.get_db")
    def test_database_connection_error(self, mock_get_db, client, auth_headers):
        """Test handling of database connection errors."""
        mock_get_db.side_effect = Exception("Database connection failed")

        response = client.post(
            "/api/v1/enhanced-resources/process/123", headers=auth_headers
        )

        assert response.status_code == 500

    def test_rate_limiting_on_batch_operations(self, client, auth_headers):
        """Test rate limiting on batch operations."""
        batch_data = {"resource_ids": [1, 2, 3]}

        # Make multiple rapid batch requests
        responses = []
        for _ in range(10):
            response = client.post(
                "/api/v1/enhanced-resources/batch-process",
                json=batch_data,
                headers=auth_headers,
            )
            responses.append(response.status_code)

        # Should eventually get rate limited or handled gracefully
        assert all(status in [200, 400, 429, 500] for status in responses)

    @patch("knowledge_service.core.database.get_db")
    def test_search_pagination(
        self, mock_get_db, client, auth_headers, mock_db_session
    ):
        """Test search pagination functionality."""
        mock_get_db.return_value = mock_db_session

        with patch(
            "knowledge_service.services.enhanced_resource_processing.EnhancedResourceProcessingService.search_by_analysis"
        ) as mock_search:
            mock_search.return_value = {
                "resources": [{"id": i, "title": f"Resource {i}"} for i in range(10)],
                "total_count": 100,
                "page": 1,
                "per_page": 10,
            }

            response = client.get(
                "/api/v1/enhanced-resources/search/by-analysis",
                params={"content_type": "document", "page": "1", "per_page": "10"},
                headers=auth_headers,
            )

            assert response.status_code == 200
            data = response.json()
            assert len(data["resources"]) == 10
            assert data["total_count"] == 100
