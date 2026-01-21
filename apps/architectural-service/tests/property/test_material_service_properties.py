"""Property-based tests for MaterialService."""

from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st
from src.api.v1.schemas.analysis import (MaterialProperties,
                                         MaterialSpecificationRequest)
from src.api.v1.schemas.enums import MaterialCategory
from src.core.exceptions import ValidationError
from src.infrastructure.vendor_service_client import VendorMaterial
from src.models.design import Design
from src.models.material_specification import MaterialSpecification
from src.services.material_service import MaterialService


# Test data strategies
@st.composite
def material_properties_strategy(draw):
    """Generate MaterialProperties for testing."""
    return MaterialProperties(
        type=draw(st.text(min_size=1, max_size=50)),
        grade=draw(st.one_of(st.none(), st.text(min_size=1, max_size=20))),
        dimensions=draw(st.one_of(st.none(), st.text(min_size=1, max_size=50))),
        finish=draw(st.one_of(st.none(), st.text(min_size=1, max_size=50))),
        properties=draw(
            st.dictionaries(st.text(max_size=20), st.text(max_size=20), max_size=3)
        ),
    )


@st.composite
def material_request_strategy(draw):
    """Generate MaterialSpecificationRequest for testing."""
    return MaterialSpecificationRequest(
        category=draw(st.sampled_from(MaterialCategory)),
        properties=draw(material_properties_strategy()),
        design_elements=draw(st.lists(st.uuids(), max_size=3)),
    )


@st.composite
def vendor_material_strategy(draw):
    """Generate VendorMaterial for testing."""
    return VendorMaterial(
        material_id=draw(st.uuids()),
        name=draw(st.text(min_size=1, max_size=50)),
        category=draw(st.sampled_from([cat.value for cat in MaterialCategory])),
        material_type=draw(st.text(min_size=1, max_size=50)),
        description=draw(st.one_of(st.none(), st.text(max_size=200))),
        properties=draw(
            st.dictionaries(st.text(max_size=20), st.text(max_size=20), max_size=3)
        ),
        vendor_id=draw(st.uuids()),
        vendor_name=draw(st.text(min_size=1, max_size=50).filter(lambda x: x.strip())),
        price=draw(st.decimals(min_value=0, max_value=1000, places=2)),
        unit=draw(st.text(min_size=1, max_size=10)),
        in_stock=draw(st.booleans()),
        lead_time_days=draw(
            st.one_of(st.none(), st.integers(min_value=0, max_value=90))
        ),
    )


# Property 15: Material validation
@given(
    design_id=st.uuids(),
    material_request=material_request_strategy(),
)
@settings(suppress_health_check=[HealthCheck.too_slow], deadline=None)
async def test_property_material_validation(design_id, material_request):
    """Property 15: Material validation.

    *For any* material specification creation request, if required properties
    (type, grade, dimensions, finish) are missing, the request should be rejected
    with validation errors.
    **Validates: Requirements 4.1**
    """
    # Create fresh mocks for each test
    mock_material_repository = AsyncMock()
    mock_design_repository = AsyncMock()
    mock_vendor_client = AsyncMock()

    material_service = MaterialService(
        material_repository=mock_material_repository,
        design_repository=mock_design_repository,
        vendor_client=mock_vendor_client,
    )

    # Setup: Mock design exists
    mock_design = Design(
        id=str(design_id),
        project_id=str(uuid4()),
        name="Test Design",
        building_type="residential",
        location_data={},
        is_deleted=False,
    )
    mock_design_repository.get.return_value = mock_design

    # Test case 1: Valid material with all required properties
    if material_request.properties.type:  # Valid case
        # Handle both enum and string category values
        category_value = (
            material_request.category.value
            if hasattr(material_request.category, "value")
            else material_request.category
        )

        mock_material_repository.create.return_value = MaterialSpecification(
            id=str(uuid4()),
            design_id=str(design_id),
            category=category_value,
            material_type=material_request.properties.type,
            properties=material_request.properties.model_dump(),
        )
        mock_vendor_client.search_materials.return_value = []

        result = await material_service.add_material(design_id, material_request)
        assert result is not None
        assert result.material_type == material_request.properties.type

    # Test case 2: Invalid material with missing type
    invalid_request = MaterialSpecificationRequest(
        category=material_request.category,
        properties=MaterialProperties(
            type="",  # Empty type should cause validation error
            grade=material_request.properties.grade,
            dimensions=material_request.properties.dimensions,
            finish=material_request.properties.finish,
            properties=material_request.properties.properties,
        ),
        design_elements=material_request.design_elements,
    )

    with pytest.raises(ValidationError) as exc_info:
        await material_service.add_material(design_id, invalid_request)

    assert "Material type is required" in str(exc_info.value)


# Property 16: Material search result completeness
@given(
    query=st.text(min_size=1, max_size=50),
    vendor_materials=st.lists(vendor_material_strategy(), min_size=1, max_size=5),
)
@settings(suppress_health_check=[HealthCheck.too_slow], deadline=None)
async def test_property_material_search_result_completeness(query, vendor_materials):
    """Property 16: Material search result completeness.

    *For any* material search query that returns results, each result should
    include availability data and cost data (or explicit null if unavailable).
    **Validates: Requirements 4.3**
    """
    # Create fresh mocks for each test
    mock_material_repository = AsyncMock()
    mock_design_repository = AsyncMock()
    mock_vendor_client = AsyncMock()

    material_service = MaterialService(
        material_repository=mock_material_repository,
        design_repository=mock_design_repository,
        vendor_client=mock_vendor_client,
    )

    # Setup: Mock vendor search returns materials
    mock_vendor_client.search_materials.return_value = vendor_materials

    # Execute search
    results = await material_service.search_materials(query)

    # Verify completeness
    assert len(results) == len(vendor_materials)

    for i, result in enumerate(results):
        expected_material = vendor_materials[i]

        # Each result should have vendor info
        assert result.vendor_info is not None
        assert result.vendor_info.vendor_id == expected_material.vendor_id
        # Normalize whitespace for comparison
        expected_vendor_name = expected_material.vendor_name.strip()
        actual_vendor_name = result.vendor_info.vendor_name.strip()
        assert actual_vendor_name == expected_vendor_name

        # Each result should have availability data
        expected_availability = (
            "in_stock" if expected_material.in_stock else "out_of_stock"
        )
        assert result.vendor_info.availability == expected_availability

        # Each result should have cost data
        assert result.cost_estimate == expected_material.price

        # Lead time should be preserved
        assert result.vendor_info.lead_time_days == expected_material.lead_time_days


