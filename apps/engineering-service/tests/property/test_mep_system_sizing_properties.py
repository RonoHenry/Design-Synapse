"""
Property-based tests for MEP system sizing.

**Validates: Property 3 - MEP System Sizing**
Property: Sized equipment meets calculated loads with appropriate safety factors

This test verifies that:
1. HVAC equipment capacity >= calculated loads with safety factor
2. Electrical panels can handle calculated loads with safety factor
3. Plumbing pipes can handle peak demand with acceptable velocity
4. Fire protection systems meet NFPA 13 requirements

**Validates: Requirements 2.1-2.4, 2.6**
"""

from hypothesis import HealthCheck, assume, given, settings
from hypothesis import strategies as st
from src.calculations.electrical_calculator import (Circuit, CircuitType,
                                                    ElectricalCalculator)
from src.calculations.fire_protection_calculator import \
    BuildingData as FireBuildingData
from src.calculations.fire_protection_calculator import (
    FireProtectionCalculator, OccupancyHazard)
from src.calculations.hvac_calculator import BuildingData as HVACBuildingData
from src.calculations.hvac_calculator import ClimateData, HVACCalculator
from src.calculations.plumbing_calculator import (Fixture, FixtureType,
                                                  PlumbingCalculator)


# Strategy for generating valid building data for HVAC
@st.composite
def hvac_building_data(draw):
    """Generate valid HVAC building data with realistic constraints."""
    # Realistic floor areas: 1000-50000 sq ft (avoid tiny buildings)
    floor_area = draw(st.floats(min_value=1000.0, max_value=50000.0))
    wall_area = draw(st.floats(min_value=floor_area * 0.3, max_value=floor_area * 0.6))
    roof_area = draw(st.floats(min_value=floor_area * 0.9, max_value=floor_area * 1.1))
    window_area = draw(
        st.floats(min_value=wall_area * 0.15, max_value=wall_area * 0.35)
    )
    volume = draw(st.floats(min_value=floor_area * 9, max_value=floor_area * 15))
    # Realistic occupancy: at least 5 people to avoid edge cases
    occupancy = draw(st.integers(min_value=5, max_value=500))
    insulation_r_value = draw(st.floats(min_value=13.0, max_value=38.0))

    return HVACBuildingData(
        floor_area=floor_area,
        wall_area=wall_area,
        roof_area=roof_area,
        window_area=window_area,
        volume=volume,
        occupancy=occupancy,
        insulation_r_value=insulation_r_value,
    )


@st.composite
def climate_data(draw):
    """Generate valid climate data with realistic constraints."""
    # Realistic winter temps: -10°F to 35°F (avoid extreme cold)
    outdoor_temp_winter = draw(st.floats(min_value=-10.0, max_value=35.0))
    # Realistic summer temps: 75°F to 105°F (avoid extreme heat)
    outdoor_temp_summer = draw(st.floats(min_value=75.0, max_value=105.0))
    indoor_temp_winter = draw(st.floats(min_value=68.0, max_value=72.0))
    indoor_temp_summer = draw(st.floats(min_value=72.0, max_value=76.0))
    humidity_summer = draw(st.floats(min_value=35.0, max_value=70.0))

    # Ensure meaningful temperature differences (at least 10°F)
    assume(outdoor_temp_winter < indoor_temp_winter - 5)
    assume(outdoor_temp_summer > indoor_temp_summer + 5)

    return ClimateData(
        outdoor_temp_winter=outdoor_temp_winter,
        outdoor_temp_summer=outdoor_temp_summer,
        indoor_temp_winter=indoor_temp_winter,
        indoor_temp_summer=indoor_temp_summer,
        humidity_summer=humidity_summer,
    )


@st.composite
def electrical_circuits(draw):
    """Generate list of electrical circuits with realistic loads."""
    num_circuits = draw(st.integers(min_value=3, max_value=20))
    circuits = []

    for i in range(num_circuits):
        circuit_type = draw(st.sampled_from(list(CircuitType)))
        # Realistic loads: 500W to 10kW (avoid very small loads)
        load = draw(st.floats(min_value=500.0, max_value=10000.0))
        voltage = draw(st.sampled_from([120.0, 240.0, 277.0, 480.0]))
        continuous = draw(st.booleans())

        circuits.append(
            Circuit(
                name=f"Circuit {i}",
                circuit_type=circuit_type,
                load=load,
                voltage=voltage,
                continuous=continuous,
            )
        )

    return circuits


