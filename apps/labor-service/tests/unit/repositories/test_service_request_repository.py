"""Tests for ServiceRequestRepository."""
import pytest
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from src.models.service_request import ServiceRequest, SkillRequirement, RequestStatus, UrgencyLevel
from src.models.service_provider import Skill, SkillCategory
from src.repositories.service_request_repository import ServiceRequestRepository
from tests.factories import ServiceRequestFactory, SkillFactory, SkillCategoryFactory

class TestServiceRequestRepository:
    """Test cases for ServiceRequestRepository."""
    
    def test_create_repository(self, db_session):
        """Test repository creation."""
        repo = ServiceRequestRepository(db_session)
        assert repo.model == ServiceRequest
        assert repo.db_session == db_session
    
    def test_find_by_status(self, db_session):
        """Test finding service requests by status."""
        repo = ServiceRequestRepository(db_session)
        
        # Create test data
        open_request = ServiceRequestFactory.create(
            status=RequestStatus.ACTIVE,
            title="Open Request"
        )
        closed_request = ServiceRequestFactory.create(
            status=RequestStatus.COMPLETED,
            title="Closed Request"
        )
        db_session.commit()
        
        # Test finding by status
        open_requests = repo.find_by_status(RequestStatus.ACTIVE)
        assert len(open_requests) == 1
        assert open_requests[0].title == "Open Request"
        
        completed_requests = repo.find_by_status(RequestStatus.COMPLETED)
        assert len(completed_requests) == 1
        assert completed_requests[0].title == "Closed Request"
    
    def test_find_by_urgency(self, db_session):
        """Test finding service requests by urgency level."""
        repo = ServiceRequestRepository(db_session)
        
        # Create test data
        urgent_request = ServiceRequestFactory.create(
            urgency_level=UrgencyLevel.EMERGENCY,
            title="Urgent Request"
        )
        normal_request = ServiceRequestFactory.create(
            urgency_level=UrgencyLevel.MEDIUM,
            title="Normal Request"
        )
        db_session.commit()
        
        # Test finding by urgency
        urgent_requests = repo.find_by_urgency(UrgencyLevel.EMERGENCY)
        assert len(urgent_requests) == 1
        assert urgent_requests[0].title == "Urgent Request"
        
        normal_requests = repo.find_by_urgency(UrgencyLevel.MEDIUM)
        assert len(normal_requests) == 1
        assert normal_requests[0].title == "Normal Request"
    
    def test_find_by_budget_range(self, db_session):
        """Test finding service requests within budget range."""
        repo = ServiceRequestRepository(db_session)
        
        # Create test data
        low_budget_request = ServiceRequestFactory.create(
            budget_min=Decimal('100.00'),
            budget_max=Decimal('300.00'),
            title="Low Budget"
        )
        high_budget_request = ServiceRequestFactory.create(
            budget_min=Decimal('800.00'),
            budget_max=Decimal('1200.00'),
            title="High Budget"
        )
        db_session.commit()
        
        # Test finding within range - should find requests that overlap with the range
        mid_range_requests = repo.find_by_budget_range(200.0, 400.0)
        assert len(mid_range_requests) == 1
        assert mid_range_requests[0].title == "Low Budget"
        
        high_range_requests = repo.find_by_budget_range(900.0, 1500.0)
        assert len(high_range_requests) == 1
        assert high_range_requests[0].title == "High Budget"
    
    def test_find_by_location(self, db_session):
        """Test finding service requests by geographic location."""
        repo = ServiceRequestRepository(db_session)
        
        # Create test data (NYC area)
        nyc_request = ServiceRequestFactory.create(
            location_latitude=40.7128,
            location_longitude=-74.0060,
            title="NYC Request"
        )
        # LA area (far from NYC)
        la_request = ServiceRequestFactory.create(
            location_latitude=34.0522,
            location_longitude=-118.2437,
            title="LA Request"
        )
        db_session.commit()
        
        # Test finding near NYC (50km radius)
        nyc_area_requests = repo.find_by_location(40.7128, -74.0060, 50)
        assert len(nyc_area_requests) == 1
        assert nyc_area_requests[0].title == "NYC Request"
        
        # Test finding near LA
        la_area_requests = repo.find_by_location(34.0522, -118.2437, 50)
        assert len(la_area_requests) == 1
        assert la_area_requests[0].title == "LA Request"
    
    def test_find_by_skills(self, db_session):
        """Test finding service requests by required skills."""
        repo = ServiceRequestRepository(db_session)
        
        # Create test data
        category = SkillCategoryFactory.create(name="Construction")
        plumbing_skill = SkillFactory.create(name="Plumbing", category=category)
        electrical_skill = SkillFactory.create(name="Electrical", category=category)
        
        plumbing_request = ServiceRequestFactory.create(title="Plumbing Job")
        electrical_request = ServiceRequestFactory.create(title="Electrical Job")
        
        # Add skill requirements
        plumbing_req = SkillRequirement(
            service_request_id=plumbing_request.id,
            skill_id=plumbing_skill.id,
            proficiency_level="INTERMEDIATE",
            is_required=True,
            importance_weight=8
        )
        electrical_req = SkillRequirement(
            service_request_id=electrical_request.id,
            skill_id=electrical_skill.id,
            proficiency_level="ADVANCED",
            is_required=True,
            importance_weight=9
        )
        
        db_session.add_all([plumbing_req, electrical_req])
        db_session.commit()
        
        # Test finding by skills
        plumbing_requests = repo.find_by_skills([plumbing_skill.id])
        assert len(plumbing_requests) == 1
        assert plumbing_requests[0].title == "Plumbing Job"
        
        electrical_requests = repo.find_by_skills([electrical_skill.id])
        assert len(electrical_requests) == 1
        assert electrical_requests[0].title == "Electrical Job"
        
        # Test finding by multiple skills
        all_requests = repo.find_by_skills([plumbing_skill.id, electrical_skill.id])
        assert len(all_requests) == 2
    
    def test_find_matching_requests(self, db_session):
        """Test finding service requests matching provider capabilities."""
        repo = ServiceRequestRepository(db_session)
        
        # Create test data
        category = SkillCategoryFactory.create(name="Construction")
        plumbing_skill = SkillFactory.create(name="Plumbing", category=category)
        
        matching_request = ServiceRequestFactory.create(
            title="Matching Request",
            status=RequestStatus.ACTIVE,
            budget_max=Decimal('500.00'),
            location_latitude=40.7128,
            location_longitude=-74.0060
        )
        
        non_matching_request = ServiceRequestFactory.create(
            title="Non-matching Request",
            status=RequestStatus.COMPLETED,  # Wrong status
            budget_max=Decimal('2000.00'),
            location_latitude=40.7128,
            location_longitude=-74.0060
        )
        
        # Add skill requirement
        skill_req = SkillRequirement(
            service_request_id=matching_request.id,
            skill_id=plumbing_skill.id,
            proficiency_level="INTERMEDIATE",
            is_required=True,
            importance_weight=8
        )
        db_session.add(skill_req)
        db_session.commit()
        
        # Test matching
        matches = repo.find_matching_requests(
            skills=[plumbing_skill.id],
            max_budget=1000.0,
            location=(40.7128, -74.0060),
            radius_km=50
        )
        
        assert len(matches) == 1
        assert matches[0].title == "Matching Request"
    
    def test_get_recent_requests(self, db_session):
        """Test getting recent service requests."""
        repo = ServiceRequestRepository(db_session)
        
        # Create test data
        recent_request = ServiceRequestFactory.create(
            title="Recent Request",
            created_at=datetime.now(timezone.utc) - timedelta(days=2)
        )
        old_request = ServiceRequestFactory.create(
            title="Old Request",
            created_at=datetime.now(timezone.utc) - timedelta(days=10)
        )
        db_session.commit()
        
        # Test getting recent requests (last 7 days)
        recent_requests = repo.get_recent_requests(7)
        assert len(recent_requests) == 1
        assert recent_requests[0].title == "Recent Request"
        
        # Test getting requests from last 15 days
        all_recent_requests = repo.get_recent_requests(15)
        assert len(all_recent_requests) == 2
    
    def test_get_urgent_requests(self, db_session):
        """Test getting urgent open service requests."""
        repo = ServiceRequestRepository(db_session)
        
        # Create test data
        urgent_open_request = ServiceRequestFactory.create(
            title="Urgent Open",
            status=RequestStatus.ACTIVE,
            urgency_level=UrgencyLevel.EMERGENCY
        )
        urgent_closed_request = ServiceRequestFactory.create(
            title="Urgent Closed",
            status=RequestStatus.COMPLETED,
            urgency_level=UrgencyLevel.EMERGENCY
        )
        normal_open_request = ServiceRequestFactory.create(
            title="Normal Open",
            status=RequestStatus.ACTIVE,
            urgency_level=UrgencyLevel.MEDIUM
        )
        db_session.commit()
        
        # Test getting urgent open requests
        urgent_requests = repo.get_urgent_requests()
        assert len(urgent_requests) == 1
        assert urgent_requests[0].title == "Urgent Open"