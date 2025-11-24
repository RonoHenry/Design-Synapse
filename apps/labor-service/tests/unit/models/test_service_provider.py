"""
TDD Tests for ServiceProvider Model

Following Test-Driven Development principles:
1. Write failing tests first
2. Implement minimal code to make tests pass
3. Refactor while keeping tests green

These tests define the expected behavior of the ServiceProvider model
and related models before implementation.
"""

import pytest
from decimal import Decimal
from datetime import datetime
from sqlalchemy.exc import IntegrityError

from src.models.service_provider import (
    ServiceProvider, SkillCategory, Skill, ProviderSkill, ServiceArea,
    ProviderType, VerificationStatus, ProficiencyLevel
)
from tests.factories import (
    ServiceProviderFactory,
    SkillCategoryFactory, SkillFactory,
    ProviderSkillFactory, ServiceAreaFactory
)


@pytest.mark.unit
@pytest.mark.tdd
class TestServiceProviderModel:
    """Test cases for ServiceProvider model following TDD principles."""
    
    def test_create_service_provider_with_required_fields(self, db_session):
        """
        TDD Test: ServiceProvider should be created with minimal required fields.
        
        This test defines the minimum requirements for creating a ServiceProvider.
        """
        # Arrange - Define what we expect to work
        provider_data = {
            "user_id": 1,
            "individual_name": "John Smith",
            "provider_type": ProviderType.INDIVIDUAL
        }
        
        # Act - Create the provider
        provider = ServiceProvider(**provider_data)
        db_session.add(provider)
        db_session.commit()
        db_session.refresh(provider)
        
        # Assert - Verify the provider was created correctly
        assert provider.id is not None
        assert provider.user_id == 1
        assert provider.individual_name == "John Smith"
        assert provider.provider_type == ProviderType.INDIVIDUAL
        assert provider.verification_status == VerificationStatus.PENDING
        assert provider.rating == Decimal("0.00")
        assert provider.total_reviews == 0
        assert provider.total_jobs_completed == 0
        assert provider.is_active is True
        assert provider.is_available is True
        assert provider.created_at is not None
        assert provider.updated_at is not None
    
    def test_service_provider_user_id_must_be_unique(self, db_session):
        """
        TDD Test: Each user can only have one service provider profile.
        
        This test ensures business rule: one user = one provider profile.
        """
        # Arrange - Create first provider
        provider1 = ServiceProviderFactory.create(user_id=1)
        
        # Act & Assert - Attempt to create second provider with same user_id should fail
        with pytest.raises(IntegrityError):
            provider2 = ServiceProviderFactory.create(user_id=1)
            db_session.commit()
    
    def test_service_provider_verification_workflow(self, db_session):
        """
        TDD Test: ServiceProvider verification status workflow.
        
        This test defines the expected verification state transitions.
        """
        # Arrange - Create pending provider
        provider = ServiceProviderFactory.create(
            verification_status=VerificationStatus.PENDING
        )
        
        # Act - Verify the provider
        provider.verification_status = VerificationStatus.VERIFIED
        provider.verification_date = datetime.now()
        db_session.commit()
        
        # Assert - Verify status changed correctly
        assert provider.verification_status == VerificationStatus.VERIFIED
        assert provider.verification_date is not None
    
    def test_service_provider_rating_calculation(self, db_session):
        """
        TDD Test: ServiceProvider rating should be calculated correctly.
        
        This test defines how ratings should be handled and validated.
        """
        # Arrange - Create provider with rating data
        provider = ServiceProviderFactory.create(
            rating=Decimal("4.25"),
            total_reviews=20
        )
        
        # Assert - Verify rating constraints
        assert provider.rating >= Decimal("0.00")
        assert provider.rating <= Decimal("5.00")
        assert provider.total_reviews >= 0
    
    def test_service_provider_business_vs_individual_types(self, db_session):
        """
        TDD Test: ServiceProvider should handle business vs individual types.
        
        This test defines the difference between business and individual providers.
        """
        # Arrange & Act - Create individual provider
        individual = ServiceProviderFactory.create(
            provider_type=ProviderType.INDIVIDUAL,
            business_name=None,
            individual_name="John Smith"
        )
        
        # Arrange & Act - Create business provider
        business = ServiceProviderFactory.create(
            provider_type=ProviderType.BUSINESS,
            business_name="Smith Construction LLC",
            individual_name="John Smith"  # Contact person
        )
        
        # Assert - Verify type-specific behavior
        assert individual.provider_type == ProviderType.INDIVIDUAL
        assert individual.business_name is None
        assert individual.individual_name == "John Smith"
        
        assert business.provider_type == ProviderType.BUSINESS
        assert business.business_name == "Smith Construction LLC"
        assert business.individual_name == "John Smith"  # Contact person
    
    def test_service_provider_insurance_info_json_field(self, db_session):
        """
        TDD Test: ServiceProvider should store insurance info as JSON.
        
        This test defines the expected structure for insurance information.
        """
        # Arrange - Define insurance info structure
        insurance_data = {
            "provider": "State Farm",
            "policy_number": "SF123456789",
            "coverage_amount": 2000000,
            "liability_coverage": 1000000,
            "expiry_date": "2024-12-31",
            "is_bonded": True
        }
        
        # Act - Create provider with insurance info
        provider = ServiceProviderFactory.create(insurance_info=insurance_data)
        
        # Assert - Verify JSON storage and retrieval
        assert provider.insurance_info == insurance_data
        assert provider.insurance_info["provider"] == "State Farm"
        assert provider.insurance_info["coverage_amount"] == 2000000
    
    def test_service_provider_portfolio_images_json_array(self, db_session):
        """
        TDD Test: ServiceProvider should store portfolio images as JSON array.
        
        This test defines how portfolio images should be stored and accessed.
        """
        # Arrange - Define portfolio images
        portfolio_images = [
            "https://example.com/project1.jpg",
            "https://example.com/project2.jpg",
            "https://example.com/project3.jpg"
        ]
        
        # Act - Create provider with portfolio
        provider = ServiceProviderFactory.create(portfolio_images=portfolio_images)
        
        # Assert - Verify JSON array storage
        assert provider.portfolio_images == portfolio_images
        assert len(provider.portfolio_images) == 3
        assert "project1.jpg" in provider.portfolio_images[0]


