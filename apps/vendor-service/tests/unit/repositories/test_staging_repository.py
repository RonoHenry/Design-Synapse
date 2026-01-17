"""Tests for StagingRepository."""

from decimal import Decimal

import pytest
from sqlalchemy.orm import Session
from src.models.product import Product
from src.models.staging import DesignStaging
from src.models.vendor import Vendor
from src.repositories.staging_repository import StagingRepository
from tests.factories import DesignStagingFactory, ProductFactory, VendorFactory


class TestStagingRepository:
    """Test cases for StagingRepository."""

    @pytest.fixture
    def repository(self, db_session: Session) -> StagingRepository:
        """Create repository instance."""
        return StagingRepository(db_session)

    @pytest.fixture
    def vendor(self, db_session: Session) -> Vendor:
        """Create a test vendor."""
        vendor = VendorFactory()
        db_session.add(vendor)
        db_session.commit()
        db_session.refresh(vendor)
        return vendor

    @pytest.fixture
    def product(self, db_session: Session, vendor: Vendor) -> Product:
        """Create a test product."""
        product = ProductFactory(
            vendor_id=vendor.id,
            price=Decimal("100.00"),
            dimensions={"length": 2.0, "width": 1.0, "height": 0.5},
        )
        db_session.add(product)
        db_session.commit()
        db_session.refresh(product)
        return product

    def test_create_staging(self, repository: StagingRepository, product: Product):
        """Test creating a new design staging entry."""
        design_id = 1
        position = {"x": 1.0, "y": 2.0, "z": 3.0}
        rotation = {"x": 0.0, "y": 90.0, "z": 0.0}
        scale = {"x": 1.0, "y": 1.0, "z": 1.0}
        quantity = 2

        staging = DesignStaging(
            design_id=design_id,
            product_id=product.id,
            position=position,
            rotation=rotation,
            scale=scale,
            quantity=quantity,
        )

        result = repository.create(staging)

        assert result.id is not None
        assert result.design_id == design_id
        assert result.product_id == product.id
        assert result.position == position
        assert result.rotation == rotation
        assert result.scale == scale
        assert result.quantity == quantity
        assert result.created_at is not None

    def test_get_by_id(
        self, repository: StagingRepository, db_session: Session, product: Product
    ):
        """Test getting staging by ID."""
        staging = DesignStagingFactory(product_id=product.id)
        db_session.add(staging)
        db_session.commit()

        result = repository.get_by_id(staging.id)

        assert result is not None
        assert result.id == staging.id
        assert result.design_id == staging.design_id
        assert result.product_id == staging.product_id

    def test_get_by_id_not_found(self, repository: StagingRepository):
        """Test getting non-existent staging."""
        result = repository.get_by_id(999)
        assert result is None

    def test_get_by_design_id(
        self, repository: StagingRepository, db_session: Session, product: Product
    ):
        """Test getting all staging entries for a design."""
        design_id = 1
        staging1 = DesignStagingFactory(design_id=design_id, product_id=product.id)
        staging2 = DesignStagingFactory(design_id=design_id, product_id=product.id)
        staging3 = DesignStagingFactory(
            design_id=2, product_id=product.id
        )  # Different design

        db_session.add_all([staging1, staging2, staging3])
        db_session.commit()

        result = repository.get_by_design_id(design_id)

        assert len(result) == 2
        assert all(s.design_id == design_id for s in result)

    def test_get_by_design_and_product(
        self, repository: StagingRepository, db_session: Session, product: Product
    ):
        """Test getting staging by design and product."""
        design_id = 1
        staging = DesignStagingFactory(design_id=design_id, product_id=product.id)
        db_session.add(staging)
        db_session.commit()

        result = repository.get_by_design_and_product(design_id, product.id)

        assert result is not None
        assert result.design_id == design_id
        assert result.product_id == product.id

    def test_get_by_design_and_product_not_found(
        self, repository: StagingRepository, product: Product
    ):
        """Test getting non-existent staging by design and product."""
        result = repository.get_by_design_and_product(999, product.id)
        assert result is None

    def test_get_by_product_id(
        self, repository: StagingRepository, db_session: Session, vendor: Vendor
    ):
        """Test getting all staging entries for a product."""
        product1 = ProductFactory(vendor_id=vendor.id)
        product2 = ProductFactory(vendor_id=vendor.id)
        db_session.add_all([product1, product2])
        db_session.commit()

        staging1 = DesignStagingFactory(design_id=1, product_id=product1.id)
        staging2 = DesignStagingFactory(design_id=2, product_id=product1.id)
        staging3 = DesignStagingFactory(
            design_id=1, product_id=product2.id
        )  # Different product

        db_session.add_all([staging1, staging2, staging3])
        db_session.commit()

        result = repository.get_by_product_id(product1.id)

        assert len(result) == 2
        assert all(s.product_id == product1.id for s in result)

    def test_update(
        self, repository: StagingRepository, db_session: Session, product: Product
    ):
        """Test updating staging entry."""
        staging = DesignStagingFactory(product_id=product.id, quantity=1)
        db_session.add(staging)
        db_session.commit()

        staging.quantity = 5
        staging.position = {"x": 10.0, "y": 20.0, "z": 30.0}
        result = repository.update(staging)

        assert result.quantity == 5
        assert result.position == {"x": 10.0, "y": 20.0, "z": 30.0}

    def test_delete(
        self, repository: StagingRepository, db_session: Session, product: Product
    ):
        """Test deleting staging entry."""
        staging = DesignStagingFactory(product_id=product.id)
        db_session.add(staging)
        db_session.commit()
        staging_id = staging.id

        repository.delete(staging)

        # Verify deletion
        result = repository.get_by_id(staging_id)
        assert result is None

    def test_delete_by_id(
        self, repository: StagingRepository, db_session: Session, product: Product
    ):
        """Test deleting staging by ID."""
        staging = DesignStagingFactory(product_id=product.id)
        db_session.add(staging)
        db_session.commit()
        staging_id = staging.id

        success = repository.delete_by_id(staging_id)

        assert success is True
        result = repository.get_by_id(staging_id)
        assert result is None

    def test_delete_by_id_not_found(self, repository: StagingRepository):
        """Test deleting non-existent staging."""
        success = repository.delete_by_id(999)
        assert success is False

    def test_delete_by_design_id(
        self, repository: StagingRepository, db_session: Session, product: Product
    ):
        """Test deleting all staging entries for a design."""
        design_id = 1
        staging1 = DesignStagingFactory(design_id=design_id, product_id=product.id)
        staging2 = DesignStagingFactory(design_id=design_id, product_id=product.id)
        staging3 = DesignStagingFactory(
            design_id=2, product_id=product.id
        )  # Different design

        db_session.add_all([staging1, staging2, staging3])
        db_session.commit()

        count = repository.delete_by_design_id(design_id)

        assert count == 2
        # Verify deletions
        remaining = repository.get_by_design_id(design_id)
        assert len(remaining) == 0
        # Other design should remain
        other_design = repository.get_by_design_id(2)
        assert len(other_design) == 1

    def test_count_by_design(
        self, repository: StagingRepository, db_session: Session, product: Product
    ):
        """Test counting staging entries by design."""
        design_id = 1
        staging1 = DesignStagingFactory(design_id=design_id, product_id=product.id)
        staging2 = DesignStagingFactory(design_id=design_id, product_id=product.id)
        staging3 = DesignStagingFactory(
            design_id=2, product_id=product.id
        )  # Different design

        db_session.add_all([staging1, staging2, staging3])
        db_session.commit()

        count = repository.count_by_design(design_id)
        assert count == 2

    def test_get_design_staging_with_products(
        self, repository: StagingRepository, db_session: Session, vendor: Vendor
    ):
        """Test getting design staging with product details."""
        design_id = 1
        product1 = ProductFactory(
            vendor_id=vendor.id, name="Product 1", price=Decimal("100.00")
        )
        product2 = ProductFactory(
            vendor_id=vendor.id, name="Product 2", price=Decimal("200.00")
        )
        db_session.add_all([product1, product2])
        db_session.commit()

        staging1 = DesignStagingFactory(
            design_id=design_id, product_id=product1.id, quantity=2
        )
        staging2 = DesignStagingFactory(
            design_id=design_id, product_id=product2.id, quantity=1
        )
        db_session.add_all([staging1, staging2])
        db_session.commit()

        result = repository.get_design_staging_with_products(design_id)

        assert len(result) == 2
        # Each result should be a tuple of (staging, product)
        stagings, products = zip(*result)
        assert all(s.design_id == design_id for s in stagings)
        assert len(set(p.name for p in products)) == 2  # Both products present

    def test_get_procurement_list(
        self, repository: StagingRepository, db_session: Session, vendor: Vendor
    ):
        """Test generating procurement list for a design."""
        design_id = 1
        product1 = ProductFactory(
            vendor_id=vendor.id,
            name="Product 1",
            price=Decimal("100.00"),
            inventory_quantity=10,
        )
        product2 = ProductFactory(
            vendor_id=vendor.id,
            name="Product 2",
            price=Decimal("200.00"),
            inventory_quantity=5,
        )
        db_session.add_all([product1, product2])
        db_session.commit()

        staging1 = DesignStagingFactory(
            design_id=design_id, product_id=product1.id, quantity=3
        )
        staging2 = DesignStagingFactory(
            design_id=design_id, product_id=product2.id, quantity=2
        )
        db_session.add_all([staging1, staging2])
        db_session.commit()

        result = repository.get_procurement_list(design_id)

        assert len(result) == 2

        # Check first item
        item1 = next(item for item in result if item["product_name"] == "Product 1")
        assert item1["quantity"] == 3
        assert item1["unit_price"] == Decimal("100.00")
        assert item1["total_price"] == Decimal("300.00")
        assert item1["available_quantity"] == 10

        # Check second item
        item2 = next(item for item in result if item["product_name"] == "Product 2")
        assert item2["quantity"] == 2
        assert item2["unit_price"] == Decimal("200.00")
        assert item2["total_price"] == Decimal("400.00")
        assert item2["available_quantity"] == 5

    def test_get_total_cost_by_design(
        self, repository: StagingRepository, db_session: Session, vendor: Vendor
    ):
        """Test calculating total cost for a design."""
        design_id = 1
        product1 = ProductFactory(vendor_id=vendor.id, price=Decimal("100.00"))
        product2 = ProductFactory(vendor_id=vendor.id, price=Decimal("200.00"))
        db_session.add_all([product1, product2])
        db_session.commit()

        staging1 = DesignStagingFactory(
            design_id=design_id, product_id=product1.id, quantity=3
        )
        staging2 = DesignStagingFactory(
            design_id=design_id, product_id=product2.id, quantity=2
        )
        db_session.add_all([staging1, staging2])
        db_session.commit()

        total_cost = repository.get_total_cost_by_design(design_id)

        # 3 * 100.00 + 2 * 200.00 = 700.00
        assert total_cost == Decimal("700.00")

    def test_get_most_staged_products(
        self, repository: StagingRepository, db_session: Session, vendor: Vendor
    ):
        """Test getting most frequently staged products."""
        product1 = ProductFactory(vendor_id=vendor.id, name="Popular Product")
        product2 = ProductFactory(vendor_id=vendor.id, name="Less Popular Product")
        db_session.add_all([product1, product2])
        db_session.commit()

        # Create multiple staging entries for product1
        stagings = [
            DesignStagingFactory(design_id=1, product_id=product1.id),
            DesignStagingFactory(design_id=2, product_id=product1.id),
            DesignStagingFactory(design_id=3, product_id=product1.id),
            DesignStagingFactory(design_id=1, product_id=product2.id),
        ]
        db_session.add_all(stagings)
        db_session.commit()

        result = repository.get_most_staged_products(limit=2)

        assert len(result) <= 2
        # Should be ordered by staging count descending
        if len(result) >= 2:
            first_product, first_count = result[0]
            second_product, second_count = result[1]
            assert first_count >= second_count
            assert first_product.id == product1.id
            assert first_count == 3

    def test_pagination(
        self, repository: StagingRepository, db_session: Session, product: Product
    ):
        """Test pagination in get_by_design_id."""
        design_id = 1
        stagings = [
            DesignStagingFactory(design_id=design_id, product_id=product.id)
            for _ in range(5)
        ]
        db_session.add_all(stagings)
        db_session.commit()

        # Test first page
        page1 = repository.get_by_design_id(design_id, skip=0, limit=2)
        assert len(page1) == 2

        # Test second page
        page2 = repository.get_by_design_id(design_id, skip=2, limit=2)
        assert len(page2) == 2

        # Test third page
        page3 = repository.get_by_design_id(design_id, skip=4, limit=2)
        assert len(page3) == 1

        # Ensure no overlap
        all_ids = [s.id for s in page1 + page2 + page3]
        assert len(all_ids) == len(set(all_ids))  # All unique
