"""
Load Calculator for structural engineering calculations.
Implements ASCE 7 standards for dead, live, wind, and seismic loads.
"""

import math
from dataclasses import dataclass
from enum import Enum
from typing import List


class OccupancyType(str, Enum):
    """Occupancy types per ASCE 7 Table 4.3-1."""

    RESIDENTIAL = "residential"
    OFFICE = "office"
    RETAIL = "retail"
    ASSEMBLY = "assembly"
    STORAGE_LIGHT = "storage_light"
    STORAGE_HEAVY = "storage_heavy"


@dataclass
class Component:
    """Building component for dead load calculation."""

    name: str
    weight_per_area: float  # psf (pounds per square foot)
    area: float  # square feet


@dataclass
class BuildingData:
    """Building geometry and properties."""

    height: float  # feet
    width: float  # feet
    length: float  # feet
    exposure_category: str  # B, C, or D per ASCE 7


@dataclass
class WindLoadResult:
    """Wind load calculation results."""

    design_pressure: float  # psf
    wind_speed: float  # mph
    exposure_category: str
    velocity_pressure: float  # psf


@dataclass
class SeismicData:
    """Seismic design parameters per ASCE 7."""

    ss: float  # Spectral acceleration at short periods
    s1: float  # Spectral acceleration at 1-second period
    site_class: str  # A, B, C, D, E, or F
    importance_factor: float  # Ie
    response_modification_factor: float  # R


@dataclass
class SeismicLoadResult:
    """Seismic load calculation results."""

    base_shear: float  # pounds
    seismic_design_category: str  # A, B, C, D, E, or F
    design_spectral_acceleration_short: float  # SDS
    design_spectral_acceleration_1s: float  # SD1


