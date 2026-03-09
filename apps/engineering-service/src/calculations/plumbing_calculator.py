"""
Plumbing Calculator for fixture units, pipe sizing, and water supply calculations.
Implements calculations per IPC (International Plumbing Code) standards.

**Validates: Requirements 2.3, 2.6, 7.1-7.6**
"""

import math
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List


class FixtureType(Enum):
    """Types of plumbing fixtures per IPC."""

    WATER_CLOSET = "water_closet"
    LAVATORY = "lavatory"
    BATHTUB = "bathtub"
    SHOWER = "shower"
    KITCHEN_SINK = "kitchen_sink"
    LAUNDRY = "laundry"
    DISHWASHER = "dishwasher"
    URINAL = "urinal"
    DRINKING_FOUNTAIN = "drinking_fountain"


@dataclass
class Fixture:
    """Plumbing fixture definition."""

    name: str
    fixture_type: FixtureType
    quantity: int = 1
    private: bool = True  # Private vs public use


@dataclass
class PipeSize:
    """Pipe sizing results."""

    nominal_size: str  # inches
    flow_rate: float  # GPM
    velocity: float  # ft/s
    friction_loss: float  # psi per 100 ft


@dataclass
class WaterSupplyResult:
    """Water supply system sizing results."""

    total_fixture_units: float
    peak_demand: float  # GPM
    service_size: str  # inches
    meter_size: str  # inches
    supply_pressure_required: float  # psi


