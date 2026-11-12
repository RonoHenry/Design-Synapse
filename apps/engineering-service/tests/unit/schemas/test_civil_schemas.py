"""Unit tests for civil engineering schemas."""

import pytest
from pydantic import ValidationError
from src.api.v1.schemas.civil import (DesignType, GradingDesignRequest,
                                      GradingDesignResponse,
                                      StormwaterDesignRequest,
                                      StormwaterDesignResponse, UnitSystem,
                                      UtilityDesignRequest,
                                      UtilityDesignResponse)


class TestDesignType:
    """Tests for DesignType enum."""

    def test_design_type_values(self):
        """Test DesignType enum has correct values."""
        assert DesignType.GRADING == "grading"
        assert DesignType.STORMWATER == "stormwater"
        assert DesignType.UTILITIES == "utilities"
        assert DesignType.PAVING == "paving"


class TestGradingDesignRequest:
    """Tests for GradingDesignRequest schema."""

    def test_valid_grading_design_request(self):
        """Test creating valid grading design request."""
        data = {
            "project_id": "123e4567-e89b-12d3-a456-426614174000",
            "site_data": {
                "area": 50000.0,
                "existing_elevations": {"point1": 100.0, "point2": 105.0},
                "soil_type": "clay",
            },
            "target_elevations": {
                "point1": 102.0,
                "point2": 107.0,
            },
            "unit_system": "imperial",
        }
        request = GradingDesignRequest(**data)
        assert str(request.project_id) == "123e4567-e89b-12d3-a456-426614174000"
        assert request.site_data["area"] == 50000.0
        assert request.unit_system == UnitSystem.IMPERIAL

    def test_grading_design_request_defaults_to_imperial(self):
        """Test unit_system defaults to imperial."""
        data = {
            "project_id": "123e4567-e89b-12d3-a456-426614174000",
            "site_data": {"area": 50000.0},
            "target_elevations": {"point1": 102.0},
        }
        request = GradingDesignRequest(**data)
        assert request.unit_system == UnitSystem.IMPERIAL

    def test_grading_design_request_missing_required_fields(self):
        """Test validation fails when required fields are missing."""
        data = {"project_id": "123e4567-e89b-12d3-a456-426614174000"}
        with pytest.raises(ValidationError):
            GradingDesignRequest(**data)


class TestGradingDesignResponse:
    """Tests for GradingDesignResponse schema."""

    def test_valid_grading_design_response(self):
        """Test creating valid grading design response."""
        data = {
            "design_id": "123e4567-e89b-12d3-a456-426614174000",
            "project_id": "223e4567-e89b-12d3-a456-426614174000",
            "cut_volume": 5000.0,
            "fill_volume": 4500.0,
            "net_volume": 500.0,
            "grading_plan": {
                "slopes": {"north": 2.0, "south": 2.5},
                "drainage": "positive",
            },
            "unit_system": "imperial",
        }
        response = GradingDesignResponse(**data)
        assert response.cut_volume == 5000.0
        assert response.fill_volume == 4500.0
        assert response.net_volume == 500.0


class TestStormwaterDesignRequest:
    """Tests for StormwaterDesignRequest schema."""

    def test_valid_stormwater_design_request(self):
        """Test creating valid stormwater design request."""
        data = {
            "project_id": "123e4567-e89b-12d3-a456-426614174000",
            "site_data": {
                "drainage_area": 10000.0,
                "imperviousness": 0.65,
                "slope": 2.0,
            },
            "rainfall_data": {
                "intensity": 3.5,
                "duration": 60,
                "return_period": 25,
            },
            "unit_system": "imperial",
        }
        request = StormwaterDesignRequest(**data)
        assert request.site_data["drainage_area"] == 10000.0
        assert request.rainfall_data["return_period"] == 25

    def test_stormwater_design_request_missing_required_fields(self):
        """Test validation fails when required fields are missing."""
        data = {
            "project_id": "123e4567-e89b-12d3-a456-426614174000",
            "site_data": {"drainage_area": 10000.0},
        }
        with pytest.raises(ValidationError):
            StormwaterDesignRequest(**data)


class TestStormwaterDesignResponse:
    """Tests for StormwaterDesignResponse schema."""

    def test_valid_stormwater_design_response(self):
        """Test creating valid stormwater design response."""
        data = {
            "design_id": "123e4567-e89b-12d3-a456-426614174000",
            "project_id": "223e4567-e89b-12d3-a456-426614174000",
            "runoff_rate": 25.5,
            "detention_volume": 15000.0,
            "pipe_sizing": {
                "main_line": {"diameter": 24, "material": "RCP"},
                "laterals": [{"diameter": 12, "material": "PVC"}],
            },
            "unit_system": "imperial",
        }
        response = StormwaterDesignResponse(**data)
        assert response.runoff_rate == 25.5
        assert response.detention_volume == 15000.0


class TestUtilityDesignRequest:
    """Tests for UtilityDesignRequest schema."""

    def test_valid_utility_design_request(self):
        """Test creating valid utility design request."""
        data = {
            "project_id": "123e4567-e89b-12d3-a456-426614174000",
            "site_data": {
                "connection_points": {
                    "water": {"x": 100, "y": 200},
                    "sewer": {"x": 150, "y": 250},
                },
                "distances": {"water": 500, "sewer": 600},
            },
            "utility_loads": {
                "water_demand": 50.0,
                "sewer_flow": 40.0,
                "gas_demand": 100.0,
            },
            "unit_system": "imperial",
        }
        request = UtilityDesignRequest(**data)
        assert request.utility_loads["water_demand"] == 50.0

    def test_utility_design_request_missing_required_fields(self):
        """Test validation fails when required fields are missing."""
        data = {"project_id": "123e4567-e89b-12d3-a456-426614174000"}
        with pytest.raises(ValidationError):
            UtilityDesignRequest(**data)


class TestUtilityDesignResponse:
    """Tests for UtilityDesignResponse schema."""

    def test_valid_utility_design_response(self):
        """Test creating valid utility design response."""
        data = {
            "design_id": "123e4567-e89b-12d3-a456-426614174000",
            "project_id": "223e4567-e89b-12d3-a456-426614174000",
            "water_service": {
                "size": 4,
                "material": "copper",
                "pressure": 60,
            },
            "sewer_service": {
                "size": 6,
                "material": "PVC",
                "slope": 2.0,
            },
            "gas_service": {
                "size": 2,
                "material": "steel",
                "pressure": 5,
            },
            "unit_system": "imperial",
        }
        response = UtilityDesignResponse(**data)
        assert response.water_service["size"] == 4
        assert response.sewer_service["size"] == 6
        assert response.gas_service is not None

    def test_utility_design_response_optional_gas_service(self):
        """Test response with optional gas service as None."""
        data = {
            "design_id": "123e4567-e89b-12d3-a456-426614174000",
            "project_id": "223e4567-e89b-12d3-a456-426614174000",
            "water_service": {"size": 4},
            "sewer_service": {"size": 6},
            "gas_service": None,
            "unit_system": "imperial",
        }
        response = UtilityDesignResponse(**data)
        assert response.gas_service is None
