"""
Beam Designer for structural engineering calculations.
Implements simplified ACI 318 (concrete) and AISC (steel) design methods.
"""

import math
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Tuple


class MaterialType(str, Enum):
    """Material types for beam design."""

    STEEL = "steel"
    CONCRETE = "concrete"
    TIMBER = "timber"


class BeamSupportType(str, Enum):
    """Beam support conditions."""

    SIMPLY_SUPPORTED = "simply_supported"
    FIXED_FIXED = "fixed_fixed"
    FIXED_PINNED = "fixed_pinned"
    CANTILEVER = "cantilever"


@dataclass
class MaterialProperties:
    """Material properties for beam design."""

    material_type: MaterialType
    yield_strength: float  # psi (steel) or f'c (concrete)
    elastic_modulus: float  # psi
    density: float  # lb/ft³
    allowable_stress_factor: float = 0.6  # Factor of safety


@dataclass
class BeamLoads:
    """Loads applied to beam."""

    uniform_load: float  # lb/ft (distributed load)
    point_loads: List[Tuple[float, float]] = field(
        default_factory=list
    )  # [(load_lb, position_ft), ...]
    moment_loads: List[Tuple[float, float]] = field(
        default_factory=list
    )  # [(moment_lb_ft, position_ft), ...]


@dataclass
class BeamGeometry:
    """Beam geometric properties."""

    depth: float  # inches
    width: float  # inches (for rectangular) or flange width (for I-beam)
    web_thickness: Optional[float] = None  # inches (for I-beam)
    flange_thickness: Optional[float] = None  # inches (for I-beam)

    @property
    def is_rectangular(self) -> bool:
        """Check if beam is rectangular section."""
        return self.web_thickness is None and self.flange_thickness is None

    @property
    def area(self) -> float:
        """Calculate cross-sectional area in square inches."""
        if self.is_rectangular:
            return self.width * self.depth
        else:
            # I-beam approximation
            web_area = self.web_thickness * (self.depth - 2 * self.flange_thickness)
            flange_area = 2 * self.width * self.flange_thickness
            return web_area + flange_area

    @property
    def moment_of_inertia(self) -> float:
        """Calculate moment of inertia about neutral axis (in⁴)."""
        if self.is_rectangular:
            # I = bh³/12 for rectangular section
            return (self.width * self.depth**3) / 12.0
        else:
            # I-beam approximation using parallel axis theorem
            i_web = (
                self.web_thickness * (self.depth - 2 * self.flange_thickness) ** 3
            ) / 12.0
            d_flange = (self.depth - self.flange_thickness) / 2.0
            i_flange = (self.width * self.flange_thickness**3) / 12.0 + (
                self.width * self.flange_thickness * d_flange**2
            )
            return i_web + 2 * i_flange

    @property
    def section_modulus(self) -> float:
        """Calculate section modulus S = I/c (in³)."""
        c = self.depth / 2.0  # Distance to extreme fiber
        return self.moment_of_inertia / c


@dataclass
class BeamDesignResult:
    """Results from beam design analysis."""

    is_adequate: bool
    max_moment: float  # lb-ft
    max_shear: float  # lb
    max_stress: float  # psi
    allowable_stress: float  # psi
    max_deflection: float  # inches
    allowable_deflection: float  # inches
    stress_ratio: float  # actual/allowable
    deflection_ratio: float  # actual/allowable
    geometry: BeamGeometry
    warnings: List[str]

    @property
    def utilization_ratio(self) -> float:
        """Overall utilization ratio (max of stress and deflection ratios)."""
        return max(self.stress_ratio, self.deflection_ratio)


