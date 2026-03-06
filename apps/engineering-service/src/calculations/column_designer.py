"""
Column Designer for structural engineering calculations.
Implements AISC 360 (steel) and ACI 318 (concrete) column design methods.
"""

import math
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional


class MaterialType(str, Enum):
    """Material types for column design."""

    STEEL = "steel"
    CONCRETE = "concrete"


class EndCondition(str, Enum):
    """Column end conditions for buckling analysis."""

    FIXED_FIXED = "fixed_fixed"  # K = 0.5
    FIXED_PINNED = "fixed_pinned"  # K = 0.7
    PINNED_PINNED = "pinned_pinned"  # K = 1.0
    FIXED_FREE = "fixed_free"  # K = 2.0 (cantilever)


@dataclass
class MaterialProperties:
    """Material properties for column design."""

    material_type: MaterialType
    yield_strength: float  # psi (steel Fy) or f'c (concrete)
    elastic_modulus: float  # psi
    density: float  # lb/ft³
    allowable_stress_factor: float = 0.6  # Factor of safety


@dataclass
class ColumnLoads:
    """Loads applied to column."""

    axial_load: float  # lb (compression positive)
    moment_x: float = 0.0  # lb-in (moment about x-axis)
    moment_y: float = 0.0  # lb-in (moment about y-axis)


@dataclass
class ColumnGeometry:
    """Column geometric properties."""

    depth: Optional[float] = None  # inches (for rectangular)
    width: Optional[float] = None  # inches (for rectangular)
    diameter: Optional[float] = None  # inches (for circular)

    @property
    def is_rectangular(self) -> bool:
        """Check if column is rectangular section."""
        return self.depth is not None and self.width is not None

    @property
    def is_circular(self) -> bool:
        """Check if column is circular section."""
        return self.diameter is not None

    @property
    def area(self) -> float:
        """Calculate cross-sectional area in square inches."""
        if self.is_circular:
            radius = self.diameter / 2.0
            return math.pi * radius**2
        elif self.is_rectangular:
            return self.width * self.depth
        else:
            raise ValueError(
                "Invalid geometry: must specify either " "diameter or (depth and width)"
            )

    @property
    def moment_of_inertia(self) -> float:
        """Calculate minimum moment of inertia (weak axis) in in⁴."""
        if self.is_circular:
            # I = π * d⁴ / 64
            return math.pi * self.diameter**4 / 64.0
        elif self.is_rectangular:
            # I_min = bd³/12 where d is the smaller dimension
            min_dim = min(self.depth, self.width)
            max_dim = max(self.depth, self.width)
            return (max_dim * min_dim**3) / 12.0
        else:
            raise ValueError("Invalid geometry")

    @property
    def radius_of_gyration(self) -> float:
        """Calculate radius of gyration r = sqrt(I/A) in inches."""
        if self.is_circular:
            # r = d/4 for circular section
            return self.diameter / 4.0
        elif self.is_rectangular:
            # r = sqrt(I/A) = min_dim / sqrt(12)
            min_dim = min(self.depth, self.width)
            return min_dim / math.sqrt(12.0)
        else:
            raise ValueError("Invalid geometry")

    def section_modulus(self, axis: str = "x") -> float:
        """Calculate section modulus S = I/c in in³."""
        if self.is_circular:
            # S = π * d³ / 32 (same for both axes)
            return math.pi * self.diameter**3 / 32.0
        elif self.is_rectangular:
            # S = bd²/6
            if axis == "x":
                # Bending about x-axis (depth is perpendicular)
                return (self.width * self.depth**2) / 6.0
            else:
                # Bending about y-axis (width is perpendicular)
                return (self.depth * self.width**2) / 6.0
        else:
            raise ValueError("Invalid geometry")


@dataclass
class ColumnDesignResult:
    """Results from column design analysis."""

    is_adequate: bool
    axial_capacity: float  # lb
    buckling_capacity: float  # lb
    moment_capacity_x: float  # lb-in
    moment_capacity_y: float  # lb-in
    combined_stress_ratio: float  # P/Pn + Mx/Mnx + My/Mny
    slenderness_ratio: float  # KL/r
    effective_length: float  # inches
    geometry: ColumnGeometry
    warnings: List[str]

    @property
    def governing_capacity(self) -> float:
        """Return the governing (minimum) capacity."""
        return min(self.axial_capacity, self.buckling_capacity)


