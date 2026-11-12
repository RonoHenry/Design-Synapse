"""Review API routes."""

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
from src.api.dependencies import get_current_user, get_review_service
from src.api.v1.schemas.review import (ProductRatingSummary, ReviewCreate,
                                       ReviewListResponse, ReviewModeration,
                                       ReviewResponse, ReviewSearch,
                                       ReviewUpdate, TopRatedProductsResponse,
                                       TopRatedVendorsResponse,
                                       VendorRatingSummary)
from src.services.review_service import ReviewService

router = APIRouter()


@router.post("/", response_model=ReviewResponse, status_code=status.HTTP_201_CREATED)
async def create_review(
    review_data: ReviewCreate,
    current_user: User = Depends(get_current_user),
    review_service: ReviewService = Depends(get_review_service),
):
    """Create a new review."""
    try:
        review = await review_service.create_review(
            user_id=current_user.id,
            product_id=review_data.product_id,
            rating=review_data.rating,
            comment=review_data.comment,
        )
        return ReviewResponse.from_orm(review)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except IntegrityError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Review creation failed due to data conflict",
        )


@router.get("/", response_model=ReviewListResponse)
async def list_reviews(
    search_params: ReviewSearch = Depends(),
    review_service: ReviewService = Depends(get_review_service),
):
    """List reviews with optional filtering."""
    if search_params.product_id:
        reviews = await review_service.get_product_reviews(
            product_id=search_params.product_id,
            skip=search_params.skip,
            limit=search_params.limit,
            verified_only=search_params.verified_only,
            min_rating=search_params.min_rating,
            max_rating=search_params.max_rating,
        )
    elif search_params.vendor_id:
        reviews = await review_service.get_vendor_reviews(
            vendor_id=search_params.vendor_id,
            skip=search_params.skip,
            limit=search_params.limit,
            verified_only=search_params.verified_only,
            min_rating=search_params.min_rating,
            max_rating=search_params.max_rating,
        )
    elif search_params.user_id:
        reviews = await review_service.get_user_reviews(
            user_id=search_params.user_id,
            skip=search_params.skip,
            limit=search_params.limit,
        )
    else:
        # Get recent reviews if no specific filter
        reviews = await review_service.get_recent_reviews(
            limit=search_params.limit,
        )

    # Get total count (simplified for now)
    total = len(reviews) + search_params.skip

    return ReviewListResponse(
        reviews=[ReviewResponse.from_orm(review) for review in reviews],
        total=total,
        skip=search_params.skip,
        limit=search_params.limit,
    )


@router.get("/{review_id}", response_model=ReviewResponse)
async def get_review(
    review_id: int,
    review_service: ReviewService = Depends(get_review_service),
):
    """Get review by ID."""
    review = await review_service.get_review(review_id)
    if not review:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Review not found",
        )
    return ReviewResponse.from_orm(review)


@router.put("/{review_id}", response_model=ReviewResponse)
async def update_review(
    review_id: int,
    review_data: ReviewUpdate,
    current_user: User = Depends(get_current_user),
    review_service: ReviewService = Depends(get_review_service),
):
    """Update a review."""
    try:
        updated_review = await review_service.update_review(
            review_id=review_id,
            user_id=current_user.id,
            rating=review_data.rating,
            comment=review_data.comment,
        )
        if not updated_review:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Review not found",
            )
        return ReviewResponse.from_orm(updated_review)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.delete("/{review_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_review(
    review_id: int,
    current_user: User = Depends(get_current_user),
    review_service: ReviewService = Depends(get_review_service),
):
    """Delete a review."""
    try:
        success = await review_service.delete_review(
            review_id=review_id,
            user_id=current_user.id,
        )
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Review not found",
            )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get("/products/{product_id}/reviews", response_model=ReviewListResponse)
