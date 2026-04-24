"""
Unit tests for FireProtectionCalculator class.
Tests sprinkler system design per NFPA 13 standards.

**Validates: Requirements 2.4, 2.6, 7.1-7.6**
"""

import pytest
from src.calculations.fire_protection_calculator import (
    BuildingData, FireProtectionCalculator, FireProtectionResult,
    OccupancyHazard, SprinklerDesign, SprinklerType)


class TestFireProtectionCalculatorSprinklerDemand:
    """Tests for sprinkler demand calculations per NFPA 13."""

    def test_calculate_sprinkler_demand_light_hazard(self):
        """Test sprinkler demand for light hazard occupancy."""
        calculator = FireProtectionCalculator()
        building = BuildingData(
            floor_area=10000.0,
            ceiling_height=10.0,
            occupancy_hazard=OccupancyHazard.LIGHT_HAZARD,
            construction_type="Type II",
        )

        design = calculator.calculate_sprinkler_demand(building)

        assert isinstance(design, SprinklerDesign)
        assert design.density == 0.10  # GPM/sq ft
        assert design.area_of_application == 1500  # sq ft
        assert design.number_of_heads > 0
        assert design.flow_per_head > 0

    def test_calculate_sprinkler_demand_ordinary_hazard_1(self):
        """Test sprinkler demand for ordinary hazard 1."""
        calculator = FireProtectionCalculator()
        building = BuildingData(
            floor_area=20000.0,
            ceiling_height=12.0,
            occupancy_hazard=OccupancyHazard.ORDINARY_HAZARD_1,
            construction_type="Type II",
        )

        design = calculator.calculate_sprinkler_demand(building)

        assert design.density == 0.15
        assert design.area_of_application == 1500

    def test_calculate_sprinkler_demand_ordinary_hazard_2(self):
        """Test sprinkler demand for ordinary hazard 2."""
        calculator = FireProtectionCalculator()
        building = BuildingData(
            floor_area=20000.0,
            ceiling_height=12.0,
            occupancy_hazard=OccupancyHazard.ORDINARY_HAZARD_2,
            construction_type="Type II",
        )

        design = calculator.calculate_sprinkler_demand(building)

        assert design.density == 0.20
        assert design.area_of_application == 1500

    def test_calculate_sprinkler_demand_extra_hazard_1(self):
        """Test sprinkler demand for extra hazard 1."""
        calculator = FireProtectionCalculator()
        building = BuildingData(
            floor_area=30000.0,
            ceiling_height=15.0,
            occupancy_hazard=OccupancyHazard.EXTRA_HAZARD_1,
            construction_type="Type II",
        )

        design = calculator.calculate_sprinkler_demand(building)

        assert design.density == 0.30
        assert design.area_of_application == 2500

    def test_calculate_sprinkler_demand_extra_hazard_2(self):
        """Test sprinkler demand for extra hazard 2."""
        calculator = FireProtectionCalculator()
        building = BuildingData(
            floor_area=30000.0,
            ceiling_height=15.0,
            occupancy_hazard=OccupancyHazard.EXTRA_HAZARD_2,
            construction_type="Type II",
        )

        design = calculator.calculate_sprinkler_demand(building)

        assert design.density == 0.40
        assert design.area_of_application == 2500

    def test_sprinkler_demand_increases_with_hazard(self):
        """Test that demand increases with hazard classification."""
        calculator = FireProtectionCalculator()

        light = BuildingData(10000.0, 10.0, OccupancyHazard.LIGHT_HAZARD, "Type II")
        ordinary = BuildingData(
            10000.0, 10.0, OccupancyHazard.ORDINARY_HAZARD_2, "Type II"
        )
        extra = BuildingData(10000.0, 10.0, OccupancyHazard.EXTRA_HAZARD_2, "Type II")

        light_design = calculator.calculate_sprinkler_demand(light)
        ordinary_design = calculator.calculate_sprinkler_demand(ordinary)
        extra_design = calculator.calculate_sprinkler_demand(extra)

        assert light_design.density < ordinary_design.density
        assert ordinary_design.density < extra_design.density


