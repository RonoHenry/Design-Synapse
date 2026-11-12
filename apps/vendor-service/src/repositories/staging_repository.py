"""Repository for staging data access."""

from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session, joinedload
from src.models.product import Product
from src.models.staging import DesignStaging


class StagingRepository:
    """Repository for design staging CRUD operations."""

    def __init__(self, db: Session):
        """Initialize repository with database session."""
        self.db = db

    def create(self, staging: DesignStaging) -> DesignStaging:
        """Create a new staging entry."""
        self.db.add(staging)
        self.db.commit()
        self.db.refresh(staging)
        return staging

    def get_by_id(self, staging_id: int) -> Optional[DesignStaging]:
        """Get staging by ID."""
        return (
            self.db.query(DesignStaging).filter(DesignStaging.id == staging_id).first()
        )

    def get_by_design_id(
        self, design_id: int, skip: int = 0, limit: int = 100
    ) -> List[DesignStaging]:
        """Get all staging entries for a specific design."""
        return (
            self.db.query(DesignStaging)
            .filter(DesignStaging.design_id == design_id)
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_by_design_and_product(
        self, design_id: int, product_id: int
    ) -> Optional[DesignStaging]:
        """Get staging by design and product."""
        return (
            self.db.query(DesignStaging)
            .filter(
                DesignStaging.design_id == design_id,
                DesignStaging.product_id == product_id,
            )
            .first()
        )

    def get_by_product_id(
        self, product_id: int, skip: int = 0, limit: int = 100
    ) -> List[DesignStaging]:
        """Get all staging entries for a specific product."""
        return (
            self.db.query(DesignStaging)
            .filter(DesignStaging.product_id == product_id)
            .offset(skip)
            .limit(limit)
            .all()
        )

    def update(self, staging: DesignStaging) -> DesignStaging:
        """Update an existing staging entry."""
        self.db.commit()
        self.db.refresh(staging)
        return staging

    def delete(self, staging: DesignStaging) -> None:
        """Delete a staging entry."""
        self.db.delete(staging)
        self.db.commit()

    def delete_by_id(self, staging_id: int) -> bool:
        """Delete staging by ID. Returns True if deleted, False if not found."""
        staging = self.get_by_id(staging_id)
        if staging:
            self.delete(staging)
            return True
        return False

    def delete_by_design_id(self, design_id: int) -> int:
        """Delete all staging entries for a design. Returns count of deleted entries."""
        result = (
            self.db.query(DesignStaging)
            .filter(DesignStaging.design_id == design_id)
            .delete()
        )
        self.db.commit()
        return result

    def count_by_design(self, design_id: int) -> int:
        """Count staging entries for a design."""
        return (
            self.db.query(DesignStaging)
            .filter(DesignStaging.design_id == design_id)
            .count()
        )

    def get_design_staging_with_products(
        self, design_id: int, skip: int = 0, limit: int = 100
    ) -> List[Tuple[DesignStaging, Product]]:
        """Get design staging with product details."""
        return (
            self.db.query(DesignStaging, Product)
            .join(Product, DesignStaging.product_id == Product.id)
            .filter(DesignStaging.design_id == design_id)
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_procurement_list(self, design_id: int) -> List[Dict[str, Any]]:
        """Generate procurement list for a design with quantities and pricing."""
        results = (
            self.db.query(
                DesignStaging.quantity,
                Product.id.label("product_id"),
                Product.name.label("product_name"),
                Product.price.label("unit_price"),
                Product.inventory_quantity.label("available_quantity"),
                Product.category,
                (DesignStaging.quantity * Product.price).label("total_price"),
            )
            .join(Product, DesignStaging.product_id == Product.id)
            .filter(DesignStaging.design_id == design_id)
            .all()
        )

        procurement_list = []
        for result in results:
            procurement_list.append(
                {
                    "product_id": result.product_id,
                    "product_name": result.product_name,
                    "category": result.category,
                    "quantity": result.quantity,
                    "unit_price": result.unit_price,
                    "total_price": result.total_price,
                    "available_quantity": result.available_quantity,
                }
            )

        return procurement_list

    def get_total_cost_by_design(self, design_id: int) -> Decimal:
        """Calculate total cost for all products in a design."""
        result = (
            self.db.query(
                func.sum(DesignStaging.quantity * Product.price).label("total_cost")
            )
            .join(Product, DesignStaging.product_id == Product.id)
            .filter(DesignStaging.design_id == design_id)
            .scalar()
        )

        return result or Decimal("0.00")

    def get_most_staged_products(self, limit: int = 10) -> List[Tuple[Product, int]]:
        """Get most frequently staged products with staging counts."""
        return (
            self.db.query(Product, func.count(DesignStaging.id).label("staging_count"))
            .join(DesignStaging, Product.id == DesignStaging.product_id)
            .group_by(Product.id)
            .order_by(func.count(DesignStaging.id).desc())
            .limit(limit)
            .all()
        )
