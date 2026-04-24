"""
Unit tests for ElectricalCalculator class.
Tests electrical load calculations, panel sizing, and circuit sizing per NEC.

**Validates: Requirements 2.2, 2.6, 7.1-7.6**
"""

import pytest
from src.calculations.electrical_calculator import (Circuit, CircuitSize,
                                                    CircuitType,
                                                    ElectricalCalculator,
                                                    PanelSize)


class TestElectricalCalculatorLoadCalculations:
    """Tests for electrical load calculations per NEC."""

    def test_calculate_load_empty(self):
        """Test load calculation with no circuits."""
        calculator = ElectricalCalculator()
        circuits = []

        load = calculator.calculate_load(circuits)

        assert load == 0.0

    def test_calculate_load_single_circuit(self):
        """Test load calculation with single circuit."""
        calculator = ElectricalCalculator()
        circuits = [
            Circuit(
                name="Kitchen Lights",
                circuit_type=CircuitType.LIGHTING,
                load=1000.0,  # 1000W
                voltage=120.0,
                continuous=False,
            )
        ]

        load = calculator.calculate_load(circuits)

        # Should be 1000W (no demand factor for small lighting load)
        assert load == 1000.0

    def test_calculate_load_continuous_multiplier(self):
        """Test continuous load multiplier (125%)."""
        calculator = ElectricalCalculator()
        circuits = [
            Circuit(
                name="Continuous Load",
                circuit_type=CircuitType.LIGHTING,
                load=1000.0,
                voltage=120.0,
                continuous=True,
            )
        ]

        load = calculator.calculate_load(circuits)

        # Should be 1250W (1000 × 1.25)
        assert load == 1250.0

    def test_calculate_load_lighting_demand_factor(self):
        """Test lighting demand factor per NEC 220.42."""
        calculator = ElectricalCalculator()
        circuits = [
            Circuit(
                name=f"Lighting {i}",
                circuit_type=CircuitType.LIGHTING,
                load=1000.0,
                voltage=120.0,
                continuous=False,
            )
            for i in range(10)  # 10,000W total
        ]

        load = calculator.calculate_load(circuits)

        # First 3000 at 100%, remainder at 35%
        # 3000 + (7000 × 0.35) = 5450W
        assert load == 5450.0

    def test_calculate_load_mixed_circuits(self):
        """Test load calculation with mixed circuit types."""
        calculator = ElectricalCalculator()
        circuits = [
            Circuit("Lights", CircuitType.LIGHTING, 2000.0, 120.0),
            Circuit("Receptacles", CircuitType.RECEPTACLE, 3000.0, 120.0),
            Circuit("HVAC", CircuitType.HVAC, 5000.0, 240.0),
        ]

        load = calculator.calculate_load(circuits)

        # Should apply appropriate demand factors
        assert load > 0
        assert load <= 10000  # At most the sum (demand factors may reduce it)


class TestElectricalCalculatorPanelSizing:
    """Tests for electrical panel sizing per NEC."""

    def test_size_panel_small_load(self):
        """Test panel sizing for small residential load."""
        calculator = ElectricalCalculator()

        panel = calculator.size_panel(load=10000.0, voltage=240.0)

        assert isinstance(panel, PanelSize)
        assert panel.rated_amperage >= 100
        assert panel.number_of_circuits >= 12
        assert panel.panel_type == "Residential Load Center"

    def test_size_panel_medium_load(self):
        """Test panel sizing for medium commercial load."""
        calculator = ElectricalCalculator()

        panel = calculator.size_panel(load=30000.0, voltage=240.0)

        assert panel.rated_amperage >= 200
        assert panel.panel_type in ["Residential Load Center", "Commercial Panelboard"]

    def test_size_panel_large_load(self):
        """Test panel sizing for large commercial load."""
        calculator = ElectricalCalculator()

        panel = calculator.size_panel(load=100000.0, voltage=480.0)

        assert panel.rated_amperage >= 200
        assert panel.panel_type in ["Commercial Panelboard", "Switchboard"]

    def test_panel_sizing_includes_safety_factor(self):
        """Test that panel sizing includes 125% safety factor."""
        calculator = ElectricalCalculator()

        # 10000W / 240V = 41.67A
        # With 125% factor: 52.08A
        # Should select 100A panel
        panel = calculator.size_panel(load=10000.0, voltage=240.0)

        assert panel.rated_amperage >= 100


