"""
Unit tests for ColumnDesigner class.
Tests column design calculations for axial capacity, buckling,
and combined stress.

**Validates: Requirements 1.3, 1.5, 1.6, 7.1-7.6**
"""

import pytest
from src.calculations.column_designer import (ColumnDesigner,
                                              ColumnDesignResult,
                                              ColumnGeometry, ColumnLoads,
                                              EndCondition, MaterialProperties,
                                              MaterialType)


class TestColumnGeometry:
    """Tests for ColumnGeometry class."""

    def test_rectangular_column_area(self):
        """Test area calculation for rectangular column."""
        geometry = ColumnGeometry(depth=12.0, width=12.0)

        assert geometry.is_rectangular is True
        assert geometry.area == 144.0  # 12 * 12

    def test_circular_column_area(self):
        """Test area calculation for circular column."""
        geometry = ColumnGeometry(diameter=12.0)

        assert geometry.is_circular is True
        # A = π * r² = π * 6² = 113.097
        expected_area = 3.14159265359 * 6.0**2
        assert geometry.area == pytest.approx(expected_area, rel=1e-3)

    def test_rectangular_column_radius_of_gyration(self):
        """Test radius of gyration for rectangular column."""
        geometry = ColumnGeometry(depth=12.0, width=8.0)

        # r = sqrt(I/A) = sqrt((bd³/12)/(bd))
        # = d/sqrt(12) for weak axis
        # Weak axis: r = 8/sqrt(12) = 2.309
        expected_r = 8.0 / (12.0**0.5)
        assert geometry.radius_of_gyration == pytest.approx(expected_r, rel=1e-3)

    def test_circular_column_radius_of_gyration(self):
        """Test radius of gyration for circular column."""
        geometry = ColumnGeometry(diameter=12.0)

        # r = d/4 = 12/4 = 3.0
        expected_r = 12.0 / 4.0
        assert geometry.radius_of_gyration == pytest.approx(expected_r, rel=1e-3)

    def test_moment_of_inertia_rectangular(self):
        """Test moment of inertia for rectangular column."""
        geometry = ColumnGeometry(depth=12.0, width=8.0)

        # I_weak = bd³/12 = 12 * 8³ / 12 = 512 in⁴
        expected_i = (12.0 * 8.0**3) / 12.0
        assert geometry.moment_of_inertia == pytest.approx(expected_i, rel=1e-6)

    def test_moment_of_inertia_circular(self):
        """Test moment of inertia for circular column."""
        geometry = ColumnGeometry(diameter=12.0)

        # I = π * d⁴ / 64 = π * 12⁴ / 64 = 1017.88 in⁴
        expected_i = 3.14159265359 * 12.0**4 / 64.0
        assert geometry.moment_of_inertia == pytest.approx(expected_i, rel=1e-3)


class TestColumnLoads:
    """Tests for ColumnLoads dataclass."""

    def test_axial_load_only(self):
        """Test column loads with axial load only."""
        loads = ColumnLoads(axial_load=100000.0)

        assert loads.axial_load == 100000.0
        assert loads.moment_x == 0.0
        assert loads.moment_y == 0.0

    def test_combined_axial_and_moment(self):
        """Test column loads with axial and moment."""
        loads = ColumnLoads(axial_load=100000.0, moment_x=50000.0, moment_y=30000.0)

        assert loads.axial_load == 100000.0
        assert loads.moment_x == 50000.0
        assert loads.moment_y == 30000.0


class TestMaterialProperties:
    """Tests for MaterialProperties dataclass."""

    def test_steel_column_material(self):
        """Test steel material properties for columns."""
        steel = MaterialProperties(
            material_type=MaterialType.STEEL,
            yield_strength=50000.0,  # A572 Grade 50
            elastic_modulus=29000000.0,
            density=490.0,
            allowable_stress_factor=0.6,
        )

        assert steel.material_type == MaterialType.STEEL
        assert steel.yield_strength == 50000.0

    def test_concrete_column_material(self):
        """Test concrete material properties for columns."""
        concrete = MaterialProperties(
            material_type=MaterialType.CONCRETE,
            yield_strength=4000.0,  # f'c
            elastic_modulus=3600000.0,
            density=150.0,
            allowable_stress_factor=0.45,
        )

        assert concrete.material_type == MaterialType.CONCRETE
        assert concrete.yield_strength == 4000.0


