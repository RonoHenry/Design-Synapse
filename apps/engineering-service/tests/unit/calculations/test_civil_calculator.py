"""
Unit tests for CivilCalculator class.
Tests civil engineering calculations for grading, stormwater,
and utility systems.

**Validates: Requirements 3.1, 3.2, 3.3, 3.4**
"""

import pytest
from src.calculations.civil_calculator import (CivilCalculator,
                                               GradingDesignResult,
                                               GradingPoint, RainfallData,
                                               SiteData,
                                               StormwaterDesignResult,
                                               UtilityDesignResult,
                                               UtilityLoads)


class TestSiteData:
    """Tests for SiteData dataclass."""

    def test_site_data_creation(self):
        """Test creating site data."""
        site = SiteData(
            area=2.5,  # acres
            existing_elevations={"0_0": 100.0, "100_0": 102.0, "0_100": 101.0},
            soil_type="clay",
            permeability=0.2,  # inches/hour
            slope_percent=2.0,
        )

        assert site.area == 2.5
        assert site.soil_type == "clay"
        assert len(site.existing_elevations) == 3


class TestGradingPoint:
    """Tests for GradingPoint dataclass."""

    def test_grading_point_creation(self):
        """Test creating grading point."""
        point = GradingPoint(
            x=0.0,
            y=0.0,
            existing_elevation=100.0,
            proposed_elevation=98.0,
        )

        assert point.x == 0.0
        assert point.existing_elevation == 100.0
        assert point.proposed_elevation == 98.0

    def test_cut_fill_calculation_cut(self):
        """Test cut/fill calculation for cut scenario."""
        point = GradingPoint(
            x=0.0,
            y=0.0,
            existing_elevation=100.0,
            proposed_elevation=98.0,
        )

        # Cut = existing - proposed (positive means removing earth)
        assert point.cut_fill == 2.0

    def test_cut_fill_calculation_fill(self):
        """Test cut/fill calculation for fill scenario."""
        point = GradingPoint(
            x=0.0,
            y=0.0,
            existing_elevation=100.0,
            proposed_elevation=102.0,
        )

        # Fill = existing - proposed (negative means adding earth)
        assert point.cut_fill == -2.0

    def test_cut_fill_calculation_no_change(self):
        """Test cut/fill calculation when no grading needed."""
        point = GradingPoint(
            x=0.0,
            y=0.0,
            existing_elevation=100.0,
            proposed_elevation=100.0,
        )

        assert point.cut_fill == 0.0