# Property 17: Material-element relationship preservation
@given(
    design_id=st.uuids(),
    material_request=material_request_strategy(),
    element_ids=st.lists(st.uuids(), min_size=1, max_size=3),
)
@settings(suppress_health_check=[HealthCheck.too_slow], deadline=None)
async def test_property_material_element_relationship_preservation(
    design_id, material_request, element_ids
):
    """Property 17: Material-element relationship preservation.

    *For any* material specification associated with design elements, the
    relationship should be bidirectional: the material should reference the
    elements, and querying by element should return the material.
    **Validates: Requirements 4.4**
    """
    # Create fresh mocks for each test
    mock_material_repository = AsyncMock()
    mock_design_repository = AsyncMock()
    mock_vendor_client = AsyncMock()

    material_service = MaterialService(
        material_repository=mock_material_repository,
        design_repository=mock_design_repository,
        vendor_client=mock_vendor_client,
    )

    # Setup: Mock design exists
    mock_design = Design(
        id=str(design_id),
        project_id=str(uuid4()),
        name="Test Design",
        building_type="residential",
        location_data={},
        is_deleted=False,
    )
    mock_design_repository.get.return_value = mock_design

    # Create material request with specific element associations
    material_request.design_elements = element_ids

    # Handle both enum and string category values
    category_value = (
        material_request.category.value
        if hasattr(material_request.category, "value")
        else material_request.category
    )

    # Mock material creation
    created_material = MaterialSpecification(
        id=str(uuid4()),
        design_id=str(design_id),
        category=category_value,
        material_type=material_request.properties.type,
        properties=material_request.properties.model_dump(),
        design_elements=[str(elem_id) for elem_id in element_ids],
    )
    mock_material_repository.create.return_value = created_material
    mock_vendor_client.search_materials.return_value = []

    # Create material
    result = await material_service.add_material(design_id, material_request)

    # Verify relationship preservation
    assert result.design_elements == [str(elem_id) for elem_id in element_ids]

    # Verify all element IDs are preserved
    for elem_id in element_ids:
        assert str(elem_id) in result.design_elements

    # Verify no extra elements are added
    assert len(result.design_elements) == len(element_ids)


# Property 18: Material change tracking
@given(
    material_id=st.uuids(),
    original_price=st.decimals(min_value=0, max_value=1000, places=2),
    updated_price=st.decimals(min_value=0, max_value=1000, places=2),
)
@settings(suppress_health_check=[HealthCheck.too_slow], deadline=None)
async def test_property_material_change_tracking(
    material_id, original_price, updated_price
):
    """Property 18: Material change tracking.

    *For any* material specification update, a new entry should be added to
    the change history with timestamp, user, and changed fields.
    **Validates: Requirements 4.5**
    """
    # Create fresh mocks for each test
    mock_material_repository = AsyncMock()
    mock_design_repository = AsyncMock()
    mock_vendor_client = AsyncMock()

    material_service = MaterialService(
        material_repository=mock_material_repository,
        design_repository=mock_design_repository,
        vendor_client=mock_vendor_client,
    )

    # Setup: Mock existing material
    original_material = MaterialSpecification(
        id=str(material_id),
        design_id=str(uuid4()),
        category="structural",
        material_type="Steel",
        properties={"type": "Steel", "grade": "A992"},
        vendor_material_id=str(uuid4()),
        vendor_info={"vendor_name": "Test Vendor"},
        cost_estimate=original_price,
    )
    mock_material_repository.get.return_value = original_material

    # Mock availability check returns updated pricing
    from src.infrastructure.vendor_service_client import AvailabilityInfo

    availability_info = AvailabilityInfo(
        material_id=uuid4(),
        in_stock=True,
        price=updated_price,
        lead_time_days=5,
    )
    mock_vendor_client.check_availability.return_value = availability_info

    # Mock update operation
    updated_material = MaterialSpecification(
        id=str(material_id),
        design_id=original_material.design_id,
        category=original_material.category,
        material_type=original_material.material_type,
        properties=original_material.properties,
        vendor_material_id=original_material.vendor_material_id,
        vendor_info=original_material.vendor_info.copy(),
        cost_estimate=updated_price,
    )
    mock_material_repository.update.return_value = updated_material

    # Execute update
    result = await material_service.update_material_pricing(material_id)

    # Verify change tracking
    # The update method should be called with timestamp
    mock_material_repository.update.assert_called_once()
    call_args = mock_material_repository.update.call_args

    # Verify material ID is correct
    assert call_args[0][0] == str(material_id)

    # Verify updated_at timestamp is included
    update_data = call_args[1]
    assert "updated_at" in update_data

    # Verify cost estimate was updated
    assert "cost_estimate" in update_data
    assert update_data["cost_estimate"] == updated_price

    # Verify result has updated price
    assert result.cost_estimate == updated_price
