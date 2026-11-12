"""Structural engineering API endpoints."""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from src.api.dependencies import get_user_context, require_calculation_permission
from src.api.v1.schemas.structural import (
    BeamDesignRequest,
    BeamDesignResponse,
    ColumnDesignRequest,
    ColumnDesignResponse,
    FoundationDesignRequest,
    FoundationDesignResponse,
    LoadCalculationRequest,
    LoadCalculationResponse,
)
from src.core.database import get_db
from src.core.exceptions import EngineeringServiceException
from src.repositories.calculation_sheet_repository import CalculationSheetRepository
from src.repositories.structural_design_repository import StructuralDesignRepository
from src.services.recalculation_service import RecalculationService
from src.services.structural_calculation_service import StructuralCalculationService

from packages.common.auth.models import UserContext

logger = logging.getLogger(__name__)

router = APIRouter()


# Dependency to get structural calculation service
async def get_structural_service(
    db: AsyncSession = Depends(get_db),
) -> StructuralCalculationService:
    """Get structural calculation service instance."""
    calculation_sheet_repo = CalculationSheetRepository(db)
    structural_design_repo = StructuralDesignRepository(db)
    recalculation_service = RecalculationService(db)

    return StructuralCalculationService(
        db_session=db,
        calculation_sheet_repo=calculation_sheet_repo,
        structural_design_repo=structural_design_repo,
        recalculation_service=recalculation_service,
    )


@router.post(
    "/loads",
    response_model=LoadCalculationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Calculate structural loads",
    description="Calculate dead, live, wind, and seismic loads per ASCE 7",
    responses={
        201: {
            "description": "Load calculation completed successfully",
            "content": {
                "application/json": {
                    "example": {
                        "calculation_id": ("550e8400-e29b-41d4-a716-446655440000"),
                        "project_id": ("660e8400-e29b-41d4-a716-446655440000"),
                        "dead_load": 1500.0,
                        "live_load": 800.0,
                        "wind_load": 450.0,
                        "seismic_load": 320.0,
                        "total_load": 3070.0,
                        "unit_system": "imperial",
                        "created_at": "2024-01-15T10:30:00Z",
                    }
                }
            },
        },
        400: {"description": "Invalid input data"},
        401: {"description": "Authentication required"},
        403: {"description": "Insufficient permissions"},
        500: {"description": "Internal server error"},
    },
)
async def calculate_loads(
    request: LoadCalculationRequest,
    user: UserContext = Depends(require_calculation_permission),
    structural_service: StructuralCalculationService = Depends(get_structural_service),
) -> LoadCalculationResponse:
    """
    Calculate structural loads per ASCE 7.

    Computes dead, live, wind, and seismic loads based on building data.

    **Parameters:**
    - **request**: Load calculation parameters including building data
    - **user**: Authenticated user context (from JWT token)

    **Returns:**
    - Load calculation results with all load components

    **Errors:**
    - **400**: Invalid input data or validation failure
    - **401**: Missing or invalid authentication token
    - **403**: User lacks engineer role
    - **500**: Internal server error
    """
    try:
        result = await structural_service.calculate_loads(
            project_id=str(request.project_id),
            building_data=request.building_data,
            load_types=[lt.value for lt in request.load_types],
            user_id=user.user_id,
            unit_system=request.unit_system.value,
        )

        return LoadCalculationResponse(
            calculation_id=UUID(int=result.calculation_id),
            project_id=UUID(result.project_id),
            dead_load=result.dead_load,
            live_load=result.live_load,
            wind_load=result.wind_load,
            seismic_load=result.seismic_load,
            total_load=result.total_load,
            unit_system=request.unit_system,
            created_at=result.created_at,
        )

    except ValueError as e:
        logger.error(f"Validation error in load calculation: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": str(e)},
        )
    except EngineeringServiceException as e:
        logger.error(f"Engineering service error: {e}")
        raise HTTPException(
            status_code=e.status_code,
            detail={"error": e.message, "details": e.details},
        )
    except Exception as e:
        logger.exception(f"Unexpected error calculating loads: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "Internal server error"},
        )


