"""Tests for DesignStaging model."""

from datetime import datetime
from decimal import Decimal

import pytest
from src.models.product import Product
from src.models.staging import DesignStaging
from src.models.vendor import Vendor


class TestDesignStagingModel:
    """Test DesignStaging model functionality."""

    def test_create_staging(self):
        """Test creating a staging entry with valid data."""
        staging = DesignStaging(
            design_id=1,
            product_id=10,
            position={"x": 10.5, "y": 5.0, "z": 0.0},
            rotation={"x": 0.0, "y": 90.0, "z": 0.0},
            scale={"x": 1.0, "y": 1.0, "z": 1.0},
            quantity=2,
        )

        assert staging.design_id == 1
        assert staging.product_id == 10
        assert staging.position == {"x": 10.5, "y": 5.0, "z": 0.0}
        assert staging.rotation == {"x": 0.0, "y": 90.0, "z": 0.0}
        assert staging.scale == {"x": 1.0, "y": 1.0, "z": 1.0}
        assert staging.quantity == 2
        assert isinstance(staging.created_at, datetime)

    def test_staging_default_quantity(self):
        """Test staging default quantity is 1."""
        staging = DesignStaging(
            design_id=1,
            product_id=10,
            position={"x": 0.0, "y": 0.0, "z": 0.0},
            rotation={"x": 0.0, "y": 0.0, "z": 0.0},
            scale={"x": 1.0, "y": 1.0, "z": 1.0},
        )

        assert staging.quantity == 1

    def test_staging_position_validation(self):
        """Test position validation."""
        # Missing coordinate
        with pytest.raises(ValueError, match="Position must include"):
            DesignStaging(
                design_id=1,
                product_id=10,
                position={"x": 0.0, "y": 0.0},  # Missing z
                rotation={"x": 0.0, "y": 0.0, "z": 0.0},
                scale={"x": 1.0, "y": 1.0, "z": 1.0},
            )

        # Invalid coordinate type
        with pytest.raises(ValueError, match="Position .* must be a number"):
            DesignStaging(
                design_id=1,
                product_id=10,
                position={"x": "invalid", "y": 0.0, "z": 0.0},
                rotation={"x": 0.0, "y": 0.0, "z": 0.0},
                scale={"x": 1.0, "y": 1.0, "z": 1.0},
            )

    def test_staging_rotation_validation(self):
        """Test rotation validation."""
        # Missing angle
        with pytest.raises(ValueError, match="Rotation must include"):
            DesignStaging(
                design_id=1,
                product_id=10,
                position={"x": 0.0, "y": 0.0, "z": 0.0},
                rotation={"x": 0.0, "y": 0.0},  # Missing z
                scale={"x": 1.0, "y": 1.0, "z": 1.0},
            )

        # Invalid angle type
        with pytest.raises(ValueError, match="Rotation .* must be a number"):
            DesignStaging(
                design_id=1,
                product_id=10,
                position={"x": 0.0, "y": 0.0, "z": 0.0},
                rotation={"x": 0.0, "y": "invalid", "z": 0.0},
                scale={"x": 1.0, "y": 1.0, "z": 1.0},
            )

    def test_staging_scale_validation(self):
        """Test scale validation."""
        # Missing scale factor
        with pytest.raises(ValueError, match="Scale must include"):
            DesignStaging(
                design_id=1,
                product_id=10,
                position={"x": 0.0, "y": 0.0, "z": 0.0},
                rotation={"x": 0.0, "y": 0.0, "z": 0.0},
                scale={"x": 1.0, "y": 1.0},  # Missing z
            )

        # Invalid scale type
        with pytest.raises(ValueError, match="Scale .* must be a number"):
            DesignStaging(
                design_id=1,
                product_id=10,
                position={"x": 0.0, "y": 0.0, "z": 0.0},
                rotation={"x": 0.0, "y": 0.0, "z": 0.0},
                scale={"x": 1.0, "y": "invalid", "z": 1.0},
            )

        # Negative scale
        with pytest.raises(ValueError, match="Scale .* must be positive"):
            DesignStaging(
                design_id=1,
                product_id=10,
                position={"x": 0.0, "y": 0.0, "z": 0.0},
                rotation={"x": 0.0, "y": 0.0, "z": 0.0},
                scale={"x": 1.0, "y": -1.0, "z": 1.0},
            )

        # Zero scale
        with pytest.raises(ValueError, match="Scale .* must be positive"):
            DesignStaging(
                design_id=1,
                product_id=10,
                position={"x": 0.0, "y": 0.0, "z": 0.0},
                rotation={"x": 0.0, "y": 0.0, "z": 0.0},
                scale={"x": 1.0, "y": 0.0, "z": 1.0},
            )

    def test_staging_quantity_validation(self):
        """Test quantity validation."""
        # Zero quantity
        with pytest.raises(ValueError, match="Quantity must be positive"):
            DesignStaging(
                design_id=1,
                product_id=10,
                position={"x": 0.0, "y": 0.0, "z": 0.0},
                rotation={"x": 0.0, "y": 0.0, "z": 0.0},
                scale={"x": 1.0, "y": 1.0, "z": 1.0},
                quantity=0,
            )

        # Negative quantity
        with pytest.raises(ValueError, match="Quantity must be positive"):
            DesignStaging(
                design_id=1,
                product_id=10,
                position={"x": 0.0, "y": 0.0, "z": 0.0},
                rotation={"x": 0.0, "y": 0.0, "z": 0.0},
                scale={"x": 1.0, "y": 1.0, "z": 1.0},
                quantity=-5,
            )

        # Exceeds maximum
        with pytest.raises(ValueError, match="Quantity exceeds maximum"):
            DesignStaging(
                design_id=1,
                product_id=10,
                position={"x": 0.0, "y": 0.0, "z": 0.0},
                rotation={"x": 0.0, "y": 0.0, "z": 0.0},
                scale={"x": 1.0, "y": 1.0, "z": 1.0},
                quantity=10001,
            )

    def test_staging_update_position(self):
        """Test updating position."""
        staging = DesignStaging(
            design_id=1,
            product_id=10,
            position={"x": 0.0, "y": 0.0, "z": 0.0},
            rotation={"x": 0.0, "y": 0.0, "z": 0.0},
            scale={"x": 1.0, "y": 1.0, "z": 1.0},
        )

        new_position = {"x": 5.0, "y": 10.0, "z": 2.0}
        staging.update_position(new_position)
        assert staging.position == new_position

    def test_staging_update_rotation(self):
        """Test updating rotation."""
        staging = DesignStaging(
            design_id=1,
            product_id=10,
            position={"x": 0.0, "y": 0.0, "z": 0.0},
            rotation={"x": 0.0, "y": 0.0, "z": 0.0},
            scale={"x": 1.0, "y": 1.0, "z": 1.0},
        )

        new_rotation = {"x": 45.0, "y": 90.0, "z": 180.0}
        staging.update_rotation(new_rotation)
        assert staging.rotation == new_rotation

    def test_staging_update_scale(self):
        """Test updating scale."""
        staging = DesignStaging(
            design_id=1,
            product_id=10,
            position={"x": 0.0, "y": 0.0, "z": 0.0},
            rotation={"x": 0.0, "y": 0.0, "z": 0.0},
            scale={"x": 1.0, "y": 1.0, "z": 1.0},
        )

        new_scale = {"x": 2.0, "y": 2.0, "z": 2.0}
        staging.update_scale(new_scale)
        assert staging.scale == new_scale

    def test_staging_update_quantity(self):
        """Test updating quantity."""
        staging = DesignStaging(
            design_id=1,
            product_id=10,
            position={"x": 0.0, "y": 0.0, "z": 0.0},
            rotation={"x": 0.0, "y": 0.0, "z": 0.0},
            scale={"x": 1.0, "y": 1.0, "z": 1.0},
            quantity=1,
        )

        staging.update_quantity(5)
        assert staging.quantity == 5

    def test_staging_get_transform_matrix(self):
        """Test getting complete transformation matrix."""
        staging = DesignStaging(
            design_id=1,
            product_id=10,
            position={"x": 10.0, "y": 5.0, "z": 2.0},
            rotation={"x": 0.0, "y": 90.0, "z": 0.0},
            scale={"x": 1.5, "y": 1.5, "z": 1.5},
        )

        transform = staging.get_transform_matrix()
        assert transform["position"] == {"x": 10.0, "y": 5.0, "z": 2.0}
        assert transform["rotation"] == {"x": 0.0, "y": 90.0, "z": 0.0}
        assert transform["scale"] == {"x": 1.5, "y": 1.5, "z": 1.5}

    def test_staging_repr(self):
        """Test staging string representation."""
        staging = DesignStaging(
            design_id=1,
            product_id=10,
            position={"x": 0.0, "y": 0.0, "z": 0.0},
            rotation={"x": 0.0, "y": 0.0, "z": 0.0},
            scale={"x": 1.0, "y": 1.0, "z": 1.0},
            quantity=3,
        )

        repr_str = repr(staging)
        assert "design_id=1" in repr_str
        assert "product_id=10" in repr_str
        assert "quantity=3" in repr_str