async def get_product_reviews(
    product_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    verified_only: bool = Query(False),
    min_rating: Optional[int] = Query(None, ge=1, le=5),
    max_rating: Optional[int] = Query(None, ge=1, le=5),
    review_service: ReviewService = Depends(get_review_service),
):
    """Get reviews for a specific product."""
    reviews = await review_service.get_product_reviews(
        product_id=product_id,
        skip=skip,
        limit=limit,
        verified_only=verified_only,
        min_rating=min_rating,
        max_rating=max_rating,
    )

    # Get total count (simplified for now)
    total = len(reviews) + skip

    return ReviewListResponse(
        reviews=[ReviewResponse.from_orm(review) for review in reviews],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get(
    "/products/{product_id}/rating-summary", response_model=ProductRatingSummary
)
async def get_product_rating_summary(
    product_id: int,
    review_service: ReviewService = Depends(get_review_service),
):
    """Get rating summary for a product."""
    summary = await review_service.get_product_rating_summary(product_id)
    return ProductRatingSummary(
        product_id=product_id,
        **summary,
    )


@router.get("/vendors/{vendor_id}/reviews", response_model=ReviewListResponse)
async def get_vendor_reviews(
    vendor_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    verified_only: bool = Query(False),
    min_rating: Optional[int] = Query(None, ge=1, le=5),
    max_rating: Optional[int] = Query(None, ge=1, le=5),
    review_service: ReviewService = Depends(get_review_service),
):
    """Get reviews for a specific vendor."""
    reviews = await review_service.get_vendor_reviews(
        vendor_id=vendor_id,
        skip=skip,
        limit=limit,
        verified_only=verified_only,
        min_rating=min_rating,
        max_rating=max_rating,
    )

    # Get total count (simplified for now)
    total = len(reviews) + skip

    return ReviewListResponse(
        reviews=[ReviewResponse.from_orm(review) for review in reviews],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get("/vendors/{vendor_id}/rating-summary", response_model=VendorRatingSummary)
async def get_vendor_rating_summary(
    vendor_id: int,
    review_service: ReviewService = Depends(get_review_service),
):
    """Get rating summary for a vendor."""
    summary = await review_service.get_vendor_rating_summary(vendor_id)
    return VendorRatingSummary(
        vendor_id=vendor_id,
        **summary,
    )


@router.get("/users/{user_id}/reviews", response_model=ReviewListResponse)
async def get_user_reviews(
    user_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    current_user: User = Depends(get_current_user),
    review_service: ReviewService = Depends(get_review_service),
):
    """Get reviews by a specific user."""
    # Users can only see their own reviews unless they have admin role
    if user_id != current_user.id and "admin" not in current_user.roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    reviews = await review_service.get_user_reviews(
        user_id=user_id,
        skip=skip,
        limit=limit,
    )

    # Get total count (simplified for now)
    total = len(reviews) + skip

    return ReviewListResponse(
        reviews=[ReviewResponse.from_orm(review) for review in reviews],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.post("/{review_id}/moderate", response_model=ReviewResponse)
async def moderate_review(
    review_id: int,
    moderation_data: ReviewModeration,
    current_user: User = Depends(get_current_user),
    review_service: ReviewService = Depends(get_review_service),
):
    """Moderate a review (admin only)."""
    if "admin" not in current_user.roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )

    try:
        moderated_review = await review_service.moderate_review(
            review_id=review_id,
            moderator_id=current_user.id,
            action=moderation_data.action,
            reason=moderation_data.reason,
        )
        if not moderated_review:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Review not found or was removed",
            )
        return ReviewResponse.from_orm(moderated_review)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post("/{review_id}/verify", response_model=ReviewResponse)
async def verify_review(
    review_id: int,
    current_user: User = Depends(get_current_user),
    review_service: ReviewService = Depends(get_review_service),
):
    """Mark a review as verified purchase (admin only)."""
    if "admin" not in current_user.roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )

    verified_review = await review_service.mark_review_as_verified(review_id)
    if not verified_review:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Review not found",
        )
    return ReviewResponse.from_orm(verified_review)


@router.get("/top-rated/products", response_model=TopRatedProductsResponse)
async def get_top_rated_products(
    limit: int = Query(10, ge=1, le=100),
    min_reviews: int = Query(5, ge=1),
    review_service: ReviewService = Depends(get_review_service),
):
    """Get top-rated products."""
    products = await review_service.get_top_rated_products(
        limit=limit,
        min_reviews=min_reviews,
    )

    return TopRatedProductsResponse(
        products=products,
        limit=limit,
        min_reviews=min_reviews,
    )


@router.get("/top-rated/vendors", response_model=TopRatedVendorsResponse)
async def get_top_rated_vendors(
    limit: int = Query(10, ge=1, le=100),
    min_reviews: int = Query(5, ge=1),
    review_service: ReviewService = Depends(get_review_service),
):
    """Get top-rated vendors."""
    vendors = await review_service.get_top_rated_vendors(
        limit=limit,
        min_reviews=min_reviews,
    )

    return TopRatedVendorsResponse(
        vendors=vendors,
        limit=limit,
        min_reviews=min_reviews,
    )
