"""Property-based tests for input validation.

Feature: architectural-service
Property 46: Input validation error details

For any API request with invalid input, the validation error response should
include field-level details indicating which fields failed validation and why.

Validates: Requirements 12.4
"""

import pytest
from hypothesis import given
from hypothesis import strategies as st
from pydantic import ValidationError
from src.api.v1.schemas import (BuildingType, CreateDesignRequest,
                                LocationData, UpdateDesignRequest)

# ============================================================================
# Hypothesis Strategies
# ============================================================================


@st.composite
def invalid_design_names(draw):
    """Generate invalid design names."""
    return draw(
        st.one_of(
            st.just(""),  # Empty string
            st.just("   "),  # Whitespace only
            st.text(min_size=256, max_size=300),  # Too long
        )
    )


@st.composite
def invalid_locations(draw):
    """Generate invalid location data."""
    return draw(
        st.one_of(
            # Missing required country field
            st.fixed_dictionaries(
                {
                    "city": st.text(max_size=100),
                    "state": st.text(max_size=100),
                }
            ),
            # Invalid latitude
            st.fixed_dictionaries(
                {
                    "country": st.text(max_size=100),
                    "latitude": st.floats(min_value=91, max_value=180),
                    "longitude": st.floats(min_value=-180, max_value=180),
                }
            ),
            # Invalid longitude
            st.fixed_dictionaries(
                {
                    "country": st.text(max_size=100),
                    "latitude": st.floats(min_value=-90, max_value=90),
                    "longitude": st.floats(min_value=181, max_value=360),
                }
            ),
        )
    )


# ============================================================================
# Property Tests
# ============================================================================


@given(name=invalid_design_names())
def test_property_invalid_design_name_provides_field_details(name):
    """
    Property 46: Input validation error details

    For any CreateDesignRequest with an invalid name, the validation error
    should include field-level details indicating the 'name' field failed
    validation with a specific error message.

    Validates: Requirements 12.4
    """
    # Arrange: Create request with invalid name
    request_data = {
        "project_id": "550e8400-e29b-41d4-a716-446655440000",
        "name": name,
        "building_type": "residential",
        "location": {
            "country": "United States",
            "city": "San Francisco",
            "state": "California",
        },
    }

    # Act & Assert: Validation should fail with field-level details
    with pytest.raises(ValidationError) as exc_info:
        CreateDesignRequest(**request_data)

    # Verify error structure
    errors = exc_info.value.errors()
    assert len(errors) > 0, "Should have at least one validation error"

    # Check that error includes field information
    name_errors = [e for e in errors if "name" in str(e.get("loc", []))]
    assert len(name_errors) > 0, "Should have error for 'name' field"

    # Check that error includes message
    for error in name_errors:
        assert "msg" in error, "Error should include message"
        assert error["msg"], "Error message should not be empty"
        assert "type" in error, "Error should include type"


@given(location_data=invalid_locations())
def test_property_invalid_location_provides_field_details(location_data):
    """
    Property 46: Input validation error details

    For any CreateDesignRequest with invalid location data, the validation
    error should include field-level details indicating which location fields
    failed validation.

    Validates: Requirements 12.4
    """
    # Arrange: Create request with invalid location
    request_data = {
        "project_id": "550e8400-e29b-41d4-a716-446655440000",
        "name": "Test Design",
        "building_type": "residential",
        "location": location_data,
    }

    # Act & Assert: Validation should fail with field-level details
    with pytest.raises(ValidationError) as exc_info:
        CreateDesignRequest(**request_data)

    # Verify error structure
    errors = exc_info.value.errors()
    assert len(errors) > 0, "Should have at least one validation error"

    # Check that errors include field information
    for error in errors:
        assert "loc" in error, "Error should include location (field path)"
        assert "msg" in error, "Error should include message"
        assert "type" in error, "Error should include type"
        assert error["msg"], "Error message should not be empty"