class TestColumnDesignerBasicFunctionality:
    """Tests for basic ColumnDesigner functionality."""

    def test_design_column_with_valid_inputs(self):
        """Test column design with valid inputs."""
        designer = ColumnDesigner()

        steel = MaterialProperties(
            material_type=MaterialType.STEEL,
            yield_strength=50000.0,
            elastic_modulus=29000000.0,
            density=490.0,
            allowable_stress_factor=0.6,
        )

        loads = ColumnLoads(axial_load=100000.0)
        geometry = ColumnGeometry(depth=12.0, width=12.0)

        result = designer.design_column(
            length=120.0,  # 10 feet
            loads=loads,
            material=steel,
            geometry=geometry,
            end_condition=EndCondition.PINNED_PINNED,
        )

        assert isinstance(result, ColumnDesignResult)
        assert result.axial_capacity > 0
        assert result.buckling_capacity > 0

    def test_design_column_negative_length_raises_error(self):
        """Test that negative length raises ValueError."""
        designer = ColumnDesigner()

        steel = MaterialProperties(
            material_type=MaterialType.STEEL,
            yield_strength=50000.0,
            elastic_modulus=29000000.0,
            density=490.0,
        )

        loads = ColumnLoads(axial_load=100000.0)
        geometry = ColumnGeometry(depth=12.0, width=12.0)

        with pytest.raises(ValueError, match="length must be positive"):
            designer.design_column(
                length=-120.0, loads=loads, material=steel, geometry=geometry
            )

    def test_design_column_negative_axial_load_raises_error(self):
        """Test that negative axial load raises ValueError."""
        designer = ColumnDesigner()

        steel = MaterialProperties(
            material_type=MaterialType.STEEL,
            yield_strength=50000.0,
            elastic_modulus=29000000.0,
            density=490.0,
        )

        loads = ColumnLoads(axial_load=-100000.0)
        geometry = ColumnGeometry(depth=12.0, width=12.0)

        with pytest.raises(ValueError, match="axial_load must be non-negative"):
            designer.design_column(
                length=120.0, loads=loads, material=steel, geometry=geometry
            )


class TestColumnDesignerAxialCapacity:
    """Tests for axial capacity calculations."""

    def test_axial_capacity_steel_column(self):
        """Test axial capacity for steel column."""
        designer = ColumnDesigner()

        steel = MaterialProperties(
            material_type=MaterialType.STEEL,
            yield_strength=50000.0,
            elastic_modulus=29000000.0,
            density=490.0,
            allowable_stress_factor=0.6,
        )

        geometry = ColumnGeometry(depth=12.0, width=12.0)

        # P_allowable = F_y * A * factor = 50000 * 144 * 0.6 = 4,320,000 lb
        expected_capacity = 50000.0 * 144.0 * 0.6

        capacity = designer._calculate_axial_capacity(geometry, steel)

        assert capacity == pytest.approx(expected_capacity, rel=1e-6)

    def test_axial_capacity_concrete_column(self):
        """Test axial capacity for concrete column."""
        designer = ColumnDesigner()

        concrete = MaterialProperties(
            material_type=MaterialType.CONCRETE,
            yield_strength=4000.0,
            elastic_modulus=3600000.0,
            density=150.0,
            allowable_stress_factor=0.45,
        )

        geometry = ColumnGeometry(diameter=18.0)

        # A = π * r² = π * 9² = 254.47 in²
        # P_allowable = f'c * A * factor = 4000 * 254.47 * 0.45
        area = 3.14159265359 * 9.0**2
        expected_capacity = 4000.0 * area * 0.45

        capacity = designer._calculate_axial_capacity(geometry, concrete)

        assert capacity == pytest.approx(expected_capacity, rel=1e-3)


