"""Unit tests for LoadCalculator following TDD methodology."""

from typing import Dict, List

import pytest
from src.calculations.load_calculator import (BuildingData, Component,
                                              LoadCalculator, OccupancyType,
                                              SeismicData, SeismicLoadResult,
                                              WindLoadResult)


class TestLoadCalculatorDeadLoads:
    """Test dead load calculations."""

    def test_calculate_dead_load_single_component(self):
        """Test dead load calculation with a single component."""
        calculator = LoadCalculator()
        components = [
            Component(name="Concrete Slab", weight_per_area=150.0, area=100.0)
        ]

        dead_load = calculator.calculate_dead_load(components)

        assert dead_load == 15000.0  # 150 psf * 100 sf

    def test_calculate_dead_load_multiple_components(self):
        """Test dead load calculation with multiple components."""
        calculator = LoadCalculator()
        components = [
            Component(name="Concrete Slab", weight_per_area=150.0, area=100.0),
            Component(name="Roofing", weight_per_area=10.0, area=100.0),
            Component(name="Ceiling", weight_per_area=5.0, area=100.0),
        ]

        dead_load = calculator.calculate_dead_load(components)

        assert dead_load == 16500.0  # (150 + 10 + 5) * 100

    def test_calculate_dead_load_empty_components(self):
        """Test dead load calculation with no components."""
        calculator = LoadCalculator()
        components = []

        dead_load = calculator.calculate_dead_load(components)

        assert dead_load == 0.0

    def test_calculate_dead_load_zero_area(self):
        """Test dead load calculation with zero area."""
        calculator = LoadCalculator()
        components = [Component(name="Concrete Slab", weight_per_area=150.0, area=0.0)]

        dead_load = calculator.calculate_dead_load(components)

        assert dead_load == 0.0

    def test_calculate_dead_load_negative_values_raise_error(self):
        """Test that negative values raise ValueError."""
        calculator = LoadCalculator()
        components = [Component(name="Invalid", weight_per_area=-10.0, area=100.0)]

        with pytest.raises(ValueError, match="weight_per_area must be non-negative"):
            calculator.calculate_dead_load(components)


class TestLoadCalculatorLiveLoads:
    """Test live load calculations per ASCE 7."""

    def test_calculate_live_load_residential(self):
        """Test live load for residential occupancy (40 psf per ASCE 7 Table 4.3-1)."""
        calculator = LoadCalculator()

        live_load = calculator.calculate_live_load(
            occupancy=OccupancyType.RESIDENTIAL, area=100.0
        )

        assert live_load == 4000.0  # 40 psf * 100 sf

    def test_calculate_live_load_office(self):
        """Test live load for office occupancy (50 psf per ASCE 7 Table 4.3-1)."""
        calculator = LoadCalculator()

        live_load = calculator.calculate_live_load(
            occupancy=OccupancyType.OFFICE, area=100.0
        )

        assert live_load == 5000.0  # 50 psf * 100 sf

    def test_calculate_live_load_retail(self):
        """Test live load for retail occupancy (100 psf per ASCE 7 Table 4.3-1)."""
        calculator = LoadCalculator()

        live_load = calculator.calculate_live_load(
            occupancy=OccupancyType.RETAIL, area=100.0
        )

        assert live_load == 10000.0  # 100 psf * 100 sf

    def test_calculate_live_load_assembly(self):
        """Test live load for assembly occupancy (100 psf per ASCE 7 Table 4.3-1)."""
        calculator = LoadCalculator()

        live_load = calculator.calculate_live_load(
            occupancy=OccupancyType.ASSEMBLY, area=100.0
        )

        assert live_load == 10000.0  # 100 psf * 100 sf

    def test_calculate_live_load_zero_area(self):
        """Test live load calculation with zero area."""
        calculator = LoadCalculator()

        live_load = calculator.calculate_live_load(
            occupancy=OccupancyType.RESIDENTIAL, area=0.0
        )

        assert live_load == 0.0

    def test_calculate_live_load_negative_area_raises_error(self):
        """Test that negative area raises ValueError."""
        calculator = LoadCalculator()

        with pytest.raises(ValueError, match="area must be non-negative"):
            calculator.calculate_live_load(
                occupancy=OccupancyType.RESIDENTIAL, area=-100.0
            )