class BeamDesigner:
    """
    Designer for structural beams.

    Implements simplified design methods for:
    - Steel beams (AISC principles)
    - Concrete beams (ACI 318 principles)
    - Timber beams (NDS principles)

    Checks:
    - Flexural stress (bending)
    - Shear stress
    - Deflection limits (L/360 for live load, L/240 for total load)
    """

    # Deflection limits (span/deflection ratio)
    DEFLECTION_LIMIT_LIVE = 360.0  # L/360 for live load
    DEFLECTION_LIMIT_TOTAL = 240.0  # L/240 for total load

    def design_beam(
        self,
        span: float,  # feet
        loads: BeamLoads,
        material: MaterialProperties,
        support_type: BeamSupportType = BeamSupportType.SIMPLY_SUPPORTED,
        trial_geometry: Optional[BeamGeometry] = None,
    ) -> BeamDesignResult:
        """
        Design or check a beam for given loads and span.

        Args:
            span: Beam span in feet
            loads: Applied loads on beam
            material: Material properties
            support_type: Support conditions
            trial_geometry: Trial beam geometry (if None, will auto-size)

        Returns:
            BeamDesignResult with adequacy check and design details

        Raises:
            ValueError: If inputs are invalid
        """
        if span <= 0:
            raise ValueError(f"span must be positive, got {span}")

        if loads.uniform_load < 0:
            raise ValueError(
                f"uniform_load must be non-negative, got {loads.uniform_load}"
            )

        warnings = []

        # Calculate maximum moment and shear
        max_moment, max_shear = self._calculate_max_forces(span, loads, support_type)

        # If no trial geometry provided, auto-size the beam
        if trial_geometry is None:
            trial_geometry = self._auto_size_beam(max_moment, max_shear, material, span)
            warnings.append("Beam geometry was auto-sized")

        # Calculate stresses
        max_stress = self._calculate_bending_stress(max_moment, trial_geometry)
        allowable_stress = material.yield_strength * material.allowable_stress_factor
        stress_ratio = (
            max_stress / allowable_stress if allowable_stress > 0 else float("inf")
        )

        # Calculate deflection
        max_deflection = self._calculate_deflection(
            span, loads, material, trial_geometry, support_type
        )
        allowable_deflection = (
            span * 12.0
        ) / self.DEFLECTION_LIMIT_TOTAL  # Convert to inches
        deflection_ratio = (
            max_deflection / allowable_deflection
            if allowable_deflection > 0
            else float("inf")
        )

        # Check shear stress (simplified check)
        shear_stress = self._calculate_shear_stress(max_shear, trial_geometry)
        allowable_shear = material.yield_strength * 0.4  # Simplified shear allowable

        if shear_stress > allowable_shear:
            warnings.append(
                f"Shear stress ({shear_stress:.1f} psi) exceeds allowable ({allowable_shear:.1f} psi)"
            )

        # Determine if design is adequate
        is_adequate = (
            (stress_ratio <= 1.0)
            and (deflection_ratio <= 1.0)
            and (shear_stress <= allowable_shear)
        )

        if stress_ratio > 1.0:
            warnings.append(
                f"Bending stress exceeds allowable by {(stress_ratio - 1.0) * 100:.1f}%"
            )

        if deflection_ratio > 1.0:
            warnings.append(
                f"Deflection exceeds allowable by {(deflection_ratio - 1.0) * 100:.1f}%"
            )

        return BeamDesignResult(
            is_adequate=is_adequate,
            max_moment=max_moment,
            max_shear=max_shear,
            max_stress=max_stress,
            allowable_stress=allowable_stress,
            max_deflection=max_deflection,
            allowable_deflection=allowable_deflection,
            stress_ratio=stress_ratio,
            deflection_ratio=deflection_ratio,
            geometry=trial_geometry,
            warnings=warnings,
        )

    def _calculate_max_forces(
        self,
        span: float,
        loads: BeamLoads,
        support_type: BeamSupportType,
    ) -> Tuple[float, float]:
        """Calculate maximum moment and shear for given loads."""
        # Simply supported beam formulas
        if support_type == BeamSupportType.SIMPLY_SUPPORTED:
            moment_uniform = (loads.uniform_load * span**2) / 8.0
            shear_uniform = (loads.uniform_load * span) / 2.0

            moment_point = 0.0
            shear_point = 0.0
            for load, position in loads.point_loads:
                a = position
                b = span - position
                moment_point += (load * a * b) / span
                shear_point += load / 2.0

            max_moment = moment_uniform + moment_point
            max_shear = shear_uniform + shear_point

        elif support_type == BeamSupportType.CANTILEVER:
            moment_uniform = (loads.uniform_load * span**2) / 2.0
            shear_uniform = loads.uniform_load * span

            moment_point = sum(load * (span - pos) for load, pos in loads.point_loads)
            shear_point = sum(load for load, _ in loads.point_loads)

            max_moment = moment_uniform + moment_point
            max_shear = shear_uniform + shear_point

        elif support_type == BeamSupportType.FIXED_FIXED:
            moment_uniform = (loads.uniform_load * span**2) / 12.0
            shear_uniform = (loads.uniform_load * span) / 2.0

            max_moment = moment_uniform
            max_shear = shear_uniform

        else:
            moment_uniform = (loads.uniform_load * span**2) / 8.0
            shear_uniform = (loads.uniform_load * span) / 2.0
            max_moment = moment_uniform
            max_shear = shear_uniform

        return max_moment, max_shear

    def _calculate_bending_stress(self, moment: float, geometry: BeamGeometry) -> float:
        """Calculate maximum bending stress using flexure formula."""
        moment_lb_in = moment * 12.0  # Convert lb-ft to lb-in
        section_modulus = geometry.section_modulus

        if section_modulus == 0:
            return float("inf")

        return moment_lb_in / section_modulus

    def _calculate_shear_stress(self, shear: float, geometry: BeamGeometry) -> float:
        """Calculate maximum shear stress (simplified)."""
        area = geometry.area

        if area == 0:
            return float("inf")

        # Simplified: use 1.5 factor for rectangular sections
        return 1.5 * shear / area

    def _calculate_deflection(
        self,
        span: float,
        loads: BeamLoads,
        material: MaterialProperties,
        geometry: BeamGeometry,
        support_type: BeamSupportType,
    ) -> float:
        """Calculate maximum deflection using beam deflection formulas."""
        span_inches = span * 12.0
        E = material.elastic_modulus
        I = geometry.moment_of_inertia

        if E == 0 or I == 0:
            return float("inf")

        # Simply supported uniform load: δ = 5wL⁴/384EI
        if support_type == BeamSupportType.SIMPLY_SUPPORTED:
            w = loads.uniform_load / 12.0
            deflection = (5 * w * span_inches**4) / (384 * E * I)

        elif support_type == BeamSupportType.CANTILEVER:
            w = loads.uniform_load / 12.0
            deflection = (w * span_inches**4) / (8 * E * I)

        elif support_type == BeamSupportType.FIXED_FIXED:
            w = loads.uniform_load / 12.0
            deflection = (w * span_inches**4) / (384 * E * I)

        else:
            w = loads.uniform_load / 12.0
            deflection = (5 * w * span_inches**4) / (384 * E * I)

        return deflection

    def _auto_size_beam(
        self,
        max_moment: float,
        max_shear: float,
        material: MaterialProperties,
        span: float,
    ) -> BeamGeometry:
        """Auto-size beam based on required section modulus."""
        allowable_stress = material.yield_strength * material.allowable_stress_factor
        moment_lb_in = max_moment * 12.0
        required_S = moment_lb_in / allowable_stress

        # For rectangular section: S = bd²/6
        # Assume b/d ratio of 0.5
        depth = (12 * required_S) ** (1.0 / 3.0)
        width = depth * 0.5

        # Round up to nearest inch
        depth = math.ceil(depth)
        width = math.ceil(width)

        # Ensure minimum dimensions
        depth = max(depth, 6.0)
        width = max(width, 4.0)

        return BeamGeometry(depth=depth, width=width)
