"""Tests for Product model."""

from datetime import datetime
from decimal import Decimal

import pytest
from src.models.product import Product
from src.models.vendor import Vendor


class TestProductModel:
    """Test Product model functionality."""

    def test_create_product(self):
        """Test creating a product with valid data."""
        product = Product(
            vendor_id=1,
            name="Test Product",
            category="materials",
            price=Decimal("99.99"),
            description="A test product",
            inventory_quantity=100,
        )

        assert product.vendor_id == 1
        assert product.name == "Test Product"
        assert product.category == "materials"
        assert product.price == Decimal("99.99")
        assert product.description == "A test product"
        assert product.inventory_quantity == 100
        assert product.is_active is True
        assert isinstance(product.created_at, datetime)

    def test_product_with_staging_data(self):
        """Test creating a product with 3D staging data."""
        dimensions = {"length": 10.5, "width": 5.0, "height": 3.0}
        product = Product(
            vendor_id=1,
            name="3D Product",
            category="furniture",
            price=Decimal("299.99"),
            model_url="https://storage.example.com/models/chair.glb",
            dimensions=dimensions,
            model_format="glb",
        )

        assert product.model_url == "https://storage.example.com/models/chair.glb"
        assert product.dimensions == dimensions
        assert product.model_format == "glb"
        assert product.has_3d_model() is True

    def test_product_name_validation(self):
        """Test product name validation."""
        with pytest.raises(
            ValueError, match="Product name must be at least 2 characters"
        ):
            Product(vendor_id=1, name="A", category="materials", price=Decimal("10.00"))

        with pytest.raises(
            ValueError, match="Product name cannot exceed 255 characters"
        ):
            Product(
                vendor_id=1,
                name="A" * 256,
                category="materials",
                price=Decimal("10.00"),
            )

    def test_product_category_validation(self):
        """Test product category validation."""
        with pytest.raises(ValueError, match="Invalid category"):
            Product(
                vendor_id=1,
                name="Test Product",
                category="invalid_category",
                price=Decimal("10.00"),
            )

    def test_product_price_validation(self):
        """Test product price validation."""
        with pytest.raises(ValueError, match="Price cannot be negative"):
            Product(
                vendor_id=1,
                name="Test Product",
                category="materials",
                price=Decimal("-10.00"),
            )

        with pytest.raises(ValueError, match="Price exceeds maximum"):
            Product(
                vendor_id=1,
                name="Test Product",
                category="materials",
                price=Decimal("100000000.00"),
            )

    def test_product_inventory_validation(self):
        """Test inventory quantity validation."""
        with pytest.raises(ValueError, match="Inventory quantity cannot be negative"):
            Product(
                vendor_id=1,
                name="Test Product",
                category="materials",
                price=Decimal("10.00"),
                inventory_quantity=-5,
            )

    def test_product_dimensions_validation(self):
        """Test dimensions validation for 3D staging."""
        # Missing required dimension
        with pytest.raises(ValueError, match="Dimensions must include"):
            Product(
                vendor_id=1,
                name="Test Product",
                category="furniture",
                price=Decimal("100.00"),
                dimensions={"length": 10.0, "width": 5.0},  # Missing height
            )

        # Invalid dimension value
        with pytest.raises(ValueError, match="must be a positive number"):
            Product(
                vendor_id=1,
                name="Test Product",
                category="furniture",
                price=Decimal("100.00"),
                dimensions={"length": 10.0, "width": -5.0, "height": 3.0},
            )

    def test_product_model_format_validation(self):
        """Test 3D model format validation."""
        with pytest.raises(ValueError, match="Invalid model format"):
            Product(
                vendor_id=1,
                name="Test Product",
                category="furniture",
                price=Decimal("100.00"),
                model_format="invalid_format",
            )

    def test_product_update_inventory(self):
        """Test updating product inventory."""
        product = Product(
            vendor_id=1,
            name="Test Product",
            category="materials",
            price=Decimal("10.00"),
            inventory_quantity=100,
        )

        product.update_inventory(50)
        assert product.inventory_quantity == 50

    def test_product_adjust_inventory(self):
        """Test adjusting product inventory."""
        product = Product(
            vendor_id=1,
            name="Test Product",
            category="materials",
            price=Decimal("10.00"),
            inventory_quantity=100,
        )

        product.adjust_inventory(-10)
        assert product.inventory_quantity == 90

        product.adjust_inventory(20)
        assert product.inventory_quantity == 110

        with pytest.raises(ValueError, match="Insufficient inventory"):
            product.adjust_inventory(-200)

    def test_product_availability(self):
        """Test product availability checks."""
        product = Product(
            vendor_id=1,
            name="Test Product",
            category="materials",
            price=Decimal("10.00"),
            inventory_quantity=10,
        )

        assert product.is_available() is True
        assert product.is_in_stock() is True

        product.update_inventory(0)
        assert product.is_available() is False
        assert product.is_in_stock() is False

        product.update_inventory(5)
        product.deactivate()
        assert product.is_available() is False
        assert product.is_in_stock() is True

    def test_product_activation(self):
        """Test product activation/deactivation."""
        product = Product(
            vendor_id=1,
            name="Test Product",
            category="materials",
            price=Decimal("10.00"),
        )

        assert product.is_active is True

        product.deactivate()
        assert product.is_active is False

        product.activate()
        assert product.is_active is True

    def test_product_has_3d_model(self):
        """Test 3D model availability check."""
        product = Product(
            vendor_id=1,
            name="Test Product",
            category="furniture",
            price=Decimal("100.00"),
        )

        assert product.has_3d_model() is False

        product.model_url = "https://example.com/model.glb"
        product.dimensions = {"length": 10.0, "width": 5.0, "height": 3.0}
        product.model_format = "glb"

        assert product.has_3d_model() is True

    def test_product_repr(self):
        """Test product string representation."""
        product = Product(
            vendor_id=1,
            name="Test Product",
            category="materials",
            price=Decimal("99.99"),
        )

        repr_str = repr(product)
        assert "Test Product" in repr_str
        assert "materials" in repr_str
        assert "99.99" in repr_str


