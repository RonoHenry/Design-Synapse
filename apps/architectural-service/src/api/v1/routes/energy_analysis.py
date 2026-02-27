"""Energy analysis API endpoints."""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from src.api.v1.dependencies import require_authentication
from src.api.v1.schemas.analysis import (EfficiencyRecommendation,
                                         EnergyAnalysisRequest,
                                         EnergyAnalysisResponse,
                                         EnergyEstimate, EnvelopeMetrics)
from src.core.database import get_db
from src.core.exceptions import (ArchitecturalServiceException, NotFoundError,
                                 ValidationError)
from src.repositories.design_repository import DesignRepository
from src.repositories.energy_analysis_repository import \
    EnergyAnalysisRepository
from src.services.energy_analysis_service import EnergyAnalysisService

logger = logging.getLogger(__name__)

router = APIRouter()


# Dependency to get energy analysis service
async def get_energy_analysis_service(
    db: AsyncSession = Depends(get_db),
) -> EnergyAnalysisService:
    """Get energy analysis service instance."""
    energy_repository = EnergyAnalysisRepository(db)
    design_repository = DesignRepository(db)
    return EnergyAnalysisService(energy_repository, design_repository)


@router.post(
    "/designs/{design_id}/energy-analysis",
    response_model=EnergyAnalysisResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Request energy analysis",
    description="Request energy efficiency analysis for a design",
)
async def request_energy_analysis(
    design_id: UUID,
    request: EnergyAnalysisRequest,
    user_id: UUID = Depends(require_authentication),
    energy_service: EnergyAnalysisService = Depends(get_energy_analysis_service),
) -> EnergyAnalysisResponse:
    """
    Request energy efficiency analysis for a design.

    Analyzes building envelope performance, estimates energy consumption,
    and provides efficiency recommendations based on standards like ASHRAE 90.1 and LEED.
    """
    try:
        energy_analysis = await energy_service.analyze_energy(
            design_id=design_id,
            request=request,
        )

        return energy_analysis

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
        logger.error(f"Unexpected error requesting energy analysis: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "Internal server error"},
        )


@router.get(
    "/energy-analysis/{analysis_id}",
    response_model=EnergyAnalysisResponse,
    summary="Get energy analysis results",
    description="Get energy efficiency analysis results",
)
async def get_energy_analysis_results(
    analysis_id: UUID,
    energy_service: EnergyAnalysisService = Depends(get_energy_analysis_service),
) -> EnergyAnalysisResponse:
    """
    Get energy efficiency analysis results.

    Returns the complete energy analysis including envelope performance,
    energy consumption estimates, and efficiency recommendations.
    """
    try:
        energy_analysis = await energy_service.energy_repository.get(str(analysis_id))

        if energy_analysis is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"error": f"Energy analysis {analysis_id} not found"},
            )

        # Convert envelope performance from dict to EnvelopeMetrics object
        envelope_performance = None
        if energy_analysis.envelope_performance:
            envelope_performance = EnvelopeMetrics(
                wall_r_value=energy_analysis.envelope_performance["wall_r_value"],
                roof_r_value=energy_analysis.envelope_performance["roof_r_value"],
                window_u_factor=energy_analysis.envelope_performance["window_u_factor"],
                infiltration_rate=energy_analysis.envelope_performance[
                    "infiltration_rate"
                ],
            )

        # Convert energy consumption from dict to EnergyEstimate object
        energy_consumption = None
        if energy_analysis.energy_consumption:
            energy_consumption = EnergyEstimate(
                annual_consumption_kwh=energy_analysis.energy_consumption[
                    "annual_consumption_kwh"
                ],
                heating_kwh=energy_analysis.energy_consumption["heating_kwh"],
                cooling_kwh=energy_analysis.energy_consumption["cooling_kwh"],
                lighting_kwh=energy_analysis.energy_consumption["lighting_kwh"],
                equipment_kwh=energy_analysis.energy_consumption["equipment_kwh"],
                estimated_cost=energy_analysis.energy_consumption["estimated_cost"],
            )

        # Convert recommendations from dict to EfficiencyRecommendation objects
        recommendations = []
        for rec_data in energy_analysis.recommendations:
            recommendation = EfficiencyRecommendation(
                category=rec_data["category"],
                description=rec_data["description"],
                estimated_savings_kwh=rec_data["estimated_savings_kwh"],
                estimated_cost_savings=rec_data["estimated_cost_savings"],
                implementation_cost=rec_data.get("implementation_cost"),
            )
            recommendations.append(recommendation)

        return EnergyAnalysisResponse(
            id=UUID(energy_analysis.id),
            design_id=UUID(energy_analysis.design_id),
            design_version=energy_analysis.design_version,
            standards=energy_analysis.standards,
            climate_zone=energy_analysis.climate_zone,
            status=energy_analysis.status,
            envelope_performance=envelope_performance,
            energy_consumption=energy_consumption,
            recommendations=recommendations,
            certificate_url=energy_analysis.certificate_url,
            started_at=energy_analysis.started_at,
            completed_at=energy_analysis.completed_at,
        )

    except ArchitecturalServiceException as e:
        raise HTTPException(
            status_code=e.status_code,
            detail={"error": e.message, "details": e.details},
        )
    except Exception as e:
        logger.error(f"Unexpected error getting energy analysis {analysis_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "Internal server error"},
        )
