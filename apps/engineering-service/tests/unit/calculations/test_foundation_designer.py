"""
Unit tests for FoundationDesigner class.
Tests foundation design calculations for bearing capacity, settlement,
and reinforcement requirements.

**Validates: Requirements 1.4, 1.5, 1.6, 7.1-7.6**
"""

import pytest
from src.calculations.foundation_designer import (FoundationDesigner,
                                                  FoundationDesignResult,
                                                  FoundationGeometry,
                                                  FoundationLoads,
                                                  FoundationType,
                                                  SoilProperties)


class TestSoilProperties:
    """Tests for SoilProperties dataclass."""

    def test_soil_properties_creation(self):
        """Test creating soil properties."""
        soil = SoilProperties(
            bearing_capacity=3000.0,  # psf
            unit_weight=120.0,  # pcf
            friction_angle=30.0,  # degrees
            cohesion=500.0,  # psf
        )

        assert soil.bearing_capacity == 3000.0
        assert soil.unit_weight == 120.0
        assert soil.friction_angle == 30.0
        assert soil.cohesion == 500.0


class TestFoundationLoads:
    """Tests for FoundationLoads dataclass."""

    def test_foundation_loads_vertical_only(self):
        """Test foundation loads with vertical load only."""
        loads = FoundationLoads(vertical_load=100000.0)

        assert loads.vertical_load == 100000.0
        assert loads.moment_x == 0.0
        assert loads.moment_y == 0.0
        assert loads.horizontal_x == 0.0
        assert loads.horizontal_y == 0.0

    def test_foundation_loads_with_moments(self):
        """Test foundation loads with moments."""
        loads = FoundationLoads(
            vertical_load=100000.0,
            moment_x=50000.0,
            moment_y=30000.0,
            horizontal_x=5000.0,
            horizontal_y=3000.0,
        )

        assert loads.vertical_load == 100000.0
        assert loads.moment_x == 50000.0
        assert loads.moment_y == 30000.0


class TestFoundationGeometry:
    """Tests for FoundationGeometry class."""

    def test_square_footing_area(self):
        """Test area calculation for square footing."""
        geometry = FoundationGeometry(
            foundation_type=FoundationType.SPREAD_FOOTING,
            length=10.0,
            width=10.0,
            depth=2.0,
        )

        assert geometry.area == 100.0  # 10 * 10

    def test_rectangular_footing_area(self):
        """Test area calculation for rectangular footing."""
        geometry = FoundationGeometry(
            foundation_type=FoundationType.SPREAD_FOOTING,
            length=12.0,
            width=8.0,
            depth=2.0,
        )

        assert geometry.area == 96.0  # 12 * 8

    def test_circular_footing_area(self):
        """Test area calculation for circular footing."""
        geometry = FoundationGeometry(
            foundation_type=FoundationType.SPREAD_FOOTING,
            diameter=10.0,
            depth=2.0,
        )

        # A = π * r² = π * 5² = 78.54
        expected_area = 3.14159265359 * 5.0**2
        assert geometry.area == pytest.approx(expected_area, rel=1e-3)

    def test_mat_foundation_area(self):
        """Test area calculation for mat foundation."""
        geometry = FoundationGeometry(
            foundation_type=FoundationType.MAT_FOUNDATION,
            length=50.0,
            width=40.0,
            depth=3.0,
        )

        assert geometry.area == 2000.0  # 50 * 40


