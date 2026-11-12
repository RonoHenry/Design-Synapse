"""Staging service for product bookmarking and design integration."""

from typing import Dict, List, Optional

from src.models.bookmark import ProductBookmark
from src.models.staging import DesignStaging
from src.repositories.bookmark_repository import BookmarkRepository
from src.repositories.product_repository import ProductRepository
from src.repositories.staging_repository import StagingRepository


class StagingService:
    """Service for product staging and bookmarking business logic."""

    def __init__(
        self,
        bookmark_repository: BookmarkRepository,
        staging_repository: StagingRepository,
        product_repository: ProductRepository,
    ):
        """Initialize staging service."""
        self.bookmark_repository = bookmark_repository
        self.staging_repository = staging_repository
        self.product_repository = product_repository

    async def bookmark_product(
        self,
        user_id: int,
        product_id: int,
        notes: Optional[str] = None,
    ) -> ProductBookmark:
        """Bookmark a product for later use."""
        # Validate product exists
        product = await self.product_repository.get_by_id(product_id)
        if not product:
            raise ValueError(f"Product {product_id} not found")

        # Check if already bookmarked
        existing_bookmark = await self.bookmark_repository.get_by_user_and_product(
            user_id, product_id
        )
        if existing_bookmark:
            raise ValueError("Product is already bookmarked")

        # Create bookmark
        bookmark = ProductBookmark(
            user_id=user_id,
            product_id=product_id,
            notes=notes,
        )

        return await self.bookmark_repository.create(bookmark)

    async def remove_bookmark(self, user_id: int, bookmark_id: int) -> bool:
        """Remove a bookmark."""
        bookmark = await self.bookmark_repository.get_by_id(bookmark_id)
        if not bookmark:
            return False

        # Check ownership
        if bookmark.user_id != user_id:
            raise ValueError("User can only remove their own bookmarks")

        return await self.bookmark_repository.delete(bookmark_id)

    async def get_user_bookmarks(
        self,
        user_id: int,
        skip: int = 0,
        limit: int = 100,
    ) -> List[ProductBookmark]:
        """Get user's bookmarked products."""
        return await self.bookmark_repository.get_by_user_id(
            user_id=user_id,
            skip=skip,
            limit=limit,
        )

    async def update_bookmark_notes(
        self,
        user_id: int,
        bookmark_id: int,
        notes: Optional[str] = None,
    ) -> Optional[ProductBookmark]:
        """Update bookmark notes."""
        bookmark = await self.bookmark_repository.get_by_id(bookmark_id)
        if not bookmark:
            return None

        # Check ownership
        if bookmark.user_id != user_id:
            raise ValueError("User can only update their own bookmarks")

        bookmark.notes = notes
        return await self.bookmark_repository.update(bookmark)

    async def stage_product_in_design(
        self,
        design_id: int,
        product_id: int,
        position: Dict[str, float],
        rotation: Optional[Dict[str, float]] = None,
        scale: Optional[Dict[str, float]] = None,
        quantity: int = 1,
    ) -> DesignStaging:
        """Stage a product in a design."""
        # Validate product exists and has 3D model
        product = await self.product_repository.get_by_id(product_id)
        if not product:
            raise ValueError(f"Product {product_id} not found")

        if not product.has_3d_model():
            raise ValueError(
                f"Product {product_id} does not have a 3D model for staging"
            )

        # Validate position data
        required_position_keys = ["x", "y", "z"]
        for key in required_position_keys:
            if key not in position:
                raise ValueError(f"Position must include {key} coordinate")

        # Set default rotation and scale if not provided
        if rotation is None:
            rotation = {"x": 0.0, "y": 0.0, "z": 0.0}
        if scale is None:
            scale = {"x": 1.0, "y": 1.0, "z": 1.0}

        # Check if product is already staged in this design
        existing_staging = await self.staging_repository.get_by_design_and_product(
            design_id, product_id
        )
        if existing_staging:
            # Update existing staging
            existing_staging.position = position
            existing_staging.rotation = rotation
            existing_staging.scale = scale
            existing_staging.quantity = quantity
            return await self.staging_repository.update(existing_staging)

        # Create new staging
        staging = DesignStaging(
            design_id=design_id,
            product_id=product_id,
            position=position,
            rotation=rotation,
            scale=scale,
            quantity=quantity,
        )

        return await self.staging_repository.create(staging)

    async def remove_product_from_design(
        self,
        design_id: int,
        product_id: int,
    ) -> bool:
        """Remove a product from design staging."""
        staging = await self.staging_repository.get_by_design_and_product(
            design_id, product_id
        )
        if not staging:
            return False

        return await self.staging_repository.delete(staging.id)

    async def get_design_staged_products(
        self,
        design_id: int,
        skip: int = 0,
        limit: int = 100,
    ) -> List[DesignStaging]:
        """Get all products staged in a design."""
        return await self.staging_repository.get_by_design_id(
            design_id=design_id,
            skip=skip,
            limit=limit,
        )

    async def update_product_staging(
        self,
        staging_id: int,
        position: Optional[Dict[str, float]] = None,
        rotation: Optional[Dict[str, float]] = None,
        scale: Optional[Dict[str, float]] = None,
        quantity: Optional[int] = None,
    ) -> Optional[DesignStaging]:
        """Update product staging parameters."""
        staging = await self.staging_repository.get_by_id(staging_id)
        if not staging:
            return None

        # Update fields if provided
        if position is not None:
            staging.update_position(position["x"], position["y"], position["z"])
        if rotation is not None:
            staging.update_rotation(rotation["x"], rotation["y"], rotation["z"])
        if scale is not None:
            staging.update_scale(scale["x"], scale["y"], scale["z"])
        if quantity is not None:
            staging.update_quantity(quantity)

        return await self.staging_repository.update(staging)

    async def generate_procurement_list(
        self,
        design_id: int,
        include_pricing: bool = True,
    ) -> Dict:
        """Generate procurement list for a design."""
        procurement_data = await self.staging_repository.get_procurement_list(design_id)

        total_cost = sum(item["total_cost"] for item in procurement_data)
        total_items = len(procurement_data)
        total_quantity = sum(item["quantity"] for item in procurement_data)

        # Group by vendor for easier procurement
        vendors = {}
        for item in procurement_data:
            vendor_id = item["vendor_id"]
            if vendor_id not in vendors:
                vendors[vendor_id] = {
                    "vendor_id": vendor_id,
                    "vendor_name": item["vendor_name"],
                    "products": [],
                    "vendor_total": 0,
                }

            vendors[vendor_id]["products"].append(
                {
                    "product_id": item["product_id"],
                    "product_name": item["product_name"],
                    "quantity": item["quantity"],
                    "unit_price": item["unit_price"],
                    "total_cost": item["total_cost"],
                    "availability": item["availability"],
                }
            )
            vendors[vendor_id]["vendor_total"] += item["total_cost"]

        return {
            "design_id": design_id,
            "summary": {
                "total_cost": total_cost,
                "total_items": total_items,
                "total_quantity": total_quantity,
                "vendor_count": len(vendors),
            },
            "vendors": list(vendors.values()),
            "items": procurement_data,
        }

    async def get_design_total_cost(self, design_id: int) -> float:
        """Get total cost of all staged products in a design."""
        return await self.staging_repository.get_total_cost_by_design(design_id)

    async def check_design_availability(self, design_id: int) -> Dict:
        """Check availability of all staged products in a design."""
        staged_products = await self.staging_repository.get_by_design_id(design_id)

        availability_issues = []
        total_products = len(staged_products)
        available_products = 0

        for staging in staged_products:
            product = await self.product_repository.get_by_id(staging.product_id)
            if not product:
                availability_issues.append(
                    {
                        "product_id": staging.product_id,
                        "issue": "Product not found",
                        "requested_quantity": staging.quantity,
                    }
                )
                continue

            if not product.is_active:
                availability_issues.append(
                    {
                        "product_id": staging.product_id,
                        "product_name": product.name,
                        "issue": "Product is inactive",
                        "requested_quantity": staging.quantity,
                    }
                )
                continue

            if product.inventory_quantity < staging.quantity:
                availability_issues.append(
                    {
                        "product_id": staging.product_id,
                        "product_name": product.name,
                        "issue": "Insufficient inventory",
                        "requested_quantity": staging.quantity,
                        "available_quantity": product.inventory_quantity,
                    }
                )
                continue

            available_products += 1

        return {
            "design_id": design_id,
            "total_products": total_products,
            "available_products": available_products,
            "availability_rate": available_products / total_products
            if total_products > 0
            else 0,
            "issues": availability_issues,
            "all_available": len(availability_issues) == 0,
        }

    async def get_popular_bookmarked_products(
        self,
        limit: int = 10,
        category: Optional[str] = None,
    ) -> List[Dict]:
        """Get most bookmarked products."""
        return await self.bookmark_repository.get_popular_bookmarked_products(
            limit=limit,
            category=category,
        )

    async def get_most_staged_products(
        self,
        limit: int = 10,
        category: Optional[str] = None,
    ) -> List[Dict]:
        """Get most frequently staged products."""
        return await self.staging_repository.get_most_staged_products(
            limit=limit,
            category=category,
        )

    async def get_products_with_3d_models(
        self,
        skip: int = 0,
        limit: int = 100,
        category: Optional[str] = None,
    ) -> List:
        """Get products that have 3D models for staging."""
        return await self.product_repository.get_products_with_3d_models(
            skip=skip,
            limit=limit,
            category=category,
        )

    async def validate_product_for_staging(self, product_id: int) -> Dict:
        """Validate if a product can be staged in designs."""
        product = await self.product_repository.get_by_id(product_id)
        if not product:
            return {
                "valid": False,
                "issues": ["Product not found"],
            }

        issues = []

        if not product.is_active:
            issues.append("Product is inactive")

        if not product.has_3d_model():
            issues.append("Product does not have a 3D model")

        if not product.dimensions:
            issues.append("Product dimensions are not specified")

        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "product_info": {
                "id": product.id,
                "name": product.name,
                "has_3d_model": product.has_3d_model(),
                "dimensions": product.dimensions,
                "model_format": product.model_format,
                "model_url": product.model_url,
            },
        }
