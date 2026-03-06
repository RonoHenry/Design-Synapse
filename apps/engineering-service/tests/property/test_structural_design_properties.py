"""Property-based tests for structural design validity.

**Validates: Requirements 1.2, 1.3, 1.4**

This module tests the property that designed structural members meet
strength and serviceability requirements. Tests BeamDesigner,
ColumnDesigner, and FoundationDesigner to ensure adequate capacity
and deflection limits.
"""
import hypothesis
import pytest
from hypothesis import assume, given, settings
from hypothesis import strategies as st
from src.calculations.beam_designer import (BeamDesigner, BeamGeometry,
                                            BeamLoads, BeamSupportType)
from src.calculations.beam_designer import \
    MaterialProperties as BeamMaterialProperties
from src.calculations.beam_designer import MaterialType as BeamMaterialType
from src.calculations.column_designer import (ColumnDesigner, ColumnGeometry,
                                              ColumnLoads, EndCondition)
from src.calculations.column_designer import \
    MaterialProperties as ColumnMaterialProperties
from src.calculations.column_designer import MaterialType as ColumnMaterialType
from src.calculations.foundation_designer import (FoundationDesigner,
                                                  FoundationGeometry,
                                                  FoundationLoads,
                                                  FoundationType,
                                                  SoilProperties)


# Strategies for beam design
@st.composite
def beam_material_strategy(draw):
    """Generate valid beam material properties."""
    material_type = draw(st.sampled_from(list(BeamMaterialType)))

    if material_type == BeamMaterialType.STEEL:
        yield_strength = draw(
            st.floats(
                min_value=36000.0,
                max_value=60000.0,
                allow_nan=False,
                allow_infinity=False,
            )
        )
        elastic_modulus = 29000000.0  # psi for steel
        density = 490.0  # lb/ft³
    elif material_type == BeamMaterialType.CONCRETE:
        yield_strength = draw(
            st.floats(
                min_value=3000.0,
                max_value=6000.0,
                allow_nan=False,
                allow_infinity=False,
            )
        )
        elastic_modulus = 3600000.0  # psi for concrete
        density = 150.0  # lb/ft³
    else:  # TIMBER
        yield_strength = draw(
            st.floats(
                min_value=1000.0,
                max_value=2000.0,
                allow_nan=False,
                allow_infinity=False,
            )
        )
        elastic_modulus = 1600000.0  # psi for timber
        density = 35.0  # lb/ft³

    return BeamMaterialProperties(
        material_type=material_type,
        yield_strength=yield_strength,
        elastic_modulus=elastic_modulus,
        density=density,
        allowable_stress_factor=0.6,
    )


@st.composite
def beam_geometry_strategy(draw):
    """Generate valid beam geometry."""
    depth = draw(
        st.floats(min_value=6.0, max_value=36.0, allow_nan=False, allow_infinity=False)
    )
    width = draw(
        st.floats(min_value=4.0, max_value=18.0, allow_nan=False, allow_infinity=False)
    )
    return BeamGeometry(depth=depth, width=width)


@st.composite
def beam_loads_strategy(draw):
    """Generate valid beam loads."""
    uniform_load = draw(
        st.floats(
            min_value=100.0, max_value=5000.0, allow_nan=False, allow_infinity=False
        )
    )
    return BeamLoads(uniform_load=uniform_load)


# Strategies for column design
@st.composite
def column_material_strategy(draw):
    """Generate valid column material properties."""
    material_type = draw(st.sampled_from(list(ColumnMaterialType)))

    if material_type == ColumnMaterialType.STEEL:
        yield_strength = draw(
            st.floats(
                min_value=36000.0,
                max_value=60000.0,
                allow_nan=False,
                allow_infinity=False,
            )
        )
        elastic_modulus = 29000000.0
        density = 490.0
    else:  # CONCRETE
        yield_strength = draw(
            st.floats(
                min_value=3000.0,
                max_value=6000.0,
                allow_nan=False,
                allow_infinity=False,
            )
        )
        elastic_modulus = 3600000.0
        density = 150.0

    return ColumnMaterialProperties(
        material_type=material_type,
        yield_strength=yield_strength,
        elastic_modulus=elastic_modulus,
        density=density,
        allowable_stress_factor=0.6,
    )


