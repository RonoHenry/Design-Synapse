"""Property-based tests for civil engineering calculations.

**Validates: Requirements 3.1, 3.2, 3.3, 3.4**

This module tests properties for civil engineering calculations including:
- Cut/fill volume conservation
- Stormwater runoff reasonableness
- Utility sizing validity
"""
import hypothesis
import pytest
from hypothesis import assume, given, settings
from hypothesis import strategies as st
from src.calculations.civil_calculator import (CivilCalculator, GradingPoint,
                                               RainfallData, SiteData,
                                               UtilityLoads)


# Strategy for generating valid site data
@st.composite
def site_data_strategy(draw):
    """Generate valid SiteData instances."""
    area = draw(
        st.floats(min_value=0.1, max_value=100.0, allow_nan=False, allow_infinity=False)
    )

    # Generate 2-10 elevation points
    num_points = draw(st.integers(min_value=2, max_value=10))
    existing_elevations = {}

    for i in range(num_points):
        x = i * 50.0  # 50 ft spacing
        y = 0.0
        point_id = f"{x}_{y}"
        elevation = draw(
            st.floats(
                min_value=50.0, max_value=200.0, allow_nan=False, allow_infinity=False
            )
        )
        existing_elevations[point_id] = elevation

    soil_type = draw(st.sampled_from(["clay", "sand", "silt", "rock"]))
    permeability = draw(
        st.floats(min_value=0.0, max_value=10.0, allow_nan=False, allow_infinity=False)
    )
    slope_percent = draw(
        st.floats(min_value=0.0, max_value=20.0, allow_nan=False, allow_infinity=False)
    )

    return SiteData(
        area=area,
        existing_elevations=existing_elevations,
        soil_type=soil_type,
        permeability=permeability,
        slope_percent=slope_percent,
    )


# Strategy for generating rainfall data
@st.composite
def rainfall_data_strategy(draw):
    """Generate valid RainfallData instances."""
    intensity = draw(
        st.floats(min_value=0.5, max_value=10.0, allow_nan=False, allow_infinity=False)
    )
    duration = draw(
        st.floats(min_value=0.25, max_value=24.0, allow_nan=False, allow_infinity=False)
    )
    return_period = draw(st.sampled_from([2, 5, 10, 25, 50, 100]))
    runoff_coefficient = draw(
        st.floats(min_value=0.1, max_value=0.95, allow_nan=False, allow_infinity=False)
    )

    return RainfallData(
        intensity=intensity,
        duration=duration,
        return_period=return_period,
        runoff_coefficient=runoff_coefficient,
    )


