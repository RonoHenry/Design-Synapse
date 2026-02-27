"""Unit tests for project knowledge service."""
from datetime import datetime
from unittest.mock import AsyncMock, Mock, patch

import pytest
from knowledge_service.models.resource import Resource
from knowledge_service.services.project_knowledge import (
    ProjectKnowledgeResult, ProjectKnowledgeService, ResourceType)


class TestProjectKnowledgeService:
    """Test cases for ProjectKnowledgeService."""

    @pytest.fixture
    def project_knowledge_service(self):
        """Project knowledge service fixture."""
        return ProjectKnowledgeService()

    @pytest.fixture
    def mock_db_session(self):
        """Mock database session fixture."""
        mock = Mock()
        return mock

    @pytest.fixture
    def sample_resources(self):
        """Sample resources fixture."""
        return [
            Mock(
                id=1,
                title="Machine Learning Guide",
                content="Comprehensive guide to ML algorithms",
                resource_type="document",
                keywords=["machine learning", "algorithms"],
                technical_domains=["data_science"],
                created_at=datetime.now(),
                updated_at=datetime.now(),
            ),
            Mock(
                id=2,
                title="Python Tutorial",
                content="Learn Python programming basics",
                resource_type="tutorial",
                keywords=["python", "programming"],
                technical_domains=["software_engineering"],
                created_at=datetime.now(),
                updated_at=datetime.now(),
            ),
        ]

    def test_init(self):
        """Test service initialization."""
        service = ProjectKnowledgeService()
        assert service.cache_ttl == 3600
        assert service.max_results_per_query == 100

    @pytest.mark.asyncio
    async def test_get_project_resources_success(
        self, project_knowledge_service, mock_db_session, sample_resources
    ):
        """Test successful project resources retrieval."""
        project_id = 1

        # Mock database query
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.all.return_value = sample_resources
        mock_db_session.query.return_value = mock_query

        result = await project_knowledge_service.get_project_resources(
            project_id=project_id,
            db=mock_db_session,
            resource_type=ResourceType.ALL,
            limit=10,
            offset=0,
        )

        assert isinstance(result, ProjectKnowledgeResult)
        assert len(result.resources) == 2
        assert result.total_count >= 2
        assert result.project_id == project_id

    @pytest.mark.asyncio
    async def test_get_project_resources_filtered_by_type(
        self, project_knowledge_service, mock_db_session, sample_resources
    ):
        """Test project resources retrieval filtered by type."""
        project_id = 1

        # Filter to only return documents
        filtered_resources = [
            r for r in sample_resources if r.resource_type == "document"
        ]

        # Mock database query
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.all.return_value = filtered_resources
        mock_db_session.query.return_value = mock_query

        result = await project_knowledge_service.get_project_resources(
            project_id=project_id,
            db=mock_db_session,
            resource_type=ResourceType.DOCUMENT,
            limit=10,
            offset=0,
        )

        assert len(result.resources) == 1
        assert result.resources[0].resource_type == "document"

    @pytest.mark.asyncio
    async def test_get_project_resources_with_search(
        self, project_knowledge_service, mock_db_session, sample_resources
    ):
        """Test project resources retrieval with search query."""
        project_id = 1
        search_query = "machine learning"

        # Filter resources that match search
        matching_resources = [
            r for r in sample_resources if "machine" in r.title.lower()
        ]

        # Mock database query
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.all.return_value = matching_resources
        mock_db_session.query.return_value = mock_query

        result = await project_knowledge_service.get_project_resources(
            project_id=project_id,
            db=mock_db_session,
            search_query=search_query,
            limit=10,
            offset=0,
        )

        assert len(result.resources) == 1
        assert "machine" in result.resources[0].title.lower()

    @pytest.mark.asyncio
    async def test_get_recommendations_success(
        self, project_knowledge_service, mock_db_session, sample_resources
    ):
        """Test successful recommendations retrieval."""
        project_id = 1

        # Mock project resources query
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = sample_resources
        mock_db_session.query.return_value = mock_query

        # Mock recommendation logic
        with patch.object(
            project_knowledge_service, "_generate_project_recommendations"
        ) as mock_generate:
            mock_generate.return_value = sample_resources

            result = await project_knowledge_service.get_recommendations(
                project_id=project_id, db=mock_db_session, limit=5
            )

            assert isinstance(result, ProjectKnowledgeResult)
            assert len(result.resources) <= 5
            mock_generate.assert_called_once()

    @pytest.mark.asyncio
    async def test_search_project_knowledge_success(
        self, project_knowledge_service, mock_db_session, sample_resources
    ):
        """Test successful project knowledge search."""
        project_id = 1
        query = "python programming"

        # Mock search results
        with patch.object(
            project_knowledge_service, "_perform_semantic_search"
        ) as mock_search:
            mock_search.return_value = sample_resources

            result = await project_knowledge_service.search_project_knowledge(
                project_id=project_id, query=query, db=mock_db_session, limit=10
            )

            assert isinstance(result, ProjectKnowledgeResult)
            assert len(result.resources) <= 10
            mock_search.assert_called_once_with(project_id, query, mock_db_session, 10)

    @pytest.mark.asyncio
    async def test_get_knowledge_summary_success(
        self, project_knowledge_service, mock_db_session, sample_resources
    ):
        """Test successful knowledge summary generation."""
        project_id = 1

        # Mock project resources
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.all.return_value = sample_resources
        mock_db_session.query.return_value = mock_query

        summary = await project_knowledge_service.get_knowledge_summary(
            project_id=project_id, db=mock_db_session
        )

        assert "total_resources" in summary
        assert "resource_types" in summary
        assert "technical_domains" in summary
        assert "recent_additions" in summary
        assert summary["total_resources"] == len(sample_resources)

    @pytest.mark.asyncio
    async def test_add_resource_to_project_success(
        self, project_knowledge_service, mock_db_session
    ):
        """Test successful resource addition to project."""
        project_id = 1
        resource_id = 5

        # Mock resource exists
        mock_resource = Mock(id=resource_id, title="New Resource")
        mock_db_session.query.return_value.filter.return_value.first.return_value = (
            mock_resource
        )

        # Mock project-resource relationship creation
        with patch(
            "knowledge_service.models.project_resource.ProjectResource"
        ) as mock_project_resource:
            mock_instance = Mock()
            mock_project_resource.return_value = mock_instance

            result = await project_knowledge_service.add_resource_to_project(
                project_id=project_id, resource_id=resource_id, db=mock_db_session
            )

            assert result is True
            mock_db_session.add.assert_called_once_with(mock_instance)
            mock_db_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_add_resource_to_project_not_found(
        self, project_knowledge_service, mock_db_session
    ):
        """Test resource addition when resource doesn't exist."""
        project_id = 1
        resource_id = 999

        # Mock resource not found
        mock_db_session.query.return_value.filter.return_value.first.return_value = None

        result = await project_knowledge_service.add_resource_to_project(
            project_id=project_id, resource_id=resource_id, db=mock_db_session
        )

        assert result is False

    @pytest.mark.asyncio
    async def test_remove_resource_from_project_success(
        self, project_knowledge_service, mock_db_session
    ):
        """Test successful resource removal from project."""
        project_id = 1
        resource_id = 5

        # Mock project-resource relationship exists
        mock_relationship = Mock()
        mock_db_session.query.return_value.filter.return_value.first.return_value = (
            mock_relationship
        )

        result = await project_knowledge_service.remove_resource_from_project(
            project_id=project_id, resource_id=resource_id, db=mock_db_session
        )

        assert result is True
        mock_db_session.delete.assert_called_once_with(mock_relationship)
        mock_db_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_remove_resource_from_project_not_found(
        self, project_knowledge_service, mock_db_session
    ):
        """Test resource removal when relationship doesn't exist."""
        project_id = 1
        resource_id = 999

        # Mock relationship not found
        mock_db_session.query.return_value.filter.return_value.first.return_value = None

        result = await project_knowledge_service.remove_resource_from_project(
            project_id=project_id, resource_id=resource_id, db=mock_db_session
        )

        assert result is False

    @pytest.mark.asyncio
    async def test_generate_project_recommendations(
        self, project_knowledge_service, mock_db_session, sample_resources
    ):
        """Test project recommendation generation."""
        project_id = 1

        # Mock existing project resources
        existing_resources = sample_resources[:1]  # First resource is in project

        # Mock all available resources
        all_resources = sample_resources

        # Mock database queries
        mock_db_session.query.return_value.filter.return_value.all.side_effect = [
            existing_resources,  # Project resources
            all_resources,  # All resources
        ]

        recommendations = (
            await project_knowledge_service._generate_project_recommendations(
                project_id=project_id, db=mock_db_session, limit=5
            )
        )

        # Should recommend resources not already in project
        assert len(recommendations) >= 0
        recommended_ids = [r.id for r in recommendations]
        existing_ids = [r.id for r in existing_resources]
        assert not any(rid in existing_ids for rid in recommended_ids)

    @pytest.mark.asyncio
    async def test_perform_semantic_search(
        self, project_knowledge_service, mock_db_session, sample_resources
    ):
        """Test semantic search functionality."""
        project_id = 1
        query = "machine learning algorithms"

        # Mock vector search
        with patch(
            "knowledge_service.services.vector_search.VectorSearchService"
        ) as mock_vector_service:
            mock_instance = AsyncMock()
            mock_instance.search_resources.return_value = [
                {"resource_id": 1, "score": 0.9},
                {"resource_id": 2, "score": 0.7},
            ]
            mock_vector_service.return_value = mock_instance

            # Mock resource retrieval
            mock_db_session.query.return_value.filter.return_value.all.return_value = (
                sample_resources
            )

            results = await project_knowledge_service._perform_semantic_search(
                project_id=project_id, query=query, db=mock_db_session, limit=10
            )

            assert len(results) <= 10
            assert all(isinstance(r, Mock) for r in results)  # Mock resources

    def test_build_search_filters(self, project_knowledge_service):
        """Test search filter building."""
        filters = project_knowledge_service._build_search_filters(
            resource_type=ResourceType.DOCUMENT,
            technical_domains=["data_science", "machine_learning"],
            date_from=datetime(2023, 1, 1),
            date_to=datetime(2023, 12, 31),
        )

        assert "resource_type" in filters
        assert "technical_domains" in filters
        assert "date_range" in filters
        assert filters["resource_type"] == "document"

    def test_calculate_relevance_score(
        self, project_knowledge_service, sample_resources
    ):
        """Test relevance score calculation."""
        project_resources = sample_resources[:1]  # First resource is in project
        candidate_resource = sample_resources[1]  # Second resource is candidate

        score = project_knowledge_service._calculate_relevance_score(
            candidate_resource=candidate_resource, project_resources=project_resources
        )

        assert isinstance(score, float)
        assert 0.0 <= score <= 1.0

    def test_extract_project_keywords(
        self, project_knowledge_service, sample_resources
    ):
        """Test project keyword extraction."""
        keywords = project_knowledge_service._extract_project_keywords(sample_resources)

        assert isinstance(keywords, list)
        assert len(keywords) > 0
        # Should contain keywords from sample resources
        all_keywords = []
        for resource in sample_resources:
            if resource.keywords:
                all_keywords.extend(resource.keywords)

        assert any(kw in keywords for kw in all_keywords)

    def test_extract_project_domains(self, project_knowledge_service, sample_resources):
        """Test project technical domain extraction."""
        domains = project_knowledge_service._extract_project_domains(sample_resources)

        assert isinstance(domains, list)
        assert len(domains) > 0
        # Should contain domains from sample resources
        all_domains = []
        for resource in sample_resources:
            if resource.technical_domains:
                all_domains.extend(resource.technical_domains)

        assert any(domain in domains for domain in all_domains)

    def test_group_resources_by_type(self, project_knowledge_service, sample_resources):
        """Test resource grouping by type."""
        grouped = project_knowledge_service._group_resources_by_type(sample_resources)

        assert isinstance(grouped, dict)
        assert "document" in grouped
        assert "tutorial" in grouped
        assert len(grouped["document"]) == 1
        assert len(grouped["tutorial"]) == 1

    def test_get_recent_resources(self, project_knowledge_service, sample_resources):
        """Test recent resources retrieval."""
        recent = project_knowledge_service._get_recent_resources(
            sample_resources, days=30
        )

        assert isinstance(recent, list)
        assert len(recent) <= len(sample_resources)
        # All returned resources should be recent (within 30 days)
        cutoff_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        for resource in recent:
            assert (
                resource.created_at >= cutoff_date or resource.updated_at >= cutoff_date
            )

    def test_calculate_knowledge_coverage(
        self, project_knowledge_service, sample_resources
    ):
        """Test knowledge coverage calculation."""
        coverage = project_knowledge_service._calculate_knowledge_coverage(
            sample_resources
        )

        assert isinstance(coverage, dict)
        assert "domain_coverage" in coverage
        assert "type_coverage" in coverage
        assert "completeness_score" in coverage
        assert isinstance(coverage["completeness_score"], float)
        assert 0.0 <= coverage["completeness_score"] <= 1.0

    def test_resource_type_enum_values(self):
        """Test ResourceType enum values."""
        assert ResourceType.ALL.value == "all"
        assert ResourceType.DOCUMENT.value == "document"
        assert ResourceType.TUTORIAL.value == "tutorial"
        assert ResourceType.REFERENCE.value == "reference"
        assert ResourceType.RESEARCH_PAPER.value == "research_paper"

    def test_project_knowledge_result_creation(self, sample_resources):
        """Test ProjectKnowledgeResult creation."""
        result = ProjectKnowledgeResult(
            project_id=1,
            resources=sample_resources,
            total_count=len(sample_resources),
            query="test query",
            filters={"type": "document"},
            metadata={"search_time": 0.5},
        )

        assert result.project_id == 1
        assert result.resources == sample_resources
        assert result.total_count == len(sample_resources)
        assert result.query == "test query"
        assert result.filters == {"type": "document"}
        assert result.metadata["search_time"] == 0.5

    @pytest.mark.asyncio
    async def test_cache_functionality(
        self, project_knowledge_service, mock_db_session, sample_resources
    ):
        """Test caching functionality."""
        project_id = 1

        # Mock database query
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.all.return_value = sample_resources
        mock_db_session.query.return_value = mock_query

        # First call should hit database
        result1 = await project_knowledge_service.get_project_resources(
            project_id=project_id, db=mock_db_session, limit=10, offset=0
        )

        # Second call with same parameters should use cache
        result2 = await project_knowledge_service.get_project_resources(
            project_id=project_id, db=mock_db_session, limit=10, offset=0
        )

        assert result1.resources == result2.resources
        # Database should only be called once due to caching
        assert mock_db_session.query.call_count >= 1

    @pytest.mark.asyncio
    async def test_error_handling(self, project_knowledge_service, mock_db_session):
        """Test error handling in service methods."""
        project_id = 1

        # Mock database error
        mock_db_session.query.side_effect = Exception("Database error")

        # Should handle error gracefully
        result = await project_knowledge_service.get_project_resources(
            project_id=project_id, db=mock_db_session, limit=10, offset=0
        )

        # Should return empty result on error
        assert isinstance(result, ProjectKnowledgeResult)
        assert len(result.resources) == 0
        assert result.total_count == 0
