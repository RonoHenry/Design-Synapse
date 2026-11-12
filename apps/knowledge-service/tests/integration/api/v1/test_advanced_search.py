"""Integration tests for advanced search filters and sorting."""

from datetime import datetime, timedelta
from unittest.mock import Mock, patch

import pytest
from fastapi.testclient import TestClient
from knowledge_service.infrastructure.database import get_db
from knowledge_service.main import app
from knowledge_service.models.resource import Resource

from tests.factories import ResourceFactory

client = TestClient(app)


@pytest.fixture(autouse=True)
def override_dependency(db_session):
    """Override the get_db dependency with our test session."""

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    yield
    app.dependency_overrides.clear()


class TestAdvancedSearchFilters:
    """Test suite for advanced search filters."""

    def setup_method(self):
        """Set up test data for each test method."""
        self.base_date = datetime(2023, 1, 1)

    @patch("knowledge_service.api.dependencies.get_current_user")
    @patch(
        "knowledge_service.services.project_knowledge.ProjectKnowledgeService.search_global"
    )
    def test_search_with_author_filter(self, mock_search, mock_user, db_session):
        """Test search with author filter."""
        mock_user.return_value = 1
        mock_search.return_value = {
            "total": 1,
            "page": 1,
            "page_size": 20,
            "results": [
                {
                    "id": 1,
                    "title": "Test Resource",
                    "author": "John Doe",
                    "relevance_score": 0.9,
                }
            ],
        }

        response = client.get(
            "/api/v1/search/global",
            params={"query": "machine learning", "author": "John Doe"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1

        # Verify the service was called with author filter
        mock_search.assert_called_once()
        call_args = mock_search.call_args
        assert call_args.kwargs["author"] == "John Doe"

    @patch("knowledge_service.api.dependencies.get_current_user")
    @patch(
        "knowledge_service.services.project_knowledge.ProjectKnowledgeService.search_global"
    )
    def test_search_with_date_range_filter(self, mock_search, mock_user, db_session):
        """Test search with date range filter."""
        mock_user.return_value = 1
        mock_search.return_value = {
            "total": 1,
            "page": 1,
            "page_size": 20,
            "results": [],
        }

        date_from = "2023-01-01T00:00:00"
        date_to = "2023-12-31T23:59:59"

        response = client.get(
            "/api/v1/search/global",
            params={"query": "research", "date_from": date_from, "date_to": date_to},
        )

        assert response.status_code == 200

        # Verify the service was called with date filters
        mock_search.assert_called_once()
        call_args = mock_search.call_args
        assert call_args.kwargs["date_from"] is not None
        assert call_args.kwargs["date_to"] is not None

    @patch("knowledge_service.api.dependencies.get_current_user")
    @patch(
        "knowledge_service.services.project_knowledge.ProjectKnowledgeService.search_global"
    )
    def test_search_with_file_size_filter(self, mock_search, mock_user, db_session):
        """Test search with file size filter."""
        mock_user.return_value = 1
        mock_search.return_value = {
            "total": 0,
            "page": 1,
            "page_size": 20,
            "results": [],
        }

        response = client.get(
            "/api/v1/search/global",
            params={
                "query": "documents",
                "min_file_size": 1024,
                "max_file_size": 1048576,  # 1MB
            },
        )

        assert response.status_code == 200

        # Verify the service was called with file size filters
        mock_search.assert_called_once()
        call_args = mock_search.call_args
        assert call_args.kwargs["min_file_size"] == 1024
        assert call_args.kwargs["max_file_size"] == 1048576

    @patch("knowledge_service.api.dependencies.get_current_user")
    @patch(
        "knowledge_service.services.project_knowledge.ProjectKnowledgeService.search_global"
    )
    def test_search_with_doi_filter(self, mock_search, mock_user, db_session):
        """Test search with DOI filter."""
        mock_user.return_value = 1
        mock_search.return_value = {
            "total": 0,
            "page": 1,
            "page_size": 20,
            "results": [],
        }

        response = client.get(
            "/api/v1/search/global",
            params={"query": "academic papers", "has_doi": True},
        )

        assert response.status_code == 200

        # Verify the service was called with DOI filter
        mock_search.assert_called_once()
        call_args = mock_search.call_args
        assert call_args.kwargs["has_doi"] is True

    @patch("knowledge_service.api.dependencies.get_current_user")
    @patch(
        "knowledge_service.services.project_knowledge.ProjectKnowledgeService.search_global"
    )
    def test_search_with_keywords_filter(self, mock_search, mock_user, db_session):
        """Test search with keywords filter."""
        mock_user.return_value = 1
        mock_search.return_value = {
            "total": 0,
            "page": 1,
            "page_size": 20,
            "results": [],
        }

        response = client.get(
            "/api/v1/search/global",
            params={
                "query": "AI research",
                "keywords": ["machine learning", "neural networks"],
            },
        )

        assert response.status_code == 200

        # Verify the service was called with keywords filter
        mock_search.assert_called_once()
        call_args = mock_search.call_args
        assert call_args.kwargs["keywords"] == ["machine learning", "neural networks"]


class TestAdvancedSorting:
    """Test suite for advanced sorting options."""

    @patch("knowledge_service.api.dependencies.get_current_user")
    @patch(
        "knowledge_service.services.project_knowledge.ProjectKnowledgeService.search_global"
    )
    def test_search_sort_by_author_asc(self, mock_search, mock_user, db_session):
        """Test search sorted by author ascending."""
        mock_user.return_value = 1
        mock_search.return_value = {
            "total": 2,
            "page": 1,
            "page_size": 20,
            "results": [
                {"id": 1, "title": "Resource A", "author": "Alice Smith"},
                {"id": 2, "title": "Resource B", "author": "Bob Jones"},
            ],
        }

        response = client.get(
            "/api/v1/search/global",
            params={"query": "research", "sort_by": "author", "sort_order": "asc"},
        )

        assert response.status_code == 200

        # Verify the service was called with sorting parameters
        mock_search.assert_called_once()
        call_args = mock_search.call_args
        assert call_args.kwargs["sort_by"] == "author"
        assert call_args.kwargs["sort_order"] == "asc"

    @patch("knowledge_service.api.dependencies.get_current_user")
    @patch(
        "knowledge_service.services.project_knowledge.ProjectKnowledgeService.search_global"
    )
    def test_search_sort_by_file_size_desc(self, mock_search, mock_user, db_session):
        """Test search sorted by file size descending."""
        mock_user.return_value = 1
        mock_search.return_value = {
            "total": 2,
            "page": 1,
            "page_size": 20,
            "results": [
                {"id": 1, "title": "Large File", "file_size": 2048000},
                {"id": 2, "title": "Small File", "file_size": 1024},
            ],
        }

        response = client.get(
            "/api/v1/search/global",
            params={"query": "documents", "sort_by": "file_size", "sort_order": "desc"},
        )

        assert response.status_code == 200

        # Verify the service was called with sorting parameters
        mock_search.assert_called_once()
        call_args = mock_search.call_args
        assert call_args.kwargs["sort_by"] == "file_size"
        assert call_args.kwargs["sort_order"] == "desc"


class TestProjectSearchAdvancedFilters:
    """Test suite for project search with advanced filters."""

    @patch("knowledge_service.api.dependencies.get_current_user")
    @patch(
        "knowledge_service.services.project_knowledge.ProjectKnowledgeService.search_project_knowledge"
    )
    def test_project_search_with_multiple_filters(
        self, mock_search, mock_user, db_session
    ):
        """Test project search with multiple advanced filters."""
        mock_user.return_value = 1
        mock_search.return_value = {
            "project_resources": [],
            "global_resources": [],
            "total_global": 0,
            "page": 1,
            "page_size": 20,
        }

        response = client.get(
            "/api/v1/search/project/1",
            params={
                "query": "BIM modeling",
                "author": "Jane Doe",
                "source_platform": "MDPI",
                "license_type": "CC BY",
                "min_file_size": 1024,
                "sort_by": "date",
                "sort_order": "desc",
            },
        )

        assert response.status_code == 200

        # Verify the service was called with all filters
        mock_search.assert_called_once()
        call_args = mock_search.call_args
        assert call_args.kwargs["author"] == "Jane Doe"
        assert call_args.kwargs["source_platform"] == "MDPI"
        assert call_args.kwargs["license_type"] == "CC BY"
        assert call_args.kwargs["min_file_size"] == 1024
        assert call_args.kwargs["sort_by"] == "date"
        assert call_args.kwargs["sort_order"] == "desc"


class TestRecommendationsAdvancedFilters:
    """Test suite for recommendations with advanced filters."""

    @patch("knowledge_service.api.dependencies.get_current_user")
    @patch(
        "knowledge_service.services.project_knowledge.ProjectKnowledgeService.get_recommendations"
    )
    def test_recommendations_with_advanced_filters(
        self, mock_recommendations, mock_user, db_session
    ):
        """Test recommendations with advanced filters."""
        mock_user.return_value = 1
        mock_recommendations.return_value = {
            "total": 0,
            "page": 1,
            "page_size": 20,
            "results": [],
        }

        response = client.get(
            "/api/v1/search/project/1/recommendations",
            params={
                "resource_type": "pdf",
                "author": "Expert Author",
                "date_from": "2023-01-01T00:00:00",
                "has_doi": True,
                "sort_by": "relevance",
                "sort_order": "desc",
            },
        )

        assert response.status_code == 200

        # Verify the service was called with all filters
        mock_recommendations.assert_called_once()
        call_args = mock_recommendations.call_args
        assert call_args.kwargs["resource_type"] == "pdf"
        assert call_args.kwargs["author"] == "Expert Author"
        assert call_args.kwargs["date_from"] is not None
        assert call_args.kwargs["has_doi"] is True
        assert call_args.kwargs["sort_by"] == "relevance"
        assert call_args.kwargs["sort_order"] == "desc"
