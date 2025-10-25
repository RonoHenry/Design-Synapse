"""Unit tests for request schemas."""

import pytest
from pydantic import ValidationError

from src.api.v1.schemas.requests import (
    DesignGenerationRequest,
    DesignUpdateRequest,
    ValidationRequest,
    OptimizationRequest,
    GenerateVisualsRequest,
)


class TestDesignGenerationRequest:
    """Tests for DesignGenerationRequest schema."""

    def test_valid_request(self):
        """Test creating a valid design generation request."""
        data = {
            "project_id": 1,
            "name": "Modern Office Building",
            "description": "A 5-story modern office building with open floor plans",
            "building_type": "commercial",
            "requirements": {
                "floors": 5,
                "total_area": 5000,
                "parking_spaces": 50,
            },
        }
        request = DesignGenerationRequest(**data)
        
        assert request.project_id == 1
        assert request.name == "Modern Office Building"
        assert request.description == "A 5-story modern office building with open floor plans"
        assert request.building_type == "commercial"
        assert request.requirements["floors"] == 5

    def test_valid_request_with_empty_requirements(self):
        """Test creating a request with empty requirements dict."""
        data = {
            "project_id": 1,
            "name": "Simple House",
            "description": "A simple residential house",
            "building_type": "residential",
        }
        request = DesignGenerationRequest(**data)
        
        assert request.requirements == {}

    def test_missing_required_field_project_id(self):
        """Test that missing project_id raises validation error."""
        data = {
            "name": "Test Building",
            "description": "Test description",
            "building_type": "residential",
        }
        
        with pytest.raises(ValidationError) as exc_info:
            DesignGenerationRequest(**data)
        
        errors = exc_info.value.errors()
        assert any(error["loc"] == ("project_id",) for error in errors)

    def test_missing_required_field_name(self):
        """Test that missing name raises validation error."""
        data = {
            "project_id": 1,
            "description": "Test description",
            "building_type": "residential",
        }
        
        with pytest.raises(ValidationError) as exc_info:
            DesignGenerationRequest(**data)
        
        errors = exc_info.value.errors()
        assert any(error["loc"] == ("name",) for error in errors)

    def test_missing_required_field_description(self):
        """Test that missing description raises validation error."""
        data = {
            "project_id": 1,
            "name": "Test Building",
            "building_type": "residential",
        }
        
        with pytest.raises(ValidationError) as exc_info:
            DesignGenerationRequest(**data)
        
        errors = exc_info.value.errors()
        assert any(error["loc"] == ("description",) for error in errors)

    def test_missing_required_field_building_type(self):
        """Test that missing building_type raises validation error."""
        data = {
            "project_id": 1,
            "name": "Test Building",
            "description": "Test description",
        }
        
        with pytest.raises(ValidationError) as exc_info:
            DesignGenerationRequest(**data)
        
        errors = exc_info.value.errors()
        assert any(error["loc"] == ("building_type",) for error in errors)

    def test_name_too_short(self):
        """Test that name with length 0 raises validation error."""
        data = {
            "project_id": 1,
            "name": "",
            "description": "Test description",
            "building_type": "residential",
        }
        
        with pytest.raises(ValidationError) as exc_info:
            DesignGenerationRequest(**data)
        
        errors = exc_info.value.errors()
        assert any(error["loc"] == ("name",) for error in errors)

    def test_name_too_long(self):
        """Test that name exceeding 255 characters raises validation error."""
        data = {
            "project_id": 1,
            "name": "x" * 256,
            "description": "Test description",
            "building_type": "residential",
        }
        
        with pytest.raises(ValidationError) as exc_info:
            DesignGenerationRequest(**data)
        
        errors = exc_info.value.errors()
        assert any(error["loc"] == ("name",) for error in errors)

    def test_invalid_project_id_type(self):
        """Test that non-integer project_id raises validation error."""
        data = {
            "project_id": "not_an_int",
            "name": "Test Building",
            "description": "Test description",
            "building_type": "residential",
        }
        
        with pytest.raises(ValidationError) as exc_info:
            DesignGenerationRequest(**data)
        
        errors = exc_info.value.errors()
        assert any(error["loc"] == ("project_id",) for error in errors)

    def test_invalid_requirements_type(self):
        """Test that non-dict requirements raises validation error."""
        data = {
            "project_id": 1,
            "name": "Test Building",
            "description": "Test description",
            "building_type": "residential",
            "requirements": "not_a_dict",
        }
        
        with pytest.raises(ValidationError) as exc_info:
            DesignGenerationRequest(**data)
        
        errors = exc_info.value.errors()
        assert any(error["loc"] == ("requirements",) for error in errors)


