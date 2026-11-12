"""
Unit tests for HVACCalculator class.
Tests HVAC system calculations for heating loads, cooling loads,
and equipment sizing per ASHRAE standards.

**Validates: Requirements 2.1, 2.6, 7.1-7.6**
"""

import pytest
from src.calculations.hvac_calculator import (BuildingData, ClimateData,
                                              EquipmentSize, HVACCalculator,
                                              HVACDesignResult)


class TestBuildingData:
    """Tests for BuildingData dataclass."""

    def test_building_data_creation(self):
        """Test creating building data."""
        building = BuildingData(
            floor_area=5000.0,  # sq ft
            wall_area=2000.0,  # sq ft
            roof_area=5000.0,  # sq ft
            window_area=500.0,  # sq ft
            volume=40000.0,  # cu ft
            occupancy=50,  # people
            insulation_r_value=19.0,  # R-value
        )

        assert building.floor_area == 5000.0
        assert building.wall_area == 2000.0
        assert building.occupancy == 50


class TestClimateData:
    """Tests for ClimateData dataclass."""

    def test_climate_data_creation(self):
        """Test creating climate data."""
        climate = ClimateData(
            outdoor_temp_winter=10.0,  # °F
            outdoor_temp_summer=95.0,  # °F
            indoor_temp_winter=70.0,  # °F
            indoor_temp_summer=75.0,  # °F
            humidity_summer=60.0,  # %
        )

        assert climate.outdoor_temp_winter == 10.0
        assert climate.outdoor_temp_summer == 95.0
        assert climate.indoor_temp_winter == 70.0


class TestHVACCalculatorHeatingLoads:
    """Tests for heating load calculations per ASHRAE."""

    def test_calculate_heating_load_basic(self):
        """Test basic heating load calculation."""
        calculator = HVACCalculator()

        building = BuildingData(
            floor_area=5000.0,
            wall_area=2000.0,
            roof_area=5000.0,
            window_area=500.0,
            volume=40000.0,
            occupancy=50,
            insulation_r_value=19.0,
        )

        climate = ClimateData(
            outdoor_temp_winter=10.0,
            outdoor_temp_summer=95.0,
            indoor_temp_winter=70.0,
            indoor_temp_summer=75.0,
            humidity_summer=60.0,
        )

        heating_load = calculator.calculate_heating_load(building, climate)

        # Heating load should be positive
        assert heating_load > 0
        # Should be reasonable for 5000 sq ft building (typically 30-50 BTU/sq ft)
        assert 100000 < heating_load < 300000
