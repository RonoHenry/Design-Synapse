"""Staging and bookmark API routes."""

from typing import Any, Optional


# Mock User model for testing
class User:
    def __init__(self, id: int, username: str, email: str, roles: list = None):
        self.id = id
        self.username = username
        self.email = email
        self.roles = roles or []


from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError
from src.api.dependencies import get_current_user, get_staging_service
from src.api.v1.schemas.staging import (AvailabilityCheck, BookmarkCreate,
                                        BookmarkListResponse, BookmarkResponse,
                                        BookmarkUpdate,
                                        PopularProductsResponse,
                                        ProcurementListResponse,
                                        Products3DResponse, ProductValidation,
                                        StagingCreate, StagingListResponse,
                                        StagingResponse, StagingUpdate)
from src.services.staging_service import StagingService

router = APIRouter()


# Bookmark endpoints
@router.post(
    "/bookmarks", response_model=BookmarkResponse, status_code=status.HTTP_201_CREATED
)
async def create_bookmark(
    bookmark_data: BookmarkCreate,
    current_user: User = Depends(get_current_user),
    staging_service: StagingService = Depends(get_staging_service),
):
    """Bookmark a product for later use."""
    try:
        bookmark = await staging_service.bookmark_product(
            user_id=current_user.id,
            product_id=bookmark_data.product_id,
            notes=bookmark_data.notes,
        )
        return BookmarkResponse.from_orm(bookmark)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except IntegrityError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Product is already bookmarked",
        )


@router.get("/bookmarks", response_model=BookmarkListResponse)
async def get_user_bookmarks(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    current_user: User = Depends(get_current_user),
    staging_service: StagingService = Depends(get_staging_service),
):
    """Get user's bookmarked products."""
    bookmarks = await staging_service.get_user_bookmarks(
        user_id=current_user.id,
        skip=skip,
        limit=limit,
    )

    # Get total count (simplified for now)
    total = len(bookmarks) + skip

    return BookmarkListResponse(
        bookmarks=[BookmarkResponse.from_orm(bookmark) for bookmark in bookmarks],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.put("/bookmarks/{bookmark_id}", response_model=BookmarkResponse)
async def update_bookmark(
    bookmark_id: int,
    bookmark_data: BookmarkUpdate,
    current_user: User = Depends(get_current_user),
    staging_service: StagingService = Depends(get_staging_service),
):
    """Update bookmark notes."""
    try:
        updated_bookmark = await staging_service.update_bookmark_notes(
            user_id=current_user.id,
            bookmark_id=bookmark_id,
            notes=bookmark_data.notes,
        )
        if not updated_bookmark:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Bookmark not found",
            )
        return BookmarkResponse.from_orm(updated_bookmark)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.delete("/bookmarks/{bookmark_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_bookmark(
    bookmark_id: int,
    current_user: User = Depends(get_current_user),
    staging_service: StagingService = Depends(get_staging_service),
):
    """Remove a bookmark."""
    try:
        success = await staging_service.remove_bookmark(
            user_id=current_user.id,
            bookmark_id=bookmark_id,
        )
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Bookmark not found",
            )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


# Staging endpoints
@router.post(
    "/staging", response_model=StagingResponse, status_code=status.HTTP_201_CREATED
)
async def stage_product(
    staging_data: StagingCreate,
    current_user: User = Depends(get_current_user),
    staging_service: StagingService = Depends(get_staging_service),
):
    """Stage a product in a design."""
    try:
        staging = await staging_service.stage_product_in_design(
            design_id=staging_data.design_id,
            product_id=staging_data.product_id,
            position=staging_data.position.dict(),
            rotation=staging_data.rotation.dict() if staging_data.rotation else None,
            scale=staging_data.scale.dict() if staging_data.scale else None,
            quantity=staging_data.quantity,
        )
        return StagingResponse.from_orm(staging)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get("/staging/design/{design_id}", response_model=StagingListResponse)
