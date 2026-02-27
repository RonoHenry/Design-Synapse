"""Recommendation API endpoints."""
import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from packages.common.auth.models import User

from ...api.dependencies import get_current_user
from ...core.database import get_db
from ...core.error_handling import handle_api_errors
from ...services.factory import ServiceFactory
from ...services.recommendation import (RecommendationScore,
                                        RecommendationService,
                                        RecommendationType)

logger = logging.getLogger(__name__)

router = APIRouter()


class RecommendationRequest(BaseModel):
    """Request model for getting recommendations."""

    num_recommendations: int = Field(
        default=10, ge=1, le=50, description="Number of recommendations to return"
    )
    recommendation_types: Optional[List[str]] = Field(
        default=None,
        description="Types of recommendations to include (content_based, collaborative, trending, contextual)",
    )
    context: Optional[Dict[str, Any]] = Field(
        default=None, description="Additional context for recommendations"
    )


class RecommendationResponse(BaseModel):
    """Response model for recommendations."""

    resource_id: int
    score: float
    recommendation_type: str
    explanation: str
    metadata: Dict[str, Any]


class SimilarResourcesRequest(BaseModel):
    """Request model for similar resources."""

    num_similar: int = Field(
        default=5, ge=1, le=20, description="Number of similar resources to return"
    )


class RecommendationExplanationResponse(BaseModel):
    """Response model for recommendation explanation."""

    resource_id: int
    resource_title: str
    user_profile_summary: Dict[str, Any]
    matching_factors: List[Dict[str, Any]]
    recommendation_strength: str


class RecommendationWeightsRequest(BaseModel):
    """Request model for updating recommendation weights."""

    content_based: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    collaborative: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    trending: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    contextual: Optional[float] = Field(default=None, ge=0.0, le=1.0)


