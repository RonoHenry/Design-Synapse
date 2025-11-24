"""
RED Phase: Failing tests for RequestService
Following TDD methodology - these tests define expected behavior before implementation
"""
import pytest
from unittest.mock import Mock, AsyncMock
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from src.models.service_request import ServiceRequest, RequestStatus, UrgencyLevel
from src.models.service_request import SkillRequirement
from src.models.service_provider import ProficiencyLevel
from src.core.exceptions import ServiceRequestNotFoundError as RequestNotFoundError, ValidationError


class TestRequestService:
    """Test suite for RequestService - RED phase (failing tests)"""
    
    @pytest.fixture
    def mock_request_repository(self):
        """Mock request repository for testing"""
        mock = Mock()
        mock.create = AsyncMock()
        mock.get_by_id = AsyncMock()
        mock.update = AsyncMock()
        mock.get_by_seeker_id = AsyncMock()
        mock.search_by_location = AsyncMock()
        mock.search_by_skills = AsyncMock()
        mock.get_analytics = AsyncMock()
        return mock
    
    @pytest.fixture
    def mock_skill_repository(self):
        """Mock skill repository for testing"""
        return Mock()
    
    @pytest.fixture
    def mock_notification_service(self):
        """Mock notification service for testing"""
        mock = Mock()
        mock.notify_providers_of_new_request = AsyncMock()
        return mock
    
    @pytest.fixture
    def request_service(self, mock_request_repository, mock_skill_repository, mock_notification_service):
        """Create RequestService instance with mocked dependencies"""
        # This import will fail until RequestService is implemented
        from src.services.request_service import RequestService
        return RequestService(
            request_repository=mock_request_repository,
            skill_repository=mock_skill_repository,
            notification_service=mock_notification_service
        )
    
    @pytest.fixture
    def sample_request_data(self):
        """Sample service request data"""
        return {
            "seeker_id": 1,
            "project_id": 1,
            "title": "Kitchen Renovation - Electrical Work",
            "description": "Need electrical work for kitchen renovation including new outlets and lighting",
            "location_latitude": 40.7128,
            "location_longitude": -74.0060,
            "location_address": "123 Main St, New York, NY 10001",
            "urgency_level": UrgencyLevel.MEDIUM,
            "budget_min": Decimal("1500.00"),
            "budget_max": Decimal("3000.00"),
            "preferred_start_date": datetime.now(timezone.utc) + timedelta(days=7),
            "estimated_duration_hours": 16,
            "skills_required": [
                {
                    "skill_id": 1,  # Electrical
                    "required_level": ProficiencyLevel.ADVANCED,
                    "is_primary": True,
                    "estimated_hours": 12
                },
                {
                    "skill_id": 5,  # General Construction
                    "required_level": ProficiencyLevel.INTERMEDIATE,
                    "is_primary": False,
                    "estimated_hours": 4
                }
            ],
            "requirements": {
                "insurance_required": True,
                "license_required": True,
                "background_check": False
            }
        }

    # Request Creation Tests
    @pytest.mark.asyncio
    async def test_create_request_success(self, request_service, mock_request_repository, sample_request_data):
        """Test successful service request creation"""
        # This test will fail until RequestService.create_request is implemented
        mock_request_repository.create.return_value = ServiceRequest(
            id=1,
            seeker_id=sample_request_data["seeker_id"],
            title=sample_request_data["title"],
            description=sample_request_data["description"],
            status=RequestStatus.DRAFT,
            created_at=datetime.now(timezone.utc)
        )
        
        result = await request_service.create_request(sample_request_data)
        
        assert result is not None
        assert result.seeker_id == sample_request_data["seeker_id"]
        assert result.title == sample_request_data["title"]
        assert result.status == RequestStatus.DRAFT
        mock_request_repository.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_request_with_invalid_location(self, request_service, sample_request_data):
        """Test request creation with invalid location coordinates"""
        sample_request_data["location_latitude"] = 200.0  # Invalid latitude
        sample_request_data["location_longitude"] = -200.0  # Invalid longitude
        
        with pytest.raises(ValidationError, match="Invalid location coordinates"):
            await request_service.create_request(sample_request_data)

    @pytest.mark.asyncio
    async def test_create_request_with_invalid_budget(self, request_service, sample_request_data):
        """Test request creation with invalid budget range"""
        sample_request_data["budget_min"] = Decimal("5000.00")
        sample_request_data["budget_max"] = Decimal("2000.00")  # Max less than min
        
        with pytest.raises(ValidationError, match="Budget maximum must be greater than minimum"):
            await request_service.create_request(sample_request_data)

    @pytest.mark.asyncio
    async def test_create_emergency_request(self, request_service, mock_request_repository, sample_request_data):
        """Test creating emergency service request"""
        sample_request_data["urgency_level"] = UrgencyLevel.EMERGENCY
        sample_request_data["preferred_start_date"] = datetime.now(timezone.utc) + timedelta(hours=2)
        
        mock_request_repository.create.return_value = ServiceRequest(
            id=1,
            urgency_level=UrgencyLevel.EMERGENCY,
            status=RequestStatus.ACTIVE  # Emergency requests go directly to active
        )
        
        result = await request_service.create_request(sample_request_data)
        
        assert result.urgency_level == UrgencyLevel.EMERGENCY
        assert result.status == RequestStatus.ACTIVE
        mock_request_repository.create.assert_called_once()

    # Request Management Tests
    @pytest.mark.asyncio
    async def test_get_request_success(self, request_service, mock_request_repository):
        """Test successful request retrieval"""
        expected_request = ServiceRequest(
            id=1,
            seeker_id=1,
            title="Test Request",
            status=RequestStatus.ACTIVE
        )
        mock_request_repository.get_by_id.return_value = expected_request
        
        result = await request_service.get_request(1)
        
        assert result == expected_request
        mock_request_repository.get_by_id.assert_called_once_with(1)

    @pytest.mark.asyncio
    async def test_get_request_not_found(self, request_service, mock_request_repository):
        """Test request retrieval when request doesn't exist"""
        mock_request_repository.get_by_id.return_value = None
        
        with pytest.raises(RequestNotFoundError):
            await request_service.get_request(999)

    @pytest.mark.asyncio
    async def test_update_request_status(self, request_service, mock_request_repository):
        """Test updating request status"""
        existing_request = ServiceRequest(
            id=1,
            seeker_id=1,
            title="Test Request",
            status=RequestStatus.DRAFT
        )
        mock_request_repository.get_by_id.return_value = existing_request
        
        updated_request = ServiceRequest(
            id=1,
            seeker_id=1,
            title="Test Request",
            status=RequestStatus.ACTIVE
        )
        mock_request_repository.update.return_value = updated_request
        
        result = await request_service.update_status(1, RequestStatus.ACTIVE)
        
        assert result.status == RequestStatus.ACTIVE
        mock_request_repository.update.assert_called_once()

    @pytest.mark.asyncio
    async def test_publish_request(self, request_service, mock_request_repository, mock_notification_service):
        """Test publishing a request to make it active"""
        draft_request = ServiceRequest(
            id=1,
            seeker_id=1,
            title="Test Request",
            status=RequestStatus.DRAFT
        )
        mock_request_repository.get_by_id.return_value = draft_request
        
        published_request = ServiceRequest(
            id=1,
            seeker_id=1,
            title="Test Request",
            status=RequestStatus.ACTIVE
        )
        mock_request_repository.update.return_value = published_request
        
        result = await request_service.publish_request(1)
        
        assert result.status == RequestStatus.ACTIVE
        mock_request_repository.update.assert_called_once()
        mock_notification_service.notify_providers_of_new_request.assert_called_once_with(1)

    # Request Search and Filtering Tests
    @pytest.mark.asyncio
    async def test_search_requests_by_seeker(self, request_service, mock_request_repository):
        """Test searching requests by seeker ID"""
        expected_requests = [
            ServiceRequest(id=1, seeker_id=1, title="Request 1"),
            ServiceRequest(id=2, seeker_id=1, title="Request 2")
        ]
        mock_request_repository.get_by_seeker_id.return_value = expected_requests
        
        result = await request_service.get_requests_by_seeker(1)
        
        assert len(result) == 2
        assert all(req.seeker_id == 1 for req in result)
        mock_request_repository.get_by_seeker_id.assert_called_once_with(1)

    @pytest.mark.asyncio
    async def test_search_requests_by_location(self, request_service, mock_request_repository):
        """Test searching requests by location"""
        search_criteria = {
            "latitude": 40.7128,
            "longitude": -74.0060,
            "radius_miles": 25,
            "status": RequestStatus.ACTIVE
        }
        
        expected_requests = [
            ServiceRequest(id=1, title="Nearby Request 1"),
            ServiceRequest(id=2, title="Nearby Request 2")
        ]
        mock_request_repository.search_by_location.return_value = expected_requests
        
        result = await request_service.search_requests_by_location(search_criteria)
        
        assert len(result) == 2
        mock_request_repository.search_by_location.assert_called_once()

    @pytest.mark.asyncio
    async def test_search_requests_by_skills(self, request_service, mock_request_repository):
        """Test searching requests by required skills"""
        skill_ids = [1, 2, 3]  # Electrical, Plumbing, Carpentry
        
        expected_requests = [
            ServiceRequest(id=1, title="Multi-skill Request")
        ]
        mock_request_repository.search_by_skills.return_value = expected_requests
        
        result = await request_service.search_requests_by_skills(skill_ids)
        
        assert len(result) == 1
        mock_request_repository.search_by_skills.assert_called_once_with(skill_ids)

    # Request Validation Tests
    @pytest.mark.asyncio
    async def test_validate_request_completeness(self, request_service, mock_request_repository):
        """Test validating request has all required information"""
        incomplete_request = ServiceRequest(
            id=1,
            seeker_id=1,
            title="Incomplete Request",
            description="",  # Missing description
            status=RequestStatus.DRAFT
        )
        mock_request_repository.get_by_id.return_value = incomplete_request
        
        result = await request_service.validate_request_completeness(1)
        
        assert result is False

    @pytest.mark.asyncio
    async def test_validate_complete_request(self, request_service, mock_request_repository):
        """Test validating complete request"""
        complete_request = ServiceRequest(
            id=1,
            seeker_id=1,
            title="Complete Request",
            description="Detailed description",
            location_latitude=40.7128,
            location_longitude=-74.0060,
            budget_min=Decimal("1000.00"),
            budget_max=Decimal("2000.00"),
            status=RequestStatus.DRAFT
        )
        mock_request_repository.get_by_id.return_value = complete_request
        
        result = await request_service.validate_request_completeness(1)
        
        assert result is True

    # Request Cancellation Tests
    @pytest.mark.asyncio
    async def test_cancel_request(self, request_service, mock_request_repository):
        """Test cancelling an active request"""
        active_request = ServiceRequest(
            id=1,
            seeker_id=1,
            title="Active Request",
            status=RequestStatus.ACTIVE
        )
        mock_request_repository.get_by_id.return_value = active_request
        
        cancelled_request = ServiceRequest(
            id=1,
            seeker_id=1,
            title="Active Request",
            status=RequestStatus.CANCELLED
        )
        mock_request_repository.update.return_value = cancelled_request
        
        result = await request_service.cancel_request(1, "Changed requirements")
        
        assert result.status == RequestStatus.CANCELLED
        mock_request_repository.update.assert_called_once()

    @pytest.mark.asyncio
    async def test_cannot_cancel_completed_request(self, request_service, mock_request_repository):
        """Test that completed requests cannot be cancelled"""
        completed_request = ServiceRequest(
            id=1,
            seeker_id=1,
            title="Completed Request",
            status=RequestStatus.COMPLETED
        )
        mock_request_repository.get_by_id.return_value = completed_request
        
        with pytest.raises(ValidationError, match="Cannot cancel completed request"):
            await request_service.cancel_request(1, "Too late")

    # Request Analytics Tests
    @pytest.mark.asyncio
    async def test_get_request_analytics(self, request_service, mock_request_repository):
        """Test retrieving request performance analytics"""
        request = ServiceRequest(id=1, seeker_id=1, title="Test Request")
        mock_request_repository.get_by_id.return_value = request
        
        expected_analytics = {
            "views": 45,
            "quotes_received": 8,
            "response_rate": 0.18,
            "average_quote_amount": Decimal("2250.00"),
            "time_to_first_quote": 120  # minutes
        }
        mock_request_repository.get_analytics.return_value = expected_analytics
        
        result = await request_service.get_request_analytics(1)
        
        assert result["views"] == 45
        assert result["quotes_received"] == 8
        mock_request_repository.get_analytics.assert_called_once_with(1)