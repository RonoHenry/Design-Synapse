"""
Unit tests for PlumbingCalculator class.
Tests fixture unit calculations, pipe sizing, and water supply design per IPC.

**Validates: Requirements 2.3, 2.6, 7.1-7.6**
"""

import pytest
from src.calculations.plumbing_calculator import (Fixture, FixtureType,
                                                  PipeSize, PlumbingCalculator,
                                                  WaterSupplyResult)


class TestPlumbingCalculatorFixtureUnits:
    """Tests for fixture unit calculations per IPC."""

    def test_calculate_fixture_units_empty(self):
        """Test fixture unit calculation with no fixtures."""
        calculator = PlumbingCalculator()
        fixtures = []

        units = calculator.calculate_fixture_units(fixtures)

        assert units == 0.0

    def test_calculate_fixture_units_single_fixture(self):
        """Test fixture unit calculation with single fixture."""
        calculator = PlumbingCalculator()
        fixtures = [
            Fixture(
                name="Toilet",
                fixture_type=FixtureType.WATER_CLOSET,
                quantity=1,
                private=True,
            )
        ]

        units = calculator.calculate_fixture_units(fixtures)

        # Private water closet = 3.0 FU
        assert units == 3.0

    def test_calculate_fixture_units_private_vs_public(self):
        """Test fixture unit difference between private and public use."""
        calculator = PlumbingCalculator()

        private_fixtures = [
            Fixture("Private Toilet", FixtureType.WATER_CLOSET, 1, private=True)
        ]
        public_fixtures = [
            Fixture("Public Toilet", FixtureType.WATER_CLOSET, 1, private=False)
        ]

        private_units = calculator.calculate_fixture_units(private_fixtures)
        public_units = calculator.calculate_fixture_units(public_fixtures)

        # Public should have higher FU value
        assert public_units > private_units
        assert private_units == 3.0
        assert public_units == 6.0

    def test_calculate_fixture_units_multiple_fixtures(self):
        """Test fixture unit calculation with multiple fixtures."""
        calculator = PlumbingCalculator()
        fixtures = [
            Fixture(
                "Toilet", FixtureType.WATER_CLOSET, 2, private=True
            ),  # 2 × 3.0 = 6.0
            Fixture("Sink", FixtureType.LAVATORY, 2, private=True),  # 2 × 1.0 = 2.0
            Fixture("Shower", FixtureType.SHOWER, 1, private=True),  # 1 × 2.0 = 2.0
        ]

        units = calculator.calculate_fixture_units(fixtures)

        # Total: 6.0 + 2.0 + 2.0 = 10.0
        assert units == 10.0

    def test_calculate_fixture_units_residential_bathroom(self):
        """Test typical residential bathroom fixture units."""
        calculator = PlumbingCalculator()
        fixtures = [
            Fixture("Toilet", FixtureType.WATER_CLOSET, 1, private=True),
            Fixture("Sink", FixtureType.LAVATORY, 1, private=True),
            Fixture("Bathtub", FixtureType.BATHTUB, 1, private=True),
        ]

        units = calculator.calculate_fixture_units(fixtures)

        # 3.0 + 1.0 + 2.0 = 6.0 FU
        assert units == 6.0


class TestPlumbingCalculatorPeakDemand:
    """Tests for peak demand calculations using Hunter's Curve."""

    def test_calculate_peak_demand_zero_units(self):
        """Test peak demand with zero fixture units."""
        calculator = PlumbingCalculator()

        demand = calculator.calculate_peak_demand(0.0)

        assert demand == 0.0

    def test_calculate_peak_demand_small_system(self):
        """Test peak demand for small system."""
        calculator = PlumbingCalculator()

        demand = calculator.calculate_peak_demand(10.0)

        # Should be positive and reasonable
        assert demand > 0
        assert demand < 50  # Reasonable for 10 FU

    def test_calculate_peak_demand_large_system(self):
        """Test peak demand for large system."""
        calculator = PlumbingCalculator()

        demand = calculator.calculate_peak_demand(100.0)

        # Should be positive and scale appropriately
        assert demand > 0
        assert demand > calculator.calculate_peak_demand(10.0)

    def test_peak_demand_increases_with_fixture_units(self):
        """Test that peak demand increases with fixture units."""
        calculator = PlumbingCalculator()

        demand_10 = calculator.calculate_peak_demand(10.0)
        demand_20 = calculator.calculate_peak_demand(20.0)
        demand_50 = calculator.calculate_peak_demand(50.0)

        assert demand_20 > demand_10
        assert demand_50 > demand_20