class TestFireProtectionCalculatorTotalDemand:
    """Tests for total water demand calculations."""

    def test_calculate_total_demand_with_hose_allowance(self):
        """Test total demand includes hose allowance."""
        calculator = FireProtectionCalculator()

        sprinkler_design = SprinklerDesign(
            density=0.15,
            area_of_application=1500,
            coverage_per_head=110,
            number_of_heads=14,
            flow_per_head=16.5,
        )

        total_demand = calculator.calculate_total_demand(
            sprinkler_design, hose_allowance=250.0
        )

        # Should be sprinkler demand + hose allowance
        sprinkler_demand = 14 * 16.5  # 231 GPM
        expected = sprinkler_demand + 250.0
        assert abs(total_demand - expected) < 1.0

    def test_calculate_total_demand_default_hose_allowance(self):
        """Test total demand with default hose allowance."""
        calculator = FireProtectionCalculator()

        sprinkler_design = SprinklerDesign(
            density=0.10,
            area_of_application=1500,
            coverage_per_head=191,
            number_of_heads=8,
            flow_per_head=19.1,
        )

        total_demand = calculator.calculate_total_demand(sprinkler_design)

        # Should include default 250 GPM hose allowance
        assert total_demand > 8 * 19.1


class TestFireProtectionCalculatorPipeSizing:
    """Tests for fire protection piping sizing."""

    def test_size_piping_small_flow(self):
        """Test piping size for small flow rate."""
        calculator = FireProtectionCalculator()

        pipe_size, pressure_loss = calculator.size_piping(flow_rate=50.0, length=100.0)

        assert pipe_size is not None
        assert pressure_loss > 0
        assert pressure_loss < 50.0  # Reasonable pressure loss

    def test_size_piping_medium_flow(self):
        """Test piping size for medium flow rate."""
        calculator = FireProtectionCalculator()

        pipe_size, pressure_loss = calculator.size_piping(flow_rate=250.0, length=100.0)

        assert pipe_size in ['2"', '2.5"', '3"', '4"']
        assert pressure_loss > 0

    def test_size_piping_large_flow(self):
        """Test piping size for large flow rate."""
        calculator = FireProtectionCalculator()

        pipe_size, pressure_loss = calculator.size_piping(
            flow_rate=1000.0, length=100.0
        )

        # Should select larger pipe
        assert pipe_size in ['6"', '8"']
        assert pressure_loss > 0

    def test_piping_pressure_loss_increases_with_length(self):
        """Test that pressure loss increases with pipe length."""
        calculator = FireProtectionCalculator()

        _, loss_100 = calculator.size_piping(250.0, 100.0)
        _, loss_200 = calculator.size_piping(250.0, 200.0)

        # Longer pipe should have more pressure loss
        assert loss_200 > loss_100


class TestFireProtectionCalculatorSystemDesign:
    """Tests for complete fire protection system design."""

    def test_design_system_light_hazard(self):
        """Test complete system design for light hazard."""
        calculator = FireProtectionCalculator()
        building = BuildingData(
            floor_area=5000.0,
            ceiling_height=10.0,
            occupancy_hazard=OccupancyHazard.LIGHT_HAZARD,
            construction_type="Type II",
        )

        result = calculator.design_system(building, supply_pressure=80.0)

        assert isinstance(result, FireProtectionResult)
        assert result.sprinkler_design is not None
        assert result.total_demand > 0
        assert result.residual_pressure > 0
        assert result.main_pipe_size is not None
        assert result.riser_size is not None
        assert result.system_type == SprinklerType.WET_PIPE

    def test_design_system_ordinary_hazard(self):
        """Test complete system design for ordinary hazard."""
        calculator = FireProtectionCalculator()
        building = BuildingData(
            floor_area=15000.0,
            ceiling_height=12.0,
            occupancy_hazard=OccupancyHazard.ORDINARY_HAZARD_2,
            construction_type="Type II",
        )

        result = calculator.design_system(building, supply_pressure=80.0)

        # Should have higher demand than light hazard
        assert result.total_demand > 200  # Typical for OH2

    def test_design_system_extra_hazard(self):
        """Test complete system design for extra hazard."""
        calculator = FireProtectionCalculator()
        building = BuildingData(
            floor_area=25000.0,
            ceiling_height=15.0,
            occupancy_hazard=OccupancyHazard.EXTRA_HAZARD_2,
            construction_type="Type II",
        )

        result = calculator.design_system(building, supply_pressure=100.0)

        # Should have highest demand
        assert result.total_demand > 500  # Typical for EH2

    def test_design_system_hose_allowance_varies_by_hazard(self):
        """Test that hose allowance varies by occupancy hazard."""
        calculator = FireProtectionCalculator()

        light = BuildingData(5000.0, 10.0, OccupancyHazard.LIGHT_HAZARD, "Type II")
        ordinary = BuildingData(
            5000.0, 10.0, OccupancyHazard.ORDINARY_HAZARD_1, "Type II"
        )
        extra = BuildingData(5000.0, 10.0, OccupancyHazard.EXTRA_HAZARD_1, "Type II")

        light_result = calculator.design_system(light, 80.0)
        ordinary_result = calculator.design_system(ordinary, 80.0)
        extra_result = calculator.design_system(extra, 80.0)

        # Extra hazard should have higher total demand due to hose allowance
        assert extra_result.total_demand > ordinary_result.total_demand

    def test_design_system_different_types(self):
        """Test system design with different sprinkler types."""
        calculator = FireProtectionCalculator()
        building = BuildingData(
            floor_area=10000.0,
            ceiling_height=12.0,
            occupancy_hazard=OccupancyHazard.ORDINARY_HAZARD_1,
            construction_type="Type II",
        )

        wet_pipe = calculator.design_system(building, 80.0, SprinklerType.WET_PIPE)
        dry_pipe = calculator.design_system(building, 80.0, SprinklerType.DRY_PIPE)

        assert wet_pipe.system_type == SprinklerType.WET_PIPE
        assert dry_pipe.system_type == SprinklerType.DRY_PIPE

    def test_design_system_pressure_calculations(self):
        """Test that pressure calculations account for elevation and friction."""
        calculator = FireProtectionCalculator()
        building = BuildingData(
            floor_area=10000.0,
            ceiling_height=20.0,  # Tall ceiling
            occupancy_hazard=OccupancyHazard.ORDINARY_HAZARD_1,
            construction_type="Type II",
        )

        result = calculator.design_system(building, supply_pressure=80.0)

        # Residual pressure should be less than supply due to losses
        assert result.residual_pressure < 80.0
        # Should still meet minimum (7 psi per NFPA 13)
        assert result.residual_pressure >= 7.0


