"""Tests for ProductRepository."""

from decimal import Decimal

import pytest
from sqlalchemy.orm import Session
from src.models.product import Product
from src.models.vendor import Vendor
from src.repositories.product_repository import ProductRepository
from tests.factories import ProductFactory, VendorFactory


class TestProductRepository:
    """Test suite for ProductRepository."""

    @pytest.fixture
    def vendor(self, db_session: Session) -> Vendor:
        """Create a test vendor."""
        # The db_session fixture will have configured the factories
        vendor = VendorFactory()
        db_session.add(vendor)
        db_session.commit()
        db_session.refresh(vendor)
        return vendor

    @pytest.fixture
    def repository(self, db_session: Session) -> ProductRepository:
        """Create ProductRepository instance."""
        return ProductRepository(db_session)

    def test_create_product(self, repository: ProductRepository, vendor: Vendor):
        """Test creating a product."""
        product = Product(
            vendor_id=vendor.id,
            name="Test Product",
            category="materials",
            price=Decimal("99.99"),
            description="Test description",
            inventory_quantity=100,
        )

        created = repository.create(product)

        assert created.id is not None
        assert created.name == "Test Product"
        assert created.vendor_id == vendor.id
        assert created.price == Decimal("99.99")
        assert created.inventory_quantity == 100

    def test_get_by_id(
        self, repository: ProductRepository, vendor: Vendor, db_session: Session
    ):
        """Test getting product by ID."""
        product = ProductFactory(vendor_id=vendor.id)
        db_session.add(product)
        db_session.commit()

        retrieved = repository.get_by_id(product.id)

        assert retrieved is not None
        assert retrieved.id == product.id
        assert retrieved.name == product.name

    def test_get_by_id_not_found(self, repository: ProductRepository):
        """Test getting non-existent product."""
        result = repository.get_by_id(99999)
        assert result is None

    def test_get_all(
        self, repository: ProductRepository, vendor: Vendor, db_session: Session
    ):
        """Test getting all products with pagination."""
        products = [ProductFactory(vendor_id=vendor.id) for _ in range(5)]
        for product in products:
            db_session.add(product)
        db_session.commit()

        result = repository.get_all(skip=0, limit=10)

        assert len(result) == 5

    def test_get_by_vendor(self, repository: ProductRepository, db_session: Session):
        """Test getting products by vendor."""
        vendor1 = VendorFactory()
        vendor2 = VendorFactory()
        db_session.add(vendor1)
        db_session.add(vendor2)
        db_session.commit()

        # Create products for vendor1
        products_v1 = [ProductFactory(vendor_id=vendor1.id) for _ in range(3)]
        # Create products for vendor2
        products_v2 = [ProductFactory(vendor_id=vendor2.id) for _ in range(2)]

        for product in products_v1 + products_v2:
            db_session.add(product)
        db_session.commit()

        result = repository.get_by_vendor(vendor1.id)

        assert len(result) == 3
        for product in result:
            assert product.vendor_id == vendor1.id

    def test_get_active_by_vendor(
        self, repository: ProductRepository, vendor: Vendor, db_session: Session
    ):
        """Test getting active products by vendor."""
        # Create active and inactive products
        active_product = ProductFactory(vendor_id=vendor.id, is_active=True)
        inactive_product = ProductFactory(vendor_id=vendor.id, is_active=False)

        db_session.add(active_product)
        db_session.add(inactive_product)
        db_session.commit()

        result = repository.get_active_by_vendor(vendor.id)

        assert len(result) == 1
        assert result[0].is_active is True

    def test_filter_by_category(
        self, repository: ProductRepository, vendor: Vendor, db_session: Session
    ):
        """Test filtering products by category."""
        materials_product = ProductFactory(vendor_id=vendor.id, category="materials")
        tools_product = ProductFactory(vendor_id=vendor.id, category="tools")

        db_session.add(materials_product)
        db_session.add(tools_product)
        db_session.commit()

        result = repository.filter_by_category("materials")

        assert len(result) == 1
        assert result[0].category == "materials"

    def test_filter_by_category_and_vendor(
        self, repository: ProductRepository, db_session: Session
    ):
        """Test filtering products by category and vendor."""
        vendor1 = VendorFactory()
        vendor2 = VendorFactory()
        db_session.add(vendor1)
        db_session.add(vendor2)
        db_session.commit()

        # Create products with same category but different vendors
        product_v1 = ProductFactory(vendor_id=vendor1.id, category="materials")
        product_v2 = ProductFactory(vendor_id=vendor2.id, category="materials")

        db_session.add(product_v1)
        db_session.add(product_v2)
        db_session.commit()

        result = repository.filter_by_category_and_vendor("materials", vendor1.id)

        assert len(result) == 1
        assert result[0].vendor_id == vendor1.id
        assert result[0].category == "materials"

    def test_search_products_by_name(
        self, repository: ProductRepository, vendor: Vendor, db_session: Session
    ):
        """Test searching products by name."""
        product1 = ProductFactory(vendor_id=vendor.id, name="Steel Beam")
        product2 = ProductFactory(vendor_id=vendor.id, name="Wood Plank")

        db_session.add(product1)
        db_session.add(product2)
        db_session.commit()

        result = repository.search_products("Steel")

        assert len(result) == 1
        assert "Steel" in result[0].name

    def test_search_products_by_description(
        self, repository: ProductRepository, vendor: Vendor, db_session: Session
    ):
        """Test searching products by description."""
        product1 = ProductFactory(
            vendor_id=vendor.id, description="High quality steel beam"
        )
        product2 = ProductFactory(
            vendor_id=vendor.id, description="Wooden construction material"
        )

        db_session.add(product1)
        db_session.add(product2)
        db_session.commit()

        result = repository.search_products("steel")

        assert len(result) == 1
        assert "steel" in result[0].description.lower()

    def test_search_products_with_price_range(
        self, repository: ProductRepository, vendor: Vendor, db_session: Session
    ):
        """Test searching products with price range."""
        cheap_product = ProductFactory(vendor_id=vendor.id, price=Decimal("10.00"))
        expensive_product = ProductFactory(vendor_id=vendor.id, price=Decimal("100.00"))

        db_session.add(cheap_product)
        db_session.add(expensive_product)
        db_session.commit()

        result = repository.search_products("", min_price=Decimal("50.00"))

        assert len(result) == 1
        assert result[0].price >= Decimal("50.00")

    def test_search_products_in_stock_only(
        self, repository: ProductRepository, vendor: Vendor, db_session: Session
    ):
        """Test searching only in-stock products."""
        in_stock = ProductFactory(vendor_id=vendor.id, inventory_quantity=10)
        out_of_stock = ProductFactory(vendor_id=vendor.id, inventory_quantity=0)

        db_session.add(in_stock)
        db_session.add(out_of_stock)
        db_session.commit()

        result = repository.search_products("", in_stock_only=True)

        assert len(result) == 1
        assert result[0].inventory_quantity > 0

    def test_search_products_active_only(
        self, repository: ProductRepository, vendor: Vendor, db_session: Session
    ):
        """Test searching only active products."""
        active_product = ProductFactory(vendor_id=vendor.id, is_active=True)
        inactive_product = ProductFactory(vendor_id=vendor.id, is_active=False)

        db_session.add(active_product)
        db_session.add(inactive_product)
        db_session.commit()

        result = repository.search_products("", active_only=True)

        assert len(result) == 1
        assert result[0].is_active is True

    def test_get_products_with_3d_models(
        self, repository: ProductRepository, vendor: Vendor, db_session: Session
    ):
        """Test getting products with 3D models."""
        with_model = ProductFactory(
            vendor_id=vendor.id,
            model_url="https://example.com/model.glb",
            dimensions={"length": 10.0, "width": 5.0, "height": 2.0},
            model_format="glb",
        )
        without_model = ProductFactory(vendor_id=vendor.id, model_url=None)

        db_session.add(with_model)
        db_session.add(without_model)
        db_session.commit()

        result = repository.get_products_with_3d_models()

        assert len(result) == 1
        assert result[0].model_url is not None

    def test_get_low_stock_products(
        self, repository: ProductRepository, vendor: Vendor, db_session: Session
    ):
        """Test getting low stock products."""
        low_stock = ProductFactory(
            vendor_id=vendor.id, inventory_quantity=5, is_active=True
        )
        high_stock = ProductFactory(
            vendor_id=vendor.id, inventory_quantity=50, is_active=True
        )

        db_session.add(low_stock)
        db_session.add(high_stock)
        db_session.commit()

        result = repository.get_low_stock_products(threshold=10)

        assert len(result) == 1
        assert result[0].inventory_quantity <= 10

    def test_get_low_stock_products_by_vendor(
        self, repository: ProductRepository, db_session: Session
    ):
        """Test getting low stock products for specific vendor."""
        vendor1 = VendorFactory()
        vendor2 = VendorFactory()
        db_session.add(vendor1)
        db_session.add(vendor2)
        db_session.commit()

        low_stock_v1 = ProductFactory(
            vendor_id=vendor1.id, inventory_quantity=5, is_active=True
        )
        low_stock_v2 = ProductFactory(
            vendor_id=vendor2.id, inventory_quantity=5, is_active=True
        )

        db_session.add(low_stock_v1)
        db_session.add(low_stock_v2)
        db_session.commit()

        result = repository.get_low_stock_products(threshold=10, vendor_id=vendor1.id)

        assert len(result) == 1
        assert result[0].vendor_id == vendor1.id

    def test_get_out_of_stock_products(
        self, repository: ProductRepository, vendor: Vendor, db_session: Session
    ):
        """Test getting out of stock products."""
        out_of_stock = ProductFactory(vendor_id=vendor.id, inventory_quantity=0)
        in_stock = ProductFactory(vendor_id=vendor.id, inventory_quantity=10)

        db_session.add(out_of_stock)
        db_session.add(in_stock)
        db_session.commit()

        result = repository.get_out_of_stock_products()

        assert len(result) == 1
        assert result[0].inventory_quantity == 0

    def test_update_product(
        self, repository: ProductRepository, vendor: Vendor, db_session: Session
    ):
        """Test updating a product."""
        product = ProductFactory(vendor_id=vendor.id, name="Original Name")
        db_session.add(product)
        db_session.commit()

        product.name = "Updated Name"
        updated = repository.update(product)

        assert updated.name == "Updated Name"

    def test_count(
        self, repository: ProductRepository, vendor: Vendor, db_session: Session
    ):
        """Test counting total products."""
        products = [ProductFactory(vendor_id=vendor.id) for _ in range(3)]
        for product in products:
            db_session.add(product)
        db_session.commit()

        count = repository.count()

        assert count == 3

    def test_count_by_vendor(self, repository: ProductRepository, db_session: Session):
        """Test counting products by vendor."""
        vendor1 = VendorFactory()
        vendor2 = VendorFactory()
        db_session.add(vendor1)
        db_session.add(vendor2)
        db_session.commit()

        # Create products for each vendor
        products_v1 = [ProductFactory(vendor_id=vendor1.id) for _ in range(2)]
        products_v2 = [ProductFactory(vendor_id=vendor2.id) for _ in range(3)]

        for product in products_v1 + products_v2:
            db_session.add(product)
        db_session.commit()

        count = repository.count_by_vendor(vendor1.id)

        assert count == 2

    def test_count_by_category(
        self, repository: ProductRepository, vendor: Vendor, db_session: Session
    ):
        """Test counting products by category."""
        materials = [
            ProductFactory(vendor_id=vendor.id, category="materials") for _ in range(2)
        ]
        tools = [
            ProductFactory(vendor_id=vendor.id, category="tools") for _ in range(1)
        ]

        for product in materials + tools:
            db_session.add(product)
        db_session.commit()

        count = repository.count_by_category("materials")

        assert count == 2

    def test_count_active(
        self, repository: ProductRepository, vendor: Vendor, db_session: Session
    ):
        """Test counting active products."""
        active = [ProductFactory(vendor_id=vendor.id, is_active=True) for _ in range(2)]
        inactive = [
            ProductFactory(vendor_id=vendor.id, is_active=False) for _ in range(1)
        ]

        for product in active + inactive:
            db_session.add(product)
        db_session.commit()

        count = repository.count_active()

        assert count == 2

    def test_count_in_stock(
        self, repository: ProductRepository, vendor: Vendor, db_session: Session
    ):
        """Test counting products in stock."""
        in_stock = [
            ProductFactory(vendor_id=vendor.id, inventory_quantity=10) for _ in range(2)
        ]
        out_of_stock = [
            ProductFactory(vendor_id=vendor.id, inventory_quantity=0) for _ in range(1)
        ]

        for product in in_stock + out_of_stock:
            db_session.add(product)
        db_session.commit()

        count = repository.count_in_stock()

        assert count == 2

    def test_delete_product(
        self, repository: ProductRepository, vendor: Vendor, db_session: Session
    ):
        """Test deleting a product."""
        product = ProductFactory(vendor_id=vendor.id)
        db_session.add(product)
        db_session.commit()
        product_id = product.id

        result = repository.delete(product_id)

        assert result is True

        # Verify product is deleted
        deleted_product = repository.get_by_id(product_id)
        assert deleted_product is None

    def test_delete_nonexistent_product(self, repository: ProductRepository):
        """Test deleting non-existent product."""
        result = repository.delete(99999)
        assert result is False