class TestPlumbingCalculatorPipeSizing:
    """Tests for pipe sizing calculations."""

    def test_size_pipe_small_flow(self):
        """Test pipe sizing for small flow rate."""
        calculator = PlumbingCalculator()

        pipe = calculator.size_pipe(
            flow_rate=5.0, length=50.0, material="copper"  # 5 GPM
        )

        assert isinstance(pipe, PipeSize)
        assert pipe.nominal_size in ['0.5"', '0.75"']
        assert pipe.velocity > 0
        assert pipe.velocity <= 8.0  # Within max velocity

    def test_size_pipe_medium_flow(self):
        """Test pipe sizing for medium flow rate."""
        calculator = PlumbingCalculator()

        pipe = calculator.size_pipe(
            flow_rate=20.0, length=100.0, material="copper"  # 20 GPM
        )

        assert pipe.nominal_size in ['1.0"', '1.25"', '1.5"']
        assert pipe.velocity <= 8.0

    def test_size_pipe_large_flow(self):
        """Test pipe sizing for large flow rate."""
        calculator = PlumbingCalculator()

        pipe = calculator.size_pipe(
            flow_rate=100.0, length=200.0, material="copper"  # 100 GPM
        )

        # Should select larger pipe
        assert pipe.nominal_size in ['2.0"', '2.5"', '3.0"', '4.0"']
        assert pipe.velocity <= 8.0

    def test_pipe_sizing_different_materials(self):
        """Test pipe sizing with different materials."""
        calculator = PlumbingCalculator()

        copper_pipe = calculator.size_pipe(20.0, 100.0, "copper")
        pex_pipe = calculator.size_pipe(20.0, 100.0, "pex")

        # Both should work, may have different friction losses
        assert copper_pipe.nominal_size is not None
        assert pex_pipe.nominal_size is not None

    def test_pipe_friction_loss_calculation(self):
        """Test that friction loss is calculated."""
        calculator = PlumbingCalculator()

        pipe = calculator.size_pipe(10.0, 100.0, "copper")

        # Friction loss should be positive
        assert pipe.friction_loss > 0
        # Should be reasonable (typically < 10 psi per 100 ft)
        assert pipe.friction_loss < 20.0


class TestPlumbingCalculatorWaterSupply:
    """Tests for complete water supply system design."""

    def test_design_water_supply_small_residential(self):
        """Test water supply design for small residential."""
        calculator = PlumbingCalculator()
        fixtures = [
            Fixture("Toilet", FixtureType.WATER_CLOSET, 2, private=True),
            Fixture("Sink", FixtureType.LAVATORY, 2, private=True),
            Fixture("Shower", FixtureType.SHOWER, 1, private=True),
            Fixture("Kitchen Sink", FixtureType.KITCHEN_SINK, 1, private=True),
        ]

        result = calculator.design_water_supply(fixtures, supply_pressure=60.0)

        assert isinstance(result, WaterSupplyResult)
        assert result.total_fixture_units > 0
        assert result.peak_demand > 0
        assert result.service_size is not None
        assert result.meter_size is not None

    def test_design_water_supply_large_commercial(self):
        """Test water supply design for large commercial."""
        calculator = PlumbingCalculator()
        fixtures = [
            Fixture("Toilets", FixtureType.WATER_CLOSET, 20, private=False),
            Fixture("Sinks", FixtureType.LAVATORY, 15, private=False),
            Fixture("Urinals", FixtureType.URINAL, 10, private=False),
        ]

        result = calculator.design_water_supply(fixtures, supply_pressure=80.0)

        # Should have larger service size
        assert result.total_fixture_units > 50
        assert result.peak_demand > 50
        assert result.service_size is not None

    def test_water_supply_pressure_requirements(self):
        """Test that required pressure is calculated."""
        calculator = PlumbingCalculator()
        fixtures = [
            Fixture("Toilet", FixtureType.WATER_CLOSET, 1, private=True),
        ]

        result = calculator.design_water_supply(fixtures)

        # Should calculate required pressure
        assert result.supply_pressure_required > 0
        # Should be reasonable (typically 20-40 psi minimum)
        assert result.supply_pressure_required < 100.0


class TestPlumbingCalculatorIntegration:
    """Integration tests for complete plumbing calculations."""

    def test_complete_plumbing_design_workflow(self):
        """Test complete plumbing design workflow."""
        calculator = PlumbingCalculator()

        # Define fixtures for a house
        fixtures = [
            Fixture("Master Bath Toilet", FixtureType.WATER_CLOSET, 1, private=True),
            Fixture("Master Bath Sink", FixtureType.LAVATORY, 2, private=True),
            Fixture("Master Bath Shower", FixtureType.SHOWER, 1, private=True),
            Fixture("Guest Bath Toilet", FixtureType.WATER_CLOSET, 1, private=True),
            Fixture("Guest Bath Sink", FixtureType.LAVATORY, 1, private=True),
            Fixture("Guest Bath Tub", FixtureType.BATHTUB, 1, private=True),
            Fixture("Kitchen Sink", FixtureType.KITCHEN_SINK, 1, private=True),
            Fixture("Dishwasher", FixtureType.DISHWASHER, 1, private=True),
            Fixture("Laundry", FixtureType.LAUNDRY, 1, private=True),
        ]

        # Calculate fixture units
        total_fu = calculator.calculate_fixture_units(fixtures)
        assert total_fu > 0

        # Calculate peak demand
        peak_demand = calculator.calculate_peak_demand(total_fu)
        assert peak_demand > 0

        # Size main supply pipe
        main_pipe = calculator.size_pipe(peak_demand, 100.0, "copper")
        assert main_pipe.nominal_size is not None

        # Design complete system
        result = calculator.design_water_supply(fixtures, 60.0, "copper")
        assert result.service_size is not None
        assert result.meter_size is not None


class TestPlumbingCalculatorEdgeCases:
    """Tests for edge cases and error conditions."""

    def test_negative_flow_rate(self):
        """Test handling of negative flow rate."""
        calculator = PlumbingCalculator()

        # Should handle gracefully
        pipe = calculator.size_pipe(-10.0, 100.0, "copper")
        # Implementation should handle this appropriately

    def test_zero_length_pipe(self):
        """Test pipe sizing with zero length."""
        calculator = PlumbingCalculator()

        pipe = calculator.size_pipe(10.0, 0.0, "copper")
        # Should still return valid pipe size
        assert pipe.nominal_size is not None

    def test_unknown_material(self):
        """Test pipe sizing with unknown material."""
        calculator = PlumbingCalculator()

        pipe = calculator.size_pipe(10.0, 100.0, "unknown_material")
        # Should use default C factor
        assert pipe.nominal_size is not None
