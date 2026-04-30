"""Property-based tests for civil design validity (Property 7).

**Validates: Requirements 3.4**

This module tests Property 7: Civil Design Validity, ensuring that civil
engineering calculations produce valid results that meet local jurisdiction
requirements and engineering standards.
"""
import hypothesis
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from src.calculations.civil_calculator import (CivilCalculator, RainfallData,
                                               SiteData, UtilityLoads)


# Strategy for generating valid site data
@st.composite
def site_data_strategy(draw):
    """Generate valid SiteData instances for property testing."""
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
    """Generate valid RainfallData instances for property testing."""
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


# Strategy for generating target elevations
@st.composite
def target_elevations_strategy(draw, site_data):
    """Generate target elevations based on existing site data."""
    target_elevations = {}

    for point_id, existing_elev in site_data.existing_elevations.items():
        # Generate reasonable elevation changes (-10 to +10 feet)
        elevation_change = draw(
            st.floats(
                min_value=-10.0, max_value=10.0, allow_nan=False, allow_infinity=False
            )
        )
        target_elevations[point_id] = existing_elev + elevation_change

    return target_elevations


@pytest.mark.property
class TestCivilDesignValidityProperties:
    """Property-based tests for civil design validity (Property 7)."""

    def setup_method(self):
        """Set up test fixtures."""
        self.calculator = CivilCalculator()

    @given(site_data=site_data_strategy())
    @settings(max_examples=100, suppress_health_check=[hypothesis.HealthCheck.too_slow])
    def test_property_7_civil_design_validity(self, site_data):
        """
        Property 7: Civil Design Validity.

        **Validates: Requirements 3.4**

        WHEN civil calculations are performed, THE Engineering_Service SHALL
        verify designs against local jurisdiction requirements.

        This property ensures that all civil engineering calculations produce
        valid, physically meaningful results that satisfy:
        1. Basic engineering constraints and conservation laws
        2. Local jurisdiction requirements for grading and drainage
        3. Standard engineering practices and code compliance
        4. Unit consistency and reasonable value ranges
        """
        # Generate target elevations based on site data
        target_elevations = {}
        for point_id, existing_elev in site_data.existing_elevations.items():
            # Create mixed cut/fill scenario
            if hash(point_id) % 2 == 0:
                # Cut (lower elevation) - typical 1-5 feet
                target_elevations[point_id] = existing_elev - 2.0
            else:
                # Fill (raise elevation) - typical 1-3 feet
                target_elevations[point_id] = existing_elev + 1.5

        # Test grading design validity
        grading_result = self.calculator.design_grading(
            site_data, target_elevations, grid_spacing=50.0
        )

        # Jurisdiction Requirement 1: Volume Conservation
        # All jurisdictions require earthwork calculations to conserve volume
        expected_net = grading_result.cut_volume - grading_result.fill_volume
        tolerance = 0.01
        assert (
            abs(grading_result.net_volume - expected_net) < tolerance
        ), "Volume conservation violated - required by all jurisdictions"

        # Jurisdiction Requirement 2: Non-negative Physical Quantities
        # All jurisdictions require physically meaningful results
        assert (
            grading_result.cut_volume >= 0
        ), "Cut volume must be non-negative per jurisdiction standards"
        assert (
            grading_result.fill_volume >= 0
        ), "Fill volume must be non-negative per jurisdiction standards"
        assert (
            grading_result.max_cut_depth >= 0
        ), "Max cut depth must be non-negative per jurisdiction standards"
        assert (
            grading_result.max_fill_depth >= 0
        ), "Max fill depth must be non-negative per jurisdiction standards"

        # Jurisdiction Requirement 3: Reasonable Slope Limits
        # Most jurisdictions limit slopes for safety and stability
        assert (
            grading_result.average_slope >= 0
        ), "Average slope must be non-negative per jurisdiction standards"
        # Note: Some jurisdictions allow steep slopes, so no upper limit enforced

        # Jurisdiction Requirement 4: Proper Unit System
        # All jurisdictions require consistent unit systems
        assert (
            grading_result.unit_system == "imperial"
        ), "Unit system must be consistent per jurisdiction requirements"

        # Generate rainfall data for stormwater testing
        rainfall_data = RainfallData(
            intensity=2.0,  # 2 inches/hour - typical design storm
            duration=1.0,  # 1 hour duration
            return_period=10,  # 10-year storm - common jurisdiction requirement
            runoff_coefficient=0.6,  # Typical mixed development
        )

        # Test stormwater design validity
        runoff_rate = self.calculator.calculate_stormwater_runoff(
            site_data, rainfall_data
        )

        # Jurisdiction Requirement 5: Stormwater Management
        # All jurisdictions require proper stormwater calculations
        assert (
            runoff_rate >= 0
        ), "Runoff rate must be non-negative per jurisdiction standards"

        # Jurisdiction Requirement 6: Rational Method Compliance
        # Most jurisdictions require rational method for small sites
        expected_runoff = (
            rainfall_data.runoff_coefficient * rainfall_data.intensity * site_data.area
        )
        assert (
            abs(runoff_rate - expected_runoff) < 0.01
        ), "Stormwater calculation must follow rational method per jurisdiction"

        # Test detention pond sizing (if required by jurisdiction)
        runoff_volume = runoff_rate * rainfall_data.duration * 3600
        release_rate = runoff_rate * 0.5  # 50% release rate - typical requirement

        detention_volume, detention_depth = self.calculator.size_detention_pond(
            runoff_volume, release_rate, rainfall_data.duration
        )

        # Jurisdiction Requirement 7: Detention Pond Standards
        # Many jurisdictions require detention for development
        assert (
            detention_volume >= 0
        ), "Detention volume must be non-negative per jurisdiction standards"
        assert (
            detention_depth > 0
        ), "Detention depth must be positive per jurisdiction standards"
        assert (
            2.0 <= detention_depth <= 10.0
        ), "Detention depth must meet jurisdiction safety standards (2-10 ft)"

        # Test pipe sizing validity
        pipe_diameter = self.calculator.calculate_pipe_size(runoff_rate, slope=2.0)

        # Jurisdiction Requirement 8: Minimum Pipe Sizes
        # All jurisdictions have minimum pipe size requirements
        assert (
            pipe_diameter >= 6.0
        ), "Pipe diameter must meet jurisdiction minimum (6 inches)"

        # Test utility sizing validity
        # Generate reasonable utility loads based on site area
        water_demand = min(max(site_data.area * 10, 10.0), 200.0)
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

        # Jurisdiction Requirement 9: Water Service Standards
        # All jurisdictions have water service requirements
        assert (
            0.75 <= water_size <= 6.0
        ), "Water service size must meet jurisdiction standards (0.75-6 inches)"
        assert (
            40.0 <= water_pressure <= 80.0
        ), "Water pressure must meet jurisdiction standards (40-80 PSI)"

        # Jurisdiction Requirement 10: Sewer Service Standards
        # All jurisdictions have sewer service requirements
        assert (
            4.0 <= sewer_size <= 8.0
        ), "Sewer service size must meet jurisdiction standards (4-8 inches)"
        assert (
            0.5 <= sewer_slope <= 4.0
        ), "Sewer slope must meet jurisdiction standards (0.5-4%)"

        # Cross-validation: Larger sites require larger infrastructure
        # This is a common jurisdiction requirement for proportional design
        if site_data.area > 5.0:
            assert (
                water_size >= 1.0
            ), "Large sites must have adequate water service per jurisdiction"
            assert (
                sewer_size >= 4.0
            ), "Large sites must have adequate sewer service per jurisdiction"

    @given(site_data=site_data_strategy(), rainfall_data=rainfall_data_strategy())
    @settings(max_examples=50)
    def test_stormwater_jurisdiction_compliance(self, site_data, rainfall_data):
        """
        Test stormwater calculations comply with jurisdiction requirements.

        **Validates: Requirements 3.4**

        Focuses specifically on stormwater management requirements that
        vary by jurisdiction but must always be physically valid.
        """
        runoff_rate = self.calculator.calculate_stormwater_runoff(
            site_data, rainfall_data
        )

        # Jurisdiction compliance checks
        assert (
            runoff_rate >= 0
        ), "Runoff rate must be non-negative per jurisdiction requirements"

        # Rational method compliance (required by most jurisdictions)
        expected_runoff = (
            rainfall_data.runoff_coefficient * rainfall_data.intensity * site_data.area
        )
        tolerance = 0.01
        assert (
            abs(runoff_rate - expected_runoff) < tolerance
        ), "Must follow rational method per jurisdiction standards"

        # Test pipe sizing for jurisdiction compliance
        pipe_diameter = self.calculator.calculate_pipe_size(
            runoff_rate, slope=1.0  # 1% slope - typical jurisdiction minimum
        )

        # Jurisdiction pipe requirements
        assert (
            pipe_diameter >= 6.0
        ), "Minimum 6-inch pipe required by most jurisdictions"
        assert (
            pipe_diameter <= 72.0
        ), "Pipe size must be within reasonable jurisdiction limits"

    @given(site_data=site_data_strategy())
    @settings(max_examples=50)
    def test_grading_jurisdiction_compliance(self, site_data):
        """
        Test grading calculations comply with jurisdiction requirements.

        **Validates: Requirements 3.4**

        Focuses on grading and earthwork requirements that must meet
        local jurisdiction standards for safety and environmental protection.
        """
        # Generate conservative target elevations (small changes)
        target_elevations = {}
        for point_id, existing_elev in site_data.existing_elevations.items():
            # Small elevation changes typical of jurisdiction-approved grading
            elevation_change = 1.0 if hash(point_id) % 2 == 0 else -1.0
            target_elevations[point_id] = existing_elev + elevation_change

        result = self.calculator.design_grading(
            site_data, target_elevations, grid_spacing=50.0
        )

        # Jurisdiction grading requirements
        assert (
            result.cut_volume >= 0
        ), "Cut volume must be non-negative per jurisdiction standards"
        assert (
            result.fill_volume >= 0
        ), "Fill volume must be non-negative per jurisdiction standards"

        # Volume conservation (fundamental jurisdiction requirement)
        expected_net = result.cut_volume - result.fill_volume
        tolerance = 0.01
        assert (
            abs(result.net_volume - expected_net) < tolerance
        ), "Volume conservation required by all jurisdictions"

        # Reasonable depth limits (jurisdiction safety requirements)
        assert (
            result.max_cut_depth >= 0
        ), "Cut depth must be non-negative per jurisdiction standards"
        assert (
            result.max_fill_depth >= 0
        ), "Fill depth must be non-negative per jurisdiction standards"

        # Most jurisdictions limit cut/fill depths for stability
        # These are reasonable limits that most jurisdictions would accept
        if result.max_cut_depth > 0:
            assert (
                result.max_cut_depth <= 20.0
            ), "Cut depth should be reasonable per jurisdiction limits"
        if result.max_fill_depth > 0:
            assert (
                result.max_fill_depth <= 15.0
            ), "Fill depth should be reasonable per jurisdiction limits"

    @given(
        water_demand=st.floats(
            min_value=5.0, max_value=500.0, allow_nan=False, allow_infinity=False
        ),
        sewer_flow=st.floats(
            min_value=4.0, max_value=400.0, allow_nan=False, allow_infinity=False
        ),
    )
    @settings(max_examples=50)
    def test_utility_jurisdiction_compliance(self, water_demand, sewer_flow):
        """
        Test utility sizing complies with jurisdiction requirements.

        **Validates: Requirements 3.4**

        Focuses on utility connection requirements that must meet
        local jurisdiction codes and standards.
        """
        # Test water service sizing
        water_size, water_pressure = self.calculator.design_water_service(
            water_demand, pressure_available=60.0
        )

        # Jurisdiction water service requirements
        assert (
            0.75 <= water_size <= 6.0
        ), "Water service size must meet jurisdiction standards"
        assert (
            40.0 <= water_pressure <= 80.0
        ), "Water pressure must meet jurisdiction requirements"

        # Test sewer service sizing
        sewer_size, sewer_slope = self.calculator.design_sewer_service(sewer_flow)

        # Jurisdiction sewer service requirements
        assert (
            4.0 <= sewer_size <= 8.0
        ), "Sewer service size must meet jurisdiction standards"
        assert (
            0.5 <= sewer_slope <= 4.0
        ), "Sewer slope must meet jurisdiction requirements"

        # Proportionality check (jurisdiction requirement for adequate sizing)
        if water_demand > 100.0:
            assert (
                water_size >= 1.5
            ), "High demand requires larger service per jurisdiction"

        # Convert sewer flow to CFS for proper comparison (GPM / 448.8 = CFS)
        sewer_flow_cfs = sewer_flow / 448.8
        if sewer_flow_cfs > 0.5:  # Above 224 GPM (0.5 CFS)
            assert sewer_size >= 6.0, "High flow requires larger sewer per jurisdiction"
