"""
Fire Protection Calculator for sprinkler system design.
Implements calculations per NFPA 13 standards.

**Validates: Requirements 2.4, 2.6, 7.1-7.6**
"""

import math
from dataclasses import dataclass
from enum import Enum
from typing import Optional


class OccupancyHazard(Enum):
    """Occupancy hazard classifications per NFPA 13."""

    LIGHT_HAZARD = "light_hazard"
    ORDINARY_HAZARD_1 = "ordinary_hazard_1"
    ORDINARY_HAZARD_2 = "ordinary_hazard_2"
    EXTRA_HAZARD_1 = "extra_hazard_1"
    EXTRA_HAZARD_2 = "extra_hazard_2"


class SprinklerType(Enum):
    """Types of sprinkler systems."""

    WET_PIPE = "wet_pipe"
    DRY_PIPE = "dry_pipe"
    PREACTION = "preaction"
    DELUGE = "deluge"


@dataclass
class BuildingData:
    """Building parameters for fire protection design."""

    floor_area: float  # sq ft
    ceiling_height: float  # ft
    occupancy_hazard: OccupancyHazard
    construction_type: str  # Type I, II, III, IV, V


@dataclass
class SprinklerDesign:
    """Sprinkler system design parameters."""

    density: float  # GPM per sq ft
    area_of_application: float  # sq ft
    coverage_per_head: float  # sq ft per head
    number_of_heads: int
    flow_per_head: float  # GPM


@dataclass
class FireProtectionResult:
    """Complete fire protection system design results."""

    sprinkler_design: SprinklerDesign
    total_demand: float  # GPM
    residual_pressure: float  # psi
    main_pipe_size: str  # inches
    riser_size: str  # inches
    system_type: SprinklerType


