"""
Optimization API routes.

This module provides REST API endpoints for:
- Generating optimization suggestions for designs
- Retrieving optimization suggestions
- Applying optimization suggestions to create new design versions
"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ....infrastructure.database import get_db
from ....repositories.design_repository import DesignRepository
from ....repositories.optimization_repository import OptimizationRepository
from ....services.optimization_service import OptimizationService
from ....services.llm_client import LLMClient, LLMGenerationError, LLMTimeoutError
from ....services.project_client import ProjectClient, ProjectAccessDeniedError
from ...dependencies import CurrentUserId, get_current_user_id
from ..schemas.requests import OptimizationRequest
from ..schemas.responses import OptimizationResponse, DesignResponse

router = APIRouter(tags=["optimizations"])


def get_design_repository(db: Session = Depends(get_db)) -> DesignRepository:
    """Dependency to get design repository instance."""
    return DesignRepository(db)


def get_optimization_repository(db: Session = Depends(get_db)) -> OptimizationRepository:
    """Dependency to get optimization repository instance."""
    return OptimizationRepository(db)


def get_llm_client() -> LLMClient:
    """Dependency to get LLM client instance."""
    from ....core.config import get_settings
    config = get_settings()
    return LLMClient(config.llm)


def get_project_client() -> ProjectClient:
    """Dependency to get project client instance."""
    return ProjectClient()


def get_optimization_service(
    db: Session = Depends(get_db),
    llm_client: LLMClient = Depends(get_llm_client),
) -> OptimizationService:
    """Dependency to get optimization service instance."""
    optimization_repository = OptimizationRepository(db)
    design_repository = DesignRepository(db)
    
    return OptimizationService(
        llm_client=llm_client,
        optimization_repository=optimization_repository,
        design_repository=design_repository,
    )


@router.post(
    "/designs/{design_id}/optimize",
    response_model=List[OptimizationResponse],
    status_code=status.HTTP_200_OK,
    summary="Generate optimization suggestions",
    description="Generate AI-powered optimization suggestions for a design",
)
async def generate_optimizations(
    design_id: int,
    request: OptimizationRequest,
    user_id: CurrentUserId,
    service: OptimizationService = Depends(get_optimization_service),
    design_repository: DesignRepository = Depends(get_design_repository),
    project_client: ProjectClient = Depends(get_project_client),
) -> List[OptimizationResponse]:
    """
    Generate optimization suggestions for a design.
    
    This endpoint:
    1. Verifies user has access to the project
    2. Retrieves the design
    3. Generates optimization suggestions using AI
    4. Stores and returns the suggestions
    
    Args:
        design_id: ID of the design to optimize
        request: Optimization request with types to generate
        user_id: Current authenticated user ID
        service: Optimization service
        design_repository: Design repository
        project_client: Project service client
        
    Returns:
        List of generated optimization suggestions
        
    Raises:
        401: If authentication fails
        403: If user doesn't have access to the project
        404: If design not found
        500: If AI generation fails
    """
    # Get design
    design = design_repository.get_design_by_id(design_id, include_archived=False)
    
    if not design:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Design with ID {design_id} not found",
        )
    
    # Verify project access
    try:
        await project_client.verify_project_access(
            project_id=design.project_id,
            user_id=user_id,
        )
    except ProjectAccessDeniedError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access denied to project {design.project_id}",
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Unable to verify project access",
        )
    
    # Generate optimizations
    try:
        optimizations = await service.generate_optimizations(
            design=design,
            optimization_types=request.optimization_types,
        )
        
        return [OptimizationResponse.model_validate(opt) for opt in optimizations]
        
    except LLMTimeoutError:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Optimization generation timed out. Please try again.",
        )
    except LLMGenerationError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Optimization generation failed: {str(e)}",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {str(e)}",
        )


@router.get(
    "/designs/{design_id}/optimizations",
    response_model=List[OptimizationResponse],
    summary="Get optimization suggestions",
    description="Retrieve all optimization suggestions for a design",
)
async def get_optimizations(
    design_id: int,
    user_id: CurrentUserId,
    design_repository: DesignRepository = Depends(get_design_repository),
    optimization_repository: OptimizationRepository = Depends(get_optimization_repository),
    project_client: ProjectClient = Depends(get_project_client),
) -> List[OptimizationResponse]:
    """
    Retrieve optimization suggestions for a design.
    
    Args:
        design_id: ID of the design
        user_id: Current authenticated user ID
        design_repository: Design repository
        optimization_repository: Optimization repository
        project_client: Project service client
        
    Returns:
        List of optimization suggestions
        
    Raises:
        401: If authentication fails
        403: If user doesn't have access to the project
        404: If design not found
    """
    # Get design
    design = design_repository.get_design_by_id(design_id, include_archived=False)
    
    if not design:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Design with ID {design_id} not found",
        )
    
    # Verify project access
    try:
        await project_client.verify_project_access(
            project_id=design.project_id,
            user_id=user_id,
        )
    except ProjectAccessDeniedError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access denied to project {design.project_id}",
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Unable to verify project access",
        )
    
    # Get optimizations
    optimizations = optimization_repository.get_optimizations_by_design_id(design_id)
    
    return [OptimizationResponse.model_validate(opt) for opt in optimizations]


@router.post(
    "/optimizations/{optimization_id}/apply",
    response_model=DesignResponse,
    status_code=status.HTTP_200_OK,
    summary="Apply optimization suggestion",
    description="Apply an optimization suggestion by creating a new design version",
)
async def apply_optimization(
    optimization_id: int,
    user_id: CurrentUserId,
    service: OptimizationService = Depends(get_optimization_service),
    optimization_repository: OptimizationRepository = Depends(get_optimization_repository),
    design_repository: DesignRepository = Depends(get_design_repository),
    project_client: ProjectClient = Depends(get_project_client),
) -> DesignResponse:
    """
    Apply an optimization suggestion.
    
    This endpoint:
    1. Retrieves the optimization
    2. Verifies user has access to the project
    3. Checks optimization hasn't already been applied
    4. Creates a new design version with the optimization applied
    5. Updates optimization status to 'applied'
    
    Args:
        optimization_id: ID of the optimization to apply
        user_id: Current authenticated user ID
        service: Optimization service
        optimization_repository: Optimization repository
        design_repository: Design repository
        project_client: Project service client
        
    Returns:
        New design version with optimization applied
        
    Raises:
        400: If optimization has already been applied
        401: If authentication fails
        403: If user doesn't have access to the project
        404: If optimization not found
    """
    # Get optimization (without updating status yet)
    from sqlalchemy import select
    from ....models.design_optimization import DesignOptimization
    
    # Get optimization using repository's session
    stmt = select(DesignOptimization).where(DesignOptimization.id == optimization_id)
    result = optimization_repository.db.execute(stmt)
    optimization = result.scalar_one_or_none()
    
    if not optimization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Optimization with ID {optimization_id} not found",
        )
    
    # Check if already applied
    if optimization.status == "applied":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Optimization {optimization_id} has already been applied",
        )
    
    # Get associated design
    design = design_repository.get_design_by_id(
        optimization.design_id,
        include_archived=False
    )
    
    if not design:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Design with ID {optimization.design_id} not found",
        )
    
    # Verify project access
    try:
        await project_client.verify_project_access(
            project_id=design.project_id,
            user_id=user_id,
        )
    except ProjectAccessDeniedError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access denied to project {design.project_id}",
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Unable to verify project access",
        )
    
    # Apply optimization
    try:
        new_design = await service.apply_optimization(
            optimization_id=optimization_id,
            user_id=user_id,
        )
        
        return DesignResponse.model_validate(new_design)
        
    except ValueError as e:
        # This shouldn't happen since we already checked, but handle it
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {str(e)}",
        )