class TestProductModelDatabase:
    """Test Product model with database."""

    def test_create_product_in_db(self, db_session):
        """Test creating and persisting a product."""
        # Create vendor first
        vendor = Vendor(
            user_id=1, company_name="Test Vendor", email="vendor@example.com"
        )
        db_session.add(vendor)
        db_session.commit()

        # Create product
        product = Product(
            vendor_id=vendor.id,
            name="DB Test Product",
            category="materials",
            price=Decimal("49.99"),
            inventory_quantity=50,
        )
        db_session.add(product)
        db_session.commit()

        assert product.id is not None

        # Retrieve from database
        retrieved = db_session.query(Product).filter_by(name="DB Test Product").first()
        assert retrieved is not None
        assert retrieved.vendor_id == vendor.id
        assert retrieved.price == Decimal("49.99")

    def test_product_vendor_relationship(self, db_session):
        """Test product-vendor relationship."""
        vendor = Vendor(
            user_id=1, company_name="Test Vendor", email="vendor@example.com"
        )
        db_session.add(vendor)
        db_session.commit()

        product = Product(
            vendor_id=vendor.id,
            name="Relationship Test Product",
            category="tools",
            price=Decimal("29.99"),
        )
        db_session.add(product)
        db_session.commit()

        # Test relationship
        assert product.vendor == vendor
        assert product in vendor.products

    def test_product_cascade_delete(self, db_session):
        """Test that products are deleted when vendor is deleted."""
        vendor = Vendor(
            user_id=1, company_name="Test Vendor", email="vendor@example.com"
        )
        db_session.add(vendor)
        db_session.commit()

        product = Product(
            vendor_id=vendor.id,
            name="Cascade Test Product",
            category="equipment",
            price=Decimal("199.99"),
        )
        db_session.add(product)
        db_session.commit()

        product_id = product.id

        # Delete vendor
        db_session.delete(vendor)
        db_session.commit()

        # Product should be deleted
        deleted_product = db_session.query(Product).filter_by(id=product_id).first()
        assert deleted_product is None
