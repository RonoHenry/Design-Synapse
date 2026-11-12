"""Design management API endpoints."""

import logging
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from src.api.v1.dependencies import require_authentication
from src.api.v1.schemas.base import PaginationParams
from src.api.v1.schemas.design import (CreateDesignRequest,
                                       DesignDetailResponse,
                                       DesignListResponse, DesignResponse,
                                       DesignVersionDetailResponse,
                                       DesignVersionResponse,
                                       UpdateDesignRequest)
from src.core.config import settings
from src.core.database import get_db
from src.core.exceptions import (ArchitecturalServiceException, ConflictError,
                                 NotFoundError, ValidationError)
from src.core.pagination import create_pagination_params
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


@router.post(
    "/designs",
    response_model=DesignResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new design document",
    description="Create a new architectural design document with version 1.0",
    responses={
        201: {
            "description": "Design document created successfully",
            "content": {
                "application/json": {
                    "example": {
                        "id": "550e8400-e29b-41d4-a716-446655440000",
                        "project_id": "660e8400-e29b-41d4-a716-446655440000",
                        "name": "Downtown Office Building",
                        "building_type": "commercial",
                        "current_version": "1.0",
                        "version_number": 1,
                        "status": "draft",
                        "created_by": "770e8400-e29b-41d4-a716-446655440000",
                        "created_at": "2024-01-15T10:30:00Z",
                        "updated_at": "2024-01-15T10:30:00Z",
                    }
                }
            },
        },
        400: {
            "description": "Invalid input data",
            "content": {
                "application/json": {
                    "example": {
                        "error": {
                            "code": "VALIDATION_ERROR",
                            "message": "Input validation failed",
                            "details": {
                                "validation_errors": [
                                    {
                                        "field": "name",
                                        "message": "Field required",
                                        "type": "missing",
                                    }
                                ]
                            },
                            "timestamp": "2024-01-15T10:30:00Z",
                            "request_id": "abc123",
                        }
                    }
                }
            },
        },
        401: {
            "description": "Authentication required",
            "content": {
                "application/json": {
                    "example": {
                        "error": {
                            "code": "UNAUTHORIZED",
                            "message": "Authentication required",
                            "details": {},
                            "timestamp": "2024-01-15T10:30:00Z",
                            "request_id": "abc123",
                        }
                    }
                }
            },
        },
        404: {
            "description": "Project not found",
            "content": {
                "application/json": {
                    "example": {
                        "error": {
                            "code": "NOT_FOUND",
                            "message": "Project not found",
                            "details": {
                                "project_id": "660e8400-e29b-41d4-a716-446655440000"
                            },
                            "timestamp": "2024-01-15T10:30:00Z",
                            "request_id": "abc123",
                        }
                    }
                }
            },
        },
        500: {
            "description": "Internal server error",
            "content": {
                "application/json": {
                    "example": {
                        "error": {
                            "code": "INTERNAL_ERROR",
                            "message": "An unexpected error occurred",
                            "details": {},
                            "timestamp": "2024-01-15T10:30:00Z",
                            "request_id": "abc123",
                        }
                    }
                }
            },
        },
    },
)
async def create_design(
    request: CreateDesignRequest,
    user_id: UUID = Depends(require_authentication),
    design_service: DesignService = Depends(get_design_service),
) -> DesignResponse:
    """
    Create a new architectural design document.

    Creates a design with version 1.0 and validates project access.

    **Parameters:**
    - **request**: Design creation data including project_id, name, building_type, location
    - **user_id**: Authenticated user ID (from JWT token)

    **Returns:**
    - Design document with unique ID and version 1.0

    **Errors:**
    - **400**: Invalid input data or validation failure
    - **401**: Missing or invalid authentication token
    - **404**: Project not found or user lacks access
    - **500**: Internal server error
    """
    try:
        design = await design_service.create_design(
            project_id=request.project_id,
            user_id=user_id,
            data=request,
        )

        return DesignResponse(
            id=UUID(design.id),
            project_id=UUID(design.project_id),
            name=design.name,
            building_type=design.building_type,
            current_version=design.current_version,
            version_number=design.version_number,
            status=design.status,
            created_by=UUID(design.created_by),
            created_at=design.created_at,
            updated_at=design.updated_at,
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
        logger.error(f"Unexpected error creating design: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "Internal server error"},
        )


@router.get(
    "/designs",
    response_model=DesignListResponse,
    summary="List design documents",
    description="List design documents with cursor-based pagination",
    responses={
        200: {
            "description": "List of design documents",
            "content": {
                "application/json": {
                    "example": {
                        "items": [
                            {
                                "id": "550e8400-e29b-41d4-a716-446655440000",
                                "project_id": "660e8400-e29b-41d4-a716-446655440000",
                                "name": "Downtown Office Building",
                                "building_type": "commercial",
                                "current_version": "2.0",
                                "version_number": 2,
                                "status": "draft",
                                "created_by": "770e8400-e29b-41d4-a716-446655440000",
                                "created_at": "2024-01-15T10:30:00Z",
                                "updated_at": "2024-01-16T14:20:00Z",
                            }
                        ],
                        "has_next": True,
                        "next_cursor": "eyJpZCI6IjU1MGU4NDAwLWUyOWItNDFkNC1hNzE2LTQ0NjY1NTQ0MDAwMCJ9",
                        "total_count": 42,
                        "page_info": {
                            "limit": 20,
                            "sort_field": "created_at",
                            "sort_direction": "desc",
                        },
                    }
                }
            },
        },
        400: {"description": "Invalid pagination parameters"},
        500: {"description": "Internal server error"},
    },
)
async def list_designs(
    project_id: Optional[UUID] = Query(None, description="Filter by project ID"),
    limit: int = Query(20, description="Number of items per page", ge=1, le=100),
    cursor: Optional[str] = Query(None, description="Cursor for pagination"),
    sort_field: Optional[str] = Query(
        None, description="Field to sort by (defaults to created_at)"
    ),
    sort_direction: str = Query(
        "desc", description="Sort direction (asc or desc)", pattern="^(asc|desc)$"
    ),
    include_deleted: bool = Query(False, description="Include soft-deleted designs"),
    include_total: bool = Query(False, description="Include total count in response"),
    design_service: DesignService = Depends(get_design_service),
) -> DesignListResponse:
    """
    List design documents with pagination.

    Returns paginated list of designs with optional filtering by project.

    **Query Parameters:**
    - **project_id**: Filter designs by project (optional)
    - **limit**: Number of items per page (1-100, default: 20)
    - **cursor**: Pagination cursor from previous response
    - **sort_field**: Field to sort by (default: created_at)
    - **sort_direction**: Sort direction - asc or desc (default: desc)
    - **include_deleted**: Include soft-deleted designs (default: false)
    - **include_total**: Include total count (default: false, may impact performance)

    **Returns:**
    - Paginated list of design documents with navigation cursors

    **Errors:**
    - **400**: Invalid pagination parameters
    - **500**: Internal server error
    """
    try:
        # Create pagination parameters
        params = create_pagination_params(
            limit=limit,
            cursor=cursor,
            sort_field=sort_field,
            sort_direction=sort_direction,
        )

        # Get paginated designs
        paginated_designs = await design_service.list_designs(
            params=params,
            project_id=project_id,
            include_deleted=include_deleted,
            include_total=include_total,
        )

        # Convert to response format
        design_responses = [
            DesignResponse(
                id=UUID(design.id),
                project_id=UUID(design.project_id),
                name=design.name,
                building_type=design.building_type,
                current_version=design.current_version,
                version_number=design.version_number,
                status=design.status,
                created_by=UUID(design.created_by),
                created_at=design.created_at,
                updated_at=design.updated_at,
            )
            for design in paginated_designs.items
        ]

        return DesignListResponse(
            items=design_responses,
            has_next=paginated_designs.has_next,
            next_cursor=paginated_designs.next_cursor,
            total_count=paginated_designs.total_count,
            page_info=paginated_designs.page_info,
        )

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
        logger.error(f"Unexpected error listing designs: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "Internal server error"},
        )


@router.get(
    "/designs/{design_id}",
    response_model=DesignDetailResponse,
    summary="Get a design document",
    description="Retrieve a design document with detailed information",
    responses={
        200: {
            "description": "Design document details",
            "content": {
                "application/json": {
                    "example": {
                        "id": "550e8400-e29b-41d4-a716-446655440000",
                        "project_id": "660e8400-e29b-41d4-a716-446655440000",
                        "name": "Downtown Office Building",
                        "description": "Modern 10-story office building",
                        "building_type": "commercial",
                        "location": {
                            "address": "123 Main St",
                            "city": "Seattle",
                            "state": "WA",
                        },
                        "current_version": "2.0",
                        "version_number": 2,
                        "status": "draft",
                        "metadata": {},
                        "is_deleted": False,
                        "deleted_at": None,
                        "drawing_count": 5,
                        "material_count": 12,
                        "compliance_check_count": 2,
                        "created_by": "770e8400-e29b-41d4-a716-446655440000",
                        "created_at": "2024-01-15T10:30:00Z",
                        "updated_at": "2024-01-16T14:20:00Z",
                    }
                }
            },
        },
        404: {"description": "Design not found"},
        500: {"description": "Internal server error"},
    },
)
async def get_design(
    design_id: UUID,
    version: Optional[str] = Query(
        None, description="Specific version to retrieve (e.g., '1.0', '2.0')"
    ),
    design_service: DesignService = Depends(get_design_service),
) -> DesignDetailResponse:
    """
    Retrieve a design document.

    Returns detailed design information including metadata and related counts.

    **Path Parameters:**
    - **design_id**: Unique identifier of the design document

    **Query Parameters:**
    - **version**: Specific version to retrieve (optional, defaults to current version)

    **Returns:**
    - Complete design document with all details and related entity counts

    **Errors:**
    - **404**: Design or version not found
    - **500**: Internal server error
    """
    try:
        design = await design_service.get_design(design_id, version)

        # TODO: Get actual counts from repositories
        drawing_count = 0
        material_count = 0
        compliance_check_count = 0

        return DesignDetailResponse(
            id=UUID(design.id),
            project_id=UUID(design.project_id),
            name=design.name,
            description=design.description,
            building_type=design.building_type,
            location=design.location_data,
            current_version=design.current_version,
            version_number=design.version_number,
            status=design.status,
            metadata=design.metadata,
            is_deleted=design.is_deleted,
            deleted_at=design.deleted_at,
            drawing_count=drawing_count,
            material_count=material_count,
            compliance_check_count=compliance_check_count,
            created_by=UUID(design.created_by),
            created_at=design.created_at,
            updated_at=design.updated_at,
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
        logger.error(f"Unexpected error retrieving design {design_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "Internal server error"},
        )


@router.put(
    "/designs/{design_id}",
    response_model=DesignResponse,
    summary="Update a design document",
    description="Update a design document and create a new version",
    responses={
        200: {
            "description": "Design updated successfully",
            "content": {
                "application/json": {
                    "example": {
                        "id": "550e8400-e29b-41d4-a716-446655440000",
                        "project_id": "660e8400-e29b-41d4-a716-446655440000",
                        "name": "Downtown Office Building - Updated",
                        "building_type": "commercial",
                        "current_version": "2.0",
                        "version_number": 2,
                        "status": "draft",
                        "created_by": "770e8400-e29b-41d4-a716-446655440000",
                        "created_at": "2024-01-15T10:30:00Z",
                        "updated_at": "2024-01-16T14:20:00Z",
                    }
                }
            },
        },
        400: {"description": "Invalid input data"},
        404: {"description": "Design not found"},
        409: {"description": "Version conflict - design was modified by another user"},
        500: {"description": "Internal server error"},
    },
)
async def update_design(
    design_id: UUID,
    request: UpdateDesignRequest,
    user_id: UUID = Depends(require_authentication),
    design_service: DesignService = Depends(get_design_service),
) -> DesignResponse:
    """
    Update a design document.

    Creates a new version with incremented version number.

    **Path Parameters:**
    - **design_id**: Unique identifier of the design document

    **Parameters:**
    - **request**: Updated design data
    - **user_id**: Authenticated user ID (from JWT token)

    **Returns:**
    - Updated design document with new version number

    **Errors:**
    - **400**: Invalid input data
    - **404**: Design not found
    - **409**: Version conflict (optimistic locking failure)
    - **500**: Internal server error
    """
    try:
        design = await design_service.update_design(
            design_id=design_id,
            user_id=user_id,
            data=request,
        )

        return DesignResponse(
            id=UUID(design.id),
            project_id=UUID(design.project_id),
            name=design.name,
            building_type=design.building_type,
            current_version=design.current_version,
            version_number=design.version_number,
            status=design.status,
            created_by=UUID(design.created_by),
            created_at=design.created_at,
            updated_at=design.updated_at,
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
    except ConflictError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error": e.message, "details": e.details},
        )
    except ArchitecturalServiceException as e:
        raise HTTPException(
            status_code=e.status_code,
            detail={"error": e.message, "details": e.details},
        )
    except Exception as e:
        logger.error(f"Unexpected error updating design {design_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "Internal server error"},
        )


@router.delete(
    "/designs/{design_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Soft delete a design document",
    description="Soft delete a design document (preserves data for audit)",
    responses={
        204: {"description": "Design deleted successfully"},
        404: {"description": "Design not found"},
        500: {"description": "Internal server error"},
    },
)
async def delete_design(
    design_id: UUID,
    user_id: UUID = Depends(require_authentication),
    design_service: DesignService = Depends(get_design_service),
) -> None:
    """
    Soft delete a design document.

    Sets is_deleted=True and deleted_at timestamp without removing data.

    **Path Parameters:**
    - **design_id**: Unique identifier of the design document

    **Parameters:**
    - **user_id**: Authenticated user ID (from JWT token)

    **Returns:**
    - No content (204)

    **Errors:**
    - **404**: Design not found
    - **500**: Internal server error
    """
    try:
        await design_service.soft_delete(design_id, user_id)

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
        logger.error(f"Unexpected error deleting design {design_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "Internal server error"},
        )


@router.get(
    "/designs/{design_id}/versions",
    response_model=List[DesignVersionResponse],
    summary="List design versions",
    description="List all versions of a design document",
    responses={
        200: {
            "description": "List of design versions",
            "content": {
                "application/json": {
                    "example": [
                        {
                            "id": "880e8400-e29b-41d4-a716-446655440000",
                            "design_id": "550e8400-e29b-41d4-a716-446655440000",
                            "version": "1.0",
                            "version_number": 1,
                            "change_summary": "Initial version",
                            "created_by": "770e8400-e29b-41d4-a716-446655440000",
                            "created_at": "2024-01-15T10:30:00Z",
                        },
                        {
                            "id": "990e8400-e29b-41d4-a716-446655440000",
                            "design_id": "550e8400-e29b-41d4-a716-446655440000",
                            "version": "2.0",
                            "version_number": 2,
                            "change_summary": "Updated floor plan layout",
                            "created_by": "770e8400-e29b-41d4-a716-446655440000",
                            "created_at": "2024-01-16T14:20:00Z",
                        },
                    ]
                }
            },
        },
        404: {"description": "Design not found"},
        500: {"description": "Internal server error"},
    },
)
async def list_design_versions(
    design_id: UUID,
    design_service: DesignService = Depends(get_design_service),
) -> List[DesignVersionResponse]:
    """
    List all versions of a design document.

    Returns versions ordered by version number.

    **Path Parameters:**
    - **design_id**: Unique identifier of the design document

    **Returns:**
    - List of all versions with metadata (ordered by version number)

    **Errors:**
    - **404**: Design not found
    - **500**: Internal server error
    """
    try:
        versions = await design_service.list_versions(design_id)

        return [
            DesignVersionResponse(
                id=UUID(version.id),
                design_id=UUID(version.design_id),
                version=version.version,
                version_number=version.version_number,
                change_summary=version.change_summary,
                created_by=UUID(version.created_by),
                created_at=version.created_at,
            )
            for version in versions
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
        logger.error(f"Unexpected error listing versions for design {design_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "Internal server error"},
        )


@router.get(
    "/designs/{design_id}/versions/{version}",
    response_model=DesignVersionDetailResponse,
    summary="Get specific design version",
    description="Retrieve a specific version of a design document with full data",
    responses={
        200: {
            "description": "Design version details with complete snapshot",
            "content": {
                "application/json": {
                    "example": {
                        "id": "880e8400-e29b-41d4-a716-446655440000",
                        "design_id": "550e8400-e29b-41d4-a716-446655440000",
                        "version": "1.0",
                        "version_number": 1,
                        "change_summary": "Initial version",
                        "design_data": {
                            "name": "Downtown Office Building",
                            "building_type": "commercial",
                            "location": {"address": "123 Main St"},
                        },
                        "created_by": "770e8400-e29b-41d4-a716-446655440000",
                        "created_at": "2024-01-15T10:30:00Z",
                    }
                }
            },
        },
        404: {"description": "Design or version not found"},
        500: {"description": "Internal server error"},
    },
)
async def get_design_version(
    design_id: UUID,
    version: str,
    design_service: DesignService = Depends(get_design_service),
) -> DesignVersionDetailResponse:
    """
    Retrieve a specific version of a design document.

    Returns the complete design data snapshot for the specified version.

    **Path Parameters:**
    - **design_id**: Unique identifier of the design document
    - **version**: Version string (e.g., "1.0", "2.0")

    **Returns:**
    - Complete design version with full data snapshot

    **Errors:**
    - **404**: Design or version not found
    - **500**: Internal server error
    """
    try:
        # Get the design at the specific version
        design = await design_service.get_design(design_id, version)

        # Get the version record to get the snapshot data
        versions = await design_service.list_versions(design_id)
        version_record = next((v for v in versions if v.version == version), None)

        if version_record is None:
            raise NotFoundError(
                f"Version {version} not found for design {design_id}",
                details={"design_id": str(design_id), "version": version},
            )

        return DesignVersionDetailResponse(
            id=UUID(version_record.id),
            design_id=UUID(version_record.design_id),
            version=version_record.version,
            version_number=version_record.version_number,
            change_summary=version_record.change_summary,
            design_data=version_record.design_data,
            created_by=UUID(version_record.created_by),
            created_at=version_record.created_at,
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
            f"Unexpected error retrieving version {version} for design {design_id}: {e}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "Internal server error"},
        )