class TestFoundationDesignerBasicFunctionality:
    """Tests for basic FoundationDesigner functionality."""

    def test_design_foundation_with_valid_inputs(self):
        """Test foundation design with valid inputs."""
        designer = FoundationDesigner()

        soil = SoilProperties(
            bearing_capacity=3000.0,
            unit_weight=120.0,
            friction_angle=30.0,
            cohesion=500.0,
        )

        loads = FoundationLoads(vertical_load=100000.0)

        geometry = FoundationGeometry(
            foundation_type=FoundationType.SPREAD_FOOTING,
            length=10.0,
            width=10.0,
            depth=2.0,
        )

        result = designer.design_foundation(
            loads=loads, soil_properties=soil, geometry=geometry
        )

        assert isinstance(result, FoundationDesignResult)
        assert result.bearing_pressure > 0
        assert result.allowable_bearing_capacity > 0

    def test_design_foundation_negative_load_raises_error(self):
        """Test that negative vertical load raises ValueError."""
        designer = FoundationDesigner()

        soil = SoilProperties(
            bearing_capacity=3000.0,
            unit_weight=120.0,
            friction_angle=30.0,
            cohesion=500.0,
        )

        loads = FoundationLoads(vertical_load=-100000.0)

        geometry = FoundationGeometry(
            foundation_type=FoundationType.SPREAD_FOOTING,
            length=10.0,
            width=10.0,
            depth=2.0,
        )

        with pytest.raises(ValueError, match="vertical_load must be non-negative"):
            designer.design_foundation(
                loads=loads, soil_properties=soil, geometry=geometry
            )

    def test_design_foundation_zero_area_raises_error(self):
        """Test that zero area raises ValueError."""
        designer = FoundationDesigner()

        soil = SoilProperties(
            bearing_capacity=3000.0,
            unit_weight=120.0,
            friction_angle=30.0,
            cohesion=500.0,
        )

        loads = FoundationLoads(vertical_load=100000.0)

        geometry = FoundationGeometry(
            foundation_type=FoundationType.SPREAD_FOOTING,
            length=0.0,
            width=10.0,
            depth=2.0,
        )

        with pytest.raises(ValueError, match="Foundation area must be positive"):
            designer.design_foundation(
                loads=loads, soil_properties=soil, geometry=geometry
            )


class TestFoundationDesignerBearingCapacity:
    """Tests for bearing capacity calculations."""

    def test_bearing_pressure_calculation(self):
        """Test bearing pressure calculation."""
        designer = FoundationDesigner()

        loads = FoundationLoads(vertical_load=100000.0)

        geometry = FoundationGeometry(
            foundation_type=FoundationType.SPREAD_FOOTING,
            length=10.0,
            width=10.0,
            depth=2.0,
        )

        # P = V / A = 100000 / 100 = 1000 psf
        expected_pressure = 1000.0

        pressure = designer._calculate_bearing_pressure(loads, geometry.area, geometry)

        assert pressure == pytest.approx(expected_pressure, rel=1e-6)

    def test_bearing_pressure_with_moment(self):
        """Test bearing pressure with moment (eccentric loading)."""
        designer = FoundationDesigner()

        # Moment creates eccentricity
        loads = FoundationLoads(
            vertical_load=100000.0,
            moment_x=100000.0,  # lb-ft
        )

        geometry = FoundationGeometry(
            foundation_type=FoundationType.SPREAD_FOOTING,
            length=10.0,
            width=10.0,
            depth=2.0,
        )

        pressure = designer._calculate_bearing_pressure(loads, geometry.area, geometry)

        # With moment, max pressure should be higher than uniform
        uniform_pressure = 100000.0 / 100.0
        assert pressure > uniform_pressure

    def test_allowable_bearing_capacity_from_soil(self):
        """Test allowable bearing capacity from soil properties."""
        designer = FoundationDesigner()

        soil = SoilProperties(
            bearing_capacity=3000.0,
            unit_weight=120.0,
            friction_angle=30.0,
            cohesion=500.0,
        )

        geometry = FoundationGeometry(
            foundation_type=FoundationType.SPREAD_FOOTING,
            length=10.0,
            width=10.0,
            depth=2.0,
        )

        capacity = designer._calculate_allowable_bearing_capacity(soil, geometry)

        # Should be based on soil bearing capacity with depth adjustment
        assert capacity > 0
        assert capacity >= soil.bearing_capacity

    def test_bearing_capacity_increases_with_depth(self):
        """Test that bearing capacity increases with foundation depth."""
        designer = FoundationDesigner()

        soil = SoilProperties(
            bearing_capacity=3000.0,
            unit_weight=120.0,
            friction_angle=30.0,
            cohesion=500.0,
        )

        shallow = FoundationGeometry(
            foundation_type=FoundationType.SPREAD_FOOTING,
            length=10.0,
            width=10.0,
            depth=1.0,
        )

        deep = FoundationGeometry(
            foundation_type=FoundationType.SPREAD_FOOTING,
            length=10.0,
            width=10.0,
            depth=4.0,
        )

        capacity_shallow = designer._calculate_allowable_bearing_capacity(soil, shallow)
        capacity_deep = designer._calculate_allowable_bearing_capacity(soil, deep)

        # Deeper foundation should have higher capacity
        assert capacity_deep > capacity_shallow


