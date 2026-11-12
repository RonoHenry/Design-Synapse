"""
Electrical Calculator for load calculations, panel sizing, and circuit sizing.
Implements calculations per NEC (National Electrical Code) standards.

**Validates: Requirements 2.2, 2.6, 7.1-7.6**
"""

from dataclasses import dataclass
from enum import Enum
from typing import List, Optional


class CircuitType(Enum):
    """Types of electrical circuits."""

    LIGHTING = "lighting"
    RECEPTACLE = "receptacle"
    APPLIANCE = "appliance"
    HVAC = "hvac"
    MOTOR = "motor"


@dataclass
class Circuit:
    """Electrical circuit definition."""

    name: str
    circuit_type: CircuitType
    load: float  # Watts
    voltage: float  # Volts
    power_factor: float = 1.0  # Power factor (0-1)
    continuous: bool = False  # Continuous load (>3 hours)


@dataclass
class PanelSize:
    """Electrical panel sizing results."""

    rated_amperage: int  # Amps
    number_of_circuits: int
    bus_rating: int  # Amps
    main_breaker_size: int  # Amps
    panel_type: str


@dataclass
class CircuitSize:
    """Circuit conductor sizing results."""

    conductor_size: str  # AWG
    conduit_size: str  # inches
    breaker_size: int  # Amps
    voltage_drop: float  # %
    ampacity: int  # Amps