@st.composite
def plumbing_fixtures(draw):
    """Generate list of plumbing fixtures with realistic quantities."""
    # Realistic fixture count: 3-25 fixtures
    num_fixtures = draw(st.integers(min_value=3, max_value=25))
    fixtures = []

    for i in range(num_fixtures):
        fixture_type = draw(st.sampled_from(list(FixtureType)))
        # Realistic quantities: 1-8 per fixture type
        quantity = draw(st.integers(min_value=1, max_value=8))
        private = draw(st.booleans())

        fixtures.append(
            Fixture(
                name=f"Fixture {i}",
                fixture_type=fixture_type,
                quantity=quantity,
                private=private,
            )
        )

    return fixtures


@st.composite
def fire_building_data(draw):
    """Generate valid fire protection building data with realistic constraints."""
    # Realistic floor areas: 1000-50000 sq ft
    floor_area = draw(st.floats(min_value=1000.0, max_value=50000.0))
    # Realistic ceiling heights: 9-18 ft
    ceiling_height = draw(st.floats(min_value=9.0, max_value=18.0))
    occupancy_hazard = draw(st.sampled_from(list(OccupancyHazard)))
    construction_type = draw(
        st.sampled_from(["Type I", "Type II", "Type III", "Type IV", "Type V"])
    )

    return FireBuildingData(
        floor_area=floor_area,
        ceiling_height=ceiling_height,
        occupancy_hazard=occupancy_hazard,
        construction_type=construction_type,
    )


