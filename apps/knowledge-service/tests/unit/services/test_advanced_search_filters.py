"""Unit tests for advanced search filters and sorting."""

from datetime import datetime, timedelta
from unittest.mock import MagicMock, Mock

import pytest
from knowledge_service.models.resource import Resource
from knowledge_service.services.project_knowledge import \
    ProjectKnowledgeService
from sqlalchemy.orm import Session


class TestAdvancedSearchFilters:
    """Test suite for advanced search filter logic."""

    def setup_method(self):
        """Set up test fixtures."""
        self.service = ProjectKnowledgeService()
        self.mock_db = Mock(spec=Session)

    def test_apply_database_filters_author(self):
        """Test author filter application."""
        mock_query = Mock()

        result = self.service._apply_database_filters(mock_query, author="John Doe")

        # Verify filter was applied
        mock_query.filter.assert_called()

    def test_apply_database_filters_date_range(self):
        """Test date range filter application."""
        mock_query = Mock()
        date_from = datetime(2023, 1, 1)
        date_to = datetime(2023, 12, 31)

        result = self.service._apply_database_filters(
            mock_query, date_from=date_from, date_to=date_to
        )

        # Verify filters were applied (should be called twice for date range)
        assert mock_query.filter.call_count >= 2

    def test_apply_database_filters_file_size(self):
        """Test file size filter application."""
        mock_query = Mock()

        result = self.service._apply_database_filters(
            mock_query, min_file_size=1024, max_file_size=1048576
        )

        # Verify filters were applied
        assert mock_query.filter.call_count >= 2

    def test_apply_database_filters_doi(self):
        """Test DOI filter application."""
        mock_query = Mock()

        # Test has_doi=True
        result = self.service._apply_database_filters(mock_query, has_doi=True)

        mock_query.filter.assert_called()

        # Reset mock and test has_doi=False
        mock_query.reset_mock()
        result = self.service._apply_database_filters(mock_query, has_doi=False)

        mock_query.filter.assert_called()

    def test_apply_database_filters_keywords(self):
        """Test keywords filter application."""
        mock_query = Mock()

        result = self.service._apply_database_filters(
            mock_query, keywords=["machine learning", "AI"]
        )

        # Should be called twice for two keywords
        assert mock_query.filter.call_count >= 2

    def test_sort_results_by_relevance_desc(self):
        """Test sorting by relevance descending."""
        results = [
            {"title": "Resource A", "relevance_score": 0.7},
            {"title": "Resource B", "relevance_score": 0.9},
            {"title": "Resource C", "relevance_score": 0.5},
        ]

        sorted_results = self.service._sort_results(results, "relevance", "desc")

        assert sorted_results[0]["relevance_score"] == 0.9
        assert sorted_results[1]["relevance_score"] == 0.7
        assert sorted_results[2]["relevance_score"] == 0.5

    def test_sort_results_by_title_asc(self):
        """Test sorting by title ascending."""
        results = [
            {"title": "Zebra Research", "relevance_score": 0.8},
            {"title": "Alpha Study", "relevance_score": 0.7},
            {"title": "Beta Analysis", "relevance_score": 0.9},
        ]

        sorted_results = self.service._sort_results(results, "title", "asc")

        assert sorted_results[0]["title"] == "Alpha Study"
        assert sorted_results[1]["title"] == "Beta Analysis"
        assert sorted_results[2]["title"] == "Zebra Research"

    def test_sort_results_by_date_desc(self):
        """Test sorting by date descending."""
        results = [
            {"title": "Old Paper", "publication_date": "2020-01-01T00:00:00"},
            {"title": "Recent Paper", "publication_date": "2023-01-01T00:00:00"},
            {"title": "Middle Paper", "publication_date": "2021-01-01T00:00:00"},
        ]

        sorted_results = self.service._sort_results(results, "date", "desc")

        assert sorted_results[0]["title"] == "Recent Paper"
        assert sorted_results[1]["title"] == "Middle Paper"
        assert sorted_results[2]["title"] == "Old Paper"

    def test_sort_results_by_author_asc(self):
        """Test sorting by author ascending."""
        results = [
            {"title": "Paper 1", "author": "Zoe Smith"},
            {"title": "Paper 2", "author": "Alice Johnson"},
            {"title": "Paper 3", "author": "Bob Wilson"},
        ]

        sorted_results = self.service._sort_results(results, "author", "asc")

        assert sorted_results[0]["author"] == "Alice Johnson"
        assert sorted_results[1]["author"] == "Bob Wilson"
        assert sorted_results[2]["author"] == "Zoe Smith"

    def test_sort_results_by_file_size_desc(self):
        """Test sorting by file size descending."""
        results = [
            {"title": "Small File", "file_size": 1024},
            {"title": "Large File", "file_size": 2048000},
            {"title": "Medium File", "file_size": 512000},
        ]

        sorted_results = self.service._sort_results(results, "file_size", "desc")

        assert sorted_results[0]["title"] == "Large File"
        assert sorted_results[1]["title"] == "Medium File"
        assert sorted_results[2]["title"] == "Small File"

    def test_sort_results_handles_missing_values(self):
        """Test sorting handles missing values gracefully."""
        results = [
            {"title": "Paper 1", "author": "John Doe"},
            {"title": "Paper 2", "author": None},
            {"title": "Paper 3"},  # No author field
        ]

        # Should not raise an exception
        sorted_results = self.service._sort_results(results, "author", "asc")

        assert len(sorted_results) == 3
        # Papers without authors should be sorted to the end for ascending
        assert sorted_results[0]["author"] == "John Doe"