class TestFireProtectionCalculatorIntegration:
    """Integration tests for complete fire protection calculations."""

    def test_complete_fire_protection_workflow(self):
        """Test complete fire protection design workflow."""
        calculator = FireProtectionCalculator()

        # Office building - Ordinary Hazard 1
        building = BuildingData(
            floor_area=12000.0,
            ceiling_height=12.0,
            occupancy_hazard=OccupancyHazard.ORDINARY_HAZARD_1,
            construction_type="Type II",
        )

        # Calculate sprinkler demand
        sprinkler_design = calculator.calculate_sprinkler_demand(building)
        assert sprinkler_design.number_of_heads > 0

        # Calculate total demand
        total_demand = calculator.calculate_total_demand(sprinkler_design, 250.0)
        assert total_demand > 0

        # Size piping
        main_size, main_loss = calculator.size_piping(total_demand, 200.0)
        riser_size, riser_loss = calculator.size_piping(total_demand, 50.0)
        assert main_size is not None
        assert riser_size is not None

        # Complete system design
        result = calculator.design_system(building, 80.0, SprinklerType.WET_PIPE)
        assert result.total_demand == total_demand
        assert result.main_pipe_size == main_size


class TestFireProtectionCalculatorEdgeCases:
    """Tests for edge cases and error conditions."""

    def test_very_small_building(self):
        """Test system design for very small building."""
        calculator = FireProtectionCalculator()
        building = BuildingData(
            floor_area=500.0,
            ceiling_height=8.0,
            occupancy_hazard=OccupancyHazard.LIGHT_HAZARD,
            construction_type="Type V",
        )

        result = calculator.design_system(building, 60.0)

        # Should still produce valid design
        assert result.total_demand > 0
        assert result.main_pipe_size is not None

    def test_very_large_building(self):
        """Test system design for very large building."""
        calculator = FireProtectionCalculator()
        building = BuildingData(
            floor_area=100000.0,
            ceiling_height=20.0,
            occupancy_hazard=OccupancyHazard.EXTRA_HAZARD_2,
            construction_type="Type I",
        )

        result = calculator.design_system(building, 100.0)

        # Should produce valid design with large demand
        assert result.total_demand > 500
        assert result.main_pipe_size is not None

    def test_low_supply_pressure(self):
        """Test system design with low supply pressure."""
        calculator = FireProtectionCalculator()
        building = BuildingData(
            floor_area=10000.0,
            ceiling_height=15.0,
            occupancy_hazard=OccupancyHazard.ORDINARY_HAZARD_2,
            construction_type="Type II",
        )

        result = calculator.design_system(building, supply_pressure=30.0)

        # Should still calculate, but may indicate need for fire pump
        assert result.residual_pressure >= 7.0  # Minimum maintained
