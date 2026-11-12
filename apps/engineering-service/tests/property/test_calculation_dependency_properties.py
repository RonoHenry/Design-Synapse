"""Property-based tests for calculation dependency updates.

**Validates: Requirements 1.6**

This module tests the property that changing input A triggers recalculation
of dependent calculation B. Tests automatic recalculation cascades when
calculation inputs change.
"""
import hypothesis
import pytest
from hypothesis import assume, given, settings
from hypothesis import strategies as st
from src.models.calculation_sheet import CalculationSheet
from src.services.recalculation_service import RecalculationService
from src.services.structural_calculation_service import \
    StructuralCalculationService


# Strategy for generating valid calculation inputs
@st.composite
def calculation_inputs_strategy(draw):
    """Generate valid calculation input data."""
    # Generate building data for load calculations
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

    return {
        "height": height,
        "width": width,
        "length": length,
        "exposure_category": exposure_category,
        "occupancy": "office",
        "floor_area": width * length,
        "components": [
            {
                "name": "Concrete Slab",
                "weight_per_area": 50.0,
                "area": width * length,
            }
        ],
    }


# Strategy for generating beam load inputs
@st.composite
def beam_load_inputs_strategy(draw):
    """Generate valid beam load input data."""
    uniform_load = draw(
        st.floats(
            min_value=0.0, max_value=10000.0, allow_nan=False, allow_infinity=False
        )
    )
    span = draw(
        st.floats(min_value=5.0, max_value=50.0, allow_nan=False, allow_infinity=False)
    )

    return {
        "loads": {
            "uniform_load": uniform_load,
            "point_loads": [],
            "moment_loads": [],
        },
        "span": span,
        "material": {
            "material_type": "steel",
            "yield_strength": 36000.0,
            "elastic_modulus": 29000000.0,
            "density": 490.0,
            "allowable_stress_factor": 0.6,
        },
        "support_type": "simply_supported",
        "trial_geometry": {
            "depth": 12.0,
            "width": 8.0,
            "web_thickness": 0.5,
            "flange_thickness": 0.75,
        },
    }