class TestColumnDesignerBucklingCapacity:
    """Tests for buckling capacity calculations (Euler buckling)."""

    def test_euler_buckling_load(self):
        """Test Euler buckling load calculation."""
        designer = ColumnDesigner()

        steel = MaterialProperties(
            material_type=MaterialType.STEEL,
            yield_strength=50000.0,
            elastic_modulus=29000000.0,
            density=490.0,
        )

        geometry = ColumnGeometry(depth=12.0, width=12.0)
        length = 120.0  # inches
        k_factor = 1.0  # Pinned-pinned

        # P_cr = π² * E * I / (KL)²
        # I = bd³/12 = 12 * 12³ / 12 = 1728 in⁴ (weak axis)
        # P_cr = π² * 29e6 * 1728 / (1.0 * 120)²
        i_value = (12.0 * 12.0**3) / 12.0
        expected_pcr = (3.14159265359**2 * 29000000.0 * i_value) / (
            (k_factor * length) ** 2
        )

        pcr = designer._calculate_euler_buckling_load(geometry, steel, length, k_factor)

        assert pcr == pytest.approx(expected_pcr, rel=1e-3)

    def test_buckling_capacity_pinned_pinned(self):
        """Test buckling capacity with pinned-pinned ends."""
        designer = ColumnDesigner()

        steel = MaterialProperties(
            material_type=MaterialType.STEEL,
            yield_strength=50000.0,
            elastic_modulus=29000000.0,
            density=490.0,
        )

        geometry = ColumnGeometry(depth=12.0, width=12.0)
        length = 120.0

        capacity = designer._calculate_buckling_capacity(
            geometry, steel, length, EndCondition.PINNED_PINNED
        )

        assert capacity > 0

    def test_buckling_capacity_fixed_fixed(self):
        """Test buckling capacity with fixed-fixed ends."""
        designer = ColumnDesigner()

        steel = MaterialProperties(
            material_type=MaterialType.STEEL,
            yield_strength=50000.0,
            elastic_modulus=29000000.0,
            density=490.0,
        )

        # Use very long column to ensure buckling governs
        geometry = ColumnGeometry(depth=12.0, width=12.0)
        length = 480.0  # 40 feet - very long to ensure buckling controls

        capacity_fixed = designer._calculate_buckling_capacity(
            geometry, steel, length, EndCondition.FIXED_FIXED
        )
        capacity_pinned = designer._calculate_buckling_capacity(
            geometry, steel, length, EndCondition.PINNED_PINNED
        )

        # Fixed-fixed should have higher capacity (K=0.5 vs K=1.0)
        # With K=0.5, effective length is half, so capacity is 4x higher
        assert capacity_fixed > capacity_pinned

    def test_buckling_capacity_fixed_pinned(self):
        """Test buckling capacity with fixed-pinned ends."""
        designer = ColumnDesigner()

        steel = MaterialProperties(
            material_type=MaterialType.STEEL,
            yield_strength=50000.0,
            elastic_modulus=29000000.0,
            density=490.0,
        )

        geometry = ColumnGeometry(depth=12.0, width=12.0)
        length = 120.0

        capacity = designer._calculate_buckling_capacity(
            geometry, steel, length, EndCondition.FIXED_PINNED
        )

        assert capacity > 0

    def test_slenderness_ratio(self):
        """Test slenderness ratio calculation."""
        designer = ColumnDesigner()

        geometry = ColumnGeometry(depth=12.0, width=8.0)
        length = 120.0
        k_factor = 1.0

        # r = 8/sqrt(12) = 2.309
        # λ = KL/r = 1.0 * 120 / 2.309 = 51.96
        r_value = 8.0 / (12.0**0.5)
        expected_lambda = (k_factor * length) / r_value

        slenderness = designer._calculate_slenderness_ratio(geometry, length, k_factor)

        assert slenderness == pytest.approx(expected_lambda, rel=1e-3)


