"""
TDD Tests for ServiceRequest Model

Following Test-Driven Development principles:
1. Write failing tests first (RED)
2. Implement minimal code to make tests pass (GREEN)
3. Refactor while keeping tests green (REFACTOR)

These tests define the expected behavior of the ServiceRequest model
BEFORE implementation exists.
"""

import pytest
from decimal import Decimal
from datetime import datetime, timedelta
from sqlalchemy.exc import IntegrityError

# These imports will fail initially - that's the point of TDD!
# We write tests for models that don't exist yet
try:
    from src.models.service_request import (
        ServiceRequest, SkillRequirement, UrgencyLevel, RequestStatus
    )
    from tests.factories import SkillFactory, ServiceRequestFactory
except ImportError:
    # Expected during TDD RED phase
    ServiceRequest = None
    SkillRequirement = None
    UrgencyLevel = None
    RequestStatus = None
    SkillFactory = None
    ServiceRequestFactory = None

from tests.factories import (
    ServiceProviderFactory, SkillRequirementFactory
)


@pytest.mark.unit
@pytest.mark.tdd
class TestServiceRequestModel:
    """TDD Test cases for ServiceRequest model - RED phase."""
    
    def test_create_service_request_with_required_fields(self, db_session):
        """
        TDD Test: ServiceRequest should be created with minimal required fields.
        
        This test defines the minimum requirements for creating a ServiceRequest.
        Requirements: 3.1, 3.2
        """
        # Arrange - Define what we expect to work
        request_data = {
            "seeker_id": 1,  # Reference to User Service
            "title": "Kitchen Renovation - Electrical Work",
            "description": "Need licensed electrician for kitchen renovation project",
            "location_latitude": Decimal("40.7128"),
            "location_longitude": Decimal("-74.0060"),
            "location_address": "123 Main St, New York, NY 10001",
            "urgency_level": UrgencyLevel.MEDIUM,
            "preferred_start_date": datetime.now() + timedelta(days=7)
        }
        
        # Act - Create the service request
        request = ServiceRequest(**request_data)
        db_session.add(request)
        db_session.commit()
        db_session.refresh(request)
        
        # Assert - Verify the request was created correctly
        assert request.id is not None
        assert request.seeker_id == 1
        assert request.title == "Kitchen Renovation - Electrical Work"
        assert request.status == RequestStatus.DRAFT  # Default status
        assert request.urgency_level == UrgencyLevel.MEDIUM
        assert request.created_at is not None
        assert request.updated_at is not None
    
    def test_service_request_budget_range_handling(self, db_session):
        """
        TDD Test: ServiceRequest should handle budget ranges properly.
        
        Requirements: 3.3
        """
        # Arrange & Act - Create request with budget range
        request = ServiceRequest(
            seeker_id=1,
            title="Plumbing Repair",
            description="Fix leaky pipes",
            location_latitude=Decimal("40.7128"),
            location_longitude=Decimal("-74.0060"),
            location_address="456 Oak Ave, Brooklyn, NY 11201",
            budget_min=Decimal("500.00"),
            budget_max=Decimal("1500.00"),
            urgency_level=UrgencyLevel.HIGH
        )
        db_session.add(request)
        db_session.commit()
        
        # Assert - Verify budget handling
        assert request.budget_min == Decimal("500.00")
        assert request.budget_max == Decimal("1500.00")
        assert request.budget_min <= request.budget_max
    
    def test_service_request_urgency_levels(self, db_session):
        """
        TDD Test: ServiceRequest should support different urgency levels.
        
        Requirements: 3.5
        """
        # Test all urgency levels
        urgency_levels = [
            UrgencyLevel.LOW,
            UrgencyLevel.MEDIUM, 
            UrgencyLevel.HIGH,
            UrgencyLevel.EMERGENCY
        ]
        
        for urgency in urgency_levels:
            request = ServiceRequest(
                seeker_id=1,
                title=f"Test Request - {urgency.value}",
                description="Test description",
                location_latitude=Decimal("40.7128"),
                location_longitude=Decimal("-74.0060"),
                location_address="Test Address",
                urgency_level=urgency
            )
            db_session.add(request)
        
        db_session.commit()
        
        # Verify all urgency levels are supported
        requests = db_session.query(ServiceRequest).all()
        found_urgencies = {req.urgency_level for req in requests}
        assert found_urgencies == set(urgency_levels)
    
    def test_service_request_status_workflow(self, db_session):
        """
        TDD Test: ServiceRequest should follow proper status workflow.
        
        This test defines the expected status transitions.
        """
        # Arrange - Create draft request
        request = ServiceRequest(
            seeker_id=1,
            title="Test Request",
            description="Test description",
            location_latitude=Decimal("40.7128"),
            location_longitude=Decimal("-74.0060"),
            location_address="Test Address"
        )
        db_session.add(request)
        db_session.commit()
        
        # Assert initial status
        assert request.status == RequestStatus.DRAFT
        
        # Test status transitions
        request.status = RequestStatus.ACTIVE
        db_session.commit()
        assert request.status == RequestStatus.ACTIVE
        
        request.status = RequestStatus.QUOTED
        db_session.commit()
        assert request.status == RequestStatus.QUOTED
        
        request.status = RequestStatus.BOOKED
        db_session.commit()
        assert request.status == RequestStatus.BOOKED
    
    def test_service_request_project_integration(self, db_session):
        """
        TDD Test: ServiceRequest should optionally link to projects.
        
        Requirements: 11.1
        """
        # Test with project reference
        request_with_project = ServiceRequest(
            seeker_id=1,
            project_id=123,  # Reference to Project Service
            title="Project-linked Request",
            description="Part of larger project",
            location_latitude=Decimal("40.7128"),
            location_longitude=Decimal("-74.0060"),
            location_address="Project Site Address"
        )
        
        # Test without project reference
        standalone_request = ServiceRequest(
            seeker_id=1,
            project_id=None,
            title="Standalone Request", 
            description="Independent job",
            location_latitude=Decimal("40.7128"),
            location_longitude=Decimal("-74.0060"),
            location_address="Independent Site Address"
        )
        
        db_session.add_all([request_with_project, standalone_request])
        db_session.commit()
        
        assert request_with_project.project_id == 123
        assert standalone_request.project_id is None
    
    def test_service_request_images_json_field(self, db_session):
        """
        TDD Test: ServiceRequest should store images as JSON array.
        
        Requirements: 3.4
        """
        # Arrange - Define image URLs
        images = [
            "https://example.com/before1.jpg",
            "https://example.com/before2.jpg", 
            "https://example.com/blueprint.pdf"
        ]
        
        # Act - Create request with images
        request = ServiceRequest(
            seeker_id=1,
            title="Request with Images",
            description="Job with reference photos",
            location_latitude=Decimal("40.7128"),
            location_longitude=Decimal("-74.0060"),
            location_address="Test Address",
            images=images
        )
        db_session.add(request)
        db_session.commit()
        
        # Assert - Verify JSON storage
        assert request.images == images
        assert len(request.images) == 3
        assert "before1.jpg" in request.images[0]
    
    def test_service_request_requirements_json_field(self, db_session):
        """
        TDD Test: ServiceRequest should store requirements as JSON.
        
        This test defines how special requirements should be stored.
        """
        # Arrange - Define requirements
        requirements = {
            "insurance_required": True,
            "license_required": True,
            "background_check": True,
            "minimum_experience_years": 5,
            "certifications": ["OSHA 30", "Electrical License"],
            "tools_provided": False,
            "materials_included": True
        }
        
        # Act - Create request with requirements
        request = ServiceRequest(
            seeker_id=1,
            title="High-Security Job",
            description="Requires verified professionals",
            location_latitude=Decimal("40.7128"),
            location_longitude=Decimal("-74.0060"),
            location_address="Secure Facility",
            requirements=requirements
        )
        db_session.add(request)
        db_session.commit()
        
        # Assert - Verify JSON storage and access
        assert request.requirements == requirements
        assert request.requirements["insurance_required"] is True
        assert request.requirements["minimum_experience_years"] == 5
        assert "OSHA 30" in request.requirements["certifications"]


