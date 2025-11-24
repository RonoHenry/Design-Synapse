"""
RED Phase: Failing tests for MatchingService
Following TDD methodology - these tests define expected behavior before implementation
"""
import pytest
from unittest.mock import Mock, AsyncMock
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from src.models.service_provider import ServiceProvider, VerificationStatus
from src.models.service_request import ServiceRequest, RequestStatus, UrgencyLevel
from src.models.service_provider import ProficiencyLevel
from src.core.exceptions import MatchingError, ValidationError


class TestMatchingService:
    """Test suite for MatchingService - RED phase (failing tests)"""
    
    @pytest.fixture
    def mock_provider_repository(self):
        """Mock provider repository for testing"""
        mock = Mock()
        mock.find_matching_providers = AsyncMock()
        mock.find_emergency_providers = AsyncMock()
        mock.find_team_matches = AsyncMock()
        return mock
    
    @pytest.fixture
    def mock_request_repository(self):
        """Mock request repository for testing"""
        mock = Mock()
        mock.get_by_id = AsyncMock()
        mock.find_matching_requests = AsyncMock()
        return mock
    
    @pytest.fixture
    def mock_notification_service(self):
        """Mock notification service for testing"""
        mock = Mock()
        mock.send_job_alerts = AsyncMock()
        mock.notify_providers = AsyncMock()
        return mock
    
    @pytest.fixture
    def matching_service(self, mock_provider_repository, mock_request_repository, mock_notification_service):
        """Create MatchingService instance with mocked dependencies"""
        # This import will fail until MatchingService is implemented
        from src.services.matching_service import MatchingService
        return MatchingService(
            provider_repository=mock_provider_repository,
            request_repository=mock_request_repository,
            notification_service=mock_notification_service
        )
    
    @pytest.fixture
    def sample_provider(self):
        """Sample service provider for testing"""
        return ServiceProvider(
            id=1,
            user_id=1,
            individual_name="John Smith",
            verification_status=VerificationStatus.VERIFIED,
            rating=4.5,
            total_reviews=25,
            response_time_avg=45,
            experience_years=8
        )
    
    @pytest.fixture
    def sample_request(self):
        """Sample service request for testing"""
        return ServiceRequest(
            id=1,
            seeker_id=2,
            title="Kitchen Electrical Work",
            description="Need electrical work for kitchen renovation",
            location_latitude=40.7128,
            location_longitude=-74.0060,
            urgency_level=UrgencyLevel.MEDIUM,
            budget_min=Decimal("1500.00"),
            budget_max=Decimal("3000.00"),
            status=RequestStatus.ACTIVE
        )

    # Provider-Request Matching Tests
    @pytest.mark.asyncio
    async def test_find_providers_for_request(self, matching_service, mock_provider_repository, mock_request_repository, sample_request):
        """Test finding matching providers for a service request"""
        # Mock request exists
        mock_request_repository.get_by_id.return_value = sample_request
        expected_matches = [
            {
                "provider_id": 1,
                "match_score": 0.95,
                "distance_miles": 12.5,
                "reasons": ["skill_match", "location", "rating", "availability"]
            },
            {
                "provider_id": 2,
                "match_score": 0.87,
                "distance_miles": 18.2,
                "reasons": ["skill_match", "experience", "response_time"]
            }
        ]
        mock_provider_repository.find_matching_providers.return_value = expected_matches
        
        result = await matching_service.find_providers_for_request(1)
        
        assert len(result) == 2
        assert result[0]["match_score"] == 0.95
        assert result[0]["provider_id"] == 1
        assert "skill_match" in result[0]["reasons"]
        mock_provider_repository.find_matching_providers.assert_called_once_with(1)

    @pytest.mark.asyncio
    async def test_find_opportunities_for_provider(self, matching_service, mock_request_repository, sample_provider):
        """Test finding job opportunities for a service provider"""
        expected_opportunities = [
            {
                "request_id": 1,
                "match_score": 0.92,
                "distance_miles": 15.3,
                "budget_range": {"min": Decimal("1500.00"), "max": Decimal("3000.00")},
                "urgency": UrgencyLevel.MEDIUM
            },
            {
                "request_id": 3,
                "match_score": 0.84,
                "distance_miles": 22.1,
                "budget_range": {"min": Decimal("2000.00"), "max": Decimal("4000.00")},
                "urgency": UrgencyLevel.HIGH
            }
        ]
        mock_request_repository.find_matching_requests.return_value = expected_opportunities
        
        result = await matching_service.find_opportunities_for_provider(1)
        
        assert len(result) == 2
        assert result[0]["match_score"] == 0.92
        assert result[0]["request_id"] == 1
        mock_request_repository.find_matching_requests.assert_called_once_with(1)

    @pytest.mark.asyncio
    async def test_calculate_match_score(self, matching_service, sample_provider, sample_request):
        """Test calculating match score between provider and request"""
        # Mock the individual scoring components
        matching_service._calculate_skill_match = Mock(return_value=0.90)
        matching_service._calculate_distance_score = Mock(return_value=0.85)
        matching_service._calculate_availability_score = Mock(return_value=0.95)
        matching_service._calculate_reputation_score = Mock(return_value=0.88)
        matching_service._calculate_response_score = Mock(return_value=0.92)
        
        result = await matching_service.calculate_match_score(sample_provider.id, sample_request.id)
        
        # Expected weighted score: 0.90*0.4 + 0.85*0.25 + 0.95*0.2 + 0.88*0.1 + 0.92*0.05 = 0.8885
        assert 0.88 <= result <= 0.90
        assert isinstance(result, float)

    # Skill Matching Tests
    @pytest.mark.asyncio
    async def test_skill_match_calculation(self, matching_service):
        """Test skill matching algorithm"""
        provider_skills = [
            {"skill_id": 1, "proficiency_level": ProficiencyLevel.ADVANCED, "years_experience": 8},
            {"skill_id": 2, "proficiency_level": ProficiencyLevel.INTERMEDIATE, "years_experience": 5}
        ]
        
        request_skills = [
            {"skill_id": 1, "required_level": ProficiencyLevel.INTERMEDIATE, "is_primary": True},
            {"skill_id": 2, "required_level": ProficiencyLevel.BEGINNER, "is_primary": False}
        ]
        
        result = matching_service._calculate_skill_match(provider_skills, request_skills)
        
        # Should be high score since provider exceeds requirements
        assert result >= 0.90
        assert isinstance(result, float)

    @pytest.mark.asyncio
    async def test_skill_mismatch_calculation(self, matching_service):
        """Test skill matching when provider doesn't meet requirements"""
        provider_skills = [
            {"skill_id": 1, "proficiency_level": ProficiencyLevel.BEGINNER, "years_experience": 1}
        ]
        
        request_skills = [
            {"skill_id": 1, "required_level": ProficiencyLevel.EXPERT, "is_primary": True},
            {"skill_id": 2, "required_level": ProficiencyLevel.ADVANCED, "is_primary": True}  # Missing skill
        ]
        
        result = matching_service._calculate_skill_match(provider_skills, request_skills)
        
        # Should be low score due to skill gaps
        assert result <= 0.30
        assert isinstance(result, float)

    # Location Matching Tests
    @pytest.mark.asyncio
    async def test_distance_score_calculation(self, matching_service):
        """Test distance-based scoring"""
        provider_location = {"latitude": 40.7128, "longitude": -74.0060}  # NYC
        request_location = {"latitude": 40.7589, "longitude": -73.9851}   # Manhattan
        
        result = matching_service._calculate_distance_score(provider_location, request_location)
        
        # Close locations should have high score
        assert result >= 0.80
        assert isinstance(result, float)

    @pytest.mark.asyncio
    async def test_distance_score_far_locations(self, matching_service):
        """Test distance scoring for far locations"""
        provider_location = {"latitude": 40.7128, "longitude": -74.0060}  # NYC
        request_location = {"latitude": 34.0522, "longitude": -118.2437}  # LA
        
        result = matching_service._calculate_distance_score(provider_location, request_location)
        
        # Far locations should have low score
        assert result <= 0.20
        assert isinstance(result, float)

    # Availability Matching Tests
    @pytest.mark.asyncio
    async def test_availability_match_calculation(self, matching_service):
        """Test availability matching"""
        provider_availability = {
            "available_from": datetime.now(timezone.utc),
            "available_until": datetime.now(timezone.utc) + timedelta(days=30),
            "weekly_schedule": {
                "monday": {"start": "08:00", "end": "17:00"},
                "tuesday": {"start": "08:00", "end": "17:00"}
            }
        }
        
        request_timing = {
            "preferred_start_date": datetime.now(timezone.utc) + timedelta(days=7),
            "estimated_duration_hours": 8
        }
        
        result = matching_service._calculate_availability_score(provider_availability, request_timing)
        
        # Good availability match should have high score
        assert result >= 0.80
        assert isinstance(result, float)

    # Notification and Alert Tests
    @pytest.mark.asyncio
    async def test_send_job_alerts(self, matching_service, mock_notification_service):
        """Test sending job alerts to providers"""
        provider_id = 1
        matching_requests = [
            {"request_id": 1, "match_score": 0.95, "urgency": UrgencyLevel.HIGH},
            {"request_id": 2, "match_score": 0.87, "urgency": UrgencyLevel.MEDIUM}
        ]
        
        result = await matching_service.send_job_alerts(provider_id, matching_requests)
        
        assert result is True
        mock_notification_service.send_job_alerts.assert_called_once_with(provider_id, matching_requests)

    @pytest.mark.asyncio
    async def test_notify_providers_of_new_request(self, matching_service, mock_provider_repository, mock_notification_service):
        """Test notifying relevant providers of new request"""
        request_id = 1
        matching_providers = [
            {"provider_id": 1, "match_score": 0.95},
            {"provider_id": 2, "match_score": 0.87},
            {"provider_id": 3, "match_score": 0.82}
        ]
        mock_provider_repository.find_matching_providers.return_value = matching_providers
        
        result = await matching_service.notify_providers_of_new_request(request_id)
        
        assert result is True
        # Should only notify top matches (score >= 0.85)
        expected_notifications = [p for p in matching_providers if p["match_score"] >= 0.85]
        mock_notification_service.notify_providers.assert_called_once()

    # Matching Algorithm Configuration Tests
    @pytest.mark.asyncio
    async def test_emergency_request_matching(self, matching_service, mock_provider_repository):
        """Test matching for emergency requests prioritizes availability"""
        emergency_request = ServiceRequest(
            id=1,
            urgency_level=UrgencyLevel.EMERGENCY,
            preferred_start_date=datetime.now(timezone.utc) + timedelta(hours=2)
        )
        
        # Emergency matching should prioritize immediate availability
        expected_matches = [
            {"provider_id": 1, "match_score": 0.92, "available_immediately": True},
            {"provider_id": 2, "match_score": 0.88, "available_immediately": True}
        ]
        mock_provider_repository.find_emergency_providers.return_value = expected_matches
        
        result = await matching_service.find_providers_for_emergency_request(1)
        
        assert len(result) == 2
        assert all(match["available_immediately"] for match in result)
        mock_provider_repository.find_emergency_providers.assert_called_once_with(1)

    @pytest.mark.asyncio
    async def test_bulk_matching_for_project(self, matching_service, mock_provider_repository):
        """Test matching multiple providers for large project"""
        project_requests = [1, 2, 3]  # Multiple related requests
        
        expected_team_matches = [
            {
                "team_composition": [
                    {"provider_id": 1, "role": "lead_electrician", "match_score": 0.95},
                    {"provider_id": 2, "role": "assistant_electrician", "match_score": 0.87},
                    {"provider_id": 3, "role": "general_contractor", "match_score": 0.82}
                ],
                "team_score": 0.88,
                "coordination_score": 0.92
            }
        ]
        mock_provider_repository.find_team_matches.return_value = expected_team_matches
        
        result = await matching_service.find_team_for_project(project_requests)
        
        assert len(result) == 1
        assert "team_composition" in result[0]
        assert result[0]["team_score"] == 0.88
        mock_provider_repository.find_team_matches.assert_called_once()

    # Performance and Optimization Tests
    @pytest.mark.asyncio
    async def test_matching_performance_with_large_dataset(self, matching_service, mock_provider_repository):
        """Test matching performance with large number of providers"""
        # Simulate large dataset
        large_provider_list = [{"provider_id": i, "match_score": 0.5 + (i % 50) / 100} for i in range(1000)]
        mock_provider_repository.find_matching_providers.return_value = large_provider_list
        
        start_time = datetime.now(timezone.utc)
        result = await matching_service.find_providers_for_request(1)
        end_time = datetime.now(timezone.utc)
        
        # Should return top matches efficiently
        assert len(result) <= 20  # Limited to top matches
        assert (end_time - start_time).total_seconds() < 2.0  # Performance requirement
        
        # Results should be sorted by match score
        scores = [match["match_score"] for match in result]
        assert scores == sorted(scores, reverse=True)

    # Error Handling Tests
    @pytest.mark.asyncio
    async def test_matching_with_invalid_request(self, matching_service, mock_request_repository):
        """Test matching behavior with invalid request"""
        mock_request_repository.get_by_id.return_value = None
        
        with pytest.raises(MatchingError, match="Request not found"):
            await matching_service.find_providers_for_request(999)

    @pytest.mark.asyncio
    async def test_matching_with_inactive_providers(self, matching_service, mock_provider_repository):
        """Test that inactive providers are excluded from matching"""
        all_providers = [
            {"provider_id": 1, "is_active": True, "match_score": 0.95},
            {"provider_id": 2, "is_active": False, "match_score": 0.90},  # Should be excluded
            {"provider_id": 3, "is_active": True, "match_score": 0.85}
        ]
        mock_provider_repository.find_matching_providers.return_value = all_providers
        
        result = await matching_service.find_providers_for_request(1)
        
        # Should only include active providers
        active_provider_ids = [match["provider_id"] for match in result]
        assert 2 not in active_provider_ids
        assert 1 in active_provider_ids
        assert 3 in active_provider_ids