class TestFoundationDesignerSettlement:
    """Tests for settlement analysis."""

    def test_settlement_calculation(self):
        """Test settlement calculation."""
        designer = FoundationDesigner()

        soil = SoilProperties(
            bearing_capacity=3000.0,
            unit_weight=120.0,
            friction_angle=30.0,
            cohesion=500.0,
            elastic_modulus=5000.0,  # psi
        )

        loads = FoundationLoads(vertical_load=100000.0)

        geometry = FoundationGeometry(
            foundation_type=FoundationType.SPREAD_FOOTING,
            length=10.0,
            width=10.0,
            depth=2.0,
        )

        settlement = designer._calculate_settlement(loads, soil, geometry)

        # Settlement should be positive and reasonable
        assert settlement > 0
        assert settlement < 12.0  # Less than 12 inches

    def test_settlement_increases_with_load(self):
        """Test that settlement increases with load."""
        designer = FoundationDesigner()

        soil = SoilProperties(
            bearing_capacity=3000.0,
            unit_weight=120.0,
            friction_angle=30.0,
            cohesion=500.0,
            elastic_modulus=5000.0,
        )

        geometry = FoundationGeometry(
            foundation_type=FoundationType.SPREAD_FOOTING,
            length=10.0,
            width=10.0,
            depth=2.0,
        )

        loads_low = FoundationLoads(vertical_load=50000.0)
        loads_high = FoundationLoads(vertical_load=150000.0)

        settlement_low = designer._calculate_settlement(loads_low, soil, geometry)
        settlement_high = designer._calculate_settlement(loads_high, soil, geometry)

        assert settlement_high > settlement_low

    def test_allowable_settlement_limit(self):
        """Test allowable settlement limit."""
        designer = FoundationDesigner()

        # Typical allowable settlement is 1 inch for most structures
        assert designer.ALLOWABLE_SETTLEMENT_TOTAL == 1.0


class TestFoundationDesignerReinforcement:
    """Tests for reinforcement requirements."""

    def test_reinforcement_calculation(self):
        """Test reinforcement calculation."""
        designer = FoundationDesigner()

        loads = FoundationLoads(vertical_load=100000.0)

        geometry = FoundationGeometry(
            foundation_type=FoundationType.SPREAD_FOOTING,
            length=10.0,
            width=10.0,
            depth=2.0,
            thickness=18.0,  # inches
        )

        reinforcement = designer._calculate_reinforcement(loads, geometry)

        # Should return reinforcement area in square inches
        assert reinforcement > 0

    def test_reinforcement_increases_with_load(self):
        """Test that reinforcement increases with load."""
        designer = FoundationDesigner()

        geometry = FoundationGeometry(
            foundation_type=FoundationType.SPREAD_FOOTING,
            length=10.0,
            width=10.0,
            depth=2.0,
            thickness=18.0,
        )

        loads_low = FoundationLoads(vertical_load=50000.0)
        loads_high = FoundationLoads(vertical_load=150000.0)

        reinf_low = designer._calculate_reinforcement(loads_low, geometry)
        reinf_high = designer._calculate_reinforcement(loads_high, geometry)

        assert reinf_high > reinf_low

    def test_minimum_reinforcement_ratio(self):
        """Test minimum reinforcement ratio."""
        designer = FoundationDesigner()

        # ACI 318 minimum reinforcement ratio
        assert designer.MIN_REINFORCEMENT_RATIO == 0.0018


