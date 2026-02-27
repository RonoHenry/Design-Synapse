"""Project-related API routes."""

import logging
from typing import Any, Dict
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from src.core.config import settings
from src.core.database import get_db
from src.core.exceptions import NotFoundError, ValidationError
from src.infrastructure.project_service_client import ProjectServiceClient
from src.repositories.design_repository import DesignRepository
from src.services.design_service import DesignService

logger = logging.getLogger(__name__)

router = APIRouter()


# Dependency to get design service
async def get_design_service(
    db: AsyncSession = Depends(get_db),
) -> DesignService:
    """Get design service instance."""
    design_repository = DesignRepository(db)
    project_client = ProjectServiceClient(settings.project_service_url)
    return DesignService(design_repository, project_client)


@router.get("/projects/{project_id}/summary")
async def get_project_summary(
    project_id: UUID,
    design_service: DesignService = Depends(get_design_service),
) -> Dict[str, Any]:
    """
    Get project summary with design count, compliance status, and completion percentage.

    Args:
        project_id: Project ID to get summary for
        design_service: Design service dependency

    Returns:
        Project summary with design statistics

    Raises:
        404: If project not found
        500: If calculation fails
    """
    try:
        summary = await design_service.calculate_project_summary(project_id)
        return summary
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=e.message)
    except Exception as e:
        logger.error(f"Failed to calculate project summary for {project_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to calculate project summary",
        )


@router.post("/projects/{project_id}/archive")
async def cascade_archive_project_designs(
    project_id: UUID,
    user_id: UUID,
    design_service: DesignService = Depends(get_design_service),
) -> Dict[str, Any]:
    """
    Archive all designs when a project is archived.

    This endpoint should be called by the Project Service when a project
    is archived to cascade the archive operation to all associated designs.

    Args:
        project_id: Project ID that was archived
        user_id: User ID who initiated the archive
        design_service: Design service dependency

    Returns:
        Archive operation results

    Raises:
        404: If project not found
        500: If archive operation fails
    """
    try:
        result = await design_service.cascade_archive_designs(project_id, user_id)
        return result
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=e.message)
    except Exception as e:
        logger.error(f"Failed to cascade archive for project {project_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to archive project designs",
        )