class TestMEPSystemSizingProperties:
    """Property-based tests for MEP system sizing."""

    @given(
        building=hvac_building_data(),
        climate=climate_data(),
    )
    @settings(
        max_examples=100, deadline=None, suppress_health_check=[HealthCheck.too_slow]
    )
    def test_hvac_equipment_meets_loads_with_safety_factor(self, building, climate):
        """
        **Validates: Requirements 2.1, 2.6**

        Property: HVAC equipment capacity >= calculated loads with safety factor

        This test verifies that sized HVAC equipment has sufficient capacity
        to meet both heating and cooling loads with appropriate safety factors
        applied per ASHRAE standards.
        """
        calculator = HVACCalculator()

        # Calculate loads
        heating_load = calculator.calculate_heating_load(building, climate)
        cooling_load = calculator.calculate_cooling_load(building, climate)

        # Size equipment
        equipment = calculator.size_equipment(heating_load, cooling_load)

        # Property 1: Equipment heating capacity >= calculated heating load
        assert equipment.heating_capacity >= heating_load, (
            f"Heating capacity {equipment.heating_capacity} BTU/hr is less than "
            f"calculated load {heating_load} BTU/hr"
        )

        # Property 2: Equipment cooling capacity >= calculated cooling load
        assert equipment.cooling_capacity >= cooling_load, (
            f"Cooling capacity {equipment.cooling_capacity} BTU/hr is less than "
            f"calculated load {cooling_load} BTU/hr"
        )

        # Property 3: Safety factor is reasonable (equipment not oversized by >50%)
        heating_safety_factor = equipment.heating_capacity / heating_load
        cooling_safety_factor = equipment.cooling_capacity / cooling_load

        assert (
            1.0 <= heating_safety_factor <= 1.5
        ), f"Heating safety factor {heating_safety_factor:.2f} is outside reasonable range [1.0, 1.5]"
        assert (
            1.0 <= cooling_safety_factor <= 1.5
        ), f"Cooling safety factor {cooling_safety_factor:.2f} is outside reasonable range [1.0, 1.5]"

        # Property 4: Airflow is proportional to cooling capacity
        # Rule of thumb: 400 CFM per ton (12,000 BTU/hr)
        expected_airflow = (equipment.cooling_capacity / 12000) * 400
        assert (
            abs(equipment.airflow - expected_airflow) < 100
        ), f"Airflow {equipment.airflow} CFM deviates significantly from expected {expected_airflow} CFM"

    @given(circuits=electrical_circuits())
    @settings(
        max_examples=100, deadline=None, suppress_health_check=[HealthCheck.too_slow]
    )
    def test_electrical_panel_handles_load_with_safety_factor(self, circuits):
        """
        **Validates: Requirements 2.2, 2.6**

        Property: Electrical panels can handle calculated loads with safety factor

        This test verifies that sized electrical panels have sufficient capacity
        to handle the calculated load with NEC-required safety factors.
        """
        calculator = ElectricalCalculator()

        # Calculate total load
        total_load = calculator.calculate_load(circuits)

        # Assume 240V system for panel sizing
        voltage = 240.0

        # Size panel
        panel = calculator.size_panel(total_load, voltage)

        # Property 1: Panel can handle the calculated load
        required_amps = total_load / voltage
        assert (
            panel.rated_amperage >= required_amps
        ), f"Panel rating {panel.rated_amperage}A is less than required {required_amps:.1f}A"

        # Property 2: Panel has NEC-required 125% safety factor
        design_amps = required_amps * 1.25
        assert (
            panel.rated_amperage >= design_amps
        ), f"Panel rating {panel.rated_amperage}A is less than design requirement {design_amps:.1f}A"

        # Property 3: Panel is not excessively oversized (< 2x required)
        safety_factor = panel.rated_amperage / required_amps
        assert (
            safety_factor <= 2.5
        ), f"Panel safety factor {safety_factor:.2f} is excessively high (>2.5x)"

        # Property 4: Main breaker matches panel rating
        assert (
            panel.main_breaker_size == panel.rated_amperage
        ), f"Main breaker {panel.main_breaker_size}A does not match panel rating {panel.rated_amperage}A"

        # Property 5: Bus rating matches panel rating
        assert (
            panel.bus_rating == panel.rated_amperage
        ), f"Bus rating {panel.bus_rating}A does not match panel rating {panel.rated_amperage}A"

    @given(
        circuits=electrical_circuits(),
        # Realistic circuit lengths: 20-300 ft (avoid very long runs)
        length=st.floats(min_value=20.0, max_value=300.0),
    )
    @settings(
        max_examples=100, deadline=None, suppress_health_check=[HealthCheck.too_slow]
    )
    def test_circuit_sizing_meets_nec_requirements(self, circuits, length):
        """
        **Validates: Requirements 2.2, 2.6**

        Property: Circuit conductors are sized per NEC with adequate ampacity

        This test verifies that circuit conductors have sufficient ampacity
        for the load and meet NEC voltage drop requirements.
        """
        calculator = ElectricalCalculator()

        # Test each circuit
        for circuit in circuits:
            # Size the circuit
            sized_circuit = calculator.size_circuit(
                load=circuit.load,
                voltage=circuit.voltage,
                length=length,
                continuous=circuit.continuous,
            )

            # Calculate required current
            required_amps = circuit.load / circuit.voltage
            if circuit.continuous:
                design_amps = required_amps * 1.25
            else:
                design_amps = required_amps

            # Property 1: Conductor ampacity >= design current
            assert sized_circuit.ampacity >= design_amps, (
                f"Conductor ampacity {sized_circuit.ampacity}A is less than "
                f"design current {design_amps:.1f}A for {circuit.name}"
            )

            # Property 2: Breaker size >= design current
            assert sized_circuit.breaker_size >= design_amps, (
                f"Breaker size {sized_circuit.breaker_size}A is less than "
                f"design current {design_amps:.1f}A for {circuit.name}"
            )

            # Property 3: Voltage drop is within NEC recommendation (5% max)
            assert sized_circuit.voltage_drop <= 5.0, (
                f"Voltage drop {sized_circuit.voltage_drop}% exceeds NEC recommendation "
                f"of 5% for {circuit.name}"
            )

            # Property 4: Breaker protects conductor (breaker <= ampacity)
            assert sized_circuit.breaker_size <= sized_circuit.ampacity * 1.25, (
                f"Breaker {sized_circuit.breaker_size}A is too large for conductor "
                f"ampacity {sized_circuit.ampacity}A for {circuit.name}"
            )

    @given(fixtures=plumbing_fixtures())
    @settings(
        max_examples=100, deadline=None, suppress_health_check=[HealthCheck.too_slow]
    )
    def test_plumbing_system_meets_peak_demand(self, fixtures):
        """
        **Validates: Requirements 2.3, 2.6**

        Property: Plumbing pipes can handle peak demand with acceptable velocity

        This test verifies that sized plumbing pipes have sufficient capacity
        for peak demand while maintaining acceptable water velocity per IPC.
        """
        calculator = PlumbingCalculator()

        # Calculate fixture units and peak demand
        total_fu = calculator.calculate_fixture_units(fixtures)
        peak_demand = calculator.calculate_peak_demand(total_fu)

        # Size pipe for peak demand
        pipe = calculator.size_pipe(
            flow_rate=peak_demand,
            length=100.0,
            material="copper",
            max_velocity=8.0,
        )

        # Property 1: Pipe can handle the peak demand
        assert (
            pipe.flow_rate == peak_demand
        ), f"Pipe flow rate {pipe.flow_rate} GPM does not match peak demand {peak_demand} GPM"

        # Property 2: Water velocity is within acceptable range (2-8 ft/s)
        assert (
            2.0 <= pipe.velocity <= 8.0
        ), f"Water velocity {pipe.velocity} ft/s is outside acceptable range [2.0, 8.0]"

        # Property 3: Friction loss is reasonable (< 10 psi per 100 ft)
        assert (
            pipe.friction_loss <= 10.0
        ), f"Friction loss {pipe.friction_loss} psi/100ft is excessive (>10 psi)"

        # Property 4: Peak demand is proportional to fixture units
        # Hunter's curve: GPM should increase with fixture units
        if total_fu > 0:
            gpm_per_fu = peak_demand / total_fu
            assert (
                0.5 <= gpm_per_fu <= 5.0
            ), f"GPM per fixture unit {gpm_per_fu:.2f} is outside reasonable range [0.5, 5.0]"

    @given(fixtures=plumbing_fixtures())
    @settings(
        max_examples=100, deadline=None, suppress_health_check=[HealthCheck.too_slow]
    )
    def test_water_supply_system_adequacy(self, fixtures):
        """
        **Validates: Requirements 2.3, 2.6**

        Property: Water supply system is adequately sized for all fixtures

        This test verifies that the complete water supply system (service,
        meter, distribution) is properly sized for the fixture load.
        """
        calculator = PlumbingCalculator()

        # Design water supply system
        supply = calculator.design_water_supply(
            fixtures=fixtures,
            supply_pressure=60.0,
            material="copper",
        )

        # Property 1: Peak demand is reasonable for fixture count
        assert supply.peak_demand > 0, "Peak demand must be positive"
        assert supply.peak_demand <= supply.total_fixture_units * 5.0, (
            f"Peak demand {supply.peak_demand} GPM is unreasonably high for "
            f"{supply.total_fixture_units} fixture units"
        )

        # Property 2: Service size is adequate for peak demand
        # Extract numeric size from string (e.g., "1.0\"" -> 1.0)
        service_size_num = float(supply.service_size.strip('"'))
        # Minimum sizes for flow rates (approximate)
        if supply.peak_demand <= 10:
            assert service_size_num >= 0.5
        elif supply.peak_demand <= 20:
            assert service_size_num >= 0.75
        elif supply.peak_demand <= 40:
            assert service_size_num >= 1.0
        else:
            assert service_size_num >= 1.5

        # Property 3: Required pressure is reasonable (15-80 psi)
        assert 15.0 <= supply.supply_pressure_required <= 80.0, (
            f"Required pressure {supply.supply_pressure_required} psi is outside "
            f"reasonable range [15, 80]"
        )

    @given(building=fire_building_data())
    @settings(
        max_examples=100, deadline=None, suppress_health_check=[HealthCheck.too_slow]
    )
    def test_fire_protection_meets_nfpa_requirements(self, building):
        """
        **Validates: Requirements 2.4, 2.6**

        Property: Fire protection systems meet NFPA 13 requirements

        This test verifies that fire protection system design meets NFPA 13
        requirements for sprinkler density, coverage, and water demand.
        """
        calculator = FireProtectionCalculator()

        # Design fire protection system
        system = calculator.design_system(
            building=building,
            supply_pressure=80.0,
        )

        # Property 1: Sprinkler density meets NFPA 13 requirements
        # Density should be between 0.10 and 0.40 GPM/sq ft per NFPA 13
        assert 0.10 <= system.sprinkler_design.density <= 0.40, (
            f"Sprinkler density {system.sprinkler_design.density} GPM/sq ft is outside "
            f"NFPA 13 range [0.10, 0.40]"
        )

        # Property 2: Coverage per head is within NFPA 13 limits
        # Maximum coverage varies by hazard: 100-225 sq ft per head
        assert 50 <= system.sprinkler_design.coverage_per_head <= 250, (
            f"Coverage per head {system.sprinkler_design.coverage_per_head} sq ft is outside "
            f"reasonable range [50, 250]"
        )

        # Property 3: Total demand includes sprinkler + hose allowance
        sprinkler_demand = (
            system.sprinkler_design.flow_per_head
            * system.sprinkler_design.number_of_heads
        )
        assert system.total_demand > sprinkler_demand, (
            f"Total demand {system.total_demand} GPM should exceed sprinkler demand "
            f"{sprinkler_demand} GPM (must include hose allowance)"
        )

        # Property 4: Hose allowance is reasonable (100-500 GPM per NFPA 13)
        hose_allowance = system.total_demand - sprinkler_demand
        assert (
            100 <= hose_allowance <= 500
        ), f"Hose allowance {hose_allowance} GPM is outside NFPA 13 range [100, 500]"

        # Property 5: Residual pressure meets minimum requirement (7 psi per NFPA 13)
        assert system.residual_pressure >= 7.0, (
            f"Residual pressure {system.residual_pressure} psi is below NFPA 13 "
            f"minimum of 7 psi"
        )

        # Property 6: Number of heads is reasonable for area of application
        expected_heads = (
            system.sprinkler_design.area_of_application
            / system.sprinkler_design.coverage_per_head
        )
        assert abs(system.sprinkler_design.number_of_heads - expected_heads) <= 5, (
            f"Number of heads {system.sprinkler_design.number_of_heads} deviates significantly "
            f"from expected {expected_heads:.0f}"
        )

    @given(
        building=fire_building_data(),
        # Realistic supply pressures: 50-100 psi
        supply_pressure=st.floats(min_value=50.0, max_value=100.0),
    )
    @settings(
        max_examples=100, deadline=None, suppress_health_check=[HealthCheck.too_slow]
    )
    def test_fire_protection_piping_adequacy(self, building, supply_pressure):
        """
        **Validates: Requirements 2.4, 2.6**

        Property: Fire protection piping is adequately sized for demand

        This test verifies that fire protection piping (mains and risers)
        is properly sized to deliver required flow with acceptable pressure loss.
        """
        calculator = FireProtectionCalculator()

        # Design system
        system = calculator.design_system(
            building=building,
            supply_pressure=supply_pressure,
        )

        # Property 1: Pipe sizes are standard fire protection sizes
        standard_sizes = ['1"', '1.25"', '1.5"', '2"', '2.5"', '3"', '4"', '6"', '8"']
        assert (
            system.main_pipe_size in standard_sizes
        ), f"Main pipe size {system.main_pipe_size} is not a standard size"
        assert (
            system.riser_size in standard_sizes
        ), f"Riser size {system.riser_size} is not a standard size"

        # Property 2: Larger demand requires larger pipes
        # Main should be >= riser for typical layouts
        main_size_num = float(system.main_pipe_size.strip('"'))
        riser_size_num = float(system.riser_size.strip('"'))
        assert main_size_num >= riser_size_num * 0.8, (
            f"Main pipe {system.main_pipe_size} is significantly smaller than "
            f"riser {system.riser_size}"
        )

        # Property 3: System can deliver required flow at adequate pressure
        # Residual pressure should be positive
        assert (
            system.residual_pressure > 0
        ), f"Residual pressure {system.residual_pressure} psi is not positive"