class TestDesignUpdateRequest:
    """Tests for DesignUpdateRequest schema."""

    def test_valid_request_all_fields(self):
        """Test creating a valid update request with all fields."""
        data = {
            "name": "Updated Building Name",
            "description": "Updated description",
            "specification": {"building_info": {"type": "residential"}},
            "status": "validated",
        }
        request = DesignUpdateRequest(**data)
        
        assert request.name == "Updated Building Name"
        assert request.description == "Updated description"
        assert request.specification == {"building_info": {"type": "residential"}}
        assert request.status == "validated"

    def test_valid_request_partial_fields(self):
        """Test creating a valid update request with only some fields."""
        data = {
            "name": "Updated Name",
        }
        request = DesignUpdateRequest(**data)
        
        assert request.name == "Updated Name"
        assert request.description is None
        assert request.specification is None
        assert request.status is None

    def test_valid_request_empty(self):
        """Test creating an update request with no fields (all optional)."""
        data = {}
        request = DesignUpdateRequest(**data)
        
        assert request.name is None
        assert request.description is None
        assert request.specification is None
        assert request.status is None

    def test_name_too_short(self):
        """Test that name with length 0 raises validation error."""
        data = {
            "name": "",
        }
        
        with pytest.raises(ValidationError) as exc_info:
            DesignUpdateRequest(**data)
        
        errors = exc_info.value.errors()
        assert any(error["loc"] == ("name",) for error in errors)

    def test_name_too_long(self):
        """Test that name exceeding 255 characters raises validation error."""
        data = {
            "name": "x" * 256,
        }
        
        with pytest.raises(ValidationError) as exc_info:
            DesignUpdateRequest(**data)
        
        errors = exc_info.value.errors()
        assert any(error["loc"] == ("name",) for error in errors)

    def test_invalid_specification_type(self):
        """Test that non-dict specification raises validation error."""
        data = {
            "specification": "not_a_dict",
        }
        
        with pytest.raises(ValidationError) as exc_info:
            DesignUpdateRequest(**data)
        
        errors = exc_info.value.errors()
        assert any(error["loc"] == ("specification",) for error in errors)


class TestValidationRequest:
    """Tests for ValidationRequest schema."""

    def test_valid_request(self):
        """Test creating a valid validation request."""
        data = {
            "validation_type": "building_code",
            "rule_set": "Kenya_Building_Code_2020",
        }
        request = ValidationRequest(**data)
        
        assert request.validation_type == "building_code"
        assert request.rule_set == "Kenya_Building_Code_2020"

    def test_missing_validation_type(self):
        """Test that missing validation_type raises validation error."""
        data = {
            "rule_set": "Kenya_Building_Code_2020",
        }
        
        with pytest.raises(ValidationError) as exc_info:
            ValidationRequest(**data)
        
        errors = exc_info.value.errors()
        assert any(error["loc"] == ("validation_type",) for error in errors)

    def test_missing_rule_set(self):
        """Test that missing rule_set raises validation error."""
        data = {
            "validation_type": "building_code",
        }
        
        with pytest.raises(ValidationError) as exc_info:
            ValidationRequest(**data)
        
        errors = exc_info.value.errors()
        assert any(error["loc"] == ("rule_set",) for error in errors)

    def test_invalid_validation_type_type(self):
        """Test that non-string validation_type raises validation error."""
        data = {
            "validation_type": 123,
            "rule_set": "Kenya_Building_Code_2020",
        }
        
        with pytest.raises(ValidationError) as exc_info:
            ValidationRequest(**data)
        
        errors = exc_info.value.errors()
        assert any(error["loc"] == ("validation_type",) for error in errors)

    def test_invalid_rule_set_type(self):
        """Test that non-string rule_set raises validation error."""
        data = {
            "validation_type": "building_code",
            "rule_set": 123,
        }
        
        with pytest.raises(ValidationError) as exc_info:
            ValidationRequest(**data)
        
        errors = exc_info.value.errors()
        assert any(error["loc"] == ("rule_set",) for error in errors)


