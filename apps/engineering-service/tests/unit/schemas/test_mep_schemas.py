"""Unit tests for MEP engineering schemas."""

import pytest
from pydantic import ValidationError
from src.api.v1.schemas.mep import (ElectricalDesignRequest,
                                    ElectricalDesignResponse,
                                    FireProtectionDesignRequest,
                                    FireProtectionDesignResponse,
                                    HVACDesignRequest, HVACDesignResponse,
                                    PlumbingDesignRequest,
                                    PlumbingDesignResponse, SystemType,
                                    UnitSystem)


class TestSystemType:
    """Tests for SystemType enum."""

    def test_system_type_values(self):
        """Test SystemType enum has correct values."""
        assert SystemType.HVAC == "hvac"
        assert SystemType.ELECTRICAL == "electrical"
        assert SystemType.PLUMBING == "plumbing"
        assert SystemType.FIRE_PROTECTION == "fire_protection"


class TestHVACDesignRequest:
    """Tests for HVACDesignRequest schema."""

    def test_valid_hvac_design_request(self):
        """Test creating valid HVAC design request."""
        data = {
            "project_id": "123e4567-e89b-12d3-a456-426614174000",
            "building_data": {
                "area": 5000.0,
                "volume": 50000.0,
                "occupancy_type": "office",
                "num_floors": 3,
            },
            "climate_data": {
                "heating_design_temp": -10.0,
                "cooling_design_temp": 95.0,
                "humidity": 60.0,
            },
            "unit_system": "imperial",
        }
        request = HVACDesignRequest(**data)
        assert str(request.project_id) == "123e4567-e89b-12d3-a456-426614174000"
        assert request.building_data["area"] == 5000.0
        assert request.climate_data["heating_design_temp"] == -10.0

    def test_hvac_design_request_defaults_to_imperial(self):
        """Test unit_system defaults to imperial."""
        data = {
            "project_id": "123e4567-e89b-12d3-a456-426614174000",
            "building_data": {"area": 5000.0},
            "climate_data": {"heating_design_temp": -10.0},
        }
        request = HVACDesignRequest(**data)
        assert request.unit_system == UnitSystem.IMPERIAL

    def test_hvac_design_request_missing_required_fields(self):
        """Test validation fails when required fields are missing."""
        data = {"project_id": "123e4567-e89b-12d3-a456-426614174000"}
        with pytest.raises(ValidationError):
            HVACDesignRequest(**data)


class TestHVACDesignResponse:
    """Tests for HVACDesignResponse schema."""

    def test_valid_hvac_design_response(self):
        """Test creating valid HVAC design response."""
        data = {
            "design_id": "123e4567-e89b-12d3-a456-426614174000",
            "project_id": "223e4567-e89b-12d3-a456-426614174000",
            "heating_load": 250000.0,
            "cooling_load": 180000.0,
            "equipment_size": {
                "heating_unit": "Boiler 250 MBH",
                "cooling_unit": "Chiller 15 Tons",
            },
            "ductwork": {
                "main_duct_size": "24x18",
                "total_cfm": 8000.0,
            },
            "unit_system": "imperial",
        }
        response = HVACDesignResponse(**data)
        assert response.heating_load == 250000.0
        assert response.cooling_load == 180000.0


class TestElectricalDesignRequest:
    """Tests for ElectricalDesignRequest schema."""

    def test_valid_electrical_design_request(self):
        """Test creating valid electrical design request."""
        data = {
            "project_id": "123e4567-e89b-12d3-a456-426614174000",
            "loads": {
                "lighting": 15000.0,
                "receptacles": 10000.0,
                "hvac": 25000.0,
                "other": 5000.0,
            },
            "voltage": 480.0,
            "unit_system": "imperial",
        }
        request = ElectricalDesignRequest(**data)
        assert request.voltage == 480.0
        assert request.loads["lighting"] == 15000.0

    def test_electrical_design_request_positive_voltage(self):
        """Test voltage must be positive."""
        data = {
            "project_id": "123e4567-e89b-12d3-a456-426614174000",
            "loads": {"lighting": 15000.0},
            "voltage": -120.0,
        }
        with pytest.raises(ValidationError):
            ElectricalDesignRequest(**data)