class TestCivilCalculatorGrading:
    """Tests for grading design calculations."""

    def test_design_grading_basic(self):
        """Test basic grading design calculation."""
        calculator = CivilCalculator()

        site = SiteData(
            area=1.0,
            existing_elevations={
                "0_0": 100.0,
                "100_0": 100.0,
                "0_100": 100.0,
                "100_100": 100.0,
            },
            soil_type="clay",
            permeability=0.2,
            slope_percent=0.0,
        )

        # Propose lowering one corner by 2 feet
        target_elevations = {
            "0_0": 100.0,
            "100_0": 100.0,
            "0_100": 100.0,
            "100_100": 98.0,
        }

        result = calculator.design_grading(site, target_elevations, grid_spacing=100.0)

        # Should have cut volume (removing earth)
        assert result.cut_volume > 0
        # Should have some fill or no fill
        assert result.fill_volume >= 0
        # Net volume should be positive (net cut)
        assert result.net_volume > 0
        # Should have 4 grading points
        assert len(result.grading_points) == 4

    def test_design_grading_cut_only(self):
        """Test grading design with only cut (excavation)."""
        calculator = CivilCalculator()

        site = SiteData(
            area=1.0,
            existing_elevations={
                "0_0": 105.0,
                "50_0": 105.0,
            },
            soil_type="sand",
            permeability=2.0,
            slope_percent=0.0,
        )

        # Lower all elevations by 2 feet
        target_elevations = {
            "0_0": 103.0,
            "50_0": 103.0,
        }

        result = calculator.design_grading(site, target_elevations, grid_spacing=50.0)

        # Should have cut volume
        assert result.cut_volume > 0
        # Should have no fill
        assert result.fill_volume == 0
        # Net volume equals cut volume
        assert result.net_volume == result.cut_volume
        # Max cut depth should be 2 feet
        assert result.max_cut_depth == 2.0

    def test_design_grading_fill_only(self):
        """Test grading design with only fill."""
        calculator = CivilCalculator()

        site = SiteData(
            area=1.0,
            existing_elevations={
                "0_0": 100.0,
                "50_0": 100.0,
            },
            soil_type="clay",
            permeability=0.2,
            slope_percent=0.0,
        )

        # Raise all elevations by 3 feet
        target_elevations = {
            "0_0": 103.0,
            "50_0": 103.0,
        }

        result = calculator.design_grading(site, target_elevations, grid_spacing=50.0)

        # Should have no cut
        assert result.cut_volume == 0
        # Should have fill volume
        assert result.fill_volume > 0
        # Net volume should be negative (net fill)
        assert result.net_volume < 0
        # Max fill depth should be 3 feet
        assert result.max_fill_depth == 3.0

    def test_design_grading_balanced(self):
        """Test grading design with balanced cut and fill."""
        calculator = CivilCalculator()

        site = SiteData(
            area=1.0,
            existing_elevations={
                "0_0": 100.0,
                "100_0": 100.0,
            },
            soil_type="silt",
            permeability=0.5,
            slope_percent=0.0,
        )

        # Cut one point, fill another
        target_elevations = {
            "0_0": 98.0,  # 2 ft cut
            "100_0": 102.0,  # 2 ft fill
        }

        result = calculator.design_grading(site, target_elevations, grid_spacing=100.0)

        # Should have both cut and fill
        assert result.cut_volume > 0
        assert result.fill_volume > 0
        # Volumes should be approximately equal
        assert abs(result.cut_volume - result.fill_volume) < 1.0

    def test_design_grading_slope_calculation(self):
        """Test average slope calculation in grading design."""
        calculator = CivilCalculator()

        site = SiteData(
            area=1.0,
            existing_elevations={
                "0_0": 100.0,
                "100_0": 100.0,
            },
            soil_type="clay",
            permeability=0.2,
            slope_percent=0.0,
        )

        # Create 2% slope (2 ft rise over 100 ft)
        target_elevations = {
            "0_0": 100.0,
            "100_0": 102.0,
        }

        result = calculator.design_grading(site, target_elevations, grid_spacing=100.0)

        # Average slope should be approximately 2%
        assert 1.5 < result.average_slope < 2.5