class TestLoadCalculatorWindLoads:
    """Test wind load calculations per ASCE 7 Chapter 27."""

    def test_calculate_wind_load_basic(self):
        """Test basic wind load calculation."""
        calculator = LoadCalculator()
        building = BuildingData(
            height=30.0, width=50.0, length=100.0, exposure_category="C"  # feet
        )

        result = calculator.calculate_wind_load(
            building=building, wind_speed=115.0  # mph (3-second gust)
        )

        assert isinstance(result, WindLoadResult)
        assert result.design_pressure > 0
        assert result.wind_speed == 115.0
        assert result.exposure_category == "C"

    def test_calculate_wind_load_exposure_b(self):
        """Test wind load with Exposure B (urban/suburban)."""
        calculator = LoadCalculator()
        building = BuildingData(
            height=30.0, width=50.0, length=100.0, exposure_category="B"
        )

        result = calculator.calculate_wind_load(building=building, wind_speed=115.0)

        # Exposure B should have lower pressure than C
        assert result.design_pressure > 0
        assert result.exposure_category == "B"

    def test_calculate_wind_load_exposure_d(self):
        """Test wind load with Exposure D (flat, unobstructed)."""
        calculator = LoadCalculator()
        building = BuildingData(
            height=30.0, width=50.0, length=100.0, exposure_category="D"
        )

        result = calculator.calculate_wind_load(building=building, wind_speed=115.0)

        # Exposure D should have higher pressure than C
        assert result.design_pressure > 0
        assert result.exposure_category == "D"

    def test_calculate_wind_load_invalid_exposure_raises_error(self):
        """Test that invalid exposure category raises ValueError."""
        calculator = LoadCalculator()
        building = BuildingData(
            height=30.0, width=50.0, length=100.0, exposure_category="X"  # Invalid
        )

        with pytest.raises(ValueError, match="Invalid exposure category"):
            calculator.calculate_wind_load(building=building, wind_speed=115.0)

    def test_calculate_wind_load_negative_wind_speed_raises_error(self):
        """Test that negative wind speed raises ValueError."""
        calculator = LoadCalculator()
        building = BuildingData(
            height=30.0, width=50.0, length=100.0, exposure_category="C"
        )

        with pytest.raises(ValueError, match="wind_speed must be positive"):
            calculator.calculate_wind_load(building=building, wind_speed=-115.0)


class TestLoadCalculatorSeismicLoads:
    """Test seismic load calculations per ASCE 7 Chapter 12."""

    def test_calculate_seismic_load_basic(self):
        """Test basic seismic load calculation."""
        calculator = LoadCalculator()
        building = BuildingData(
            height=30.0, width=50.0, length=100.0, exposure_category="C"
        )
        seismic_data = SeismicData(
            ss=1.5,  # Spectral acceleration at short periods
            s1=0.6,  # Spectral acceleration at 1-second period
            site_class="D",
            importance_factor=1.0,
            response_modification_factor=8.0,  # R factor
        )

        result = calculator.calculate_seismic_load(
            building=building, seismic_data=seismic_data
        )

        assert isinstance(result, SeismicLoadResult)
        assert result.base_shear > 0
        assert result.seismic_design_category in ["A", "B", "C", "D", "E", "F"]

    def test_calculate_seismic_load_high_seismicity(self):
        """Test seismic load in high seismicity region."""
        calculator = LoadCalculator()
        building = BuildingData(
            height=30.0, width=50.0, length=100.0, exposure_category="C"
        )
        seismic_data = SeismicData(
            ss=2.0,  # High seismicity
            s1=0.8,
            site_class="D",
            importance_factor=1.0,
            response_modification_factor=8.0,
        )

        result = calculator.calculate_seismic_load(
            building=building, seismic_data=seismic_data
        )

        assert result.base_shear > 0
        assert result.seismic_design_category in ["D", "E", "F"]

    def test_calculate_seismic_load_low_seismicity(self):
        """Test seismic load in low seismicity region."""
        calculator = LoadCalculator()
        building = BuildingData(
            height=30.0, width=50.0, length=100.0, exposure_category="C"
        )
        seismic_data = SeismicData(
            ss=0.25,  # Low seismicity
            s1=0.1,
            site_class="D",
            importance_factor=1.0,
            response_modification_factor=8.0,
        )

        result = calculator.calculate_seismic_load(
            building=building, seismic_data=seismic_data
        )

        assert result.base_shear >= 0
        assert result.seismic_design_category in ["A", "B", "C"]

    def test_calculate_seismic_load_invalid_site_class_raises_error(self):
        """Test that invalid site class raises ValueError."""
        calculator = LoadCalculator()
        building = BuildingData(
            height=30.0, width=50.0, length=100.0, exposure_category="C"
        )
        seismic_data = SeismicData(
            ss=1.5,
            s1=0.6,
            site_class="X",  # Invalid
            importance_factor=1.0,
            response_modification_factor=8.0,
        )

        with pytest.raises(ValueError, match="Invalid site class"):
            calculator.calculate_seismic_load(
                building=building, seismic_data=seismic_data
            )

    def test_calculate_seismic_load_negative_values_raise_error(self):
        """Test that negative spectral accelerations raise ValueError."""
        calculator = LoadCalculator()
        building = BuildingData(
            height=30.0, width=50.0, length=100.0, exposure_category="C"
        )
        seismic_data = SeismicData(
            ss=-1.5,  # Invalid
            s1=0.6,
            site_class="D",
            importance_factor=1.0,
            response_modification_factor=8.0,
        )

        with pytest.raises(
            ValueError, match="Spectral accelerations must be non-negative"
        ):
            calculator.calculate_seismic_load(
                building=building, seismic_data=seismic_data
            )