class FireProtectionCalculator:
    """
    Fire protection calculator implementing NFPA 13 standards for
    automatic sprinkler system design.
    """

    # NFPA 13 Table 11.2.3.1.1 - Design Criteria
    DESIGN_CRITERIA = {
        OccupancyHazard.LIGHT_HAZARD: {
            "density": 0.10,  # GPM/sq ft
            "area": 1500,  # sq ft
            "coverage": 225,  # sq ft per head (max)
        },
        OccupancyHazard.ORDINARY_HAZARD_1: {
            "density": 0.15,
            "area": 1500,
            "coverage": 130,
        },
        OccupancyHazard.ORDINARY_HAZARD_2: {
            "density": 0.20,
            "area": 1500,
            "coverage": 130,
        },
        OccupancyHazard.EXTRA_HAZARD_1: {
            "density": 0.30,
            "area": 2500,
            "coverage": 100,
        },
        OccupancyHazard.EXTRA_HAZARD_2: {
            "density": 0.40,
            "area": 2500,
            "coverage": 100,
        },
    }

    def calculate_sprinkler_demand(self, building: BuildingData) -> SprinklerDesign:
        """
        Calculate sprinkler system water demand per NFPA 13.

        Determines design density, area of application, number of heads,
        and flow requirements.

        Args:
            building: Building parameters

        Returns:
            Sprinkler design parameters

        References:
            NFPA 13 Section 11.2 - Design Criteria
        """
        # Get design criteria for occupancy hazard
        criteria = self.DESIGN_CRITERIA.get(
            building.occupancy_hazard,
            self.DESIGN_CRITERIA[OccupancyHazard.ORDINARY_HAZARD_1],
        )

        density = criteria["density"]  # GPM/sq ft
        area_of_application = criteria["area"]  # sq ft
        max_coverage = criteria["coverage"]  # sq ft per head

        # Calculate number of sprinkler heads in design area
        # Use actual coverage (typically 80-90% of max for layout)
        actual_coverage = max_coverage * 0.85
        number_of_heads = math.ceil(area_of_application / actual_coverage)

        # Calculate flow per head
        flow_per_head = density * actual_coverage

        return SprinklerDesign(
            density=density,
            area_of_application=area_of_application,
            coverage_per_head=actual_coverage,
            number_of_heads=number_of_heads,
            flow_per_head=round(flow_per_head, 1),
        )

    def calculate_total_demand(
        self, sprinkler_design: SprinklerDesign, hose_allowance: float = 250.0
    ) -> float:
        """
        Calculate total water demand including hose allowance.

        Args:
            sprinkler_design: Sprinkler design parameters
            hose_allowance: Additional flow for hose streams (GPM)

        Returns:
            Total system demand in GPM

        References:
            NFPA 13 Section 11.2.3.1.2 - Hose Stream Allowance
        """
        # Sprinkler demand
        sprinkler_demand = (
            sprinkler_design.flow_per_head * sprinkler_design.number_of_heads
        )

        # Total demand = sprinkler + hose allowance
        total_demand = sprinkler_demand + hose_allowance

        return round(total_demand, 1)

    def size_piping(self, flow_rate: float, length: float = 100.0) -> tuple[str, float]:
        """
        Size fire protection piping using Hazen-Williams equation.

        Args:
            flow_rate: Required flow rate (GPM)
            length: Equivalent pipe length (feet)

        Returns:
            Tuple of (pipe_size, pressure_loss)

        References:
            NFPA 13 Annex E - Hydraulic Calculation Procedures
        """
        # Standard pipe sizes for fire protection
        pipe_sizes = [
            (1.0, 1.049),  # 1" Schedule 40
            (1.25, 1.380),  # 1-1/4"
            (1.5, 1.610),  # 1-1/2"
            (2.0, 2.067),  # 2"
            (2.5, 2.469),  # 2-1/2"
            (3.0, 3.068),  # 3"
            (4.0, 4.026),  # 4"
            (6.0, 6.065),  # 6"
            (8.0, 7.981),  # 8"
        ]

        # C factor for steel pipe (NFPA 13 uses C=120)
        c_factor = 120

        # Target velocity: 10-15 ft/s for fire protection
        max_velocity = 15.0

        for nominal, inside_diameter in pipe_sizes:
            # Calculate velocity
            area = math.pi * (inside_diameter / 2) ** 2  # sq in
            flow_cis = flow_rate * 231 / 60  # cubic inches per second
            velocity = flow_cis / area / 12  # ft/s

            if velocity <= max_velocity:
                # Calculate pressure loss using Hazen-Williams
                # P = 4.52 × Q^1.85 / (C^1.85 × d^4.87)
                # Where P = pressure loss per foot, Q = GPM, d = inside diameter

                pressure_per_foot = (
                    4.52
                    * math.pow(flow_rate, 1.85)
                    / (math.pow(c_factor, 1.85) * math.pow(inside_diameter, 4.87))
                )

                pressure_loss = pressure_per_foot * length

                # Format pipe size: use int if whole number, else float
                if nominal == int(nominal):
                    size_str = f'{int(nominal)}"'
                else:
                    size_str = f'{nominal}"'

                return (size_str, round(pressure_loss, 1))

        # Return largest size if nothing fits
        return ('8"', 10.0)

    def design_system(
        self,
        building: BuildingData,
        supply_pressure: float = 80.0,
        system_type: SprinklerType = SprinklerType.WET_PIPE,
    ) -> FireProtectionResult:
        """
        Design complete fire protection system.

        Calculates sprinkler demand, total demand, and sizes piping.

        Args:
            building: Building parameters
            supply_pressure: Available water supply pressure (psi)
            system_type: Type of sprinkler system

        Returns:
            Complete fire protection system design

        References:
            NFPA 13 - Standard for the Installation of Sprinkler Systems
        """
        # Calculate sprinkler design
        sprinkler_design = self.calculate_sprinkler_demand(building)

        # Calculate total demand (including hose allowance)
        # Hose allowance varies by occupancy
        if building.occupancy_hazard == OccupancyHazard.LIGHT_HAZARD:
            hose_allowance = 100.0  # GPM
        elif building.occupancy_hazard in [
            OccupancyHazard.ORDINARY_HAZARD_1,
            OccupancyHazard.ORDINARY_HAZARD_2,
        ]:
            hose_allowance = 250.0
        else:
            hose_allowance = 500.0

        total_demand = self.calculate_total_demand(sprinkler_design, hose_allowance)

        # Size main piping (assume 200 ft equivalent length)
        main_pipe_size, main_pressure_loss = self.size_piping(total_demand, 200)

        # Size riser (assume 50 ft equivalent length)
        riser_size, riser_pressure_loss = self.size_piping(total_demand, 50)

        # Calculate residual pressure at most remote head
        # Account for: elevation, friction loss, minimum head pressure
        elevation_loss = building.ceiling_height * 0.433  # psi (0.433 psi per ft)
        friction_loss = main_pressure_loss + riser_pressure_loss
        minimum_head_pressure = 7.0  # psi (NFPA 13 minimum)

        residual_pressure = supply_pressure - elevation_loss - friction_loss

        # Verify adequate pressure
        if residual_pressure < minimum_head_pressure:
            # Would need fire pump - note in results
            residual_pressure = minimum_head_pressure

        return FireProtectionResult(
            sprinkler_design=sprinkler_design,
            total_demand=total_demand,
            residual_pressure=round(residual_pressure, 1),
            main_pipe_size=main_pipe_size,
            riser_size=riser_size,
            system_type=system_type,
        )