class TestColumnDesignerCombinedStress:
    """Tests for combined stress ratio calculations."""

    def test_combined_stress_ratio_axial_only(self):
        """Test combined stress ratio with axial load only."""
        designer = ColumnDesigner()

        loads = ColumnLoads(axial_load=100000.0)
        axial_capacity = 200000.0
        moment_capacity_x = 500000.0
        moment_capacity_y = 500000.0

        # P/Pn + Mx/Mnx + My/Mny = 100000/200000 + 0 + 0 = 0.5
        expected_ratio = 0.5

        ratio = designer._calculate_combined_stress_ratio(
            loads, axial_capacity, moment_capacity_x, moment_capacity_y
        )

        assert ratio == pytest.approx(expected_ratio, rel=1e-6)

    def test_combined_stress_ratio_with_moments(self):
        """Test combined stress ratio with axial and moments."""
        designer = ColumnDesigner()

        loads = ColumnLoads(axial_load=100000.0, moment_x=200000.0, moment_y=150000.0)
        axial_capacity = 200000.0
        moment_capacity_x = 500000.0
        moment_capacity_y = 500000.0

        # Ratio = 100000/200000 + 200000/500000 + 150000/500000
        #       = 0.5 + 0.4 + 0.3 = 1.2
        expected_ratio = 0.5 + 0.4 + 0.3

        ratio = designer._calculate_combined_stress_ratio(
            loads, axial_capacity, moment_capacity_x, moment_capacity_y
        )

        assert ratio == pytest.approx(expected_ratio, rel=1e-6)

    def test_combined_stress_ratio_moment_only(self):
        """Test combined stress ratio with moment only."""
        designer = ColumnDesigner()

        loads = ColumnLoads(axial_load=0.0, moment_x=250000.0)
        axial_capacity = 200000.0
        moment_capacity_x = 500000.0
        moment_capacity_y = 500000.0

        # Ratio = 0 + 250000/500000 + 0 = 0.5
        expected_ratio = 0.5

        ratio = designer._calculate_combined_stress_ratio(
            loads, axial_capacity, moment_capacity_x, moment_capacity_y
        )

        assert ratio == pytest.approx(expected_ratio, rel=1e-6)


class TestColumnDesignerMomentCapacity:
    """Tests for moment capacity calculations."""

    def test_moment_capacity_rectangular_column(self):
        """Test moment capacity for rectangular column."""
        designer = ColumnDesigner()

        steel = MaterialProperties(
            material_type=MaterialType.STEEL,
            yield_strength=50000.0,
            elastic_modulus=29000000.0,
            density=490.0,
            allowable_stress_factor=0.6,
        )

        geometry = ColumnGeometry(depth=12.0, width=8.0)

        # S = bd²/6 = 8 * 12² / 6 = 192 in³
        # M = F_y * S * factor = 50000 * 192 * 0.6 = 5,760,000 lb-in
        section_modulus = (8.0 * 12.0**2) / 6.0
        expected_capacity = 50000.0 * section_modulus * 0.6

        capacity = designer._calculate_moment_capacity(geometry, steel)

        assert capacity == pytest.approx(expected_capacity, rel=1e-6)

    def test_moment_capacity_circular_column(self):
        """Test moment capacity for circular column."""
        designer = ColumnDesigner()

        steel = MaterialProperties(
            material_type=MaterialType.STEEL,
            yield_strength=50000.0,
            elastic_modulus=29000000.0,
            density=490.0,
            allowable_stress_factor=0.6,
        )

        geometry = ColumnGeometry(diameter=12.0)

        # S = π * d³ / 32 = π * 12³ / 32 = 169.65 in³
        section_modulus = 3.14159265359 * 12.0**3 / 32.0
        expected_capacity = 50000.0 * section_modulus * 0.6

        capacity = designer._calculate_moment_capacity(geometry, steel)

        assert capacity == pytest.approx(expected_capacity, rel=1e-3)


