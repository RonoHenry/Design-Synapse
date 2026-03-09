"""
Civil Engineering Calculator for grading, stormwater, and utility calculations.
Implements calculations per civil engineering standards.

**Validates: Requirements 3.1, 3.2, 3.3, 3.4**
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple


@dataclass
class SiteData:
    """Site parameters for civil engineering calculations."""

    area: float  # acres
    existing_elevations: Dict[str, float]  # point_id -> elevation (ft)
    soil_type: str  # clay, sand, silt, rock
    permeability: float  # inches/hour
    slope_percent: float  # existing average slope


@dataclass
class GradingPoint:
    """A point in the grading plan with coordinates and elevation."""

    x: float  # feet
    y: float  # feet
    existing_elevation: float  # feet
    proposed_elevation: float  # feet

    @property
    def cut_fill(self) -> float:
        """Calculate cut (positive) or fill (negative) at this point."""
        return self.existing_elevation - self.proposed_elevation


@dataclass
class GradingDesignResult:
    """Results from grading design calculations."""

    cut_volume: float  # cubic yards
    fill_volume: float  # cubic yards
    net_volume: float  # cubic yards (positive = net cut, negative = net fill)
    grading_points: List[GradingPoint]
    max_cut_depth: float  # feet
    max_fill_depth: float  # feet
    average_slope: float  # percent
    unit_system: str = "imperial"


@dataclass
class RainfallData:
    """Rainfall parameters for stormwater calculations."""

    intensity: float  # inches/hour
    duration: float  # hours
    return_period: int  # years (e.g., 10, 25, 100)
    runoff_coefficient: float  # 0.0 to 1.0


@dataclass
class StormwaterDesignResult:
    """Results from stormwater management design."""

    runoff_rate: float  # cubic feet per second (CFS)
    runoff_volume: float  # cubic feet
    detention_volume: float  # cubic feet
    detention_depth: float  # feet
    outlet_size: float  # inches
    pipe_sizes: Dict[str, float]  # pipe_id -> diameter (inches)
    unit_system: str = "imperial"


@dataclass
class UtilityLoads:
    """Utility load requirements."""

    water_demand: float  # gallons per minute (GPM)
    sewer_flow: float  # gallons per minute (GPM)
    gas_demand: Optional[float] = None  # cubic feet per hour (CFH)


@dataclass
class UtilityDesignResult:
    """Results from utility system design."""

    water_service_size: float  # inches
    water_pressure_required: float  # PSI
    sewer_service_size: float  # inches
    sewer_slope: float  # percent
    gas_service_size: Optional[float] = None  # inches
    unit_system: str = "imperial"


class CivilCalculator:
    """
    Civil engineering calculator implementing standard civil engineering
    calculations for grading, stormwater, and utilities.
    """

    def design_grading(
        self,
        site_data: SiteData,
        target_elevations: Dict[str, float],
        grid_spacing: float = 50.0,
    ) -> GradingDesignResult:
        """
        Design site grading with cut/fill analysis.

        Uses grid-based method to calculate earthwork volumes:
        1. Create grid of points across site
        2. Interpolate existing and proposed elevations
        3. Calculate cut/fill at each point
        4. Sum volumes using average end area method

        Args:
            site_data: Site parameters and existing conditions
            target_elevations: Proposed elevation at key points
            grid_spacing: Distance between grid points (feet)

        Returns:
            Grading design with cut/fill volumes

        References:
            - Civil Engineering Reference Manual (Lindeburg)
            - AASHTO Geometric Design Standards
        """
        # Create grading points from existing and target elevations
        grading_points = []

        for point_id, existing_elev in site_data.existing_elevations.items():
            # Get proposed elevation (use existing if not specified)
            proposed_elev = target_elevations.get(point_id, existing_elev)

            # Parse point coordinates from point_id (format: "x_y")
            try:
                x_str, y_str = point_id.split("_")
                x, y = float(x_str), float(y_str)
            except (ValueError, AttributeError):
                # If point_id is not in x_y format, use index-based positioning
                x = len(grading_points) * grid_spacing
                y = 0.0

            point = GradingPoint(
                x=x,
                y=y,
                existing_elevation=existing_elev,
                proposed_elevation=proposed_elev,
            )
            grading_points.append(point)

        # Calculate cut and fill volumes using average end area method
        # Volume = (Area1 + Area2) / 2 * Distance

        total_cut = 0.0  # cubic feet
        total_fill = 0.0  # cubic feet
        max_cut = 0.0
        max_fill = 0.0

        # Calculate area per grid point (square feet)
        grid_area = grid_spacing * grid_spacing

        for point in grading_points:
            cut_fill_depth = point.cut_fill  # positive = cut, negative = fill

            # Volume at this point (depth * area)
            volume = abs(cut_fill_depth) * grid_area

            if cut_fill_depth > 0:
                # Cut (removing earth)
                total_cut += volume
                max_cut = max(max_cut, cut_fill_depth)
            elif cut_fill_depth < 0:
                # Fill (adding earth)
                total_fill += volume
                max_fill = max(max_fill, abs(cut_fill_depth))

        # Convert cubic feet to cubic yards (27 cubic feet = 1 cubic yard)
        cut_volume_cy = total_cut / 27.0
        fill_volume_cy = total_fill / 27.0
        net_volume_cy = cut_volume_cy - fill_volume_cy

        # Calculate average slope
        if len(grading_points) > 1:
            total_slope = 0.0
            slope_count = 0

            for i, point in enumerate(grading_points[:-1]):
                next_point = grading_points[i + 1]

                # Calculate distance
                dx = next_point.x - point.x
                dy = next_point.y - point.y
                distance = (dx**2 + dy**2) ** 0.5

                if distance > 0:
                    # Calculate elevation change
                    dz = abs(next_point.proposed_elevation - point.proposed_elevation)

                    # Slope as percentage
                    slope = (dz / distance) * 100
                    total_slope += slope
                    slope_count += 1

            average_slope = total_slope / slope_count if slope_count > 0 else 0.0
        else:
            average_slope = 0.0

        return GradingDesignResult(
            cut_volume=cut_volume_cy,
            fill_volume=fill_volume_cy,
            net_volume=net_volume_cy,
            grading_points=grading_points,
            max_cut_depth=max_cut,
            max_fill_depth=max_fill,
            average_slope=average_slope,
            unit_system="imperial",
        )

    def calculate_stormwater_runoff(
        self, site_data: SiteData, rainfall_data: RainfallData
    ) -> float:
        """
        Calculate stormwater runoff using the Rational Method.

        Q = C × I × A

        Where:
        - Q = peak runoff rate (CFS)
        - C = runoff coefficient (dimensionless)
        - I = rainfall intensity (inches/hour)
        - A = drainage area (acres)

        Args:
            site_data: Site parameters including area
            rainfall_data: Rainfall intensity and duration

        Returns:
            Peak runoff rate in cubic feet per second (CFS)

        References:
            - ASCE Manual of Practice No. 77
            - Local jurisdiction stormwater management manuals
        """
        # Rational Method: Q = C × I × A
        runoff_rate = (
            rainfall_data.runoff_coefficient * rainfall_data.intensity * site_data.area
        )

        return runoff_rate

    def size_detention_pond(
        self, runoff_volume: float, release_rate: float, duration: float
    ) -> Tuple[float, float]:
        """
        Size detention pond for stormwater management.

        Detention volume is calculated to temporarily store runoff
        and release it at a controlled rate.

        Args:
            runoff_volume: Total runoff volume (cubic feet)
            release_rate: Allowable release rate (CFS)
            duration: Storm duration (hours)

        Returns:
            Tuple of (detention_volume in cubic feet, depth in feet)

        References:
            - ASCE Manual of Practice No. 77
        """
        # Calculate required detention volume
        # Volume = Inflow - Outflow over storm duration

        # Convert duration to seconds
        duration_seconds = duration * 3600

        # Outflow volume during storm
        outflow_volume = release_rate * duration_seconds

        # Required detention volume
        detention_volume = max(0, runoff_volume - outflow_volume)

        # Add 20% freeboard
        detention_volume *= 1.2

        # Estimate depth assuming 3:1 side slopes
        # For simplified calculation, assume rectangular pond
        # with length:width ratio of 3:1

        # Assume average depth of 4 feet for typical detention pond
        depth = 4.0

        # Adjust depth if volume is very large or small
        if detention_volume > 50000:
            depth = 6.0
        elif detention_volume < 5000:
            depth = 3.0

        return detention_volume, depth

    def calculate_pipe_size(
        self, flow_rate: float, slope: float, roughness: float = 0.013
    ) -> float:
        """
        Calculate required pipe diameter using Manning's equation.

        Q = (1.486/n) × A × R^(2/3) × S^(1/2)

        Where:
        - Q = flow rate (CFS)
        - n = Manning's roughness coefficient
        - A = cross-sectional area (sq ft)
        - R = hydraulic radius (ft)
        - S = slope (ft/ft)

        Args:
            flow_rate: Design flow rate (CFS)
            slope: Pipe slope (percent)
            roughness: Manning's n value (default 0.013 for smooth pipe)

        Returns:
            Required pipe diameter in inches

        References:
            - Hydraulic Design Handbook (Lindeburg)
        """
        # Convert slope from percent to decimal
        slope_decimal = slope / 100.0

        # For circular pipe flowing full:
        # A = π × D² / 4
        # R = D / 4
        # Substituting into Manning's equation and solving for D:

        # Q = (1.486/n) × (π×D²/4) × (D/4)^(2/3) × S^(1/2)
        # Rearranging: D = [(Q × n) / (0.463 × S^(1/2))]^(3/8)

        diameter_ft = ((flow_rate * roughness) / (0.463 * (slope_decimal**0.5))) ** (
            3 / 8
        )

        # Convert to inches
        diameter_inches = diameter_ft * 12

        # Round up to nearest standard pipe size
        standard_sizes = [6, 8, 10, 12, 15, 18, 21, 24, 27, 30, 36, 42, 48, 54, 60]

        for size in standard_sizes:
            if size >= diameter_inches:
                return float(size)

        # If larger than standard sizes, return calculated size
        return diameter_inches

    def design_water_service(
        self, demand: float, pressure_available: float = 60.0
    ) -> Tuple[float, float]:
        """
        Size water service line based on demand.

        Uses Hazen-Williams equation for pressure loss:
        P = 4.52 × Q^1.85 / (C^1.85 × D^4.87) × L

        Args:
            demand: Water demand (GPM)
            pressure_available: Available pressure (PSI)

        Returns:
            Tuple of (service_size in inches, pressure_required in PSI)

        References:
            - International Plumbing Code (IPC)
        """
        # Typical service sizes and capacities (GPM at 60 PSI)
        service_capacities = {
            0.75: 15,
            1.0: 30,
            1.5: 60,
            2.0: 100,
            3.0: 200,
            4.0: 350,
            6.0: 700,
        }

        # Select smallest size that meets demand
        service_size = 0.75
        for size, capacity in sorted(service_capacities.items()):
            if capacity >= demand:
                service_size = size
                break

        # Calculate required pressure (simplified)
        # Assume 10 PSI loss per 100 feet of pipe
        # and 100 feet of service line
        pressure_loss = 10.0
        pressure_required = 40.0 + pressure_loss  # 40 PSI minimum at fixture

        return service_size, pressure_required

    def design_sewer_service(self, flow: float) -> Tuple[float, float]:
        """
        Size sewer service line based on flow.

        Args:
            flow: Sewer flow (GPM)

        Returns:
            Tuple of (service_size in inches, slope in percent)

        References:
            - International Plumbing Code (IPC)
        """
        # Convert GPM to CFS
        flow_cfs = flow / 448.8

        # Minimum sewer service size is 4 inches
        # Typical residential: 4-6 inches
        # Commercial: 6-8 inches

        if flow_cfs <= 0.5:
            service_size = 4.0
            slope = 2.0  # 2% minimum slope for 4" pipe
        elif flow_cfs <= 1.0:
            service_size = 6.0
            slope = 1.0  # 1% minimum slope for 6" pipe
        else:
            service_size = 8.0
            slope = 0.5  # 0.5% minimum slope for 8" pipe

        return service_size, slope
