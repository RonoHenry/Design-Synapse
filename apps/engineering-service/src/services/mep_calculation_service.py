"""
MEP Calculation Service for coordinating MEP engineering calculations.

This service layer orchestrates MEP (Mechanical, Electrical, Plumbing)
calculations, manages data persistence, and handles automatic recalculation
when inputs change.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from ..calculations.electrical_calculator import Circuit, ElectricalCalculator
from ..calculations.fire_protection_calculator import \
    BuildingData as FireBuildingData
from ..calculations.fire_protection_calculator import (
    FireProtectionCalculator, OccupancyHazard, SprinklerType)
from ..calculations.hvac_calculator import (BuildingData, ClimateData,
                                            HVACCalculator, HVACDesignResult)
from ..calculations.plumbing_calculator import (Fixture, FixtureType,
                                                PlumbingCalculator)
from ..models.calculation_sheet import CalculationSheet
from ..models.mep_design import MEPDesign
from ..repositories.calculation_sheet_repository import \
    CalculationSheetRepository
from ..repositories.mep_design_repository import MEPDesignRepository


class MEPCalculationService:
    """
    Service for MEP engineering calculations.

    Coordinates calculation engines, manages data persistence,
    and handles automatic recalculation on input changes.
    """

    def __init__(
        self,
        db_session: AsyncSession,
        calculation_sheet_repo: Optional[CalculationSheetRepository] = None,
        mep_design_repo: Optional[MEPDesignRepository] = None,
    ):
        """
        Initialize the MEP calculation service.

        Args:
            db_session: Database session for persistence
            calculation_sheet_repo: Repository for calculation sheets
            mep_design_repo: Repository for MEP designs
        """
        self.db_session = db_session
        self.calculation_sheet_repo = (
            calculation_sheet_repo or CalculationSheetRepository(db_session)
        )
        self.mep_design_repo = mep_design_repo or MEPDesignRepository(db_session)

        # Initialize calculation engines
        self.hvac_calculator = HVACCalculator()
        self.electrical_calculator = ElectricalCalculator()
        self.plumbing_calculator = PlumbingCalculator()
        self.fire_protection_calculator = FireProtectionCalculator()

    async def design_hvac_system(
        self,
        project_id: str,
        building_data: Dict[str, Any],
        climate_data: Dict[str, Any],
        user_id: str,
        unit_system: str = "imperial",
    ) -> HVACDesignResult:
        """
        Design HVAC system per ASHRAE standards.

        Args:
            project_id: Project identifier
            building_data: Building parameters (floor_area, wall_area,
                          roof_area, window_area, volume, occupancy,
                          insulation_r_value)
            climate_data: Climate parameters (outdoor_temp_winter,
                         outdoor_temp_summer, indoor_temp_winter,
                         indoor_temp_summer, humidity_summer)
            user_id: User performing the design
            unit_system: Unit system (imperial or metric)

        Returns:
            HVACDesignResult with heating/cooling loads and equipment sizing

        Raises:
            ValueError: If building_data or climate_data are invalid
        """
        # Parse building data
        building = BuildingData(
            floor_area=building_data.get("floor_area", 0.0),
            wall_area=building_data.get("wall_area", 0.0),
            roof_area=building_data.get("roof_area", 0.0),
            window_area=building_data.get("window_area", 0.0),
            volume=building_data.get("volume", 0.0),
            occupancy=building_data.get("occupancy", 0),
            insulation_r_value=building_data.get("insulation_r_value", 13.0),
        )

        # Parse climate data
        climate = ClimateData(
            outdoor_temp_winter=climate_data.get("outdoor_temp_winter", 0.0),
            outdoor_temp_summer=climate_data.get("outdoor_temp_summer", 95.0),
            indoor_temp_winter=climate_data.get("indoor_temp_winter", 70.0),
            indoor_temp_summer=climate_data.get("indoor_temp_summer", 75.0),
            humidity_summer=climate_data.get("humidity_summer", 50.0),
        )

        # Calculate heating load
        heating_load = self.hvac_calculator.calculate_heating_load(building, climate)

        # Calculate cooling load
        cooling_load = self.hvac_calculator.calculate_cooling_load(building, climate)

        # Size equipment
        equipment = self.hvac_calculator.size_equipment(heating_load, cooling_load)

        # Create calculation sheet
        calculation_sheet = CalculationSheet(
            project_id=project_id,
            title=(f"HVAC Design - " f"{datetime.utcnow().strftime('%Y-%m-%d %H:%M')}"),
            description="HVAC system design with heating/cooling loads "
            "and equipment sizing per ASHRAE standards",
            calculation_type="hvac_design",
            inputs={
                "building_data": building_data,
                "climate_data": climate_data,
            },
            outputs={
                "heating_load": heating_load,
                "cooling_load": cooling_load,
                "heating_capacity": equipment.heating_capacity,
                "cooling_capacity": equipment.cooling_capacity,
                "airflow": equipment.airflow,
                "equipment_type": equipment.equipment_type,
            },
            formulas=[
                "Heating Load: Q = (U × A × ΔT) + Infiltration + Ventilation",
                "Cooling Load: Transmission + Solar + Internal + "
                "Infiltration + Ventilation",
                "Equipment Sizing: Standard capacity selection with " "safety factor",
            ],
            references=["ASHRAE Handbook - Fundamentals", "ASHRAE 62.1"],
            units=unit_system,
            created_by=user_id,
            status="approved",
        )

        # Save calculation sheet to database
        saved_sheet = await self.calculation_sheet_repo.create(calculation_sheet)

        # Create MEP design record linked to the calculation sheet
        mep_design = MEPDesign(
            project_id=project_id,
            calculation_sheet_id=saved_sheet.id,
            title=(f"HVAC Design - " f"{datetime.utcnow().strftime('%Y-%m-%d %H:%M')}"),
            description=(
                f"HVAC system design: heating={heating_load:.0f} BTU/hr, "
                f"cooling={cooling_load:.0f} BTU/hr"
            ),
            system_type="hvac",
            loads={
                "heating_load": heating_load,
                "cooling_load": cooling_load,
            },
            equipment={
                "heating_capacity": equipment.heating_capacity,
                "cooling_capacity": equipment.cooling_capacity,
                "airflow": equipment.airflow,
                "equipment_type": equipment.equipment_type,
            },
            distribution={
                "airflow_cfm": equipment.airflow,
                "supply_temp": 55.0,  # Typical supply air temperature (°F)
                "return_temp": 75.0,  # Typical return air temperature (°F)
            },
            sizing_results={
                "heating_capacity_btu_hr": equipment.heating_capacity,
                "cooling_capacity_btu_hr": equipment.cooling_capacity,
                "cooling_tons": equipment.cooling_capacity / 12000,
                "airflow_cfm": equipment.airflow,
            },
            code_references={
                "codes": ["ASHRAE Handbook - Fundamentals", "ASHRAE 62.1"],
                "standards": ["ASHRAE 90.1"],
            },
            units=unit_system,
            status="draft",
            created_by=user_id,
        )

        # Save MEP design to database
        await self.mep_design_repo.create(mep_design)

        # Commit transaction
        await self.db_session.commit()

        # Return result
        return HVACDesignResult(
            heating_load=heating_load,
            cooling_load=cooling_load,
            equipment=equipment,
            unit_system=unit_system,
        )

    async def design_electrical_system(
        self,
        project_id: str,
        circuits: List[Dict[str, Any]],
        voltage: float,
        user_id: str,
        unit_system: str = "imperial",
    ) -> Dict[str, Any]:
        """
        Design electrical system per NEC standards.

        Args:
            project_id: Project identifier
            circuits: List of circuit definitions with keys:
                     name, circuit_type, load, voltage, power_factor, continuous
            voltage: System voltage (Volts)
            user_id: User performing the design
            unit_system: Unit system (imperial or metric)

        Returns:
            Dictionary with electrical design results including:
            - total_load: Total calculated load (Watts)
            - panel_size: Panel sizing results
            - circuit_sizes: List of circuit sizing results

        Raises:
            ValueError: If circuits or voltage are invalid
        """
        # Validate inputs
        if not circuits:
            raise ValueError("At least one circuit must be provided")
        if voltage <= 0:
            raise ValueError("Voltage must be positive")

        # Parse circuits
        circuit_objects = []
        for circuit_data in circuits:
            circuit = Circuit(
                name=circuit_data.get("name", "Unnamed Circuit"),
                circuit_type=circuit_data.get("circuit_type"),
                load=circuit_data.get("load", 0.0),
                voltage=circuit_data.get("voltage", voltage),
                power_factor=circuit_data.get("power_factor", 1.0),
                continuous=circuit_data.get("continuous", False),
            )
            circuit_objects.append(circuit)

        # Calculate total electrical load
        total_load = self.electrical_calculator.calculate_load(circuit_objects)

        # Size electrical panel
        panel_size = self.electrical_calculator.size_panel(total_load, voltage)

        # Size individual circuits
        circuit_sizes = []
        for circuit in circuit_objects:
            # Use default length of 100 feet if not specified
            length = 100.0
            circuit_size = self.electrical_calculator.size_circuit(
                load=circuit.load,
                voltage=circuit.voltage,
                length=length,
                continuous=circuit.continuous,
            )
            circuit_sizes.append(
                {
                    "name": circuit.name,
                    "conductor_size": circuit_size.conductor_size,
                    "conduit_size": circuit_size.conduit_size,
                    "breaker_size": circuit_size.breaker_size,
                    "voltage_drop": circuit_size.voltage_drop,
                    "ampacity": circuit_size.ampacity,
                }
            )

        # Create calculation sheet
        calculation_sheet = CalculationSheet(
            project_id=project_id,
            title=(
                f"Electrical Design - "
                f"{datetime.utcnow().strftime('%Y-%m-%d %H:%M')}"
            ),
            description="Electrical system design with load calculations, "
            "panel sizing, and circuit sizing per NEC standards",
            calculation_type="electrical_design",
            inputs={
                "circuits": circuits,
                "voltage": voltage,
            },
            outputs={
                "total_load": total_load,
                "panel_size": {
                    "rated_amperage": panel_size.rated_amperage,
                    "number_of_circuits": panel_size.number_of_circuits,
                    "bus_rating": panel_size.bus_rating,
                    "main_breaker_size": panel_size.main_breaker_size,
                    "panel_type": panel_size.panel_type,
                },
                "circuit_sizes": circuit_sizes,
            },
            formulas=[
                "Total Load: Sum of all circuit loads with demand "
                "factors per NEC 220",
                "Panel Sizing: I = P / V with 125% continuous load "
                "factor per NEC 408.36",
                "Circuit Sizing: Conductor ampacity per NEC 310.16, "
                "voltage drop ≤ 5%",
            ],
            references=["NEC Article 220", "NEC Article 310", "NEC Article 408"],
            units=unit_system,
            created_by=user_id,
            status="approved",
        )

        # Save calculation sheet to database
        saved_sheet = await self.calculation_sheet_repo.create(calculation_sheet)

        # Create MEP design record linked to the calculation sheet
        mep_design = MEPDesign(
            project_id=project_id,
            calculation_sheet_id=saved_sheet.id,
            title=(
                f"Electrical Design - "
                f"{datetime.utcnow().strftime('%Y-%m-%d %H:%M')}"
            ),
            description=(
                f"Electrical system design: total load={total_load:.0f} W, "
                f"panel={panel_size.rated_amperage}A"
            ),
            system_type="electrical",
            loads={
                "total_load": total_load,
                "voltage": voltage,
            },
            equipment={
                "panel_rated_amperage": panel_size.rated_amperage,
                "panel_type": panel_size.panel_type,
                "main_breaker_size": panel_size.main_breaker_size,
                "bus_rating": panel_size.bus_rating,
            },
            distribution={
                "number_of_circuits": panel_size.number_of_circuits,
                "circuit_details": circuit_sizes,
            },
            sizing_results={
                "total_load_watts": total_load,
                "panel_amperage": panel_size.rated_amperage,
                "number_of_circuits": panel_size.number_of_circuits,
            },
            code_references={
                "codes": ["NEC Article 220", "NEC Article 310", "NEC Article 408"],
                "standards": ["NFPA 70"],
            },
            units=unit_system,
            status="draft",
            created_by=user_id,
        )

        # Save MEP design to database
        await self.mep_design_repo.create(mep_design)

        # Commit transaction
        await self.db_session.commit()

        # Return result
        return {
            "total_load": total_load,
            "panel_size": {
                "rated_amperage": panel_size.rated_amperage,
                "number_of_circuits": panel_size.number_of_circuits,
                "bus_rating": panel_size.bus_rating,
                "main_breaker_size": panel_size.main_breaker_size,
                "panel_type": panel_size.panel_type,
            },
            "circuit_sizes": circuit_sizes,
            "unit_system": unit_system,
        }

    async def design_plumbing_system(
        self,
        project_id: str,
        fixtures: List[Dict[str, Any]],
        supply_pressure: float,
        user_id: str,
        unit_system: str = "imperial",
        material: str = "copper",
    ) -> Dict[str, Any]:
        """
        Design plumbing system per IPC standards.

        Args:
            project_id: Project identifier
            fixtures: List of fixture definitions with keys:
                     name, fixture_type, quantity, private
            supply_pressure: Available water supply pressure (psi)
            user_id: User performing the design
            unit_system: Unit system (imperial or metric)
            material: Pipe material (copper, pex, cpvc, galvanized, cast_iron)

        Returns:
            Dictionary with plumbing design results including:
            - total_fixture_units: Total fixture units
            - peak_demand: Peak water demand (GPM)
            - service_size: Service pipe size
            - meter_size: Water meter size
            - supply_pressure_required: Required supply pressure (psi)

        Raises:
            ValueError: If fixtures or supply_pressure are invalid
        """
        # Validate inputs
        if not fixtures:
            raise ValueError("At least one fixture must be provided")
        if supply_pressure <= 0:
            raise ValueError("Supply pressure must be positive")

        # Parse fixtures
        fixture_objects = []
        for fixture_data in fixtures:
            # Parse fixture type
            fixture_type_str = fixture_data.get("fixture_type", "lavatory")
            try:
                fixture_type = FixtureType(fixture_type_str)
            except ValueError:
                # Default to lavatory if invalid type
                fixture_type = FixtureType.LAVATORY

            fixture = Fixture(
                name=fixture_data.get("name", "Unnamed Fixture"),
                fixture_type=fixture_type,
                quantity=fixture_data.get("quantity", 1),
                private=fixture_data.get("private", True),
            )
            fixture_objects.append(fixture)

        # Design water supply system
        water_supply = self.plumbing_calculator.design_water_supply(
            fixtures=fixture_objects,
            supply_pressure=supply_pressure,
            material=material,
        )

        # Create calculation sheet
        calculation_sheet = CalculationSheet(
            project_id=project_id,
            title=(
                f"Plumbing Design - " f"{datetime.utcnow().strftime('%Y-%m-%d %H:%M')}"
            ),
            description=(
                "Plumbing system design with fixture units, "
                "pipe sizing, and water supply requirements per IPC "
                "standards"
            ),
            calculation_type="plumbing_design",
            inputs={
                "fixtures": fixtures,
                "supply_pressure": supply_pressure,
                "material": material,
            },
            outputs={
                "total_fixture_units": water_supply.total_fixture_units,
                "peak_demand": water_supply.peak_demand,
                "service_size": water_supply.service_size,
                "meter_size": water_supply.meter_size,
                "supply_pressure_required": (water_supply.supply_pressure_required),
            },
            formulas=[
                "Fixture Units: Per IPC Table 709.1",
                ("Peak Demand: Hunter's Curve method per " "IPC Appendix E"),
                ("Pipe Sizing: Hazen-Williams equation per " "IPC Section 604"),
            ],
            references=[
                "IPC Section 604",
                "IPC Section 709",
                "IPC Appendix E",
            ],
            units=unit_system,
            created_by=user_id,
            status="approved",
        )

        # Save calculation sheet to database
        saved_sheet = await self.calculation_sheet_repo.create(calculation_sheet)

        # Create MEP design record linked to the calculation sheet
        mep_design = MEPDesign(
            project_id=project_id,
            calculation_sheet_id=saved_sheet.id,
            title=(
                f"Plumbing Design - " f"{datetime.utcnow().strftime('%Y-%m-%d %H:%M')}"
            ),
            description=(
                f"Plumbing system design: "
                f"{water_supply.total_fixture_units} "
                f"fixture units, peak demand={water_supply.peak_demand} GPM"
            ),
            system_type="plumbing",
            loads={
                "total_fixture_units": water_supply.total_fixture_units,
                "peak_demand": water_supply.peak_demand,
                "supply_pressure": supply_pressure,
            },
            equipment={
                "service_size": water_supply.service_size,
                "meter_size": water_supply.meter_size,
                "material": material,
            },
            distribution={
                "service_pipe": water_supply.service_size,
                "meter": water_supply.meter_size,
                "supply_pressure_required": (water_supply.supply_pressure_required),
            },
            sizing_results={
                "total_fixture_units": water_supply.total_fixture_units,
                "peak_demand_gpm": water_supply.peak_demand,
                "service_size": water_supply.service_size,
                "meter_size": water_supply.meter_size,
                "supply_pressure_required_psi": (water_supply.supply_pressure_required),
            },
            code_references={
                "codes": [
                    "IPC Section 604",
                    "IPC Section 709",
                    "IPC Appendix E",
                ],
                "standards": ["IPC"],
            },
            units=unit_system,
            status="draft",
            created_by=user_id,
        )

        # Save MEP design to database
        await self.mep_design_repo.create(mep_design)

        # Commit transaction
        await self.db_session.commit()

        # Return result
        return {
            "total_fixture_units": water_supply.total_fixture_units,
            "peak_demand": water_supply.peak_demand,
            "service_size": water_supply.service_size,
            "meter_size": water_supply.meter_size,
            "supply_pressure_required": (water_supply.supply_pressure_required),
            "unit_system": unit_system,
        }

    async def design_fire_protection(
        self,
        project_id: str,
        building_data: Dict[str, Any],
        user_id: str,
        unit_system: str = "imperial",
    ) -> Dict[str, Any]:
        """
        Design fire protection system per NFPA 13 standards.

        Args:
            project_id: Project identifier
            building_data: Building parameters with keys:
                          floor_area, ceiling_height, occupancy_hazard,
                          construction_type, supply_pressure (optional),
                          system_type (optional)
            user_id: User performing the design
            unit_system: Unit system (imperial or metric)

        Returns:
            Dictionary with fire protection design results including:
            - sprinkler_design: Sprinkler system parameters
            - total_demand: Total water demand (GPM)
            - residual_pressure: Residual pressure at remote head (psi)
            - main_pipe_size: Main pipe size
            - riser_size: Riser pipe size
            - system_type: Type of sprinkler system

        Raises:
            ValueError: If building_data is invalid
        """
        # Validate inputs
        if not building_data:
            raise ValueError("Building data must be provided")

        floor_area = building_data.get("floor_area", 0.0)
        ceiling_height = building_data.get("ceiling_height", 10.0)
        occupancy_hazard_str = building_data.get(
            "occupancy_hazard", "ordinary_hazard_1"
        )
        construction_type = building_data.get("construction_type", "Type II")
        supply_pressure = building_data.get("supply_pressure", 80.0)
        system_type_str = building_data.get("system_type", "wet_pipe")

        # Validate required fields
        if floor_area <= 0:
            raise ValueError("Floor area must be positive")
        if ceiling_height <= 0:
            raise ValueError("Ceiling height must be positive")

        # Parse occupancy hazard
        try:
            occupancy_hazard = OccupancyHazard(occupancy_hazard_str)
        except ValueError:
            # Default to ordinary hazard 1 if invalid
            occupancy_hazard = OccupancyHazard.ORDINARY_HAZARD_1

        # Parse system type
        try:
            system_type = SprinklerType(system_type_str)
        except ValueError:
            # Default to wet pipe if invalid
            system_type = SprinklerType.WET_PIPE

        # Create building data object for fire protection calculator
        fire_building = FireBuildingData(
            floor_area=floor_area,
            ceiling_height=ceiling_height,
            occupancy_hazard=occupancy_hazard,
            construction_type=construction_type,
        )

        # Design fire protection system
        fire_result = self.fire_protection_calculator.design_system(
            building=fire_building,
            supply_pressure=supply_pressure,
            system_type=system_type,
        )

        # Create calculation sheet
        calculation_sheet = CalculationSheet(
            project_id=project_id,
            title=(
                f"Fire Protection Design - "
                f"{datetime.utcnow().strftime('%Y-%m-%d %H:%M')}"
            ),
            description=(
                "Fire protection system design with sprinkler demand, "
                "pipe sizing, and coverage per NFPA 13 standards"
            ),
            calculation_type="fire_protection_design",
            inputs={
                "building_data": building_data,
                "supply_pressure": supply_pressure,
                "system_type": system_type_str,
            },
            outputs={
                "sprinkler_design": {
                    "density": fire_result.sprinkler_design.density,
                    "area_of_application": (
                        fire_result.sprinkler_design.area_of_application
                    ),
                    "coverage_per_head": (
                        fire_result.sprinkler_design.coverage_per_head
                    ),
                    "number_of_heads": (fire_result.sprinkler_design.number_of_heads),
                    "flow_per_head": (fire_result.sprinkler_design.flow_per_head),
                },
                "total_demand": fire_result.total_demand,
                "residual_pressure": fire_result.residual_pressure,
                "main_pipe_size": fire_result.main_pipe_size,
                "riser_size": fire_result.riser_size,
                "system_type": fire_result.system_type.value,
            },
            formulas=[
                "Sprinkler Demand: Per NFPA 13 Table 11.2.3.1.1",
                "Total Demand: Sprinkler demand + hose allowance",
                ("Pipe Sizing: Hazen-Williams equation per " "NFPA 13 Annex E"),
                (
                    "Residual Pressure: Supply pressure - elevation "
                    "loss - friction loss"
                ),
            ],
            references=[
                "NFPA 13 - Standard for the Installation of " "Sprinkler Systems",
                "NFPA 13 Section 11.2 - Design Criteria",
                "NFPA 13 Annex E - Hydraulic Calculation Procedures",
            ],
            units=unit_system,
            created_by=user_id,
            status="approved",
        )

        # Save calculation sheet to database
        saved_sheet = await self.calculation_sheet_repo.create(calculation_sheet)

        # Create MEP design record linked to the calculation sheet
        mep_design = MEPDesign(
            project_id=project_id,
            calculation_sheet_id=saved_sheet.id,
            title=(
                f"Fire Protection Design - "
                f"{datetime.utcnow().strftime('%Y-%m-%d %H:%M')}"
            ),
            description=(
                f"Fire protection system design: "
                f"{fire_result.sprinkler_design.number_of_heads} heads, "
                f"total demand={fire_result.total_demand} GPM"
            ),
            system_type="fire_protection",
            loads={
                "total_demand": fire_result.total_demand,
                "supply_pressure": supply_pressure,
                "occupancy_hazard": occupancy_hazard.value,
            },
            equipment={
                "system_type": fire_result.system_type.value,
                "number_of_heads": (fire_result.sprinkler_design.number_of_heads),
                "flow_per_head": fire_result.sprinkler_design.flow_per_head,
            },
            distribution={
                "main_pipe_size": fire_result.main_pipe_size,
                "riser_size": fire_result.riser_size,
                "residual_pressure": fire_result.residual_pressure,
            },
            sizing_results={
                "total_demand_gpm": fire_result.total_demand,
                "number_of_heads": (fire_result.sprinkler_design.number_of_heads),
                "density_gpm_per_sqft": (fire_result.sprinkler_design.density),
                "area_of_application_sqft": (
                    fire_result.sprinkler_design.area_of_application
                ),
                "main_pipe_size": fire_result.main_pipe_size,
                "riser_size": fire_result.riser_size,
                "residual_pressure_psi": fire_result.residual_pressure,
            },
            code_references={
                "codes": [
                    "NFPA 13 - Standard for the Installation of " "Sprinkler Systems",
                    "NFPA 13 Section 11.2 - Design Criteria",
                ],
                "standards": ["NFPA 13"],
            },
            units=unit_system,
            status="draft",
            created_by=user_id,
        )

        # Save MEP design to database
        await self.mep_design_repo.create(mep_design)

        # Commit transaction
        await self.db_session.commit()

        # Return result
        return {
            "sprinkler_design": {
                "density": fire_result.sprinkler_design.density,
                "area_of_application": (
                    fire_result.sprinkler_design.area_of_application
                ),
                "coverage_per_head": (fire_result.sprinkler_design.coverage_per_head),
                "number_of_heads": (fire_result.sprinkler_design.number_of_heads),
                "flow_per_head": fire_result.sprinkler_design.flow_per_head,
            },
            "total_demand": fire_result.total_demand,
            "residual_pressure": fire_result.residual_pressure,
            "main_pipe_size": fire_result.main_pipe_size,
            "riser_size": fire_result.riser_size,
            "system_type": fire_result.system_type.value,
            "unit_system": unit_system,
        }