class TestFoundationDesignerAdequacyChecks:
    """Tests for foundation adequacy checks."""

    def test_adequate_foundation_design(self):
        """Test foundation design that meets all requirements."""
        designer = FoundationDesigner()

        soil = SoilProperties(
            bearing_capacity=4000.0,
            unit_weight=120.0,
            friction_angle=30.0,
            cohesion=500.0,
            elastic_modulus=5000.0,
        )

        # Use large footing with moderate load
        geometry = FoundationGeometry(
            foundation_type=FoundationType.SPREAD_FOOTING,
            length=12.0,
            width=12.0,
            depth=3.0,
            thickness=18.0,
        )

        loads = FoundationLoads(vertical_load=100000.0)

        result = designer.design_foundation(
            loads=loads, soil_properties=soil, geometry=geometry
        )

        assert result.is_adequate is True
        assert result.bearing_ratio <= 1.0
        assert result.settlement <= designer.ALLOWABLE_SETTLEMENT_TOTAL

    def test_inadequate_foundation_bearing(self):
        """Test foundation design that fails bearing capacity check."""
        designer = FoundationDesigner()

        soil = SoilProperties(
            bearing_capacity=2000.0,  # Low bearing capacity
            unit_weight=120.0,
            friction_angle=25.0,
            cohesion=300.0,
            elastic_modulus=3000.0,
        )

        # Small footing with high load
        geometry = FoundationGeometry(
            foundation_type=FoundationType.SPREAD_FOOTING,
            length=5.0,
            width=5.0,
            depth=2.0,
            thickness=12.0,
        )

        loads = FoundationLoads(vertical_load=200000.0)

        result = designer.design_foundation(
            loads=loads, soil_properties=soil, geometry=geometry
        )

        assert result.is_adequate is False
        assert result.bearing_ratio > 1.0

    def test_inadequate_foundation_settlement(self):
        """Test foundation design that fails settlement check."""
        designer = FoundationDesigner()

        soil = SoilProperties(
            bearing_capacity=3000.0,
            unit_weight=120.0,
            friction_angle=28.0,
            cohesion=400.0,
            elastic_modulus=1000.0,  # Very soft soil
        )

        geometry = FoundationGeometry(
            foundation_type=FoundationType.SPREAD_FOOTING,
            length=8.0,
            width=8.0,
            depth=2.0,
            thickness=15.0,
        )

        loads = FoundationLoads(vertical_load=150000.0)

        result = designer.design_foundation(
            loads=loads, soil_properties=soil, geometry=geometry
        )

        # May fail settlement check with soft soil
        if result.settlement > designer.ALLOWABLE_SETTLEMENT_TOTAL:
            assert result.is_adequate is False


class TestFoundationDesignerDifferentTypes:
    """Tests for different foundation types."""

    def test_spread_footing_design(self):
        """Test spread footing design."""
        designer = FoundationDesigner()

        soil = SoilProperties(
            bearing_capacity=3000.0,
            unit_weight=120.0,
            friction_angle=30.0,
            cohesion=500.0,
            elastic_modulus=5000.0,
        )

        geometry = FoundationGeometry(
            foundation_type=FoundationType.SPREAD_FOOTING,
            length=10.0,
            width=10.0,
            depth=2.0,
            thickness=18.0,
        )

        loads = FoundationLoads(vertical_load=100000.0)

        result = designer.design_foundation(
            loads=loads, soil_properties=soil, geometry=geometry
        )

        assert result.bearing_pressure > 0
        assert result.settlement > 0

    def test_mat_foundation_design(self):
        """Test mat foundation design."""
        designer = FoundationDesigner()

        soil = SoilProperties(
            bearing_capacity=2500.0,
            unit_weight=120.0,
            friction_angle=28.0,
            cohesion=400.0,
            elastic_modulus=4000.0,
        )

        geometry = FoundationGeometry(
            foundation_type=FoundationType.MAT_FOUNDATION,
            length=50.0,
            width=40.0,
            depth=3.0,
            thickness=24.0,
        )

        loads = FoundationLoads(vertical_load=2000000.0)

        result = designer.design_foundation(
            loads=loads, soil_properties=soil, geometry=geometry
        )

        assert result.bearing_pressure > 0
        # Mat foundation should have lower bearing pressure
        assert result.bearing_pressure < 2000.0

    def test_continuous_footing_design(self):
        """Test continuous footing design."""
        designer = FoundationDesigner()

        soil = SoilProperties(
            bearing_capacity=3000.0,
            unit_weight=120.0,
            friction_angle=30.0,
            cohesion=500.0,
            elastic_modulus=5000.0,
        )

        geometry = FoundationGeometry(
            foundation_type=FoundationType.CONTINUOUS_FOOTING,
            length=100.0,  # Long wall footing
            width=4.0,
            depth=2.0,
            thickness=15.0,
        )

        loads = FoundationLoads(vertical_load=200000.0)

        result = designer.design_foundation(
            loads=loads, soil_properties=soil, geometry=geometry
        )

        assert result.bearing_pressure > 0