class ColumnDesigner:
    """
    Designer for structural columns.

    Implements simplified design methods for:
    - Steel columns (AISC 360 principles)
    - Concrete columns (ACI 318 principles)

    Checks:
    - Axial capacity (compression)
    - Buckling resistance (Euler buckling)
    - Combined stress ratios (P/Pn + M/Mn)
    - Slenderness limits
    """

    # Slenderness limits
    MAX_SLENDERNESS_STEEL = 200.0  # KL/r limit for steel
    MAX_SLENDERNESS_CONCRETE = 100.0  # KL/r limit for concrete

    def design_column(
        self,
        length: float,  # inches
        loads: ColumnLoads,
        material: MaterialProperties,
        geometry: ColumnGeometry,
        end_condition: EndCondition = EndCondition.PINNED_PINNED,
    ) -> ColumnDesignResult:
        """
        Design or check a column for given loads and length.

        Args:
            length: Column length in inches
            loads: Applied loads on column
            material: Material properties
            geometry: Column geometry
            end_condition: End support conditions

        Returns:
            ColumnDesignResult with adequacy check and design details

        Raises:
            ValueError: If inputs are invalid
        """
        if length <= 0:
            raise ValueError(f"length must be positive, got {length}")

        if loads.axial_load < 0:
            raise ValueError(f"axial_load must be non-negative, got {loads.axial_load}")

        warnings = []

        # Get effective length factor
        k_factor = self._get_effective_length_factor(end_condition)
        effective_length = k_factor * length

        # Calculate slenderness ratio
        slenderness = self._calculate_slenderness_ratio(geometry, length, k_factor)

        # Check slenderness limits
        max_slenderness = (
            self.MAX_SLENDERNESS_STEEL
            if material.material_type == MaterialType.STEEL
            else self.MAX_SLENDERNESS_CONCRETE
        )

        if slenderness > max_slenderness:
            warnings.append(
                f"Slenderness ratio ({slenderness:.1f}) exceeds "
                f"maximum ({max_slenderness:.1f}) - column is very slender"
            )

        # Calculate capacities
        axial_capacity = self._calculate_axial_capacity(geometry, material)
        buckling_capacity = self._calculate_buckling_capacity(
            geometry, material, length, end_condition
        )
        moment_capacity_x = self._calculate_moment_capacity(
            geometry, material, axis="x"
        )
        moment_capacity_y = self._calculate_moment_capacity(
            geometry, material, axis="y"
        )

        # Calculate combined stress ratio
        combined_ratio = self._calculate_combined_stress_ratio(
            loads, buckling_capacity, moment_capacity_x, moment_capacity_y
        )

        # Check adequacy
        is_adequate = combined_ratio <= 1.0

        if combined_ratio > 1.0:
            warnings.append(
                f"Combined stress ratio ({combined_ratio:.2f}) exceeds "
                f"1.0 by {(combined_ratio - 1.0) * 100:.1f}%"
            )

        if loads.axial_load > buckling_capacity:
            warnings.append(
                f"Axial load ({loads.axial_load:.0f} lb) exceeds "
                f"buckling capacity ({buckling_capacity:.0f} lb)"
            )

        return ColumnDesignResult(
            is_adequate=is_adequate,
            axial_capacity=axial_capacity,
            buckling_capacity=buckling_capacity,
            moment_capacity_x=moment_capacity_x,
            moment_capacity_y=moment_capacity_y,
            combined_stress_ratio=combined_ratio,
            slenderness_ratio=slenderness,
            effective_length=effective_length,
            geometry=geometry,
            warnings=warnings,
        )

    def _get_effective_length_factor(self, end_condition: EndCondition) -> float:
        """Get effective length factor K based on end conditions."""
        k_factors = {
            EndCondition.FIXED_FIXED: 0.5,
            EndCondition.FIXED_PINNED: 0.7,
            EndCondition.PINNED_PINNED: 1.0,
            EndCondition.FIXED_FREE: 2.0,
        }
        return k_factors[end_condition]

    def _calculate_slenderness_ratio(
        self, geometry: ColumnGeometry, length: float, k_factor: float
    ) -> float:
        """Calculate slenderness ratio λ = KL/r."""
        r = geometry.radius_of_gyration
        return (k_factor * length) / r

    def _calculate_axial_capacity(
        self, geometry: ColumnGeometry, material: MaterialProperties
    ) -> float:
        """Calculate axial capacity (without buckling consideration)."""
        area = geometry.area
        allowable_stress = material.yield_strength * material.allowable_stress_factor
        return area * allowable_stress

    def _calculate_euler_buckling_load(
        self,
        geometry: ColumnGeometry,
        material: MaterialProperties,
        length: float,
        k_factor: float,
    ) -> float:
        """Calculate Euler critical buckling load P_cr = π²EI/(KL)²."""
        E = material.elastic_modulus
        I = geometry.moment_of_inertia
        KL = k_factor * length

        if KL == 0:
            return float("inf")

        return (math.pi**2 * E * I) / (KL**2)

    def _calculate_buckling_capacity(
        self,
        geometry: ColumnGeometry,
        material: MaterialProperties,
        length: float,
        end_condition: EndCondition,
    ) -> float:
        """Calculate buckling capacity with safety factor."""
        k_factor = self._get_effective_length_factor(end_condition)
        pcr = self._calculate_euler_buckling_load(geometry, material, length, k_factor)

        # Apply safety factor (typically 1.67 for buckling)
        safety_factor = 1.67
        allowable_buckling = pcr / safety_factor

        # Also check against material yield
        axial_capacity = self._calculate_axial_capacity(geometry, material)

        # Return the minimum (governing capacity)
        return min(allowable_buckling, axial_capacity)

    def _calculate_moment_capacity(
        self,
        geometry: ColumnGeometry,
        material: MaterialProperties,
        axis: str = "x",
    ) -> float:
        """Calculate moment capacity M = F_y * S * factor."""
        section_modulus = geometry.section_modulus(axis)
        allowable_stress = material.yield_strength * material.allowable_stress_factor
        return section_modulus * allowable_stress

    def _calculate_combined_stress_ratio(
        self,
        loads: ColumnLoads,
        axial_capacity: float,
        moment_capacity_x: float,
        moment_capacity_y: float,
    ) -> float:
        """
        Calculate combined stress ratio per AISC interaction equation.
        Ratio = P/Pn + Mx/Mnx + My/Mny
        """
        # Avoid division by zero
        if axial_capacity == 0:
            axial_ratio = float("inf") if loads.axial_load > 0 else 0.0
        else:
            axial_ratio = loads.axial_load / axial_capacity

        if moment_capacity_x == 0:
            moment_ratio_x = float("inf") if loads.moment_x > 0 else 0.0
        else:
            moment_ratio_x = abs(loads.moment_x) / moment_capacity_x

        if moment_capacity_y == 0:
            moment_ratio_y = float("inf") if loads.moment_y > 0 else 0.0
        else:
            moment_ratio_y = abs(loads.moment_y) / moment_capacity_y

        return axial_ratio + moment_ratio_x + moment_ratio_y