@pytest.mark.unit
@pytest.mark.tdd
class TestSkillRequirementModel:
    """TDD Test cases for SkillRequirement junction model - RED phase."""
    
    def test_create_skill_requirement_relationship(self, db_session):
        """
        TDD Test: SkillRequirement should link requests to required skills.
        
        Requirements: 3.1, 3.2
        """
        # Arrange - Create dependencies (these exist)
        skill = SkillFactory.create(name="Electrical Wiring")
        
        # This will fail until ServiceRequest model exists
        request = ServiceRequest(
            seeker_id=1,
            title="Electrical Job",
            description="Need electrical work",
            location_latitude=Decimal("40.7128"),
            location_longitude=Decimal("-74.0060"),
            location_address="Test Address"
        )
        db_session.add(request)
        db_session.commit()
        
        # Act - Create skill requirement
        skill_req = SkillRequirement(
            service_request_id=request.id,
            skill_id=skill.id,
            proficiency_level="ADVANCED",
            is_required=True,
            importance_weight=8
        )
        db_session.add(skill_req)
        db_session.commit()
        db_session.refresh(skill_req)
        
        # Assert - Verify relationship
        assert skill_req.id is not None
        assert skill_req.service_request_id == request.id
        assert skill_req.skill_id == skill.id
        assert skill_req.proficiency_level == "ADVANCED"
        assert skill_req.is_required is True
        assert skill_req.importance_weight == 8
    
    def test_skill_requirement_primary_designation(self, db_session):
        """
        TDD Test: SkillRequirement should support primary skill designation.
        """
        # Arrange - Create request and skills
        request = ServiceRequest(
            seeker_id=1,
            title="Multi-skill Job",
            description="Requires multiple skills",
            location_latitude=Decimal("40.7128"),
            location_longitude=Decimal("-74.0060"),
            location_address="Test Address"
        )
        db_session.add(request)
        db_session.commit()
        
        electrical_skill = SkillFactory.create(name="Electrical")
        plumbing_skill = SkillFactory.create(name="Plumbing")
        
        # Act - Create skill requirements
        primary_req = SkillRequirement(
            service_request_id=request.id,
            skill_id=electrical_skill.id,
            proficiency_level="EXPERT",
            is_required=True,
            importance_weight=10
        )
        
        secondary_req = SkillRequirement(
            service_request_id=request.id,
            skill_id=plumbing_skill.id,
            proficiency_level="INTERMEDIATE",
            is_required=False,
            importance_weight=5
        )
        
        db_session.add_all([primary_req, secondary_req])
        db_session.commit()
        
        # Assert - Verify primary designation
        assert primary_req.is_required is True
        assert secondary_req.is_required is False
        assert primary_req.importance_weight > secondary_req.importance_weight


