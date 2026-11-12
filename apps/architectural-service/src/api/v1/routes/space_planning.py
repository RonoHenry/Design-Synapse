"""Space planning API endpoints."""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from src.api.v1.dependencies import require_authentication
from src.api.v1.schemas.analysis import (LayoutRecommendation, SpaceMetrics,
                                         SpacePlanningRequest,
                                         SpacePlanningResponse)
from src.core.database import get_db
from src.core.exceptions import (ArchitecturalServiceException, NotFoundError,
                                 ValidationError)
from src.repositories.design_repository import DesignRepository
from src.repositories.space_planning_repository import SpacePlanningRepository
from src.services.space_planning_service import SpacePlanningService

logger = logging.getLogger(__name__)

router = APIRouter()


# Dependency to get space planning service
async def get_space_planning_service(
    db: AsyncSession = Depends(get_db),
) -> SpacePlanningService:
    """Get space planning service instance."""
    space_planning_repository = SpacePlanningRepository(db)
    design_repository = DesignRepository(db)
    return SpacePlanningService(space_planning_repository, design_repository)


@router.post(
    "/designs/{design_id}/space-planning",
    response_model=SpacePlanningResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Request space planning",
    description="Request space planning analysis for a design",
)
async def request_space_planning(
    design_id: UUID,
    request: SpacePlanningRequest,
    user_id: UUID = Depends(require_authentication),
    space_planning_service: SpacePlanningService = Depends(get_space_planning_service),
) -> SpacePlanningResponse:
    """
    Request space planning analysis for a design.

    Generates layout recommendations, space utilization metrics,
    and a comprehensive space program document.
    """
    try:
        space_planning = await space_planning_service.plan_spaces(
            design_id=design_id,
            requirements=request.requirements,
            constraints=request.constraints,
            optimization_goals=[goal.value for goal in request.optimization_goals],
        )

        # Convert recommendations from dict to LayoutRecommendation objects
        recommendations = []
        for rec_data in space_planning.recommendations:
            recommendation = LayoutRecommendation(
                space_type=rec_data["space_type"],
                recommended_area=rec_data["recommended_area"],
                location=rec_data["location"],
                rationale=rec_data["rationale"],
            )
            recommendations.append(recommendation)

        # Convert metrics from dict to SpaceMetrics object
        metrics = None
        if space_planning.metrics:
            metrics = SpaceMetrics(
                area_efficiency=space_planning.metrics["area_efficiency"],
                circulation_ratio=space_planning.metrics["circulation_ratio"],
                density=space_planning.metrics["density"],
            )

        return SpacePlanningResponse(
            id=UUID(space_planning.id),
            design_id=UUID(space_planning.design_id),
            status=space_planning.status,
            recommendations=recommendations,
            metrics=metrics,
            space_program=space_planning.space_program,
            started_at=space_planning.started_at,
            completed_at=space_planning.completed_at,
        )

    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": e.message, "details": e.details},
        )
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": e.message, "details": e.details},
        )
    except ArchitecturalServiceException as e:
        raise HTTPException(
            status_code=e.status_code,
            detail={"error": e.message, "details": e.details},
        )
    except Exception as e:
        logger.error(f"Unexpected error requesting space planning: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "Internal server error"},
        )


@router.get(
    "/space-planning/{planning_id}",
    response_model=SpacePlanningResponse,
    summary="Get space planning results",
    description="Get space planning analysis results",
)
async def get_space_planning_results(
    planning_id: UUID,
    space_planning_service: SpacePlanningService = Depends(get_space_planning_service),
) -> SpacePlanningResponse:
    """
    Get space planning analysis results.

    Returns the complete space planning analysis including recommendations,
    metrics, and space program document.
    """
    try:
        space_planning = await space_planning_service.space_planning_repository.get(
            str(planning_id)
        )

        if space_planning is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"error": f"Space planning {planning_id} not found"},
            )

        # Convert recommendations from dict to LayoutRecommendation objects
        recommendations = []
        for rec_data in space_planning.recommendations:
            recommendation = LayoutRecommendation(
                space_type=rec_data["space_type"],
                recommended_area=rec_data["recommended_area"],
                location=rec_data["location"],
                rationale=rec_data["rationale"],
            )
            recommendations.append(recommendation)

        # Convert metrics from dict to SpaceMetrics object
        metrics = None
        if space_planning.metrics:
            metrics = SpaceMetrics(
                area_efficiency=space_planning.metrics["area_efficiency"],
                circulation_ratio=space_planning.metrics["circulation_ratio"],
                density=space_planning.metrics["density"],
            )

        return SpacePlanningResponse(
            id=UUID(space_planning.id),
            design_id=UUID(space_planning.design_id),
            status=space_planning.status,
            recommendations=recommendations,
            metrics=metrics,
            space_program=space_planning.space_program,
            started_at=space_planning.started_at,
            completed_at=space_planning.completed_at,
        )

    except ArchitecturalServiceException as e:
        raise HTTPException(
            status_code=e.status_code,
            detail={"error": e.message, "details": e.details},
        )
    except Exception as e:
        logger.error(f"Unexpected error getting space planning {planning_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "Internal server error"},
        )
