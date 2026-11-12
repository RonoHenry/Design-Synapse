"""ServiceRequest repository with specialized query methods."""
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import and_, func, or_
from sqlalchemy.orm import Session, joinedload
from src.models.service_provider import Skill
from src.models.service_request import (RequestStatus, ServiceRequest,
                                        SkillRequirement, UrgencyLevel)

from .base_repository import BaseRepository


class ServiceRequestRepository(BaseRepository[ServiceRequest]):
    """Repository for ServiceRequest with specialized query methods."""

    def __init__(self, db_session: Session):
        super().__init__(ServiceRequest, db_session)

    def find_by_status(self, status: RequestStatus) -> List[ServiceRequest]:
        """Find service requests by status."""
        return (
            self.db_session.query(ServiceRequest)
            .filter(ServiceRequest.status == status)
            .all()
        )

    def find_by_urgency(self, urgency: UrgencyLevel) -> List[ServiceRequest]:
        """Find service requests by urgency level."""
        return (
            self.db_session.query(ServiceRequest)
            .filter(ServiceRequest.urgency_level == urgency)
            .all()
        )

    def find_by_budget_range(
        self, min_budget: float, max_budget: float
    ) -> List[ServiceRequest]:
        """Find service requests within budget range."""
        return (
            self.db_session.query(ServiceRequest)
            .filter(
                and_(
                    ServiceRequest.budget_min <= max_budget,
                    ServiceRequest.budget_max >= min_budget,
                )
            )
            .all()
        )

    def find_by_location(
        self, latitude: float, longitude: float, radius_km: float = 50
    ) -> List[ServiceRequest]:
        """Find service requests within geographic radius."""
        # Simple distance calculation (for production, use PostGIS or similar)
        lat_range = radius_km / 111.0  # Rough conversion km to degrees
        lng_range = radius_km / (111.0 * func.cos(func.radians(latitude)))

        return (
            self.db_session.query(ServiceRequest)
            .filter(
                and_(
                    ServiceRequest.location_latitude.between(
                        latitude - lat_range, latitude + lat_range
                    ),
                    ServiceRequest.location_longitude.between(
                        longitude - lng_range, longitude + lng_range
                    ),
                )
            )
            .all()
        )

    def find_by_skills(self, skill_ids: List[int]) -> List[ServiceRequest]:
        """Find service requests requiring specific skills."""
        return (
            self.db_session.query(ServiceRequest)
            .join(SkillRequirement)
            .filter(SkillRequirement.skill_id.in_(skill_ids))
            .distinct()
            .all()
        )

    def find_matching_requests(
        self,
        skills: List[int] = None,
        max_budget: float = None,
        location: tuple = None,
        radius_km: float = 50,
    ) -> List[ServiceRequest]:
        """Find service requests matching provider capabilities."""
        query = self.db_session.query(ServiceRequest).filter(
            ServiceRequest.status == RequestStatus.ACTIVE
        )

        if skills:
            query = query.join(SkillRequirement).filter(
                SkillRequirement.skill_id.in_(skills)
            )

        if max_budget:
            query = query.filter(ServiceRequest.budget_max <= max_budget)

        if location:
            lat, lng = location
            lat_range = radius_km / 111.0
            lng_range = radius_km / (111.0 * func.cos(func.radians(lat)))

            query = query.filter(
                and_(
                    ServiceRequest.location_latitude.between(
                        lat - lat_range, lat + lat_range
                    ),
                    ServiceRequest.location_longitude.between(
                        lng - lng_range, lng + lng_range
                    ),
                )
            )

        return query.distinct().all()

    def get_with_skills(self, request_id: int) -> Optional[ServiceRequest]:
        """Get service request with skill requirements loaded."""
        return (
            self.db_session.query(ServiceRequest)
            .options(
                joinedload(ServiceRequest.skill_requirements).joinedload(
                    SkillRequirement.skill
                )
            )
            .filter(ServiceRequest.id == request_id)
            .first()
        )

    def get_recent_requests(self, days: int = 7) -> List[ServiceRequest]:
        """Get service requests created in the last N days."""
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
        return (
            self.db_session.query(ServiceRequest)
            .filter(ServiceRequest.created_at >= cutoff_date)
            .order_by(ServiceRequest.created_at.desc())
            .all()
        )

    def get_urgent_requests(self) -> List[ServiceRequest]:
        """Get urgent service requests that are still open."""
        return (
            self.db_session.query(ServiceRequest)
            .filter(
                and_(
                    ServiceRequest.status == RequestStatus.ACTIVE,
                    ServiceRequest.urgency_level == UrgencyLevel.EMERGENCY,
                )
            )
            .order_by(ServiceRequest.created_at.asc())
            .all()
        )

    def get_by_seeker_id(self, seeker_id: int) -> List[ServiceRequest]:
        """Get service requests by seeker ID."""
        return (
            self.db_session.query(ServiceRequest)
            .filter(ServiceRequest.seeker_id == seeker_id)
            .order_by(ServiceRequest.created_at.desc())
            .all()
        )

    def search_by_location(
        self, latitude: float, longitude: float, radius_km: float = 50
    ) -> List[ServiceRequest]:
        """Search requests by location (alias for find_by_location for service compatibility)."""
        return self.find_by_location(latitude, longitude, radius_km)

    def search_by_skills(self, skill_ids: List[int]) -> List[ServiceRequest]:
        """Search requests by skills (alias for find_by_skills for service compatibility)."""
        return self.find_by_skills(skill_ids)

    def get_all_active(self) -> List[ServiceRequest]:
        """Get all active service requests"""
        return (
            self.db_session.query(ServiceRequest)
            .filter(ServiceRequest.status == RequestStatus.ACTIVE)
            .order_by(ServiceRequest.created_at.desc())
            .all()
        )

    def get_analytics(self, request_id: int) -> Dict[str, Any]:
        """Get analytics for a specific request"""
        request = self.get_by_id(request_id)
        if not request:
            return {}

        # Basic analytics - in production this would be more comprehensive
        return {
            "views": 0,  # Would track actual views
            "quotes_received": 0,  # Would count related quotes
            "avg_quote_amount": 0.0,  # Would calculate from quotes
            "time_to_first_quote": None,  # Would calculate from timestamps
            "completion_rate": 0.0,  # Would calculate based on status history
        }
