"""
Structural Calculation Service for coordinating structural engineering
calculations.

This service layer orchestrates structural calculations, manages data
persistence, and handles automatic recalculation when inputs change.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from ..calculations.beam_designer import (BeamDesigner, BeamDesignResult,
                                          BeamGeometry, BeamLoads,
                                          BeamSupportType)
from ..calculations.beam_designer import \
    MaterialProperties as BeamMaterialProperties
from ..calculations.beam_designer import MaterialType as BeamMaterialType
from ..calculations.column_designer import ColumnDesigner
from ..calculations.foundation_designer import FoundationDesigner
from ..calculations.load_calculator import (BuildingData, Component,
                                            LoadCalculator, OccupancyType,
                                            SeismicData)
from ..models.calculation_sheet import CalculationSheet
from ..models.structural_design import StructuralDesign
from ..repositories.calculation_sheet_repository import \
    CalculationSheetRepository
from ..repositories.structural_design_repository import \
    StructuralDesignRepository
from .recalculation_service import RecalculationService


class LoadCalculationResult:
    """Result from load calculations."""

    def __init__(
        self,
        calculation_id: int,
        project_id: str,
        dead_load: float,
        live_load: float,
        wind_load: Optional[float] = None,
        seismic_load: Optional[float] = None,
        total_load: Optional[float] = None,
        unit_system: str = "imperial",
        created_at: Optional[datetime] = None,
    ):
        self.calculation_id = calculation_id
        self.project_id = project_id
        self.dead_load = dead_load
        self.live_load = live_load
        self.wind_load = wind_load
        self.seismic_load = seismic_load
        self.total_load = total_load or self._calculate_total()
        self.unit_system = unit_system
        self.created_at = created_at or datetime.utcnow()

    def _calculate_total(self) -> float:
        """Calculate total load from components."""
        total = self.dead_load + self.live_load
        if self.wind_load:
            total += self.wind_load
        if self.seismic_load:
            total += self.seismic_load
        return total


class StructuralCalculationService:
    """
    Service for structural engineering calculations.

    Coordinates calculation engines, manages data persistence,
    and handles automatic recalculation on input changes.
    """

    def __init__(
        self,
        db_session: AsyncSession,
        calculation_sheet_repo: Optional[CalculationSheetRepository] = None,
        structural_design_repo: Optional[StructuralDesignRepository] = None,
        recalculation_service: Optional[RecalculationService] = None,
    ):
        """
        Initialize the structural calculation service.

        Args:
            db_session: Database session for persistence
            calculation_sheet_repo: Repository for calculation sheets
            structural_design_repo: Repository for structural designs
            recalculation_service: Service for managing recalculation cascades
        """
        self.db_session = db_session
        self.calculation_sheet_repo = (
            calculation_sheet_repo or CalculationSheetRepository(db_session)
        )
        self.structural_design_repo = (
            structural_design_repo or StructuralDesignRepository(db_session)
        )
        self.recalculation_service = recalculation_service or RecalculationService(
            db_session
        )

        # Initialize calculation engines
        self.load_calculator = LoadCalculator()
        self.beam_designer = BeamDesigner()
        self.column_designer = ColumnDesigner()
        self.foundation_designer = FoundationDesigner()

    async def calculate_loads(
        self,
        project_id: str,
        building_data: Dict[str, Any],
        load_types: List[str],
        user_id: str,
        unit_system: str = "imperial",
    ) -> LoadCalculationResult:
        """
        Calculate structural loads per ASCE 7.

        Args:
            project_id: Project identifier
            building_data: Building parameters (height, width, length, etc.)
            load_types: List of load types to calculate
                       (dead, live, wind, seismic)
            user_id: User performing the calculation
            unit_system: Unit system (imperial or metric)

        Returns:
            LoadCalculationResult with calculated loads

        Raises:
            ValueError: If building_data or load_types are invalid
        """
        # Parse building data
        building = self._parse_building_data(building_data)

        # Initialize load values
        dead_load = 0.0
        live_load = 0.0
        wind_load = None
        seismic_load = None

        # Calculate dead load
        if "dead" in load_types:
            components = self._parse_components(building_data.get("components", []))
            dead_load = self.load_calculator.calculate_dead_load(components)

        # Calculate live load
        if "live" in load_types:
            occupancy = OccupancyType(building_data.get("occupancy", "office"))
            area = building_data.get("floor_area", building.width * building.length)
            live_load = self.load_calculator.calculate_live_load(occupancy, area)

        # Calculate wind load
        if "wind" in load_types:
            wind_speed = building_data.get("wind_speed", 90.0)  # mph
            wind_result = self.load_calculator.calculate_wind_load(building, wind_speed)
            # Convert pressure to total load (pressure * area)
            wind_area = building.height * building.width
            wind_load = wind_result.design_pressure * wind_area

        # Calculate seismic load
        if "seismic" in load_types:
            seismic_data = self._parse_seismic_data(building_data.get("seismic", {}))
            seismic_result = self.load_calculator.calculate_seismic_load(
                building, seismic_data
            )
            seismic_load = seismic_result.base_shear

        # Create calculation sheet
        calculation_sheet = CalculationSheet(
            project_id=project_id,
            title=(
                f"Load Calculation - " f"{datetime.utcnow().strftime('%Y-%m-%d %H:%M')}"
            ),
            description="Structural load calculations per ASCE 7",
            calculation_type="structural_loads",
            inputs={
                "building_data": building_data,
                "load_types": load_types,
            },
            outputs={
                "dead_load": dead_load,
                "live_load": live_load,
                "wind_load": wind_load,
                "seismic_load": seismic_load,
                "total_load": (
                    dead_load + live_load + (wind_load or 0) + (seismic_load or 0)
                ),
            },
            formulas=[
                "Dead Load: Sum of component weights",
                "Live Load: ASCE 7 Table 4.3-1",
                "Wind Load: ASCE 7 Chapter 27",
                "Seismic Load: ASCE 7 Chapter 12",
            ],
            references=["ASCE 7-16"],
            units=unit_system,
            created_by=user_id,
            status="approved",
        )

        # Save to database
        saved_sheet = await self.calculation_sheet_repo.create(calculation_sheet)
        await self.db_session.commit()

        return LoadCalculationResult(
            calculation_id=saved_sheet.id,
            project_id=project_id,
            dead_load=dead_load,
            live_load=live_load,
            wind_load=wind_load,
            seismic_load=seismic_load,
            unit_system=unit_system,
        )

    def _parse_building_data(self, building_data: Dict[str, Any]) -> BuildingData:
        """Parse building data dictionary into BuildingData object."""
        return BuildingData(
            height=building_data.get("height", 20.0),
            width=building_data.get("width", 50.0),
            length=building_data.get("length", 100.0),
            exposure_category=building_data.get("exposure_category", "C"),
        )

    def _parse_components(
        self, components_data: List[Dict[str, Any]]
    ) -> List[Component]:
        """Parse component data into Component objects."""
        components = []
        for comp_data in components_data:
            component = Component(
                name=comp_data.get("name", "Unknown"),
                weight_per_area=comp_data.get("weight_per_area", 0.0),
                area=comp_data.get("area", 0.0),
            )
            components.append(component)
        return components

    def _parse_seismic_data(self, seismic_data: Dict[str, Any]) -> SeismicData:
        """Parse seismic data dictionary into SeismicData object."""
        return SeismicData(
            ss=seismic_data.get("ss", 0.5),
            s1=seismic_data.get("s1", 0.2),
            site_class=seismic_data.get("site_class", "D"),
            importance_factor=seismic_data.get("importance_factor", 1.0),
            response_modification_factor=seismic_data.get(
                "response_modification_factor", 8.0
            ),
        )

    async def design_beam(
        self,
        project_id: str,
        loads: Dict[str, Any],
        span: float,
        material: Dict[str, Any],
        user_id: str,
        unit_system: str = "imperial",
        support_type: str = "simply_supported",
        trial_geometry: Optional[Dict[str, Any]] = None,
    ) -> BeamDesignResult:
        """
        Design beam with deflection and stress checks.

        Args:
            project_id: Project identifier
            loads: Beam loads (uniform_load, point_loads, moment_loads)
            span: Beam span in feet
            material: Material properties
            user_id: User performing the design
            unit_system: Unit system (imperial or metric)
            support_type: Support conditions
            trial_geometry: Optional trial beam geometry

        Returns:
            BeamDesignResult with design adequacy and details

        Raises:
            ValueError: If inputs are invalid
        """
        # Parse inputs
        beam_loads = BeamLoads(
            uniform_load=loads.get("uniform_load", 0.0),
            point_loads=[
                (float(pl[0]), float(pl[1])) for pl in loads.get("point_loads", [])
            ],
            moment_loads=[
                (float(ml[0]), float(ml[1])) for ml in loads.get("moment_loads", [])
            ],
        )

        beam_material = BeamMaterialProperties(
            material_type=BeamMaterialType(material.get("material_type", "steel")),
            yield_strength=material.get("yield_strength", 36000.0),
            elastic_modulus=material.get("elastic_modulus", 29000000.0),
            density=material.get("density", 490.0),
            allowable_stress_factor=material.get("allowable_stress_factor", 0.6),
        )

        support_type_enum = BeamSupportType(support_type)

        trial_geom: Optional[BeamGeometry] = None
        if trial_geometry is not None:
            trial_geom = BeamGeometry(
                depth=trial_geometry["depth"],
                width=trial_geometry["width"],
                web_thickness=trial_geometry.get("web_thickness"),
                flange_thickness=trial_geometry.get("flange_thickness"),
            )

        # Run beam design calculation
        result = self.beam_designer.design_beam(
            span=span,
            loads=beam_loads,
            material=beam_material,
            support_type=support_type_enum,
            trial_geometry=trial_geom,
        )

        # Create calculation sheet
        calculation_sheet = CalculationSheet(
            project_id=project_id,
            title=(f"Beam Design - " f"{datetime.utcnow().strftime('%Y-%m-%d %H:%M')}"),
            description="Beam design with deflection and stress checks",
            calculation_type="beam_design",
            inputs={
                "span": span,
                "loads": loads,
                "material": material,
                "support_type": support_type,
                "trial_geometry": trial_geometry,
            },
            outputs={
                "is_adequate": result.is_adequate,
                "max_moment": result.max_moment,
                "max_shear": result.max_shear,
                "max_stress": result.max_stress,
                "allowable_stress": result.allowable_stress,
                "max_deflection": result.max_deflection,
                "allowable_deflection": result.allowable_deflection,
                "stress_ratio": result.stress_ratio,
                "deflection_ratio": result.deflection_ratio,
                "utilization_ratio": result.utilization_ratio,
                "warnings": result.warnings,
            },
            formulas=[
                "Flexural stress: fb = M / S",
                "Shear stress: fv = V / A",
                "Deflection: δ = 5wL⁴ / (384EI) for simply supported",
                "Allowable stress: Fa = Fy × allowable_stress_factor",
            ],
            references=["AISC 360", "ACI 318", "NDS"],
            units=unit_system,
            created_by=user_id,
            status="approved",
        )

        await self.calculation_sheet_repo.create(calculation_sheet)

        # Create structural design record linked to the calculation sheet
        structural_design = StructuralDesign(
            project_id=project_id,
            calculation_sheet_id=calculation_sheet.id,
            title=(f"Beam Design - " f"{datetime.utcnow().strftime('%Y-%m-%d %H:%M')}"),
            description=(
                f"Beam design: span={span} ft, "
                f"material={material.get('material_type', 'steel')}"
            ),
            design_type="beam",
            loads=loads,
            material_properties=material,
            geometry={
                "depth": result.geometry.depth,
                "width": result.geometry.width,
                "web_thickness": result.geometry.web_thickness,
                "flange_thickness": result.geometry.flange_thickness,
                "span": span,
                "support_type": support_type,
            },
            design_results={
                "is_adequate": result.is_adequate,
                "max_moment": result.max_moment,
                "max_shear": result.max_shear,
                "max_stress": result.max_stress,
                "allowable_stress": result.allowable_stress,
                "max_deflection": result.max_deflection,
                "allowable_deflection": result.allowable_deflection,
                "warnings": result.warnings,
            },
            stress_ratios={
                "stress_ratio": result.stress_ratio,
                "deflection_ratio": result.deflection_ratio,
                "utilization_ratio": result.utilization_ratio,
            },
            code_references={"codes": ["AISC 360", "ACI 318", "NDS"]},
            units=unit_system,
            status="draft",
            created_by=user_id,
        )

        await self.structural_design_repo.create(structural_design)
        await self.db_session.commit()

        return result

    async def design_foundation(
        self,
        project_id: str,
        loads: Dict[str, Any],
        soil_properties: Dict[str, Any],
        geometry: Dict[str, Any],
        user_id: str,
        unit_system: str = "imperial",
    ):
        """
        Design foundation with bearing capacity and settlement analysis.

        Args:
            project_id: Project identifier
            loads: Foundation loads (vertical_load, moment_x, moment_y,
                   horizontal_x, horizontal_y)
            soil_properties: Soil properties (bearing_capacity, unit_weight,
                           friction_angle, cohesion, elastic_modulus)
            geometry: Foundation geometry (foundation_type, length, width,
                     diameter, depth, thickness)
            user_id: User performing the design
            unit_system: Unit system (imperial or metric)

        Returns:
            FoundationDesignResult with design adequacy and details

        Raises:
            ValueError: If inputs are invalid
        """
        from ..calculations.foundation_designer import (FoundationDesignResult,
                                                        FoundationGeometry,
                                                        FoundationLoads,
                                                        FoundationType,
                                                        SoilProperties)

        # Parse inputs
        foundation_loads = FoundationLoads(
            vertical_load=loads.get("vertical_load", 0.0),
            moment_x=loads.get("moment_x", 0.0),
            moment_y=loads.get("moment_y", 0.0),
            horizontal_x=loads.get("horizontal_x", 0.0),
            horizontal_y=loads.get("horizontal_y", 0.0),
        )

        soil_props = SoilProperties(
            bearing_capacity=soil_properties.get("bearing_capacity", 2000.0),
            unit_weight=soil_properties.get("unit_weight", 120.0),
            friction_angle=soil_properties.get("friction_angle", 30.0),
            cohesion=soil_properties.get("cohesion", 0.0),
            elastic_modulus=soil_properties.get("elastic_modulus", 5000.0),
        )

        foundation_geometry = FoundationGeometry(
            foundation_type=FoundationType(
                geometry.get("foundation_type", "spread_footing")
            ),
            length=geometry.get("length"),
            width=geometry.get("width"),
            diameter=geometry.get("diameter"),
            depth=geometry.get("depth", 2.0),
            thickness=geometry.get("thickness", 18.0),
        )

        # Run foundation design calculation
        result = self.foundation_designer.design_foundation(
            loads=foundation_loads,
            soil_properties=soil_props,
            geometry=foundation_geometry,
        )

        # Create calculation sheet
        calculation_sheet = CalculationSheet(
            project_id=project_id,
            title=(
                f"Foundation Design - "
                f"{datetime.utcnow().strftime('%Y-%m-%d %H:%M')}"
            ),
            description="Foundation design with bearing capacity and "
            "settlement analysis",
            calculation_type="foundation_design",
            inputs={
                "loads": loads,
                "soil_properties": soil_properties,
                "geometry": geometry,
            },
            outputs={
                "is_adequate": result.is_adequate,
                "bearing_pressure": result.bearing_pressure,
                "allowable_bearing_capacity": (result.allowable_bearing_capacity),
                "bearing_ratio": result.bearing_ratio,
                "settlement": result.settlement,
                "allowable_settlement": result.allowable_settlement,
                "reinforcement_area": result.reinforcement_area,
                "warnings": result.warnings,
            },
            formulas=[
                "Bearing pressure: q = P/A (with eccentric loading effects)",
                "Allowable capacity: q_allow = q_ult/FS + γ*D",
                "Settlement: S = q*B*(1-ν²)/E_s*I_f",
                "Reinforcement: A_s = M/(φ*f_y*d)",
            ],
            references=["ACI 318", "IBC"],
            units=unit_system,
            created_by=user_id,
            status="approved",
        )

        await self.calculation_sheet_repo.create(calculation_sheet)

        # Create structural design record linked to the calculation sheet
        structural_design = StructuralDesign(
            project_id=project_id,
            calculation_sheet_id=calculation_sheet.id,
            title=(
                f"Foundation Design - "
                f"{datetime.utcnow().strftime('%Y-%m-%d %H:%M')}"
            ),
            description=(
                f"Foundation design: type="
                f"{geometry.get('foundation_type', 'spread_footing')}, "
                f"bearing_capacity="
                f"{soil_properties.get('bearing_capacity')} psf"
            ),
            design_type="foundation",
            loads=loads,
            material_properties=soil_properties,
            geometry={
                "foundation_type": geometry.get("foundation_type", "spread_footing"),
                "length": result.geometry.length,
                "width": result.geometry.width,
                "diameter": result.geometry.diameter,
                "depth": result.geometry.depth,
                "thickness": result.geometry.thickness,
            },
            design_results={
                "is_adequate": result.is_adequate,
                "bearing_pressure": result.bearing_pressure,
                "allowable_bearing_capacity": (result.allowable_bearing_capacity),
                "settlement": result.settlement,
                "allowable_settlement": result.allowable_settlement,
                "reinforcement_area": result.reinforcement_area,
                "warnings": result.warnings,
            },
            stress_ratios={
                "bearing_ratio": result.bearing_ratio,
            },
            code_references={"codes": ["ACI 318", "IBC"]},
            units=unit_system,
            status="draft",
            created_by=user_id,
        )

        await self.structural_design_repo.create(structural_design)
        await self.db_session.commit()

        return result

    async def design_column(
        self,
        project_id: str,
        loads: Dict[str, Any],
        length: float,
        material: Dict[str, Any],
        geometry: Dict[str, Any],
        user_id: str,
        unit_system: str = "imperial",
        end_condition: str = "pinned_pinned",
    ):
        """
        Design column with buckling analysis.

        Args:
            project_id: Project identifier
            loads: Column loads (axial_load, moment_x, moment_y)
            length: Column length in inches
            material: Material properties
            geometry: Column geometry (depth, width, or diameter)
            user_id: User performing the design
            unit_system: Unit system (imperial or metric)
            end_condition: End support conditions

        Returns:
            ColumnDesignResult with design adequacy and details

        Raises:
            ValueError: If inputs are invalid
        """
        from ..calculations.column_designer import (ColumnDesignResult,
                                                    ColumnGeometry,
                                                    ColumnLoads, EndCondition)
        from ..calculations.column_designer import \
            MaterialProperties as ColumnMaterialProperties
        from ..calculations.column_designer import \
            MaterialType as ColumnMaterialType

        # Parse inputs
        column_loads = ColumnLoads(
            axial_load=loads.get("axial_load", 0.0),
            moment_x=loads.get("moment_x", 0.0),
            moment_y=loads.get("moment_y", 0.0),
        )

        column_material = ColumnMaterialProperties(
            material_type=ColumnMaterialType(material.get("material_type", "steel")),
            yield_strength=material.get("yield_strength", 36000.0),
            elastic_modulus=material.get("elastic_modulus", 29000000.0),
            density=material.get("density", 490.0),
            allowable_stress_factor=material.get("allowable_stress_factor", 0.6),
        )

        column_geometry = ColumnGeometry(
            depth=geometry.get("depth"),
            width=geometry.get("width"),
            diameter=geometry.get("diameter"),
        )

        end_condition_enum = EndCondition(end_condition)

        # Run column design calculation
        result = self.column_designer.design_column(
            length=length,
            loads=column_loads,
            material=column_material,
            geometry=column_geometry,
            end_condition=end_condition_enum,
        )

        # Create calculation sheet
        calculation_sheet = CalculationSheet(
            project_id=project_id,
            title=(
                f"Column Design - " f"{datetime.utcnow().strftime('%Y-%m-%d %H:%M')}"
            ),
            description="Column design with buckling analysis",
            calculation_type="column_design",
            inputs={
                "length": length,
                "loads": loads,
                "material": material,
                "geometry": geometry,
                "end_condition": end_condition,
            },
            outputs={
                "is_adequate": result.is_adequate,
                "axial_capacity": result.axial_capacity,
                "buckling_capacity": result.buckling_capacity,
                "moment_capacity_x": result.moment_capacity_x,
                "moment_capacity_y": result.moment_capacity_y,
                "combined_stress_ratio": result.combined_stress_ratio,
                "slenderness_ratio": result.slenderness_ratio,
                "effective_length": result.effective_length,
                "warnings": result.warnings,
            },
            formulas=[
                "Axial capacity: P = A × Fy × factor",
                "Euler buckling: Pcr = π²EI / (KL)²",
                "Slenderness ratio: λ = KL / r",
                "Combined stress: P/Pn + Mx/Mnx + My/Mny",
            ],
            references=["AISC 360", "ACI 318"],
            units=unit_system,
            created_by=user_id,
            status="approved",
        )

        await self.calculation_sheet_repo.create(calculation_sheet)

        # Create structural design record linked to the calculation sheet
        structural_design = StructuralDesign(
            project_id=project_id,
            calculation_sheet_id=calculation_sheet.id,
            title=(
                f"Column Design - " f"{datetime.utcnow().strftime('%Y-%m-%d %H:%M')}"
            ),
            description=(
                f"Column design: length={length} in, "
                f"material={material.get('material_type', 'steel')}"
            ),
            design_type="column",
            loads=loads,
            material_properties=material,
            geometry={
                "depth": result.geometry.depth,
                "width": result.geometry.width,
                "diameter": result.geometry.diameter,
                "length": length,
                "end_condition": end_condition,
            },
            design_results={
                "is_adequate": result.is_adequate,
                "axial_capacity": result.axial_capacity,
                "buckling_capacity": result.buckling_capacity,
                "moment_capacity_x": result.moment_capacity_x,
                "moment_capacity_y": result.moment_capacity_y,
                "effective_length": result.effective_length,
                "warnings": result.warnings,
            },
            stress_ratios={
                "combined_stress_ratio": result.combined_stress_ratio,
                "slenderness_ratio": result.slenderness_ratio,
            },
            code_references={"codes": ["AISC 360", "ACI 318"]},
            units=unit_system,
            status="draft",
            created_by=user_id,
        )

        await self.structural_design_repo.create(structural_design)
        await self.db_session.commit()

        return result

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
            dependency_type: Type of dependency (e.g., "load_input", "material_property")
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
            It determines the calculation type and calls the appropriate
            calculation method.
        """
        try:
            # Determine calculation type and recalculate
            if sheet.calculation_type == "structural_loads":
                # Recalculate loads
                result = await self.calculate_loads(
                    project_id=sheet.project_id,
                    building_data=sheet.inputs.get("building_data", {}),
                    load_types=sheet.inputs.get("load_types", []),
                    user_id=user_id,
                    unit_system=sheet.units or "imperial",
                )
                # Update the existing sheet
                update_data = {
                    "outputs": {
                        "dead_load": result.dead_load,
                        "live_load": result.live_load,
                        "wind_load": result.wind_load,
                        "seismic_load": result.seismic_load,
                        "total_load": result.total_load,
                    },
                    "updated_by": user_id,
                    "updated_at": datetime.utcnow(),
                    "status": "approved",
                }
                return await self.calculation_sheet_repo.update(sheet.id, update_data)

            elif sheet.calculation_type == "beam_design":
                # Recalculate beam design
                result = await self.design_beam(
                    project_id=sheet.project_id,
                    loads=sheet.inputs.get("loads", {}),
                    span=sheet.inputs.get("span", 0.0),
                    material=sheet.inputs.get("material", {}),
                    user_id=user_id,
                    unit_system=sheet.units or "imperial",
                    support_type=sheet.inputs.get("support_type", "simply_supported"),
                    trial_geometry=sheet.inputs.get("trial_geometry"),
                )
                # Update the existing sheet
                update_data = {
                    "outputs": {
                        "is_adequate": result.is_adequate,
                        "max_moment": result.max_moment,
                        "max_shear": result.max_shear,
                        "max_stress": result.max_stress,
                        "allowable_stress": result.allowable_stress,
                        "max_deflection": result.max_deflection,
                        "allowable_deflection": result.allowable_deflection,
                        "stress_ratio": result.stress_ratio,
                        "deflection_ratio": result.deflection_ratio,
                        "utilization_ratio": result.utilization_ratio,
                        "warnings": result.warnings,
                    },
                    "updated_by": user_id,
                    "updated_at": datetime.utcnow(),
                    "status": "approved",
                }
                return await self.calculation_sheet_repo.update(sheet.id, update_data)

            elif sheet.calculation_type == "column_design":
                # Recalculate column design
                result = await self.design_column(
                    project_id=sheet.project_id,
                    loads=sheet.inputs.get("loads", {}),
                    length=sheet.inputs.get("length", 0.0),
                    material=sheet.inputs.get("material", {}),
                    geometry=sheet.inputs.get("geometry", {}),
                    user_id=user_id,
                    unit_system=sheet.units or "imperial",
                    end_condition=sheet.inputs.get("end_condition", "pinned_pinned"),
                )
                # Update the existing sheet
                update_data = {
                    "outputs": {
                        "is_adequate": result.is_adequate,
                        "axial_capacity": result.axial_capacity,
                        "buckling_capacity": result.buckling_capacity,
                        "moment_capacity_x": result.moment_capacity_x,
                        "moment_capacity_y": result.moment_capacity_y,
                        "combined_stress_ratio": result.combined_stress_ratio,
                        "slenderness_ratio": result.slenderness_ratio,
                        "effective_length": result.effective_length,
                        "warnings": result.warnings,
                    },
                    "updated_by": user_id,
                    "updated_at": datetime.utcnow(),
                    "status": "approved",
                }
                return await self.calculation_sheet_repo.update(sheet.id, update_data)

            elif sheet.calculation_type == "foundation_design":
                # Recalculate foundation design
                result = await self.design_foundation(
                    project_id=sheet.project_id,
                    loads=sheet.inputs.get("loads", {}),
                    soil_properties=sheet.inputs.get("soil_properties", {}),
                    geometry=sheet.inputs.get("geometry", {}),
                    user_id=user_id,
                    unit_system=sheet.units or "imperial",
                )
                # Update the existing sheet
                update_data = {
                    "outputs": {
                        "is_adequate": result.is_adequate,
                        "bearing_pressure": result.bearing_pressure,
                        "allowable_bearing_capacity": result.allowable_bearing_capacity,
                        "bearing_ratio": result.bearing_ratio,
                        "settlement": result.settlement,
                        "allowable_settlement": result.allowable_settlement,
                        "reinforcement_area": result.reinforcement_area,
                        "warnings": result.warnings,
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
                f"Error recalculating sheet {sheet.id}: {str(e)}", exc_info=True
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
