"""
Foundation Designer for structural engineering calculations.
Implements simplified foundation design methods based on geotechnical
engineering principles and building codes.
"""

import math
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional


class FoundationType(str, Enum):
    """Foundation types."""

    SPREAD_FOOTING = "spread_footing"
    CONTINUOUS_FOOTING = "continuous_footing"
    MAT_FOUNDATION = "mat_foundation"
    PILE_CAP = "pile_cap"


@dataclass
class SoilProperties:
    """Soil properties for foundation design."""

    bearing_capacity: float  # psf (allowable bearing capacity)
    unit_weight: float  # pcf (pounds per cubic foot)
    friction_angle: float  # degrees (internal friction angle φ)
    cohesion: float  # psf (soil cohesion c)
    elastic_modulus: Optional[float] = 5000.0  # psi (for settlement)


@dataclass
class FoundationLoads:
    """Loads applied to foundation."""

    vertical_load: float  # lb (dead + live loads)
    moment_x: float = 0.0  # lb-ft (moment about x-axis)
    moment_y: float = 0.0  # lb-ft (moment about y-axis)
    horizontal_x: float = 0.0  # lb (horizontal load in x-direction)
    horizontal_y: float = 0.0  # lb (horizontal load in y-direction)


@dataclass
class FoundationGeometry:
    """Foundation geometric properties."""

    foundation_type: FoundationType
    length: Optional[float] = None  # feet (for rectangular)
    width: Optional[float] = None  # feet (for rectangular)
    diameter: Optional[float] = None  # feet (for circular)
    depth: float = 2.0  # feet (depth below grade)
    thickness: Optional[float] = 18.0  # inches (footing thickness)

    @property
    def is_rectangular(self) -> bool:
        """Check if foundation is rectangular."""
        return self.length is not None and self.width is not None

    @property
    def is_circular(self) -> bool:
        """Check if foundation is circular."""
        return self.diameter is not None

    @property
    def area(self) -> float:
        """Calculate foundation area in square feet."""
        if self.is_circular:
            radius = self.diameter / 2.0
            return math.pi * radius**2
        elif self.is_rectangular:
            return self.length * self.width
        else:
            raise ValueError(
                "Invalid geometry: must specify either "
                "diameter or (length and width)"
            )


@dataclass
class FoundationDesignResult:
    """Results from foundation design analysis."""

    is_adequate: bool
    bearing_pressure: float  # psf (actual bearing pressure)
    allowable_bearing_capacity: float  # psf
    bearing_ratio: float  # actual/allowable
    settlement: float  # inches (estimated settlement)
    allowable_settlement: float  # inches
    reinforcement_area: float  # in² (required reinforcement)
    geometry: FoundationGeometry
    warnings: List[str]