@pytest.mark.unit
@pytest.mark.tdd
class TestSkillCategoryModel:
    """Test cases for SkillCategory model following TDD principles."""
    
    def test_create_skill_category_with_required_fields(self, db_session):
        """
        TDD Test: SkillCategory should be created with required fields.
        """
        # Arrange
        category_data = {
            "name": "Construction",
            "description": "General construction and building skills"
        }
        
        # Act
        category = SkillCategory(**category_data)
        db_session.add(category)
        db_session.commit()
        db_session.refresh(category)
        
        # Assert
        assert category.id is not None
        assert category.name == "Construction"
        assert category.description == "General construction and building skills"
        assert category.sort_order == 0  # Default value
        assert category.is_active is True  # Default value
        assert category.created_at is not None
    
    def test_skill_category_name_must_be_unique(self, db_session):
        """
        TDD Test: SkillCategory names must be unique.
        """
        # Arrange - Create first category
        category1 = SkillCategoryFactory.create(name="Construction")
        
        # Act & Assert - Duplicate name should fail
        with pytest.raises(IntegrityError):
            category2 = SkillCategoryFactory.create(name="Construction")
            db_session.commit()
    
    def test_skill_category_sort_order_for_display(self, db_session):
        """
        TDD Test: SkillCategory should support sort ordering.
        """
        # Arrange & Act - Create categories with different sort orders
        category1 = SkillCategoryFactory.create(name="Electrical", sort_order=2)
        category2 = SkillCategoryFactory.create(name="Plumbing", sort_order=1)
        category3 = SkillCategoryFactory.create(name="Construction", sort_order=3)
        
        # Assert - Verify sort order is stored correctly
        assert category2.sort_order < category1.sort_order < category3.sort_order