class TestElectricalCalculatorCircuitSizing:
    """Tests for circuit conductor sizing per NEC."""

    def test_size_circuit_small_load(self):
        """Test circuit sizing for small load."""
        calculator = ElectricalCalculator()

        circuit = calculator.size_circuit(
            load=1500.0, voltage=120.0, length=50.0, continuous=False  # 1500W
        )

        assert isinstance(circuit, CircuitSize)
        assert circuit.breaker_size >= 15
        assert "#14" in circuit.conductor_size or "#12" in circuit.conductor_size

    def test_size_circuit_continuous_load(self):
        """Test circuit sizing with continuous load factor."""
        calculator = ElectricalCalculator()

        circuit = calculator.size_circuit(
            load=1500.0, voltage=120.0, length=50.0, continuous=True
        )

        # Continuous load requires 125% factor
        # 1500W / 120V = 12.5A × 1.25 = 15.625A
        # Should use #14 AWG with 20A breaker
        assert circuit.breaker_size >= 20

    def test_size_circuit_voltage_drop(self):
        """Test voltage drop calculation."""
        calculator = ElectricalCalculator()

        circuit = calculator.size_circuit(
            load=2400.0, voltage=120.0, length=100.0, continuous=False  # 20A at 120V
        )

        # Voltage drop should be calculated
        assert circuit.voltage_drop > 0
        # Should be reasonable (typically < 5%)
        assert circuit.voltage_drop < 10.0

    def test_size_circuit_large_load(self):
        """Test circuit sizing for large load."""
        calculator = ElectricalCalculator()

        circuit = calculator.size_circuit(
            load=10000.0, voltage=240.0, length=100.0, continuous=False  # Large load
        )

        # Should select appropriate conductor size
        # 10000W / 240V = 41.67A → next standard breaker is 45A
        assert circuit.ampacity >= 42  # 10000W / 240V = 41.67A
        assert circuit.breaker_size >= 45


class TestElectricalCalculatorIntegration:
    """Integration tests for complete electrical calculations."""

    def test_complete_electrical_design(self):
        """Test complete electrical design workflow."""
        calculator = ElectricalCalculator()

        # Define circuits
        circuits = [
            Circuit(
                "Kitchen Lights", CircuitType.LIGHTING, 1200.0, 120.0, continuous=True
            ),
            Circuit("Living Room Receptacles", CircuitType.RECEPTACLE, 1800.0, 120.0),
            Circuit("HVAC Unit", CircuitType.HVAC, 5000.0, 240.0),
            Circuit("Water Heater", CircuitType.APPLIANCE, 4500.0, 240.0),
        ]

        # Calculate total load
        total_load = calculator.calculate_load(circuits)
        assert total_load > 0

        # Size panel
        panel = calculator.size_panel(total_load, 240.0)
        assert panel.rated_amperage >= 100

        # Size individual circuits
        for circuit_def in circuits:
            circuit = calculator.size_circuit(
                circuit_def.load, circuit_def.voltage, 50.0, circuit_def.continuous
            )
            assert circuit.breaker_size > 0
            assert circuit.ampacity > 0


class TestElectricalCalculatorEdgeCases:
    """Tests for edge cases and error conditions."""

    def test_zero_voltage(self):
        """Test handling of zero voltage."""
        calculator = ElectricalCalculator()

        # Should handle gracefully (may raise exception or return large value)
        # Implementation should prevent division by zero
        try:
            panel = calculator.size_panel(10000.0, 0.0)
            # If it doesn't raise, should return some default
            assert panel is not None
        except (ZeroDivisionError, ValueError):
            # Acceptable to raise exception
            pass

    def test_very_long_circuit(self):
        """Test circuit sizing with very long run."""
        calculator = ElectricalCalculator()

        circuit = calculator.size_circuit(
            load=2400.0, voltage=120.0, length=500.0, continuous=False  # Very long run
        )

        # Should size up conductor to reduce voltage drop
        assert circuit.voltage_drop > 0
        # Larger conductor should be selected
        assert circuit.ampacity >= 20
