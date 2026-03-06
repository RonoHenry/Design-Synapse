"""Property-based tests for load calculation reasonableness.

**Validates: Requirements 1.1**

This module tests the property that all calculated loads are non-negative
and proportional to inputs. Tests LoadCalculator methods for dead loads,
live loads, wind loads, and seismic loads.
"""
import hypothesis
import pytest
from hypothesis import assume, given, settings
from hypothesis import strategies as st
from src.calculations.load_calculator import (BuildingData, Component,
                                              LoadCalculator, OccupancyType,
                                              SeismicData)


# Strategy for generating valid components
@st.composite
def component_strategy(draw):
    """Generate valid Component instances."""
    # Use simple ASCII text to avoid slow generation
    name = draw(
        st.text(
            alphabet=st.characters(min_codepoint=65, max_codepoint=90),
            min_size=1,
            max_size=10,
        )
    )
    weight_per_area = draw(
        st.floats(min_value=0.0, max_value=500.0, allow_nan=False, allow_infinity=False)
    )
    area = draw(
        st.floats(
            min_value=0.0, max_value=10000.0, allow_nan=False, allow_infinity=False
        )
    )
    return Component(name=name, weight_per_area=weight_per_area, area=area)


# Strategy for generating valid building data
@st.composite
def building_data_strategy(draw):
    """Generate valid BuildingData instances."""
    height = draw(
        st.floats(
            min_value=10.0, max_value=500.0, allow_nan=False, allow_infinity=False
        )
    )
    width = draw(
        st.floats(
            min_value=10.0, max_value=500.0, allow_nan=False, allow_infinity=False
        )
    )
    length = draw(
        st.floats(
            min_value=10.0, max_value=500.0, allow_nan=False, allow_infinity=False
        )
    )
    exposure_category = draw(st.sampled_from(["B", "C", "D"]))
    return BuildingData(
        height=height, width=width, length=length, exposure_category=exposure_category
    )


# Strategy for generating valid seismic data
@st.composite
def seismic_data_strategy(draw):
    """Generate valid SeismicData instances."""
    ss = draw(
        st.floats(min_value=0.0, max_value=2.5, allow_nan=False, allow_infinity=False)
    )
    s1 = draw(
        st.floats(min_value=0.0, max_value=1.5, allow_nan=False, allow_infinity=False)
    )
    site_class = draw(st.sampled_from(["A", "B", "C", "D", "E", "F"]))
    importance_factor = draw(
        st.floats(min_value=1.0, max_value=1.5, allow_nan=False, allow_infinity=False)
    )
    response_modification_factor = draw(
        st.floats(min_value=1.0, max_value=8.0, allow_nan=False, allow_infinity=False)
    )
    return SeismicData(
        ss=ss,
        s1=s1,
        site_class=site_class,
        importance_factor=importance_factor,
        response_modification_factor=response_modification_factor,
    )


