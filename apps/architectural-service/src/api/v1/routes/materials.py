"""Material specification API endpoints."""

import logging
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from src.api.v1.dependencies import require_authentication
from src.api.v1.schemas.analysis import (MaterialSpecificationRequest,
                                         MaterialSpecificationResponse)
from src.core.config import settings
from src.core.database import get_db
from src.core.exceptions import (ArchitecturalServiceException, NotFoundError,
                                 ValidationError)
from src.infrastructure.vendor_service_client import VendorServiceClient
from src.repositories.design_repository import DesignRepository
from src.repositories.material_specification_repository import \
    MaterialSpecificationRepository
from src.services.material_service import MaterialService

logger = logging.getLogger(__name__)

router = APIRouter()


# Dependency to get material service
async def get_material_service(
    db: AsyncSession = Depends(get_db),
) -> MaterialService:
    """Get material service instance."""
    material_repository = MaterialSpecificationRepository(db)
    design_repository = DesignRepository(db)
    vendor_client = VendorServiceClient(settings.vendor_service_url)
    return MaterialService(material_repository, design_repository, vendor_client)


@router.post(
    "/designs/{design_id}/materials",
    response_model=MaterialSpecificationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add material specification",
    description="Add a material specification to a design",
)
async def add_material_specification(
    design_id: UUID,
    request: MaterialSpecificationRequest,
    user_id: UUID = Depends(require_authentication),
    material_service: MaterialService = Depends(get_material_service),
) -> MaterialSpecificationResponse:
    """
    Add a material specification to a design.

    Creates a material specification with vendor information and cost estimates.
    """
    try:
        material_spec = await material_service.add_material(
            design_id=design_id,
            data=request,
        )

        return MaterialSpecificationResponse(
            id=UUID(material_spec.id),
            design_id=UUID(material_spec.design_id),
            category=material_spec.category,
            properties=material_spec.properties,
            vendor_info=material_spec.vendor_info,
            cost_estimate=material_spec.cost_estimate,
            design_elements=material_spec.design_elements,
            created_at=material_spec.created_at,
            updated_at=material_spec.updated_at,
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
        logger.error(f"Unexpected error adding material specification: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "Internal server error"},
        )


@router.get(
    "/designs/{design_id}/materials",
    response_model=List[MaterialSpecificationResponse],
    summary="List material specifications",
    description="List all material specifications for a design",
)
async def list_material_specifications(
    design_id: UUID,
    category: str = Query(None, description="Filter by material category"),
    material_service: MaterialService = Depends(get_material_service),
) -> List[MaterialSpecificationResponse]:
    """
    List all material specifications for a design.

    Returns all materials optionally filtered by category.
    """
    try:
        material_specs = await material_service.list_materials_for_design(
            design_id=design_id,
            category=category,
        )

        return [
            MaterialSpecificationResponse(
                id=UUID(spec.id),
                design_id=UUID(spec.design_id),
                category=spec.category,
                properties=spec.properties,
                vendor_info=spec.vendor_info,
                cost_estimate=spec.cost_estimate,
                design_elements=spec.design_elements,
                created_at=spec.created_at,
                updated_at=spec.updated_at,
            )
            for spec in material_specs
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
        logger.error(f"Unexpected error listing materials for design {design_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "Internal server error"},
        )


@router.get(
    "/materials/search",
    response_model=List[MaterialSpecificationResponse],
    summary="Search materials",
    description="Search for materials across all designs with vendor information",
)
async def search_materials(
    query: str = Query(..., description="Search query for materials"),
    category: str = Query(None, description="Filter by material category"),
    limit: int = Query(50, description="Maximum number of results", le=100),
    material_service: MaterialService = Depends(get_material_service),
) -> List[MaterialSpecificationResponse]:
    """
    Search for materials across all designs.

    Returns materials matching the search query with vendor information.
    """
    try:
        material_specs = await material_service.search_materials(
            query=query,
            category=category,
            limit=limit,
        )

        return [
            MaterialSpecificationResponse(
                id=UUID(spec.id),
                design_id=UUID(spec.design_id),
                category=spec.category,
                properties=spec.properties,
                vendor_info=spec.vendor_info,
                cost_estimate=spec.cost_estimate,
                design_elements=spec.design_elements,
                created_at=spec.created_at,
                updated_at=spec.updated_at,
            )
            for spec in material_specs
        ]

    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": e.message, "details": e.details},
        )
    except ArchitecturalServiceException as e:
        raise HTTPException(
            status_code=e.status_code,
            detail={"error": e.message, "details": e.details},
        )
    except Exception as e:
        logger.error(f"Unexpected error searching materials: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "Internal server error"},
        )