@pytest.mark.unit
@pytest.mark.tdd
class TestSkillModel:
    """Test cases for Skill model following TDD principles."""
    
    def test_create_skill_with_category_relationship(self, db_session):
        """
        TDD Test: Skill should be created with category relationship.
        """
        # Arrange - Create category first
        category = SkillCategoryFactory.create(name="Construction")
        
        skill_data = {
            "category_id": category.id,
            "name": "Carpentry",
            "description": "Wood working and framing skills"
        }
        
        # Act
        skill = Skill(**skill_data)
        db_session.add(skill)
        db_session.commit()
        db_session.refresh(skill)
        
        # Assert
        assert skill.id is not None
        assert skill.category_id == category.id
        assert skill.name == "Carpentry"
        assert skill.requires_certification is False  # Default
        assert skill.is_active is True  # Default
        assert skill.category.name == "Construction"  # Relationship works
    
    def test_skill_certification_requirement_flag(self, db_session):
        """
        TDD Test: Skill should track certification requirements.
        """
        # Arrange & Act - Create skills with different certification requirements
        electrical_skill = SkillFactory.create(
            name="Electrical Wiring",
            requires_certification=True
        )
        
        carpentry_skill = SkillFactory.create(
            name="Basic Carpentry",
            requires_certification=False
        )
        
        # Assert
        assert electrical_skill.requires_certification is True
        assert carpentry_skill.requires_certification is False


@pytest.mark.unit
@pytest.mark.tdd
class TestProviderSkillModel:
    """Test cases for ProviderSkill junction model following TDD principles."""
    
    def test_create_provider_skill_relationship(self, db_session):
        """
        TDD Test: ProviderSkill should link providers to skills with proficiency.
        """
        # Arrange
        provider = ServiceProviderFactory.create()
        skill = SkillFactory.create(name="Carpentry")
        
        provider_skill_data = {
            "provider_id": provider.id,
            "skill_id": skill.id,
            "proficiency_level": ProficiencyLevel.ADVANCED,
            "years_experience": 8,
            "hourly_rate": Decimal("75.00")
        }
        
        # Act
        provider_skill = ProviderSkill(**provider_skill_data)
        db_session.add(provider_skill)
        db_session.commit()
        db_session.refresh(provider_skill)
        
        # Assert
        assert provider_skill.id is not None
        assert provider_skill.provider_id == provider.id
        assert provider_skill.skill_id == skill.id
        assert provider_skill.proficiency_level == ProficiencyLevel.ADVANCED
        assert provider_skill.years_experience == 8
        assert provider_skill.hourly_rate == Decimal("75.00")
        assert provider_skill.is_primary is False  # Default
    
    def test_provider_skill_unique_constraint(self, db_session):
        """
        TDD Test: Provider can't have duplicate skills.
        """
        # Arrange
        provider = ServiceProviderFactory.create()
        skill = SkillFactory.create()
        
        # Create first provider-skill relationship
        ProviderSkillFactory.create(provider=provider, skill=skill)
        
        # Act & Assert - Duplicate should fail
        with pytest.raises(IntegrityError):
            ProviderSkillFactory.create(provider=provider, skill=skill)
            db_session.commit()
    
    def test_provider_skill_certifications_json_field(self, db_session):
        """
        TDD Test: ProviderSkill should store certifications as JSON.
        """
        # Arrange
        certifications = [
            {
                "name": "OSHA 30-Hour Construction",
                "issuer": "OSHA",
                "issue_date": "2023-01-15",
                "expiry_date": "2026-01-15",
                "certificate_number": "OSHA123456"
            },
            {
                "name": "Certified Carpenter",
                "issuer": "National Association of Home Builders",
                "issue_date": "2022-06-01",
                "expiry_date": None,  # No expiry
                "certificate_number": "NAHB789012"
            }
        ]
        
        # Act
        provider_skill = ProviderSkillFactory.create(certifications=certifications)
        
        # Assert
        assert provider_skill.certifications == certifications
        assert len(provider_skill.certifications) == 2
        assert provider_skill.certifications[0]["name"] == "OSHA 30-Hour Construction"
    
    def test_provider_skill_primary_skill_designation(self, db_session):
        """
        TDD Test: ProviderSkill should support primary skill designation.
        """
        # Arrange
        provider = ServiceProviderFactory.create()
        
        # Act - Create skills with one marked as primary
        primary_skill = ProviderSkillFactory.create(
            provider=provider,
            is_primary=True,
            proficiency_level=ProficiencyLevel.EXPERT
        )
        
        secondary_skill = ProviderSkillFactory.create(
            provider=provider,
            is_primary=False,
            proficiency_level=ProficiencyLevel.INTERMEDIATE
        )
        
        # Assert
        assert primary_skill.is_primary is True
        assert secondary_skill.is_primary is False