@pytest.mark.property
class TestLoadCalculationProperties:
    """Property-based tests for load calculation reasonableness."""

    def setup_method(self):
        """Set up test fixtures."""
        self.calculator = LoadCalculator()

    @given(components=st.lists(component_strategy(), min_size=0, max_size=10))
    @settings(max_examples=100, suppress_health_check=[hypothesis.HealthCheck.too_slow])
    def test_dead_load_is_non_negative(self, components):
        """
        Property: Dead load calculations always produce non-negative results.

        Dead loads represent the weight of permanent building components,
        which must always be non-negative.
        """
        dead_load = self.calculator.calculate_dead_load(components)
        assert dead_load >= 0, f"Dead load must be non-negative, got {dead_load}"

    @given(components=st.lists(component_strategy(), min_size=1, max_size=10))
    @settings(max_examples=100)
    def test_dead_load_increases_with_components(self, components):
        """
        Property: Adding components increases or maintains dead load.

        Dead load should never decrease when adding components.
        """
        # Calculate load with all components
        full_load = self.calculator.calculate_dead_load(components)

        # Calculate load with subset (all but last)
        if len(components) > 1:
            subset_load = self.calculator.calculate_dead_load(components[:-1])
            assert (
                full_load >= subset_load
            ), f"Adding components should not decrease load: {full_load} < {subset_load}"

    @given(
        weight_per_area=st.floats(
            min_value=0.0, max_value=500.0, allow_nan=False, allow_infinity=False
        ),
        area=st.floats(
            min_value=0.0, max_value=10000.0, allow_nan=False, allow_infinity=False
        ),
    )
    @settings(max_examples=100)
    def test_dead_load_proportional_to_weight_and_area(self, weight_per_area, area):
        """
        Property: Dead load is proportional to weight per area and area.

        Doubling either weight or area should double the load.
        """
        component = Component(name="test", weight_per_area=weight_per_area, area=area)

        load = self.calculator.calculate_dead_load([component])
        expected_load = weight_per_area * area

        # Allow small floating point tolerance
        tolerance = 1e-6
        assert (
            abs(load - expected_load) < tolerance
        ), f"Load {load} not proportional to weight {weight_per_area} * area {area} = {expected_load}"

    @given(
        occupancy=st.sampled_from(list(OccupancyType)),
        area=st.floats(
            min_value=0.0, max_value=50000.0, allow_nan=False, allow_infinity=False
        ),
    )
    @settings(max_examples=100)
    def test_live_load_is_non_negative(self, occupancy, area):
        """
        Property: Live load calculations always produce non-negative results.

        Live loads represent occupancy loads, which must always be non-negative.
        """
        live_load = self.calculator.calculate_live_load(occupancy, area)
        assert live_load >= 0, f"Live load must be non-negative, got {live_load}"

    @given(
        occupancy=st.sampled_from(list(OccupancyType)),
        area=st.floats(
            min_value=0.1, max_value=50000.0, allow_nan=False, allow_infinity=False
        ),
    )
    @settings(max_examples=100)
    def test_live_load_proportional_to_area(self, occupancy, area):
        """
        Property: Live load is proportional to area for a given occupancy.

        Doubling the area should double the live load.
        """
        load_single = self.calculator.calculate_live_load(occupancy, area)
        load_double = self.calculator.calculate_live_load(occupancy, area * 2)

        # Allow small floating point tolerance
        tolerance = 1e-6
        expected_double = load_single * 2

        assert (
            abs(load_double - expected_double) < tolerance
        ), f"Live load not proportional to area: {load_double} != 2 * {load_single}"

    @given(
        area=st.floats(
            min_value=100.0, max_value=50000.0, allow_nan=False, allow_infinity=False
        ),
    )
    @settings(max_examples=100)
    def test_live_load_varies_by_occupancy(self, area):
        """
        Property: Different occupancy types produce different live loads.

        Storage occupancies should have higher loads than residential.
        """
        residential_load = self.calculator.calculate_live_load(
            OccupancyType.RESIDENTIAL, area
        )
        storage_heavy_load = self.calculator.calculate_live_load(
            OccupancyType.STORAGE_HEAVY, area
        )

        assert (
            storage_heavy_load > residential_load
        ), f"Heavy storage load {storage_heavy_load} should exceed residential {residential_load}"

    @given(
        building=building_data_strategy(),
        wind_speed=st.floats(
            min_value=85.0, max_value=200.0, allow_nan=False, allow_infinity=False
        ),
    )
    @settings(max_examples=100)
    def test_wind_load_is_non_negative(self, building, wind_speed):
        """
        Property: Wind load calculations always produce non-negative results.

        Wind loads represent pressure on building surfaces, which must be non-negative.
        """
        result = self.calculator.calculate_wind_load(building, wind_speed)

        assert (
            result.design_pressure >= 0
        ), f"Design pressure must be non-negative, got {result.design_pressure}"
        assert (
            result.velocity_pressure >= 0
        ), f"Velocity pressure must be non-negative, got {result.velocity_pressure}"

    @given(
        building=building_data_strategy(),
        wind_speed=st.floats(
            min_value=85.0, max_value=200.0, allow_nan=False, allow_infinity=False
        ),
    )
    @settings(max_examples=100)
    def test_wind_load_increases_with_wind_speed(self, building, wind_speed):
        """
        Property: Wind load increases with wind speed.

        Higher wind speeds should produce higher design pressures.
        """
        # Ensure we have a reasonable range to test
        assume(wind_speed < 180.0)

        result_lower = self.calculator.calculate_wind_load(building, wind_speed)
        result_higher = self.calculator.calculate_wind_load(building, wind_speed * 1.2)

        assert (
            result_higher.design_pressure > result_lower.design_pressure
        ), f"Higher wind speed should increase pressure: {result_higher.design_pressure} <= {result_lower.design_pressure}"

    @given(
        building=building_data_strategy(),
        wind_speed=st.floats(
            min_value=85.0, max_value=150.0, allow_nan=False, allow_infinity=False
        ),
    )
    @settings(max_examples=100)
    def test_wind_load_proportional_to_speed_squared(self, building, wind_speed):
        """
        Property: Wind load is proportional to wind speed squared.

        Per ASCE 7, velocity pressure q = 0.00256 * K * V^2
        """
        result = self.calculator.calculate_wind_load(building, wind_speed)

        # Calculate expected velocity pressure
        kz = self.calculator.EXPOSURE_COEFFICIENTS[building.exposure_category]
        kzt = 1.0
        kd = 0.85
        expected_velocity_pressure = 0.00256 * kz * kzt * kd * (wind_speed**2)

        # Allow small floating point tolerance
        tolerance = 1e-3
        assert (
            abs(result.velocity_pressure - expected_velocity_pressure) < tolerance
        ), f"Velocity pressure {result.velocity_pressure} not proportional to speed squared"

    @given(
        height=st.floats(
            min_value=10.0, max_value=500.0, allow_nan=False, allow_infinity=False
        ),
        width=st.floats(
            min_value=10.0, max_value=500.0, allow_nan=False, allow_infinity=False
        ),
        length=st.floats(
            min_value=10.0, max_value=500.0, allow_nan=False, allow_infinity=False
        ),
        wind_speed=st.floats(
            min_value=85.0, max_value=150.0, allow_nan=False, allow_infinity=False
        ),
    )
    @settings(max_examples=100)
    def test_wind_load_varies_by_exposure(self, height, width, length, wind_speed):
        """
        Property: Wind load varies by exposure category.

        Exposure D (flat, unobstructed) should have higher loads than Exposure B (urban).
        """
        building_b = BuildingData(
            height=height, width=width, length=length, exposure_category="B"
        )
        building_d = BuildingData(
            height=height, width=width, length=length, exposure_category="D"
        )

        result_b = self.calculator.calculate_wind_load(building_b, wind_speed)
        result_d = self.calculator.calculate_wind_load(building_d, wind_speed)

        assert (
            result_d.design_pressure > result_b.design_pressure
        ), f"Exposure D pressure {result_d.design_pressure} should exceed Exposure B {result_b.design_pressure}"

    @given(
        building=building_data_strategy(),
        seismic_data=seismic_data_strategy(),
    )
    @settings(max_examples=100)
    def test_seismic_load_is_non_negative(self, building, seismic_data):
        """
        Property: Seismic load calculations always produce non-negative results.

        Seismic loads represent earthquake forces, which must be non-negative.
        """
        result = self.calculator.calculate_seismic_load(building, seismic_data)

        assert (
            result.base_shear >= 0
        ), f"Base shear must be non-negative, got {result.base_shear}"
        assert (
            result.design_spectral_acceleration_short >= 0
        ), f"SDS must be non-negative, got {result.design_spectral_acceleration_short}"
        assert (
            result.design_spectral_acceleration_1s >= 0
        ), f"SD1 must be non-negative, got {result.design_spectral_acceleration_1s}"

    @given(
        building=building_data_strategy(),
        ss=st.floats(
            min_value=0.1, max_value=2.0, allow_nan=False, allow_infinity=False
        ),
        s1=st.floats(
            min_value=0.1, max_value=1.0, allow_nan=False, allow_infinity=False
        ),
    )
    @settings(max_examples=100)
    def test_seismic_load_increases_with_spectral_acceleration(self, building, ss, s1):
        """
        Property: Seismic load increases with spectral acceleration.

        Higher spectral accelerations should produce higher base shear.
        """
        seismic_data_lower = SeismicData(
            ss=ss,
            s1=s1,
            site_class="C",
            importance_factor=1.0,
            response_modification_factor=5.0,
        )

        seismic_data_higher = SeismicData(
            ss=ss * 1.5,
            s1=s1 * 1.5,
            site_class="C",
            importance_factor=1.0,
            response_modification_factor=5.0,
        )

        result_lower = self.calculator.calculate_seismic_load(
            building, seismic_data_lower
        )
        result_higher = self.calculator.calculate_seismic_load(
            building, seismic_data_higher
        )

        assert (
            result_higher.base_shear > result_lower.base_shear
        ), f"Higher spectral acceleration should increase base shear: {result_higher.base_shear} <= {result_lower.base_shear}"

    @given(
        building=building_data_strategy(),
        seismic_data=seismic_data_strategy(),
    )
    @settings(max_examples=100)
    def test_seismic_load_proportional_to_building_size(self, building, seismic_data):
        """
        Property: Seismic load is proportional to building size.

        Larger buildings (more weight) should have higher base shear.
        """
        # Create a larger building (double dimensions)
        building_larger = BuildingData(
            height=building.height * 2,
            width=building.width * 2,
            length=building.length * 2,
            exposure_category=building.exposure_category,
        )

        result_normal = self.calculator.calculate_seismic_load(building, seismic_data)
        result_larger = self.calculator.calculate_seismic_load(
            building_larger, seismic_data
        )

        # Larger building should have higher base shear
        assert (
            result_larger.base_shear > result_normal.base_shear
        ), f"Larger building should have higher base shear: {result_larger.base_shear} <= {result_normal.base_shear}"

    @given(
        building=building_data_strategy(),
    )
    @settings(max_examples=100)
    def test_seismic_design_category_increases_with_acceleration(self, building):
        """
        Property: Seismic design category increases with spectral acceleration.

        Higher spectral accelerations should result in higher design categories.
        """
        # Low seismic
        seismic_low = SeismicData(
            ss=0.1,
            s1=0.05,
            site_class="C",
            importance_factor=1.0,
            response_modification_factor=5.0,
        )

        # High seismic
        seismic_high = SeismicData(
            ss=1.5,
            s1=0.6,
            site_class="C",
            importance_factor=1.0,
            response_modification_factor=5.0,
        )

        result_low = self.calculator.calculate_seismic_load(building, seismic_low)
        result_high = self.calculator.calculate_seismic_load(building, seismic_high)

        categories = ["A", "B", "C", "D", "E", "F"]
        idx_low = categories.index(result_low.seismic_design_category)
        idx_high = categories.index(result_high.seismic_design_category)

        assert (
            idx_high >= idx_low
        ), f"Higher seismic should have higher category: {result_high.seismic_design_category} < {result_low.seismic_design_category}"

    @given(
        components=st.lists(component_strategy(), min_size=0, max_size=10),
        occupancy=st.sampled_from(list(OccupancyType)),
        area=st.floats(
            min_value=0.0, max_value=10000.0, allow_nan=False, allow_infinity=False
        ),
    )
    @settings(max_examples=100)
    def test_combined_loads_are_non_negative(self, components, occupancy, area):
        """
        Property: Combined dead and live loads are always non-negative.

        Total load combinations must always be non-negative.
        """
        dead_load = self.calculator.calculate_dead_load(components)
        live_load = self.calculator.calculate_live_load(occupancy, area)
        total_load = dead_load + live_load

        assert total_load >= 0, f"Combined load must be non-negative, got {total_load}"

    @given(
        components=st.lists(component_strategy(), min_size=1, max_size=10),
        occupancy=st.sampled_from(list(OccupancyType)),
        area=st.floats(
            min_value=100.0, max_value=10000.0, allow_nan=False, allow_infinity=False
        ),
    )
    @settings(max_examples=100)
    def test_total_load_exceeds_individual_loads(self, components, occupancy, area):
        """
        Property: Total load is greater than or equal to individual load components.

        The sum of loads should be at least as large as any individual component.
        """
        dead_load = self.calculator.calculate_dead_load(components)
        live_load = self.calculator.calculate_live_load(occupancy, area)
        total_load = dead_load + live_load

        assert (
            total_load >= dead_load
        ), f"Total load {total_load} should be >= dead load {dead_load}"
        assert (
            total_load >= live_load
        ), f"Total load {total_load} should be >= live load {live_load}"

    def test_zero_inputs_produce_zero_loads(self):
        """
        Property: Zero inputs produce zero loads.

        Empty components or zero area should result in zero loads.
        """
        # Zero dead load
        dead_load = self.calculator.calculate_dead_load([])
        assert (
            dead_load == 0.0
        ), f"Empty components should give zero load, got {dead_load}"

        # Zero live load
        live_load = self.calculator.calculate_live_load(OccupancyType.RESIDENTIAL, 0.0)
        assert live_load == 0.0, f"Zero area should give zero load, got {live_load}"
