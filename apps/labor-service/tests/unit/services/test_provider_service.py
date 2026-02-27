"""
RED Phase: Failing tests for ProviderService
Following TDD methodology - these tests define expected behavior before implementation
"""
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, Mock

import pytest
from src.core.exceptions import ProviderNotFoundError, ValidationError
from src.models.service_provider import (ProficiencyLevel, ProviderType,
                                         ServiceProvider, Skill, SkillCategory,
                                         VerificationStatus)


class TestProviderService:
    """Test suite for ProviderService - RED phase (failing tests)"""

    @pytest.fixture
    def mock_provider_repository(self):
        """Mock provider repository for testing"""
        mock = Mock()
        # Make async methods return AsyncMock
        mock.get_by_user_id = AsyncMock()
        mock.create = AsyncMock()
        mock.get_by_id = AsyncMock()
        mock.update = AsyncMock()
        mock.add_skill = AsyncMock()
        mock.update_availability = AsyncMock()
        mock.get_availability = AsyncMock()
        mock.add_service_area = AsyncMock()
        mock.update_service_area = AsyncMock()
        mock.get_analytics = AsyncMock()
        mock.update_verification_documents = AsyncMock()
        mock.update_verification_status = AsyncMock()
        mock.search_by_location = AsyncMock()
        mock.get_recommendations = AsyncMock()
        return mock

    @pytest.fixture
    def mock_skill_repository(self):
        """Mock skill repository for testing"""
        return Mock()

    @pytest.fixture
    def provider_service(self, mock_provider_repository, mock_skill_repository):
        """Create ProviderService instance with mocked dependencies"""
        # This import will fail until ProviderService is implemented
        from src.services.provider_service import ProviderService

        return ProviderService(
            provider_repository=mock_provider_repository,
            skill_repository=mock_skill_repository,
        )

    @pytest.fixture
    def sample_provider_data(self):
        """Sample provider registration data"""
        return {
            "user_id": 1,
            "individual_name": "John Smith",
            "business_name": "Smith Construction",
            "provider_type": ProviderType.BUSINESS,
            "description": "Professional contractor with 10 years experience",
            "experience_years": 10,
            "skills": [
                {
                    "skill_id": 1,
                    "proficiency_level": ProficiencyLevel.ADVANCED,
                    "years_experience": 8,
                    "hourly_rate": Decimal("75.00"),
                }
            ],
            "service_areas": [
                {
                    "center_latitude": 40.7128,
                    "center_longitude": -74.0060,
                    "radius_miles": 25,
                    "travel_rate": Decimal("1.50"),
                    "is_primary": True,
                }
            ],
        }

    # Provider Registration Tests
    @pytest.mark.asyncio
    async def test_register_provider_success(
        self, provider_service, mock_provider_repository, sample_provider_data
    ):
        """Test successful provider registration"""
        # Setup mocks - no existing provider
        mock_provider_repository.get_by_user_id.return_value = None

        expected_provider = ServiceProvider(
            id=1,
            user_id=sample_provider_data["user_id"],
            individual_name=sample_provider_data["individual_name"],
            business_name=sample_provider_data["business_name"],
            provider_type=sample_provider_data["provider_type"],
            verification_status=VerificationStatus.PENDING,
            created_at=datetime.now(timezone.utc),
        )
        mock_provider_repository.create.return_value = expected_provider

        result = await provider_service.register_provider(sample_provider_data)

        assert result is not None
        assert result.user_id == sample_provider_data["user_id"]
        assert result.individual_name == sample_provider_data["individual_name"]
        assert result.verification_status == VerificationStatus.PENDING
        mock_provider_repository.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_register_provider_duplicate_user(
        self, provider_service, mock_provider_repository, sample_provider_data
    ):
        """Test provider registration with duplicate user_id"""
        mock_provider_repository.get_by_user_id.return_value = ServiceProvider(
            id=1, user_id=1
        )

        with pytest.raises(
            ValidationError, match="Provider already exists for this user"
        ):
            await provider_service.register_provider(sample_provider_data)

    @pytest.mark.asyncio
    async def test_get_provider_success(
        self, provider_service, mock_provider_repository
    ):
        """Test successful provider retrieval"""
        expected_provider = ServiceProvider(
            id=1,
            user_id=1,
            individual_name="John Smith",
            verification_status=VerificationStatus.VERIFIED,
        )
        mock_provider_repository.get_by_id.return_value = expected_provider

        result = await provider_service.get_provider(1)

        assert result == expected_provider
        mock_provider_repository.get_by_id.assert_called_once_with(1)

    @pytest.mark.asyncio
    async def test_get_provider_not_found(
        self, provider_service, mock_provider_repository
    ):
        """Test provider retrieval when provider doesn't exist"""
        mock_provider_repository.get_by_id.return_value = None

        with pytest.raises(ProviderNotFoundError):
            await provider_service.get_provider(999)

    @pytest.mark.asyncio
    async def test_update_provider_profile(
        self, provider_service, mock_provider_repository
    ):
        """Test provider profile update"""
        existing_provider = ServiceProvider(
            id=1, user_id=1, individual_name="John Smith", description="Old description"
        )
        mock_provider_repository.get_by_id.return_value = existing_provider

        update_data = {
            "description": "Updated professional description",
            "experience_years": 12,
        }

        updated_provider = ServiceProvider(
            id=1,
            user_id=1,
            individual_name="John Smith",
            description="Updated professional description",
            experience_years=12,
        )
        mock_provider_repository.update.return_value = updated_provider

        result = await provider_service.update_provider(1, update_data)

        assert result.description == "Updated professional description"
        assert result.experience_years == 12
        mock_provider_repository.update.assert_called_once()

    @pytest.mark.asyncio
    async def test_add_provider_skill(self, provider_service, mock_provider_repository):
        """Test adding skill to provider"""
        provider = ServiceProvider(id=1, user_id=1, individual_name="John Smith")
        mock_provider_repository.get_by_id.return_value = provider

        skill_data = {
            "skill_id": 1,
            "proficiency_level": ProficiencyLevel.ADVANCED,
            "years_experience": 5,
            "hourly_rate": Decimal("80.00"),
        }

        # Mock the return value for add_skill
        mock_skill_result = Mock()
        mock_skill_result.skill_id = 1
        mock_skill_result.proficiency_level = ProficiencyLevel.ADVANCED
        mock_provider_repository.add_skill.return_value = mock_skill_result

        result = await provider_service.add_skill(1, skill_data)

        assert result is not None
        assert result.skill_id == 1
        assert result.proficiency_level == ProficiencyLevel.ADVANCED
        mock_provider_repository.add_skill.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_availability(
        self, provider_service, mock_provider_repository
    ):
        """Test provider availability update"""
        provider = ServiceProvider(id=1, user_id=1, individual_name="John Smith")
        mock_provider_repository.get_by_id.return_value = provider

        availability_data = {
            "available_from": datetime.now(timezone.utc),
            "available_until": datetime.now(timezone.utc) + timedelta(days=30),
            "weekly_schedule": {
                "monday": {"start": "08:00", "end": "17:00"},
                "tuesday": {"start": "08:00", "end": "17:00"},
            },
        }

        result = await provider_service.update_availability(1, availability_data)

        assert result is True
        mock_provider_repository.update_availability.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_provider_analytics(
        self, provider_service, mock_provider_repository
    ):
        """Test retrieving provider performance analytics"""
        provider = ServiceProvider(id=1, user_id=1, individual_name="John Smith")
        mock_provider_repository.get_by_id.return_value = provider

        expected_analytics = {
            "total_jobs": 25,
            "completion_rate": 0.96,
            "average_rating": 4.7,
            "response_time_avg": 45,
            "earnings_last_30_days": Decimal("3500.00"),
        }
        mock_provider_repository.get_analytics.return_value = expected_analytics

        result = await provider_service.get_provider_analytics(1)

        assert result["total_jobs"] == 25
        assert result["completion_rate"] == 0.96
        mock_provider_repository.get_analytics.assert_called_once_with(1)