class TestDesignStagingDatabase:
    """Test DesignStaging model with database."""

    def test_create_staging_in_db(self, db_session):
        """Test creating and persisting a staging entry."""
        # Create vendor and product first
        vendor = Vendor(
            user_id=1, company_name="Test Vendor", email="vendor@example.com"
        )
        db_session.add(vendor)
        db_session.commit()

        product = Product(
            vendor_id=vendor.id,
            name="Test Product",
            category="furniture",
            price=Decimal("299.99"),
        )
        db_session.add(product)
        db_session.commit()

        # Create staging
        staging = DesignStaging(
            design_id=1,
            product_id=product.id,
            position={"x": 10.0, "y": 5.0, "z": 0.0},
            rotation={"x": 0.0, "y": 90.0, "z": 0.0},
            scale={"x": 1.0, "y": 1.0, "z": 1.0},
            quantity=2,
        )
        db_session.add(staging)
        db_session.commit()

        assert staging.id is not None

        # Retrieve from database
        retrieved = db_session.query(DesignStaging).filter_by(design_id=1).first()
        assert retrieved is not None
        assert retrieved.product_id == product.id
        assert retrieved.quantity == 2

    def test_staging_cascade_delete_with_product(self, db_session):
        """Test that staging entries are deleted when product is deleted."""
        vendor = Vendor(
            user_id=1, company_name="Test Vendor", email="vendor@example.com"
        )
        db_session.add(vendor)
        db_session.commit()

        product = Product(
            vendor_id=vendor.id,
            name="Test Product",
            category="furniture",
            price=Decimal("299.99"),
        )
        db_session.add(product)
        db_session.commit()

        staging = DesignStaging(
            design_id=1,
            product_id=product.id,
            position={"x": 0.0, "y": 0.0, "z": 0.0},
            rotation={"x": 0.0, "y": 0.0, "z": 0.0},
            scale={"x": 1.0, "y": 1.0, "z": 1.0},
        )
        db_session.add(staging)
        db_session.commit()

        staging_id = staging.id

        # Delete product
        db_session.delete(product)
        db_session.commit()

        # Staging should be deleted
        deleted_staging = (
            db_session.query(DesignStaging).filter_by(id=staging_id).first()
        )
        assert deleted_staging is None

    def test_multiple_products_in_design(self, db_session):
        """Test staging multiple products in one design."""
        vendor = Vendor(
            user_id=1, company_name="Test Vendor", email="vendor@example.com"
        )
        db_session.add(vendor)
        db_session.commit()

        product1 = Product(
            vendor_id=vendor.id,
            name="Product 1",
            category="furniture",
            price=Decimal("299.99"),
        )
        product2 = Product(
            vendor_id=vendor.id,
            name="Product 2",
            category="fixtures",
            price=Decimal("199.99"),
        )
        db_session.add_all([product1, product2])
        db_session.commit()

        # Stage both products in same design
        staging1 = DesignStaging(
            design_id=1,
            product_id=product1.id,
            position={"x": 0.0, "y": 0.0, "z": 0.0},
            rotation={"x": 0.0, "y": 0.0, "z": 0.0},
            scale={"x": 1.0, "y": 1.0, "z": 1.0},
        )
        staging2 = DesignStaging(
            design_id=1,
            product_id=product2.id,
            position={"x": 5.0, "y": 0.0, "z": 0.0},
            rotation={"x": 0.0, "y": 90.0, "z": 0.0},
            scale={"x": 1.0, "y": 1.0, "z": 1.0},
        )
        db_session.add_all([staging1, staging2])
        db_session.commit()

        # Query design's staged products
        design_staging = db_session.query(DesignStaging).filter_by(design_id=1).all()
        assert len(design_staging) == 2

    def test_same_product_multiple_designs(self, db_session):
        """Test staging same product in multiple designs."""
        vendor = Vendor(
            user_id=1, company_name="Test Vendor", email="vendor@example.com"
        )
        db_session.add(vendor)
        db_session.commit()

        product = Product(
            vendor_id=vendor.id,
            name="Popular Product",
            category="furniture",
            price=Decimal("299.99"),
        )
        db_session.add(product)
        db_session.commit()

        # Stage same product in different designs
        staging1 = DesignStaging(
            design_id=1,
            product_id=product.id,
            position={"x": 0.0, "y": 0.0, "z": 0.0},
            rotation={"x": 0.0, "y": 0.0, "z": 0.0},
            scale={"x": 1.0, "y": 1.0, "z": 1.0},
        )
        staging2 = DesignStaging(
            design_id=2,
            product_id=product.id,
            position={"x": 10.0, "y": 5.0, "z": 2.0},
            rotation={"x": 0.0, "y": 45.0, "z": 0.0},
            scale={"x": 1.5, "y": 1.5, "z": 1.5},
        )
        db_session.add_all([staging1, staging2])
        db_session.commit()

        # Query product's usage across designs
        product_staging = (
            db_session.query(DesignStaging).filter_by(product_id=product.id).all()
        )
        assert len(product_staging) == 2