def test_property_invalid_description_length_provides_details():
    """
    Property 46: Input validation error details

    For any UpdateDesignRequest with description exceeding max length (5000),
    the validation error should include field-level details.

    Validates: Requirements 12.4
    """
    # Arrange: Create update request with too-long description (5001 chars)
    description = "x" * 5001
    request_data = {
        "name": "Updated Design",
        "description": description,
    }

    # Act & Assert: Validation should fail with field-level details
    with pytest.raises(ValidationError) as exc_info:
        UpdateDesignRequest(**request_data)

    # Verify error structure
    errors = exc_info.value.errors()
    assert len(errors) > 0, "Should have at least one validation error"

    # Check for description error
    description_errors = [e for e in errors if "description" in str(e.get("loc", []))]
    assert len(description_errors) > 0, "Should have error for 'description'"

    # Verify error details
    for error in description_errors:
        assert "msg" in error, "Error should include message"
        assert "type" in error, "Error should include type"
        assert error["msg"], "Error message should not be empty"


def test_property_empty_update_request_provides_details():
    """
    Property 46: Input validation error details

    For any UpdateDesignRequest with no fields to update (all None),
    the validation error should indicate that at least one field must be
    provided.

    Validates: Requirements 12.4
    """
    # Arrange: Create update request with no fields
    request_data = {}

    # Act & Assert: Validation should fail with field-level details
    with pytest.raises(ValidationError) as exc_info:
        UpdateDesignRequest(**request_data)

    # Verify error structure
    errors = exc_info.value.errors()
    assert len(errors) > 0, "Should have at least one validation error"

    # Check that error message indicates the issue
    error_messages = [e.get("msg", "") for e in errors]
    assert any(
        "at least one field" in msg.lower() for msg in error_messages
    ), "Error should indicate at least one field must be provided"


@given(
    metadata=st.one_of(
        st.lists(st.text()),  # List instead of dict
        st.text(),  # String instead of dict
        st.integers(),  # Integer instead of dict
    )
)
def test_property_invalid_metadata_type_provides_details(metadata):
    """
    Property 46: Input validation error details

    For any CreateDesignRequest with invalid metadata type (not a dict),
    the validation error should include field-level details.

    Validates: Requirements 12.4
    """
    # Arrange: Create request with invalid metadata type
    request_data = {
        "project_id": "550e8400-e29b-41d4-a716-446655440000",
        "name": "Test Design",
        "building_type": "residential",
        "location": {
            "country": "United States",
        },
        "metadata": metadata,
    }

    # Act & Assert: Validation should fail with field-level details
    with pytest.raises(ValidationError) as exc_info:
        CreateDesignRequest(**request_data)

    # Verify error structure
    errors = exc_info.value.errors()
    assert len(errors) > 0, "Should have at least one validation error"

    # Check for metadata error
    metadata_errors = [e for e in errors if "metadata" in str(e.get("loc", []))]
    assert len(metadata_errors) > 0, "Should have error for 'metadata'"

    # Verify error details
    for error in metadata_errors:
        assert "msg" in error, "Error should include message"
        assert "type" in error, "Error should include type"


@given(project_id=st.text().filter(lambda x: x != "" and len(x) != 36))
def test_property_invalid_uuid_format_provides_details(project_id):
    """
    Property 46: Input validation error details

    For any CreateDesignRequest with invalid UUID format for project_id,
    the validation error should include field-level details.

    Validates: Requirements 12.4
    """
    # Arrange: Create request with invalid UUID
    request_data = {
        "project_id": project_id,
        "name": "Test Design",
        "building_type": "residential",
        "location": {
            "country": "United States",
        },
    }

    # Act & Assert: Validation should fail with field-level details
    with pytest.raises(ValidationError) as exc_info:
        CreateDesignRequest(**request_data)

    # Verify error structure
    errors = exc_info.value.errors()
    assert len(errors) > 0, "Should have at least one validation error"

    # Check for project_id error
    project_id_errors = [e for e in errors if "project_id" in str(e.get("loc", []))]
    assert len(project_id_errors) > 0, "Should have error for 'project_id'"

    # Verify error details
    for error in project_id_errors:
        assert "msg" in error, "Error should include message"
        assert "type" in error, "Error should include type"