class LoadCalculator:
    """
    Calculator for structural loads per ASCE 7 standards.

    Implements:
    - Dead load calculations
    - Live load calculations (ASCE 7 Table 4.3-1)
    - Wind load calculations (ASCE 7 Chapter 27)
    - Seismic load calculations (ASCE 7 Chapter 12)
    """

    # Live load values per ASCE 7 Table 4.3-1 (psf)
    LIVE_LOAD_VALUES = {
        OccupancyType.RESIDENTIAL: 40.0,
        OccupancyType.OFFICE: 50.0,
        OccupancyType.RETAIL: 100.0,
        OccupancyType.ASSEMBLY: 100.0,
        OccupancyType.STORAGE_LIGHT: 125.0,
        OccupancyType.STORAGE_HEAVY: 250.0,
    }

    # Exposure coefficients for wind load (simplified)
    EXPOSURE_COEFFICIENTS = {
        "B": 0.70,  # Urban/suburban
        "C": 1.00,  # Open terrain
        "D": 1.15,  # Flat, unobstructed
    }

    # Site coefficients for seismic (simplified Fa values)
    SITE_COEFFICIENTS_SHORT = {
        "A": 0.8,
        "B": 1.0,
        "C": 1.2,
        "D": 1.6,
        "E": 2.5,
        "F": 2.5,
    }

    # Site coefficients for seismic (simplified Fv values)
    SITE_COEFFICIENTS_1S = {
        "A": 0.8,
        "B": 1.0,
        "C": 1.7,
        "D": 2.4,
        "E": 3.5,
        "F": 3.5,
    }

    def calculate_dead_load(self, components: List[Component]) -> float:
        """
        Calculate total dead load from building components.

        Args:
            components: List of building components with weight and area

        Returns:
            Total dead load in pounds

        Raises:
            ValueError: If any component has negative weight or area
        """
        if not components:
            return 0.0

        total_load = 0.0
        for component in components:
            if component.weight_per_area < 0:
                raise ValueError(
                    f"weight_per_area must be non-negative, got {component.weight_per_area}"
                )
            if component.area < 0:
                raise ValueError(f"area must be non-negative, got {component.area}")

            total_load += component.weight_per_area * component.area

        return total_load

    def calculate_live_load(self, occupancy: OccupancyType, area: float) -> float:
        """
        Calculate live load per ASCE 7 Table 4.3-1.

        Args:
            occupancy: Type of occupancy
            area: Floor area in square feet

        Returns:
            Total live load in pounds

        Raises:
            ValueError: If area is negative
        """
        if area < 0:
            raise ValueError(f"area must be non-negative, got {area}")

        if area == 0:
            return 0.0

        live_load_psf = self.LIVE_LOAD_VALUES[occupancy]
        return live_load_psf * area

    def calculate_wind_load(
        self, building: BuildingData, wind_speed: float
    ) -> WindLoadResult:
        """
        Calculate wind loads per ASCE 7 Chapter 27 (simplified method).

        Uses simplified equation: q = 0.00256 * Kz * Kzt * Kd * V^2
        where:
        - q = velocity pressure (psf)
        - Kz = velocity pressure exposure coefficient
        - Kzt = topographic factor (assumed 1.0)
        - Kd = wind directionality factor (assumed 0.85)
        - V = basic wind speed (mph)

        Args:
            building: Building geometry and exposure
            wind_speed: Basic wind speed in mph (3-second gust)

        Returns:
            WindLoadResult with design pressure and parameters

        Raises:
            ValueError: If wind_speed is negative or exposure category is invalid
        """
        if wind_speed <= 0:
            raise ValueError(f"wind_speed must be positive, got {wind_speed}")

        if building.exposure_category not in self.EXPOSURE_COEFFICIENTS:
            raise ValueError(
                f"Invalid exposure category: {building.exposure_category}. "
                f"Must be one of {list(self.EXPOSURE_COEFFICIENTS.keys())}"
            )

        # Get exposure coefficient
        kz = self.EXPOSURE_COEFFICIENTS[building.exposure_category]

        # Topographic factor (simplified, assume flat terrain)
        kzt = 1.0

        # Wind directionality factor
        kd = 0.85

        # Calculate velocity pressure: q = 0.00256 * Kz * Kzt * Kd * V^2
        velocity_pressure = 0.00256 * kz * kzt * kd * (wind_speed**2)

        # Design pressure (simplified, using pressure coefficient of 1.0)
        # In practice, this would use GCp values from ASCE 7
        design_pressure = velocity_pressure * 1.0

        return WindLoadResult(
            design_pressure=design_pressure,
            wind_speed=wind_speed,
            exposure_category=building.exposure_category,
            velocity_pressure=velocity_pressure,
        )

    def calculate_seismic_load(
        self, building: BuildingData, seismic_data: SeismicData
    ) -> SeismicLoadResult:
        """
        Calculate seismic loads per ASCE 7 Chapter 12 (simplified method).

        Uses equivalent lateral force procedure:
        - Calculate design spectral accelerations (SDS, SD1)
        - Determine seismic design category
        - Calculate base shear: V = Cs * W

        Args:
            building: Building geometry
            seismic_data: Seismic design parameters

        Returns:
            SeismicLoadResult with base shear and design category

        Raises:
            ValueError: If parameters are invalid
        """
        if seismic_data.ss < 0 or seismic_data.s1 < 0:
            raise ValueError(
                f"Spectral accelerations must be non-negative, "
                f"got Ss={seismic_data.ss}, S1={seismic_data.s1}"
            )

        if seismic_data.site_class not in self.SITE_COEFFICIENTS_SHORT:
            raise ValueError(
                f"Invalid site class: {seismic_data.site_class}. "
                f"Must be one of {list(self.SITE_COEFFICIENTS_SHORT.keys())}"
            )

        # Get site coefficients
        fa = self.SITE_COEFFICIENTS_SHORT[seismic_data.site_class]
        fv = self.SITE_COEFFICIENTS_1S[seismic_data.site_class]

        # Calculate maximum considered earthquake spectral accelerations
        sms = fa * seismic_data.ss
        sm1 = fv * seismic_data.s1

        # Calculate design spectral accelerations (2/3 of MCE)
        sds = (2.0 / 3.0) * sms
        sd1 = (2.0 / 3.0) * sm1

        # Determine seismic design category (simplified)
        sdc = self._determine_seismic_design_category(sds, sd1)

        # Estimate building weight (simplified: assume 100 psf)
        building_area = building.width * building.length
        building_weight = building_area * 100.0 * (building.height / 10.0)

        # Calculate seismic response coefficient Cs
        # Simplified: Cs = SDS / (R / Ie)
        cs = sds / (
            seismic_data.response_modification_factor / seismic_data.importance_factor
        )

        # Apply minimum and maximum limits
        cs_min = 0.01
        cs = max(cs, cs_min)

        # Calculate base shear
        base_shear = cs * building_weight

        return SeismicLoadResult(
            base_shear=base_shear,
            seismic_design_category=sdc,
            design_spectral_acceleration_short=sds,
            design_spectral_acceleration_1s=sd1,
        )

    def _determine_seismic_design_category(self, sds: float, sd1: float) -> str:
        """
        Determine seismic design category per ASCE 7 Table 11.6-1 and 11.6-2.

        Args:
            sds: Design spectral acceleration at short periods
            sd1: Design spectral acceleration at 1-second period

        Returns:
            Seismic design category (A, B, C, D, E, or F)
        """
        # Use the more conservative of the two checks
        if sds < 0.167:
            sdc_short = "A"
        elif sds < 0.33:
            sdc_short = "B"
        elif sds < 0.50:
            sdc_short = "C"
        elif sds < 0.75:
            sdc_short = "D"
        elif sds < 1.25:
            sdc_short = "E"
        else:
            sdc_short = "F"

        if sd1 < 0.067:
            sdc_1s = "A"
        elif sd1 < 0.133:
            sdc_1s = "B"
        elif sd1 < 0.20:
            sdc_1s = "C"
        elif sd1 < 0.30:
            sdc_1s = "D"
        elif sd1 < 0.50:
            sdc_1s = "E"
        else:
            sdc_1s = "F"

        # Return the more conservative (higher) category
        categories = ["A", "B", "C", "D", "E", "F"]
        idx_short = categories.index(sdc_short)
        idx_1s = categories.index(sdc_1s)

        return categories[max(idx_short, idx_1s)]