@pytest.mark.unit
@pytest.mark.tdd
class TestServiceAreaModel:
    """Test cases for ServiceArea model following TDD principles."""
    
    def test_create_service_area_with_geographic_data(self, db_session):
        """
        TDD Test: ServiceArea should store geographic coverage data.
        """
        # Arrange
        provider = ServiceProviderFactory.create()
        
        service_area_data = {
            "provider_id": provider.id,
            "center_latitude": Decimal("40.7128"),  # NYC coordinates
            "center_longitude": Decimal("-74.0060"),
            "radius_miles": 25,
            "travel_rate": Decimal("0.75"),
            "area_name": "New York Metro Area"
        }
        
        # Act
        service_area = ServiceArea(**service_area_data)
        db_session.add(service_area)
        db_session.commit()
        db_session.refresh(service_area)
        
        # Assert
        assert service_area.id is not None
        assert service_area.provider_id == provider.id
        assert service_area.center_latitude == Decimal("40.7128")
        assert service_area.center_longitude == Decimal("-74.0060")
        assert service_area.radius_miles == 25
        assert service_area.travel_rate == Decimal("0.75")
        assert service_area.area_name == "New York Metro Area"
        assert service_area.is_primary is False  # Default
        assert service_area.is_active is True  # Default
    
    def test_service_area_primary_designation(self, db_session):
        """
        TDD Test: ServiceArea should support primary area designation.
        """
        # Arrange
        provider = ServiceProviderFactory.create()
        
        # Act - Create multiple service areas
        primary_area = ServiceAreaFactory.create(
            provider=provider,
            area_name="Primary Service Area",
            is_primary=True
        )
        
        secondary_area = ServiceAreaFactory.create(
            provider=provider,
            area_name="Secondary Service Area",
            is_primary=False
        )
        
        # Assert
        assert primary_area.is_primary is True
        assert secondary_area.is_primary is False
    
    def test_service_area_travel_rate_calculation(self, db_session):
        """
        TDD Test: ServiceArea should store travel rates for distance pricing.
        """
        # Arrange & Act
        service_area = ServiceAreaFactory.create(
            radius_miles=50,
            travel_rate=Decimal("1.25")  # $1.25 per mile
        )
        
        # Assert - Verify travel rate is stored correctly
        assert service_area.travel_rate == Decimal("1.25")
        assert service_area.radius_miles == 50