@pytest.mark.property
class TestCivilCalculationProperties:
    """Property-based tests for civil engineering calculations."""

    def setup_method(self):
        """Set up test fixtures."""
        self.calculator = CivilCalculator()

    @given(site_data=site_data_strategy())
    @settings(max_examples=100, suppress_health_check=[hypothesis.HealthCheck.too_slow])
    def test_cut_fill_volume_conservation(self, site_data):
        """
        Property 4: Cut/fill volume conservation.

        **Validates: Requirements 3.1**

        The total cut volume plus fill volume should equal the net volume change.
        This is a fundamental conservation principle: earth removed (cut) plus
        earth added (fill) equals the net change in earth volume.

        Mathematical property:
        net_volume = cut_volume - fill_volume
        """
        # Generate target elevations
        target_elevations = {}
        for point_id, existing_elev in site_data.existing_elevations.items():
            # Vary elevations to create both cut and fill
            if hash(point_id) % 2 == 0:
                # Cut (lower elevation)
                target_elevations[point_id] = existing_elev - 2.0
            else:
                # Fill (raise elevation)
                target_elevations[point_id] = existing_elev + 1.5

        result = self.calculator.design_grading(
            site_data, target_elevations, grid_spacing=50.0
        )

        # Property: net_volume = cut_volume - fill_volume
        expected_net = result.cut_volume - result.fill_volume

        # Allow small floating point tolerance
        tolerance = 0.01
        assert (
            abs(result.net_volume - expected_net) < tolerance
        ), f"Volume conservation violated: net={result.net_volume}, cut={result.cut_volume}, fill={result.fill_volume}"

        # Additional check: volumes should be non-negative
        assert (
            result.cut_volume >= 0
        ), f"Cut volume must be non-negative: {result.cut_volume}"
        assert (
            result.fill_volume >= 0
        ), f"Fill volume must be non-negative: {result.fill_volume}"

    @given(site_data=site_data_strategy())
    @settings(max_examples=100)
    def test_grading_volumes_are_non_negative(self, site_data):
        """
        Property: All grading volumes are non-negative.

        Cut and fill volumes represent physical quantities and must be non-negative.
        """
        target_elevations = {}
        for point_id, existing_elev in site_data.existing_elevations.items():
            target_elevations[point_id] = existing_elev - 1.0

        result = self.calculator.design_grading(
            site_data, target_elevations, grid_spacing=50.0
        )

        assert (
            result.cut_volume >= 0
        ), f"Cut volume must be non-negative: {result.cut_volume}"
        assert (
            result.fill_volume >= 0
        ), f"Fill volume must be non-negative: {result.fill_volume}"
        assert (
            result.max_cut_depth >= 0
        ), f"Max cut depth must be non-negative: {result.max_cut_depth}"
        assert (
            result.max_fill_depth >= 0
        ), f"Max fill depth must be non-negative: {result.max_fill_depth}"

    @given(site_data=site_data_strategy())
    @settings(max_examples=100)
    def test_no_grading_produces_zero_volumes(self, site_data):
        """
        Property: When target elevations equal existing elevations, volumes are zero.

        No grading change should result in zero cut and fill volumes.
        """
        # Target elevations same as existing
        target_elevations = site_data.existing_elevations.copy()

        result = self.calculator.design_grading(
            site_data, target_elevations, grid_spacing=50.0
        )

        tolerance = 0.01
        assert (
            abs(result.cut_volume) < tolerance
        ), f"No grading should give zero cut: {result.cut_volume}"
        assert (
            abs(result.fill_volume) < tolerance
        ), f"No grading should give zero fill: {result.fill_volume}"
        assert (
            abs(result.net_volume) < tolerance
        ), f"No grading should give zero net: {result.net_volume}"

    @given(site_data=site_data_strategy())
    @settings(max_examples=100)
    def test_uniform_cut_produces_only_cut_volume(self, site_data):
        """
        Property: Uniform lowering of all elevations produces only cut volume.

        When all points are lowered, there should be cut but no fill.
        """
        # Lower all elevations by 2 feet
        target_elevations = {
            point_id: elev - 2.0
            for point_id, elev in site_data.existing_elevations.items()
        }

        result = self.calculator.design_grading(
            site_data, target_elevations, grid_spacing=50.0
        )

        tolerance = 0.01
        assert (
            result.cut_volume > 0
        ), f"Uniform cut should produce cut volume: {result.cut_volume}"
        assert (
            abs(result.fill_volume) < tolerance
        ), f"Uniform cut should have no fill: {result.fill_volume}"
        assert (
            result.net_volume > 0
        ), f"Uniform cut should have positive net: {result.net_volume}"

    @given(site_data=site_data_strategy())
    @settings(max_examples=100)
    def test_uniform_fill_produces_only_fill_volume(self, site_data):
        """
        Property: Uniform raising of all elevations produces only fill volume.

        When all points are raised, there should be fill but no cut.
        """
        # Raise all elevations by 3 feet
        target_elevations = {
            point_id: elev + 3.0
            for point_id, elev in site_data.existing_elevations.items()
        }

        result = self.calculator.design_grading(
            site_data, target_elevations, grid_spacing=50.0
        )

        tolerance = 0.01
        assert (
            abs(result.cut_volume) < tolerance
        ), f"Uniform fill should have no cut: {result.cut_volume}"
        assert (
            result.fill_volume > 0
        ), f"Uniform fill should produce fill volume: {result.fill_volume}"
        assert (
            result.net_volume < 0
        ), f"Uniform fill should have negative net: {result.net_volume}"

    @given(
        site_data=site_data_strategy(),
        rainfall_data=rainfall_data_strategy(),
    )
    @settings(max_examples=100)
    def test_stormwater_runoff_is_non_negative(self, site_data, rainfall_data):
        """
        Property: Stormwater runoff rate is always non-negative.

        Runoff represents flow rate which must be non-negative.
        """
        runoff_rate = self.calculator.calculate_stormwater_runoff(
            site_data, rainfall_data
        )

        assert runoff_rate >= 0, f"Runoff rate must be non-negative: {runoff_rate}"

    @given(
        site_data=site_data_strategy(),
        rainfall_data=rainfall_data_strategy(),
    )
    @settings(max_examples=100)
    def test_stormwater_runoff_proportional_to_area(self, site_data, rainfall_data):
        """
        Property: Runoff is proportional to drainage area.

        Per Rational Method: Q = C × I × A
        Doubling area should double runoff.
        """
        runoff_single = self.calculator.calculate_stormwater_runoff(
            site_data, rainfall_data
        )

        # Double the area
        site_data_double = SiteData(
            area=site_data.area * 2,
            existing_elevations=site_data.existing_elevations,
            soil_type=site_data.soil_type,
            permeability=site_data.permeability,
            slope_percent=site_data.slope_percent,
        )

        runoff_double = self.calculator.calculate_stormwater_runoff(
            site_data_double, rainfall_data
        )

        # Should be approximately double
        tolerance = 0.01
        expected_double = runoff_single * 2
        assert (
            abs(runoff_double - expected_double) < tolerance
        ), f"Runoff not proportional to area: {runoff_double} != 2 * {runoff_single}"

    @given(
        runoff_volume=st.floats(
            min_value=1000.0, max_value=100000.0, allow_nan=False, allow_infinity=False
        ),
        release_rate=st.floats(
            min_value=1.0, max_value=20.0, allow_nan=False, allow_infinity=False
        ),
        duration=st.floats(
            min_value=0.5, max_value=6.0, allow_nan=False, allow_infinity=False
        ),
    )
    @settings(max_examples=100)
    def test_detention_pond_sizing_is_reasonable(
        self, runoff_volume, release_rate, duration
    ):
        """
        Property: Detention pond sizing produces reasonable results.

        Detention volume should be non-negative and include freeboard.
        """
        detention_volume, depth = self.calculator.size_detention_pond(
            runoff_volume, release_rate, duration
        )

        assert (
            detention_volume >= 0
        ), f"Detention volume must be non-negative: {detention_volume}"
        assert depth > 0, f"Detention depth must be positive: {depth}"
        assert 2.0 <= depth <= 10.0, f"Detention depth should be reasonable: {depth}"

    @given(
        flow_rate=st.floats(
            min_value=0.5, max_value=100.0, allow_nan=False, allow_infinity=False
        ),
        slope=st.floats(
            min_value=0.25, max_value=10.0, allow_nan=False, allow_infinity=False
        ),
    )
    @settings(max_examples=100)
    def test_pipe_sizing_is_reasonable(self, flow_rate, slope):
        """
        Property: Pipe sizing produces reasonable diameters.

        Pipe diameter should be within standard sizes and increase with flow.
        """
        diameter = self.calculator.calculate_pipe_size(flow_rate, slope)

        assert diameter >= 6.0, f"Pipe diameter should be at least 6 inches: {diameter}"
        assert diameter <= 72.0, f"Pipe diameter should be reasonable: {diameter}"

    @given(
        site_data=site_data_strategy(),
        target_elevations=st.dictionaries(
            st.text(min_size=3, max_size=10),
            st.floats(
                min_value=50.0, max_value=200.0, allow_nan=False, allow_infinity=False
            ),
            min_size=2,
            max_size=10,
        ),
        rainfall_data=rainfall_data_strategy(),
    )
    @settings(max_examples=50, suppress_health_check=[hypothesis.HealthCheck.too_slow])
    def test_property_7_civil_design_validity(
        self, site_data, target_elevations, rainfall_data
    ):
        """
        Property 7: Civil design validity.

        **Validates: Requirements 3.1, 3.2, 3.3**

        For any valid site data and design parameters, civil engineering
        calculations should produce valid, physically meaningful results
        that satisfy basic engineering constraints and conservation laws.

        This property ensures that:
        1. Grading designs conserve volume (cut + fill = net change)
        2. Stormwater calculations follow rational method principles
        3. All results are within reasonable engineering ranges
        4. Unit consistency is maintained throughout calculations
        """
        # Test grading design validity
        grading_result = self.calculator.design_grading(
            site_data, target_elevations, grid_spacing=50.0
        )

        # Grading validity checks
        assert grading_result.cut_volume >= 0, "Cut volume must be non-negative"
        assert grading_result.fill_volume >= 0, "Fill volume must be non-negative"
        assert grading_result.max_cut_depth >= 0, "Max cut depth must be non-negative"
        assert grading_result.max_fill_depth >= 0, "Max fill depth must be non-negative"
        assert grading_result.average_slope >= 0, "Average slope must be non-negative"
        # Note: Slopes can exceed 100% (45 degrees) in civil engineering, so no upper limit

        # Volume conservation (fundamental engineering principle)
        expected_net = grading_result.cut_volume - grading_result.fill_volume
        tolerance = 0.01
        assert (
            abs(grading_result.net_volume - expected_net) < tolerance
        ), "Volume conservation violated in grading design"

        # Test stormwater design validity
        runoff_rate = self.calculator.calculate_stormwater_runoff(
            site_data, rainfall_data
        )

        # Stormwater validity checks
        assert runoff_rate >= 0, "Runoff rate must be non-negative"

        # Rational method validation: Q = C × I × A
        expected_runoff = (
            rainfall_data.runoff_coefficient * rainfall_data.intensity * site_data.area
        )
        assert (
            abs(runoff_rate - expected_runoff) < 0.01
        ), "Stormwater calculation must follow rational method"

        # Test detention pond sizing validity
        runoff_volume = runoff_rate * rainfall_data.duration * 3600
        release_rate = runoff_rate * 0.5  # 50% of peak
        detention_volume, detention_depth = self.calculator.size_detention_pond(
            runoff_volume, release_rate, rainfall_data.duration
        )

        # Detention validity checks
        assert detention_volume >= 0, "Detention volume must be non-negative"
        assert detention_depth > 0, "Detention depth must be positive"
        assert 2.0 <= detention_depth <= 10.0, "Detention depth must be reasonable"

        # Test pipe sizing validity
        pipe_diameter = self.calculator.calculate_pipe_size(runoff_rate, slope=2.0)

        # Pipe sizing validity checks
        assert pipe_diameter >= 6.0, "Pipe diameter must be at least 6 inches"
        # Note: Large sites may require pipes larger than 72 inches

        # Test utility sizing validity
        from src.calculations.civil_calculator import UtilityLoads

        # Generate reasonable utility loads
        water_demand = min(max(site_data.area * 10, 10.0), 200.0)  # 10-200 GPM
        sewer_flow = water_demand * 0.8  # 80% of water demand

        utility_loads = UtilityLoads(
            water_demand=water_demand, sewer_flow=sewer_flow, gas_demand=150.0
        )

        water_size, water_pressure = self.calculator.design_water_service(
            utility_loads.water_demand, pressure_available=60.0
        )
        sewer_size, sewer_slope = self.calculator.design_sewer_service(
            utility_loads.sewer_flow
        )

        # Utility validity checks
        assert 0.75 <= water_size <= 6.0, "Water service size must be reasonable"
        assert 40.0 <= water_pressure <= 80.0, "Water pressure must be reasonable"
        assert 4.0 <= sewer_size <= 8.0, "Sewer service size must be reasonable"
        assert 0.5 <= sewer_slope <= 4.0, "Sewer slope must be reasonable"

        # Cross-validation: larger sites should generally require larger utilities
        if site_data.area > 5.0:
            assert water_size >= 1.0, "Large sites should require larger water service"
            assert (
                sewer_size >= 4.0
            ), "Large sites should require adequate sewer service"

        # Unit system consistency check
        assert (
            grading_result.unit_system == "imperial"
        ), "Unit system must be consistent"
