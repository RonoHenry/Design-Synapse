"""Product API routes."""

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
from src.api.dependencies import (get_current_user, get_current_vendor,
                                  get_product_service,
                                  verify_product_ownership)
from src.api.v1.schemas.product import (InventoryAdjustment, InventoryUpdate,
                                        ProductCreate, ProductListResponse,
                                        ProductResponse, ProductSearch,
                                        ProductUpdate)
from src.models.vendor import Vendor
from src.services.product_service import ProductService

router = APIRouter()


@router.post("/", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
async def create_product(
    product_data: ProductCreate,
    current_vendor: Vendor = Depends(get_current_vendor),
    product_service: ProductService = Depends(get_product_service),
):
    """Create a new product."""
    try:
        product = await product_service.create_product(
            vendor_id=current_vendor.id,
            name=product_data.name,
            category=product_data.category,
            price=product_data.price,
            description=product_data.description,
            inventory_quantity=product_data.inventory_quantity,
            images=product_data.images,
            specifications=product_data.specifications,
            model_url=product_data.model_url,
            dimensions=product_data.dimensions,
            model_format=product_data.model_format,
        )
        return ProductResponse.from_orm(product)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get("/search", response_model=ProductListResponse)
async def search_products(
    search_params: ProductSearch = Depends(),
    product_service: ProductService = Depends(get_product_service),
):
    """Search products with filters."""
    products = await product_service.search_products(
        query=search_params.query,
        category=search_params.category,
        min_price=search_params.min_price,
        max_price=search_params.max_price,
        in_stock_only=search_params.in_stock_only,
        has_3d_model=search_params.has_3d_model,
        skip=search_params.skip,
        limit=search_params.limit,
    )

    # Get total count (simplified for now)
    total = len(products) + search_params.skip

    return ProductListResponse(
        products=[ProductResponse.from_orm(product) for product in products],
        total=total,
        skip=search_params.skip,
        limit=search_params.limit,
    )


@router.get("/3d-models", response_model=ProductListResponse)
async def get_products_with_3d_models(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    category: Optional[str] = Query(None),
    product_service: ProductService = Depends(get_product_service),
):
    """Get products that have 3D models for staging."""
    products = await product_service.get_products_with_3d_models(
        skip=skip,
        limit=limit,
        category=category,
    )

    # Get total count (simplified for now)
    total = len(products) + skip

    return ProductListResponse(
        products=[ProductResponse.from_orm(product) for product in products],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get("/{product_id}", response_model=ProductResponse)
async def get_product(
    product_id: int,
    product_service: ProductService = Depends(get_product_service),
):
    """Get product by ID."""
    product = await product_service.get_product(product_id)
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found",
        )
    return ProductResponse.from_orm(product)


@router.put("/{product_id}", response_model=ProductResponse)
async def update_product(
    product_id: int,
    product_data: ProductUpdate,
    product_and_vendor: tuple[Any, Any] = Depends(verify_product_ownership),
    product_service: ProductService = Depends(get_product_service),
):
    """Update product."""
    product, vendor = product_and_vendor

    try:
        updated_product = await product_service.update_product(
            product_id=product_id,
            name=product_data.name,
            description=product_data.description,
            category=product_data.category,
            price=product_data.price,
            inventory_quantity=product_data.inventory_quantity,
            images=product_data.images,
            specifications=product_data.specifications,
            model_url=product_data.model_url,
            dimensions=product_data.dimensions,
            model_format=product_data.model_format,
            is_active=product_data.is_active,
        )
        if not updated_product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Product not found",
            )
        return ProductResponse.from_orm(updated_product)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_product(
    product_id: int,
    product_and_vendor: tuple[Any, Any] = Depends(verify_product_ownership),
    product_service: ProductService = Depends(get_product_service),
):
    """Delete product."""
    product, vendor = product_and_vendor

    success = await product_service.delete_product(product_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found",
        )


@router.put("/{product_id}/inventory", response_model=ProductResponse)
async def update_product_inventory(
    product_id: int,
    inventory_data: InventoryUpdate,
    product_and_vendor: tuple[Any, Any] = Depends(verify_product_ownership),
    product_service: ProductService = Depends(get_product_service),
):
    """Update product inventory."""
    product, vendor = product_and_vendor

    updated_product = await product_service.update_inventory(
        product_id=product_id,
        quantity=inventory_data.quantity,
    )
    if not updated_product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found",
        )
    return ProductResponse.from_orm(updated_product)


@router.patch("/{product_id}/inventory", response_model=ProductResponse)
async def adjust_product_inventory(
    product_id: int,
    adjustment_data: InventoryAdjustment,
    product_and_vendor: tuple[Any, Any] = Depends(verify_product_ownership),
    product_service: ProductService = Depends(get_product_service),
):
    """Adjust product inventory by delta."""
    product, vendor = product_and_vendor

    try:
        updated_product = await product_service.adjust_inventory(
            product_id=product_id,
            adjustment=adjustment_data.adjustment,
        )
        if not updated_product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Product not found",
            )
        return ProductResponse.from_orm(updated_product)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post("/{product_id}/activate", response_model=ProductResponse)
async def activate_product(
    product_id: int,
    product_and_vendor: tuple[Any, Any] = Depends(verify_product_ownership),
    product_service: ProductService = Depends(get_product_service),
):
    """Activate a product."""
    product, vendor = product_and_vendor

    updated_product = await product_service.activate_product(product_id)
    if not updated_product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found",
        )
    return ProductResponse.from_orm(updated_product)


@router.post("/{product_id}/deactivate", response_model=ProductResponse)
async def deactivate_product(
    product_id: int,
    product_and_vendor: tuple[Any, Any] = Depends(verify_product_ownership),
    product_service: ProductService = Depends(get_product_service),
):
    """Deactivate a product."""
    product, vendor = product_and_vendor

    updated_product = await product_service.deactivate_product(product_id)
    if not updated_product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found",
        )
    return ProductResponse.from_orm(updated_product)


@router.get("/{product_id}/availability")
async def check_product_availability(
    product_id: int,
    quantity: int = Query(1, ge=1),
    product_service: ProductService = Depends(get_product_service),
):
    """Check if product is available in requested quantity."""
    is_available = await product_service.check_availability(product_id, quantity)

    return {
        "product_id": product_id,
        "requested_quantity": quantity,
        "available": is_available,
    }