class PlumbingCalculator:
    """
    Plumbing calculator implementing IPC standards for fixture units,
    pipe sizing, and water supply requirements.
    """

    # IPC Table 709.1 - Fixture Unit Values
    FIXTURE_UNITS = {
        FixtureType.WATER_CLOSET: {"private": 3.0, "public": 6.0},
        FixtureType.LAVATORY: {"private": 1.0, "public": 2.0},
        FixtureType.BATHTUB: {"private": 2.0, "public": 4.0},
        FixtureType.SHOWER: {"private": 2.0, "public": 4.0},
        FixtureType.KITCHEN_SINK: {"private": 1.5, "public": 3.0},
        FixtureType.LAUNDRY: {"private": 2.0, "public": 3.0},
        FixtureType.DISHWASHER: {"private": 1.5, "public": 2.0},
        FixtureType.URINAL: {"private": 3.0, "public": 5.0},
        FixtureType.DRINKING_FOUNTAIN: {"private": 0.5, "public": 0.5},
    }

    # Hazen-Williams C factors for different pipe materials
    C_FACTORS = {
        "copper": 150,
        "pex": 150,
        "cpvc": 150,
        "galvanized": 120,
        "cast_iron": 100,
    }

    def calculate_fixture_units(self, fixtures: List[Fixture]) -> float:
        """
        Calculate total fixture units per IPC Table 709.1.

        Fixture units are used to size water supply piping and determine
        peak demand.

        Args:
            fixtures: List of plumbing fixtures

        Returns:
            Total fixture units

        References:
            IPC Section 709 - Fixture Unit Values
        """
        if not fixtures:
            return 0.0

        total_units = 0.0

        for fixture in fixtures:
            # Get fixture unit value based on type and use
            use_type = "private" if fixture.private else "public"
            fu_value = self.FIXTURE_UNITS.get(fixture.fixture_type, {}).get(
                use_type, 1.0
            )

            # Multiply by quantity
            total_units += fu_value * fixture.quantity

        return total_units

    def calculate_peak_demand(self, fixture_units: float) -> float:
        """
        Calculate peak water demand from fixture units.

        Uses Hunter's Curve method per IPC Appendix E.

        Args:
            fixture_units: Total fixture units

        Returns:
            Peak demand in GPM (gallons per minute)

        References:
            IPC Appendix E - Sizing of Water Piping System
        """
        if fixture_units <= 0:
            return 0.0

        # Hunter's Curve approximation
        # GPM = C × √(FU - C)
        # Where C is a constant (typically 0.6 for residential, 0.8 for commercial)

        if fixture_units <= 10:
            # Small systems - use simplified formula
            gpm = fixture_units * 2.5
        else:
            # Larger systems - use Hunter's Curve
            # Simplified: GPM ≈ 0.6 × √(FU)^1.2
            gpm = 0.6 * math.pow(fixture_units, 1.2)

        return round(gpm, 1)

    def size_pipe(
        self,
        flow_rate: float,
        length: float,
        material: str = "copper",
        max_velocity: float = 8.0,
    ) -> PipeSize:
        """
        Size water supply pipe per IPC Section 604.

        Uses Hazen-Williams equation for friction loss calculation.

        Args:
            flow_rate: Required flow rate (GPM)
            length: Pipe length (feet)
            material: Pipe material (copper, pex, cpvc, galvanized, cast_iron)
            max_velocity: Maximum allowable velocity (ft/s), default 8.0

        Returns:
            Pipe sizing recommendations

        References:
            IPC Section 604 - Water Supply Systems
        """
        # Standard pipe sizes (nominal diameter in inches)
        pipe_sizes = [0.5, 0.75, 1.0, 1.25, 1.5, 2.0, 2.5, 3.0, 4.0, 6.0]

        # Get C factor for material
        c_factor = self.C_FACTORS.get(material.lower(), 150)

        # Try each pipe size until we find one that meets velocity constraint
        for size in pipe_sizes:
            # Calculate actual inside diameter (approximate)
            # Type L copper: ID ≈ nominal - 0.125"
            inside_diameter = size - 0.125
            area = math.pi * (inside_diameter / 2) ** 2  # sq in

            # Calculate velocity: V = Q / A
            # Convert GPM to cubic inches per second: GPM × 231 / 60
            flow_cis = flow_rate * 231 / 60  # cubic inches per second
            velocity = flow_cis / area / 12  # ft/s

            # Check if velocity is acceptable (strictly less than max)
            if velocity < max_velocity:
                # Calculate friction loss using Hazen-Williams equation
                # hf = 0.2083 × (100/C)^1.852 × (Q^1.852 / d^4.8655)
                # Where: hf = head loss per 100 ft, Q = GPM, d = inside diameter (inches)

                friction_loss = (
                    0.2083
                    * math.pow(100 / c_factor, 1.852)
                    * math.pow(flow_rate, 1.852)
                    / math.pow(inside_diameter, 4.8655)
                )

                # Convert head loss to psi (1 ft head = 0.433 psi)
                friction_loss_psi = friction_loss * 0.433

                return PipeSize(
                    nominal_size=f'{size}"',
                    flow_rate=flow_rate,
                    velocity=round(velocity, 2),
                    friction_loss=round(friction_loss_psi, 2),
                )

        # If no size works, return largest size with estimated friction loss
        # Calculate friction loss for largest pipe
        largest_diameter = 6.065  # 6" Schedule 40
        area = math.pi * (largest_diameter / 2) ** 2
        flow_cis = flow_rate * 231 / 60
        velocity = flow_cis / area / 12

        friction_loss = (
            0.2083
            * math.pow(100 / c_factor, 1.852)
            * math.pow(flow_rate, 1.852)
            / math.pow(largest_diameter, 4.8655)
        )
        friction_loss_psi = friction_loss * 0.433

        return PipeSize(
            nominal_size='6"',
            flow_rate=flow_rate,
            velocity=round(velocity, 2),
            friction_loss=round(friction_loss_psi, 2),
        )

    def design_water_supply(
        self,
        fixtures: List[Fixture],
        supply_pressure: float = 60.0,
        material: str = "copper",
    ) -> WaterSupplyResult:
        """
        Design complete water supply system.

        Calculates fixture units, peak demand, and sizes service entrance,
        meter, and main distribution piping.

        Args:
            fixtures: List of plumbing fixtures
            supply_pressure: Available supply pressure (psi)
            material: Pipe material

        Returns:
            Complete water supply system design

        References:
            IPC Chapter 6 - Water Supply and Distribution
        """
        # Calculate total fixture units
        total_fu = self.calculate_fixture_units(fixtures)

        # Calculate peak demand
        peak_demand = self.calculate_peak_demand(total_fu)

        # Size service entrance pipe
        # Assume 100 ft equivalent length for service
        service_pipe = self.size_pipe(peak_demand, 100, material)
        service_size = service_pipe.nominal_size

        # Size water meter (typically one size smaller than service for residential)
        meter_sizes = ['5/8"', '3/4"', '1"', '1-1/2"', '2"', '3"', '4"', '6"']
        pipe_sizes_list = [
            '0.5"',
            '0.75"',
            '1"',
            '1.25"',
            '1.5"',
            '2"',
            '2.5"',
            '3"',
            '4"',
            '6"',
        ]

        try:
            service_index = pipe_sizes_list.index(service_size)
            meter_size = meter_sizes[
                max(0, min(service_index - 1, len(meter_sizes) - 1))
            ]
        except (ValueError, IndexError):
            # Default to 3/4" meter if service size not found
            meter_size = '3/4"'

        # Calculate required supply pressure
        # Account for: elevation, friction loss, fixture pressure requirement
        elevation_loss = 0  # Assume single story for simplicity
        friction_loss = service_pipe.friction_loss  # psi per 100 ft
        fixture_pressure = 15  # Minimum fixture pressure (psi)

        required_pressure = elevation_loss + friction_loss + fixture_pressure

        return WaterSupplyResult(
            total_fixture_units=total_fu,
            peak_demand=peak_demand,
            service_size=service_size,
            meter_size=meter_size,
            supply_pressure_required=round(required_pressure, 1),
        )
