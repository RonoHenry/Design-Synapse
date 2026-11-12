"""Search API routes."""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from src.api.dependencies import get_matching_service
from src.services.matching_service import MatchingService

router = APIRouter(prefix="/search", tags=["search"])


@router.get("/providers")
async def search_providers_advanced(
    skills: Optional[str] = Query(None, description="Comma-separated list of skills"),
    location: Optional[str] = Query(None, description="Location to search near"),
    radius: Optional[float] = Query(None, description="Search radius in miles"),
    min_rating: Optional[float] = Query(None, description="Minimum provider rating"),
    max_hourly_rate: Optional[float] = Query(None, description="Maximum hourly rate"),
    available_from: Optional[str] = Query(
        None, description="Available from date (ISO format)"
    ),
    available_until: Optional[str] = Query(
        None, description="Available until date (ISO format)"
    ),
    certifications: Optional[str] = Query(None, description="Required certifications"),
    sort_by: Optional[str] = Query("rating", description="Sort field"),
    order: Optional[str] = Query("desc", description="Sort order (asc/desc)"),
    limit: int = Query(20, ge=1, le=100, description="Maximum results to return"),
    offset: int = Query(0, ge=0, description="Results offset for pagination"),
    matching_service: MatchingService = Depends(get_matching_service),
):
    """Advanced provider search with filtering and faceting."""
    try:
        search_params = {
            "skills": skills.split(",") if skills else None,
            "location": location,
            "radius": radius,
            "min_rating": min_rating,
            "max_hourly_rate": max_hourly_rate,
            "available_from": available_from,
            "available_until": available_until,
            "certifications": certifications.split(",") if certifications else None,
            "sort_by": sort_by,
            "order": order,
            "limit": limit,
            "offset": offset,
        }

        result = await matching_service.search_providers(search_params)

        return {
            "results": result.get("results", []),
            "filters_applied": {
                "skills": skills,
                "location": location,
                "radius": radius,
                "min_rating": min_rating,
                "max_hourly_rate": max_hourly_rate,
            },
            "total": result.get("total", 0),
            "facets": result.get("facets", {}),
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Provider search failed: {str(e)}",
        )


@router.get("/requests")
async def search_requests_advanced(
    category: Optional[str] = Query(None, description="Service category"),
    location: Optional[str] = Query(None, description="Location to search near"),
    radius: Optional[float] = Query(None, description="Search radius in miles"),
    budget_min: Optional[float] = Query(None, description="Minimum budget"),
    budget_max: Optional[float] = Query(None, description="Maximum budget"),
    urgency: Optional[str] = Query(None, description="Urgency level"),
    timeline_start: Optional[str] = Query(
        None, description="Timeline start date (ISO format)"
    ),
    timeline_end: Optional[str] = Query(
        None, description="Timeline end date (ISO format)"
    ),
    limit: int = Query(20, ge=1, le=100, description="Maximum results to return"),
    offset: int = Query(0, ge=0, description="Results offset for pagination"),
    matching_service: MatchingService = Depends(get_matching_service),
):
    """Advanced service request search with filtering and faceting."""
    try:
        search_params = {
            "category": category,
            "location": location,
            "radius": radius,
            "budget_min": budget_min,
            "budget_max": budget_max,
            "urgency": urgency,
            "timeline_start": timeline_start,
            "timeline_end": timeline_end,
            "limit": limit,
            "offset": offset,
        }

        result = await matching_service.search_requests(search_params)

        return {
            "results": result.get("results", []),
            "total": result.get("total", 0),
            "facets": result.get("facets", {}),
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Request search failed: {str(e)}",
        )


@router.get("/suggestions")
async def get_search_suggestions(
    q: str = Query(..., description="Search query for suggestions"),
    type: str = Query(
        "skills",
        pattern="^(providers|requests|skills|all)$",
        description="Type of suggestions",
    ),
    limit: int = Query(10, ge=1, le=50, description="Maximum suggestions to return"),
    matching_service: MatchingService = Depends(get_matching_service),
):
    """Get search suggestions based on query and type."""
    try:
        result = await matching_service.get_search_suggestions(
            query=q, suggestion_type=type, limit=limit
        )

        return {"suggestions": result.get("suggestions", [])}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get suggestions: {str(e)}",
        )
