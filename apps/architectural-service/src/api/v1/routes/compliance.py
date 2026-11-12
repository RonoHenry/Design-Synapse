"""Compliance check API endpoints."""

import logging
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from src.api.v1.dependencies import require_authentication
from src.api.v1.schemas.analysis import (ComplianceCheckRequest,
                                         ComplianceCheckResponse)
from src.core.config import settings
from src.core.database import get_db
from src.core.exceptions import (ArchitecturalServiceException, NotFoundError,
                                 ValidationError)
from src.infrastructure.knowledge_service_client import KnowledgeServiceClient
from src.repositories.compliance_check_repository import \
    ComplianceCheckRepository
from src.repositories.design_repository import DesignRepository
from src.services.compliance_service import ComplianceService

logger = logging.getLogger(__name__)

router = APIRouter()


# Dependency to get compliance service
async def get_compliance_service(
    db: AsyncSession = Depends(get_db),
) -> ComplianceService:
    """Get compliance service instance."""
    compliance_repository = ComplianceCheckRepository(db)
    design_repository = DesignRepository(db)
    knowledge_client = KnowledgeServiceClient(settings.knowledge_service_url)
    return ComplianceService(compliance_repository, design_repository, knowledge_client)


@router.post(
    "/designs/{design_id}/compliance-checks",
    response_model=ComplianceCheckResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Request compliance check",
    description="Request a building code compliance check for a design",
)
async def request_compliance_check(
    design_id: UUID,
    request: ComplianceCheckRequest,
    user_id: UUID = Depends(require_authentication),
    compliance_service: ComplianceService = Depends(get_compliance_service),
) -> ComplianceCheckResponse:
    """
    Request a building code compliance check.

    Initiates compliance checking against specified building codes and standards.
    """
    try:
        compliance_check = await compliance_service.check_compliance(
            design_id=design_id,
            standards=request.code_standards,
            jurisdiction=request.jurisdiction,
        )

        return ComplianceCheckResponse(
            id=UUID(compliance_check.id),
            design_id=UUID(compliance_check.design_id),
            design_version=compliance_check.design_version,
            code_standards=compliance_check.code_standards,
            jurisdiction=compliance_check.jurisdiction,
            status=compliance_check.status,
            passed=compliance_check.passed,
            violations=[],  # Will be populated when check completes
            warnings=[],  # Will be populated when check completes
            recommendations=compliance_check.recommendations,
            report_url=compliance_check.report_url,
            started_at=compliance_check.started_at,
            completed_at=compliance_check.completed_at,
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
        logger.error(f"Unexpected error requesting compliance check: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "Internal server error"},
        )


@router.get(
    "/compliance-checks/{check_id}",
    response_model=ComplianceCheckResponse,
    summary="Get compliance check results",
    description="Retrieve compliance check results and status",
)
async def get_compliance_check(
    check_id: UUID,
    compliance_service: ComplianceService = Depends(get_compliance_service),
) -> ComplianceCheckResponse:
    """
    Get compliance check results.

    Returns detailed compliance check results including violations and warnings.
    """
    try:
        compliance_check = await compliance_service.get_check_results(check_id)

        # Convert violations and warnings from JSON to schema objects
        violations = []
        for violation_data in compliance_check.violations:
            violations.append(
                {
                    "code_section": violation_data.get("code_section", ""),
                    "description": violation_data.get("description", ""),
                    "severity": violation_data.get("severity", ""),
                    "location": violation_data.get("location"),
                    "remediation": violation_data.get("remediation"),
                }
            )

        warnings = []
        for warning_data in compliance_check.warnings:
            warnings.append(
                {
                    "code_section": warning_data.get("code_section", ""),
                    "description": warning_data.get("description", ""),
                    "recommendation": warning_data.get("recommendation"),
                }
            )

        return ComplianceCheckResponse(
            id=UUID(compliance_check.id),
            design_id=UUID(compliance_check.design_id),
            design_version=compliance_check.design_version,
            code_standards=compliance_check.code_standards,
            jurisdiction=compliance_check.jurisdiction,
            status=compliance_check.status,
            passed=compliance_check.passed,
            violations=violations,
            warnings=warnings,
            recommendations=compliance_check.recommendations,
            report_url=compliance_check.report_url,
            started_at=compliance_check.started_at,
            completed_at=compliance_check.completed_at,
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
        logger.error(f"Unexpected error retrieving compliance check {check_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "Internal server error"},
        )


@router.get(
    "/designs/{design_id}/compliance-checks",
    response_model=List[ComplianceCheckResponse],
    summary="List compliance checks",
    description="List all compliance checks for a design",
)
async def list_compliance_checks(
    design_id: UUID,
    compliance_service: ComplianceService = Depends(get_compliance_service),
) -> List[ComplianceCheckResponse]:
    """
    List all compliance checks for a design.

    Returns all compliance checks ordered by creation date.
    """
    try:
        compliance_checks = await compliance_service.list_checks_for_design(design_id)

        return [
            ComplianceCheckResponse(
                id=UUID(check.id),
                design_id=UUID(check.design_id),
                design_version=check.design_version,
                code_standards=check.code_standards,
                jurisdiction=check.jurisdiction,
                status=check.status,
                passed=check.passed,
                violations=[],  # Simplified for list view
                warnings=[],  # Simplified for list view
                recommendations=check.recommendations,
                report_url=check.report_url,
                started_at=check.started_at,
                completed_at=check.completed_at,
            )
            for check in compliance_checks
        ]

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
            f"Unexpected error listing compliance checks for design {design_id}: {e}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "Internal server error"},
        )
