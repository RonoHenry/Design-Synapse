"""Unit tests for structural engineering schemas."""

import pytest
from pydantic import ValidationError
from src.api.v1.schemas.structural import (BeamDesignRequest,
                                           BeamDesignResponse,
                                           ColumnDesignRequest,
                                           ColumnDesignResponse,
                                           FoundationDesignRequest,
                                           FoundationDesignResponse,
                                           LoadCalculationRequest,
                                           LoadCalculationResponse, LoadType,
                                           UnitSystem)


class TestUnitSystem:
    """Tests for UnitSystem enum."""

    def test_unit_system_values(self):
        """Test UnitSystem enum has correct values."""
        assert UnitSystem.IMPERIAL == "imperial"
        assert UnitSystem.METRIC == "metric"


class TestLoadType:
    """Tests for LoadType enum."""

    def test_load_type_values(self):
        """Test LoadType enum has correct values."""
        assert LoadType.DEAD == "dead"
        assert LoadType.LIVE == "live"
        assert LoadType.WIND == "wind"
        assert LoadType.SEISMIC == "seismic"


class TestLoadCalculationRequest:
    """Tests for LoadCalculationRequest schema."""

    def test_valid_load_calculation_request(self):
        """Test creating valid load calculation request."""
        data = {
            "project_id": "123e4567-e89b-12d3-a456-426614174000",
            "building_data": {
                "height": 30.0,
                "width": 50.0,
                "length": 100.0,
                "occupancy_type": "office",
                "num_floors": 3,
            },
            "load_types": ["dead", "live", "wind"],
            "unit_system": "imperial",
        }
        request = LoadCalculationRequest(**data)
        assert str(request.project_id) == "123e4567-e89b-12d3-a456-426614174000"
        assert request.building_data["height"] == 30.0
        assert len(request.load_types) == 3
        assert request.unit_system == UnitSystem.IMPERIAL

    def test_load_calculation_request_defaults_to_imperial(self):
        """Test unit_system defaults to imperial."""
        data = {
            "project_id": "123e4567-e89b-12d3-a456-426614174000",
            "building_data": {
                "height": 30.0,
                "width": 50.0,
                "length": 100.0,
                "occupancy_type": "office",
                "num_floors": 3,
            },
            "load_types": ["dead", "live"],
        }
        request = LoadCalculationRequest(**data)
        assert request.unit_system == UnitSystem.IMPERIAL

    def test_load_calculation_request_invalid_project_id(self):
        """Test validation fails for invalid project_id."""
        data = {
            "project_id": "invalid-uuid",
            "building_data": {"height": 30.0},
            "load_types": ["dead"],
        }
        with pytest.raises(ValidationError):
            LoadCalculationRequest(**data)

    def test_load_calculation_request_missing_required_fields(self):
        """Test validation fails when required fields are missing."""
        data = {"project_id": "123e4567-e89b-12d3-a456-426614174000"}
        with pytest.raises(ValidationError):
            LoadCalculationRequest(**data)


class TestLoadCalculationResponse:
    """Tests for LoadCalculationResponse schema."""

    def test_valid_load_calculation_response(self):
        """Test creating valid load calculation response."""
        data = {
            "calculation_id": "123e4567-e89b-12d3-a456-426614174000",
            "project_id": "223e4567-e89b-12d3-a456-426614174000",
            "dead_load": 1500.0,
            "live_load": 800.0,
            "wind_load": 500.0,
            "seismic_load": 300.0,
            "total_load": 3100.0,
            "unit_system": "imperial",
        }
        response = LoadCalculationResponse(**data)
        assert response.dead_load == 1500.0
        assert response.total_load == 3100.0
        assert response.unit_system == UnitSystem.IMPERIAL

    def test_load_calculation_response_optional_loads(self):
        """Test response with optional loads as None."""
        data = {
            "calculation_id": "123e4567-e89b-12d3-a456-426614174000",
            "project_id": "223e4567-e89b-12d3-a456-426614174000",
            "dead_load": 1500.0,
            "live_load": 800.0,
            "wind_load": None,
            "seismic_load": None,
            "total_load": 2300.0,
            "unit_system": "imperial",
        }
        response = LoadCalculationResponse(**data)
        assert response.wind_load is None
        assert response.seismic_load is None


