"""
Validation API routes.

This module provides REST API endpoints for:
- Validating designs against building codes
- Retrieving validation history for designs
"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ....infrastructure.database import get_db
from ....repositories.design_repository import DesignRepository
from ....repositories.validation_repository import ValidationRepository
from ....services.validation_service import ValidationService
from ....services.project_client import ProjectClient, ProjectAccessDeniedError
from ...dependencies import CurrentUserId, get_current_user_id
from ..schemas.requests import ValidationRequest
from ..schemas.responses import ValidationResponse

router = APIRouter(prefix="/designs", tags=["validations"])


def get_design_repository(db: Session = Depends(get_db)) -> DesignRepository:
    """Dependency to get design repository instance."""
    return DesignRepository(db)


def get_validation_repository(db: Session = Depends(get_db)) -> ValidationRepository:
    """Dependency to get validation repository instance."""
    return ValidationRepository(db)


def get_project_client() -> ProjectClient:
    """Dependency to get project client instance."""
    return ProjectClient()


def get_validation_service(
    db: Session = Depends(get_db),
) -> ValidationService:
    """Dependency to get validation service instance."""
    validation_repository = ValidationRepository(db)
    design_repository = DesignRepository(db)
    
    return ValidationService(
        validation_repo=validation_repository,
        design_repo=design_repository,
    )


@router.post(
    "/{design_id}/validate",
    response_model=ValidationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Validate a design",
    description="Validate a design against building code rules",
)
async def validate_design(
    design_id: int,
    request: ValidationRequest,
    user_id: CurrentUserId,
    design_repository: DesignRepository = Depends(get_design_repository),
    validation_service: ValidationService = Depends(get_validation_service),
    project_client: ProjectClient = Depends(get_project_client),
) -> ValidationResponse:
    """
    Validate a design against building code rules.
    
    This endpoint:
    1. Verifies the design exists and is not archived
    2. Verifies user has access to the project
    3. Loads the specified rule set
    4. Runs validation rules against the design
    5. Creates and stores validation results
    6. Updates design status based on validation outcome
    
    Args:
        design_id: ID of the design to validate
        request: Validation request with validation_type and rule_set
        user_id: Current authenticated user ID
        design_repository: Design repository
        validation_service: Validation service
        project_client: Project service client
        
    Returns:
        Validation results with compliance status, violations, and warnings
        
    Raises:
        401: If authentication fails
        403: If user doesn't have access to the project
        404: If design not found or rule set not found
        422: If request validation fails
        500: If validation processing fails
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
    
    # Validate design
    try:
        validation = validation_service.validate_design(
            design=design,
            validation_type=request.validation_type,
            rule_set=request.rule_set,
            user_id=user_id,
        )
        
        return ValidationResponse.model_validate(validation)
        
    except FileNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Rule set not found: {str(e)}",
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid rule set format: {str(e)}",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Validation failed: {str(e)}",
        )


@router.get(
    "/{design_id}/validations",
    response_model=List[ValidationResponse],
    summary="Get validation history",
    description="Retrieve all validation results for a design",
)
async def get_validations(
    design_id: int,
    user_id: CurrentUserId,
    design_repository: DesignRepository = Depends(get_design_repository),
    validation_repository: ValidationRepository = Depends(get_validation_repository),
    project_client: ProjectClient = Depends(get_project_client),
) -> List[ValidationResponse]:
    """
    Get validation history for a design.
    
    Returns all validation results for the specified design,
    ordered by validation date (newest first).
    
    Args:
        design_id: ID of the design to get validations for
        user_id: Current authenticated user ID
        design_repository: Design repository
        validation_repository: Validation repository
        project_client: Project service client
        
    Returns:
        List of validation results ordered by validated_at descending
        
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
    
    # Get validations
    validations = validation_repository.get_validations_by_design_id(design_id)
    
    return [ValidationResponse.model_validate(validation) for validation in validations]