async def get_design_staging(
    design_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    staging_service: StagingService = Depends(get_staging_service),
):
    """Get all products staged in a design."""
    stagings = await staging_service.get_design_staged_products(
        design_id=design_id,
        skip=skip,
        limit=limit,
    )

    # Get total count (simplified for now)
    total = len(stagings) + skip

    return StagingListResponse(
        stagings=[StagingResponse.from_orm(staging) for staging in stagings],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.put("/staging/{staging_id}", response_model=StagingResponse)
async def update_staging(
    staging_id: int,
    staging_data: StagingUpdate,
    current_user: User = Depends(get_current_user),
    staging_service: StagingService = Depends(get_staging_service),
):
    """Update product staging parameters."""
    try:
        updated_staging = await staging_service.update_product_staging(
            staging_id=staging_id,
            position=staging_data.position.dict() if staging_data.position else None,
            rotation=staging_data.rotation.dict() if staging_data.rotation else None,
            scale=staging_data.scale.dict() if staging_data.scale else None,
            quantity=staging_data.quantity,
        )
        if not updated_staging:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Staging not found",
            )
        return StagingResponse.from_orm(updated_staging)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.delete(
    "/staging/design/{design_id}/product/{product_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def remove_product_from_design(
    design_id: int,
    product_id: int,
    current_user: User = Depends(get_current_user),
    staging_service: StagingService = Depends(get_staging_service),
):
    """Remove a product from design staging."""
    success = await staging_service.remove_product_from_design(
        design_id=design_id,
        product_id=product_id,
    )
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Staged product not found",
        )


# Procurement endpoints
@router.get(
    "/staging/design/{design_id}/procurement", response_model=ProcurementListResponse
)
async def get_procurement_list(
    design_id: int,
    include_pricing: bool = Query(True),
    staging_service: StagingService = Depends(get_staging_service),
):
    """Generate procurement list for a design."""
    procurement_list = await staging_service.generate_procurement_list(
        design_id=design_id,
        include_pricing=include_pricing,
    )

    return ProcurementListResponse(**procurement_list)


@router.get("/staging/design/{design_id}/cost")
async def get_design_cost(
    design_id: int,
    staging_service: StagingService = Depends(get_staging_service),
):
    """Get total cost of all staged products in a design."""
    total_cost = await staging_service.get_design_total_cost(design_id)

    return {
        "design_id": design_id,
        "total_cost": total_cost,
    }


@router.get(
    "/staging/design/{design_id}/availability", response_model=AvailabilityCheck
)
async def check_design_availability(
    design_id: int,
    staging_service: StagingService = Depends(get_staging_service),
):
    """Check availability of all staged products in a design."""
    availability = await staging_service.check_design_availability(design_id)

    return AvailabilityCheck(**availability)


# Product discovery endpoints
@router.get("/products/3d-models", response_model=Products3DResponse)
async def get_products_with_3d_models(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    category: Optional[str] = Query(None),
    staging_service: StagingService = Depends(get_staging_service),
):
    """Get products that have 3D models for staging."""
    products = await staging_service.get_products_with_3d_models(
        skip=skip,
        limit=limit,
        category=category,
    )

    # Get total count (simplified for now)
    total = len(products) + skip

    return Products3DResponse(
        products=products,
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get("/products/{product_id}/validate-staging", response_model=ProductValidation)
async def validate_product_for_staging(
    product_id: int,
    staging_service: StagingService = Depends(get_staging_service),
):
    """Validate if a product can be staged in designs."""
    validation = await staging_service.validate_product_for_staging(product_id)

    return ProductValidation(**validation)


# Analytics endpoints
@router.get("/bookmarks/popular", response_model=PopularProductsResponse)
async def get_popular_bookmarked_products(
    limit: int = Query(10, ge=1, le=100),
    category: Optional[str] = Query(None),
    staging_service: StagingService = Depends(get_staging_service),
):
    """Get most bookmarked products."""
    products = await staging_service.get_popular_bookmarked_products(
        limit=limit,
        category=category,
    )

    return PopularProductsResponse(
        products=products,
        limit=limit,
        category=category,
    )


@router.get("/staging/popular", response_model=PopularProductsResponse)
async def get_most_staged_products(
    limit: int = Query(10, ge=1, le=100),
    category: Optional[str] = Query(None),
    staging_service: StagingService = Depends(get_staging_service),
):
    """Get most frequently staged products."""
    products = await staging_service.get_most_staged_products(
        limit=limit,
        category=category,
    )

    return PopularProductsResponse(
        products=products,
        limit=limit,
        category=category,
    )
