"""Accessibility check API endpoints."""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from src.api.v1.dependencies import require_authentication
from src.api.v1.schemas.analysis import (AccessibilityCheckRequest,
                                         AccessibilityCheckResponse,
                                         AccessibilityViolation,
                                         RouteValidation)
from src.core.database import get_db
from src.core.exceptions import (ArchitecturalServiceException, NotFoundError,
                                 ValidationError)
from src.repositories.accessibility_check_repository import \
    AccessibilityCheckRepository
from src.repositories.design_repository import DesignRepository
from src.services.accessibility_service import AccessibilityService

logger = logging.getLogger(__name__)

router = APIRouter()


# Dependency to get accessibility service
async def get_accessibility_service(
    db: AsyncSession = Depends(get_db),
) -> AccessibilityService:
    """Get accessibility service instance."""
    accessibility_repository = AccessibilityCheckRepository(db)
    design_repository = DesignRepository(db)
    return AccessibilityService(accessibility_repository, design_repository)


@router.post(
    "/designs/{design_id}/accessibility-checks",
    response_model=AccessibilityCheckResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Request accessibility check",
    description="Request accessibility compliance check for a design",
)
async def request_accessibility_check(
    design_id: UUID,
    request: AccessibilityCheckRequest,
    user_id: UUID = Depends(require_authentication),
    accessibility_service: AccessibilityService = Depends(get_accessibility_service),
) -> AccessibilityCheckResponse:
    """
    Request accessibility compliance check for a design.

    Validates design against ADA, ANSI A117.1, and other accessibility standards.
    Checks door widths, corridor widths, accessible routes, and restroom compliance.
    """
    try:
        accessibility_check = await accessibility_service.check_accessibility(
            design_id=design_id,
            request=request,
        )

        return accessibility_check

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
        logger.error(f"Unexpected error requesting accessibility check: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "Internal server error"},
        )


@router.get(
    "/accessibility-checks/{check_id}",
    response_model=AccessibilityCheckResponse,
    summary="Get accessibility check results",
    description="Get accessibility compliance check results",
)
async def get_accessibility_check_results(
    check_id: UUID,
    accessibility_service: AccessibilityService = Depends(get_accessibility_service),
) -> AccessibilityCheckResponse:
    """
    Get accessibility compliance check results.

    Returns the complete accessibility analysis including violations,
    accessible route validations, and compliance status.
    """
    try:
        accessibility_check = await accessibility_service.accessibility_repository.get(
            str(check_id)
        )

        if accessibility_check is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"error": f"Accessibility check {check_id} not found"},
            )

        # Convert violations from dict to AccessibilityViolation objects
        violations = []
        for violation_data in accessibility_check.violations:
            violation = AccessibilityViolation(
                standard_section=violation_data["standard_section"],
                location=violation_data["location"],
                description=violation_data["description"],
                required_value=violation_data["required_value"],
                actual_value=violation_data["actual_value"],
                remediation=violation_data["remediation"],
            )
            violations.append(violation)

        # Convert accessible routes from dict to RouteValidation objects
        accessible_routes = []
        for route_data in accessibility_check.accessible_routes:
            route = RouteValidation(
                route_id=route_data["route_id"],
                from_location=route_data["from_location"],
                to_location=route_data["to_location"],
                is_accessible=route_data["is_accessible"],
                issues=route_data["issues"],
            )
            accessible_routes.append(route)

        return AccessibilityCheckResponse(
            id=UUID(accessibility_check.id),
            design_id=UUID(accessibility_check.design_id),
            design_version=accessibility_check.design_version,
            standards=accessibility_check.standards,
            status=accessibility_check.status,
            passed=accessibility_check.passed,
            violations=violations,
            accessible_routes=accessible_routes,
            started_at=accessibility_check.started_at,
            completed_at=accessibility_check.completed_at,
        )

    except ArchitecturalServiceException as e:
        raise HTTPException(
            status_code=e.status_code,
            detail={"error": e.message, "details": e.details},
        )
    except Exception as e:
        logger.error(f"Unexpected error getting accessibility check {check_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "Internal server error"},
        )