class ElectricalCalculator:
    """
    Electrical calculator implementing NEC standards for load calculations,
    panel sizing, and circuit sizing.
    """

    # NEC Table 310.16 - Conductor ampacities (copper, 75°C)
    CONDUCTOR_AMPACITY = {
        "14": 20,
        "12": 25,
        "10": 35,
        "8": 50,
        "6": 65,
        "4": 85,
        "3": 100,
        "2": 115,
        "1": 130,
        "1/0": 150,
        "2/0": 175,
        "3/0": 200,
        "4/0": 230,
        "250": 255,
        "300": 285,
        "350": 310,
        "400": 335,
        "500": 380,
    }

    # Standard breaker sizes (NEC 240.6)
    STANDARD_BREAKER_SIZES = [
        15,
        20,
        25,
        30,
        35,
        40,
        45,
        50,
        60,
        70,
        80,
        90,
        100,
        110,
        125,
        150,
        175,
        200,
        225,
        250,
        300,
        350,
        400,
        450,
        500,
        600,
        700,
        800,
        1000,
        1200,
    ]

    def calculate_load(self, circuits: List[Circuit]) -> float:
        """
        Calculate total electrical load per NEC Article 220.

        Applies demand factors and continuous load multipliers per NEC.

        Args:
            circuits: List of electrical circuits

        Returns:
            Total calculated load in Watts

        References:
            NEC Article 220 - Branch-Circuit, Feeder, and Service Load Calculations
        """
        if not circuits:
            return 0.0

        # Separate circuits by type for demand factor application
        lighting_load = 0.0
        receptacle_load = 0.0
        appliance_load = 0.0
        hvac_load = 0.0
        motor_load = 0.0

        for circuit in circuits:
            # Apply continuous load factor (125% per NEC 210.20(A))
            load = circuit.load
            if circuit.continuous:
                load *= 1.25

            # Categorize by type
            if circuit.circuit_type == CircuitType.LIGHTING:
                lighting_load += load
            elif circuit.circuit_type == CircuitType.RECEPTACLE:
                receptacle_load += load
            elif circuit.circuit_type == CircuitType.APPLIANCE:
                appliance_load += load
            elif circuit.circuit_type == CircuitType.HVAC:
                hvac_load += load
            elif circuit.circuit_type == CircuitType.MOTOR:
                motor_load += load

        # Apply demand factors per NEC 220.42, 220.43, 220.44

        # Lighting: First 3000 VA at 100%, remainder at 35% (NEC 220.42)
        if lighting_load <= 3000:
            lighting_demand = lighting_load
        else:
            lighting_demand = 3000 + (lighting_load - 3000) * 0.35

        # Receptacles: First 10 kVA at 100%, remainder at 50% (NEC 220.44)
        if receptacle_load <= 10000:
            receptacle_demand = receptacle_load
        else:
            receptacle_demand = 10000 + (receptacle_load - 10000) * 0.5

        # Appliances: Apply 75% demand factor if 4+ appliances (NEC 220.53)
        appliance_demand = (
            appliance_load * 0.75
            if len([c for c in circuits if c.circuit_type == CircuitType.APPLIANCE])
            >= 4
            else appliance_load
        )

        # HVAC and motors: 100% of largest + 25% of others (NEC 220.60)
        hvac_motors = [
            c.load
            for c in circuits
            if c.circuit_type in [CircuitType.HVAC, CircuitType.MOTOR]
        ]
        if hvac_motors:
            hvac_motors.sort(reverse=True)
            hvac_motor_demand = hvac_motors[0] + sum(hvac_motors[1:]) * 0.25
        else:
            hvac_motor_demand = 0.0

        # Total calculated load
        total_load = (
            lighting_demand + receptacle_demand + appliance_demand + hvac_motor_demand
        )

        return total_load

    def size_panel(self, load: float, voltage: float) -> PanelSize:
        """
        Size electrical panel per NEC Article 408.

        Args:
            load: Total calculated load (Watts)
            voltage: System voltage (Volts)

        Returns:
            Panel sizing recommendations

        References:
            NEC Article 408 - Switchboards, Switchgear, and Panelboards
        """
        # Calculate required amperage
        # I = P / V (for single phase)
        required_amps = load / voltage

        # Apply 125% factor for continuous loads (NEC 408.36)
        design_amps = required_amps * 1.25

        # Select standard panel size
        # Ensure safety factor doesn't exceed 2.5x
        standard_panel_sizes = [100, 125, 150, 200, 225, 400, 600, 800, 1000, 1200]
        max_allowed_amps = design_amps * 2.5

        rated_amperage = None
        for size in standard_panel_sizes:
            if size >= design_amps:
                if size <= max_allowed_amps:
                    rated_amperage = size
                    break
                else:
                    # Use custom size if standard would exceed 2.5x
                    rated_amperage = int(design_amps * 1.5)  # 1.5x safety factor
                    break

        if rated_amperage is None:
            rated_amperage = 1200

        # Determine number of circuits (estimate based on load)
        # Typical: 1 circuit per 1500-2000 VA
        estimated_circuits = int(load / 1500) + 2  # Add 2 for spares

        # Standard panel circuit counts: 12, 20, 24, 30, 40, 42
        circuit_counts = [12, 20, 24, 30, 40, 42]
        number_of_circuits = min(
            [count for count in circuit_counts if count >= estimated_circuits],
            default=42,
        )

        # Bus rating (typically same as panel rating)
        bus_rating = rated_amperage

        # Main breaker size (typically same as panel rating)
        main_breaker_size = rated_amperage

        # Determine panel type
        if rated_amperage <= 200:
            panel_type = "Residential Load Center"
        elif rated_amperage <= 400:
            panel_type = "Commercial Panelboard"
        else:
            panel_type = "Switchboard"

        return PanelSize(
            rated_amperage=rated_amperage,
            number_of_circuits=number_of_circuits,
            bus_rating=bus_rating,
            main_breaker_size=main_breaker_size,
            panel_type=panel_type,
        )

    def size_circuit(
        self, load: float, voltage: float, length: float, continuous: bool = False
    ) -> CircuitSize:
        """
        Size circuit conductors per NEC Article 310.

        Calculates conductor size, conduit size, breaker size, and voltage drop.

        Args:
            load: Circuit load (Watts)
            voltage: Circuit voltage (Volts)
            length: One-way circuit length (feet)
            continuous: Whether load is continuous (>3 hours)

        Returns:
            Circuit sizing recommendations

        References:
            NEC Article 310 - Conductors for General Wiring
            NEC Article 210 - Branch Circuits
        """
        # Calculate circuit current
        circuit_amps = load / voltage

        # Apply continuous load factor (125% per NEC 210.19(A)(1))
        if continuous:
            design_amps = circuit_amps * 1.25
        else:
            design_amps = circuit_amps

        # Select conductor size based on ampacity
        conductor_size = None
        ampacity = 0
        for size, amp in self.CONDUCTOR_AMPACITY.items():
            if amp >= design_amps:
                conductor_size = size
                ampacity = amp
                break

        if conductor_size is None:
            conductor_size = "500"
            ampacity = 380

        # Circular mils for common wire sizes (approximate)
        circular_mils = {
            "14": 4110,
            "12": 6530,
            "10": 10380,
            "8": 16510,
            "6": 26240,
            "4": 41740,
            "3": 52620,
            "2": 66360,
            "1": 83690,
            "1/0": 105600,
            "2/0": 133100,
            "3/0": 167800,
            "4/0": 211600,
            "250": 250000,
            "300": 300000,
            "350": 350000,
            "400": 400000,
            "500": 500000,
        }

        # Check voltage drop and upsize if needed (max 5% per NEC recommendation)
        max_voltage_drop = 5.0
        cm = circular_mils.get(conductor_size, 500000)
        voltage_drop_volts = (2 * 12.9 * circuit_amps * length) / cm
        voltage_drop_percent = (voltage_drop_volts / voltage) * 100

        # If voltage drop exceeds limit, upsize conductor
        conductor_sizes_ordered = [
            "14",
            "12",
            "10",
            "8",
            "6",
            "4",
            "3",
            "2",
            "1",
            "1/0",
            "2/0",
            "3/0",
            "4/0",
            "250",
            "300",
            "350",
            "400",
            "500",
        ]

        if voltage_drop_percent > max_voltage_drop:
            current_index = conductor_sizes_ordered.index(conductor_size)
            for size in conductor_sizes_ordered[current_index + 1 :]:
                cm = circular_mils.get(size, 500000)
                voltage_drop_volts = (2 * 12.9 * circuit_amps * length) / cm
                voltage_drop_percent = (voltage_drop_volts / voltage) * 100

                if voltage_drop_percent <= max_voltage_drop:
                    conductor_size = size
                    ampacity = self.CONDUCTOR_AMPACITY.get(size, 380)
                    break

        # Select breaker size (next standard size above design amps)
        breaker_size = min(
            [size for size in self.STANDARD_BREAKER_SIZES if size >= design_amps],
            default=1200,
        )

        # Select conduit size based on conductor size and number of conductors
        # Simplified: 3 conductors (hot, neutral, ground)
        conduit_sizes = {
            "14": "1/2",
            "12": "1/2",
            "10": "1/2",
            "8": "3/4",
            "6": "3/4",
            "4": "1",
            "3": "1",
            "2": "1-1/4",
            "1": "1-1/4",
            "1/0": "1-1/2",
            "2/0": "1-1/2",
            "3/0": "2",
            "4/0": "2",
            "250": "2-1/2",
            "300": "2-1/2",
            "350": "3",
            "400": "3",
            "500": "3",
        }

        conduit_size = conduit_sizes.get(conductor_size, "3")

        return CircuitSize(
            conductor_size=f"#{conductor_size} AWG",
            conduit_size=conduit_size,
            breaker_size=breaker_size,
            voltage_drop=round(voltage_drop_percent, 2),
            ampacity=ampacity,
        )