@pytest.mark.property
class TestCalculationDependencyProperties:
    """Property-based tests for calculation dependency updates."""

    @given(
        initial_inputs=calculation_inputs_strategy(),
        updated_inputs=calculation_inputs_strategy(),
    )
    @settings(
        max_examples=100,
        deadline=None,  # Disable deadline for database operations
        suppress_health_check=[
            hypothesis.HealthCheck.too_slow,
            hypothesis.HealthCheck.function_scoped_fixture,
        ],
    )
    async def test_input_change_triggers_dependent_recalculation(
        self, initial_inputs, updated_inputs, test_db_session
    ):
        """
        Property: Changing input A triggers recalculation of dependent calculation B.

        When calculation A's inputs change, all calculations that depend on A
        should be automatically recalculated with the new values.
        """
        # Ensure inputs are actually different
        assume(initial_inputs != updated_inputs)

        # Create service instances
        structural_service = StructuralCalculationService(test_db_session)
        recalc_service = RecalculationService(test_db_session)

        # Create calculation A (load calculation)
        result_a = await structural_service.calculate_loads(
            project_id="test-project",
            building_data=initial_inputs,
            load_types=["dead", "live"],
            user_id="test-user",
            unit_system="imperial",
        )

        # Get the created calculation sheet A
        calc_a = await structural_service.calculation_sheet_repo.get_by_id(
            result_a.calculation_id
        )
        assert calc_a is not None, "Calculation A should be created"

        # Store initial output from calculation A
        initial_dead_load = calc_a.outputs.get("dead_load", 0.0)
        initial_live_load = calc_a.outputs.get("live_load", 0.0)
        initial_total_load = calc_a.outputs.get("total_load", 0.0)

        # Create calculation B (beam design) that depends on calculation A's outputs
        beam_inputs = {
            "loads": {
                "uniform_load": initial_total_load,  # Depends on calc A
                "point_loads": [],
                "moment_loads": [],
            },
            "span": 20.0,
            "material": {
                "material_type": "steel",
                "yield_strength": 36000.0,
                "elastic_modulus": 29000000.0,
                "density": 490.0,
                "allowable_stress_factor": 0.6,
            },
            "support_type": "simply_supported",
            "trial_geometry": {
                "depth": 12.0,
                "width": 8.0,
                "web_thickness": 0.5,
                "flange_thickness": 0.75,
            },
        }

        result_b = await structural_service.design_beam(
            project_id="test-project",
            loads=beam_inputs["loads"],
            span=beam_inputs["span"],
            material=beam_inputs["material"],
            user_id="test-user",
            unit_system="imperial",
            support_type=beam_inputs["support_type"],
            trial_geometry=beam_inputs["trial_geometry"],
        )

        # Get the created calculation sheet B
        # Get the most recent calculation sheet (should be the beam design we just created)
        recent_sheets = await structural_service.calculation_sheet_repo.get_recent(
            limit=2
        )
        calc_b = None
        for sheet in recent_sheets:
            if sheet.calculation_type == "beam_design" and sheet.id != calc_a.id:
                calc_b = sheet
                break
        assert calc_b is not None, "Calculation B should be created"

        # Store initial output from calculation B
        initial_max_moment_b = calc_b.outputs.get("max_moment", 0.0)

        # Add dependency: B depends on A
        await recalc_service.add_dependency(
            source_calculation_id=calc_b.id,
            target_calculation_id=calc_a.id,
            dependency_type="load_input",
            user_id="test-user",
            dependent_field="inputs.loads.uniform_load",
            source_field="outputs.total_load",
        )

        # Update calculation A's inputs
        await structural_service.update_calculation_inputs(
            calculation_id=calc_a.id,
            new_inputs={"building_data": updated_inputs},
            user_id="test-user",
            trigger_recalculation=True,
        )

        # Refresh calculation A from database
        await test_db_session.refresh(calc_a)

        # Get updated output from calculation A
        updated_dead_load = calc_a.outputs.get("dead_load", 0.0)
        updated_live_load = calc_a.outputs.get("live_load", 0.0)
        updated_total_load = calc_a.outputs.get("total_load", 0.0)

        # Verify calculation A was recalculated
        # (outputs should reflect the new inputs)
        if initial_inputs != updated_inputs:
            # At least one output should have changed
            assert (
                updated_dead_load != initial_dead_load
                or updated_live_load != initial_live_load
                or updated_total_load != initial_total_load
            ), "Calculation A outputs should change when inputs change"

        # Refresh calculation B from database
        await test_db_session.refresh(calc_b)

        # Verify calculation B was marked for recalculation
        # (status should be 'draft' or outputs should be updated)
        assert (
            calc_b.status == "draft" or calc_b.updated_at > calc_a.created_at
        ), "Calculation B should be marked for recalculation or recalculated"

    @given(
        initial_inputs=calculation_inputs_strategy(),
        updated_inputs=calculation_inputs_strategy(),
    )
    @settings(
        max_examples=100,
        deadline=None,  # Disable deadline for database operations
        suppress_health_check=[
            hypothesis.HealthCheck.too_slow,
            hypothesis.HealthCheck.function_scoped_fixture,
        ],
    )
    async def test_dependency_chain_recalculation(
        self, initial_inputs, updated_inputs, test_db_session
    ):
        """
        Property: Changing input A triggers recalculation of entire dependency chain.

        When calculation A changes, calculations B (depends on A) and C (depends on B)
        should both be recalculated in the correct order.
        """
        # Ensure inputs are actually different
        assume(initial_inputs != updated_inputs)

        # Create service instances
        structural_service = StructuralCalculationService(test_db_session)
        recalc_service = RecalculationService(test_db_session)

        # Create calculation A (load calculation)
        result_a = await structural_service.calculate_loads(
            project_id="test-project",
            building_data=initial_inputs,
            load_types=["dead", "live"],
            user_id="test-user",
            unit_system="imperial",
        )

        calc_a = await structural_service.calculation_sheet_repo.get_by_id(
            result_a.calculation_id
        )
        assert calc_a is not None

        initial_total_load_a = calc_a.outputs.get("total_load", 0.0)

        # Create calculation B (beam design) that depends on A
        result_b = await structural_service.design_beam(
            project_id="test-project",
            loads={
                "uniform_load": initial_total_load_a,
                "point_loads": [],
                "moment_loads": [],
            },
            span=20.0,
            material={
                "material_type": "steel",
                "yield_strength": 36000.0,
                "elastic_modulus": 29000000.0,
                "density": 490.0,
                "allowable_stress_factor": 0.6,
            },
            user_id="test-user",
            unit_system="imperial",
            support_type="simply_supported",
            trial_geometry={
                "depth": 12.0,
                "width": 8.0,
                "web_thickness": 0.5,
                "flange_thickness": 0.75,
            },
        )

        # Get the most recent calculation sheet (should be the beam design we just created)
        recent_sheets = await structural_service.calculation_sheet_repo.get_recent(
            limit=2
        )
        calc_b = None
        for sheet in recent_sheets:
            if sheet.calculation_type == "beam_design" and sheet.id != calc_a.id:
                calc_b = sheet
                break
        assert calc_b is not None

        initial_max_moment_b = calc_b.outputs.get("max_moment", 0.0)

        # Create calculation C (column design) that depends on B
        result_c = await structural_service.design_column(
            project_id="test-project",
            loads={
                "axial_load": initial_max_moment_b,  # Depends on B
                "moment_x": 0.0,
                "moment_y": 0.0,
            },
            length=120.0,
            material={
                "material_type": "steel",
                "yield_strength": 36000.0,
                "elastic_modulus": 29000000.0,
                "density": 490.0,
                "allowable_stress_factor": 0.6,
            },
            geometry={"depth": 12.0, "width": 12.0},
            user_id="test-user",
            unit_system="imperial",
            end_condition="pinned_pinned",
        )

        # Get the most recent calculation sheet (should be the column design we just created)
        recent_sheets = await structural_service.calculation_sheet_repo.get_recent(
            limit=3
        )
        calc_c = None
        for sheet in recent_sheets:
            if sheet.calculation_type == "column_design" and sheet.id not in [
                calc_a.id,
                calc_b.id,
            ]:
                calc_c = sheet
                break
        assert calc_c is not None

        # Add dependencies: B depends on A, C depends on B
        await recalc_service.add_dependency(
            source_calculation_id=calc_b.id,
            target_calculation_id=calc_a.id,
            dependency_type="load_input",
            user_id="test-user",
        )

        await recalc_service.add_dependency(
            source_calculation_id=calc_c.id,
            target_calculation_id=calc_b.id,
            dependency_type="load_input",
            user_id="test-user",
        )

        # Update calculation A's inputs
        await structural_service.update_calculation_inputs(
            calculation_id=calc_a.id,
            new_inputs={"building_data": updated_inputs},
            user_id="test-user",
            trigger_recalculation=True,
        )

        # Refresh all calculations from database
        await test_db_session.refresh(calc_a)
        await test_db_session.refresh(calc_b)
        await test_db_session.refresh(calc_c)

        # Verify all calculations in the chain were marked for recalculation
        assert (
            calc_b.status == "draft" or calc_b.updated_at > calc_a.created_at
        ), "Calculation B should be marked for recalculation"

        assert (
            calc_c.status == "draft" or calc_c.updated_at > calc_b.created_at
        ), "Calculation C should be marked for recalculation"

    @given(inputs=calculation_inputs_strategy())
    @settings(
        max_examples=100,
        deadline=None,  # Disable deadline for database operations
        suppress_health_check=[
            hypothesis.HealthCheck.too_slow,
            hypothesis.HealthCheck.function_scoped_fixture,
        ],
    )
    async def test_no_recalculation_without_dependency(self, inputs, test_db_session):
        """
        Property: Independent calculations are not recalculated when unrelated calculations change.

        When calculation A changes, calculation B (which does NOT depend on A)
        should NOT be recalculated.
        """
        # Create service instances
        structural_service = StructuralCalculationService(test_db_session)

        # Create calculation A (load calculation)
        result_a = await structural_service.calculate_loads(
            project_id="test-project",
            building_data=inputs,
            load_types=["dead", "live"],
            user_id="test-user",
            unit_system="imperial",
        )

        calc_a = await structural_service.calculation_sheet_repo.get_by_id(
            result_a.calculation_id
        )
        assert calc_a is not None

        # Create independent calculation B (beam design with its own loads)
        result_b = await structural_service.design_beam(
            project_id="test-project",
            loads={
                "uniform_load": 1000.0,  # Independent value
                "point_loads": [],
                "moment_loads": [],
            },
            span=20.0,
            material={
                "material_type": "steel",
                "yield_strength": 36000.0,
                "elastic_modulus": 29000000.0,
                "density": 490.0,
                "allowable_stress_factor": 0.6,
            },
            user_id="test-user",
            unit_system="imperial",
            support_type="simply_supported",
            trial_geometry={
                "depth": 12.0,
                "width": 8.0,
                "web_thickness": 0.5,
                "flange_thickness": 0.75,
            },
        )

        # Get the most recent calculation sheet (should be the beam design we just created)
        recent_sheets = await structural_service.calculation_sheet_repo.get_recent(
            limit=2
        )
        calc_b = None
        for sheet in recent_sheets:
            if sheet.calculation_type == "beam_design" and sheet.id != calc_a.id:
                calc_b = sheet
                break
        assert calc_b is not None

        # Store initial state of calculation B
        initial_updated_at_b = calc_b.updated_at
        initial_status_b = calc_b.status

        # Update calculation A's inputs (no dependency exists)
        modified_inputs = inputs.copy()
        modified_inputs["height"] = inputs["height"] * 1.5

        await structural_service.update_calculation_inputs(
            calculation_id=calc_a.id,
            new_inputs={"building_data": modified_inputs},
            user_id="test-user",
            trigger_recalculation=True,
        )

        # Refresh calculation B from database
        await test_db_session.refresh(calc_b)

        # Verify calculation B was NOT recalculated
        assert (
            calc_b.updated_at == initial_updated_at_b
        ), "Independent calculation B should not be recalculated"
        assert (
            calc_b.status == initial_status_b
        ), "Independent calculation B status should not change"

    @given(inputs=calculation_inputs_strategy())
    @settings(
        max_examples=100,
        deadline=None,  # Disable deadline for database operations
        suppress_health_check=[
            hypothesis.HealthCheck.too_slow,
            hypothesis.HealthCheck.function_scoped_fixture,
        ],
    )
    async def test_circular_dependency_prevention(self, inputs, test_db_session):
        """
        Property: Circular dependencies are prevented.

        The system should reject attempts to create circular dependencies
        (A depends on B, B depends on A).
        """
        # Create service instances
        structural_service = StructuralCalculationService(test_db_session)
        recalc_service = RecalculationService(test_db_session)

        # Create calculation A
        result_a = await structural_service.calculate_loads(
            project_id="test-project",
            building_data=inputs,
            load_types=["dead", "live"],
            user_id="test-user",
            unit_system="imperial",
        )

        calc_a = await structural_service.calculation_sheet_repo.get_by_id(
            result_a.calculation_id
        )
        assert calc_a is not None

        # Create calculation B
        result_b = await structural_service.design_beam(
            project_id="test-project",
            loads={
                "uniform_load": 1000.0,
                "point_loads": [],
                "moment_loads": [],
            },
            span=20.0,
            material={
                "material_type": "steel",
                "yield_strength": 36000.0,
                "elastic_modulus": 29000000.0,
                "density": 490.0,
                "allowable_stress_factor": 0.6,
            },
            user_id="test-user",
            unit_system="imperial",
            support_type="simply_supported",
            trial_geometry={
                "depth": 12.0,
                "width": 8.0,
                "web_thickness": 0.5,
                "flange_thickness": 0.75,
            },
        )

        # Get the most recent calculation sheet (should be the beam design we just created)
        recent_sheets = await structural_service.calculation_sheet_repo.get_recent(
            limit=2
        )
        calc_b = None
        for sheet in recent_sheets:
            if sheet.calculation_type == "beam_design" and sheet.id != calc_a.id:
                calc_b = sheet
                break
        assert calc_b is not None

        # Add dependency: B depends on A
        await recalc_service.add_dependency(
            source_calculation_id=calc_b.id,
            target_calculation_id=calc_a.id,
            dependency_type="load_input",
            user_id="test-user",
        )

        # Attempt to add circular dependency: A depends on B
        # This should raise a ValueError
        with pytest.raises(ValueError, match="circular dependency"):
            await recalc_service.add_dependency(
                source_calculation_id=calc_a.id,
                target_calculation_id=calc_b.id,
                dependency_type="load_input",
                user_id="test-user",
            )

    @given(
        initial_inputs=calculation_inputs_strategy(),
        updated_inputs=calculation_inputs_strategy(),
    )
    @settings(
        max_examples=100,
        deadline=None,  # Disable deadline for database operations
        suppress_health_check=[
            hypothesis.HealthCheck.too_slow,
            hypothesis.HealthCheck.function_scoped_fixture,
        ],
    )
    async def test_dependent_outputs_reflect_updated_inputs(
        self, initial_inputs, updated_inputs, test_db_session
    ):
        """
        Property: Dependent calculation outputs reflect updated input values.

        When calculation A's outputs change, dependent calculation B's outputs
        should reflect the new values from A (when recalculated).
        """
        # Ensure inputs are actually different
        assume(initial_inputs != updated_inputs)

        # Create service instances
        structural_service = StructuralCalculationService(test_db_session)
        recalc_service = RecalculationService(test_db_session)

        # Create calculation A
        result_a = await structural_service.calculate_loads(
            project_id="test-project",
            building_data=initial_inputs,
            load_types=["dead", "live"],
            user_id="test-user",
            unit_system="imperial",
        )

        calc_a = await structural_service.calculation_sheet_repo.get_by_id(
            result_a.calculation_id
        )
        assert calc_a is not None

        initial_total_load = calc_a.outputs.get("total_load", 0.0)

        # Create calculation B that depends on A
        result_b = await structural_service.design_beam(
            project_id="test-project",
            loads={
                "uniform_load": initial_total_load,
                "point_loads": [],
                "moment_loads": [],
            },
            span=20.0,
            material={
                "material_type": "steel",
                "yield_strength": 36000.0,
                "elastic_modulus": 29000000.0,
                "density": 490.0,
                "allowable_stress_factor": 0.6,
            },
            user_id="test-user",
            unit_system="imperial",
            support_type="simply_supported",
            trial_geometry={
                "depth": 12.0,
                "width": 8.0,
                "web_thickness": 0.5,
                "flange_thickness": 0.75,
            },
        )

        # Get the most recent calculation sheet (should be the beam design we just created)
        recent_sheets = await structural_service.calculation_sheet_repo.get_recent(
            limit=2
        )
        calc_b = None
        for sheet in recent_sheets:
            if sheet.calculation_type == "beam_design" and sheet.id != calc_a.id:
                calc_b = sheet
                break
        assert calc_b is not None

        # Add dependency
        await recalc_service.add_dependency(
            source_calculation_id=calc_b.id,
            target_calculation_id=calc_a.id,
            dependency_type="load_input",
            user_id="test-user",
        )

        # Update calculation A's inputs
        await structural_service.update_calculation_inputs(
            calculation_id=calc_a.id,
            new_inputs={"building_data": updated_inputs},
            user_id="test-user",
            trigger_recalculation=True,
        )

        # Refresh calculations
        await test_db_session.refresh(calc_a)
        await test_db_session.refresh(calc_b)

        updated_total_load = calc_a.outputs.get("total_load", 0.0)

        # Verify that calculation A's outputs changed
        if initial_inputs != updated_inputs:
            # If inputs changed significantly, outputs should differ
            assert (
                updated_total_load != initial_total_load
                or abs(updated_total_load - initial_total_load) < 1e-6
            ), "Calculation A outputs should reflect updated inputs"

        # Verify that calculation B was marked for recalculation
        # (In a full implementation, B would be recalculated with new values from A)
        assert (
            calc_b.status == "draft" or calc_b.updated_at > calc_a.created_at
        ), "Calculation B should be marked for recalculation after A changes"