@router.post(
    "/beams",
    response_model=BeamDesignResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Design beam",
    description="Design beam with deflection and stress checks",
    responses={
        201: {
            "description": "Beam design completed successfully",
            "content": {
                "application/json": {
                    "example": {
                        "design_id": ("550e8400-e29b-41d4-a716-446655440000"),
                        "project_id": ("660e8400-e29b-41d4-a716-446655440000"),
                        "required_section": "W18x50",
                        "deflection": 0.75,
                        "stress_ratio": 0.85,
                        "is_adequate": True,
                        "unit_system": "imperial",
                        "created_at": "2024-01-15T10:30:00Z",
                    }
                }
            },
        },
        400: {"description": "Invalid input data"},
        401: {"description": "Authentication required"},
        403: {"description": "Insufficient permissions"},
        500: {"description": "Internal server error"},
    },
)
async def design_beam(
    request: BeamDesignRequest,
    user: UserContext = Depends(require_calculation_permission),
    structural_service: StructuralCalculationService = Depends(get_structural_service),
) -> BeamDesignResponse:
    """
    Design beam with deflection and stress checks.

    Calculates required beam section based on loads, span, and material.

    **Parameters:**
    - **request**: Beam design parameters including loads and span
    - **user**: Authenticated user context (from JWT token)

    **Returns:**
    - Beam design results with adequacy check

    **Errors:**
    - **400**: Invalid input data or validation failure
    - **401**: Missing or invalid authentication token
    - **403**: User lacks engineer role
    - **500**: Internal server error
    """
    try:
        result = await structural_service.design_beam(
            project_id=str(request.project_id),
            loads=request.loads,
            span=request.span,
            material=request.material,
            user_id=user.user_id,
            unit_system=request.unit_system.value,
        )

        # Format section description
        section_desc = (
            f"Depth: {result.geometry.depth:.2f} in, "
            f"Width: {result.geometry.width:.2f} in"
        )

        return BeamDesignResponse(
            design_id=UUID(int=result.geometry.depth),  # Placeholder
            project_id=request.project_id,
            required_section=section_desc,
            deflection=result.max_deflection,
            stress_ratio=result.stress_ratio,
            is_adequate=result.is_adequate,
            unit_system=request.unit_system,
        )

    except ValueError as e:
        logger.error(f"Validation error in beam design: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": str(e)},
        )
    except EngineeringServiceException as e:
        logger.error(f"Engineering service error: {e}")
        raise HTTPException(
            status_code=e.status_code,
            detail={"error": e.message, "details": e.details},
        )
    except Exception as e:
        logger.exception(f"Unexpected error designing beam: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "Internal server error"},
        )


@router.post(
    "/columns",
    response_model=ColumnDesignResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Design column",
    description="Design column with buckling analysis",
    responses={
        201: {
            "description": "Column design completed successfully",
            "content": {
                "application/json": {
                    "example": {
                        "design_id": ("550e8400-e29b-41d4-a716-446655440000"),
                        "project_id": ("660e8400-e29b-41d4-a716-446655440000"),
                        "required_section": "W14x90",
                        "axial_capacity": 450000.0,
                        "buckling_ratio": 0.72,
                        "stress_ratio": 0.68,
                        "is_adequate": True,
                        "unit_system": "imperial",
                        "created_at": "2024-01-15T10:30:00Z",
                    }
                }
            },
        },
        400: {"description": "Invalid input data"},
        401: {"description": "Authentication required"},
        403: {"description": "Insufficient permissions"},
        500: {"description": "Internal server error"},
    },
)
async def design_column(
    request: ColumnDesignRequest,
    user: UserContext = Depends(require_calculation_permission),
    structural_service: StructuralCalculationService = Depends(get_structural_service),
) -> ColumnDesignResponse:
    """
    Design column with buckling analysis.

    Calculates required column section based on axial load and moment.

    **Parameters:**
    - **request**: Column design parameters including loads and length
    - **user**: Authenticated user context (from JWT token)

    **Returns:**
    - Column design results with adequacy check

    **Errors:**
    - **400**: Invalid input data or validation failure
    - **401**: Missing or invalid authentication token
    - **403**: User lacks engineer role
    - **500**: Internal server error
    """
    try:
        result = await structural_service.design_column(
            project_id=str(request.project_id),
            loads={
                "axial_load": request.axial_load,
                "moment_x": request.moment,
                "moment_y": 0.0,
            },
            length=request.length,
            material=request.material,
            geometry={},  # Will be determined by designer
            user_id=user.user_id,
            unit_system=request.unit_system.value,
        )

        # Format section description
        if result.geometry.diameter:
            section_desc = f"Diameter: {result.geometry.diameter:.2f} in"
        else:
            section_desc = (
                f"Depth: {result.geometry.depth:.2f} in, "
                f"Width: {result.geometry.width:.2f} in"
            )

        # Calculate buckling ratio
        buckling_ratio = (
            result.combined_stress_ratio if result.buckling_capacity > 0 else 0.0
        )

        return ColumnDesignResponse(
            design_id=UUID(int=result.geometry.depth),  # Placeholder
            project_id=request.project_id,
            required_section=section_desc,
            axial_capacity=result.axial_capacity,
            buckling_ratio=buckling_ratio,
            stress_ratio=result.combined_stress_ratio,
            is_adequate=result.is_adequate,
            unit_system=request.unit_system,
        )

    except ValueError as e:
        logger.error(f"Validation error in column design: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": str(e)},
        )
    except EngineeringServiceException as e:
        logger.error(f"Engineering service error: {e}")
        raise HTTPException(
            status_code=e.status_code,
            detail={"error": e.message, "details": e.details},
        )
    except Exception as e:
        logger.exception(f"Unexpected error designing column: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "Internal server error"},
        )