class TestBeamDesignRequest:
    """Tests for BeamDesignRequest schema."""

    def test_valid_beam_design_request(self):
        """Test creating valid beam design request."""
        data = {
            "project_id": "123e4567-e89b-12d3-a456-426614174000",
            "loads": {
                "dead_load": 1000.0,
                "live_load": 500.0,
                "point_loads": [],
            },
            "span": 20.0,
            "material": {
                "type": "steel",
                "grade": "A992",
                "fy": 50000.0,
            },
            "unit_system": "imperial",
        }
        request = BeamDesignRequest(**data)
        assert request.span == 20.0
        assert request.material["type"] == "steel"

    def test_beam_design_request_positive_span(self):
        """Test span must be positive."""
        data = {
            "project_id": "123e4567-e89b-12d3-a456-426614174000",
            "loads": {"dead_load": 1000.0},
            "span": -10.0,
            "material": {"type": "steel"},
        }
        with pytest.raises(ValidationError):
            BeamDesignRequest(**data)


class TestBeamDesignResponse:
    """Tests for BeamDesignResponse schema."""

    def test_valid_beam_design_response(self):
        """Test creating valid beam design response."""
        data = {
            "design_id": "123e4567-e89b-12d3-a456-426614174000",
            "project_id": "223e4567-e89b-12d3-a456-426614174000",
            "required_section": "W18x50",
            "deflection": 0.75,
            "stress_ratio": 0.85,
            "is_adequate": True,
            "unit_system": "imperial",
        }
        response = BeamDesignResponse(**data)
        assert response.required_section == "W18x50"
        assert response.is_adequate is True


class TestColumnDesignRequest:
    """Tests for ColumnDesignRequest schema."""

    def test_valid_column_design_request(self):
        """Test creating valid column design request."""
        data = {
            "project_id": "123e4567-e89b-12d3-a456-426614174000",
            "axial_load": 50000.0,
            "moment": 10000.0,
            "length": 12.0,
            "material": {
                "type": "steel",
                "grade": "A992",
                "fy": 50000.0,
            },
            "unit_system": "imperial",
        }
        request = ColumnDesignRequest(**data)
        assert request.axial_load == 50000.0
        assert request.length == 12.0

    def test_column_design_request_positive_values(self):
        """Test axial_load and length must be positive."""
        data = {
            "project_id": "123e4567-e89b-12d3-a456-426614174000",
            "axial_load": -1000.0,
            "moment": 10000.0,
            "length": 12.0,
            "material": {"type": "steel"},
        }
        with pytest.raises(ValidationError):
            ColumnDesignRequest(**data)


class TestColumnDesignResponse:
    """Tests for ColumnDesignResponse schema."""

    def test_valid_column_design_response(self):
        """Test creating valid column design response."""
        data = {
            "design_id": "123e4567-e89b-12d3-a456-426614174000",
            "project_id": "223e4567-e89b-12d3-a456-426614174000",
            "required_section": "W14x90",
            "axial_capacity": 60000.0,
            "buckling_ratio": 0.75,
            "stress_ratio": 0.82,
            "is_adequate": True,
            "unit_system": "imperial",
        }
        response = ColumnDesignResponse(**data)
        assert response.required_section == "W14x90"
        assert response.is_adequate is True


class TestFoundationDesignRequest:
    """Tests for FoundationDesignRequest schema."""

    def test_valid_foundation_design_request(self):
        """Test creating valid foundation design request."""
        data = {
            "project_id": "123e4567-e89b-12d3-a456-426614174000",
            "loads": {
                "dead_load": 50000.0,
                "live_load": 20000.0,
                "moment": 5000.0,
            },
            "soil_properties": {
                "bearing_capacity": 3000.0,
                "soil_type": "clay",
                "depth": 4.0,
            },
            "unit_system": "imperial",
        }
        request = FoundationDesignRequest(**data)
        assert request.soil_properties["bearing_capacity"] == 3000.0

    def test_foundation_design_request_positive_bearing_capacity(self):
        """Test bearing capacity must be positive."""
        data = {
            "project_id": "123e4567-e89b-12d3-a456-426614174000",
            "loads": {"dead_load": 50000.0},
            "soil_properties": {
                "bearing_capacity": -1000.0,
                "soil_type": "clay",
            },
        }
        with pytest.raises(ValidationError):
            FoundationDesignRequest(**data)


class TestFoundationDesignResponse:
    """Tests for FoundationDesignResponse schema."""

    def test_valid_foundation_design_response(self):
        """Test creating valid foundation design response."""
        data = {
            "design_id": "123e4567-e89b-12d3-a456-426614174000",
            "project_id": "223e4567-e89b-12d3-a456-426614174000",
            "foundation_type": "spread_footing",
            "dimensions": {
                "length": 10.0,
                "width": 10.0,
                "depth": 4.0,
            },
            "bearing_pressure": 2500.0,
            "settlement": 0.5,
            "reinforcement": {
                "bars": "#5",
                "spacing": 12.0,
            },
            "is_adequate": True,
            "unit_system": "imperial",
        }
        response = FoundationDesignResponse(**data)
        assert response.foundation_type == "spread_footing"
        assert response.is_adequate is True
