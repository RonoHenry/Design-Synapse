"""API dependencies for vendor service."""

import sys
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

# Add packages to path for common imports
packages_path = Path(__file__).parent.parent.parent.parent.parent / "packages"
sys.path.insert(0, str(packages_path))


# Mock User model for testing
class User:
    def __init__(self, id: int, username: str, email: str, roles: list = None):
        self.id = id
        self.username = username
        self.email = email
        self.roles = roles or []


from src.core.database import get_db_session
from src.models.vendor import Vendor
from src.repositories.bookmark_repository import BookmarkRepository
from src.repositories.order_repository import OrderRepository
from src.repositories.product_repository_async import ProductRepository
from src.repositories.review_repository import ReviewRepository
from src.repositories.staging_repository import StagingRepository
from src.repositories.vendor_repository_async import VendorRepository
from src.services.order_service import OrderService
from src.services.product_service import ProductService
from src.services.review_service import ReviewService
from src.services.staging_service import StagingService
from src.services.vendor_service import VendorService


async def get_current_user(authorization: Optional[str] = Header(None)) -> User:
    """Get current authenticated user from JWT token."""
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header required",
        )

    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header format",
        )

    token = authorization.split(" ")[1]

    # TODO: Implement JWT token validation
    # For now, return a mock user for development
    return User(
        id=1,
        username="testuser",
        email="test@example.com",
        roles=["user"],
    )


async def get_vendor_repository(
    db: AsyncSession = Depends(get_db_session),
) -> VendorRepository:
    """Get vendor repository."""
    return VendorRepository(db)


async def get_product_repository(
    db: AsyncSession = Depends(get_db_session),
) -> ProductRepository:
    """Get product repository."""
    return ProductRepository(db)


async def get_order_repository(
    db: AsyncSession = Depends(get_db_session),
) -> OrderRepository:
    """Get order repository."""
    return OrderRepository(db)


async def get_review_repository(
    db: AsyncSession = Depends(get_db_session),
) -> ReviewRepository:
    """Get review repository."""
    return ReviewRepository(db)


async def get_bookmark_repository(
    db: AsyncSession = Depends(get_db_session),
) -> BookmarkRepository:
    """Get bookmark repository."""
    return BookmarkRepository(db)


async def get_staging_repository(
    db: AsyncSession = Depends(get_db_session),
) -> StagingRepository:
    """Get staging repository."""
    return StagingRepository(db)


async def get_vendor_service(
    vendor_repository: VendorRepository = Depends(get_vendor_repository),
) -> VendorService:
    """Get vendor service."""
    return VendorService(vendor_repository)


async def get_product_service(
    product_repository: ProductRepository = Depends(get_product_repository),
) -> ProductService:
    """Get product service."""
    return ProductService(product_repository)


async def get_order_service(
    order_repository: OrderRepository = Depends(get_order_repository),
    product_repository: ProductRepository = Depends(get_product_repository),
) -> OrderService:
    """Get order service."""
    return OrderService(order_repository, product_repository)


async def get_review_service(
    review_repository: ReviewRepository = Depends(get_review_repository),
    order_repository: OrderRepository = Depends(get_order_repository),
    product_repository: ProductRepository = Depends(get_product_repository),
    vendor_repository: VendorRepository = Depends(get_vendor_repository),
) -> ReviewService:
    """Get review service."""
    return ReviewService(
        review_repository, order_repository, product_repository, vendor_repository
    )


async def get_staging_service(
    bookmark_repository: BookmarkRepository = Depends(get_bookmark_repository),
    staging_repository: StagingRepository = Depends(get_staging_repository),
    product_repository: ProductRepository = Depends(get_product_repository),
) -> StagingService:
    """Get staging service."""
    return StagingService(bookmark_repository, staging_repository, product_repository)


async def get_current_vendor(
    current_user: User = Depends(get_current_user),
    vendor_service: VendorService = Depends(get_vendor_service),
) -> Vendor:
    """Get current user's vendor profile."""
    vendor = await vendor_service.get_vendor_by_user_id(current_user.id)
    if not vendor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vendor profile not found",
        )
    return vendor


async def verify_vendor_ownership(
    vendor_id: int,
    current_user: User = Depends(get_current_user),
    vendor_service: VendorService = Depends(get_vendor_service),
) -> Vendor:
    """Verify that current user owns the vendor profile."""
    vendor = await vendor_service.get_vendor(vendor_id)
    if not vendor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vendor not found",
        )

    if vendor.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this vendor profile",
        )

    return vendor


async def verify_product_ownership(
    product_id: int,
    current_user: User = Depends(get_current_user),
    product_service: ProductService = Depends(get_product_service),
    vendor_service: VendorService = Depends(get_vendor_service),
) -> tuple[Any, Vendor]:
    """Verify that current user owns the product through their vendor profile."""
    product = await product_service.get_product(product_id)
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found",
        )

    vendor = await vendor_service.get_vendor(product.vendor_id)
    if not vendor or vendor.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this product",
        )

    return product, vendor
