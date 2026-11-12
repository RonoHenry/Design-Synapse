"""Structural analysis API endpoints."""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from src.api.v1.dependencies import require_authentication
from src.api.v1.schemas.analysis import (StructuralAnalysisRequest,
                                         StructuralAnalysisResponse)
from src.core.database import get_db
from src.core.exceptions import (ArchitecturalServiceException, NotFoundError,
                                 ValidationError)
from src.repositories.design_repository import DesignRepository
from src.repositories.structural_analysis_repository import \
    StructuralAnalysisRepository
from src.services.structural_analysis_service import StructuralAnalysisService

logger = logging.getLogger(__name__)

router = APIRouter()


# Dependency to get structural analysis service
async def get_structural_analysis_service(
    db: AsyncSession = Depends(get_db),
) -> StructuralAnalysisService:
    """Get structural analysis service instance."""
    structural_repository = StructuralAnalysisRepository(db)
    design_repository = DesignRepository(db)
    return StructuralAnalysisService(structural_repository, design_repository)


@router.post(
    "/designs/{design_id}/structural-analysis",
    response_model=StructuralAnalysisResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Request structural analysis",
    description="Request structural analysis for a design",
)
async def request_structural_analysis(
    design_id: UUID,
    request: StructuralAnalysisRequest,
    user_id: UUID = Depends(require_authentication),
    structural_service: StructuralAnalysisService = Depends(
        get_structural_analysis_service
    ),
) -> StructuralAnalysisResponse:
    """
    Request structural analysis for a design.

    Initiates structural analysis with specified parameters and system type.
    """
    try:
        structural_analysis = await structural_service.analyze_structure(
            design_id=design_id,
            parameters=request,
        )

        return StructuralAnalysisResponse(
            id=UUID(structural_analysis.id),
            design_id=UUID(structural_analysis.design_id),
            design_version=structural_analysis.design_version,
            structural_system=structural_analysis.structural_system,
            analysis_type=structural_analysis.analysis_type,
            status=structural_analysis.status,
            load_calculations=structural_analysis.load_calculations,
            issues=[],  # Will be populated when analysis completes
            recommendations=structural_analysis.recommendations,
            report_url=structural_analysis.report_url,
            started_at=structural_analysis.started_at,
            completed_at=structural_analysis.completed_at,
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
        logger.error(f"Unexpected error requesting structural analysis: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "Internal server error"},
        )


@router.get(
    "/structural-analysis/{analysis_id}",
    response_model=StructuralAnalysisResponse,
    summary="Get structural analysis results",
    description="Retrieve structural analysis results and status",
)
async def get_structural_analysis(
    analysis_id: UUID,
    structural_service: StructuralAnalysisService = Depends(
        get_structural_analysis_service
    ),
) -> StructuralAnalysisResponse:
    """
    Get structural analysis results.

    Returns detailed structural analysis results including load calculations and issues.
    """
    try:
        structural_analysis = await structural_service.get_analysis_results(analysis_id)

        # Convert issues from JSON to schema objects
        issues = []
        for issue_data in structural_analysis.issues:
            issues.append(
                {
                    "element_id": issue_data.get("element_id", ""),
                    "issue_type": issue_data.get("issue_type", ""),
                    "description": issue_data.get("description", ""),
                    "severity": issue_data.get("severity", ""),
                    "recommendation": issue_data.get("recommendation", ""),
                }
            )

        return StructuralAnalysisResponse(
            id=UUID(structural_analysis.id),
            design_id=UUID(structural_analysis.design_id),
            design_version=structural_analysis.design_version,
            structural_system=structural_analysis.structural_system,
            analysis_type=structural_analysis.analysis_type,
            status=structural_analysis.status,
            load_calculations=structural_analysis.load_calculations,
            issues=issues,
            recommendations=structural_analysis.recommendations,
            report_url=structural_analysis.report_url,
            started_at=structural_analysis.started_at,
            completed_at=structural_analysis.completed_at,
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
        logger.error(
            f"Unexpected error retrieving structural analysis {analysis_id}: {e}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "Internal server error"},
        )