class FoundationDesigner:
    """
    Designer for structural foundations.

    Implements simplified design methods for:
    - Spread footings (isolated and continuous)
    - Mat foundations
    - Pile caps

    Checks:
    - Bearing capacity
    - Settlement analysis
    - Reinforcement requirements
    """

    # Settlement limits
    ALLOWABLE_SETTLEMENT_TOTAL = 1.0  # inches (typical for buildings)
    ALLOWABLE_SETTLEMENT_DIFFERENTIAL = 0.5  # inches

    # Reinforcement limits (ACI 318)
    MIN_REINFORCEMENT_RATIO = 0.0018  # minimum steel ratio
    CONCRETE_STRENGTH = 3000.0  # psi (f'c)
    STEEL_YIELD = 60000.0  # psi (fy)

    # Safety factors
    BEARING_CAPACITY_SAFETY_FACTOR = 3.0
    SETTLEMENT_SAFETY_FACTOR = 1.5

    def design_foundation(
        self,
        loads: FoundationLoads,
        soil_properties: SoilProperties,
        geometry: FoundationGeometry,
    ) -> FoundationDesignResult:
        """
        Design or check a foundation for given loads and soil conditions.

        Args:
            loads: Applied loads on foundation
            soil_properties: Soil properties
            geometry: Foundation geometry

        Returns:
            FoundationDesignResult with adequacy check and design details

        Raises:
            ValueError: If inputs are invalid
        """
        if loads.vertical_load < 0:
            raise ValueError(
                f"vertical_load must be non-negative, " f"got {loads.vertical_load}"
            )

        if geometry.area <= 0:
            raise ValueError("Foundation area must be positive")

        warnings = []

        # Calculate bearing pressure
        bearing_pressure = self._calculate_bearing_pressure(
            loads, geometry.area, geometry
        )

        # Calculate allowable bearing capacity
        allowable_capacity = self._calculate_allowable_bearing_capacity(
            soil_properties, geometry
        )

        # Calculate bearing ratio
        bearing_ratio = bearing_pressure / allowable_capacity

        # Calculate settlement
        settlement = self._calculate_settlement(loads, soil_properties, geometry)

        # Calculate reinforcement
        reinforcement_area = self._calculate_reinforcement(loads, geometry)

        # Check for warnings
        if bearing_ratio > 0.9:
            warnings.append(
                f"Bearing pressure ({bearing_pressure:.0f} psf) is "
                f"{bearing_ratio * 100:.1f}% of allowable capacity"
            )

        if bearing_ratio > 1.0:
            warnings.append(
                f"Bearing capacity exceeded by " f"{(bearing_ratio - 1.0) * 100:.1f}%"
            )

        if settlement > self.ALLOWABLE_SETTLEMENT_TOTAL:
            warnings.append(
                f"Settlement ({settlement:.2f} in) exceeds allowable "
                f"({self.ALLOWABLE_SETTLEMENT_TOTAL:.2f} in)"
            )

        # Check for eccentric loading
        if loads.moment_x != 0 or loads.moment_y != 0:
            eccentricity_x = (
                abs(loads.moment_x) * 12.0 / loads.vertical_load
                if loads.vertical_load > 0
                else 0
            )
            eccentricity_y = (
                abs(loads.moment_y) * 12.0 / loads.vertical_load
                if loads.vertical_load > 0
                else 0
            )

            if geometry.is_rectangular:
                # L/6 limit
                max_ecc_x = geometry.length * 12.0 / 6.0
                # B/6 limit
                max_ecc_y = geometry.width * 12.0 / 6.0

                if eccentricity_x > max_ecc_x or eccentricity_y > max_ecc_y:
                    warnings.append(
                        "Eccentric loading exceeds L/6 or B/6 limit - "
                        "tension may develop"
                    )
                elif (
                    eccentricity_x > max_ecc_x * 0.5 or eccentricity_y > max_ecc_y * 0.5
                ):
                    warnings.append(
                        "Significant eccentric loading detected - "
                        "consider larger footing"
                    )

        # Determine adequacy
        is_adequate = (
            bearing_ratio <= 1.0 and settlement <= self.ALLOWABLE_SETTLEMENT_TOTAL
        )

        return FoundationDesignResult(
            is_adequate=is_adequate,
            bearing_pressure=bearing_pressure,
            allowable_bearing_capacity=allowable_capacity,
            bearing_ratio=bearing_ratio,
            settlement=settlement,
            allowable_settlement=self.ALLOWABLE_SETTLEMENT_TOTAL,
            reinforcement_area=reinforcement_area,
            geometry=geometry,
            warnings=warnings,
        )

    def _calculate_bearing_pressure(
        self,
        loads: FoundationLoads,
        area: float,
        geometry: FoundationGeometry,
    ) -> float:
        """
        Calculate bearing pressure including eccentric loading effects.

        For concentric loading: q = P/A
        For eccentric loading: q_max = P/A * (1 + 6e/L)
        """
        if area == 0:
            return float("inf")

        # Base pressure
        base_pressure = loads.vertical_load / area

        # Check for moments (eccentric loading)
        if loads.moment_x == 0 and loads.moment_y == 0:
            return base_pressure

        # Calculate eccentricities (in feet)
        e_x = (
            abs(loads.moment_x) / loads.vertical_load if loads.vertical_load > 0 else 0
        )
        e_y = (
            abs(loads.moment_y) / loads.vertical_load if loads.vertical_load > 0 else 0
        )

        # For rectangular footings, use eccentric loading formula
        if geometry.is_rectangular:
            # Maximum pressure occurs at corner
            # q_max = P/A * (1 + 6*e_x/L + 6*e_y/B)
            factor_x = 1.0 + (6.0 * e_x / geometry.length)
            factor_y = 1.0 + (6.0 * e_y / geometry.width)

            # Combined effect (simplified)
            max_pressure = base_pressure * factor_x * factor_y

            return max_pressure
        else:
            # For circular footings, use simplified approach
            # Increase pressure by 20% for eccentric loading
            if e_x > 0 or e_y > 0:
                return base_pressure * 1.2
            return base_pressure

    def _calculate_allowable_bearing_capacity(
        self, soil: SoilProperties, geometry: FoundationGeometry
    ) -> float:
        """
        Calculate allowable bearing capacity with depth adjustment.

        Uses Terzaghi's bearing capacity equation (simplified):
        q_ult = c*Nc + γ*D*Nq + 0.5*γ*B*Nγ
        q_allow = q_ult / FS + γ*D (surcharge)
        """
        # Start with provided soil bearing capacity
        base_capacity = soil.bearing_capacity

        # Add surcharge from depth of foundation
        # q_surcharge = γ * D
        surcharge = soil.unit_weight * geometry.depth

        # Depth factor (simplified): increases capacity by ~10% per foot
        depth_factor = 1.0 + (0.1 * geometry.depth)

        # Apply depth factor to base capacity
        adjusted_capacity = base_capacity * depth_factor + surcharge

        return adjusted_capacity

    def _calculate_settlement(
        self,
        loads: FoundationLoads,
        soil: SoilProperties,
        geometry: FoundationGeometry,
    ) -> float:
        """
        Calculate estimated settlement using elastic theory.

        Settlement = q * B * (1 - ν²) / E_s * I_f

        Where:
        - q = bearing pressure
        - B = foundation width
        - ν = Poisson's ratio (assumed 0.3)
        - E_s = soil elastic modulus
        - I_f = influence factor (assumed 1.0 for center)
        """
        # Calculate bearing pressure
        bearing_pressure = loads.vertical_load / geometry.area

        # Get characteristic dimension
        # (width for rectangular, diameter for circular)
        if geometry.is_rectangular:
            char_dimension = min(geometry.length, geometry.width)
        else:
            char_dimension = geometry.diameter

        # Convert to inches
        char_dimension_inches = char_dimension * 12.0

        # Poisson's ratio for soil (typical value)
        poisson_ratio = 0.3

        # Elastic modulus (use provided or default)
        elastic_modulus = soil.elastic_modulus if soil.elastic_modulus else 5000.0

        # Influence factor (simplified, typically 0.8-1.2)
        influence_factor = 1.0

        # Settlement calculation (simplified elastic theory)
        # S = q * B * (1 - ν²) / E_s * I_f
        # Convert bearing pressure from psf to psi
        bearing_pressure_psi = bearing_pressure / 144.0

        settlement = (
            bearing_pressure_psi
            * char_dimension_inches
            * (1.0 - poisson_ratio**2)
            / elastic_modulus
            * influence_factor
        )

        return settlement

    def _calculate_reinforcement(
        self, loads: FoundationLoads, geometry: FoundationGeometry
    ) -> float:
        """
        Calculate required reinforcement area for foundation.

        Uses simplified flexural design:
        M = q * a² / 2 (for cantilever from column face)
        A_s = M / (φ * f_y * d)

        Where:
        - M = moment
        - a = cantilever projection
        - φ = strength reduction factor (0.9)
        - f_y = steel yield strength
        - d = effective depth
        """
        # Calculate bearing pressure
        bearing_pressure = loads.vertical_load / geometry.area

        # Assume column is centered and has width of 1/4 of footing
        # Cantilever projection from column face
        if geometry.is_rectangular:
            # feet
            cantilever_length = (geometry.length - geometry.length / 4.0) / 2.0
            width = geometry.width  # feet
        else:
            # feet
            cantilever_length = (geometry.diameter - geometry.diameter / 4.0) / 2.0
            width = geometry.diameter  # feet

        # Calculate moment per unit width
        # M = q * a² / 2 (lb-ft per foot width)
        moment_per_ft = bearing_pressure * width * cantilever_length**2 / 2.0

        # Convert to lb-in per foot width
        moment_lb_in = moment_per_ft * 12.0

        # Effective depth (assume 3" cover)
        thickness_inches = geometry.thickness if geometry.thickness else 18.0
        effective_depth = thickness_inches - 3.0  # inches

        # Strength reduction factor
        phi = 0.9

        # Required steel area per foot width
        # A_s = M / (φ * f_y * d)
        if effective_depth > 0:
            required_area_per_ft = moment_lb_in / (
                phi * self.STEEL_YIELD * effective_depth
            )
        else:
            required_area_per_ft = 0.0

        # Check minimum reinforcement per foot width
        # A_s,min = ρ_min * b * d (where b = 12" for per foot width)
        min_area_per_ft = self.MIN_REINFORCEMENT_RATIO * 12.0 * effective_depth

        # Return the larger of required or minimum (per foot width)
        return max(required_area_per_ft, min_area_per_ft)
