"""Unit tests for MaterialService."""

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from src.api.v1.schemas.analysis import (MaterialProperties,
                                         MaterialSpecificationRequest)
from src.api.v1.schemas.enums import MaterialCategory
from src.core.exceptions import NotFoundError, ValidationError
from src.infrastructure.vendor_service_client import (AvailabilityInfo,
                                                      VendorMaterial)
from src.models.design import Design
from src.models.material_specification import MaterialSpecification
from src.services.material_service import MaterialService


class TestMaterialService:
    """Unit tests for MaterialService."""

    @pytest.fixture
    def mock_material_repository(self):
        """Mock material repository."""
        repo = AsyncMock()
        repo.create = AsyncMock()
        repo.get = AsyncMock()
        repo.update = AsyncMock()
        return repo

    @pytest.fixture
    def mock_design_repository(self):
        """Mock design repository."""
        repo = AsyncMock()
        repo.get = AsyncMock()
        return repo

    @pytest.fixture
    def mock_vendor_client(self):
        """Mock vendor service client."""
        client = AsyncMock()
        client.search_materials = AsyncMock()
        client.get_supplier_info = AsyncMock()
        client.check_availability = AsyncMock()
        return client

    @pytest.fixture
    def material_service(
        self, mock_material_repository, mock_design_repository, mock_vendor_client
    ):
        """MaterialService instance with mocked dependencies."""
        return MaterialService(
            material_repository=mock_material_repository,
            design_repository=mock_design_repository,
            vendor_client=mock_vendor_client,
        )

    @pytest.fixture
    def sample_design(self):
        """Sample design for testing."""
        return Design(
            id=str(uuid4()),
            project_id=str(uuid4()),
            name="Test Design",
            building_type="residential",
            location_data={},
            is_deleted=False,
        )

    @pytest.fixture
    def valid_material_request(self):
        """Valid material specification request."""
        return MaterialSpecificationRequest(
            category=MaterialCategory.STRUCTURAL,
            properties=MaterialProperties(
                type="Steel",
                grade="A992",
                dimensions="W12x26",
                finish="Painted",
                properties={"yield_strength": "50 ksi"},
            ),
            design_elements=[uuid4()],
        )

    async def test_add_material_missing_required_properties(
        self, material_service, mock_design_repository, sample_design
    ):
        """
        Test missing required properties.
        Requirements: 4.1
        """
        # Setup: Mock design exists
        mock_design_repository.get.return_value = sample_design

        # Test case: Missing material type
        invalid_request = MaterialSpecificationRequest(
            category=MaterialCategory.STRUCTURAL,
            properties=MaterialProperties(
                type="",  # Empty type should cause validation error
                grade="A992",
                dimensions="W12x26",
                finish="Painted",
                properties={},
            ),
            design_elements=[],
        )

        with pytest.raises(ValidationError) as exc_info:
            await material_service.add_material(uuid4(), invalid_request)

        assert "Material type is required" in str(exc_info.value)
        assert exc_info.value.details["field"] == "properties.type"

    async def test_add_material_invalid_material_categories(
        self,
        material_service,
        mock_design_repository,
        mock_material_repository,
        mock_vendor_client,
        sample_design,
    ):
        """
        Test invalid material categories.
        Requirements: 4.1
        """
        # Setup: Mock design exists
        mock_design_repository.get.return_value = sample_design
        mock_vendor_client.search_materials.return_value = []

        # Test all valid categories work
        valid_categories = [
            MaterialCategory.STRUCTURAL,
            MaterialCategory.FINISHES,
            MaterialCategory.MECHANICAL,
            MaterialCategory.ELECTRICAL,
            MaterialCategory.PLUMBING,
            MaterialCategory.INSULATION,
            MaterialCategory.ROOFING,
            MaterialCategory.GLAZING,
            MaterialCategory.DOORS_WINDOWS,
            MaterialCategory.HARDWARE,
        ]

        for category in valid_categories:
            request = MaterialSpecificationRequest(
                category=category,
                properties=MaterialProperties(
                    type="Test Material",
                    grade="Grade A",
                    dimensions="10x10",
                    finish="Standard",
                    properties={},
                ),
                design_elements=[],
            )

            # Mock material creation for each category
            created_material = MaterialSpecification(
                id=str(uuid4()),
                design_id=sample_design.id,
                category=category.value,
                material_type=request.properties.type,
                properties=request.properties.model_dump(),
            )
            mock_material_repository.create.return_value = created_material

            # Should not raise validation error for valid categories
            result = await material_service.add_material(uuid4(), request)
            assert result.category == category.value

        # Test that Pydantic validation prevents invalid categories
        # This would be caught at the schema level, not service level
        with pytest.raises(ValueError):
            MaterialSpecificationRequest(
                category="invalid_category",  # This should fail Pydantic validation
                properties=MaterialProperties(
                    type="Test Material",
                    grade="Grade A",
                    dimensions="10x10",
                    finish="Standard",
                    properties={},
                ),
                design_elements=[],
            )

    async def test_add_material_vendor_service_integration_failures(
        self,
        material_service,
        mock_design_repository,
        mock_vendor_client,
        mock_material_repository,
        sample_design,
        valid_material_request,
    ):
        """
        Test vendor service integration failures.
        Requirements: 4.2
        """
        # Setup: Mock design exists
        mock_design_repository.get.return_value = sample_design

        # Setup: Mock vendor service failure
        mock_vendor_client.search_materials.side_effect = Exception(
            "Vendor service unavailable"
        )

        # Setup: Mock material creation (should still work without vendor info)
        created_material = MaterialSpecification(
            id=str(uuid4()),
            design_id=sample_design.id,
            category=valid_material_request.category,  # Already a string
            material_type=valid_material_request.properties.type,
            properties=valid_material_request.properties.model_dump(),
            vendor_material_id=None,  # No vendor info due to failure
            vendor_info=None,
            cost_estimate=None,
        )
        mock_material_repository.create.return_value = created_material

        # Execute: Should succeed despite vendor service failure
        result = await material_service.add_material(uuid4(), valid_material_request)

        # Verify: Material created without vendor info
        assert result is not None
        assert result.vendor_material_id is None
        assert result.vendor_info is None
        assert result.cost_estimate is None

    async def test_add_material_design_not_found(
        self, material_service, mock_design_repository, valid_material_request
    ):
        """
        Test material creation when design doesn't exist.
        Requirements: 4.1
        """
        # Setup: Mock design not found
        mock_design_repository.get.return_value = None

        design_id = uuid4()

        with pytest.raises(NotFoundError) as exc_info:
            await material_service.add_material(design_id, valid_material_request)

        assert f"Design {design_id} not found" in str(exc_info.value)
        assert exc_info.value.details["design_id"] == str(design_id)

    async def test_add_material_design_deleted(
        self, material_service, mock_design_repository, valid_material_request
    ):
        """
        Test material creation when design is deleted.
        Requirements: 4.1
        """
        # Setup: Mock deleted design
        deleted_design = Design(
            id=str(uuid4()),
            project_id=str(uuid4()),
            name="Deleted Design",
            building_type="residential",
            location_data={},
            is_deleted=True,  # Design is deleted
        )
        mock_design_repository.get.return_value = deleted_design

        design_id = uuid4()

        with pytest.raises(ValidationError) as exc_info:
            await material_service.add_material(design_id, valid_material_request)

        assert f"Cannot add material to deleted design {design_id}" in str(
            exc_info.value
        )
        assert exc_info.value.details["design_id"] == str(design_id)

    async def test_search_materials_empty_query(self, material_service):
        """
        Test search with empty query.
        Requirements: 4.2
        """
        with pytest.raises(ValidationError) as exc_info:
            await material_service.search_materials("")

        assert "Search query cannot be empty" in str(exc_info.value)
        assert exc_info.value.details["query"] == ""

    async def test_search_materials_whitespace_query(self, material_service):
        """
        Test search with whitespace-only query.
        Requirements: 4.2
        """
        with pytest.raises(ValidationError) as exc_info:
            await material_service.search_materials("   ")

        assert "Search query cannot be empty" in str(exc_info.value)

    async def test_search_materials_vendor_service_failure(
        self, material_service, mock_vendor_client
    ):
        """
        Test search when vendor service fails.
        Requirements: 4.2
        """
        # Setup: Mock vendor service failure
        mock_vendor_client.search_materials.side_effect = Exception(
            "Connection timeout"
        )

        with pytest.raises(ValidationError) as exc_info:
            await material_service.search_materials("steel")

        assert "Material search failed" in str(exc_info.value)
        assert "Connection timeout" in str(exc_info.value)
        assert exc_info.value.details["query"] == "steel"

    async def test_get_vendor_info_not_found(
        self, material_service, mock_vendor_client
    ):
        """
        Test get vendor info when material not found.
        Requirements: 4.2
        """
        # Setup: Mock vendor service not found
        mock_vendor_client.get_supplier_info.side_effect = Exception(
            "Material not found"
        )

        material_id = uuid4()

        with pytest.raises(NotFoundError) as exc_info:
            await material_service.get_vendor_info(material_id)

        assert f"Vendor information not found for material {material_id}" in str(
            exc_info.value
        )
        assert exc_info.value.details["material_id"] == str(material_id)

    async def test_update_material_pricing_not_found(
        self, material_service, mock_material_repository
    ):
        """
        Test update pricing when material not found.
        Requirements: 4.2
        """
        # Setup: Mock material not found
        mock_material_repository.get.return_value = None

        material_id = uuid4()

        with pytest.raises(NotFoundError) as exc_info:
            await material_service.update_material_pricing(material_id)

        assert f"Material specification {material_id} not found" in str(exc_info.value)
        assert exc_info.value.details["material_id"] == str(material_id)

    async def test_update_material_pricing_no_vendor_info(
        self, material_service, mock_material_repository
    ):
        """
        Test update pricing when material has no vendor info.
        Requirements: 4.2
        """
        # Setup: Mock material without vendor info
        material = MaterialSpecification(
            id=str(uuid4()),
            design_id=str(uuid4()),
            category="structural",
            material_type="Steel",
            properties={"type": "Steel"},
            vendor_material_id=None,  # No vendor info
        )
        mock_material_repository.get.return_value = material

        material_id = uuid4()

        with pytest.raises(ValidationError) as exc_info:
            await material_service.update_material_pricing(material_id)

        assert f"Material {material_id} has no vendor information to update" in str(
            exc_info.value
        )
        assert exc_info.value.details["material_id"] == str(material_id)

    async def test_update_material_pricing_vendor_service_failure(
        self, material_service, mock_material_repository, mock_vendor_client
    ):
        """
        Test update pricing when vendor service fails.
        Requirements: 4.2
        """
        # Setup: Mock material with vendor info
        material = MaterialSpecification(
            id=str(uuid4()),
            design_id=str(uuid4()),
            category="structural",
            material_type="Steel",
            properties={"type": "Steel"},
            vendor_material_id=str(uuid4()),  # Has vendor info
            vendor_info={"vendor_name": "Test Vendor"},
        )
        mock_material_repository.get.return_value = material

        # Setup: Mock vendor service failure
        mock_vendor_client.check_availability.side_effect = Exception(
            "Service unavailable"
        )

        material_id = uuid4()

        with pytest.raises(ValidationError) as exc_info:
            await material_service.update_material_pricing(material_id)

        assert "Failed to update material pricing" in str(exc_info.value)
        assert "Service unavailable" in str(exc_info.value)
        assert exc_info.value.details["material_id"] == str(material_id)

    async def test_validate_material_properties_invalid_design_elements(
        self, material_service, mock_design_repository, sample_design
    ):
        """
        Test validation with invalid design element IDs.
        Requirements: 4.1

        Note: This test focuses on the service's UUID validation logic.
        Pydantic already validates UUID format at the schema level.
        """
        # Setup: Mock design exists
        mock_design_repository.get.return_value = sample_design

        # Test case: Create a request with valid UUID format
        # The service validation will be tested by checking that valid UUIDs pass
        valid_request = MaterialSpecificationRequest(
            category=MaterialCategory.STRUCTURAL,
            properties=MaterialProperties(
                type="Steel",
                grade="A992",
                dimensions="W12x26",
                finish="Painted",
                properties={},
            ),
            design_elements=[uuid4()],  # Valid UUID
        )

        # Mock material creation to verify the service processes valid UUIDs correctly
        from unittest.mock import AsyncMock

        mock_material_repository = AsyncMock()
        mock_vendor_client = AsyncMock()
        mock_vendor_client.search_materials.return_value = []

        created_material = MaterialSpecification(
            id=str(uuid4()),
            design_id=sample_design.id,
            category=valid_request.category,
            material_type=valid_request.properties.type,
            properties=valid_request.properties.model_dump(),
            design_elements=[str(elem_id) for elem_id in valid_request.design_elements],
        )
        mock_material_repository.create.return_value = created_material

        # Create service with mocked dependencies
        test_service = MaterialService(
            material_repository=mock_material_repository,
            design_repository=mock_design_repository,
            vendor_client=mock_vendor_client,
        )

        # Should succeed with valid UUID
        result = await test_service.add_material(uuid4(), valid_request)
        assert result is not None
        assert len(result.design_elements) == 1

        # Test that Pydantic validation prevents invalid UUIDs at schema level
        with pytest.raises(ValueError):
            MaterialSpecificationRequest(
                category=MaterialCategory.STRUCTURAL,
                properties=MaterialProperties(
                    type="Steel",
                    grade="A992",
                    dimensions="W12x26",
                    finish="Painted",
                    properties={},
                ),
                design_elements=[
                    "invalid-uuid"
                ],  # This should fail Pydantic validation
            )

    async def test_add_material_success_with_vendor_info(
        self,
        material_service,
        mock_design_repository,
        mock_material_repository,
        mock_vendor_client,
        sample_design,
        valid_material_request,
    ):
        """
        Test successful material creation with vendor integration.
        Requirements: 4.1, 4.2
        """
        # Setup: Mock design exists
        mock_design_repository.get.return_value = sample_design

        # Setup: Mock vendor search returns material
        vendor_material = VendorMaterial(
            material_id=uuid4(),
            name="Steel Beam W12x26",
            category="structural",
            material_type="Steel",
            description="Structural steel beam",
            properties={"grade": "A992"},
            vendor_id=uuid4(),
            vendor_name="Steel Supply Co",
            price=Decimal("150.00"),
            unit="each",
            in_stock=True,
            lead_time_days=7,
        )
        mock_vendor_client.search_materials.return_value = [vendor_material]

        # Setup: Mock material creation
        created_material = MaterialSpecification(
            id=str(uuid4()),
            design_id=sample_design.id,
            category=valid_material_request.category,  # Already a string
            material_type=valid_material_request.properties.type,
            properties=valid_material_request.properties.model_dump(),
            vendor_material_id=str(vendor_material.material_id),
            vendor_info={
                "vendor_id": str(vendor_material.vendor_id),
                "vendor_name": vendor_material.vendor_name,
                "product_code": vendor_material.name,
                "availability": "in_stock",
                "lead_time_days": vendor_material.lead_time_days,
            },
            cost_estimate=vendor_material.price,
        )
        mock_material_repository.create.return_value = created_material

        # Execute
        result = await material_service.add_material(uuid4(), valid_material_request)

        # Verify
        assert result is not None
        assert result.vendor_material_id == str(vendor_material.material_id)
        assert result.vendor_info["vendor_name"] == vendor_material.vendor_name
        assert result.cost_estimate == vendor_material.price

    async def test_update_material_pricing_success(
        self, material_service, mock_material_repository, mock_vendor_client
    ):
        """
        Test successful material pricing update.
        Requirements: 4.2
        """
        # Setup: Mock existing material
        original_material = MaterialSpecification(
            id=str(uuid4()),
            design_id=str(uuid4()),
            category="structural",
            material_type="Steel",
            properties={"type": "Steel", "grade": "A992"},
            vendor_material_id=str(uuid4()),
            vendor_info={"vendor_name": "Test Vendor"},
            cost_estimate=Decimal("100.00"),
        )
        mock_material_repository.get.return_value = original_material

        # Setup: Mock availability check returns updated pricing
        availability_info = AvailabilityInfo(
            material_id=uuid4(),
            in_stock=True,
            price=Decimal("120.00"),
            lead_time_days=5,
        )
        mock_vendor_client.check_availability.return_value = availability_info

        # Setup: Mock update operation
        updated_material = MaterialSpecification(
            id=original_material.id,
            design_id=original_material.design_id,
            category=original_material.category,
            material_type=original_material.material_type,
            properties=original_material.properties,
            vendor_material_id=original_material.vendor_material_id,
            vendor_info=original_material.vendor_info.copy(),
            cost_estimate=availability_info.price,
        )
        mock_material_repository.update.return_value = updated_material

        # Execute
        result = await material_service.update_material_pricing(uuid4())

        # Verify
        assert result.cost_estimate == availability_info.price
        mock_material_repository.update.assert_called_once()
        call_args = mock_material_repository.update.call_args
        assert "cost_estimate" in call_args[1]
        assert "updated_at" in call_args[1]

    async def test_validate_material_properties_structural_missing_grade(
        self,
        material_service,
        mock_design_repository,
        mock_material_repository,
        mock_vendor_client,
        sample_design,
    ):
        """
        Test structural material validation with missing grade (warning case).
        Requirements: 4.1
        """
        # Setup: Mock design exists
        mock_design_repository.get.return_value = sample_design
        mock_vendor_client.search_materials.return_value = []

        # Create structural material request without grade
        request = MaterialSpecificationRequest(
            category=MaterialCategory.STRUCTURAL,
            properties=MaterialProperties(
                type="Steel",
                grade=None,  # Missing grade for structural material
                dimensions="W12x26",
                finish="Painted",
                properties={},
            ),
            design_elements=[],
        )

        # Mock material creation
        created_material = MaterialSpecification(
            id=str(uuid4()),
            design_id=sample_design.id,
            category=request.category,  # Already a string value
            material_type=request.properties.type,
            properties=request.properties.model_dump(),
        )
        mock_material_repository.create.return_value = created_material

        # Should succeed but log warning (not raise exception)
        result = await material_service.add_material(uuid4(), request)
        assert result is not None
        assert result.material_type == "Steel"

    async def test_validate_material_properties_finishes_missing_finish(
        self,
        material_service,
        mock_design_repository,
        mock_material_repository,
        mock_vendor_client,
        sample_design,
    ):
        """
        Test finish material validation with missing finish specification (warning case).
        Requirements: 4.1
        """
        # Setup: Mock design exists
        mock_design_repository.get.return_value = sample_design
        mock_vendor_client.search_materials.return_value = []

        # Create finish material request without finish
        request = MaterialSpecificationRequest(
            category=MaterialCategory.FINISHES,
            properties=MaterialProperties(
                type="Paint",
                grade="Premium",
                dimensions=None,
                finish=None,  # Missing finish for finish material
                properties={"color": "White"},
            ),
            design_elements=[],
        )

        # Mock material creation
        created_material = MaterialSpecification(
            id=str(uuid4()),
            design_id=sample_design.id,
            category=request.category,  # Already a string value
            material_type=request.properties.type,
            properties=request.properties.model_dump(),
        )
        mock_material_repository.create.return_value = created_material

        # Should succeed but log warning (not raise exception)
        result = await material_service.add_material(uuid4(), request)
        assert result is not None
        assert result.material_type == "Paint"

    async def test_add_material_empty_properties_dict(
        self,
        material_service,
        mock_design_repository,
        mock_material_repository,
        mock_vendor_client,
        sample_design,
    ):
        """
        Test material creation with empty properties dictionary.
        Requirements: 4.1
        """
        # Setup: Mock design exists
        mock_design_repository.get.return_value = sample_design
        mock_vendor_client.search_materials.return_value = []

        # Create request with empty properties dict
        request = MaterialSpecificationRequest(
            category=MaterialCategory.MECHANICAL,
            properties=MaterialProperties(
                type="HVAC Unit",
                grade="Commercial",
                dimensions="48x24x12",
                finish="Galvanized",
                properties={},  # Empty properties dict should be allowed
            ),
            design_elements=[],
        )

        # Mock material creation
        created_material = MaterialSpecification(
            id=str(uuid4()),
            design_id=sample_design.id,
            category=request.category,  # Already a string value
            material_type=request.properties.type,
            properties=request.properties.model_dump(),
        )
        mock_material_repository.create.return_value = created_material

        # Should succeed with empty properties
        result = await material_service.add_material(uuid4(), request)
        assert result is not None
        assert result.properties["properties"] == {}

    async def test_search_materials_invalid_price_range(
        self, material_service, mock_vendor_client
    ):
        """
        Test search with invalid price range (min > max).
        Requirements: 4.2
        """
        # Setup: Mock vendor client to return empty results
        mock_vendor_client.search_materials.return_value = []

        # Test with min_price > max_price - should still work as vendor service handles validation
        results = await material_service.search_materials(
            query="steel",
            min_price=Decimal("1000.00"),
            max_price=Decimal("500.00"),  # max < min
        )

        # Should return empty results without error (vendor service handles the logic)
        assert results == []

    async def test_search_materials_negative_price(
        self, material_service, mock_vendor_client
    ):
        """
        Test search with negative price values.
        Requirements: 4.2
        """
        # Setup: Mock vendor client to return empty results
        mock_vendor_client.search_materials.return_value = []

        # Test with negative prices - should work as vendor service validates
        results = await material_service.search_materials(
            query="steel",
            min_price=Decimal("-100.00"),  # Negative price
            max_price=Decimal("500.00"),
        )

        # Should return empty results without error
        assert results == []

    async def test_add_material_vendor_service_partial_failure(
        self,
        material_service,
        mock_design_repository,
        mock_material_repository,
        mock_vendor_client,
        sample_design,
        valid_material_request,
    ):
        """
        Test vendor service returns empty results (not an exception).
        Requirements: 4.2
        """
        # Setup: Mock design exists
        mock_design_repository.get.return_value = sample_design

        # Setup: Mock vendor service returns empty results (no materials found)
        mock_vendor_client.search_materials.return_value = []

        # Setup: Mock material creation (should still work without vendor info)
        created_material = MaterialSpecification(
            id=str(uuid4()),
            design_id=sample_design.id,
            category=valid_material_request.category,  # Already a string value
            material_type=valid_material_request.properties.type,
            properties=valid_material_request.properties.model_dump(),
            vendor_material_id=None,  # No vendor info
            vendor_info=None,
            cost_estimate=None,
        )
        mock_material_repository.create.return_value = created_material

        # Execute: Should succeed without vendor info
        result = await material_service.add_material(uuid4(), valid_material_request)

        # Verify: Material created without vendor info
        assert result is not None
        assert result.vendor_material_id is None
        assert result.vendor_info is None
        assert result.cost_estimate is None

    async def test_add_material_vendor_service_timeout(
        self,
        material_service,
        mock_design_repository,
        mock_material_repository,
        mock_vendor_client,
        sample_design,
        valid_material_request,
    ):
        """
        Test vendor service timeout handling.
        Requirements: 4.2
        """
        # Setup: Mock design exists
        mock_design_repository.get.return_value = sample_design

        # Setup: Mock vendor service timeout
        import asyncio

        mock_vendor_client.search_materials.side_effect = asyncio.TimeoutError(
            "Request timeout"
        )

        # Setup: Mock material creation (should still work without vendor info)
        created_material = MaterialSpecification(
            id=str(uuid4()),
            design_id=sample_design.id,
            category=valid_material_request.category,  # Already a string value
            material_type=valid_material_request.properties.type,
            properties=valid_material_request.properties.model_dump(),
            vendor_material_id=None,  # No vendor info due to timeout
            vendor_info=None,
            cost_estimate=None,
        )
        mock_material_repository.create.return_value = created_material

        # Execute: Should succeed despite timeout
        result = await material_service.add_material(uuid4(), valid_material_request)

        # Verify: Material created without vendor info
        assert result is not None
        assert result.vendor_material_id is None
        assert result.vendor_info is None
        assert result.cost_estimate is None

    async def test_add_material_multiple_design_elements(
        self,
        material_service,
        mock_design_repository,
        mock_material_repository,
        mock_vendor_client,
        sample_design,
    ):
        """
        Test material creation with multiple design elements.
        Requirements: 4.1
        """
        # Setup: Mock design exists
        mock_design_repository.get.return_value = sample_design
        mock_vendor_client.search_materials.return_value = []

        # Create request with multiple design elements
        element_ids = [uuid4(), uuid4(), uuid4()]
        request = MaterialSpecificationRequest(
            category=MaterialCategory.STRUCTURAL,
            properties=MaterialProperties(
                type="Concrete",
                grade="4000 PSI",
                dimensions="8 inch",
                finish="Smooth",
                properties={"compressive_strength": "4000 psi"},
            ),
            design_elements=element_ids,
        )

        # Mock material creation
        created_material = MaterialSpecification(
            id=str(uuid4()),
            design_id=sample_design.id,
            category=request.category,  # Already a string value
            material_type=request.properties.type,
            properties=request.properties.model_dump(),
            design_elements=[str(elem_id) for elem_id in element_ids],
        )
        mock_material_repository.create.return_value = created_material

        # Execute
        result = await material_service.add_material(uuid4(), request)

        # Verify all element IDs are preserved
        assert result is not None
        assert len(result.design_elements) == 3
        for elem_id in element_ids:
            assert str(elem_id) in result.design_elements

    async def test_search_materials_with_all_filters(
        self, material_service, mock_vendor_client
    ):
        """
        Test search with all possible filters applied.
        Requirements: 4.2
        """
        # Setup: Mock vendor search returns materials
        vendor_material = VendorMaterial(
            material_id=uuid4(),
            name="Filtered Steel",
            category="structural",
            material_type="Steel",
            description="High-grade steel",
            properties={"grade": "A992"},
            vendor_id=uuid4(),
            vendor_name="Premium Steel Co",
            price=Decimal("200.00"),
            unit="each",
            in_stock=True,
            lead_time_days=10,
        )
        mock_vendor_client.search_materials.return_value = [vendor_material]

        # Execute search with all filters
        results = await material_service.search_materials(
            query="steel",
            category="structural",
            material_type="Steel",
            min_price=Decimal("100.00"),
            max_price=Decimal("300.00"),
            in_stock=True,
        )

        # Verify results
        assert len(results) == 1
        result = results[0]
        assert result.vendor_info.vendor_name == "Premium Steel Co"
        assert result.cost_estimate == Decimal("200.00")
        assert result.vendor_info.availability == "in_stock"

    async def test_update_material_pricing_vendor_info_update(
        self, material_service, mock_material_repository, mock_vendor_client
    ):
        """
        Test that vendor info is properly updated during pricing update.
        Requirements: 4.2
        """
        # Setup: Mock existing material with vendor info
        original_vendor_info = {
            "vendor_id": str(uuid4()),
            "vendor_name": "Original Vendor",
            "product_code": "ORIG-001",
            "availability": "in_stock",
            "lead_time_days": 5,
        }
        original_material = MaterialSpecification(
            id=str(uuid4()),
            design_id=str(uuid4()),
            category="structural",
            material_type="Steel",
            properties={"type": "Steel", "grade": "A992"},
            vendor_material_id=str(uuid4()),
            vendor_info=original_vendor_info,
            cost_estimate=Decimal("100.00"),
        )
        mock_material_repository.get.return_value = original_material

        # Setup: Mock availability check returns updated info
        availability_info = AvailabilityInfo(
            material_id=uuid4(),
            in_stock=False,  # Changed to out of stock
            price=Decimal("120.00"),  # Price increased
            lead_time_days=14,  # Lead time increased
        )
        mock_vendor_client.check_availability.return_value = availability_info

        # Setup: Mock update operation
        updated_material = MaterialSpecification(
            id=original_material.id,
            design_id=original_material.design_id,
            category=original_material.category,
            material_type=original_material.material_type,
            properties=original_material.properties,
            vendor_material_id=original_material.vendor_material_id,
            vendor_info={
                **original_vendor_info,
                "availability": "out_of_stock",
                "lead_time_days": 14,
            },
            cost_estimate=availability_info.price,
        )
        mock_material_repository.update.return_value = updated_material

        # Execute
        result = await material_service.update_material_pricing(uuid4())

        # Verify vendor info was updated
        assert result.cost_estimate == Decimal("120.00")
        mock_material_repository.update.assert_called_once()
        call_args = mock_material_repository.update.call_args

        # Check that vendor_info was updated
        assert "vendor_info" in call_args[1]
        updated_vendor_info = call_args[1]["vendor_info"]
        assert updated_vendor_info["availability"] == "out_of_stock"
        assert updated_vendor_info["lead_time_days"] == 14