class TestOptimizationRequest:
    """Tests for OptimizationRequest schema."""

    def test_valid_request_with_default(self):
        """Test creating a valid optimization request with default types."""
        data = {}
        request = OptimizationRequest(**data)
        
        assert request.optimization_types == ["cost", "structural", "sustainability"]

    def test_valid_request_with_custom_types(self):
        """Test creating a valid optimization request with custom types."""
        data = {
            "optimization_types": ["cost", "energy_efficiency"],
        }
        request = OptimizationRequest(**data)
        
        assert request.optimization_types == ["cost", "energy_efficiency"]

    def test_valid_request_with_single_type(self):
        """Test creating a valid optimization request with single type."""
        data = {
            "optimization_types": ["cost"],
        }
        request = OptimizationRequest(**data)
        
        assert request.optimization_types == ["cost"]

    def test_valid_request_with_empty_list(self):
        """Test creating a valid optimization request with empty list."""
        data = {
            "optimization_types": [],
        }
        request = OptimizationRequest(**data)
        
        assert request.optimization_types == []

    def test_invalid_optimization_types_not_list(self):
        """Test that non-list optimization_types raises validation error."""
        data = {
            "optimization_types": "not_a_list",
        }
        
        with pytest.raises(ValidationError) as exc_info:
            OptimizationRequest(**data)
        
        errors = exc_info.value.errors()
        assert any(error["loc"] == ("optimization_types",) for error in errors)

    def test_invalid_optimization_types_list_with_non_strings(self):
        """Test that list with non-string items raises validation error."""
        data = {
            "optimization_types": ["cost", 123, "structural"],
        }
        
        with pytest.raises(ValidationError) as exc_info:
            OptimizationRequest(**data)
        
        errors = exc_info.value.errors()
        assert any("optimization_types" in error["loc"] for error in errors)


class TestDesignGenerationRequestVisualGeneration:
    """Tests for generate_visuals field in DesignGenerationRequest schema."""

    def test_valid_request_with_generate_visuals_true(self):
        """Test creating a valid design generation request with generate_visuals=True."""
        data = {
            "project_id": 1,
            "name": "Modern Office Building",
            "description": "A 5-story modern office building with open floor plans",
            "building_type": "commercial",
            "requirements": {"floors": 5},
            "generate_visuals": True,
        }
        request = DesignGenerationRequest(**data)
        
        assert request.generate_visuals is True
        assert request.project_id == 1
        assert request.name == "Modern Office Building"

    def test_valid_request_with_generate_visuals_false(self):
        """Test creating a valid design generation request with generate_visuals=False."""
        data = {
            "project_id": 1,
            "name": "Modern Office Building",
            "description": "A 5-story modern office building with open floor plans",
            "building_type": "commercial",
            "requirements": {"floors": 5},
            "generate_visuals": False,
        }
        request = DesignGenerationRequest(**data)
        
        assert request.generate_visuals is False

    def test_valid_request_without_generate_visuals_defaults_to_false(self):
        """Test that generate_visuals defaults to False when not provided."""
        data = {
            "project_id": 1,
            "name": "Modern Office Building",
            "description": "A 5-story modern office building with open floor plans",
            "building_type": "commercial",
            "requirements": {"floors": 5},
        }
        request = DesignGenerationRequest(**data)
        
        assert request.generate_visuals is False  # Default value

    def test_generate_visuals_type_coercion(self):
        """Test that generate_visuals field accepts various truthy/falsy values."""
        data = {
            "project_id": 1,
            "name": "Modern Office Building",
            "description": "A 5-story modern office building with open floor plans",
            "building_type": "commercial",
            "requirements": {"floors": 5},
            "generate_visuals": "yes",  # Should be coerced to True
        }
        
        request = DesignGenerationRequest(**data)
        assert request.generate_visuals is True  # String "yes" is truthy

    def test_generate_visuals_field_validation_rules(self):
        """Test that generate_visuals field has proper validation rules."""
        # Test with integer (should be converted to boolean)
        data = {
            "project_id": 1,
            "name": "Modern Office Building",
            "description": "A 5-story modern office building with open floor plans",
            "building_type": "commercial",
            "requirements": {"floors": 5},
            "generate_visuals": 1,  # Should be converted to True
        }
        request = DesignGenerationRequest(**data)
        assert request.generate_visuals is True

        # Test with 0 (should be converted to False)
        data["generate_visuals"] = 0
        request = DesignGenerationRequest(**data)
        assert request.generate_visuals is False