class TestColumnDesignerAdequacyChecks:
    """Tests for column adequacy checks."""

    def test_adequate_column_design(self):
        """Test column design that meets all requirements."""
        designer = ColumnDesigner()

        steel = MaterialProperties(
            material_type=MaterialType.STEEL,
            yield_strength=50000.0,
            elastic_modulus=29000000.0,
            density=490.0,
            allowable_stress_factor=0.6,
        )

        # Use large column with small load
        geometry = ColumnGeometry(depth=14.0, width=14.0)
        loads = ColumnLoads(axial_load=50000.0)

        result = designer.design_column(
            length=120.0, loads=loads, material=steel, geometry=geometry
        )

        assert result.is_adequate is True
        assert result.combined_stress_ratio <= 1.0

    def test_inadequate_column_axial(self):
        """Test column design that fails axial capacity check."""
        designer = ColumnDesigner()

        steel = MaterialProperties(
            material_type=MaterialType.STEEL,
            yield_strength=50000.0,
            elastic_modulus=29000000.0,
            density=490.0,
            allowable_stress_factor=0.6,
        )

        # Use small column with very high load
        geometry = ColumnGeometry(depth=4.0, width=4.0)
        loads = ColumnLoads(axial_load=1000000.0)

        result = designer.design_column(
            length=120.0, loads=loads, material=steel, geometry=geometry
        )

        assert result.is_adequate is False
        assert result.combined_stress_ratio > 1.0

    def test_inadequate_column_buckling(self):
        """Test column design that fails buckling check."""
        designer = ColumnDesigner()

        steel = MaterialProperties(
            material_type=MaterialType.STEEL,
            yield_strength=50000.0,
            elastic_modulus=29000000.0,
            density=490.0,
            allowable_stress_factor=0.6,
        )

        # Use slender column (high L/r ratio)
        geometry = ColumnGeometry(depth=6.0, width=6.0)
        loads = ColumnLoads(axial_load=200000.0)

        result = designer.design_column(
            length=360.0,  # 30 feet - very slender
            loads=loads,
            material=steel,
            geometry=geometry,
        )

        # Should be controlled by buckling
        assert result.buckling_capacity < result.axial_capacity


class TestColumnDesignerDifferentMaterials:
    """Tests for different material types."""

    def test_steel_column_design(self):
        """Test steel column design."""
        designer = ColumnDesigner()

        steel = MaterialProperties(
            material_type=MaterialType.STEEL,
            yield_strength=50000.0,
            elastic_modulus=29000000.0,
            density=490.0,
            allowable_stress_factor=0.6,
        )

        geometry = ColumnGeometry(depth=12.0, width=12.0)
        loads = ColumnLoads(axial_load=100000.0)

        result = designer.design_column(
            length=120.0, loads=loads, material=steel, geometry=geometry
        )

        assert result.axial_capacity > 0
        assert result.buckling_capacity > 0

    def test_concrete_column_design(self):
        """Test concrete column design."""
        designer = ColumnDesigner()

        concrete = MaterialProperties(
            material_type=MaterialType.CONCRETE,
            yield_strength=4000.0,
            elastic_modulus=3600000.0,
            density=150.0,
            allowable_stress_factor=0.45,
        )

        geometry = ColumnGeometry(diameter=18.0)
        loads = ColumnLoads(axial_load=100000.0)

        result = designer.design_column(
            length=120.0, loads=loads, material=concrete, geometry=geometry
        )

        assert result.axial_capacity > 0
        assert result.buckling_capacity > 0


