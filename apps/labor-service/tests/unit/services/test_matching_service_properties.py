"""
Property-based tests for MatchingService
Testing universal properties that should hold across all inputs
"""
from unittest.mock import AsyncMock, Mock

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st
from src.services.matching_service import MatchingService


class TestMatchingServiceProperties:
    """Property-based tests for MatchingService"""

    @pytest.fixture(scope="session")
    def mock_provider_repository(self):
        """Mock provider repository for property testing"""
        mock = Mock()
        mock.find_matching_providers = AsyncMock()
        mock.get_by_id = AsyncMock()
        mock.search_providers = AsyncMock()
        mock.get_provider_suggestions = AsyncMock()
        mock.get_skill_suggestions = AsyncMock()
        mock.get_total_matches = AsyncMock()
        mock.get_match_success_rate = AsyncMock()
        mock.get_average_response_time = AsyncMock()
        mock.get_top_skills = AsyncMock()
        return mock

    @pytest.fixture(scope="session")
    def mock_request_repository(self):
        """Mock request repository for property testing"""
        mock = Mock()
        mock.get_by_id = AsyncMock()
        mock.find_matching_requests = AsyncMock()
        mock.search_requests = AsyncMock()
        mock.get_request_suggestions = AsyncMock()
        mock.get_top_requested_skills = AsyncMock()
        return mock

    @pytest.fixture(scope="session")
    def mock_notification_service(self):
        """Mock notification service for property testing"""
        mock = Mock()
        mock.send_job_alerts = AsyncMock()
        mock.notify_providers = AsyncMock()
        return mock

    @pytest.fixture(scope="session")
    def matching_service(
        self,
        mock_provider_repository,
        mock_request_repository,
        mock_notification_service,
    ):
        """Create MatchingService instance with mocked dependencies"""
        return MatchingService(
            provider_repository=mock_provider_repository,
            request_repository=mock_request_repository,
            notification_service=mock_notification_service,
        )

    @given(
        request_id=st.integers(min_value=1, max_value=10000),
        max_distance=st.one_of(st.none(), st.floats(min_value=1.0, max_value=100.0)),
        min_rating=st.one_of(st.none(), st.floats(min_value=1.0, max_value=5.0)),
        limit=st.integers(min_value=1, max_value=50),
    )
    @settings(
        suppress_health_check=[HealthCheck.function_scoped_fixture], max_examples=10
    )
    @pytest.mark.asyncio
    async def test_property_matching_endpoints_return_required_response_fields(
        self,
        matching_service,
        mock_provider_repository,
        mock_request_repository,
        request_id,
        max_distance,
        min_rating,
        limit,
    ):
        """
        **Feature: labor-service-fixes, Property 1: Matching endpoints return required response fields**
        **Validates: Requirements 1.1, 1.2, 1.3, 3.1**

        For any valid request parameters, matching endpoints should return responses
        with all required fields in the correct format.
        """
        # Mock request exists
        mock_request_repository.get_by_id.return_value = {
            "id": request_id,
            "title": "Test Request",
        }

        # Mock provider repository response
        mock_providers = [
            {"provider_id": i, "match_score": 0.8 + (i * 0.01), "is_active": True}
            for i in range(min(limit, 5))
        ]
        mock_provider_repository.find_matching_providers.return_value = mock_providers

        # Test find_providers_for_request
        result = await matching_service.find_providers_for_request(
            request_id=request_id,
            max_distance=max_distance,
            min_rating=min_rating,
            limit=limit,
        )

        # Property: Response must contain all required fields
        assert "providers" in result
        assert "match_scores" in result
        assert "total_matches" in result

        # Property: Fields must be of correct types
        assert isinstance(result["providers"], list)
        assert isinstance(result["match_scores"], list)
        assert isinstance(result["total_matches"], int)

        # Property: Lists must have consistent lengths
        assert len(result["providers"]) == len(result["match_scores"])

        # Property: Total matches must be non-negative
        assert result["total_matches"] >= 0

        # Property: Match scores must be valid floats between 0 and 1
        for score in result["match_scores"]:
            assert isinstance(score, (int, float))
            assert 0 <= score <= 1

    @given(
        provider_id=st.integers(min_value=1, max_value=10000),
        max_distance=st.one_of(st.none(), st.floats(min_value=1.0, max_value=100.0)),
        budget_min=st.one_of(st.none(), st.floats(min_value=100.0, max_value=10000.0)),
        limit=st.integers(min_value=1, max_value=50),
    )
    @settings(
        suppress_health_check=[HealthCheck.function_scoped_fixture], max_examples=10
    )
    @pytest.mark.asyncio
    async def test_property_opportunities_endpoint_response_format(
        self,
        matching_service,
        mock_request_repository,
        provider_id,
        max_distance,
        budget_min,
        limit,
    ):
        """
        **Feature: labor-service-fixes, Property 1: Matching endpoints return required response fields**
        **Validates: Requirements 1.1, 1.2, 1.3, 3.1**

        For any valid provider parameters, opportunities endpoint should return responses
        with all required fields in the correct format.
        """
        # Mock request repository response
        mock_requests = [
            {"request_id": i, "match_score": 0.7 + (i * 0.02)}
            for i in range(min(limit, 5))
        ]
        mock_request_repository.find_matching_requests.return_value = mock_requests

        # Test find_opportunities_for_provider
        result = await matching_service.find_opportunities_for_provider(
            provider_id=provider_id,
            max_distance=max_distance,
            budget_min=budget_min,
            limit=limit,
        )

        # Property: Response must contain all required fields
        assert "requests" in result
        assert "match_scores" in result
        assert "total_matches" in result

        # Property: Fields must be of correct types
        assert isinstance(result["requests"], list)
        assert isinstance(result["match_scores"], list)
        assert isinstance(result["total_matches"], int)

        # Property: Lists must have consistent lengths
        assert len(result["requests"]) == len(result["match_scores"])

        # Property: Total matches must be non-negative
        assert result["total_matches"] >= 0

    @given(
        provider_id=st.integers(min_value=1, max_value=10000),
        request_id=st.integers(min_value=1, max_value=10000),
    )
    @settings(
        suppress_health_check=[HealthCheck.function_scoped_fixture], max_examples=10
    )
    @pytest.mark.asyncio
    async def test_property_match_score_calculation_response_format(
        self,
        matching_service,
        mock_provider_repository,
        mock_request_repository,
        provider_id,
        request_id,
    ):
        """
        **Feature: labor-service-fixes, Property 1: Matching endpoints return required response fields**
        **Validates: Requirements 1.1, 1.2, 1.3, 3.1**

        For any valid provider and request IDs, match score calculation should return
        all required score components in the correct format.
        """
        # Mock provider and request exist
        mock_provider_repository.get_by_id.return_value = {
            "id": provider_id,
            "skills": [],
            "location": {},
            "availability": {},
        }
        mock_request_repository.get_by_id.return_value = {
            "id": request_id,
            "required_skills": [],
            "location": {},
            "timeline": {},
        }

        # Test calculate_match_score
        result = await matching_service.calculate_match_score(
            provider_id=provider_id, request_id=request_id
        )

        # Property: Response must contain all required score fields
        required_fields = [
            "overall_score",
            "skill_match",
            "location_score",
            "availability_score",
            "rating_score",
        ]
        for field in required_fields:
            assert field in result

        # Property: All scores must be numeric and within valid range
        for field in required_fields:
            score = result[field]
            assert isinstance(score, (int, float))
            assert 0 <= score <= 100  # Assuming scores are 0-100 scale

        # Property: Overall score should be reasonable combination of component scores
        # (This is a business logic property - overall should not exceed max component)
        component_scores = [
            result[field] for field in required_fields[1:]
        ]  # Exclude overall
        if component_scores:
            max_component = max(component_scores)
            assert (
                result["overall_score"] <= max_component + 10
            )  # Allow some weighted combination variance

    @given(
        skills=st.one_of(st.none(), st.text(min_size=1, max_size=50)),
        location=st.one_of(st.none(), st.text(min_size=1, max_size=50)),
        limit=st.integers(min_value=1, max_value=100),
        offset=st.integers(min_value=0, max_value=1000),
    )
    @settings(
        suppress_health_check=[HealthCheck.function_scoped_fixture], max_examples=10
    )
    @pytest.mark.asyncio
    async def test_property_search_endpoints_return_consistent_format(
        self,
        matching_service,
        mock_provider_repository,
        skills,
        location,
        limit,
        offset,
    ):
        """
        **Feature: labor-service-fixes, Property 2: Search endpoints return consistent format**
        **Validates: Requirements 1.4, 1.5, 3.2**

        For any search parameters, search endpoints should return responses
        with consistent structure including results, total, and facets.
        """
        # Mock search response
        mock_search_result = {
            "results": [
                {"id": i, "name": f"Provider {i}"} for i in range(min(limit, 10))
            ],
            "total": 25,
            "facets": {
                "skills": {"electrical": 5, "plumbing": 3},
                "location": {"NYC": 8},
            },
        }
        mock_provider_repository.search_providers.return_value = mock_search_result

        search_params = {
            "skills": skills.split(",") if skills else None,
            "location": location,
            "limit": limit,
            "offset": offset,
        }

        # Test search_providers
        result = await matching_service.search_providers(search_params)

        # Property: Response must contain all required search fields
        assert "results" in result
        assert "total" in result
        assert "facets" in result

        # Property: Fields must be of correct types
        assert isinstance(result["results"], list)
        assert isinstance(result["total"], int)
        assert isinstance(result["facets"], dict)

        # Property: Total must be non-negative
        assert result["total"] >= 0

        # Property: Results length should not exceed limit
        assert len(result["results"]) <= limit

        # Property: If results exist, total should be positive
        if result["results"]:
            assert result["total"] > 0

    @given(
        provider_skills=st.lists(
            st.dictionaries(
                keys=st.sampled_from(["skill_id", "proficiency_level"]),
                values=st.one_of(
                    st.integers(min_value=1, max_value=100),
                    st.integers(min_value=1, max_value=5),
                ),
            ),
            min_size=0,
            max_size=10,
        ),
        request_skills=st.lists(
            st.dictionaries(
                keys=st.sampled_from(["skill_id", "required_level"]),
                values=st.one_of(
                    st.integers(min_value=1, max_value=100),
                    st.integers(min_value=1, max_value=5),
                ),
            ),
            min_size=0,
            max_size=10,
        ),
    )
    @settings(
        suppress_health_check=[HealthCheck.function_scoped_fixture], max_examples=20
    )
    @pytest.mark.asyncio
    async def test_property_real_matching_functionality(
        self, matching_service, provider_skills, request_skills
    ):
        """
        **Feature: labor-service-fixes, Property 7: Matching algorithms provide real functionality**
        **Validates: Requirements 5.1**

        For any combination of provider skills and request requirements, the matching
        algorithm should provide meaningful, consistent scoring based on actual skill overlap.
        """
        # Property: Skill matching should return scores between 0 and 1
        skill_score = matching_service._calculate_skill_match(
            provider_skills, request_skills
        )
        assert isinstance(skill_score, float)
        assert 0.0 <= skill_score <= 1.0

        # Property: Empty skills should result in low/zero score
        if not provider_skills or not request_skills:
            assert skill_score <= 0.1  # Should be very low for missing skills

        # Property: Perfect skill match should result in high score
        if provider_skills and request_skills:
            # Create a perfect match scenario
            perfect_provider_skills = [{"skill_id": 1, "proficiency_level": 5}]
            perfect_request_skills = [{"skill_id": 1, "required_level": 3}]
            perfect_score = matching_service._calculate_skill_match(
                perfect_provider_skills, perfect_request_skills
            )
            assert perfect_score >= 0.8  # Should be high for good match

        # Property: Skill matching should be deterministic
        score1 = matching_service._calculate_skill_match(
            provider_skills, request_skills
        )
        score2 = matching_service._calculate_skill_match(
            provider_skills, request_skills
        )
        assert score1 == score2  # Same inputs should give same output

    @given(
        provider_lat=st.floats(min_value=-90, max_value=90),
        provider_lng=st.floats(min_value=-180, max_value=180),
        request_lat=st.floats(min_value=-90, max_value=90),
        request_lng=st.floats(min_value=-180, max_value=180),
    )
    @settings(
        suppress_health_check=[HealthCheck.function_scoped_fixture], max_examples=15
    )
    @pytest.mark.asyncio
    async def test_property_distance_scoring_consistency(
        self, matching_service, provider_lat, provider_lng, request_lat, request_lng
    ):
        """
        **Feature: labor-service-fixes, Property 7: Matching algorithms provide real functionality**
        **Validates: Requirements 5.1**

        For any valid coordinates, distance scoring should be consistent and logical.
        """
        provider_location = {"latitude": provider_lat, "longitude": provider_lng}
        request_location = {"latitude": request_lat, "longitude": request_lng}

        # Property: Distance score should be between 0 and 1
        distance_score = matching_service._calculate_distance_score(
            provider_location, request_location
        )
        assert isinstance(distance_score, float)
        assert 0.0 <= distance_score <= 1.0

        # Property: Same location should give perfect score
        same_location_score = matching_service._calculate_distance_score(
            provider_location, provider_location
        )
        assert same_location_score >= 0.9  # Should be very high for same location

        # Property: Distance scoring should be symmetric
        score1 = matching_service._calculate_distance_score(
            provider_location, request_location
        )
        score2 = matching_service._calculate_distance_score(
            request_location, provider_location
        )
        assert abs(score1 - score2) < 0.001  # Should be essentially the same

    @pytest.mark.asyncio
    async def test_property_reputation_scoring_logic(self, matching_service):
        """
        **Feature: labor-service-fixes, Property 7: Matching algorithms provide real functionality**
        **Validates: Requirements 5.1**

        Reputation scoring should follow logical business rules.
        """
        # Property: Higher ratings should result in higher scores
        high_rating_provider = {
            "rating": 4.8,
            "total_reviews": 50,
            "completion_rate": 0.95,
            "response_time_avg": 30,
        }
        low_rating_provider = {
            "rating": 2.1,
            "total_reviews": 10,
            "completion_rate": 0.70,
            "response_time_avg": 120,
        }

        high_score = matching_service._calculate_reputation_score(
            high_rating_provider, {}
        )
        low_score = matching_service._calculate_reputation_score(
            low_rating_provider, {}
        )

        assert high_score > low_score  # Higher rated provider should score better
        assert 0.0 <= high_score <= 1.0
        assert 0.0 <= low_score <= 1.0

        # Property: More reviews should increase confidence
        experienced_provider = {
            "rating": 4.0,
            "total_reviews": 100,
            "completion_rate": 0.90,
            "response_time_avg": 45,
        }
        new_provider = {
            "rating": 4.0,
            "total_reviews": 2,
            "completion_rate": 0.90,
            "response_time_avg": 45,
        }

        experienced_score = matching_service._calculate_reputation_score(
            experienced_provider, {}
        )
        new_score = matching_service._calculate_reputation_score(new_provider, {})

        assert (
            experienced_score >= new_score
        )  # More reviews should help or at least not hurt

    @pytest.mark.asyncio
    async def test_property_analytics_return_all_expected_metrics(
        self, matching_service, mock_provider_repository, mock_request_repository
    ):
        """
        **Feature: labor-service-fixes, Property 6: Analytics return all expected metrics**
        **Validates: Requirements 3.5, 5.4**

        Analytics endpoint should always return all expected metrics with correct types.
        """
        # Mock analytics data
        mock_provider_repository.get_total_matches.return_value = 150
        mock_provider_repository.get_match_success_rate.return_value = 0.75
        mock_provider_repository.get_average_response_time.return_value = 45
        mock_provider_repository.get_top_skills.return_value = [
            "electrical",
            "plumbing",
        ]
        mock_request_repository.get_top_requested_skills.return_value = [
            "electrical",
            "carpentry",
        ]

        # Test get_analytics
        result = await matching_service.get_analytics()

        # Property: Response must contain all required analytics fields
        required_fields = [
            "total_matches",
            "match_success_rate",
            "average_response_time",
            "top_skills",
            "top_skills_requested",
        ]
        for field in required_fields:
            assert field in result

        # Property: Numeric fields must be of correct types and ranges
        assert isinstance(result["total_matches"], int)
        assert result["total_matches"] >= 0

        assert isinstance(result["match_success_rate"], (int, float))
        assert 0 <= result["match_success_rate"] <= 1

        assert isinstance(result["average_response_time"], (int, float))
        assert result["average_response_time"] >= 0

        # Property: List fields must be lists
        assert isinstance(result["top_skills"], list)
        assert isinstance(result["top_skills_requested"], list)