class TestGenerateVisualsRequest:
    """Tests for GenerateVisualsRequest schema."""

    def test_valid_request_with_defaults(self):
        """Test creating a valid generate visuals request with default values."""
        data = {}
        request = GenerateVisualsRequest(**data)
        
        # Check default values
        assert request.visual_types == ["floor_plan", "rendering", "3d_model"]
        assert request.size == "1024x1024"
        assert request.quality == "standard"
        assert request.priority == "normal"

    def test_valid_request_with_custom_visual_types(self):
        """Test creating a valid generate visuals request with custom visual types."""
        data = {
            "visual_types": ["floor_plan", "rendering"],
        }
        request = GenerateVisualsRequest(**data)
        
        assert request.visual_types == ["floor_plan", "rendering"]
        assert request.size == "1024x1024"  # Default
        assert request.quality == "standard"  # Default

    def test_valid_request_with_single_visual_type(self):
        """Test creating a valid generate visuals request with single visual type."""
        data = {
            "visual_types": ["3d_model"],
        }
        request = GenerateVisualsRequest(**data)
        
        assert request.visual_types == ["3d_model"]

    def test_valid_request_with_custom_size(self):
        """Test creating a valid generate visuals request with custom size."""
        data = {
            "size": "1792x1024",
        }
        request = GenerateVisualsRequest(**data)
        
        assert request.size == "1792x1024"

    def test_valid_request_with_custom_quality(self):
        """Test creating a valid generate visuals request with custom quality."""
        data = {
            "quality": "hd",
        }
        request = GenerateVisualsRequest(**data)
        
        assert request.quality == "hd"

    def test_valid_request_with_custom_priority(self):
        """Test creating a valid generate visuals request with custom priority."""
        data = {
            "priority": "high",
        }
        request = GenerateVisualsRequest(**data)
        
        assert request.priority == "high"

    def test_valid_request_with_all_custom_parameters(self):
        """Test creating a valid generate visuals request with all custom parameters."""
        data = {
            "visual_types": ["floor_plan"],
            "size": "1792x1024",
            "quality": "hd",
            "priority": "high",
        }
        request = GenerateVisualsRequest(**data)
        
        assert request.visual_types == ["floor_plan"]
        assert request.size == "1792x1024"
        assert request.quality == "hd"
        assert request.priority == "high"

    def test_visual_types_empty_list_allowed(self):
        """Test that empty visual_types list is allowed (validation happens at API level)."""
        data = {
            "visual_types": [],
        }
        
        request = GenerateVisualsRequest(**data)
        assert request.visual_types == []

    def test_visual_types_accepts_any_strings(self):
        """Test that visual_types accepts any strings (validation happens at API level)."""
        data = {
            "visual_types": ["floor_plan", "custom_type"],
        }
        
        request = GenerateVisualsRequest(**data)
        assert request.visual_types == ["floor_plan", "custom_type"]

    def test_invalid_visual_types_not_list(self):
        """Test that non-list visual_types raises validation error."""
        data = {
            "visual_types": "floor_plan",
        }
        
        with pytest.raises(ValidationError) as exc_info:
            GenerateVisualsRequest(**data)
        
        errors = exc_info.value.errors()
        assert any(error["loc"] == ("visual_types",) for error in errors)

    def test_size_accepts_any_string(self):
        """Test that size accepts any string (validation happens at API level)."""
        data = {
            "size": "custom_size",
        }
        
        request = GenerateVisualsRequest(**data)
        assert request.size == "custom_size"

    def test_quality_accepts_any_string(self):
        """Test that quality accepts any string (validation happens at API level)."""
        data = {
            "quality": "custom_quality",
        }
        
        request = GenerateVisualsRequest(**data)
        assert request.quality == "custom_quality"

    def test_priority_accepts_any_string(self):
        """Test that priority accepts any string (validation happens at API level)."""
        data = {
            "priority": "custom_priority",
        }
        
        request = GenerateVisualsRequest(**data)
        assert request.priority == "custom_priority"

    def test_visual_types_validation_all_valid_types(self):
        """Test that all valid visual types are accepted."""
        valid_types = ["floor_plan", "rendering", "3d_model"]
        
        for visual_type in valid_types:
            data = {
                "visual_types": [visual_type],
            }
            request = GenerateVisualsRequest(**data)
            assert request.visual_types == [visual_type]

    def test_size_validation_all_valid_sizes(self):
        """Test that all valid sizes are accepted."""
        valid_sizes = ["1024x1024", "1792x1024", "1024x1792"]
        
        for size in valid_sizes:
            data = {
                "size": size,
            }
            request = GenerateVisualsRequest(**data)
            assert request.size == size

    def test_quality_validation_all_valid_qualities(self):
        """Test that all valid qualities are accepted."""
        valid_qualities = ["standard", "hd"]
        
        for quality in valid_qualities:
            data = {
                "quality": quality,
            }
            request = GenerateVisualsRequest(**data)
            assert request.quality == quality

    def test_priority_validation_all_valid_priorities(self):
        """Test that all valid priorities are accepted."""
        valid_priorities = ["low", "normal", "high"]
        
        for priority in valid_priorities:
            data = {
                "priority": priority,
            }
            request = GenerateVisualsRequest(**data)
            assert request.priority == priority