class TestColumnDesignerEndConditions:
    """Tests for different end conditions."""

    def test_end_condition_k_factors(self):
        """Test that different end conditions have correct K factors."""
        designer = ColumnDesigner()

        # K factors per AISC
        assert designer._get_effective_length_factor(EndCondition.FIXED_FIXED) == 0.5
        assert designer._get_effective_length_factor(EndCondition.FIXED_PINNED) == 0.7
        assert designer._get_effective_length_factor(EndCondition.PINNED_PINNED) == 1.0
        assert designer._get_effective_length_factor(EndCondition.FIXED_FREE) == 2.0

    def test_fixed_free_cantilever_column(self):
        """Test cantilever column (fixed-free)."""
        designer = ColumnDesigner()

        steel = MaterialProperties(
            material_type=MaterialType.STEEL,
            yield_strength=50000.0,
            elastic_modulus=29000000.0,
            density=490.0,
        )

        geometry = ColumnGeometry(depth=12.0, width=12.0)
        loads = ColumnLoads(axial_load=100000.0)

        result = designer.design_column(
            length=120.0,
            loads=loads,
            material=steel,
            geometry=geometry,
            end_condition=EndCondition.FIXED_FREE,
        )

        # Cantilever should have lowest buckling capacity (K=2.0)
        assert result.buckling_capacity > 0


class TestColumnDesignerWarnings:
    """Tests for warning generation."""

    def test_high_slenderness_warning(self):
        """Test that high slenderness ratio generates warning."""
        designer = ColumnDesigner()

        steel = MaterialProperties(
            material_type=MaterialType.STEEL,
            yield_strength=50000.0,
            elastic_modulus=29000000.0,
            density=490.0,
        )

        # Very slender column
        geometry = ColumnGeometry(depth=4.0, width=4.0)
        loads = ColumnLoads(axial_load=10000.0)

        result = designer.design_column(
            length=480.0, loads=loads, material=steel, geometry=geometry  # 40 feet
        )

        # Should have warning about slenderness
        assert any("slender" in w.lower() for w in result.warnings)

    def test_combined_stress_ratio_warning(self):
        """Test that high combined stress ratio generates warning."""
        designer = ColumnDesigner()

        steel = MaterialProperties(
            material_type=MaterialType.STEEL,
            yield_strength=50000.0,
            elastic_modulus=29000000.0,
            density=490.0,
        )

        geometry = ColumnGeometry(depth=8.0, width=8.0)
        loads = ColumnLoads(axial_load=150000.0, moment_x=100000.0)

        result = designer.design_column(
            length=120.0, loads=loads, material=steel, geometry=geometry
        )

        if result.combined_stress_ratio > 1.0:
            assert any(
                "combined stress" in w.lower() or "exceeds" in w.lower()
                for w in result.warnings
            )


class TestColumnDesignerCircularColumns:
    """Tests specifically for circular columns."""

    def test_circular_column_design(self):
        """Test circular column design."""
        designer = ColumnDesigner()

        steel = MaterialProperties(
            material_type=MaterialType.STEEL,
            yield_strength=50000.0,
            elastic_modulus=29000000.0,
            density=490.0,
            allowable_stress_factor=0.6,
        )

        geometry = ColumnGeometry(diameter=12.0)
        loads = ColumnLoads(axial_load=100000.0)

        result = designer.design_column(
            length=120.0, loads=loads, material=steel, geometry=geometry
        )

        assert result.axial_capacity > 0
        assert result.buckling_capacity > 0
        assert result.moment_capacity_x == result.moment_capacity_y

    def test_circular_vs_rectangular_same_area(self):
        """Test that circular column has similar buckling capacity."""
        designer = ColumnDesigner()

        steel = MaterialProperties(
            material_type=MaterialType.STEEL,
            yield_strength=50000.0,
            elastic_modulus=29000000.0,
            density=490.0,
        )

        # Same area: circle d=12 has A=113.1, square 10.64x10.64 has A=113.2
        circular = ColumnGeometry(diameter=12.0)
        rectangular = ColumnGeometry(depth=10.64, width=10.64)

        loads = ColumnLoads(axial_load=100000.0)

        result_circular = designer.design_column(
            length=120.0, loads=loads, material=steel, geometry=circular
        )

        result_rectangular = designer.design_column(
            length=120.0, loads=loads, material=steel, geometry=rectangular
        )

        # Both should have similar buckling capacity (within 1%)
        ratio = result_circular.buckling_capacity / result_rectangular.buckling_capacity
        assert 0.99 <= ratio <= 1.01