@router.get("/", response_model=List[RecommendationResponse])
@handle_api_errors("get_user_recommendations")
async def get_user_recommendations(
    request: RecommendationRequest = Depends(),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get personalized recommendations for the current user.

    Returns recommendations based on user's interests, bookmarks, and behavior.
    Supports multiple recommendation algorithms including content-based,
    collaborative filtering, trending content, and contextual recommendations.
    """
    try:
        # Get recommendation service
        service_factory = ServiceFactory()
        recommendation_service = await service_factory.get_recommendation_service()

        # Parse recommendation types
        rec_types = None
        if request.recommendation_types:
            rec_types = []
            for rec_type_str in request.recommendation_types:
                try:
                    rec_type = RecommendationType(rec_type_str.lower())
                    rec_types.append(rec_type)
                except ValueError:
                    logger.warning(f"Invalid recommendation type: {rec_type_str}")

        # Get recommendations
        recommendations = await recommendation_service.get_recommendations(
            user_id=current_user.id,
            db=db,
            num_recommendations=request.num_recommendations,
            recommendation_types=rec_types,
            context=request.context,
        )

        # Convert to response format
        return [
            RecommendationResponse(
                resource_id=rec.resource_id,
                score=rec.score,
                recommendation_type=rec.recommendation_type.value,
                explanation=rec.explanation,
                metadata=rec.metadata,
            )
            for rec in recommendations
        ]

    except Exception as e:
        logger.error(f"Failed to get recommendations for user {current_user.id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get recommendations")


@router.get("/similar/{resource_id}", response_model=List[RecommendationResponse])
@handle_api_errors("get_similar_resources")
async def get_similar_resources(
    resource_id: int = Path(
        ..., description="ID of the resource to find similar resources for"
    ),
    num_similar: int = Query(
        5, ge=1, le=20, description="Number of similar resources to return"
    ),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get resources similar to a specific resource.

    Uses content-based similarity to find resources with similar topics,
    keywords, and technical domains.
    """
    try:
        # Get recommendation service
        service_factory = ServiceFactory()
        recommendation_service = await service_factory.get_recommendation_service()

        # Get similar resources
        similar_resources = await recommendation_service.get_similar_resources(
            resource_id=resource_id, db=db, num_similar=num_similar
        )

        # Convert to response format
        return [
            RecommendationResponse(
                resource_id=rec.resource_id,
                score=rec.score,
                recommendation_type=rec.recommendation_type.value,
                explanation=rec.explanation,
                metadata=rec.metadata,
            )
            for rec in similar_resources
        ]

    except Exception as e:
        logger.error(f"Failed to get similar resources for resource {resource_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get similar resources")


@router.get("/explain/{resource_id}", response_model=RecommendationExplanationResponse)
@handle_api_errors("explain_recommendation")
async def explain_recommendation(
    resource_id: int = Path(
        ..., description="ID of the resource to explain recommendation for"
    ),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get detailed explanation for why a resource was recommended.

    Provides insights into the recommendation algorithm's decision-making
    process, including matching factors and recommendation strength.
    """
    try:
        # Get recommendation service
        service_factory = ServiceFactory()
        recommendation_service = await service_factory.get_recommendation_service()

        # Get explanation
        explanation = await recommendation_service.explain_recommendation(
            user_id=current_user.id, resource_id=resource_id, db=db
        )

        if "error" in explanation:
            raise HTTPException(status_code=404, detail=explanation["error"])

        return RecommendationExplanationResponse(**explanation)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Failed to explain recommendation for resource {resource_id}: {e}"
        )
        raise HTTPException(status_code=500, detail="Failed to explain recommendation")


@router.get("/trending", response_model=List[RecommendationResponse])
@handle_api_errors("get_trending_recommendations")
async def get_trending_recommendations(
    num_recommendations: int = Query(
        10, ge=1, le=50, description="Number of trending resources to return"
    ),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get currently trending resources.

    Returns resources that are popular based on recent bookmarks and activity.
    """
    try:
        # Get recommendation service
        service_factory = ServiceFactory()
        recommendation_service = await service_factory.get_recommendation_service()

        # Get trending recommendations
        recommendations = await recommendation_service.get_recommendations(
            user_id=current_user.id,
            db=db,
            num_recommendations=num_recommendations,
            recommendation_types=[RecommendationType.TRENDING],
        )

        # Convert to response format
        return [
            RecommendationResponse(
                resource_id=rec.resource_id,
                score=rec.score,
                recommendation_type=rec.recommendation_type.value,
                explanation=rec.explanation,
                metadata=rec.metadata,
            )
            for rec in recommendations
        ]

    except Exception as e:
        logger.error(f"Failed to get trending recommendations: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to get trending recommendations"
        )


@router.get("/stats")
@handle_api_errors("get_recommendation_stats")
async def get_recommendation_stats(current_user: User = Depends(get_current_user)):
    """Get recommendation system statistics and cache information."""
    try:
        # Get recommendation service
        service_factory = ServiceFactory()
        recommendation_service = await service_factory.get_recommendation_service()

        # Get cache stats
        stats = recommendation_service.get_cache_stats()

        return {
            "cache_stats": stats,
            "available_recommendation_types": [rt.value for rt in RecommendationType],
            "default_weights": stats.get("weights", {}),
            "user_id": current_user.id,
        }

    except Exception as e:
        logger.error(f"Failed to get recommendation stats: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to get recommendation stats"
        )


@router.post("/weights")
@handle_api_errors("update_recommendation_weights")
async def update_recommendation_weights(
    weights_request: RecommendationWeightsRequest,
    current_user: User = Depends(get_current_user),
):
    """Update recommendation algorithm weights.

    Allows fine-tuning the balance between different recommendation algorithms.
    Weights must sum to 1.0.
    """
    try:
        # Get recommendation service
        service_factory = ServiceFactory()
        recommendation_service = await service_factory.get_recommendation_service()

        # Build weights dictionary
        new_weights = {}
        if weights_request.content_based is not None:
            new_weights[
                RecommendationType.CONTENT_BASED
            ] = weights_request.content_based
        if weights_request.collaborative is not None:
            new_weights[
                RecommendationType.COLLABORATIVE
            ] = weights_request.collaborative
        if weights_request.trending is not None:
            new_weights[RecommendationType.TRENDING] = weights_request.trending
        if weights_request.contextual is not None:
            new_weights[RecommendationType.CONTEXTUAL] = weights_request.contextual

        if not new_weights:
            raise HTTPException(
                status_code=400, detail="At least one weight must be provided"
            )

        # Update weights
        recommendation_service.update_weights(new_weights)

        return {
            "message": "Recommendation weights updated successfully",
            "new_weights": new_weights,
            "updated_by": current_user.id,
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to update recommendation weights: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to update recommendation weights"
        )


@router.post("/cache/clear")
@handle_api_errors("clear_recommendation_cache")
async def clear_recommendation_cache(current_user: User = Depends(get_current_user)):
    """Clear recommendation caches.

    Clears both user profile cache and recommendation cache.
    Useful for testing or when user preferences change significantly.
    """
    try:
        # Get recommendation service
        service_factory = ServiceFactory()
        recommendation_service = await service_factory.get_recommendation_service()

        # Clear cache
        recommendation_service.clear_cache()

        return {
            "message": "Recommendation cache cleared successfully",
            "cleared_by": current_user.id,
            "timestamp": "now",
        }

    except Exception as e:
        logger.error(f"Failed to clear recommendation cache: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to clear recommendation cache"
        )


@router.get("/contextual")
@handle_api_errors("get_contextual_recommendations")
async def get_contextual_recommendations(
    context_type: str = Query(
        ..., description="Type of context (project, search, resource)"
    ),
    context_value: str = Query(
        ..., description="Context value (project_id, search_query, resource_id)"
    ),
    num_recommendations: int = Query(
        10, ge=1, le=50, description="Number of recommendations to return"
    ),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get contextual recommendations based on current user context.

    Provides recommendations based on:
    - Current project context
    - Recent search queries
    - Currently viewed resources
    """
    try:
        # Build context dictionary
        context = {}
        if context_type == "project":
            context["current_project"] = context_value
        elif context_type == "search":
            context["search_query"] = context_value
        elif context_type == "resource":
            try:
                context["current_resource"] = int(context_value)
            except ValueError:
                raise HTTPException(
                    status_code=400, detail="Resource ID must be an integer"
                )
        else:
            raise HTTPException(
                status_code=400,
                detail="Context type must be one of: project, search, resource",
            )

        # Get recommendation service
        service_factory = ServiceFactory()
        recommendation_service = await service_factory.get_recommendation_service()

        # Get contextual recommendations
        recommendations = await recommendation_service.get_recommendations(
            user_id=current_user.id,
            db=db,
            num_recommendations=num_recommendations,
            recommendation_types=[RecommendationType.CONTEXTUAL],
            context=context,
        )

        # Convert to response format
        return [
            RecommendationResponse(
                resource_id=rec.resource_id,
                score=rec.score,
                recommendation_type=rec.recommendation_type.value,
                explanation=rec.explanation,
                metadata=rec.metadata,
            )
            for rec in recommendations
        ]

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get contextual recommendations: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to get contextual recommendations"
        )