class TestElectricalDesignResponse:
    """Tests for ElectricalDesignResponse schema."""

    def test_valid_electrical_design_response(self):
        """Test creating valid electrical design response."""
        data = {
            "design_id": "123e4567-e89b-12d3-a456-426614174000",
            "project_id": "223e4567-e89b-12d3-a456-426614174000",
            "total_load": 55000.0,
            "panel_size": {
                "main_panel": "400A",
                "sub_panels": ["100A", "100A", "60A"],
            },
            "circuit_sizing": {
                "lighting_circuits": "#12 AWG",
                "receptacle_circuits": "#12 AWG",
                "hvac_circuits": "#6 AWG",
            },
            "unit_system": "imperial",
        }
        response = ElectricalDesignResponse(**data)
        assert response.total_load == 55000.0


class TestPlumbingDesignRequest:
    """Tests for PlumbingDesignRequest schema."""

    def test_valid_plumbing_design_request(self):
        """Test creating valid plumbing design request."""
        data = {
            "project_id": "123e4567-e89b-12d3-a456-426614174000",
            "fixtures": [
                {"type": "water_closet", "count": 10},
                {"type": "lavatory", "count": 8},
                {"type": "sink", "count": 4},
            ],
            "supply_pressure": 60.0,
            "unit_system": "imperial",
        }
        request = PlumbingDesignRequest(**data)
        assert request.supply_pressure == 60.0
        assert len(request.fixtures) == 3

    def test_plumbing_design_request_positive_pressure(self):
        """Test supply pressure must be positive."""
        data = {
            "project_id": "123e4567-e89b-12d3-a456-426614174000",
            "fixtures": [{"type": "water_closet", "count": 10}],
            "supply_pressure": -10.0,
        }
        with pytest.raises(ValidationError):
            PlumbingDesignRequest(**data)


class TestPlumbingDesignResponse:
    """Tests for PlumbingDesignResponse schema."""

    def test_valid_plumbing_design_response(self):
        """Test creating valid plumbing design response."""
        data = {
            "design_id": "123e4567-e89b-12d3-a456-426614174000",
            "project_id": "223e4567-e89b-12d3-a456-426614174000",
            "fixture_units": 45.0,
            "pipe_sizing": {
                "main": "3 inch",
                "branches": ["2 inch", "1.5 inch", "1 inch"],
            },
            "water_demand": 120.0,
            "unit_system": "imperial",
        }
        response = PlumbingDesignResponse(**data)
        assert response.fixture_units == 45.0
        assert response.water_demand == 120.0


class TestFireProtectionDesignRequest:
    """Tests for FireProtectionDesignRequest schema."""

    def test_valid_fire_protection_request(self):
        """Test creating valid fire protection request."""
        data = {
            "project_id": "123e4567-e89b-12d3-a456-426614174000",
            "building_data": {
                "area": 10000.0,
                "height": 40.0,
                "occupancy_type": "business",
                "construction_type": "Type II",
            },
            "occupancy_type": "business",
            "unit_system": "imperial",
        }
        request = FireProtectionDesignRequest(**data)
        assert request.occupancy_type == "business"
        assert request.building_data["area"] == 10000.0


class TestFireProtectionDesignResponse:
    """Tests for FireProtectionDesignResponse schema."""

    def test_valid_fire_protection_response(self):
        """Test creating valid fire protection response."""
        data = {
            "design_id": "123e4567-e89b-12d3-a456-426614174000",
            "project_id": "223e4567-e89b-12d3-a456-426614174000",
            "system_type": "wet_pipe_sprinkler",
            "sprinkler_density": 0.15,
            "water_demand": 1500.0,
            "pipe_sizing": {
                "main": "6 inch",
                "branches": ["4 inch", "2.5 inch", "1.5 inch"],
            },
            "unit_system": "imperial",
        }
        response = FireProtectionDesignResponse(**data)
        assert response.system_type == "wet_pipe_sprinkler"
        assert response.sprinkler_density == 0.15
        assert response.water_demand == 1500.0
