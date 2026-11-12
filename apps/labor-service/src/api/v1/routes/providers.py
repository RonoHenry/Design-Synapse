"""Provider API routes."""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from src.api.dependencies import get_db, get_provider_service, require_auth
from src.api.v1.schemas.base import PaginatedResponse
from src.api.v1.schemas.provider import (ProviderAnalyticsResponse,
                                         ProviderAvailabilityRequest,
                                         ProviderCreateRequest,
                                         ProviderResponse,
                                         ProviderSearchParams,
                                         ProviderSkillRequest,
                                         ProviderUpdateRequest)
from src.core.exceptions import ProviderNotFoundError, ValidationError
from src.services.provider_service import ProviderService

router = APIRouter(prefix="/providers", tags=["providers"])


@router.post("", response_model=ProviderResponse, status_code=status.HTTP_201_CREATED)
async def create_provider(
    provider_data: ProviderCreateRequest,
    provider_service: ProviderService = Depends(get_provider_service),
    current_user=Depends(require_auth),
):
    """Create a new service provider."""
    try:
        # Convert Pydantic model to dict for service layer
        provider_dict = provider_data.model_dump()

        provider = await provider_service.register_provider(provider_dict)
        return ProviderResponse.model_validate(provider)
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e)
        )
    except Exception as e:
        import traceback

        print(f"Error creating provider: {str(e)}")
        print(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create provider: {str(e)}",
        )


@router.get("/{provider_id}", response_model=ProviderResponse)
async def get_provider(
    provider_id: int, provider_service: ProviderService = Depends(get_provider_service)
):
    """Get provider by ID."""
    try:
        provider = await provider_service.get_provider(provider_id)
        return ProviderResponse.model_validate(provider)
    except ProviderNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Provider not found"
        )


@router.put("/{provider_id}", response_model=ProviderResponse)
async def update_provider(
    provider_id: int,
    update_data: ProviderUpdateRequest,
    provider_service: ProviderService = Depends(get_provider_service),
    current_user=Depends(require_auth),
):
    """Update provider information."""
    try:
        provider = await provider_service.update_provider(
            provider_id, update_data.model_dump(exclude_unset=True)
        )
        return ProviderResponse.model_validate(provider)
    except ProviderNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Provider not found"
        )
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e)
        )


@router.get("", response_model=PaginatedResponse)
async def list_providers(
    skills: Optional[str] = Query(None, description="Comma-separated skills"),
    location: Optional[str] = Query(None, description="Location search"),
    radius: Optional[float] = Query(
        None, ge=0, le=500, description="Search radius in miles"
    ),
    min_rating: Optional[float] = Query(None, ge=0, le=5, description="Minimum rating"),
    available: Optional[bool] = Query(None, description="Filter by availability"),
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(10, ge=1, le=100, description="Page size"),
    provider_service: ProviderService = Depends(get_provider_service),
):
    """List providers with optional filters."""
    try:
        # Parse skills if provided
        skill_list = skills.split(",") if skills else None

        # TODO: Implement actual filtering logic in service
        # For now, return mock paginated response
        providers = []  # await provider_service.search_providers(...)

        return PaginatedResponse(
            items=providers, total=0, page=page, size=size, pages=0
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list providers",
        )


@router.post("/{provider_id}/skills", status_code=status.HTTP_201_CREATED)
async def add_provider_skill(
    provider_id: int,
    skill_data: ProviderSkillRequest,
    provider_service: ProviderService = Depends(get_provider_service),
    current_user=Depends(require_auth),
):
    """Add skill to provider."""
    try:
        provider_skill = await provider_service.add_provider_skill(
            provider_id=provider_id,
            skill_id=skill_data.skill_id,
            proficiency_level=skill_data.proficiency_level,
            years_experience=skill_data.years_experience,
            certifications=skill_data.certifications,
        )
        return {
            "id": provider_skill.id,
            "provider_id": provider_skill.provider_id,
            "skill_id": provider_skill.skill_id,
            "proficiency_level": provider_skill.proficiency_level.value,
            "years_experience": provider_skill.years_experience,
            "certifications": provider_skill.certifications,
            "created_at": provider_skill.created_at.isoformat(),
        }
    except ProviderNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Provider not found"
        )


@router.put("/{provider_id}/availability", response_model=dict)
async def update_provider_availability(
    provider_id: int,
    availability_data: ProviderAvailabilityRequest,
    provider_service: ProviderService = Depends(get_provider_service),
    current_user=Depends(require_auth),
):
    """Update provider availability."""
    try:
        await provider_service.update_availability(
            provider_id=provider_id,
            available=availability_data.available,
            available_from=availability_data.available_from,
            available_until=availability_data.available_until,
        )
        return {"available": availability_data.available}
    except ProviderNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Provider not found"
        )


@router.get("/{provider_id}/analytics", response_model=ProviderAnalyticsResponse)
async def get_provider_analytics(
    provider_id: int,
    provider_service: ProviderService = Depends(get_provider_service),
    current_user=Depends(require_auth),
):
    """Get provider analytics."""
    try:
        analytics = await provider_service.get_provider_analytics(provider_id)
        return ProviderAnalyticsResponse(**analytics)
    except ProviderNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Provider not found"
        )


@router.get("/search", response_model=dict)
async def search_providers(
    q: Optional[str] = Query(None, description="Search query"),
    location: Optional[str] = Query(
        None, description="Location coordinates or address"
    ),
    radius: Optional[float] = Query(10, ge=0, le=500, description="Search radius"),
    provider_service: ProviderService = Depends(get_provider_service),
):
    """Search providers with advanced filters."""
    try:
        # TODO: Implement actual search logic
        return {"results": [], "total": 0}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Search failed"
        )