class TestCivilCalculatorStormwater:
    """Tests for stormwater management calculations."""

    def test_calculate_stormwater_runoff_basic(self):
        """Test basic stormwater runoff calculation using Rational Method."""
        calculator = CivilCalculator()

        site = SiteData(
            area=5.0,  # acres
            existing_elevations={},
            soil_type="clay",
            permeability=0.2,
            slope_percent=2.0,
        )

        rainfall = RainfallData(
            intensity=3.0,  # inches/hour
            duration=1.0,  # hours
            return_period=10,  # years
            runoff_coefficient=0.6,  # typical for residential
        )

        runoff_rate = calculator.calculate_stormwater_runoff(site, rainfall)

        # Q = C × I × A = 0.6 × 3.0 × 5.0 = 9.0 CFS
        assert runoff_rate == pytest.approx(9.0, rel=0.01)

    def test_calculate_stormwater_runoff_impervious(self):
        """Test runoff calculation for highly impervious surface."""
        calculator = CivilCalculator()

        site = SiteData(
            area=2.0,
            existing_elevations={},
            soil_type="rock",
            permeability=0.0,
            slope_percent=1.0,
        )

        rainfall = RainfallData(
            intensity=4.0,
            duration=0.5,
            return_period=25,
            runoff_coefficient=0.9,  # parking lot
        )

        runoff_rate = calculator.calculate_stormwater_runoff(site, rainfall)

        # Q = 0.9 × 4.0 × 2.0 = 7.2 CFS
        assert runoff_rate == pytest.approx(7.2, rel=0.01)

    def test_calculate_stormwater_runoff_pervious(self):
        """Test runoff calculation for pervious surface."""
        calculator = CivilCalculator()

        site = SiteData(
            area=10.0,
            existing_elevations={},
            soil_type="sand",
            permeability=5.0,
            slope_percent=0.5,
        )

        rainfall = RainfallData(
            intensity=2.0,
            duration=2.0,
            return_period=10,
            runoff_coefficient=0.2,  # lawn/meadow
        )

        runoff_rate = calculator.calculate_stormwater_runoff(site, rainfall)

        # Q = 0.2 × 2.0 × 10.0 = 4.0 CFS
        assert runoff_rate == pytest.approx(4.0, rel=0.01)

    def test_size_detention_pond_basic(self):
        """Test basic detention pond sizing."""
        calculator = CivilCalculator()

        # 10,000 cubic feet of runoff
        runoff_volume = 10000.0
        # Release at 2 CFS
        release_rate = 2.0
        # Over 1 hour storm
        duration = 1.0

        detention_volume, depth = calculator.size_detention_pond(
            runoff_volume, release_rate, duration
        )

        # Should have positive detention volume
        assert detention_volume > 0
        # Should include freeboard (20% extra)
        assert detention_volume > (runoff_volume - release_rate * 3600)
        # Depth should be reasonable (3-6 feet typical)
        assert 3.0 <= depth <= 6.0

    def test_size_detention_pond_large_volume(self):
        """Test detention pond sizing for large volume."""
        calculator = CivilCalculator()

        # Large runoff volume
        runoff_volume = 100000.0
        release_rate = 5.0
        duration = 2.0

        detention_volume, depth = calculator.size_detention_pond(
            runoff_volume, release_rate, duration
        )

        # Should have large detention volume
        assert detention_volume > 50000
        # Depth should be deeper for large volume
        assert depth >= 6.0

    def test_size_detention_pond_small_volume(self):
        """Test detention pond sizing for small volume."""
        calculator = CivilCalculator()

        # Small runoff volume
        runoff_volume = 3000.0
        release_rate = 1.0
        duration = 0.5

        detention_volume, depth = calculator.size_detention_pond(
            runoff_volume, release_rate, duration
        )

        # Should have small detention volume
        assert detention_volume < 5000
        # Depth should be shallower for small volume
        assert depth <= 4.0

    def test_calculate_pipe_size_basic(self):
        """Test pipe sizing using Manning's equation."""
        calculator = CivilCalculator()

        # 5 CFS flow
        flow_rate = 5.0
        # 1% slope
        slope = 1.0
        # Smooth pipe (n=0.013)
        roughness = 0.013

        diameter = calculator.calculate_pipe_size(flow_rate, slope, roughness)

        # Should return reasonable pipe size
        assert diameter >= 6.0  # Minimum 6 inches
        assert diameter <= 60.0  # Maximum standard size
        # Should be a standard size
        standard_sizes = [6, 8, 10, 12, 15, 18, 21, 24, 27, 30, 36, 42, 48, 54, 60]
        assert diameter in standard_sizes

    def test_calculate_pipe_size_large_flow(self):
        """Test pipe sizing for large flow rate."""
        calculator = CivilCalculator()

        # Large flow
        flow_rate = 50.0
        slope = 0.5
        roughness = 0.013

        diameter = calculator.calculate_pipe_size(flow_rate, slope, roughness)

        # Should return large pipe size
        assert diameter >= 30.0

    def test_calculate_pipe_size_steep_slope(self):
        """Test pipe sizing with steep slope."""
        calculator = CivilCalculator()

        # Moderate flow with steep slope
        flow_rate = 10.0
        slope = 5.0  # 5% slope
        roughness = 0.013

        diameter = calculator.calculate_pipe_size(flow_rate, slope, roughness)

        # Steeper slope allows smaller pipe
        assert diameter <= 24.0