@pytest.mark.unit
@pytest.mark.tdd
class TestServiceRequestBusinessLogic:
    """TDD Test cases for ServiceRequest business logic - RED phase."""
    
    def test_service_request_to_dict_method(self, db_session):
        """
        TDD Test: ServiceRequest should convert to dictionary for API responses.
        """
        # Arrange
        request = ServiceRequest(
            seeker_id=1,
            title="Test Request",
            description="Test description",
            location_latitude=Decimal("40.7128"),
            location_longitude=Decimal("-74.0060"),
            location_address="Test Address",
            budget_min=Decimal("500.00"),
            budget_max=Decimal("1000.00")
        )
        db_session.add(request)
        db_session.commit()
        
        # Act
        request_dict = request.to_dict()
        
        # Assert
        assert isinstance(request_dict, dict)
        assert request_dict["title"] == "Test Request"
        assert request_dict["seeker_id"] == 1
        assert "id" in request_dict
        assert "created_at" in request_dict
        assert "location" in request_dict
        assert "latitude" in request_dict["location"]
    
    def test_service_request_string_representation(self, db_session):
        """
        TDD Test: ServiceRequest should have meaningful string representation.
        """
        # Arrange
        request = ServiceRequest(
            seeker_id=1,
            title="Kitchen Renovation",
            description="Complete kitchen remodel",
            location_latitude=Decimal("40.7128"),
            location_longitude=Decimal("-74.0060"),
            location_address="Test Address"
        )
        db_session.add(request)
        db_session.commit()
        
        # Act
        request_str = str(request)
        
        # Assert
        assert "ServiceRequest" in request_str
        assert str(request.id) in request_str
        assert "Kitchen Renovation" in request_str
    
    def test_service_request_estimated_duration_calculation(self, db_session):
        """
        TDD Test: ServiceRequest should calculate total estimated duration.
        """
        # Arrange - Create request with skill requirements
        request = ServiceRequest(
            seeker_id=1,
            title="Multi-phase Job",
            description="Job with multiple skill requirements",
            location_latitude=Decimal("40.7128"),
            location_longitude=Decimal("-74.0060"),
            location_address="Test Address",
            estimated_duration_hours=24  # Total estimate
        )
        db_session.add(request)
        db_session.commit()
        
        # Assert - Verify duration handling
        assert request.estimated_duration_hours == 24
        
        # Test duration calculation method (if implemented)
        # This would sum up skill requirement hours
        # total_hours = request.calculate_total_estimated_hours()
        # assert total_hours >= 0
    
    def test_service_request_location_validation(self, db_session):
        """
        TDD Test: ServiceRequest should validate location data.
        """
        # Test valid coordinates
        valid_request = ServiceRequest(
            seeker_id=1,
            title="Valid Location",
            description="Request with valid coordinates",
            location_latitude=Decimal("40.7128"),  # Valid NYC latitude
            location_longitude=Decimal("-74.0060"),  # Valid NYC longitude
            location_address="123 Main St, New York, NY"
        )
        db_session.add(valid_request)
        db_session.commit()
        
        # Verify coordinates are within valid ranges
        assert -90 <= valid_request.location_latitude <= 90
        assert -180 <= valid_request.location_longitude <= 180
        assert valid_request.location_address is not None
        assert len(valid_request.location_address) > 0