@st.composite
def column_geometry_strategy(draw):
    """Generate valid column geometry."""
    use_circular = draw(st.booleans())

    if use_circular:
        diameter = draw(
            st.floats(
                min_value=8.0, max_value=36.0, allow_nan=False, allow_infinity=False
            )
        )
        return ColumnGeometry(diameter=diameter)
    else:
        depth = draw(
            st.floats(
                min_value=8.0, max_value=36.0, allow_nan=False, allow_infinity=False
            )
        )
        width = draw(
            st.floats(
                min_value=8.0, max_value=36.0, allow_nan=False, allow_infinity=False
            )
        )
        return ColumnGeometry(depth=depth, width=width)


@st.composite
def column_loads_strategy(draw):
    """Generate valid column loads."""
    axial_load = draw(
        st.floats(
            min_value=1000.0, max_value=100000.0, allow_nan=False, allow_infinity=False
        )
    )
    moment_x = draw(
        st.floats(
            min_value=0.0, max_value=50000.0, allow_nan=False, allow_infinity=False
        )
    )
    moment_y = draw(
        st.floats(
            min_value=0.0, max_value=50000.0, allow_nan=False, allow_infinity=False
        )
    )
    return ColumnLoads(axial_load=axial_load, moment_x=moment_x, moment_y=moment_y)


# Strategies for foundation design
@st.composite
def soil_properties_strategy(draw):
    """Generate valid soil properties."""
    bearing_capacity = draw(
        st.floats(
            min_value=1000.0, max_value=10000.0, allow_nan=False, allow_infinity=False
        )
    )
    unit_weight = draw(
        st.floats(
            min_value=100.0, max_value=140.0, allow_nan=False, allow_infinity=False
        )
    )
    friction_angle = draw(
        st.floats(min_value=20.0, max_value=40.0, allow_nan=False, allow_infinity=False)
    )
    cohesion = draw(
        st.floats(
            min_value=0.0, max_value=2000.0, allow_nan=False, allow_infinity=False
        )
    )
    return SoilProperties(
        bearing_capacity=bearing_capacity,
        unit_weight=unit_weight,
        friction_angle=friction_angle,
        cohesion=cohesion,
        elastic_modulus=5000.0,
    )


@st.composite
def foundation_geometry_strategy(draw):
    """Generate valid foundation geometry."""
    foundation_type = draw(
        st.sampled_from(
            [FoundationType.SPREAD_FOOTING, FoundationType.CONTINUOUS_FOOTING]
        )
    )

    use_circular = draw(st.booleans())

    if use_circular:
        diameter = draw(
            st.floats(
                min_value=3.0, max_value=15.0, allow_nan=False, allow_infinity=False
            )
        )
        return FoundationGeometry(
            foundation_type=foundation_type,
            diameter=diameter,
            depth=2.0,
            thickness=18.0,
        )
    else:
        length = draw(
            st.floats(
                min_value=3.0, max_value=15.0, allow_nan=False, allow_infinity=False
            )
        )
        width = draw(
            st.floats(
                min_value=3.0, max_value=15.0, allow_nan=False, allow_infinity=False
            )
        )
        return FoundationGeometry(
            foundation_type=foundation_type,
            length=length,
            width=width,
            depth=2.0,
            thickness=18.0,
        )


@st.composite
def foundation_loads_strategy(draw):
    """Generate valid foundation loads."""
    vertical_load = draw(
        st.floats(
            min_value=5000.0, max_value=200000.0, allow_nan=False, allow_infinity=False
        )
    )
    moment_x = draw(
        st.floats(
            min_value=0.0, max_value=50000.0, allow_nan=False, allow_infinity=False
        )
    )
    moment_y = draw(
        st.floats(
            min_value=0.0, max_value=50000.0, allow_nan=False, allow_infinity=False
        )
    )
    return FoundationLoads(
        vertical_load=vertical_load, moment_x=moment_x, moment_y=moment_y
    )