class TestCivilCalculatorUtilities:
    """Tests for utility system design calculations."""

    def test_design_water_service_small(self):
        """Test water service sizing for small demand."""
        calculator = CivilCalculator()

        # Small residential demand
        demand = 10.0  # GPM

        service_size, pressure_required = calculator.design_water_service(demand)

        # Should be minimum size
        assert service_size == 0.75
        # Should have reasonable pressure requirement
        assert 40.0 <= pressure_required <= 60.0

    def test_design_water_service_medium(self):
        """Test water service sizing for medium demand."""
        calculator = CivilCalculator()

        # Medium residential/small commercial
        demand = 40.0  # GPM

        service_size, pressure_required = calculator.design_water_service(demand)

        # Should be 1.5 inch service
        assert service_size == 1.5
        assert pressure_required > 40.0

    def test_design_water_service_large(self):
        """Test water service sizing for large demand."""
        calculator = CivilCalculator()

        # Large commercial demand
        demand = 250.0  # GPM

        service_size, pressure_required = calculator.design_water_service(demand)

        # Should be 4 inch or larger
        assert service_size >= 4.0
        assert pressure_required > 40.0

    def test_design_sewer_service_small(self):
        """Test sewer service sizing for small flow."""
        calculator = CivilCalculator()

        # Small residential flow
        flow = 20.0  # GPM

        service_size, slope = calculator.design_sewer_service(flow)

        # Should be minimum 4 inch
        assert service_size == 4.0
        # Should have 2% slope for 4 inch pipe
        assert slope == 2.0

    def test_design_sewer_service_medium(self):
        """Test sewer service sizing for medium flow."""
        calculator = CivilCalculator()

        # Medium flow
        flow = 300.0  # GPM

        service_size, slope = calculator.design_sewer_service(flow)

        # Should be 6 inch
        assert service_size == 6.0
        # Should have 1% slope for 6 inch pipe
        assert slope == 1.0

    def test_design_sewer_service_large(self):
        """Test sewer service sizing for large flow."""
        calculator = CivilCalculator()

        # Large commercial flow
        flow = 600.0  # GPM

        service_size, slope = calculator.design_sewer_service(flow)

        # Should be 8 inch
        assert service_size == 8.0
        # Should have 0.5% slope for 8 inch pipe
        assert slope == 0.5


class TestRainfallData:
    """Tests for RainfallData dataclass."""

    def test_rainfall_data_creation(self):
        """Test creating rainfall data."""
        rainfall = RainfallData(
            intensity=3.5,
            duration=1.0,
            return_period=25,
            runoff_coefficient=0.7,
        )

        assert rainfall.intensity == 3.5
        assert rainfall.duration == 1.0
        assert rainfall.return_period == 25
        assert rainfall.runoff_coefficient == 0.7


class TestUtilityLoads:
    """Tests for UtilityLoads dataclass."""

    def test_utility_loads_creation_without_gas(self):
        """Test creating utility loads without gas."""
        loads = UtilityLoads(
            water_demand=50.0,
            sewer_flow=45.0,
        )

        assert loads.water_demand == 50.0
        assert loads.sewer_flow == 45.0
        assert loads.gas_demand is None

    def test_utility_loads_creation_with_gas(self):
        """Test creating utility loads with gas."""
        loads = UtilityLoads(
            water_demand=50.0,
            sewer_flow=45.0,
            gas_demand=100.0,
        )

        assert loads.water_demand == 50.0
        assert loads.sewer_flow == 45.0
        assert loads.gas_demand == 100.0
