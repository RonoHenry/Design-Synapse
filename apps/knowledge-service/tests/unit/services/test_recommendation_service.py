"""Unit tests for recommendation service."""
from collections import defaultdict
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, Mock, patch

import pytest
from knowledge_service.models.bookmark import Bookmark
from knowledge_service.models.resource import Resource
from knowledge_service.services.recommendation import (RecommendationScore,
                                                       RecommendationService,
                                                       RecommendationType,
                                                       UserProfile)


class TestRecommendationService:
    """Test cases for RecommendationService."""

    @pytest.fixture
    def mock_vector_search_service(self):
        """Mock vector search service fixture."""
        mock = AsyncMock()
        return mock

    @pytest.fixture
    def mock_llm_service(self):
        """Mock LLM service fixture."""
        mock = AsyncMock()
        return mock

    @pytest.fixture
    def recommendation_service(self, mock_vector_search_service, mock_llm_service):
        """Recommendation service fixture."""
        return RecommendationService(mock_vector_search_service, mock_llm_service)

    @pytest.fixture
    def mock_db_session(self):
        """Mock database session fixture."""
        mock = Mock()
        return mock

    @pytest.fixture
    def sample_user_profile(self):
        """Sample user profile fixture."""
        return UserProfile(
            user_id=1,
            interests=["machine learning", "python", "data science"],
            expertise_level="intermediate",
            recent_activity=[],
            bookmarked_resources=[1, 2, 3],
            search_history=["ML algorithms", "neural networks"],
            preferred_content_types=["technical_document", "tutorial"],
            technical_domains=["machine_learning", "data_science"],
        )

    @pytest.fixture
    def sample_recommendations(self):
        """Sample recommendation scores fixture."""
        return [
            RecommendationScore(
                resource_id=4,
                score=0.95,
                recommendation_type=RecommendationType.CONTENT_BASED,
                explanation="Based on your interests in machine learning",
                metadata={"interests_matched": ["machine learning"]},
            ),
            RecommendationScore(
                resource_id=5,
                score=0.87,
                recommendation_type=RecommendationType.COLLABORATIVE,
                explanation="Recommended by 3 users with similar interests",
                metadata={"bookmark_count": 3, "similar_users": 5},
            ),
        ]

    def test_init(self, mock_vector_search_service, mock_llm_service):
        """Test service initialization."""
        service = RecommendationService(mock_vector_search_service, mock_llm_service)

        assert service.vector_search == mock_vector_search_service
        assert service.llm_service == mock_llm_service
        assert service.weights[RecommendationType.CONTENT_BASED] == 0.4
        assert service.weights[RecommendationType.COLLABORATIVE] == 0.3
        assert service.weights[RecommendationType.TRENDING] == 0.1
        assert service.weights[RecommendationType.CONTEXTUAL] == 0.2
        assert service.cache_ttl == 3600

    @pytest.mark.asyncio
    async def test_get_recommendations_success(
        self,
        recommendation_service,
        mock_db_session,
        sample_user_profile,
        sample_recommendations,
    ):
        """Test successful recommendation retrieval."""
        user_id = 1

        # Mock user profile building
        with patch.object(
            recommendation_service, "_build_user_profile"
        ) as mock_build_profile:
            mock_build_profile.return_value = sample_user_profile

            # Mock individual recommendation methods
            with patch.object(
                recommendation_service, "_get_recommendations_by_type"
            ) as mock_get_by_type:
                mock_get_by_type.return_value = sample_recommendations[
                    :1
                ]  # Return one recommendation per type

                # Mock combine recommendations
                with patch.object(
                    recommendation_service, "_combine_recommendations"
                ) as mock_combine:
                    mock_combine.return_value = sample_recommendations

                    result = await recommendation_service.get_recommendations(
                        user_id=user_id, db=mock_db_session, num_recommendations=10
                    )

                    assert len(result) == 2
                    assert all(isinstance(rec, RecommendationScore) for rec in result)
                    mock_build_profile.assert_called_once_with(user_id, mock_db_session)

    @pytest.mark.asyncio
    async def test_get_recommendations_with_cache(
        self, recommendation_service, mock_db_session, sample_recommendations
    ):
        """Test recommendation retrieval with cache hit."""
        user_id = 1
        cache_key = f"{user_id}_10_{hash(str(None))}"

        # Set up cache
        recommendation_service.recommendation_cache[cache_key] = (
            sample_recommendations,
            datetime.now().timestamp(),
        )

        result = await recommendation_service.get_recommendations(
            user_id=user_id, db=mock_db_session, num_recommendations=10
        )

        assert result == sample_recommendations

    @pytest.mark.asyncio
    async def test_build_user_profile_success(
        self, recommendation_service, mock_db_session
    ):
        """Test successful user profile building."""
        user_id = 1

        # Mock database queries
        mock_bookmarks = [Mock(resource_id=1), Mock(resource_id=2)]
        mock_db_session.query.return_value.filter.return_value.all.return_value = (
            mock_bookmarks
        )

        # Mock resources
        mock_resources = [
            Mock(
                id=1,
                keywords=["python", "programming"],
                technical_domains=["software_engineering"],
                content_type="tutorial",
                complexity_level="basic",
            ),
            Mock(
                id=2,
                keywords=["machine learning", "AI"],
                technical_domains=["data_science"],
                content_type="technical_document",
                complexity_level="intermediate",
            ),
        ]
        mock_db_session.query.return_value.filter.return_value.all.side_effect = [
            mock_bookmarks,
            mock_resources,
        ]

        profile = await recommendation_service._build_user_profile(
            user_id, mock_db_session
        )

        assert isinstance(profile, UserProfile)
        assert profile.user_id == user_id
        assert "python" in profile.interests
        assert "machine learning" in profile.interests
        assert "software_engineering" in profile.technical_domains
        assert "data_science" in profile.technical_domains

    @pytest.mark.asyncio
    async def test_build_user_profile_with_cache(
        self, recommendation_service, mock_db_session
    ):
        """Test user profile building with cache hit."""
        user_id = 1
        cached_profile = UserProfile(
            user_id=user_id,
            interests=["cached", "interests"],
            expertise_level="expert",
            recent_activity=[],
            bookmarked_resources=[],
            search_history=[],
            preferred_content_types=[],
            technical_domains=[],
        )

        # Set up cache
        recommendation_service.user_profile_cache[user_id] = (
            cached_profile,
            datetime.now().timestamp(),
        )

        profile = await recommendation_service._build_user_profile(
            user_id, mock_db_session
        )

        assert profile == cached_profile

    def test_estimate_expertise_level(self, recommendation_service):
        """Test expertise level estimation."""
        # Basic level resources
        basic_resources = [
            Mock(complexity_level="basic"),
            Mock(complexity_level="basic"),
        ]
        level = recommendation_service._estimate_expertise_level(basic_resources)
        assert level == "basic"

        # Advanced level resources
        advanced_resources = [
            Mock(complexity_level="advanced"),
            Mock(complexity_level="expert"),
            Mock(complexity_level="advanced"),
        ]
        level = recommendation_service._estimate_expertise_level(advanced_resources)
        assert level == "advanced"

        # No resources
        level = recommendation_service._estimate_expertise_level([])
        assert level == "intermediate"

    @pytest.mark.asyncio
    async def test_get_content_based_recommendations(
        self,
        recommendation_service,
        mock_vector_search_service,
        sample_user_profile,
        mock_db_session,
    ):
        """Test content-based recommendations."""
        # Mock vector search results
        search_results = [
            {
                "resource_id": 4,
                "score": 0.9,
                "metadata": {"content_type": "technical_document"},
            },
            {
                "resource_id": 5,
                "score": 0.8,
                "metadata": {"technical_domains": ["machine_learning"]},
            },
        ]
        mock_vector_search_service.search_resources.return_value = search_results

        recommendations = (
            await recommendation_service._get_content_based_recommendations(
                sample_user_profile, mock_db_session
            )
        )

        assert len(recommendations) <= 10
        assert all(isinstance(rec, RecommendationScore) for rec in recommendations)
        assert all(
            rec.recommendation_type == RecommendationType.CONTENT_BASED
            for rec in recommendations
        )
        mock_vector_search_service.search_resources.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_collaborative_recommendations(
        self, recommendation_service, sample_user_profile, mock_db_session
    ):
        """Test collaborative filtering recommendations."""
        # Mock similar users
        with patch.object(
            recommendation_service, "_find_similar_users"
        ) as mock_find_similar:
            mock_find_similar.return_value = [(2, 0.8), (3, 0.7)]

            # Mock bookmarks from similar users
            mock_bookmarks = [
                Mock(resource_id=4),
                Mock(resource_id=5),
                Mock(resource_id=4),
            ]
            mock_db_session.query.return_value.filter.return_value.all.return_value = (
                mock_bookmarks
            )

            recommendations = (
                await recommendation_service._get_collaborative_recommendations(
                    sample_user_profile, mock_db_session
                )
            )

            assert len(recommendations) >= 0
            assert all(isinstance(rec, RecommendationScore) for rec in recommendations)
            assert all(
                rec.recommendation_type == RecommendationType.COLLABORATIVE
                for rec in recommendations
            )

    @pytest.mark.asyncio
    async def test_get_trending_recommendations(
        self, recommendation_service, sample_user_profile, mock_db_session
    ):
        """Test trending recommendations."""
        # Mock trending resources query
        mock_trending = [(4, 10), (5, 8), (6, 6)]
        mock_db_session.query.return_value.filter.return_value.group_by.return_value.order_by.return_value.limit.return_value.all.return_value = (
            mock_trending
        )

        recommendations = await recommendation_service._get_trending_recommendations(
            sample_user_profile, mock_db_session
        )

        assert len(recommendations) <= 8
        assert all(isinstance(rec, RecommendationScore) for rec in recommendations)
        assert all(
            rec.recommendation_type == RecommendationType.TRENDING
            for rec in recommendations
        )

    @pytest.mark.asyncio
    async def test_get_contextual_recommendations_search(
        self,
        recommendation_service,
        mock_vector_search_service,
        sample_user_profile,
        mock_db_session,
    ):
        """Test contextual recommendations with search context."""
        context = {"search_query": "neural networks"}

        # Mock vector search results
        search_results = [
            {"resource_id": 7, "score": 0.85},
            {"resource_id": 8, "score": 0.75},
        ]
        mock_vector_search_service.search_resources.return_value = search_results

        recommendations = await recommendation_service._get_contextual_recommendations(
            sample_user_profile, mock_db_session, context
        )

        assert len(recommendations) <= 10
        assert all(isinstance(rec, RecommendationScore) for rec in recommendations)
        assert all(
            rec.recommendation_type == RecommendationType.CONTEXTUAL
            for rec in recommendations
        )

    @pytest.mark.asyncio
    async def test_get_contextual_recommendations_resource(
        self,
        recommendation_service,
        mock_vector_search_service,
        sample_user_profile,
        mock_db_session,
    ):
        """Test contextual recommendations with resource context."""
        context = {"current_resource": 10}

        # Mock current resource
        mock_resource = Mock(id=10, content="Machine learning content for similarity")
        mock_db_session.query.return_value.filter.return_value.first.return_value = (
            mock_resource
        )

        # Mock vector search results
        search_results = [
            {"resource_id": 11, "score": 0.9},
            {"resource_id": 12, "score": 0.8},
        ]
        mock_vector_search_service.search_resources.return_value = search_results

        recommendations = await recommendation_service._get_contextual_recommendations(
            sample_user_profile, mock_db_session, context
        )

        assert len(recommendations) <= 10
        assert all(isinstance(rec, RecommendationScore) for rec in recommendations)

    def test_find_similar_users(
        self, recommendation_service, sample_user_profile, mock_db_session
    ):
        """Test finding similar users."""
        # Mock all bookmarks
        mock_bookmarks = [
            Mock(user_id=2, resource_id=1),
            Mock(user_id=2, resource_id=2),
            Mock(user_id=2, resource_id=4),
            Mock(user_id=3, resource_id=1),
            Mock(user_id=3, resource_id=5),
        ]
        mock_db_session.query.return_value.filter.return_value.all.return_value = (
            mock_bookmarks
        )

        similar_users = recommendation_service._find_similar_users(
            sample_user_profile, mock_db_session
        )

        assert isinstance(similar_users, list)
        assert len(similar_users) >= 0
        for user_id, similarity in similar_users:
            assert isinstance(user_id, int)
            assert 0.0 <= similarity <= 1.0

    def test_calculate_content_similarity_score(
        self, recommendation_service, sample_user_profile
    ):
        """Test content similarity score calculation."""
        search_result = {
            "score": 0.8,
            "metadata": {
                "content_type": "technical_document",
                "technical_domains": ["machine_learning"],
                "complexity_level": "intermediate",
            },
        }

        score = recommendation_service._calculate_content_similarity_score(
            search_result, sample_user_profile
        )

        assert isinstance(score, float)
        assert 0.0 <= score <= 1.0
        assert score >= 0.8  # Should be boosted due to matching preferences

    def test_calculate_collaborative_score(self, recommendation_service):
        """Test collaborative filtering score calculation."""
        score = recommendation_service._calculate_collaborative_score(
            resource_id=1, bookmark_count=5, total_similar_users=10
        )

        assert isinstance(score, float)
        assert 0.0 <= score <= 1.0

    def test_calculate_trending_score(self, recommendation_service):
        """Test trending score calculation."""
        score = recommendation_service._calculate_trending_score(bookmark_count=15)

        assert isinstance(score, float)
        assert 0.0 <= score <= 1.0

    def test_combine_recommendations(
        self, recommendation_service, sample_recommendations
    ):
        """Test recommendation combination."""
        # Add more recommendations with different types
        all_recommendations = sample_recommendations + [
            RecommendationScore(
                resource_id=4,  # Same resource as first recommendation
                score=0.8,
                recommendation_type=RecommendationType.TRENDING,
                explanation="Trending content",
                metadata={"trending_score": 0.8},
            )
        ]

        combined = recommendation_service._combine_recommendations(
            all_recommendations, 5
        )

        assert len(combined) <= 5
        assert all(isinstance(rec, RecommendationScore) for rec in combined)
        # Should combine scores for resource_id=4
        resource_4_rec = next((rec for rec in combined if rec.resource_id == 4), None)
        assert resource_4_rec is not None
        assert resource_4_rec.recommendation_type == RecommendationType.HYBRID

    @pytest.mark.asyncio
    async def test_get_similar_resources_success(
        self, recommendation_service, mock_vector_search_service, mock_db_session
    ):
        """Test getting similar resources."""
        resource_id = 1

        # Mock resource
        mock_resource = Mock(
            id=resource_id, title="Test Resource", content="Test content for similarity"
        )
        mock_db_session.query.return_value.filter.return_value.first.return_value = (
            mock_resource
        )

        # Mock vector search results
        search_results = [
            {"resource_id": 1, "score": 1.0},  # Same resource (should be filtered)
            {"resource_id": 2, "score": 0.9},
            {"resource_id": 3, "score": 0.8},
        ]
        mock_vector_search_service.search_resources.return_value = search_results

        similar_resources = await recommendation_service.get_similar_resources(
            resource_id=resource_id, db=mock_db_session, num_similar=5
        )

        assert len(similar_resources) == 2  # Excludes the original resource
        assert all(rec.resource_id != resource_id for rec in similar_resources)
        assert all(isinstance(rec, RecommendationScore) for rec in similar_resources)

    @pytest.mark.asyncio
    async def test_get_similar_resources_not_found(
        self, recommendation_service, mock_db_session
    ):
        """Test getting similar resources for non-existent resource."""
        resource_id = 999

        # Mock resource not found
        mock_db_session.query.return_value.filter.return_value.first.return_value = None

        similar_resources = await recommendation_service.get_similar_resources(
            resource_id=resource_id, db=mock_db_session, num_similar=5
        )

        assert similar_resources == []

    def test_clear_cache(self, recommendation_service):
        """Test cache clearing."""
        # Add some cache entries
        recommendation_service.user_profile_cache[1] = (
            "profile",
            datetime.now().timestamp(),
        )
        recommendation_service.recommendation_cache["key"] = (
            "recommendations",
            datetime.now().timestamp(),
        )

        recommendation_service.clear_cache()

        assert len(recommendation_service.user_profile_cache) == 0
        assert len(recommendation_service.recommendation_cache) == 0

    def test_get_cache_stats(self, recommendation_service):
        """Test getting cache statistics."""
        # Add some cache entries
        recommendation_service.user_profile_cache[1] = (
            "profile",
            datetime.now().timestamp(),
        )
        recommendation_service.recommendation_cache["key"] = (
            "recommendations",
            datetime.now().timestamp(),
        )

        stats = recommendation_service.get_cache_stats()

        assert "user_profile_cache_size" in stats
        assert "recommendation_cache_size" in stats
        assert "cache_ttl" in stats
        assert "weights" in stats
        assert stats["user_profile_cache_size"] == 1
        assert stats["recommendation_cache_size"] == 1

    def test_update_weights_success(self, recommendation_service):
        """Test successful weight update."""
        new_weights = {
            RecommendationType.CONTENT_BASED: 0.5,
            RecommendationType.COLLABORATIVE: 0.3,
            RecommendationType.TRENDING: 0.1,
            RecommendationType.CONTEXTUAL: 0.1,
        }

        recommendation_service.update_weights(new_weights)

        assert recommendation_service.weights[RecommendationType.CONTENT_BASED] == 0.5
        assert recommendation_service.weights[RecommendationType.COLLABORATIVE] == 0.3

    def test_update_weights_invalid_sum(self, recommendation_service):
        """Test weight update with invalid sum."""
        invalid_weights = {
            RecommendationType.CONTENT_BASED: 0.8,
            RecommendationType.COLLABORATIVE: 0.8,  # Sum > 1.0
        }

        with pytest.raises(ValueError, match="Weights must sum to 1.0"):
            recommendation_service.update_weights(invalid_weights)

    @pytest.mark.asyncio
    async def test_explain_recommendation_success(
        self, recommendation_service, mock_db_session, sample_user_profile
    ):
        """Test successful recommendation explanation."""
        user_id = 1
        resource_id = 4

        # Mock user profile building
        with patch.object(
            recommendation_service, "_build_user_profile"
        ) as mock_build_profile:
            mock_build_profile.return_value = sample_user_profile

            # Mock resource
            mock_resource = Mock(
                id=resource_id,
                title="Machine Learning Guide",
                keywords=["machine learning", "algorithms"],
                technical_domains=["machine_learning"],
                complexity_level="intermediate",
            )
            mock_db_session.query.return_value.filter.return_value.first.return_value = (
                mock_resource
            )

            explanation = await recommendation_service.explain_recommendation(
                user_id=user_id, resource_id=resource_id, db=mock_db_session
            )

            assert "resource_id" in explanation
            assert "resource_title" in explanation
            assert "user_profile_summary" in explanation
            assert "matching_factors" in explanation
            assert "recommendation_strength" in explanation
            assert explanation["resource_id"] == resource_id

    @pytest.mark.asyncio
    async def test_explain_recommendation_not_found(
        self, recommendation_service, mock_db_session, sample_user_profile
    ):
        """Test recommendation explanation for non-existent resource."""
        user_id = 1
        resource_id = 999

        # Mock user profile building
        with patch.object(
            recommendation_service, "_build_user_profile"
        ) as mock_build_profile:
            mock_build_profile.return_value = sample_user_profile

            # Mock resource not found
            mock_db_session.query.return_value.filter.return_value.first.return_value = (
                None
            )

            explanation = await recommendation_service.explain_recommendation(
                user_id=user_id, resource_id=resource_id, db=mock_db_session
            )

            assert "error" in explanation
            assert explanation["error"] == "Resource not found"

    def test_complexity_to_number(self, recommendation_service):
        """Test complexity level to number conversion."""
        assert recommendation_service._complexity_to_number("basic") == 1
        assert recommendation_service._complexity_to_number("intermediate") == 2
        assert recommendation_service._complexity_to_number("advanced") == 3
        assert recommendation_service._complexity_to_number("expert") == 4
        assert recommendation_service._complexity_to_number("unknown") == 2  # Default

    def test_get_cached_recommendations_hit(
        self, recommendation_service, sample_recommendations
    ):
        """Test cache hit for recommendations."""
        cache_key = "test_key"
        recommendation_service.recommendation_cache[cache_key] = (
            sample_recommendations,
            datetime.now().timestamp(),
        )

        cached = recommendation_service._get_cached_recommendations(cache_key)

        assert cached == sample_recommendations

    def test_get_cached_recommendations_miss(self, recommendation_service):
        """Test cache miss for recommendations."""
        cache_key = "nonexistent_key"

        cached = recommendation_service._get_cached_recommendations(cache_key)

        assert cached is None

    def test_get_cached_recommendations_expired(
        self, recommendation_service, sample_recommendations
    ):
        """Test expired cache for recommendations."""
        cache_key = "test_key"
        expired_timestamp = (datetime.now() - timedelta(hours=2)).timestamp()
        recommendation_service.recommendation_cache[cache_key] = (
            sample_recommendations,
            expired_timestamp,
        )

        cached = recommendation_service._get_cached_recommendations(cache_key)

        assert cached is None

    def test_cache_recommendations(
        self, recommendation_service, sample_recommendations
    ):
        """Test caching recommendations."""
        cache_key = "test_key"

        recommendation_service._cache_recommendations(cache_key, sample_recommendations)

        assert cache_key in recommendation_service.recommendation_cache
        cached_recs, timestamp = recommendation_service.recommendation_cache[cache_key]
        assert cached_recs == sample_recommendations
        assert isinstance(timestamp, float)

    def test_cache_cleanup(self, recommendation_service):
        """Test cache cleanup when limit exceeded."""
        # Fill cache beyond limit
        for i in range(1005):  # Exceeds 1000 limit
            recommendation_service.recommendation_cache[f"key_{i}"] = (
                [],
                datetime.now().timestamp(),
            )

        # Add one more to trigger cleanup
        recommendation_service._cache_recommendations("final_key", [])

        # Should have cleaned up oldest entries
        assert len(recommendation_service.recommendation_cache) < 1005
