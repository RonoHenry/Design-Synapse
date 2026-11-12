"""
Design CRUD API routes.

This module provides REST API endpoints for:
- Creating designs (with AI generation)
- Retrieving designs
- Updating designs
- Deleting designs (soft delete)
- Listing designs with filters
"""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from ....infrastructure.database import get_db
from ....repositories.design_repository import DesignRepository
from ....services.design_generator import DesignGeneratorService
from ....services.llm_client import (LLMClient, LLMGenerationError,
                                     LLMTimeoutError)
from ....services.project_client import ProjectAccessDeniedError, ProjectClient
from ....tasks.visual_generation import generate_visuals_task
from ...dependencies import CurrentUserId, get_current_user_id
from ..schemas.requests import (DesignGenerationRequest, DesignUpdateRequest,
                                GenerateVisualsRequest)
from ..schemas.responses import DesignResponse

router = APIRouter(prefix="/designs", tags=["designs"])


def get_design_repository(db: Session = Depends(get_db)) -> DesignRepository:
    """Dependency to get design repository instance."""
    return DesignRepository(db)


def get_llm_client() -> LLMClient:
    """Dependency to get LLM client instance."""
    from ....core.config import get_settings

    config = get_settings()
    return LLMClient(config.llm)


def get_project_client() -> ProjectClient:
    """Dependency to get project client instance."""
    return ProjectClient()


def get_design_generator_service(
    db: Session = Depends(get_db),
    llm_client: LLMClient = Depends(get_llm_client),
    project_client: ProjectClient = Depends(get_project_client),
) -> DesignGeneratorService:
    """Dependency to get design generator service instance."""
    design_repository = DesignRepository(db)

    return DesignGeneratorService(
        llm_client=llm_client,
        project_client=project_client,
        design_repository=design_repository,
    )


@router.post(
    "/",
    response_model=DesignResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new design",
    description="Generate a new architectural design using AI from natural language description. Optionally generate visual outputs.",
)
async def create_design(
    request: DesignGenerationRequest,
    user_id: CurrentUserId,
    db: Session = Depends(get_db),
    service: DesignGeneratorService = Depends(get_design_generator_service),
) -> DesignResponse:
    """
    Create a new design with AI generation.

    This endpoint:
    1. Verifies user has access to the project
    2. Generates design specification using AI
    3. Creates and stores the design
    4. Optionally triggers visual generation (floor plans, renderings, 3D models)

    Args:
        request: Design generation request with description and requirements
        user_id: Current authenticated user ID
        service: Design generator service

    Returns:
        Created design with generated specification. If generate_visuals=True,
        visual_generation_status will be set to "processing" and visuals will
        be generated asynchronously.

    Raises:
        401: If authentication fails
        403: If user doesn't have access to the project
        422: If request validation fails
        500: If AI generation fails
    """
    try:
        design = await service.generate_design(
            request=request,
            user_id=user_id,
        )

        # Trigger visual generation if requested
        if request.generate_visuals:
            try:
                # Prepare design data for visual generation
                design_data = {
                    "building_type": design.building_type,
                    "description": design.description,
                    "requirements": design.specification or {},
                    "style": getattr(design, "style", None),
                    "materials": design.materials or [],
                }

                # Update design status to indicate visual generation is starting
                from ....repositories.design_repository import DesignRepository

                # Use the existing database session
                repo = DesignRepository(db)
                repo.update_design(design.id, visual_generation_status="pending")
                db.commit()

                # Update the design object to reflect the status change
                design.visual_generation_status = "pending"

                # Start visual generation task asynchronously
                task = generate_visuals_task.delay(
                    design_id=str(design.id),
                    design_data=design_data,
                    visual_types=["floor_plan", "rendering", "3d_model"],
                    size="1024x1024",
                    quality="standard",
                )

            except Exception as visual_error:
                # Log the error but don't fail the design creation
                import logging

                logger = logging.getLogger(__name__)
                logger.error(
                    f"Failed to start visual generation for design {design.id}: {visual_error}"
                )

                # Set status to failed
                try:
                    db_gen = get_db()
                    db_session = next(db_gen)
                    try:
                        repo = DesignRepository(db_session)
                        repo.update_design(design.id, visual_generation_status="failed")
                        db_session.commit()
                        design.visual_generation_status = "failed"
                    finally:
                        db_session.close()
                except Exception:
                    pass  # Don't fail if we can't update status

        return DesignResponse.model_validate(design)

    except ProjectAccessDeniedError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access denied to project {request.project_id}",
        )
    except LLMTimeoutError:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Design generation timed out. Please try again.",
        )
    except LLMGenerationError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Design generation failed: {str(e)}",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {str(e)}",
        )


