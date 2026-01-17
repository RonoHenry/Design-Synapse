"""
RequestService - GREEN Phase Implementation
Following TDD methodology - minimal implementation to make tests pass
"""
from typing import Dict, Any, Optional, List
from decimal import Decimal
from src.models.service_request import ServiceRequest, RequestStatus, UrgencyLevel
from src.core.exceptions import ServiceRequestNotFoundError as RequestNotFoundError, ValidationError


class RequestService:
    """Service for managing service requests - minimal TDD implementation"""
    
    def __init__(self, request_repository, skill_repository, notification_service):
        self.request_repository = request_repository
        self.skill_repository = skill_repository
        self.notification_service = notification_service
    
    async def create_request(self, request_data: Dict[str, Any]) -> ServiceRequest:
        """Create a new service request"""
        # Validate location coordinates
        lat = request_data.get("location_latitude")
        lng = request_data.get("location_longitude")
        if lat and (lat < -90 or lat > 90 or lng < -180 or lng > 180):
            raise ValidationError("Invalid location coordinates")
        
        # Validate budget range
        budget_min = request_data.get("budget_min")
        budget_max = request_data.get("budget_max")
        if budget_min and budget_max and budget_max < budget_min:
            raise ValidationError("Budget maximum must be greater than minimum")
        
        # Emergency requests go directly to active status
        if request_data.get("urgency_level") == UrgencyLevel.EMERGENCY:
            request_data["status"] = RequestStatus.ACTIVE
        
        return await self.request_repository.create(request_data)
    
    async def get_request(self, request_id: int) -> ServiceRequest:
        """Get request by ID"""
        request = await self.request_repository.get_by_id(request_id)
        if not request:
            raise RequestNotFoundError(request_id)
        return request
    
    async def update_status(self, request_id: int, status: RequestStatus) -> ServiceRequest:
        """Update request status"""
        request = await self.get_request(request_id)
        return await self.request_repository.update(request_id, {"status": status})
    
    async def publish_request(self, request_id: int) -> ServiceRequest:
        """Publish a request to make it active"""
        request = await self.get_request(request_id)
        updated_request = await self.request_repository.update(request_id, {"status": RequestStatus.ACTIVE})
        
        # Notify providers of new request
        await self.notification_service.notify_providers_of_new_request(request_id)
        
        return updated_request
    
    async def get_requests_by_seeker(self, seeker_id: int) -> List[ServiceRequest]:
        """Get all requests by seeker ID"""
        return await self.request_repository.get_by_seeker_id(seeker_id)
    
    async def search_requests_by_location(self, search_criteria: Dict[str, Any]) -> List[ServiceRequest]:
        """Search requests by location"""
        latitude = search_criteria.get("latitude")
        longitude = search_criteria.get("longitude")
        radius_km = search_criteria.get("radius_km", 50)
        
        return await self.request_repository.search_by_location(latitude, longitude, radius_km)
    
    async def search_requests_by_skills(self, skill_ids: List[int]) -> List[ServiceRequest]:
        """Search requests by required skills"""
        return await self.request_repository.search_by_skills(skill_ids)
    
    async def validate_request_completeness(self, request_id: int) -> bool:
        """Validate that request has all required information"""
        request = await self.get_request(request_id)
        
        # Check required fields
        if not request.description or not request.description.strip():
            return False
        if not request.location_latitude or not request.location_longitude:
            return False
        if not request.budget_min or not request.budget_max:
            return False
        
        return True
    
    async def cancel_request(self, request_id: int, reason: str) -> ServiceRequest:
        """Cancel an active request"""
        request = await self.get_request(request_id)
        
        # Cannot cancel completed requests
        if request.status == RequestStatus.COMPLETED:
            raise ValidationError("Cannot cancel completed request")
        
        return await self.request_repository.update(request_id, {
            "status": RequestStatus.CANCELLED,
            "cancellation_reason": reason
        })
    
    async def get_request_analytics(self, request_id: int) -> Dict[str, Any]:
        """Get request performance analytics"""
        request = await self.get_request(request_id)
        
        # Get analytics from repository
        analytics = await self.request_repository.get_analytics(request_id)
        return analytics
    
    async def update_request_status(self, request_id: int, status: RequestStatus) -> ServiceRequest:
        """Update request status (alias for update_status for test compatibility)"""
        return await self.update_status(request_id, status)