"""
Civil Calculation Service for coordinating civil engineering calculations.

This service layer orchestrates civil engineering calculations, manages data
persistence, and handles automatic recalculation when inputs change.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from ..calculations.civil_calculator import (CivilCalculator,
                                             GradingDesignResult, RainfallData,
                                             SiteData, StormwaterDesignResult,
                                             UtilityDesignResult, UtilityLoads)
from ..models.calculation_sheet import CalculationSheet
from ..models.civil_design import CivilDesign
from ..repositories.calculation_sheet_repository import \
    CalculationSheetRepository
from ..repositories.civil_design_repository import CivilDesignRepository
from ..utils.unit_converter import UnitConverter, UnitSystem
from .recalculation_service import RecalculationService


class CivilCalculationService:
    """
    Service for civil engineering calculations.

    Coordinates calculation engines, manages data persistence,
    and handles automatic recalculation on input changes.
    """

    def __init__(
        self,
        db_session: AsyncSession,
        calculation_sheet_repo: Optional[CalculationSheetRepository] = None,
        civil_design_repo: Optional[CivilDesignRepository] = None,
        recalculation_service: Optional[RecalculationService] = None,
    ):
        """
        Initialize the civil calculation service.

        Args:
            db_session: Database session for persistence
            calculation_sheet_repo: Repository for calculation sheets
            civil_design_repo: Repository for civil designs
            recalculation_service: Service for managing recalculation cascades
        """
        self.db_session = db_session
        self.calculation_sheet_repo = (
            calculation_sheet_repo or CalculationSheetRepository(db_session)
        )
        self.civil_design_repo = civil_design_repo or CivilDesignRepository(db_session)
        self.recalculation_service = recalculation_service or RecalculationService(
            db_session
        )

        # Initialize calculation engines
        self.civil_calculator = CivilCalculator()
        self.unit_converter = UnitConverter()

    async def design_grading(
        self,
        project_id: str,
        site_data: Dict[str, Any],
        target_elevations: Dict[str, float],
        user_id: str,
        unit_system: str = "imperial",
        grid_spacing: float = 50.0,
    ) -> GradingDesignResult:
        """
        Design site grading with cut/fill analysis.

        Integrates grading calculations with service layer and creates
        calculation sheet with version control.

        Args:
            project_id: Project identifier
            site_data: Site parameters (area, existing_elevations, soil_type, etc.)
            target_elevations: Proposed elevation at key points
            user_id: User performing the design
            unit_system: Unit system (imperial or metric)
            grid_spacing: Distance between grid points (feet)

        Returns:
            GradingDesignResult with cut/fill volumes and analysis

        Raises:
            ValueError: If site_data or target_elevations are invalid
        """
        # Parse site data
        site = self._parse_site_data(site_data)

        # Validate target elevations
        if not target_elevations:
            raise ValueError("Target elevations cannot be empty")

        # Run grading design calculation
        result = self.civil_calculator.design_grading(
            site_data=site,
            target_elevations=target_elevations,
            grid_spacing=grid_spacing,
        )

        # Create calculation sheet
        calculation_sheet = CalculationSheet(
            project_id=project_id,
            title=f"Grading Design - {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}",
            description="Site grading design with cut/fill analysis",
            calculation_type="grading_design",
            inputs={
                "site_data": site_data,
                "target_elevations": target_elevations,
                "grid_spacing": grid_spacing,
            },
            outputs={
                "cut_volume": result.cut_volume,
                "fill_volume": result.fill_volume,
                "net_volume": result.net_volume,
                "max_cut_depth": result.max_cut_depth,
                "max_fill_depth": result.max_fill_depth,
                "average_slope": result.average_slope,
                "grading_points_count": len(result.grading_points),
            },
            formulas=[
                "Cut/Fill Volume: V = Σ(depth × area) / 27 (cubic yards)",
                "Net Volume: Net = Cut - Fill",
                "Average Slope: Slope = Σ(Δz/distance) × 100%",
            ],
            references=["Civil Engineering Reference Manual", "AASHTO Standards"],
            units=unit_system,
            created_by=user_id,
            status="approved",
        )

        # Save calculation sheet
        saved_sheet = await self.calculation_sheet_repo.create(calculation_sheet)

        # Create civil design record
        civil_design = CivilDesign(
            project_id=project_id,
            calculation_sheet_id=saved_sheet.id,
            title=f"Grading Design - {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}",
            description=f"Site grading: {result.cut_volume:.1f} CY cut, {result.fill_volume:.1f} CY fill",
            design_type="grading",
            site_parameters={
                "area": site_data.get("area"),
                "soil_type": site_data.get("soil_type"),
                "existing_elevations": site_data.get("existing_elevations"),
                "permeability": site_data.get("permeability"),
                "slope_percent": site_data.get("slope_percent"),
            },
            design_criteria={
                "target_elevations": target_elevations,
                "grid_spacing": grid_spacing,
            },
            design_results={
                "cut_volume": result.cut_volume,
                "fill_volume": result.fill_volume,
                "net_volume": result.net_volume,
                "max_cut_depth": result.max_cut_depth,
                "max_fill_depth": result.max_fill_depth,
                "average_slope": result.average_slope,
                "grading_points": [
                    {
                        "x": point.x,
                        "y": point.y,
                        "existing_elevation": point.existing_elevation,
                        "proposed_elevation": point.proposed_elevation,
                        "cut_fill": point.cut_fill,
                    }
                    for point in result.grading_points
                ],
            },
            units=unit_system,
            status="draft",
            created_by=user_id,
        )

        await self.civil_design_repo.create(civil_design)
        await self.db_session.commit()

        return result

    async def design_stormwater(
        self,
        project_id: str,
        site_data: Dict[str, Any],
        rainfall_data: Dict[str, Any],
        user_id: str,
        unit_system: str = "imperial",
        release_rate: Optional[float] = None,
    ) -> StormwaterDesignResult:
        """
        Design stormwater management system.

        Integrates stormwater calculations with service layer and creates
        calculation sheet with version control.

        Args:
            project_id: Project identifier
            site_data: Site parameters for runoff calculation
            rainfall_data: Rainfall intensity and duration data
            user_id: User performing the design
            unit_system: Unit system (imperial or metric)
            release_rate: Optional controlled release rate (CFS)

        Returns:
            StormwaterDesignResult with runoff volumes and system sizing

        Raises:
            ValueError: If site_data or rainfall_data are invalid
        """
        # Parse input data
        site = self._parse_site_data(site_data)
        rainfall = self._parse_rainfall_data(rainfall_data)

        # Calculate runoff rate
        runoff_rate = self.civil_calculator.calculate_stormwater_runoff(site, rainfall)

        # Calculate runoff volume (rate × duration × 3600 seconds/hour)
        runoff_volume = runoff_rate * rainfall.duration * 3600

        # Size detention pond if release rate provided
        detention_volume = 0.0
        detention_depth = 0.0
        if release_rate is not None and release_rate > 0:
            (
                detention_volume,
                detention_depth,
            ) = self.civil_calculator.size_detention_pond(
                runoff_volume, release_rate, rainfall.duration
            )

        # Size outlet pipe (use release rate or 50% of peak runoff)
        outlet_flow = release_rate if release_rate else runoff_rate * 0.5
        outlet_size = self.civil_calculator.calculate_pipe_size(
            outlet_flow, slope=2.0  # 2% slope for outlet
        )

        # Size main collection pipes (assume 3 pipe segments)
        pipe_sizes = {}
        for i in range(3):
            segment_flow = runoff_rate * (1.0 - i * 0.2)  # Decreasing flow upstream
            pipe_diameter = self.civil_calculator.calculate_pipe_size(
                segment_flow, slope=1.0  # 1% slope for collection
            )
            pipe_sizes[f"pipe_{i+1}"] = pipe_diameter

        # Create result
        result = StormwaterDesignResult(
            runoff_rate=runoff_rate,
            runoff_volume=runoff_volume,
            detention_volume=detention_volume,
            detention_depth=detention_depth,
            outlet_size=outlet_size,
            pipe_sizes=pipe_sizes,
            unit_system=unit_system,
        )

        # Create calculation sheet
        calculation_sheet = CalculationSheet(
            project_id=project_id,
            title=f"Stormwater Design - {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}",
            description="Stormwater management system design",
            calculation_type="stormwater_design",
            inputs={
                "site_data": site_data,
                "rainfall_data": rainfall_data,
                "release_rate": release_rate,
            },
            outputs={
                "runoff_rate": result.runoff_rate,
                "runoff_volume": result.runoff_volume,
                "detention_volume": result.detention_volume,
                "detention_depth": result.detention_depth,
                "outlet_size": result.outlet_size,
                "pipe_sizes": result.pipe_sizes,
            },
            formulas=[
                "Rational Method: Q = C × I × A",
                "Runoff Volume: V = Q × t × 3600",
                "Detention Volume: V_det = V_in - V_out",
                "Manning's Equation: Q = (1.486/n) × A × R^(2/3) × S^(1/2)",
            ],
            references=["ASCE Manual of Practice No. 77", "Local Stormwater Manual"],
            units=unit_system,
            created_by=user_id,
            status="approved",
        )

        # Save calculation sheet
        saved_sheet = await self.calculation_sheet_repo.create(calculation_sheet)

        # Create civil design record
        civil_design = CivilDesign(
            project_id=project_id,
            calculation_sheet_id=saved_sheet.id,
            title=f"Stormwater Design - {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}",
            description=f"Stormwater system: {result.runoff_rate:.1f} CFS peak runoff",
            design_type="stormwater",
            site_parameters={
                "area": site_data.get("area"),
                "soil_type": site_data.get("soil_type"),
                "permeability": site_data.get("permeability"),
            },
            design_criteria={
                "rainfall_intensity": rainfall_data.get("intensity"),
                "return_period": rainfall_data.get("return_period"),
                "runoff_coefficient": rainfall_data.get("runoff_coefficient"),
                "release_rate": release_rate,
            },
            design_results={
                "runoff_rate": result.runoff_rate,
                "runoff_volume": result.runoff_volume,
                "detention_volume": result.detention_volume,
                "detention_depth": result.detention_depth,
                "outlet_size": result.outlet_size,
                "pipe_sizes": result.pipe_sizes,
            },
            units=unit_system,
            status="draft",
            created_by=user_id,
        )

        await self.civil_design_repo.create(civil_design)
        await self.db_session.commit()

        return result

    async def design_utilities(
        self,
        project_id: str,
        site_data: Dict[str, Any],
        utility_loads: Dict[str, Any],
        user_id: str,
        unit_system: str = "imperial",
        pressure_available: float = 60.0,
    ) -> UtilityDesignResult:
        """
        Design utility connections and sizing.

        Integrates utility calculations with service layer and creates
        calculation sheet with version control.

        Args:
            project_id: Project identifier
            site_data: Site parameters for utility routing
            utility_loads: Utility load requirements (water, sewer, gas)
            user_id: User performing the design
            unit_system: Unit system (imperial or metric)
            pressure_available: Available water pressure (PSI)

        Returns:
            UtilityDesignResult with utility sizing and requirements

        Raises:
            ValueError: If utility_loads are invalid
        """
        # Parse utility loads
        loads = self._parse_utility_loads(utility_loads)

        # Design water service
        (
            water_service_size,
            water_pressure_required,
        ) = self.civil_calculator.design_water_service(
            loads.water_demand, pressure_available
        )

        # Design sewer service
        sewer_service_size, sewer_slope = self.civil_calculator.design_sewer_service(
            loads.sewer_flow
        )

        # Design gas service (if required)
        gas_service_size = None
        if loads.gas_demand is not None and loads.gas_demand > 0:
            # Simplified gas sizing based on demand
            if loads.gas_demand <= 100:
                gas_service_size = 1.0  # 1" service
            elif loads.gas_demand <= 300:
                gas_service_size = 1.25  # 1.25" service
            elif loads.gas_demand <= 600:
                gas_service_size = 1.5  # 1.5" service
            else:
                gas_service_size = 2.0  # 2" service

        # Create result
        result = UtilityDesignResult(
            water_service_size=water_service_size,
            water_pressure_required=water_pressure_required,
            sewer_service_size=sewer_service_size,
            sewer_slope=sewer_slope,
            gas_service_size=gas_service_size,
            unit_system=unit_system,
        )

        # Create calculation sheet
        calculation_sheet = CalculationSheet(
            project_id=project_id,
            title=f"Utility Design - {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}",
            description="Utility connections and sizing design",
            calculation_type="utility_design",
            inputs={
                "site_data": site_data,
                "utility_loads": utility_loads,
                "pressure_available": pressure_available,
            },
            outputs={
                "water_service_size": result.water_service_size,
                "water_pressure_required": result.water_pressure_required,
                "sewer_service_size": result.sewer_service_size,
                "sewer_slope": result.sewer_slope,
                "gas_service_size": result.gas_service_size,
            },
            formulas=[
                "Water Service: Based on fixture demand and pressure loss",
                "Sewer Service: Based on flow rate and minimum slopes",
                "Gas Service: Based on BTU demand and pressure drop",
            ],
            references=["International Plumbing Code (IPC)", "Local Utility Standards"],
            units=unit_system,
            created_by=user_id,
            status="approved",
        )

        # Save calculation sheet
        saved_sheet = await self.calculation_sheet_repo.create(calculation_sheet)

        # Create civil design record
        civil_design = CivilDesign(
            project_id=project_id,
            calculation_sheet_id=saved_sheet.id,
            title=f"Utility Design - {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}",
            description=f'Utilities: {result.water_service_size}" water, {result.sewer_service_size}" sewer',
            design_type="utilities",
            site_parameters={
                "area": site_data.get("area"),
                "soil_type": site_data.get("soil_type"),
            },
            design_criteria={
                "water_demand": utility_loads.get("water_demand"),
                "sewer_flow": utility_loads.get("sewer_flow"),
                "gas_demand": utility_loads.get("gas_demand"),
                "pressure_available": pressure_available,
            },
            design_results={
                "water_service_size": result.water_service_size,
                "water_pressure_required": result.water_pressure_required,
                "sewer_service_size": result.sewer_service_size,
                "sewer_slope": result.sewer_slope,
                "gas_service_size": result.gas_service_size,
            },
            units=unit_system,
            status="draft",
            created_by=user_id,
        )

        await self.civil_design_repo.create(civil_design)
        await self.db_session.commit()

        return result

    def _parse_site_data(self, site_data: Dict[str, Any]) -> SiteData:
        """Parse site data dictionary into SiteData object."""
        return SiteData(
            area=site_data.get("area", 1.0),
            existing_elevations=site_data.get("existing_elevations", {}),
            soil_type=site_data.get("soil_type", "clay"),
            permeability=site_data.get("permeability", 0.5),
            slope_percent=site_data.get("slope_percent", 2.0),
        )

    def _parse_rainfall_data(self, rainfall_data: Dict[str, Any]) -> RainfallData:
        """Parse rainfall data dictionary into RainfallData object."""
        return RainfallData(
            intensity=rainfall_data.get("intensity", 2.0),
            duration=rainfall_data.get("duration", 1.0),
            return_period=rainfall_data.get("return_period", 10),
            runoff_coefficient=rainfall_data.get("runoff_coefficient", 0.6),
        )

    def _parse_utility_loads(self, utility_loads: Dict[str, Any]) -> UtilityLoads:
        """Parse utility loads dictionary into UtilityLoads object."""
        return UtilityLoads(
            water_demand=utility_loads.get("water_demand", 20.0),
            sewer_flow=utility_loads.get("sewer_flow", 15.0),
            gas_demand=utility_loads.get("gas_demand"),
        )

    async def add_calculation_dependency(
        self,
        source_calculation_id: int,
        target_calculation_id: int,
        dependency_type: str,
        user_id: str,
        dependent_field: Optional[str] = None,
        source_field: Optional[str] = None,
    ):
        """
        Add a dependency between two calculations.

        Args:
            source_calculation_id: ID of the calculation that depends
            target_calculation_id: ID of the calculation being depended upon
            dependency_type: Type of dependency (e.g., "site_data", "elevation_input")
            user_id: User creating the dependency
            dependent_field: Field in source that depends on target
            source_field: Field in target that is depended upon

        Returns:
            Created dependency record

        Raises:
            ValueError: If adding the dependency would create a circular dependency
        """
        return await self.recalculation_service.add_dependency(
            source_calculation_id=source_calculation_id,
            target_calculation_id=target_calculation_id,
            dependency_type=dependency_type,
            user_id=user_id,
            dependent_field=dependent_field,
            source_field=source_field,
        )

    async def update_calculation_inputs(
        self,
        calculation_id: int,
        new_inputs: Dict[str, Any],
        user_id: str,
        trigger_recalculation: bool = True,
    ) -> CalculationSheet:
        """
        Update calculation inputs and optionally trigger recalculation cascade.

        Args:
            calculation_id: ID of the calculation to update
            new_inputs: New input values
            user_id: User performing the update
            trigger_recalculation: Whether to trigger recalculation of dependents

        Returns:
            Updated calculation sheet

        Raises:
            ValueError: If calculation not found
        """
        # Get the calculation sheet
        sheet = await self.calculation_sheet_repo.get_by_id(calculation_id)
        if not sheet:
            raise ValueError(f"Calculation sheet {calculation_id} not found")

        # Update inputs
        sheet.inputs.update(new_inputs)

        # Prepare update data
        update_data = {
            "inputs": sheet.inputs,
            "updated_by": user_id,
            "updated_at": datetime.utcnow(),
            "status": "draft",  # Mark as draft since inputs changed
        }

        updated_sheet = await self.calculation_sheet_repo.update(sheet.id, update_data)
        await self.db_session.commit()

        # Trigger recalculation cascade if requested
        if trigger_recalculation:
            await self.recalculation_service.trigger_recalculation_cascade(
                calculation_id=calculation_id,
                user_id=user_id,
                recalculation_callback=self._recalculate_sheet,
            )

        return updated_sheet

    async def _recalculate_sheet(
        self, sheet: CalculationSheet, user_id: str
    ) -> Optional[CalculationSheet]:
        """
        Recalculate a calculation sheet based on its type and inputs.

        Args:
            sheet: Calculation sheet to recalculate
            user_id: User triggering the recalculation

        Returns:
            Updated calculation sheet or None if recalculation not supported

        Note:
            This is a callback used by the recalculation service.
        """
        try:
            # Determine calculation type and recalculate
            if sheet.calculation_type == "grading_design":
                # Recalculate grading design
                result = await self.design_grading(
                    project_id=sheet.project_id,
                    site_data=sheet.inputs.get("site_data", {}),
                    target_elevations=sheet.inputs.get("target_elevations", {}),
                    user_id=user_id,
                    unit_system=sheet.units or "imperial",
                    grid_spacing=sheet.inputs.get("grid_spacing", 50.0),
                )
                # Update the existing sheet
                update_data = {
                    "outputs": {
                        "cut_volume": result.cut_volume,
                        "fill_volume": result.fill_volume,
                        "net_volume": result.net_volume,
                        "max_cut_depth": result.max_cut_depth,
                        "max_fill_depth": result.max_fill_depth,
                        "average_slope": result.average_slope,
                        "grading_points_count": len(result.grading_points),
                    },
                    "updated_by": user_id,
                    "updated_at": datetime.utcnow(),
                    "status": "approved",
                }
                return await self.calculation_sheet_repo.update(sheet.id, update_data)

            elif sheet.calculation_type == "stormwater_design":
                # Recalculate stormwater design
                result = await self.design_stormwater(
                    project_id=sheet.project_id,
                    site_data=sheet.inputs.get("site_data", {}),
                    rainfall_data=sheet.inputs.get("rainfall_data", {}),
                    user_id=user_id,
                    unit_system=sheet.units or "imperial",
                    release_rate=sheet.inputs.get("release_rate"),
                )
                # Update the existing sheet
                update_data = {
                    "outputs": {
                        "runoff_rate": result.runoff_rate,
                        "runoff_volume": result.runoff_volume,
                        "detention_volume": result.detention_volume,
                        "detention_depth": result.detention_depth,
                        "outlet_size": result.outlet_size,
                        "pipe_sizes": result.pipe_sizes,
                    },
                    "updated_by": user_id,
                    "updated_at": datetime.utcnow(),
                    "status": "approved",
                }
                return await self.calculation_sheet_repo.update(sheet.id, update_data)

            elif sheet.calculation_type == "utility_design":
                # Recalculate utility design
                result = await self.design_utilities(
                    project_id=sheet.project_id,
                    site_data=sheet.inputs.get("site_data", {}),
                    utility_loads=sheet.inputs.get("utility_loads", {}),
                    user_id=user_id,
                    unit_system=sheet.units or "imperial",
                    pressure_available=sheet.inputs.get("pressure_available", 60.0),
                )
                # Update the existing sheet
                update_data = {
                    "outputs": {
                        "water_service_size": result.water_service_size,
                        "water_pressure_required": result.water_pressure_required,
                        "sewer_service_size": result.sewer_service_size,
                        "sewer_slope": result.sewer_slope,
                        "gas_service_size": result.gas_service_size,
                    },
                    "updated_by": user_id,
                    "updated_at": datetime.utcnow(),
                    "status": "approved",
                }
                return await self.calculation_sheet_repo.update(sheet.id, update_data)

            else:
                # Unknown calculation type
                return None

        except Exception as e:
            # Log error and return None to indicate recalculation failed
            from ..core.logging import get_logger

            logger = get_logger(__name__)
            logger.error(
                f"Error recalculating civil sheet {sheet.id}: {str(e)}", exc_info=True
            )
            return None

    async def get_calculation_dependents(
        self, calculation_id: int
    ) -> List[CalculationSheet]:
        """
        Get all calculations that depend on the given calculation.

        Args:
            calculation_id: ID of the target calculation

        Returns:
            List of calculation sheets that depend on this calculation
        """
        return await self.recalculation_service.get_dependents(calculation_id)

    async def get_calculation_dependencies(
        self, calculation_id: int
    ) -> List[CalculationSheet]:
        """
        Get all calculations that the given calculation depends on.

        Args:
            calculation_id: ID of the source calculation

        Returns:
            List of calculation sheets that this calculation depends on
        """
        return await self.recalculation_service.get_dependencies(calculation_id)

    async def get_dependency_graph(
        self, calculation_id: int
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get the full dependency graph for a calculation.

        Args:
            calculation_id: ID of the calculation

        Returns:
            Dictionary with 'dependencies' and 'dependents' lists
        """
        return await self.recalculation_service.get_dependency_graph(calculation_id)