def test_property_multiple_validation_errors_all_reported():
    """
    Property 46: Input validation error details

    For any request with multiple validation errors, all errors should be
    reported with field-level details, not just the first error.

    Validates: Requirements 12.4
    """
    # Arrange: Create request with multiple invalid fields
    request_data = {
        "project_id": "invalid-uuid",
        "name": "",  # Empty name
        "building_type": "invalid_type",  # Invalid enum value
        "location": {
            # Missing required country field
            "latitude": 200,  # Invalid latitude
        },
    }

    # Act & Assert: Validation should fail with multiple errors
    with pytest.raises(ValidationError) as exc_info:
        CreateDesignRequest(**request_data)

    # Verify multiple errors are reported
    errors = exc_info.value.errors()
    assert len(errors) >= 2, "Should have multiple validation errors"

    # Verify each error has proper structure
    for error in errors:
        assert "loc" in error, "Each error should include location"
        assert "msg" in error, "Each error should include message"
        assert "type" in error, "Each error should include type"
        assert error["msg"], "Each error message should not be empty"

    # Verify different fields are reported
    error_fields = set()
    for error in errors:
        loc = error.get("loc", ())
        if loc:
            error_fields.add(loc[0])

    assert len(error_fields) >= 2, "Multiple different fields should have errors"


# ============================================================================
# Unit Tests for Specific Validation Cases
# ============================================================================


def test_location_data_validates_latitude_range():
    """Test that LocationData validates latitude is between -90 and 90."""
    # Valid latitude
    valid_location = LocationData(
        country="United States", latitude=45.0, longitude=-122.0
    )
    assert valid_location.latitude == 45.0

    # Invalid latitude (too high)
    with pytest.raises(ValidationError) as exc_info:
        LocationData(country="United States", latitude=91.0, longitude=-122.0)
    errors = exc_info.value.errors()
    assert any("latitude" in str(e.get("loc", [])) for e in errors)

    # Invalid latitude (too low)
    with pytest.raises(ValidationError) as exc_info:
        LocationData(country="United States", latitude=-91.0, longitude=-122.0)
    errors = exc_info.value.errors()
    assert any("latitude" in str(e.get("loc", [])) for e in errors)


def test_location_data_validates_longitude_range():
    """Test that LocationData validates longitude is between -180 and 180."""
    # Valid longitude
    valid_location = LocationData(
        country="United States", latitude=45.0, longitude=-122.0
    )
    assert valid_location.longitude == -122.0

    # Invalid longitude (too high)
    with pytest.raises(ValidationError) as exc_info:
        LocationData(country="United States", latitude=45.0, longitude=181.0)
    errors = exc_info.value.errors()
    assert any("longitude" in str(e.get("loc", [])) for e in errors)

    # Invalid longitude (too low)
    with pytest.raises(ValidationError) as exc_info:
        LocationData(country="United States", latitude=45.0, longitude=-181.0)
    errors = exc_info.value.errors()
    assert any("longitude" in str(e.get("loc", [])) for e in errors)


def test_design_name_strips_whitespace():
    """Test that design name validator strips whitespace."""
    request = CreateDesignRequest(
        project_id="550e8400-e29b-41d4-a716-446655440000",
        name="  Test Design  ",
        building_type=BuildingType.RESIDENTIAL,
        location=LocationData(country="United States"),
    )
    assert request.name == "Test Design"


def test_design_name_rejects_whitespace_only():
    """Test that design name validator rejects whitespace-only strings."""
    with pytest.raises(ValidationError) as exc_info:
        CreateDesignRequest(
            project_id="550e8400-e29b-41d4-a716-446655440000",
            name="   ",
            building_type=BuildingType.RESIDENTIAL,
            location=LocationData(country="United States"),
        )

    errors = exc_info.value.errors()
    # Should have error for name field
    assert any("name" in str(e.get("loc", [])) for e in errors)
    # The error should indicate the string is too short (after stripping)
    name_errors = [e for e in errors if "name" in str(e.get("loc", []))]
    assert len(name_errors) > 0
    # Verify error has proper structure
    for error in name_errors:
        assert "msg" in error
        assert "type" in error
