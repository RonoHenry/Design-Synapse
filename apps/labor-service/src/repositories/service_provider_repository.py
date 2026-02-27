"""ServiceProvider repository with specialized query methods."""
from decimal import Decimal
from typing import Any, Dict, List, Optional

from sqlalchemy import and_, desc, func, or_
from sqlalchemy.orm import Session, joinedload
from src.models.service_provider import (ProficiencyLevel, ProviderSkill,
                                         ProviderType, ServiceArea,
                                         ServiceProvider, Skill, SkillCategory,
                                         VerificationStatus)

from .base_repository import BaseRepository


class ServiceProviderRepository(BaseRepository[ServiceProvider]):
    """Repository for ServiceProvider with specialized query methods."""

    def __init__(self, db_session: Session):
        super().__init__(ServiceProvider, db_session)

    async def get_by_user_id(self, user_id: int) -> Optional[ServiceProvider]:
        """Get service provider by user ID."""
        return (
            self.db_session.query(ServiceProvider)
            .filter(ServiceProvider.user_id == user_id)
            .first()
        )

    def find_by_verification_status(
        self, status: VerificationStatus
    ) -> List[ServiceProvider]:
        """Find service providers by verification status."""
        return (
            self.db_session.query(ServiceProvider)
            .filter(ServiceProvider.verification_status == status)
            .all()
        )

    def find_by_provider_type(
        self, provider_type: ProviderType
    ) -> List[ServiceProvider]:
        """Find service providers by type (individual vs business)."""
        return (
            self.db_session.query(ServiceProvider)
            .filter(ServiceProvider.provider_type == provider_type)
            .all()
        )

    def find_by_skills(
        self, skill_ids: List[int], min_proficiency: ProficiencyLevel = None
    ) -> List[ServiceProvider]:
        """Find service providers with specific skills."""
        query = (
            self.db_session.query(ServiceProvider)
            .join(ProviderSkill)
            .filter(ProviderSkill.skill_id.in_(skill_ids))
        )

        if min_proficiency:
            # Define proficiency order for comparison
            proficiency_order = {
                ProficiencyLevel.BEGINNER: 1,
                ProficiencyLevel.INTERMEDIATE: 2,
                ProficiencyLevel.ADVANCED: 3,
                ProficiencyLevel.EXPERT: 4,
            }
            min_level = proficiency_order[min_proficiency]

            # Filter by proficiency level (this is a simplified approach)
            query = query.filter(
                ProviderSkill.proficiency_level.in_(
                    [
                        level
                        for level, order in proficiency_order.items()
                        if order >= min_level
                    ]
                )
            )

        return query.distinct().all()

    def find_by_location(
        self, latitude: float, longitude: float, radius_miles: float = 25
    ) -> List[ServiceProvider]:
        """Find service providers within geographic radius."""
        # Simple distance calculation using service areas
        lat_range = radius_miles / 69.0  # Rough conversion miles to degrees
        lng_range = radius_miles / (69.0 * func.cos(func.radians(latitude)))

        return (
            self.db_session.query(ServiceProvider)
            .join(ServiceArea)
            .filter(
                and_(
                    ServiceArea.center_latitude.between(
                        latitude - lat_range, latitude + lat_range
                    ),
                    ServiceArea.center_longitude.between(
                        longitude - lng_range, longitude + lng_range
                    ),
                    ServiceArea.is_active == True,
                )
            )
            .distinct()
            .all()
        )

    def find_by_rating_range(
        self, min_rating: float, max_rating: float = 5.0
    ) -> List[ServiceProvider]:
        """Find service providers within rating range."""
        return (
            self.db_session.query(ServiceProvider)
            .filter(
                and_(
                    ServiceProvider.rating >= min_rating,
                    ServiceProvider.rating <= max_rating,
                )
            )
            .all()
        )

    def find_available_providers(self) -> List[ServiceProvider]:
        """Find active and available service providers."""
        return (
            self.db_session.query(ServiceProvider)
            .filter(
                and_(
                    ServiceProvider.is_active == True,
                    ServiceProvider.is_available == True,
                    ServiceProvider.verification_status == VerificationStatus.VERIFIED,
                )
            )
            .all()
        )

    def find_top_rated_providers(self, limit: int = 10) -> List[ServiceProvider]:
        """Find top-rated service providers."""
        return (
            self.db_session.query(ServiceProvider)
            .filter(
                and_(
                    ServiceProvider.is_active == True, ServiceProvider.total_reviews > 0
                )
            )
            .order_by(desc(ServiceProvider.rating))
            .limit(limit)
            .all()
        )

    def find_matching_providers(
        self,
        skills: List[int] = None,
        location: tuple = None,
        radius_miles: float = 25,
        min_rating: float = None,
        max_hourly_rate: float = None,
    ) -> List[ServiceProvider]:
        """Find service providers matching specific criteria."""
        query = self.db_session.query(ServiceProvider).filter(
            and_(
                ServiceProvider.is_active == True,
                ServiceProvider.is_available == True,
                ServiceProvider.verification_status == VerificationStatus.VERIFIED,
            )
        )

        # Track if we've already joined ProviderSkill to avoid duplicate joins
        provider_skill_joined = False

        if skills:
            query = query.join(ProviderSkill).filter(ProviderSkill.skill_id.in_(skills))
            provider_skill_joined = True

        if location:
            lat, lng = location
            lat_range = radius_miles / 69.0
            lng_range = radius_miles / (69.0 * func.cos(func.radians(lat)))

            query = query.join(ServiceArea).filter(
                and_(
                    ServiceArea.center_latitude.between(
                        lat - lat_range, lat + lat_range
                    ),
                    ServiceArea.center_longitude.between(
                        lng - lng_range, lng + lng_range
                    ),
                    ServiceArea.is_active == True,
                )
            )

        if min_rating:
            query = query.filter(ServiceProvider.rating >= min_rating)

        if max_hourly_rate:
            if not provider_skill_joined:
                query = query.join(ProviderSkill)
            query = query.filter(ProviderSkill.hourly_rate <= max_hourly_rate)

        return query.distinct().all()

    def get_with_skills_and_areas(self, provider_id: int) -> Optional[ServiceProvider]:
        """Get service provider with skills and service areas loaded."""
        return (
            self.db_session.query(ServiceProvider)
            .options(
                joinedload(ServiceProvider.skills).joinedload(ProviderSkill.skill),
                joinedload(ServiceProvider.service_areas),
            )
            .filter(ServiceProvider.id == provider_id)
            .first()
        )

    async def get_provider_statistics(self, provider_id: int) -> Dict[str, Any]:
        """Get comprehensive statistics for a provider."""
        provider = await self.get_by_id(provider_id)
        if not provider:
            return {}

        # Get skill count
        skill_count = (
            self.db_session.query(ProviderSkill)
            .filter(ProviderSkill.provider_id == provider_id)
            .count()
        )

        # Get service area count
        area_count = (
            self.db_session.query(ServiceArea)
            .filter(
                and_(
                    ServiceArea.provider_id == provider_id,
                    ServiceArea.is_active == True,
                )
            )
            .count()
        )

        return {
            "provider_id": provider_id,
            "rating": float(provider.rating) if provider.rating else 0.0,
            "total_reviews": provider.total_reviews,
            "total_jobs_completed": provider.total_jobs_completed,
            "response_time_avg": provider.response_time_avg,
            "skill_count": skill_count,
            "service_area_count": area_count,
            "verification_status": provider.verification_status.value.upper(),
            "is_available": provider.is_available,
            "experience_years": provider.experience_years,
        }

    def search_providers(self, search_term: str) -> List[ServiceProvider]:
        """Search providers by business name, individual name, or description."""
        search_pattern = f"%{search_term}%"
        return (
            self.db_session.query(ServiceProvider)
            .filter(
                or_(
                    ServiceProvider.business_name.ilike(search_pattern),
                    ServiceProvider.individual_name.ilike(search_pattern),
                    ServiceProvider.description.ilike(search_pattern),
                )
            )
            .filter(ServiceProvider.is_active == True)
            .all()
        )

    def get_multiple_by_ids(self, provider_ids: List[int]) -> List[ServiceProvider]:
        """Get multiple service providers by their IDs."""
        return (
            self.db_session.query(ServiceProvider)
            .filter(ServiceProvider.id.in_(provider_ids))
            .all()
        )

    async def bulk_update_ratings(self, rating_updates: List[Dict[str, Any]]) -> None:
        """Bulk update provider ratings."""
        for update in rating_updates:
            provider = await self.get_by_id(update["provider_id"])
            if provider:
                provider.average_rating = Decimal(str(update["new_rating"]))
                provider.total_reviews = update["total_reviews"]

        self.db_session.commit()

    async def add_skill(
        self, provider_id: int, skill_data: Dict[str, Any]
    ) -> ProviderSkill:
        """Add a skill to a provider."""
        # Check if provider exists
        provider = await self.get_by_id(provider_id)
        if not provider:
            raise ValueError(f"Provider with id {provider_id} not found")

        # Create the ProviderSkill instance
        provider_skill = ProviderSkill(
            provider_id=provider_id,
            skill_id=skill_data["skill_id"],
            proficiency_level=ProficiencyLevel(skill_data["proficiency_level"]),
            years_experience=skill_data["years_experience"],
            certifications=skill_data.get("certifications", []),
        )

        self.db_session.add(provider_skill)
        self.db_session.commit()
        self.db_session.refresh(provider_skill)

        return provider_skill

    async def update_availability(
        self, provider_id: int, availability_data: Dict[str, Any]
    ) -> None:
        """Update provider availability."""
        provider = await self.get_by_id(provider_id)
        if not provider:
            raise ValueError(f"Provider with id {provider_id} not found")

        if "available" in availability_data:
            provider.is_available = availability_data["available"]
        if "available_from" in availability_data:
            provider.available_from = availability_data["available_from"]
        if "available_until" in availability_data:
            provider.available_until = availability_data["available_until"]

        self.db_session.commit()

    async def get_availability(self, provider_id: int) -> Dict[str, Any]:
        """Get provider availability."""
        provider = await self.get_by_id(provider_id)
        if not provider:
            return {}

        return {
            "available": provider.is_available,
            "available_from": provider.available_from,
            "available_until": provider.available_until,
        }

    async def add_service_area(
        self, provider_id: int, service_area_data: Dict[str, Any]
    ) -> ServiceArea:
        """Add service area to provider."""
        provider = await self.get_by_id(provider_id)
        if not provider:
            raise ValueError(f"Provider with id {provider_id} not found")

        service_area = ServiceArea(
            provider_id=provider_id,
            name=service_area_data["name"],
            center_latitude=service_area_data["center_latitude"],
            center_longitude=service_area_data["center_longitude"],
            radius_miles=service_area_data["radius_miles"],
            is_active=service_area_data.get("is_active", True),
        )

        self.db_session.add(service_area)
        self.db_session.commit()
        self.db_session.refresh(service_area)

        return service_area

    async def update_service_area(
        self, provider_id: int, area_id: int, update_data: Dict[str, Any]
    ) -> ServiceArea:
        """Update existing service area."""
        service_area = (
            self.db_session.query(ServiceArea)
            .filter(ServiceArea.id == area_id, ServiceArea.provider_id == provider_id)
            .first()
        )

        if not service_area:
            raise ValueError(
                f"Service area with id {area_id} not found for provider {provider_id}"
            )

        for key, value in update_data.items():
            if hasattr(service_area, key):
                setattr(service_area, key, value)

        self.db_session.commit()
        self.db_session.refresh(service_area)

        return service_area

    async def get_analytics(self, provider_id: int) -> Dict[str, Any]:
        """Get provider performance analytics."""
        provider = await self.get_by_id(provider_id)
        if not provider:
            return {}

        return {
            "total_jobs": provider.total_jobs_completed,
            "average_rating": float(provider.rating) if provider.rating else 0.0,
            "total_reviews": provider.total_reviews,
            "response_time": provider.response_time_avg,
            "completion_rate": 95.0,  # Mock data
            "repeat_customer_rate": 80.0,  # Mock data
        }

    async def update_verification_documents(
        self, provider_id: int, documents: Dict[str, Any]
    ) -> None:
        """Update verification documents."""
        provider = await self.get_by_id(provider_id)
        if not provider:
            raise ValueError(f"Provider with id {provider_id} not found")

        provider.verification_documents = documents
        self.db_session.commit()

    async def update_verification_status(
        self, provider_id: int, status: VerificationStatus
    ) -> None:
        """Update provider verification status."""
        provider = await self.get_by_id(provider_id)
        if not provider:
            raise ValueError(f"Provider with id {provider_id} not found")

        provider.verification_status = status
        self.db_session.commit()

    async def search_by_location(
        self, search_criteria: Dict[str, Any]
    ) -> List[ServiceProvider]:
        """Search providers by location criteria."""
        query = self.db_session.query(ServiceProvider).filter(
            ServiceProvider.is_active == True
        )

        if "location" in search_criteria:
            # Simple location search - in real implementation would use proper geo queries
            location = search_criteria["location"]
            query = query.filter(
                ServiceProvider.business_address.ilike(f"%{location}%")
            )

        if "skills" in search_criteria:
            skills = search_criteria["skills"]
            if isinstance(skills, str):
                skills = [skills]
            query = query.join(ProviderSkill).filter(ProviderSkill.skill_id.in_(skills))

        return query.distinct().all()

    async def get_recommendations(self, request_id: int) -> List[Dict[str, Any]]:
        """Get provider recommendations for a request."""
        # Mock implementation - in real system would analyze request and match providers
        providers = self.find_available_providers()[:5]  # Get top 5 available providers

        recommendations = []
        for provider in providers:
            recommendations.append(
                {
                    "provider_id": provider.id,
                    "match_score": 85.0,  # Mock score
                    "reasons": ["High rating", "Available now", "Relevant skills"],
                }
            )

        return recommendations