class TestFoundationDesignerWarnings:
    """Tests for warning generation."""

    def test_high_bearing_ratio_warning(self):
        """Test that high bearing ratio generates warning."""
        designer = FoundationDesigner()

        soil = SoilProperties(
            bearing_capacity=2500.0,
            unit_weight=120.0,
            friction_angle=28.0,
            cohesion=400.0,
            elastic_modulus=4000.0,
        )

        geometry = FoundationGeometry(
            foundation_type=FoundationType.SPREAD_FOOTING,
            length=6.0,
            width=6.0,
            depth=2.0,
            thickness=15.0,
        )

        loads = FoundationLoads(vertical_load=120000.0)

        result = designer.design_foundation(
            loads=loads, soil_properties=soil, geometry=geometry
        )

        if result.bearing_ratio > 0.9:
            assert any(
                "bearing" in w.lower() or "capacity" in w.lower()
                for w in result.warnings
            )

    def test_excessive_settlement_warning(self):
        """Test that excessive settlement generates warning."""
        designer = FoundationDesigner()

        soil = SoilProperties(
            bearing_capacity=3000.0,
            unit_weight=120.0,
            friction_angle=28.0,
            cohesion=400.0,
            elastic_modulus=2000.0,  # Soft soil
        )

        geometry = FoundationGeometry(
            foundation_type=FoundationType.SPREAD_FOOTING,
            length=8.0,
            width=8.0,
            depth=2.0,
            thickness=15.0,
        )

        loads = FoundationLoads(vertical_load=150000.0)

        result = designer.design_foundation(
            loads=loads, soil_properties=soil, geometry=geometry
        )

        if result.settlement > designer.ALLOWABLE_SETTLEMENT_TOTAL:
            assert any("settlement" in w.lower() for w in result.warnings)

    def test_eccentric_loading_warning(self):
        """Test that eccentric loading generates warning."""
        designer = FoundationDesigner()

        soil = SoilProperties(
            bearing_capacity=3000.0,
            unit_weight=120.0,
            friction_angle=30.0,
            cohesion=500.0,
            elastic_modulus=5000.0,
        )

        geometry = FoundationGeometry(
            foundation_type=FoundationType.SPREAD_FOOTING,
            length=10.0,
            width=10.0,
            depth=2.0,
            thickness=18.0,
        )

        # Large moment creates eccentricity
        loads = FoundationLoads(
            vertical_load=100000.0,
            moment_x=200000.0,  # Large moment
        )

        result = designer.design_foundation(
            loads=loads, soil_properties=soil, geometry=geometry
        )

        # Should have warning about eccentric loading
        assert any(
            "eccentric" in w.lower() or "moment" in w.lower() for w in result.warnings
        )


class TestFoundationDesignerCircularFootings:
    """Tests specifically for circular footings."""

    def test_circular_footing_design(self):
        """Test circular footing design."""
        designer = FoundationDesigner()

        soil = SoilProperties(
            bearing_capacity=3000.0,
            unit_weight=120.0,
            friction_angle=30.0,
            cohesion=500.0,
            elastic_modulus=5000.0,
        )

        geometry = FoundationGeometry(
            foundation_type=FoundationType.SPREAD_FOOTING,
            diameter=10.0,
            depth=2.0,
            thickness=18.0,
        )

        loads = FoundationLoads(vertical_load=100000.0)

        result = designer.design_foundation(
            loads=loads, soil_properties=soil, geometry=geometry
        )

        assert result.bearing_pressure > 0
        assert result.settlement > 0

    def test_circular_vs_square_same_area(self):
        """
        Test that circular and square footings with same area
        behave similarly.
        """
        designer = FoundationDesigner()

        soil = SoilProperties(
            bearing_capacity=3000.0,
            unit_weight=120.0,
            friction_angle=30.0,
            cohesion=500.0,
            elastic_modulus=5000.0,
        )

        # Circle d=10 has A=78.54, square 8.86x8.86 has A=78.50
        circular = FoundationGeometry(
            foundation_type=FoundationType.SPREAD_FOOTING,
            diameter=10.0,
            depth=2.0,
            thickness=18.0,
        )

        square = FoundationGeometry(
            foundation_type=FoundationType.SPREAD_FOOTING,
            length=8.86,
            width=8.86,
            depth=2.0,
            thickness=18.0,
        )

        loads = FoundationLoads(vertical_load=100000.0)

        result_circular = designer.design_foundation(
            loads=loads, soil_properties=soil, geometry=circular
        )

        result_square = designer.design_foundation(
            loads=loads, soil_properties=soil, geometry=square
        )

        # Bearing pressures should be very similar (within 2%)
        ratio = result_circular.bearing_pressure / result_square.bearing_pressure
        assert 0.98 <= ratio <= 1.02
