"""Integration tests for content analysis API endpoints."""
import io
from unittest.mock import AsyncMock, patch

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
def sample_content():
    """Sample content for testing."""
    return {
        "content": """
        Machine learning is a subset of artificial intelligence that focuses on
        algorithms that can learn from and make predictions on data. This comprehensive
        guide covers supervised learning, unsupervised learning, and reinforcement learning.
        We'll explore various algorithms such as linear regression, decision trees,
        neural networks, and support vector machines.
        """,
        "title": "Introduction to Machine Learning",
    }


@pytest.fixture
def mock_analysis_result():
    """Mock content analysis result."""
    return {
        "content_type": "technical_document",
        "complexity_level": "intermediate",
        "technical_domains": ["machine_learning", "artificial_intelligence"],
        "keywords": ["machine learning", "algorithms", "neural networks"],
        "summary": "A comprehensive guide to machine learning fundamentals",
        "key_takeaways": ["Understanding ML concepts", "Practical implementation"],
        "readability_score": 0.7,
        "estimated_reading_time": 15,
        "language": "en",
        "quality_score": 0.8,
    }


class TestContentAnalysisAPI:
    """Integration tests for content analysis API."""

    @patch(
        "knowledge_service.services.content_analysis.ContentAnalysisService.analyze_content"
    )
    def test_analyze_content_success(
        self, mock_analyze, client, auth_headers, sample_content, mock_analysis_result
    ):
        """Test successful content analysis."""
        # Mock the service response
        mock_analyze.return_value = AsyncMock()
        mock_analyze.return_value.__dict__.update(mock_analysis_result)

        response = client.post(
            "/api/v1/content-analysis/analyze",
            data=sample_content,
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["content_type"] == "technical_document"
        assert data["complexity_level"] == "intermediate"
        assert "machine_learning" in data["technical_domains"]
        assert len(data["keywords"]) > 0

    def test_analyze_content_missing_content(self, client, auth_headers):
        """Test content analysis with missing content."""
        response = client.post(
            "/api/v1/content-analysis/analyze",
            data={"title": "Test Title"},
            headers=auth_headers,
        )

        assert response.status_code == 422  # Validation error

    def test_analyze_content_unauthorized(self, client, sample_content):
        """Test content analysis without authentication."""
        response = client.post("/api/v1/content-analysis/analyze", data=sample_content)

        assert response.status_code == 401

    @patch(
        "knowledge_service.services.content_analysis.ContentAnalysisService.analyze_file_content"
    )
    def test_analyze_file_success(
        self, mock_analyze_file, client, auth_headers, mock_analysis_result
    ):
        """Test successful file analysis."""
        # Mock the service response
        mock_analyze_file.return_value = AsyncMock()
        mock_analyze_file.return_value.__dict__.update(mock_analysis_result)

        # Create a test file
        test_file_content = b"This is a test PDF content about machine learning."
        test_file = io.BytesIO(test_file_content)

        response = client.post(
            "/api/v1/content-analysis/analyze-file",
            files={"file": ("test.pdf", test_file, "application/pdf")},
            data={"title": "Test Document"},
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["content_type"] == "technical_document"

    def test_analyze_file_no_file(self, client, auth_headers):
        """Test file analysis without file."""
        response = client.post(
            "/api/v1/content-analysis/analyze-file",
            data={"title": "Test Document"},
            headers=auth_headers,
        )

        assert response.status_code == 422

    def test_analyze_file_unsupported_format(self, client, auth_headers):
        """Test file analysis with unsupported format."""
        test_file = io.BytesIO(b"test content")

        response = client.post(
            "/api/v1/content-analysis/analyze-file",
            files={
                "file": (
                    "test.xlsx",
                    test_file,
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
            },
            data={"title": "Test Document"},
            headers=auth_headers,
        )

        assert response.status_code == 400

    @patch(
        "knowledge_service.services.content_analysis.ContentAnalysisService.batch_analyze_content"
    )
    def test_batch_analyze_success(
        self, mock_batch_analyze, client, auth_headers, mock_analysis_result
    ):
        """Test successful batch content analysis."""
        # Mock the service response
        mock_results = [
            AsyncMock(**mock_analysis_result),
            AsyncMock(**{**mock_analysis_result, "content_type": "tutorial"}),
        ]
        mock_batch_analyze.return_value = mock_results

        batch_data = {
            "content_items": [
                {"content": "First document content", "title": "Doc 1"},
                {"content": "Second document content", "title": "Doc 2"},
            ]
        }

        response = client.post(
            "/api/v1/content-analysis/batch-analyze",
            json=batch_data,
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["content_type"] == "technical_document"
        assert data[1]["content_type"] == "tutorial"

    def test_batch_analyze_empty_list(self, client, auth_headers):
        """Test batch analysis with empty content list."""
        batch_data = {"content_items": []}

        response = client.post(
            "/api/v1/content-analysis/batch-analyze",
            json=batch_data,
            headers=auth_headers,
        )

        assert response.status_code == 400

    @patch(
        "knowledge_service.services.content_analysis.ContentAnalysisService.extract_tags_only"
    )
    def test_extract_tags_success(
        self, mock_extract_tags, client, auth_headers, sample_content
    ):
        """Test successful tag extraction."""
        mock_extract_tags.return_value = [
            "machine learning",
            "AI",
            "algorithms",
            "data science",
        ]

        response = client.post(
            "/api/v1/content-analysis/extract-tags",
            data={**sample_content, "max_tags": "10"},
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert "tags" in data
        assert len(data["tags"]) <= 10
        assert "machine learning" in data["tags"]

    def test_extract_tags_invalid_max_tags(self, client, auth_headers, sample_content):
        """Test tag extraction with invalid max_tags."""
        response = client.post(
            "/api/v1/content-analysis/extract-tags",
            data={**sample_content, "max_tags": "0"},
            headers=auth_headers,
        )

        assert response.status_code == 422

    @patch(
        "knowledge_service.services.content_analysis.ContentAnalysisService.analyze_content"
    )
    def test_classify_content_success(
        self, mock_analyze, client, auth_headers, sample_content, mock_analysis_result
    ):
        """Test successful content classification."""
        mock_analyze.return_value = AsyncMock()
        mock_analyze.return_value.__dict__.update(mock_analysis_result)

        response = client.post(
            "/api/v1/content-analysis/classify-content",
            data=sample_content,
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert "content_type" in data
        assert "complexity_level" in data
        assert "technical_domains" in data

    def test_get_content_types(self, client, auth_headers):
        """Test getting available content types."""
        response = client.get(
            "/api/v1/content-analysis/content-types", headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert "content_types" in data
        assert isinstance(data["content_types"], list)
        assert len(data["content_types"]) > 0

    def test_get_complexity_levels(self, client, auth_headers):
        """Test getting available complexity levels."""
        response = client.get(
            "/api/v1/content-analysis/complexity-levels", headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert "complexity_levels" in data
        assert isinstance(data["complexity_levels"], list)
        assert len(data["complexity_levels"]) > 0

    def test_get_technical_domains(self, client, auth_headers):
        """Test getting available technical domains."""
        response = client.get(
            "/api/v1/content-analysis/technical-domains", headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert "technical_domains" in data
        assert isinstance(data["technical_domains"], list)
        assert len(data["technical_domains"]) > 0

    @patch(
        "knowledge_service.services.content_analysis.ContentAnalysisService.analyze_content"
    )
    def test_service_error_handling(
        self, mock_analyze, client, auth_headers, sample_content
    ):
        """Test error handling when service fails."""
        mock_analyze.side_effect = Exception("Service error")

        response = client.post(
            "/api/v1/content-analysis/analyze",
            data=sample_content,
            headers=auth_headers,
        )

        assert response.status_code == 500

    def test_rate_limiting(self, client, auth_headers, sample_content):
        """Test rate limiting on content analysis endpoints."""
        # Make multiple rapid requests to trigger rate limiting
        responses = []
        for _ in range(15):  # Exceed typical rate limit
            response = client.post(
                "/api/v1/content-analysis/analyze",
                data=sample_content,
                headers=auth_headers,
            )
            responses.append(response.status_code)

        # Should eventually get rate limited
        assert 429 in responses or any(r >= 500 for r in responses)

    def test_large_content_handling(self, client, auth_headers):
        """Test handling of large content."""
        large_content = {
            "content": "x" * 1000000,  # 1MB of content
            "title": "Large Document",
        }

        response = client.post(
            "/api/v1/content-analysis/analyze", data=large_content, headers=auth_headers
        )

        # Should either process successfully or return appropriate error
        assert response.status_code in [200, 400, 413, 422]

    def test_special_characters_handling(self, client, auth_headers):
        """Test handling of special characters in content."""
        special_content = {
            "content": "Content with émojis 🚀 and spëcial çharacters ñ",
            "title": "Spëcial Tëst",
        }

        response = client.post(
            "/api/v1/content-analysis/analyze",
            data=special_content,
            headers=auth_headers,
        )

        # Should handle special characters gracefully
        assert response.status_code in [200, 400]

    def test_concurrent_requests(self, client, auth_headers, sample_content):
        """Test handling of concurrent requests."""
        import threading
        import time

        results = []

        def make_request():
            response = client.post(
                "/api/v1/content-analysis/analyze",
                data=sample_content,
                headers=auth_headers,
            )
            results.append(response.status_code)

        # Create multiple threads for concurrent requests
        threads = []
        for _ in range(5):
            thread = threading.Thread(target=make_request)
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # All requests should be handled properly
        assert len(results) == 5
        assert all(status in [200, 429, 500] for status in results)

    def test_malformed_json_handling(self, client, auth_headers):
        """Test handling of malformed JSON in batch requests."""
        response = client.post(
            "/api/v1/content-analysis/batch-analyze",
            data="invalid json",
            headers={**auth_headers, "Content-Type": "application/json"},
        )

        assert response.status_code == 422

    def test_missing_required_fields(self, client, auth_headers):
        """Test handling of missing required fields."""
        incomplete_data = {"title": "Test Title"}  # Missing content

        response = client.post(
            "/api/v1/content-analysis/analyze",
            data=incomplete_data,
            headers=auth_headers,
        )

        assert response.status_code == 422

    @patch(
        "knowledge_service.services.content_analysis.ContentAnalysisService.analyze_content"
    )
    def test_timeout_handling(self, mock_analyze, client, auth_headers, sample_content):
        """Test handling of service timeouts."""
        import asyncio

        mock_analyze.side_effect = asyncio.TimeoutError("Service timeout")

        response = client.post(
            "/api/v1/content-analysis/analyze",
            data=sample_content,
            headers=auth_headers,
        )

        assert response.status_code == 500

    def test_content_type_validation(self, client, auth_headers):
        """Test content type validation for file uploads."""
        test_file = io.BytesIO(b"test content")

        response = client.post(
            "/api/v1/content-analysis/analyze-file",
            files={"file": ("test.exe", test_file, "application/octet-stream")},
            data={"title": "Test Document"},
            headers=auth_headers,
        )

        assert response.status_code == 400

    def test_file_size_limits(self, client, auth_headers):
        """Test file size limit enforcement."""
        # Create a large file (simulate 60MB)
        large_file_content = b"x" * (60 * 1024 * 1024)
        large_file = io.BytesIO(large_file_content)

        response = client.post(
            "/api/v1/content-analysis/analyze-file",
            files={"file": ("large.pdf", large_file, "application/pdf")},
            data={"title": "Large Document"},
            headers=auth_headers,
        )

        # Should reject files that are too large
        assert response.status_code in [400, 413, 422]
