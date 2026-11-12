"""
HVAC Calculator for heating loads, cooling loads, and equipment sizing.
Implements calculations per ASHRAE standards.

**Validates: Requirements 2.1, 2.6, 7.1-7.6**
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class BuildingData:
    """Building parameters for HVAC calculations."""

    floor_area: float  # sq ft
    wall_area: float  # sq ft
    roof_area: float  # sq ft
    window_area: float  # sq ft
    volume: float  # cu ft
    occupancy: int  # number of people
    insulation_r_value: float  # R-value


@dataclass
class ClimateData:
    """Climate parameters for HVAC calculations."""

    outdoor_temp_winter: float  # °F
    outdoor_temp_summer: float  # °F
    indoor_temp_winter: float  # °F
    indoor_temp_summer: float  # °F
    humidity_summer: float  # %


@dataclass
class EquipmentSize:
    """HVAC equipment sizing results."""

    heating_capacity: float  # BTU/hr
    cooling_capacity: float  # BTU/hr
    airflow: float  # CFM
    equipment_type: str


@dataclass
class HVACDesignResult:
    """Complete HVAC design results."""

    heating_load: float  # BTU/hr
    cooling_load: float  # BTU/hr
    equipment: EquipmentSize
    unit_system: str = "imperial"


class HVACCalculator:
    """
    HVAC calculator implementing ASHRAE standards for heating/cooling loads
    and equipment sizing.
    """

    def calculate_heating_load(
        self, building: BuildingData, climate: ClimateData
    ) -> float:
        """
        Calculate heating load per ASHRAE Handbook.

        Uses simplified heat loss calculation:
        Q = (U × A × ΔT) + (Infiltration) + (Ventilation)

        Where:
        - Q = heat loss (BTU/hr)
        - U = overall heat transfer coefficient (BTU/hr·ft²·°F)
        - A = surface area (ft²)
        - ΔT = temperature difference (°F)

        Args:
            building: Building parameters
            climate: Climate data

        Returns:
            Heating load in BTU/hr

        References:
            ASHRAE Handbook - Fundamentals, Chapter 18
        """
        # Temperature difference
        delta_t = climate.indoor_temp_winter - climate.outdoor_temp_winter

        # Calculate U-values (overall heat transfer coefficients)
        # U = 1/R for insulated surfaces
        u_wall = 1.0 / building.insulation_r_value  # BTU/hr·ft²·°F
        u_roof = 1.0 / (
            building.insulation_r_value + 10
        )  # Roof typically better insulated
        u_window = 0.5  # Typical double-pane window U-value
        u_floor = 0.05  # Floor heat loss (minimal for slab on grade)

        # Transmission heat loss through building envelope
        wall_loss = u_wall * building.wall_area * delta_t
        roof_loss = u_roof * building.roof_area * delta_t
        window_loss = u_window * building.window_area * delta_t
        floor_loss = u_floor * building.floor_area * delta_t

        transmission_loss = wall_loss + roof_loss + window_loss + floor_loss

        # Infiltration heat loss
        # Q_inf = 1.08 × CFM × ΔT
        # Assume 0.5 air changes per hour for typical construction
        ach = 0.5  # air changes per hour
        cfm_infiltration = (building.volume * ach) / 60  # convert to CFM
        infiltration_loss = 1.08 * cfm_infiltration * delta_t

        # Ventilation heat loss (fresh air for occupants)
        # ASHRAE 62.1: 15 CFM per person minimum
        cfm_ventilation = building.occupancy * 15
        ventilation_loss = 1.08 * cfm_ventilation * delta_t

        # Total heating load
        total_heating_load = transmission_loss + infiltration_loss + ventilation_loss

        # Return base load without safety factor
        # Safety factor will be applied during equipment sizing
        return total_heating_load

    def calculate_cooling_load(
        self, building: BuildingData, climate: ClimateData
    ) -> float:
        """
        Calculate cooling load per ASHRAE Handbook.

        Cooling load includes:
        - Transmission gains through envelope
        - Solar gains through windows
        - Internal gains (people, lights, equipment)
        - Ventilation and infiltration

        Args:
            building: Building parameters
            climate: Climate data

        Returns:
            Cooling load in BTU/hr

        References:
            ASHRAE Handbook - Fundamentals, Chapter 18
        """
        # Temperature difference
        delta_t = climate.outdoor_temp_summer - climate.indoor_temp_summer

        # Calculate U-values
        u_wall = 1.0 / building.insulation_r_value
        u_roof = 1.0 / (building.insulation_r_value + 10)
        u_window = 0.5

        # Transmission heat gain
        wall_gain = u_wall * building.wall_area * delta_t
        roof_gain = u_roof * building.roof_area * delta_t
        window_gain = u_window * building.window_area * delta_t

        transmission_gain = wall_gain + roof_gain + window_gain

        # Solar heat gain through windows
        # SHGC (Solar Heat Gain Coefficient) typically 0.25-0.4 for modern windows
        shgc = 0.3
        solar_intensity = 200  # BTU/hr·ft² (peak summer)
        solar_gain = building.window_area * solar_intensity * shgc

        # Internal heat gains
        # People: 250 BTU/hr per person (sensible)
        people_gain = building.occupancy * 250

        # Lighting: 1.5 W/sq ft typical = 5.12 BTU/hr·sq ft
        lighting_gain = building.floor_area * 5.12

        # Equipment: 1.0 W/sq ft typical = 3.41 BTU/hr·sq ft
        equipment_gain = building.floor_area * 3.41

        internal_gain = people_gain + lighting_gain + equipment_gain

        # Infiltration and ventilation
        ach = 0.3  # Lower for cooling (building under positive pressure)
        cfm_infiltration = (building.volume * ach) / 60

        # Sensible cooling from infiltration
        infiltration_sensible = 1.08 * cfm_infiltration * delta_t

        # Latent cooling from infiltration (humidity)
        # Q_latent = 0.68 × CFM × Δω (where Δω is humidity ratio difference)
        # Simplified: assume 30% humidity difference
        infiltration_latent = 0.68 * cfm_infiltration * 0.003 * 1000  # Approximate

        # Ventilation
        cfm_ventilation = building.occupancy * 15
        ventilation_sensible = 1.08 * cfm_ventilation * delta_t
        ventilation_latent = 0.68 * cfm_ventilation * 0.003 * 1000

        # Total cooling load
        total_cooling_load = (
            transmission_gain
            + solar_gain
            + internal_gain
            + infiltration_sensible
            + infiltration_latent
            + ventilation_sensible
            + ventilation_latent
        )

        # Return base load without safety factor
        # Safety factor will be applied during equipment sizing
        return total_cooling_load

    def size_equipment(self, heating_load: float, cooling_load: float) -> EquipmentSize:
        """
        Size HVAC equipment based on calculated loads.

        Equipment is sized to standard capacities which provides inherent
        safety factor (typically 1.0-1.5x) over the base load.

        Args:
            heating_load: Base heating load (BTU/hr) without safety factor
            cooling_load: Base cooling load (BTU/hr) without safety factor

        Returns:
            Equipment sizing recommendations

        References:
            ASHRAE Handbook - HVAC Systems and Equipment
        """
        # Convert cooling to tons (12,000 BTU/hr = 1 ton)
        cooling_tons = cooling_load / 12000
        heating_tons = heating_load / 12000

        # Round up to nearest standard size (provides safety factor)
        # But ensure safety factor doesn't exceed 1.5x
        standard_sizes = [1.5, 2, 2.5, 3, 3.5, 4, 5, 6, 7.5, 10, 12.5, 15, 20, 25]

        # Find minimum size that meets load with max 1.5x safety factor
        required_tons = max(cooling_tons, heating_tons)
        max_allowed_tons = required_tons * 1.5

        # Select smallest standard size >= required but <= max_allowed
        equipment_tons = None
        for size in standard_sizes:
            if size >= required_tons and size <= max_allowed_tons:
                equipment_tons = size
                break

        # If no standard size fits, use custom size with 1.25x safety factor
        if equipment_tons is None:
            equipment_tons = required_tons * 1.25

        cooling_capacity = equipment_tons * 12000
        heating_capacity = equipment_tons * 12000

        # Calculate required airflow
        # Rule of thumb: 400 CFM per ton of cooling
        airflow = equipment_tons * 400

        # Determine equipment type
        if equipment_tons <= 5:
            equipment_type = "Residential Split System"
        elif equipment_tons <= 10:
            equipment_type = "Light Commercial Packaged Unit"
        else:
            equipment_type = "Commercial Rooftop Unit"

        return EquipmentSize(
            heating_capacity=heating_capacity,
            cooling_capacity=cooling_capacity,
            airflow=airflow,
            equipment_type=equipment_type,
        )
