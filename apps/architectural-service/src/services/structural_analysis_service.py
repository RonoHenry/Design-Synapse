"""Structural analysis service for engineering calculations."""

import logging
from datetime import datetime
from typing import Dict, List, Optional
from uuid import UUID, uuid4

from src.api.v1.schemas.analysis import (LoadCalculations, LoadParameters,
                                         StructuralAnalysisRequest,
                                         StructuralAnalysisResponse,
                                         StructuralIssue)
from src.api.v1.schemas.enums import (AnalysisType, CheckStatus,
                                      StructuralSystem)
from src.core.exceptions import NotFoundError, ValidationError
from src.models.design import Design
from src.models.structural_analysis import StructuralAnalysis
from src.repositories.design_repository import DesignRepository
from src.repositories.structural_analysis_repository import \
    StructuralAnalysisRepository

logger = logging.getLogger(__name__)


class StructuralAnalysisService:
    """
    Service for structural analysis and engineering calculations.

    Handles structural analysis initiation, load calculations,
    issue identification, and result management.
    """

    def __init__(
        self,
        structural_repository: StructuralAnalysisRepository,
        design_repository: DesignRepository,
    ):
        """
        Initialize StructuralAnalysisService.

        Args:
            structural_repository: Repository for structural analysis data
            design_repository: Repository for design data
        """
        self.structural_repository = structural_repository
        self.design_repository = design_repository

    async def analyze_structure(
        self,
        design_id: UUID,
        parameters: StructuralAnalysisRequest,
    ) -> StructuralAnalysis:
        """
        Initiate structural analysis for a design.

        Args:
            design_id: Design ID to analyze
            parameters: Structural analysis request parameters

        Returns:
            StructuralAnalysis model instance

        Raises:
            NotFoundError: If design not found
            ValidationError: If design data is invalid for analysis
        """
        logger.info(f"Starting structural analysis for design {design_id}")

        # Get design
        design = await self.design_repository.get(str(design_id))
        if not design:
            raise NotFoundError(f"Design {design_id} not found")

        if design.is_deleted:
            raise ValidationError("Cannot analyze deleted design")

        # Create analysis record
        analysis = StructuralAnalysis(
            id=str(uuid4()),
            design_id=str(design_id),
            design_version=design.current_version,
            structural_system=parameters.structural_system
            if isinstance(parameters.structural_system, str)
            else parameters.structural_system.value,
            analysis_type=parameters.analysis_type
            if isinstance(parameters.analysis_type, str)
            else parameters.analysis_type.value,
            status=CheckStatus.IN_PROGRESS.value,
            started_at=datetime.utcnow(),
        )

        # Save initial analysis record
        await self.structural_repository.create(analysis)

        try:
            # Perform load calculations
            load_calculations = await self.calculate_loads(
                design, parameters.load_parameters
            )

            # Identify structural issues
            issues = await self.identify_issues(analysis, load_calculations)

            # Update analysis with results
            analysis.load_calculations = load_calculations.model_dump()
            analysis.issues = [issue.model_dump() for issue in issues]
            analysis.status = CheckStatus.COMPLETED.value
            analysis.completed_at = datetime.utcnow()

            # Generate recommendations based on issues
            recommendations = self._generate_recommendations(issues)
            analysis.recommendations = recommendations

            await self.structural_repository.update(analysis)

            logger.info(f"Completed structural analysis {analysis.id}")

        except Exception as e:
            logger.error(f"Structural analysis failed: {e}")
            analysis.status = CheckStatus.FAILED.value
            analysis.completed_at = datetime.utcnow()
            await self.structural_repository.update(analysis)
            raise

        return analysis

    async def calculate_loads(
        self,
        design: Design,
        load_params: LoadParameters,
    ) -> LoadCalculations:
        """
        Calculate structural loads (dead, live, wind, seismic).

        Args:
            design: Design to analyze
            load_params: Load calculation parameters

        Returns:
            LoadCalculations with calculated loads
        """
        logger.info(f"Calculating loads for design {design.id}")

        # Extract building parameters from design
        building_type = design.building_type
        location_data = design.location_data
        metadata = design.metadata

        # Calculate dead loads based on materials and construction
        dead_loads = self._calculate_dead_loads(design, load_params)

        # Calculate live loads based on occupancy and building type
        live_loads = self._calculate_live_loads(design, load_params, building_type)

        # Calculate wind loads if wind speed provided
        wind_loads = None
        if load_params.wind_speed:
            wind_loads = self._calculate_wind_loads(design, load_params)

        # Calculate seismic loads if seismic zone provided
        seismic_loads = None
        if load_params.seismic_zone:
            seismic_loads = self._calculate_seismic_loads(design, load_params)

        return LoadCalculations(
            dead_loads=dead_loads,
            live_loads=live_loads,
            wind_loads=wind_loads,
            seismic_loads=seismic_loads,
        )

    async def identify_issues(
        self,
        analysis: StructuralAnalysis,
        load_calculations: LoadCalculations,
    ) -> List[StructuralIssue]:
        """
        Identify structural issues based on load calculations.

        Args:
            analysis: Structural analysis record
            load_calculations: Calculated loads

        Returns:
            List of structural issues identified
        """
        logger.info(f"Identifying issues for analysis {analysis.id}")

        issues = []

        # Check for excessive loads
        issues.extend(
            self._check_load_limits(load_calculations, analysis.structural_system)
        )

        # Check for structural adequacy
        issues.extend(
            self._check_structural_adequacy(
                load_calculations, analysis.structural_system
            )
        )

        # Check for deflection limits
        issues.extend(self._check_deflection_limits(load_calculations))

        # Check for connection adequacy
        issues.extend(
            self._check_connection_adequacy(
                load_calculations, analysis.structural_system
            )
        )

        logger.info(f"Identified {len(issues)} structural issues")
        return issues

    def _calculate_dead_loads(
        self, design: Design, load_params: LoadParameters
    ) -> Dict[str, float]:
        """Calculate dead loads based on materials and construction."""
        dead_loads = {}

        # Basic dead load calculations based on typical construction
        # These would be more sophisticated in a real implementation
        building_area = design.metadata.get("building_area", 10000)  # sq ft

        if "steel_frame" in design.metadata.get("structural_system", ""):
            # Steel frame dead loads
            dead_loads["structure"] = (
                building_area * 15.0 * load_params.dead_load_factor
            )  # psf
            dead_loads["floor_system"] = (
                building_area * 25.0 * load_params.dead_load_factor
            )
            dead_loads["roof_system"] = (
                building_area * 20.0 * load_params.dead_load_factor
            )
        elif "concrete" in design.metadata.get("structural_system", ""):
            # Concrete dead loads
            dead_loads["structure"] = (
                building_area * 25.0 * load_params.dead_load_factor
            )
            dead_loads["floor_system"] = (
                building_area * 35.0 * load_params.dead_load_factor
            )
            dead_loads["roof_system"] = (
                building_area * 30.0 * load_params.dead_load_factor
            )
        else:
            # Default wood frame
            dead_loads["structure"] = (
                building_area * 10.0 * load_params.dead_load_factor
            )
            dead_loads["floor_system"] = (
                building_area * 15.0 * load_params.dead_load_factor
            )
            dead_loads["roof_system"] = (
                building_area * 12.0 * load_params.dead_load_factor
            )

        return dead_loads

    def _calculate_live_loads(
        self, design: Design, load_params: LoadParameters, building_type: str
    ) -> Dict[str, float]:
        """Calculate live loads based on occupancy and building type."""
        live_loads = {}
        building_area = design.metadata.get("building_area", 10000)

        # Live loads based on building type (IBC Table 1607.1)
        live_load_psf = {
            "office": 50.0,
            "residential": 40.0,
            "retail": 75.0,
            "warehouse": 125.0,
            "assembly": 100.0,
        }.get(building_type.lower(), 50.0)

        live_loads["floor"] = (
            building_area * live_load_psf * load_params.live_load_factor
        )
        live_loads["roof"] = (
            building_area * 20.0 * load_params.live_load_factor
        )  # Basic roof live load

        return live_loads

    def _calculate_wind_loads(
        self, design: Design, load_params: LoadParameters
    ) -> Dict[str, float]:
        """Calculate wind loads based on wind speed and building geometry."""
        wind_loads = {}

        if not load_params.wind_speed:
            return wind_loads

        building_height = design.metadata.get("building_height", 30)  # feet
        building_width = design.metadata.get("building_width", 100)  # feet

        # Simplified wind pressure calculation (ASCE 7)
        # qz = 0.00256 * Kz * Kzt * Kd * V^2 (psf)
        velocity_pressure = 0.00256 * 0.85 * 1.0 * 1.0 * (load_params.wind_speed**2)

        # Wind loads on different surfaces
        wind_loads["windward_wall"] = (
            building_height * building_width * velocity_pressure * 0.8
        )
        wind_loads["leeward_wall"] = (
            building_height * building_width * velocity_pressure * 0.5
        )
        wind_loads["side_walls"] = (
            building_height * building_width * velocity_pressure * 0.7
        )
        wind_loads["roof"] = building_width * building_width * velocity_pressure * 0.6

        return wind_loads

    def _calculate_seismic_loads(
        self, design: Design, load_params: LoadParameters
    ) -> Dict[str, float]:
        """Calculate seismic loads based on seismic zone and building characteristics."""
        seismic_loads = {}

        if not load_params.seismic_zone:
            return seismic_loads

        building_weight = design.metadata.get("building_weight", 1000000)  # lbs

        # Simplified seismic base shear calculation
        # V = Cs * W where Cs depends on seismic design category
        seismic_coefficients = {
            "A": 0.05,
            "B": 0.10,
            "C": 0.15,
            "D": 0.20,
            "E": 0.25,
            "F": 0.30,
        }

        cs = seismic_coefficients.get(load_params.seismic_zone.upper(), 0.15)
        base_shear = cs * building_weight

        seismic_loads["base_shear"] = base_shear
        seismic_loads["story_forces"] = base_shear * 0.8  # Simplified distribution
        seismic_loads["overturning_moment"] = base_shear * design.metadata.get(
            "building_height", 30
        )

        return seismic_loads

    def _check_load_limits(
        self, loads: LoadCalculations, structural_system: str
    ) -> List[StructuralIssue]:
        """Check if loads exceed typical limits for the structural system."""
        issues = []

        # Check dead load limits
        total_dead_load = sum(loads.dead_loads.values())
        dead_load_limit = {
            "steel_frame": 500000,  # lbs
            "concrete": 800000,
            "wood_frame": 300000,
            "masonry": 600000,
        }.get(structural_system, 500000)

        if total_dead_load > dead_load_limit:
            issues.append(
                StructuralIssue(
                    element_id="structure",
                    issue_type="excessive_dead_load",
                    description=f"Total dead load ({total_dead_load:,.0f} lbs) exceeds recommended limit",
                    severity="major",
                    recommendation="Consider lighter construction materials or structural optimization",
                )
            )

        # Check live load limits
        total_live_load = sum(loads.live_loads.values())
        live_load_limit = {
            "steel_frame": 400000,
            "concrete": 600000,
            "wood_frame": 200000,
            "masonry": 400000,
        }.get(structural_system, 400000)

        if total_live_load > live_load_limit:
            issues.append(
                StructuralIssue(
                    element_id="structure",
                    issue_type="excessive_live_load",
                    description=f"Total live load ({total_live_load:,.0f} lbs) exceeds capacity",
                    severity="critical",
                    recommendation="Increase structural capacity or reduce occupancy loads",
                )
            )

        return issues

    def _check_structural_adequacy(
        self, loads: LoadCalculations, structural_system: str
    ) -> List[StructuralIssue]:
        """Check structural adequacy for the given loads."""
        issues = []

        total_load = sum(loads.dead_loads.values()) + sum(loads.live_loads.values())

        # Add wind loads if present
        if loads.wind_loads:
            total_load += (
                sum(loads.wind_loads.values()) * 0.6
            )  # Load combination factor

        # Add seismic loads if present
        if loads.seismic_loads:
            seismic_load = loads.seismic_loads.get("base_shear", 0)
            total_load += seismic_load * 0.7  # Load combination factor

        # Check against structural capacity
        capacity_limits = {
            "steel_frame": 1200000,
            "concrete": 1500000,
            "wood_frame": 600000,
            "masonry": 1000000,
        }

        capacity = capacity_limits.get(structural_system, 1000000)
        utilization_ratio = total_load / capacity

        if utilization_ratio > 1.0:
            issues.append(
                StructuralIssue(
                    element_id="structure",
                    issue_type="inadequate_capacity",
                    description=f"Structure utilization ratio ({utilization_ratio:.2f}) exceeds 1.0",
                    severity="critical",
                    recommendation="Increase structural member sizes or add additional support",
                )
            )
        elif utilization_ratio > 0.9:
            issues.append(
                StructuralIssue(
                    element_id="structure",
                    issue_type="high_utilization",
                    description=f"Structure utilization ratio ({utilization_ratio:.2f}) is high",
                    severity="major",
                    recommendation="Consider structural reinforcement for safety margin",
                )
            )

        return issues

    def _check_deflection_limits(
        self, loads: LoadCalculations
    ) -> List[StructuralIssue]:
        """Check deflection limits for structural elements."""
        issues = []

        # Simplified deflection check
        total_live_load = sum(loads.live_loads.values())

        # Assume typical span and calculate deflection
        typical_span = 30  # feet
        estimated_deflection = total_live_load / (
            1000000 * typical_span
        )  # Simplified calculation

        deflection_limit = typical_span * 12 / 360  # L/360 in inches

        if estimated_deflection > deflection_limit:
            issues.append(
                StructuralIssue(
                    element_id="floor_system",
                    issue_type="excessive_deflection",
                    description=f"Estimated deflection ({estimated_deflection:.2f} in) exceeds L/360 limit",
                    severity="major",
                    recommendation="Increase structural stiffness or reduce span lengths",
                )
            )

        return issues

    def _check_connection_adequacy(
        self, loads: LoadCalculations, structural_system: str
    ) -> List[StructuralIssue]:
        """Check connection adequacy for the structural system."""
        issues = []

        # Check wind uplift on connections
        if loads.wind_loads:
            roof_uplift = loads.wind_loads.get("roof", 0)

            # Typical connection capacity
            connection_capacity = {
                "steel_frame": 50000,  # lbs
                "concrete": 40000,
                "wood_frame": 20000,
                "masonry": 30000,
            }.get(structural_system, 30000)

            if roof_uplift > connection_capacity:
                issues.append(
                    StructuralIssue(
                        element_id="roof_connections",
                        issue_type="inadequate_connection",
                        description=f"Wind uplift ({roof_uplift:,.0f} lbs) exceeds connection capacity",
                        severity="critical",
                        recommendation="Upgrade connection details or add additional fasteners",
                    )
                )

        return issues

    def _generate_recommendations(self, issues: List[StructuralIssue]) -> List[str]:
        """Generate general recommendations based on identified issues."""
        recommendations = []

        critical_issues = [issue for issue in issues if issue.severity == "critical"]
        major_issues = [issue for issue in issues if issue.severity == "major"]

        if critical_issues:
            recommendations.append(
                "Critical structural issues identified - immediate design revision required"
            )
            recommendations.append(
                "Engage a licensed structural engineer for detailed analysis"
            )

        if major_issues:
            recommendations.append(
                "Major structural concerns require attention before construction"
            )

        if not issues:
            recommendations.append(
                "Structural analysis shows adequate capacity for design loads"
            )
            recommendations.append(
                "Recommend detailed engineering analysis for construction documents"
            )

        # Add specific recommendations based on issue types
        issue_types = [issue.issue_type for issue in issues]

        if "excessive_dead_load" in issue_types:
            recommendations.append(
                "Consider lightweight construction materials to reduce dead loads"
            )

        if "inadequate_capacity" in issue_types:
            recommendations.append(
                "Increase structural member sizes or add additional support elements"
            )

        if "excessive_deflection" in issue_types:
            recommendations.append(
                "Increase structural stiffness through deeper members or reduced spans"
            )

        return recommendations

    def _to_response(self, analysis: StructuralAnalysis) -> StructuralAnalysisResponse:
        """Convert StructuralAnalysis model to response schema."""
        # Convert load calculations
        load_calculations = None
        if analysis.load_calculations:
            load_calculations = LoadCalculations(**analysis.load_calculations)

        # Convert issues
        issues = []
        for issue_data in analysis.issues:
            issues.append(StructuralIssue(**issue_data))

        return StructuralAnalysisResponse(
            id=UUID(analysis.id),
            design_id=UUID(analysis.design_id),
            design_version=analysis.design_version,
            structural_system=StructuralSystem(analysis.structural_system)
            if isinstance(analysis.structural_system, str)
            else analysis.structural_system,
            analysis_type=AnalysisType(analysis.analysis_type)
            if isinstance(analysis.analysis_type, str)
            else analysis.analysis_type,
            status=CheckStatus(analysis.status),
            load_calculations=load_calculations,
            issues=issues,
            recommendations=analysis.recommendations,
            report_url=analysis.report_url,
            started_at=analysis.started_at,
            completed_at=analysis.completed_at,
        )

    async def get_analysis_results(self, analysis_id: UUID) -> StructuralAnalysis:
        """
        Get structural analysis results by ID.

        Args:
            analysis_id: Analysis ID

        Returns:
            StructuralAnalysis model instance

        Raises:
            NotFoundError: If analysis not found
        """
        analysis = await self.structural_repository.get(str(analysis_id))
        if not analysis:
            raise NotFoundError(f"Structural analysis {analysis_id} not found")

        return analysis

    async def list_analyses_by_design(
        self, design_id: UUID, status: Optional[CheckStatus] = None
    ) -> List[StructuralAnalysisResponse]:
        """
        List all structural analyses for a design.

        Args:
            design_id: Design ID
            status: Optional status filter

        Returns:
            List of StructuralAnalysisResponse
        """
        status_str = status.value if status else None
        analyses = await self.structural_repository.list_by_design(
            str(design_id), status_str
        )

        return [self._to_response(analysis) for analysis in analyses]