@router.post(
    "/foundations",
    response_model=FoundationDesignResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Design foundation",
    description="Design foundation with bearing capacity check",
    responses={
        201: {
            "description": "Foundation design completed successfully",
            "content": {
                "application/json": {
                    "example": {
                        "design_id": ("550e8400-e29b-41d4-a716-446655440000"),
                        "project_id": ("660e8400-e29b-41d4-a716-446655440000"),
                        "foundation_type": "spread_footing",
                        "dimensions": {
                            "length": 10.0,
                            "width": 10.0,
                            "depth": 3.0,
                        },
                        "bearing_pressure": 1800.0,
                        "settlement": 0.5,
                        "reinforcement": {
                            "area": 2.5,
                            "spacing": 12.0,
                        },
                        "is_adequate": True,
                        "unit_system": "imperial",
                        "created_at": "2024-01-15T10:30:00Z",
                    }
                }
            },
        },
        400: {"description": "Invalid input data"},
        401: {"description": "Authentication required"},
        403: {"description": "Insufficient permissions"},
        500: {"description": "Internal server error"},
    },
)
async def design_foundation(
    request: FoundationDesignRequest,
    user: UserContext = Depends(require_calculation_permission),
    structural_service: StructuralCalculationService = Depends(get_structural_service),
) -> FoundationDesignResponse:
    """
    Design foundation with bearing capacity check.

    Calculates foundation dimensions based on loads and soil properties.

    **Parameters:**
    - **request**: Foundation design parameters including loads and soil
    - **user**: Authenticated user context (from JWT token)

    **Returns:**
    - Foundation design results with adequacy check

    **Errors:**
    - **400**: Invalid input data or validation failure
    - **401**: Missing or invalid authentication token
    - **403**: User lacks engineer role
    - **500**: Internal server error
    """
    try:
        # Determine foundation type and geometry from loads
        geometry = {
            "foundation_type": "spread_footing",
            "length": 10.0,
            "width": 10.0,
            "depth": 3.0,
            "thickness": 18.0,
        }

        result = await structural_service.design_foundation(
            project_id=str(request.project_id),
            loads=request.loads,
            soil_properties=request.soil_properties,
            geometry=geometry,
            user_id=user.user_id,
            unit_system=request.unit_system.value,
        )

        # Format dimensions
        dimensions = {
            "length": result.geometry.length,
            "width": result.geometry.width,
            "depth": result.geometry.depth,
            "thickness": result.geometry.thickness,
        }
        if result.geometry.diameter:
            dimensions["diameter"] = result.geometry.diameter

        # Format reinforcement
        reinforcement = {
            "area": result.reinforcement_area,
            "spacing": 12.0,  # Default spacing
        }

        return FoundationDesignResponse(
            design_id=UUID(int=int(result.geometry.length * 1000)),
            project_id=request.project_id,
            foundation_type=result.geometry.foundation_type.value,
            dimensions=dimensions,
            bearing_pressure=result.bearing_pressure,
            settlement=result.settlement,
            reinforcement=reinforcement,
            is_adequate=result.is_adequate,
            unit_system=request.unit_system,
        )

    except ValueError as e:
        logger.error(f"Validation error in foundation design: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": str(e)},
        )
    except EngineeringServiceException as e:
        logger.error(f"Engineering service error: {e}")
        raise HTTPException(
            status_code=e.status_code,
            detail={"error": e.message, "details": e.details},
        )
    except Exception as e:
        logger.exception(f"Unexpected error designing foundation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "Internal server error"},
        )


