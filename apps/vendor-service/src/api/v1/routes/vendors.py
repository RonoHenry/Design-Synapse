"""Vendor API routes."""

from typing import Any, List, Optional


# Mock User model for testing
class User:
    def __init__(self, id: int, username: str, email: str, roles: list = None):
        self.id = id
        self.username = username
        self.email = email
        self.roles = roles or []


from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError
from src.api.dependencies import (get_current_user, get_product_service,
                                  get_vendor_service, verify_vendor_ownership)
from src.api.v1.schemas.product import ProductListResponse, ProductResponse
from src.api.v1.schemas.vendor import (VendorCreate, VendorListResponse,
                                       VendorResponse, VendorUpdate)
from src.services.product_service import ProductService
from src.services.vendor_service import VendorService

router = APIRouter()


@router.post("/", response_model=VendorResponse, status_code=status.HTTP_201_CREATED)
async def register_vendor(
    vendor_data: VendorCreate,
    current_user: User = Depends(get_current_user),
    vendor_service: VendorService = Depends(get_vendor_service),
):
    """Register a new vendor."""
    try:
        vendor = await vendor_service.register_vendor(
            user_id=current_user.id,
            company_name=vendor_data.company_name,
            email=vendor_data.email,
            phone=vendor_data.phone,
            address=vendor_data.address,
        )
        return VendorResponse.from_orm(vendor)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except IntegrityError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User already has a vendor profile",
        )


@router.get("/me", response_model=VendorResponse)
async def get_my_vendor_profile(
    current_user: User = Depends(get_current_user),
    vendor_service: VendorService = Depends(get_vendor_service),
):
    """Get current user's vendor profile."""
    vendor = await vendor_service.get_vendor_by_user_id(current_user.id)
    if not vendor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vendor profile not found",
        )
    return VendorResponse.from_orm(vendor)


@router.get("/{vendor_id}", response_model=VendorResponse)
async def get_vendor(
    vendor_id: int,
    vendor_service: VendorService = Depends(get_vendor_service),
):
    """Get vendor by ID."""
    vendor = await vendor_service.get_vendor(vendor_id)
    if not vendor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vendor not found",
        )
    return VendorResponse.from_orm(vendor)


@router.put("/{vendor_id}", response_model=VendorResponse)
async def update_vendor(
    vendor_id: int,
    vendor_data: VendorUpdate,
    vendor: Any = Depends(verify_vendor_ownership),
    vendor_service: VendorService = Depends(get_vendor_service),
):
    """Update vendor profile."""
    try:
        updated_vendor = await vendor_service.update_vendor_profile(
            vendor_id=vendor_id,
            company_name=vendor_data.company_name,
            email=vendor_data.email,
            phone=vendor_data.phone,
            address=vendor_data.address,
        )
        if not updated_vendor:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Vendor not found",
            )
        return VendorResponse.from_orm(updated_vendor)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get("/", response_model=VendorListResponse)
async def list_vendors(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    verification_status: Optional[str] = Query(None),
    vendor_service: VendorService = Depends(get_vendor_service),
):
    """List vendors with optional filtering."""
    vendors = await vendor_service.list_vendors(
        skip=skip,
        limit=limit,
        verification_status=verification_status,
    )

    # Get total count (simplified for now)
    total = len(vendors) + skip

    return VendorListResponse(
        vendors=[VendorResponse.from_orm(vendor) for vendor in vendors],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get("/{vendor_id}/products", response_model=ProductListResponse)
async def get_vendor_products(
    vendor_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    category: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    vendor_service: VendorService = Depends(get_vendor_service),
    product_service: ProductService = Depends(get_product_service),
):
    """Get products for a vendor."""
    # Verify vendor exists
    vendor = await vendor_service.get_vendor(vendor_id)
    if not vendor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vendor not found",
        )

    products = await product_service.get_vendor_products(
        vendor_id=vendor_id,
        skip=skip,
        limit=limit,
        category=category,
        is_active=is_active,
    )

    # Get total count (simplified for now)
    total = len(products) + skip

    return ProductListResponse(
        products=[ProductResponse.from_orm(product) for product in products],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.delete("/{vendor_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_vendor(
    vendor_id: int,
    vendor: Any = Depends(verify_vendor_ownership),
    vendor_service: VendorService = Depends(get_vendor_service),
):
    """Delete vendor profile."""
    success = await vendor_service.delete_vendor(vendor_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vendor not found",
        )