@pytest.mark.unit
@pytest.mark.tdd
class TestServiceProviderRelationships:
    """Test cases for ServiceProvider model relationships following TDD principles."""
    
    def test_service_provider_skills_relationship(self, db_session):
        """
        TDD Test: ServiceProvider should have many skills through ProviderSkill.
        """
        # Arrange
        provider = ServiceProviderFactory.create()
        skill1 = SkillFactory.create(name="Carpentry")
        skill2 = SkillFactory.create(name="Plumbing")
        
        # Act - Add skills to provider
        ProviderSkillFactory.create(provider=provider, skill=skill1)
        ProviderSkillFactory.create(provider=provider, skill=skill2)
        
        # Assert - Verify relationship works
        assert len(provider.skills) == 2
        skill_names = [ps.skill.name for ps in provider.skills]
        assert "Carpentry" in skill_names
        assert "Plumbing" in skill_names
    
    def test_service_provider_service_areas_relationship(self, db_session):
        """
        TDD Test: ServiceProvider should have many service areas.
        """
        # Arrange
        provider = ServiceProviderFactory.create()
        
        # Act - Add service areas
        area1 = ServiceAreaFactory.create(provider=provider, area_name="NYC")
        area2 = ServiceAreaFactory.create(provider=provider, area_name="Brooklyn")
        
        # Assert - Verify relationship works
        assert len(provider.service_areas) == 2
        area_names = [area.area_name for area in provider.service_areas]
        assert "NYC" in area_names
        assert "Brooklyn" in area_names
    
    def test_skill_category_skills_relationship(self, db_session):
        """
        TDD Test: SkillCategory should have many skills.
        """
        # Arrange
        category = SkillCategoryFactory.create(name="Construction")
        
        # Act - Add skills to category
        skill1 = SkillFactory.create(category=category, name="Carpentry")
        skill2 = SkillFactory.create(category=category, name="Framing")
        
        # Assert - Verify relationship works
        assert len(category.skills) == 2
        skill_names = [skill.name for skill in category.skills]
        assert "Carpentry" in skill_names
        assert "Framing" in skill_names


@pytest.mark.unit
@pytest.mark.tdd
class TestServiceProviderBusinessLogic:
    """Test cases for ServiceProvider business logic following TDD principles."""
    
    def test_service_provider_to_dict_method(self, db_session):
        """
        TDD Test: ServiceProvider should convert to dictionary for API responses.
        """
        # Arrange
        provider = ServiceProviderFactory.create(
            individual_name="John Smith",
            business_name="Smith Construction",
            experience_years=10
        )
        
        # Act
        provider_dict = provider.to_dict()
        
        # Assert
        assert isinstance(provider_dict, dict)
        assert provider_dict["individual_name"] == "John Smith"
        assert provider_dict["business_name"] == "Smith Construction"
        assert provider_dict["experience_years"] == 10
        assert "id" in provider_dict
        assert "created_at" in provider_dict
    
    def test_service_provider_string_representation(self, db_session):
        """
        TDD Test: ServiceProvider should have meaningful string representation.
        """
        # Arrange
        provider = ServiceProviderFactory.create(individual_name="John Smith")
        
        # Act
        provider_str = str(provider)
        
        # Assert
        assert "ServiceProvider" in provider_str
        assert str(provider.id) in provider_str
        assert "John Smith" in provider_str
    
    def test_service_provider_verification_business_rules(self, db_session):
        """
        TDD Test: ServiceProvider verification should follow business rules.
        
        This test defines the expected behavior for provider verification.
        """
        # Arrange - Create unverified provider
        provider = ServiceProviderFactory.create(
            verification_status=VerificationStatus.PENDING,
            verification_date=None
        )
        
        # Act - Simulate verification process
        provider.verification_status = VerificationStatus.VERIFIED
        provider.verification_date = datetime.now()
        db_session.commit()
        
        # Assert - Verify business rules
        assert provider.verification_status == VerificationStatus.VERIFIED
        assert provider.verification_date is not None
        assert provider.verification_date <= datetime.now()
    
    def test_service_provider_rating_constraints(self, db_session):
        """
        TDD Test: ServiceProvider rating should have proper constraints.
        """
        # Arrange & Act - Create provider with valid rating
        provider = ServiceProviderFactory.create(
            rating=Decimal("4.75"),
            total_reviews=100
        )
        
        # Assert - Verify rating constraints
        assert Decimal("0.00") <= provider.rating <= Decimal("5.00")
        assert provider.total_reviews >= 0
        
        # Test rating precision
        assert provider.rating == Decimal("4.75")  # Exact decimal match