@router.get(
    "/designs/{id}",
    response_model=dict,
    summary="Get structural design",
    description="Retrieve a structural design by ID",
    responses={
        200: {
            "description": "Structural design retrieved successfully",
            "content": {
                "application/json": {
                    "example": {
                        "id": "550e8400-e29b-41d4-a716-446655440000",
                        "project_id": ("660e8400-e29b-41d4-a716-446655440000"),
                        "design_type": "beam",
                        "title": "Beam Design - 2024-01-15",
                        "status": "approved",
                        "created_at": "2024-01-15T10:30:00Z",
                    }
                }
            },
        },
        404: {"description": "Design not found"},
        401: {"description": "Authentication required"},
        500: {"description": "Internal server error"},
    },
)
async def get_design(
    id: int,
    user: UserContext = Depends(get_user_context),
    structural_service: StructuralCalculationService = Depends(get_structural_service),
) -> dict:
    """
    Retrieve a structural design by ID.

    **Path Parameters:**
    - **id**: Structural design ID

    **Returns:**
    - Structural design details

    **Errors:**
    - **404**: Design not found
    - **401**: Missing or invalid authentication token
    - **500**: Internal server error
    """
    try:
        design = await structural_service.structural_design_repo.get_by_id(id)

        if not design:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"error": "Design not found"},
            )

        return {
            "id": design.id,
            "project_id": design.project_id,
            "design_type": design.design_type,
            "title": design.title,
            "description": design.description,
            "loads": design.loads,
            "material_properties": design.material_properties,
            "geometry": design.geometry,
            "design_results": design.design_results,
            "stress_ratios": design.stress_ratios,
            "status": design.status,
            "units": design.units,
            "created_by": design.created_by,
            "created_at": design.created_at,
            "updated_at": design.updated_at,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Unexpected error retrieving design {id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "Internal server error"},
        )


@router.put(
    "/designs/{id}",
    response_model=dict,
    summary="Update structural design",
    description="Update a structural design",
    responses={
        200: {
            "description": "Design updated successfully",
            "content": {
                "application/json": {
                    "example": {
                        "id": "550e8400-e29b-41d4-a716-446655440000",
                        "status": "approved",
                        "updated_at": "2024-01-15T11:00:00Z",
                    }
                }
            },
        },
        404: {"description": "Design not found"},
        401: {"description": "Authentication required"},
        403: {"description": "Insufficient permissions"},
        500: {"description": "Internal server error"},
    },
)
async def update_design(
    id: int,
    update_data: dict,
    user: UserContext = Depends(require_calculation_permission),
    structural_service: StructuralCalculationService = Depends(get_structural_service),
) -> dict:
    """
    Update a structural design.

    **Path Parameters:**
    - **id**: Structural design ID

    **Parameters:**
    - **update_data**: Fields to update

    **Returns:**
    - Updated design details

    **Errors:**
    - **404**: Design not found
    - **401**: Missing or invalid authentication token
    - **403**: User lacks engineer role
    - **500**: Internal server error
    """
    try:
        design = await structural_service.structural_design_repo.get_by_id(id)

        if not design:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"error": "Design not found"},
            )

        # Update allowed fields
        update_data["updated_by"] = user.user_id

        updated_design = await structural_service.structural_design_repo.update(
            id, update_data
        )
        await structural_service.db_session.commit()

        return {
            "id": updated_design.id,
            "status": updated_design.status,
            "updated_at": updated_design.updated_at,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Unexpected error updating design {id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "Internal server error"},
        )


@router.delete(
    "/designs/{id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete structural design",
    description="Soft delete a structural design",
    responses={
        204: {"description": "Design deleted successfully"},
        404: {"description": "Design not found"},
        401: {"description": "Authentication required"},
        403: {"description": "Insufficient permissions"},
        500: {"description": "Internal server error"},
    },
)
async def delete_design(
    id: int,
    user: UserContext = Depends(require_calculation_permission),
    structural_service: StructuralCalculationService = Depends(get_structural_service),
) -> None:
    """
    Soft delete a structural design.

    **Path Parameters:**
    - **id**: Structural design ID

    **Returns:**
    - No content (204)

    **Errors:**
    - **404**: Design not found
    - **401**: Missing or invalid authentication token
    - **403**: User lacks engineer role
    - **500**: Internal server error
    """
    try:
        design = await structural_service.structural_design_repo.get_by_id(id)

        if not design:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"error": "Design not found"},
            )

        await structural_service.structural_design_repo.soft_delete(id, user.user_id)
        await structural_service.db_session.commit()

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Unexpected error deleting design {id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "Internal server error"},
        )