@router.get(
    "/{design_id}",
    response_model=DesignResponse,
    summary="Get a design by ID",
    description="Retrieve a specific design by its ID",
)
async def get_design(
    design_id: int,
    user_id: CurrentUserId,
    repository: DesignRepository = Depends(get_design_repository),
    project_client: ProjectClient = Depends(get_project_client),
) -> DesignResponse:
    """
    Retrieve a design by ID.

    Args:
        design_id: ID of the design to retrieve
        user_id: Current authenticated user ID
        repository: Design repository
        project_client: Project service client

    Returns:
        Design data

    Raises:
        401: If authentication fails
        403: If user doesn't have access to the project
        404: If design not found
    """
    # Get design
    design = repository.get_design_by_id(design_id, include_archived=False)

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

    return DesignResponse.model_validate(design)


@router.get(
    "/{design_id}/visual-status",
    summary="Get visual generation status",
    description="Get the current status of visual generation for a design",
)
async def get_visual_status(
    design_id: int,
    user_id: CurrentUserId,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    Get visual generation status for a design.

    This endpoint provides detailed information about the visual generation process:
    - Current status (not_requested, pending, processing, completed, failed)
    - Available visual URLs (floor_plan_url, rendering_url, model_3d_url)
    - Generation metadata (timestamps, error messages, progress)
    - Cost and timing information

    Args:
        design_id: ID of the design
        user_id: Current authenticated user ID
        db: Database session

    Returns:
        Dictionary containing:
            - status: Current visual generation status
            - visuals: Available visual URLs and metadata
            - progress: Generation progress information
            - error: Error details if generation failed
            - timestamps: Creation and completion times

    Raises:
        404: If design not found
        403: If user doesn't have access to the design
    """
    repository = DesignRepository(db)

    # Get design and verify access
    design = repository.get_design_by_id(design_id)
    if not design:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Design {design_id} not found",
        )

    # Check authorization
    if design.created_by != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this design",
        )

    # Build visual status response
    visual_status = {
        "design_id": design_id,
        "status": design.visual_generation_status,
        "visuals": {
            "floor_plan": {
                "url": design.floor_plan_url,
                "available": design.floor_plan_url is not None,
            },
            "rendering": {
                "url": design.rendering_url,
                "available": design.rendering_url is not None,
            },
            "model_3d": {
                "url": design.model_file_url,
                "available": design.model_file_url is not None,
            },
        },
        "timestamps": {
            "created_at": design.created_at.isoformat() if design.created_at else None,
            "visual_generated_at": design.visual_generated_at.isoformat()
            if design.visual_generated_at
            else None,
        },
    }

    # Add error information if generation failed
    if design.visual_generation_status == "failed":
        visual_status["error"] = {
            "message": design.visual_generation_error or "Visual generation failed",
            "occurred_at": design.visual_generated_at.isoformat()
            if design.visual_generated_at
            else None,
        }

    # Add progress information based on status
    if design.visual_generation_status == "not_requested":
        visual_status["progress"] = {
            "message": "Visual generation has not been requested for this design",
            "can_request": True,
        }
    elif design.visual_generation_status == "pending":
        visual_status["progress"] = {
            "message": "Visual generation request is queued and will start soon",
            "estimated_completion": "2-5 minutes",
        }
    elif design.visual_generation_status == "processing":
        # Count available visuals to show progress
        completed_visuals = sum(
            [
                1
                for url in [
                    design.floor_plan_url,
                    design.rendering_url,
                    design.model_file_url,
                ]
                if url is not None
            ]
        )
        total_visuals = 3

        visual_status["progress"] = {
            "message": f"Generating visuals... {completed_visuals}/{total_visuals} completed",
            "completed_count": completed_visuals,
            "total_count": total_visuals,
            "percentage": round((completed_visuals / total_visuals) * 100, 1),
            "estimated_completion": "1-3 minutes remaining",
        }
    elif design.visual_generation_status == "completed":
        completed_visuals = sum(
            [
                1
                for url in [
                    design.floor_plan_url,
                    design.rendering_url,
                    design.model_file_url,
                ]
                if url is not None
            ]
        )

        visual_status["progress"] = {
            "message": f"Visual generation completed successfully",
            "completed_count": completed_visuals,
            "total_count": 3,
            "percentage": 100.0,
        }

    return visual_status


@router.put(
    "/{design_id}",
    response_model=DesignResponse,
    summary="Update a design",
    description="Update an existing design's properties",
)
async def update_design(
    design_id: int,
    request: DesignUpdateRequest,
    user_id: CurrentUserId,
    repository: DesignRepository = Depends(get_design_repository),
    project_client: ProjectClient = Depends(get_project_client),
) -> DesignResponse:
    """
    Update a design.

    Args:
        design_id: ID of the design to update
        request: Update request with fields to change
        user_id: Current authenticated user ID
        repository: Design repository
        project_client: Project service client

    Returns:
        Updated design data

    Raises:
        401: If authentication fails
        403: If user doesn't have access to the project
        404: If design not found
        422: If request validation fails
    """
    # Get design
    design = repository.get_design_by_id(design_id, include_archived=False)

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

    # Update design
    update_data = request.model_dump(exclude_unset=True)
    updated_design = repository.update_design(design_id, **update_data)

    return DesignResponse.model_validate(updated_design)


@router.delete(
    "/{design_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a design",
    description="Soft delete a design (marks as archived)",
)
async def delete_design(
    design_id: int,
    user_id: CurrentUserId,
    repository: DesignRepository = Depends(get_design_repository),
    project_client: ProjectClient = Depends(get_project_client),
) -> None:
    """
    Delete a design (soft delete).

    Args:
        design_id: ID of the design to delete
        user_id: Current authenticated user ID
        repository: Design repository
        project_client: Project service client

    Raises:
        401: If authentication fails
        403: If user doesn't have access to the project
        404: If design not found
    """
    # Get design
    design = repository.get_design_by_id(design_id, include_archived=False)

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

    # Soft delete design
    repository.delete_design(design_id)


@router.get(
    "/",
    response_model=List[DesignResponse],
    summary="List designs",
    description="List designs with optional filters and pagination",
)
async def list_designs(
    user_id: CurrentUserId,
    project_id: Optional[int] = Query(None, description="Filter by project ID"),
    building_type: Optional[str] = Query(None, description="Filter by building type"),
    status: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(50, ge=1, le=100, description="Maximum number of results"),
    offset: int = Query(0, ge=0, description="Number of results to skip"),
    repository: DesignRepository = Depends(get_design_repository),
    project_client: ProjectClient = Depends(get_project_client),
) -> List[DesignResponse]:
    """
    List designs with filters and pagination.

    Args:
        user_id: Current authenticated user ID
        project_id: Optional filter by project ID
        building_type: Optional filter by building type
        status: Optional filter by status
        limit: Maximum number of results (default 50, max 100)
        offset: Number of results to skip (for pagination)
        repository: Design repository
        project_client: Project service client

    Returns:
        List of designs matching the filters

    Raises:
        401: If authentication fails
        403: If user doesn't have access to filtered project
    """
    # If filtering by project, verify access
    if project_id:
        try:
            await project_client.verify_project_access(
                project_id=project_id,
                user_id=user_id,
            )
        except ProjectAccessDeniedError:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied to project {project_id}",
            )
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Unable to verify project access",
            )

    # Get designs
    designs = repository.list_designs(
        project_id=project_id,
        building_type=building_type,
        status=status,
        limit=limit,
        offset=offset,
    )

    return [DesignResponse.model_validate(design) for design in designs]


@router.post(
    "/{design_id}/generate-visuals",
    response_model=Dict[str, Any],
    status_code=status.HTTP_202_ACCEPTED,
    summary="Generate visuals for an existing design",
    description="Trigger visual generation (floor plans, renderings, 3D models) for an existing design",
)
async def generate_visuals(
    design_id: int,
    request: GenerateVisualsRequest,
    user_id: CurrentUserId,
    repository: DesignRepository = Depends(get_design_repository),
    project_client: ProjectClient = Depends(get_project_client),
) -> Dict[str, Any]:
    """
    Generate visuals for an existing design.

    This endpoint:
    1. Verifies the design exists and user has access
    2. Validates the design is in a suitable state for visual generation
    3. Triggers async visual generation with specified parameters
    4. Returns task information for tracking progress

    Args:
        design_id: ID of the design to generate visuals for
        request: Visual generation request with options
        user_id: Current authenticated user ID
        repository: Design repository
        project_client: Project service client

    Returns:
        Dictionary containing task information and generation details

    Raises:
        401: If authentication fails
        403: If user doesn't have access to the project
        404: If design not found
        409: If design is already processing visuals
        422: If request validation fails
        500: If task creation fails
    """
    # Get design
    design = repository.get_design_by_id(design_id, include_archived=False)

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

    # Check if visual generation is already in progress
    if design.visual_generation_status == "processing":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Visual generation is already in progress for this design",
        )

    # Validate visual types
    valid_visual_types = ["floor_plan", "rendering", "3d_model"]
    invalid_types = [vt for vt in request.visual_types if vt not in valid_visual_types]
    if invalid_types:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid visual types: {invalid_types}. Valid types: {valid_visual_types}",
        )

    # Validate size parameter
    valid_sizes = ["1024x1024", "1792x1024", "1024x1792"]
    if request.size not in valid_sizes:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid size: {request.size}. Valid sizes: {valid_sizes}",
        )

    # Validate quality parameter
    valid_qualities = ["standard", "hd"]
    if request.quality not in valid_qualities:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid quality: {request.quality}. Valid qualities: {valid_qualities}",
        )

    try:
        # Prepare design data for visual generation
        design_data = {
            "building_type": design.building_type,
            "description": design.description,
            "requirements": design.specification or {},
            "style": getattr(design, "style", None),
            "materials": design.materials or [],
        }

        # Update design status to indicate visual generation is starting
        repository.update_design(design_id, visual_generation_status="pending")

        # Start visual generation task asynchronously
        task = generate_visuals_task.delay(
            design_id=str(design_id),
            design_data=design_data,
            visual_types=request.visual_types,
            size=request.size,
            quality=request.quality,
            priority=request.priority,
        )

        import logging

        logger = logging.getLogger(__name__)
        logger.info(
            f"Visual generation task started for design {design_id}. "
            f"Task ID: {task.id}, Types: {request.visual_types}, "
            f"Size: {request.size}, Quality: {request.quality}"
        )

        return {
            "message": "Visual generation started successfully",
            "design_id": design_id,
            "task_id": task.id,
            "visual_types": request.visual_types,
            "size": request.size,
            "quality": request.quality,
            "priority": request.priority,
            "status": "pending",
            "estimated_completion_time": "2-5 minutes",
            "tracking_url": f"/api/v1/tasks/{task.id}",
        }

    except Exception as e:
        # Update design status to failed if task creation fails
        try:
            repository.update_design(design_id, visual_generation_status="failed")
        except Exception:
            pass  # Don't fail if we can't update status

        import logging

        logger = logging.getLogger(__name__)
        logger.error(f"Failed to start visual generation for design {design_id}: {e}")

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start visual generation: {str(e)}",
        )