@pytest.mark.property
class TestStructuralDesignProperties:
    """Property-based tests for structural design validity."""

    def setup_method(self):
        """Set up test fixtures."""
        self.beam_designer = BeamDesigner()
        self.column_designer = ColumnDesigner()
        self.foundation_designer = FoundationDesigner()

    # Beam Design Properties
    @given(
        span=st.floats(
            min_value=10.0, max_value=50.0, allow_nan=False, allow_infinity=False
        ),
        loads=beam_loads_strategy(),
        material=beam_material_strategy(),
        geometry=beam_geometry_strategy(),
    )
    @settings(max_examples=100, suppress_health_check=[hypothesis.HealthCheck.too_slow])
    def test_beam_stress_ratio_within_limits(self, span, loads, material, geometry):
        """
        Property: Adequate beam designs have stress ratios <= 1.0.

        When a beam is marked as adequate, its stress ratio
        (actual/allowable) must not exceed 1.0.
        """
        result = self.beam_designer.design_beam(
            span=span,
            loads=loads,
            material=material,
            support_type=BeamSupportType.SIMPLY_SUPPORTED,
            trial_geometry=geometry,
        )

        if result.is_adequate:
            assert (
                result.stress_ratio <= 1.0
            ), f"Adequate beam has stress ratio {result.stress_ratio} > 1.0"

    @given(
        span=st.floats(
            min_value=10.0, max_value=50.0, allow_nan=False, allow_infinity=False
        ),
        loads=beam_loads_strategy(),
        material=beam_material_strategy(),
        geometry=beam_geometry_strategy(),
    )
    @settings(max_examples=100, suppress_health_check=[hypothesis.HealthCheck.too_slow])
    def test_beam_deflection_ratio_within_limits(self, span, loads, material, geometry):
        """
        Property: Adequate beam designs have deflection ratios <= 1.0.

        When a beam is marked as adequate, its deflection ratio
        (actual/allowable) must not exceed 1.0.
        """
        result = self.beam_designer.design_beam(
            span=span,
            loads=loads,
            material=material,
            support_type=BeamSupportType.SIMPLY_SUPPORTED,
            trial_geometry=geometry,
        )

        if result.is_adequate:
            assert result.deflection_ratio <= 1.0, (
                f"Adequate beam has deflection ratio "
                f"{result.deflection_ratio} > 1.0"
            )

    @given(
        span=st.floats(
            min_value=10.0, max_value=50.0, allow_nan=False, allow_infinity=False
        ),
        loads=beam_loads_strategy(),
        material=beam_material_strategy(),
        geometry=beam_geometry_strategy(),
    )
    @settings(max_examples=100, suppress_health_check=[hypothesis.HealthCheck.too_slow])
    def test_beam_adequate_meets_all_criteria(self, span, loads, material, geometry):
        """
        Property: Adequate beams meet both stress and deflection limits.

        A beam marked as adequate must satisfy both strength
        (stress ratio <= 1.0) and serviceability (deflection <= L/240).
        """
        result = self.beam_designer.design_beam(
            span=span,
            loads=loads,
            material=material,
            support_type=BeamSupportType.SIMPLY_SUPPORTED,
            trial_geometry=geometry,
        )

        if result.is_adequate:
            # Check stress criterion
            assert result.stress_ratio <= 1.0, (
                f"Adequate beam fails stress check: " f"ratio {result.stress_ratio}"
            )
            # Check deflection criterion
            assert result.deflection_ratio <= 1.0, (
                f"Adequate beam fails deflection check: "
                f"ratio {result.deflection_ratio}"
            )
            # Check actual stress vs allowable
            assert result.max_stress <= result.allowable_stress, (
                f"Adequate beam stress {result.max_stress} exceeds "
                f"allowable {result.allowable_stress}"
            )
            # Check actual deflection vs allowable
            assert result.max_deflection <= result.allowable_deflection, (
                f"Adequate beam deflection {result.max_deflection} exceeds "
                f"allowable {result.allowable_deflection}"
            )

    @given(
        span=st.floats(
            min_value=10.0, max_value=50.0, allow_nan=False, allow_infinity=False
        ),
        loads=beam_loads_strategy(),
        material=beam_material_strategy(),
    )
    @settings(max_examples=100, suppress_health_check=[hypothesis.HealthCheck.too_slow])
    def test_beam_moment_is_non_negative(self, span, loads, material):
        """
        Property: Beam moments are always non-negative.

        Maximum moment in a beam must be non-negative.
        """
        result = self.beam_designer.design_beam(
            span=span,
            loads=loads,
            material=material,
            support_type=BeamSupportType.SIMPLY_SUPPORTED,
        )

        assert (
            result.max_moment >= 0
        ), f"Beam moment must be non-negative, got {result.max_moment}"

    # Column Design Properties
    @given(
        length=st.floats(
            min_value=96.0, max_value=240.0, allow_nan=False, allow_infinity=False
        ),
        loads=column_loads_strategy(),
        material=column_material_strategy(),
        geometry=column_geometry_strategy(),
    )
    @settings(max_examples=100, suppress_health_check=[hypothesis.HealthCheck.too_slow])
    def test_column_combined_stress_ratio_within_limits(
        self, length, loads, material, geometry
    ):
        """
        Property: Adequate column designs have combined stress <= 1.0.

        When a column is marked as adequate, its combined stress ratio
        (P/Pn + Mx/Mnx + My/Mny) must not exceed 1.0.
        """
        result = self.column_designer.design_column(
            length=length,
            loads=loads,
            material=material,
            geometry=geometry,
            end_condition=EndCondition.PINNED_PINNED,
        )

        if result.is_adequate:
            assert result.combined_stress_ratio <= 1.0, (
                f"Adequate column has combined stress ratio "
                f"{result.combined_stress_ratio} > 1.0"
            )

    @given(
        length=st.floats(
            min_value=96.0, max_value=240.0, allow_nan=False, allow_infinity=False
        ),
        loads=column_loads_strategy(),
        material=column_material_strategy(),
        geometry=column_geometry_strategy(),
    )
    @settings(max_examples=100, suppress_health_check=[hypothesis.HealthCheck.too_slow])
    def test_column_axial_load_within_capacity(self, length, loads, material, geometry):
        """
        Property: Adequate columns have axial load within capacity.

        When a column is marked as adequate, the applied axial load
        must not exceed the buckling capacity.
        """
        result = self.column_designer.design_column(
            length=length,
            loads=loads,
            material=material,
            geometry=geometry,
            end_condition=EndCondition.PINNED_PINNED,
        )

        if result.is_adequate:
            assert loads.axial_load <= result.buckling_capacity, (
                f"Adequate column axial load {loads.axial_load} exceeds "
                f"buckling capacity {result.buckling_capacity}"
            )

    @given(
        length=st.floats(
            min_value=96.0, max_value=240.0, allow_nan=False, allow_infinity=False
        ),
        loads=column_loads_strategy(),
        material=column_material_strategy(),
        geometry=column_geometry_strategy(),
    )
    @settings(max_examples=100, suppress_health_check=[hypothesis.HealthCheck.too_slow])
    def test_column_capacities_are_positive(self, length, loads, material, geometry):
        """
        Property: Column capacities are always positive.

        Axial capacity and buckling capacity must be positive values.
        """
        result = self.column_designer.design_column(
            length=length,
            loads=loads,
            material=material,
            geometry=geometry,
            end_condition=EndCondition.PINNED_PINNED,
        )

        assert (
            result.axial_capacity > 0
        ), f"Axial capacity must be positive, got {result.axial_capacity}"
        assert result.buckling_capacity > 0, (
            f"Buckling capacity must be positive, " f"got {result.buckling_capacity}"
        )

    @given(
        length=st.floats(
            min_value=96.0, max_value=240.0, allow_nan=False, allow_infinity=False
        ),
        loads=column_loads_strategy(),
        material=column_material_strategy(),
        geometry=column_geometry_strategy(),
    )
    @settings(max_examples=100, suppress_health_check=[hypothesis.HealthCheck.too_slow])
    def test_column_buckling_less_than_yield(self, length, loads, material, geometry):
        """
        Property: Buckling capacity is less than or equal to yield.

        For slender columns, buckling capacity should be less than
        the material yield capacity.
        """
        result = self.column_designer.design_column(
            length=length,
            loads=loads,
            material=material,
            geometry=geometry,
            end_condition=EndCondition.PINNED_PINNED,
        )

        assert result.buckling_capacity <= result.axial_capacity, (
            f"Buckling capacity {result.buckling_capacity} exceeds "
            f"axial capacity {result.axial_capacity}"
        )

    # Foundation Design Properties
    @given(
        loads=foundation_loads_strategy(),
        soil=soil_properties_strategy(),
        geometry=foundation_geometry_strategy(),
    )
    @settings(max_examples=100, suppress_health_check=[hypothesis.HealthCheck.too_slow])
    def test_foundation_bearing_ratio_within_limits(self, loads, soil, geometry):
        """
        Property: Adequate foundations have bearing ratios <= 1.0.

        When a foundation is marked as adequate, its bearing ratio
        (actual/allowable) must not exceed 1.0.
        """
        result = self.foundation_designer.design_foundation(
            loads=loads,
            soil_properties=soil,
            geometry=geometry,
        )

        if result.is_adequate:
            assert result.bearing_ratio <= 1.0, (
                f"Adequate foundation has bearing ratio "
                f"{result.bearing_ratio} > 1.0"
            )

    @given(
        loads=foundation_loads_strategy(),
        soil=soil_properties_strategy(),
        geometry=foundation_geometry_strategy(),
    )
    @settings(max_examples=100, suppress_health_check=[hypothesis.HealthCheck.too_slow])
    def test_foundation_settlement_within_limits(self, loads, soil, geometry):
        """
        Property: Adequate foundations have settlement within limits.

        When a foundation is marked as adequate, its settlement
        must not exceed the allowable settlement (typically 1 inch).
        """
        result = self.foundation_designer.design_foundation(
            loads=loads,
            soil_properties=soil,
            geometry=geometry,
        )

        if result.is_adequate:
            assert result.settlement <= result.allowable_settlement, (
                f"Adequate foundation settlement {result.settlement} "
                f"exceeds allowable {result.allowable_settlement}"
            )

    @given(
        loads=foundation_loads_strategy(),
        soil=soil_properties_strategy(),
        geometry=foundation_geometry_strategy(),
    )
    @settings(max_examples=100, suppress_health_check=[hypothesis.HealthCheck.too_slow])
    def test_foundation_bearing_pressure_non_negative(self, loads, soil, geometry):
        """
        Property: Foundation bearing pressure is always non-negative.

        Bearing pressure on soil must be non-negative.
        """
        result = self.foundation_designer.design_foundation(
            loads=loads,
            soil_properties=soil,
            geometry=geometry,
        )

        assert result.bearing_pressure >= 0, (
            f"Bearing pressure must be non-negative, " f"got {result.bearing_pressure}"
        )

    @given(
        loads=foundation_loads_strategy(),
        soil=soil_properties_strategy(),
        geometry=foundation_geometry_strategy(),
    )
    @settings(max_examples=100, suppress_health_check=[hypothesis.HealthCheck.too_slow])
    def test_foundation_adequate_meets_all_criteria(self, loads, soil, geometry):
        """
        Property: Adequate foundations meet bearing and settlement.

        A foundation marked as adequate must satisfy both bearing
        capacity and settlement limits.
        """
        result = self.foundation_designer.design_foundation(
            loads=loads,
            soil_properties=soil,
            geometry=geometry,
        )

        if result.is_adequate:
            # Check bearing criterion
            assert result.bearing_ratio <= 1.0, (
                f"Adequate foundation fails bearing check: "
                f"ratio {result.bearing_ratio}"
            )
            # Check settlement criterion
            assert result.settlement <= result.allowable_settlement, (
                f"Adequate foundation fails settlement check: "
                f"{result.settlement} > {result.allowable_settlement}"
            )
            # Check bearing pressure vs capacity
            assert result.bearing_pressure <= result.allowable_bearing_capacity, (
                f"Adequate foundation bearing pressure "
                f"{result.bearing_pressure} exceeds allowable "
                f"{result.allowable_bearing_capacity}"
            )

    @given(
        loads=foundation_loads_strategy(),
        soil=soil_properties_strategy(),
        geometry=foundation_geometry_strategy(),
    )
    @settings(max_examples=100, suppress_health_check=[hypothesis.HealthCheck.too_slow])
    def test_foundation_reinforcement_non_negative(self, loads, soil, geometry):
        """
        Property: Foundation reinforcement area is non-negative.

        Required reinforcement area must be non-negative.
        """
        result = self.foundation_designer.design_foundation(
            loads=loads,
            soil_properties=soil,
            geometry=geometry,
        )

        assert result.reinforcement_area >= 0, (
            f"Reinforcement area must be non-negative, "
            f"got {result.reinforcement_area}"
        )

    # Cross-component properties
    @given(
        span=st.floats(
            min_value=10.0, max_value=50.0, allow_nan=False, allow_infinity=False
        ),
        uniform_load=st.floats(
            min_value=100.0, max_value=5000.0, allow_nan=False, allow_infinity=False
        ),
        material=beam_material_strategy(),
        geometry=beam_geometry_strategy(),
    )
    @settings(max_examples=100, suppress_health_check=[hypothesis.HealthCheck.too_slow])
    def test_beam_load_increases_stress_ratio(
        self, span, uniform_load, material, geometry
    ):
        """
        Property: Increasing load increases stress ratio.

        For a given beam geometry, increasing the load should
        increase the stress ratio.
        """
        loads_lower = BeamLoads(uniform_load=uniform_load)
        loads_higher = BeamLoads(uniform_load=uniform_load * 1.5)

        result_lower = self.beam_designer.design_beam(
            span=span,
            loads=loads_lower,
            material=material,
            support_type=BeamSupportType.SIMPLY_SUPPORTED,
            trial_geometry=geometry,
        )

        result_higher = self.beam_designer.design_beam(
            span=span,
            loads=loads_higher,
            material=material,
            support_type=BeamSupportType.SIMPLY_SUPPORTED,
            trial_geometry=geometry,
        )

        assert result_higher.stress_ratio > result_lower.stress_ratio, (
            f"Higher load should increase stress ratio: "
            f"{result_higher.stress_ratio} <= {result_lower.stress_ratio}"
        )

    @given(
        length=st.floats(
            min_value=96.0, max_value=240.0, allow_nan=False, allow_infinity=False
        ),
        axial_load=st.floats(
            min_value=1000.0, max_value=100000.0, allow_nan=False, allow_infinity=False
        ),
        material=column_material_strategy(),
        geometry=column_geometry_strategy(),
    )
    @settings(max_examples=100, suppress_health_check=[hypothesis.HealthCheck.too_slow])
    def test_column_load_increases_stress_ratio(
        self, length, axial_load, material, geometry
    ):
        """
        Property: Increasing axial load increases stress ratio.

        For a given column geometry, increasing the axial load
        should increase the combined stress ratio.
        """
        loads_lower = ColumnLoads(axial_load=axial_load)
        loads_higher = ColumnLoads(axial_load=axial_load * 1.5)

        result_lower = self.column_designer.design_column(
            length=length,
            loads=loads_lower,
            material=material,
            geometry=geometry,
            end_condition=EndCondition.PINNED_PINNED,
        )

        result_higher = self.column_designer.design_column(
            length=length,
            loads=loads_higher,
            material=material,
            geometry=geometry,
            end_condition=EndCondition.PINNED_PINNED,
        )

        assert (
            result_higher.combined_stress_ratio > result_lower.combined_stress_ratio
        ), (
            f"Higher load should increase stress ratio: "
            f"{result_higher.combined_stress_ratio} <= "
            f"{result_lower.combined_stress_ratio}"
        )

    @given(
        vertical_load=st.floats(
            min_value=5000.0, max_value=200000.0, allow_nan=False, allow_infinity=False
        ),
        soil=soil_properties_strategy(),
        geometry=foundation_geometry_strategy(),
    )
    @settings(max_examples=100, suppress_health_check=[hypothesis.HealthCheck.too_slow])
    def test_foundation_load_increases_bearing_ratio(
        self, vertical_load, soil, geometry
    ):
        """
        Property: Increasing load increases bearing ratio.

        For a given foundation geometry, increasing the vertical
        load should increase the bearing ratio.
        """
        loads_lower = FoundationLoads(vertical_load=vertical_load)
        loads_higher = FoundationLoads(vertical_load=vertical_load * 1.5)

        result_lower = self.foundation_designer.design_foundation(
            loads=loads_lower,
            soil_properties=soil,
            geometry=geometry,
        )

        result_higher = self.foundation_designer.design_foundation(
            loads=loads_higher,
            soil_properties=soil,
            geometry=geometry,
        )

        assert result_higher.bearing_ratio > result_lower.bearing_ratio, (
            f"Higher load should increase bearing ratio: "
            f"{result_higher.bearing_ratio} <= "
            f"{result_lower.bearing_ratio}"
        )
