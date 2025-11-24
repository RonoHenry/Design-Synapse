"""Tests for ServiceProviderRepository."""
import pytest
from decimal import Decimal

from src.models.service_provider import (
    ServiceProvider, ProviderSkill, ServiceArea, Skill, SkillCategory,
    ProviderType, VerificationStatus, ProficiencyLevel
)
from src.repositories.service_provider_repository import ServiceProviderRepository
from tests.factories import (
    ServiceProviderFactory, ProviderSkillFactory, ServiceAreaFactory,
    SkillFactory, SkillCategoryFactory
)

class TestServiceProviderRepository:
    """Test cases for ServiceProviderRepository."""
    
    def test_create_repository(self, db_session):
        """Test repository creation."""
        repo = ServiceProviderRepository(db_session)
        assert repo.model == ServiceProvider
        assert repo.db_session == db_session
    
    def test_find_by_verification_status(self, db_session):
        """Test finding service providers by verification status."""
        repo = ServiceProviderRepository(db_session)
        
        # Create test data
        verified_provider = ServiceProviderFactory.create(
            verification_status=VerificationStatus.VERIFIED,
            business_name="Verified Provider"
        )
        pending_provider = ServiceProviderFactory.create(
            verification_status=VerificationStatus.PENDING,
            business_name="Pending Provider"
        )
        db_session.commit()
        
        # Test finding by verification status
        verified_providers = repo.find_by_verification_status(VerificationStatus.VERIFIED)
        assert len(verified_providers) == 1
        assert verified_providers[0].business_name == "Verified Provider"
        
        pending_providers = repo.find_by_verification_status(VerificationStatus.PENDING)
        assert len(pending_providers) == 1
        assert pending_providers[0].business_name == "Pending Provider"
    
    def test_find_by_provider_type(self, db_session):
        """Test finding service providers by type."""
        repo = ServiceProviderRepository(db_session)
        
        # Create test data
        individual_provider = ServiceProviderFactory.create(
            provider_type=ProviderType.INDIVIDUAL,
            individual_name="John Doe"
        )
        business_provider = ServiceProviderFactory.create(
            provider_type=ProviderType.BUSINESS,
            business_name="ABC Construction"
        )
        db_session.commit()
        
        # Test finding by provider type
        individual_providers = repo.find_by_provider_type(ProviderType.INDIVIDUAL)
        assert len(individual_providers) == 1
        assert individual_providers[0].individual_name == "John Doe"
        
        business_providers = repo.find_by_provider_type(ProviderType.BUSINESS)
        assert len(business_providers) == 1
        assert business_providers[0].business_name == "ABC Construction"
    
    def test_find_by_skills(self, db_session):
        """Test finding service providers by skills."""
        repo = ServiceProviderRepository(db_session)
        
        # Create test data
        category = SkillCategoryFactory.create(name="Construction")
        plumbing_skill = SkillFactory.create(name="Plumbing", category=category)
        electrical_skill = SkillFactory.create(name="Electrical", category=category)
        
        plumber = ServiceProviderFactory.create(business_name="Plumber Co")
        electrician = ServiceProviderFactory.create(business_name="Electrician Co")
        
        # Add skills to providers
        plumber_skill = ProviderSkillFactory.create(
            provider=plumber,
            skill=plumbing_skill,
            proficiency_level=ProficiencyLevel.ADVANCED
        )
        electrician_skill = ProviderSkillFactory.create(
            provider=electrician,
            skill=electrical_skill,
            proficiency_level=ProficiencyLevel.INTERMEDIATE
        )
        db_session.commit()
        
        # Test finding by skills
        plumbing_providers = repo.find_by_skills([plumbing_skill.id])
        assert len(plumbing_providers) == 1
        assert plumbing_providers[0].business_name == "Plumber Co"
        
        electrical_providers = repo.find_by_skills([electrical_skill.id])
        assert len(electrical_providers) == 1
        assert electrical_providers[0].business_name == "Electrician Co"
        
        # Test finding by skills with proficiency filter
        advanced_providers = repo.find_by_skills([plumbing_skill.id], ProficiencyLevel.ADVANCED)
        assert len(advanced_providers) == 1
        assert advanced_providers[0].business_name == "Plumber Co"
        
        # Should not find intermediate provider when looking for advanced
        advanced_electrical = repo.find_by_skills([electrical_skill.id], ProficiencyLevel.ADVANCED)
        assert len(advanced_electrical) == 0
    
    def test_find_by_location(self, db_session):
        """Test finding service providers by geographic location."""
        repo = ServiceProviderRepository(db_session)
        
        # Create test data
        nyc_provider = ServiceProviderFactory.create(business_name="NYC Provider")
        la_provider = ServiceProviderFactory.create(business_name="LA Provider")
        
        # Add service areas
        nyc_area = ServiceAreaFactory.create(
            provider=nyc_provider,
            center_latitude=40.7128,
            center_longitude=-74.0060,
            area_name="NYC Area"
        )
        la_area = ServiceAreaFactory.create(
            provider=la_provider,
            center_latitude=34.0522,
            center_longitude=-118.2437,
            area_name="LA Area"
        )
        db_session.commit()
        
        # Test finding near NYC
        nyc_providers = repo.find_by_location(40.7128, -74.0060, 25)
        assert len(nyc_providers) == 1
        assert nyc_providers[0].business_name == "NYC Provider"
        
        # Test finding near LA
        la_providers = repo.find_by_location(34.0522, -118.2437, 25)
        assert len(la_providers) == 1
        assert la_providers[0].business_name == "LA Provider"
    
    def test_find_by_rating_range(self, db_session):
        """Test finding service providers by rating range."""
        repo = ServiceProviderRepository(db_session)
        
        # Create test data
        high_rated_provider = ServiceProviderFactory.create(
            rating=Decimal('4.8'),
            business_name="High Rated"
        )
        low_rated_provider = ServiceProviderFactory.create(
            rating=Decimal('3.2'),
            business_name="Low Rated"
        )
        db_session.commit()
        
        # Test finding high-rated providers
        high_rated = repo.find_by_rating_range(4.0, 5.0)
        assert len(high_rated) == 1
        assert high_rated[0].business_name == "High Rated"
        
        # Test finding all providers above 3.0
        all_above_3 = repo.find_by_rating_range(3.0, 5.0)
        assert len(all_above_3) == 2
    
    def test_find_available_providers(self, db_session):
        """Test finding active and available service providers."""
        repo = ServiceProviderRepository(db_session)
        
        # Create test data
        available_provider = ServiceProviderFactory.create(
            is_active=True,
            is_available=True,
            verification_status=VerificationStatus.VERIFIED,
            business_name="Available Provider"
        )
        unavailable_provider = ServiceProviderFactory.create(
            is_active=True,
            is_available=False,
            verification_status=VerificationStatus.VERIFIED,
            business_name="Unavailable Provider"
        )
        unverified_provider = ServiceProviderFactory.create(
            is_active=True,
            is_available=True,
            verification_status=VerificationStatus.PENDING,
            business_name="Unverified Provider"
        )
        db_session.commit()
        
        # Test finding available providers
        available_providers = repo.find_available_providers()
        assert len(available_providers) == 1
        assert available_providers[0].business_name == "Available Provider"
    
    def test_find_top_rated_providers(self, db_session):
        """Test finding top-rated service providers."""
        repo = ServiceProviderRepository(db_session)
        
        # Create test data
        top_provider = ServiceProviderFactory.create(
            rating=Decimal('4.9'),
            total_reviews=50,
            business_name="Top Provider"
        )
        good_provider = ServiceProviderFactory.create(
            rating=Decimal('4.2'),
            total_reviews=25,
            business_name="Good Provider"
        )
        no_reviews_provider = ServiceProviderFactory.create(
            rating=Decimal('0.0'),
            total_reviews=0,
            business_name="No Reviews"
        )
        db_session.commit()
        
        # Test finding top-rated providers
        top_providers = repo.find_top_rated_providers(5)
        assert len(top_providers) == 2  # Only providers with reviews
        assert top_providers[0].business_name == "Top Provider"  # Highest rated first
        assert top_providers[1].business_name == "Good Provider"
    
    def test_find_matching_providers(self, db_session):
        """Test finding providers matching multiple criteria."""
        repo = ServiceProviderRepository(db_session)
        
        # Create test data
        category = SkillCategoryFactory.create(name="Construction")
        plumbing_skill = SkillFactory.create(name="Plumbing", category=category)
        
        matching_provider = ServiceProviderFactory.create(
            is_active=True,
            is_available=True,
            verification_status=VerificationStatus.VERIFIED,
            rating=Decimal('4.5'),
            business_name="Matching Provider"
        )
        
        non_matching_provider = ServiceProviderFactory.create(
            is_active=False,  # Not active
            is_available=True,
            verification_status=VerificationStatus.VERIFIED,
            rating=Decimal('4.5'),
            business_name="Non-matching Provider"
        )
        
        # Add skill and service area to matching provider
        provider_skill = ProviderSkillFactory.create(
            provider=matching_provider,
            skill=plumbing_skill,
            hourly_rate=Decimal('75.00')
        )
        service_area = ServiceAreaFactory.create(
            provider=matching_provider,
            center_latitude=40.7128,
            center_longitude=-74.0060
        )
        db_session.commit()
        
        # Test matching with multiple criteria
        matches = repo.find_matching_providers(
            skills=[plumbing_skill.id],
            location=(40.7128, -74.0060),
            radius_miles=25,
            min_rating=4.0,
            max_hourly_rate=100.0
        )
        
        assert len(matches) == 1
        assert matches[0].business_name == "Matching Provider"
    
    def test_get_with_skills_and_areas(self, db_session):
        """Test getting provider with skills and areas loaded."""
        repo = ServiceProviderRepository(db_session)
        
        # Create test data
        provider = ServiceProviderFactory.create(business_name="Test Provider")
        category = SkillCategoryFactory.create(name="Construction")
        skill = SkillFactory.create(name="Plumbing", category=category)
        
        provider_skill = ProviderSkillFactory.create(provider=provider, skill=skill)
        service_area = ServiceAreaFactory.create(provider=provider)
        db_session.commit()
        
        # Test getting with relationships loaded
        loaded_provider = repo.get_with_skills_and_areas(provider.id)
        assert loaded_provider is not None
        assert loaded_provider.business_name == "Test Provider"
        # Note: In a real test, you'd verify the relationships are loaded
    
    @pytest.mark.asyncio
    async def test_get_provider_statistics(self, db_session):
        """Test getting comprehensive provider statistics."""
        repo = ServiceProviderRepository(db_session)
        
        # Create test data
        provider = ServiceProviderFactory.create(
            rating=Decimal('4.5'),
            total_reviews=25,
            total_jobs_completed=50,
            response_time_avg=30,
            experience_years=5,
            verification_status=VerificationStatus.VERIFIED,
            is_available=True
        )
        
        category = SkillCategoryFactory.create(name="Construction")
        skill = SkillFactory.create(name="Plumbing", category=category)
        provider_skill = ProviderSkillFactory.create(provider=provider, skill=skill)
        service_area = ServiceAreaFactory.create(provider=provider)
        db_session.commit()
        
        # Test getting statistics
        stats = await repo.get_provider_statistics(provider.id)
        assert stats["provider_id"] == provider.id
        assert stats["rating"] == 4.5
        assert stats["total_reviews"] == 25
        assert stats["total_jobs_completed"] == 50
        assert stats["response_time_avg"] == 30
        assert stats["skill_count"] == 1
        assert stats["service_area_count"] == 1
        assert stats["verification_status"] == "VERIFIED"
        assert stats["is_available"] == True
        assert stats["experience_years"] == 5
    
    def test_search_providers(self, db_session):
        """Test searching providers by text."""
        repo = ServiceProviderRepository(db_session)
        
        # Create test data
        provider1 = ServiceProviderFactory.create(
            business_name="ABC Plumbing Services",
            individual_name="Provider One",
            description="General services",
            is_active=True
        )
        provider2 = ServiceProviderFactory.create(
            business_name="General Services",
            individual_name="John Plumber",
            description="General contractor",
            is_active=True
        )
        provider3 = ServiceProviderFactory.create(
            business_name="Heating Services",
            individual_name="Provider Three",
            description="Expert in plumbing and heating systems",
            is_active=True
        )
        inactive_provider = ServiceProviderFactory.create(
            business_name="XYZ Plumbing",
            individual_name="Inactive Provider",
            description="Inactive services",
            is_active=False
        )
        db_session.commit()
        
        # Test searching by term
        plumbing_providers = repo.search_providers("plumbing")
        assert len(plumbing_providers) == 2  # Should not include inactive provider or non-matching terms
        
        # Test case-insensitive search
        abc_providers = repo.search_providers("abc")
        assert len(abc_providers) == 1
        assert abc_providers[0].business_name == "ABC Plumbing Services"