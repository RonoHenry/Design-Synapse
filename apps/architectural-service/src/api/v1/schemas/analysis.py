"""Analysis schemas for compliance, structural, and other analyses."""

from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import Field, field_validator

from .base import BaseSchema
from .enums import (AnalysisType, CheckStatus, ComplianceCheckType,
                    MaterialCategory, OptimizationGoal, StructuralSystem)

# ============================================================================
# Compliance Check Schemas
# ============================================================================


class ComplianceCheckRequest(BaseSchema):
    """Request schema for compliance check."""

    code_standards: List[str] = Field(
        ...,
        description="Building code standards to check against (e.g., 'IBC-2021', 'ADA')",
        min_length=1,
    )
    jurisdiction: Optional[str] = Field(
        None, description="Local jurisdiction for code requirements", max_length=100
    )
    check_types: List[ComplianceCheckType] = Field(
        default_factory=lambda: [ComplianceCheckType.BUILDING_CODE],
        description="Types of compliance checks to perform",
    )

    @field_validator("code_standards")
    @classmethod
    def validate_code_standards(cls, v: List[str]) -> List[str]:
        """Validate code standards list is not empty."""
        if not v:
            raise ValueError("At least one code standard must be specified")
        return v

    model_config = {
        "json_schema_extra": {
            "example": {
                "code_standards": ["IBC-2021", "ADA"],
                "jurisdiction": "City and County of San Francisco",
                "check_types": ["building_code", "accessibility"],
            }
        }
    }


class ViolationDetail(BaseSchema):
    """Compliance violation detail."""

    code_section: str = Field(..., description="Code section reference")
    description: str = Field(..., description="Violation description")
    severity: str = Field(..., description="Severity level (critical, major, minor)")
    location: Optional[str] = Field(
        None, description="Location in design where violation occurs"
    )
    remediation: Optional[str] = Field(None, description="Suggested remediation")


class WarningDetail(BaseSchema):
    """Compliance warning detail."""

    code_section: str = Field(..., description="Code section reference")
    description: str = Field(..., description="Warning description")
    recommendation: Optional[str] = Field(None, description="Recommended action")


class ComplianceCheckResponse(BaseSchema):
    """Response schema for compliance check."""

    id: UUID = Field(..., description="Compliance check ID")
    design_id: UUID = Field(..., description="Associated design ID")
    design_version: str = Field(..., description="Design version checked")
    code_standards: List[str] = Field(..., description="Code standards checked")
    jurisdiction: Optional[str] = Field(None, description="Jurisdiction")
    status: CheckStatus = Field(..., description="Check status")
    passed: Optional[bool] = Field(None, description="Whether all checks passed")
    violations: List[ViolationDetail] = Field(
        default_factory=list, description="List of violations found"
    )
    warnings: List[WarningDetail] = Field(
        default_factory=list, description="List of warnings"
    )
    recommendations: List[str] = Field(
        default_factory=list, description="General recommendations"
    )
    report_url: Optional[str] = Field(
        None, description="URL to detailed compliance report"
    )
    started_at: datetime = Field(..., description="Check start time")
    completed_at: Optional[datetime] = Field(None, description="Check completion time")


# ============================================================================
# Structural Analysis Schemas
# ============================================================================


class LoadParameters(BaseSchema):
    """Load parameters for structural analysis."""

    dead_load_factor: float = Field(1.2, description="Dead load factor", ge=0)
    live_load_factor: float = Field(1.6, description="Live load factor", ge=0)
    wind_speed: Optional[float] = Field(
        None, description="Design wind speed in mph", ge=0
    )
    seismic_zone: Optional[str] = Field(None, description="Seismic design category")
    snow_load: Optional[float] = Field(None, description="Snow load in psf", ge=0)


class StructuralAnalysisRequest(BaseSchema):
    """Request schema for structural analysis."""

    structural_system: StructuralSystem = Field(
        ..., description="Type of structural system"
    )
    load_parameters: LoadParameters = Field(
        ..., description="Load parameters for analysis"
    )
    analysis_type: AnalysisType = Field(
        AnalysisType.STATIC, description="Type of analysis to perform"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "structural_system": "steel_frame",
                "load_parameters": {
                    "dead_load_factor": 1.2,
                    "live_load_factor": 1.6,
                    "wind_speed": 90,
                    "seismic_zone": "D",
                },
                "analysis_type": "static",
            }
        }
    }


class LoadCalculations(BaseSchema):
    """Structural load calculations."""

    dead_loads: Dict[str, float] = Field(
        ..., description="Dead load calculations by element"
    )
    live_loads: Dict[str, float] = Field(
        ..., description="Live load calculations by element"
    )
    wind_loads: Optional[Dict[str, float]] = Field(
        None, description="Wind load calculations"
    )
    seismic_loads: Optional[Dict[str, float]] = Field(
        None, description="Seismic load calculations"
    )


class StructuralIssue(BaseSchema):
    """Structural issue detail."""

    element_id: str = Field(..., description="Design element with issue")
    issue_type: str = Field(..., description="Type of structural issue")
    description: str = Field(..., description="Issue description")
    severity: str = Field(..., description="Severity level")
    recommendation: str = Field(..., description="Recommended action")


class StructuralAnalysisResponse(BaseSchema):
    """Response schema for structural analysis."""

    id: UUID = Field(..., description="Analysis ID")
    design_id: UUID = Field(..., description="Associated design ID")
    design_version: str = Field(..., description="Design version analyzed")
    structural_system: StructuralSystem = Field(
        ..., description="Structural system type"
    )
    analysis_type: AnalysisType = Field(..., description="Analysis type")
    status: CheckStatus = Field(..., description="Analysis status")
    load_calculations: Optional[LoadCalculations] = Field(
        None, description="Load calculations"
    )
    issues: List[StructuralIssue] = Field(
        default_factory=list, description="Structural issues found"
    )
    recommendations: List[str] = Field(
        default_factory=list, description="General recommendations"
    )
    report_url: Optional[str] = Field(
        None, description="URL to detailed analysis report"
    )
    started_at: datetime = Field(..., description="Analysis start time")
    completed_at: Optional[datetime] = Field(
        None, description="Analysis completion time"
    )


# ============================================================================
# Material Specification Schemas
# ============================================================================


class MaterialProperties(BaseSchema):
    """Material properties."""

    type: str = Field(..., description="Material type", max_length=100)
    grade: Optional[str] = Field(None, description="Material grade", max_length=50)
    dimensions: Optional[str] = Field(
        None, description="Material dimensions", max_length=100
    )
    finish: Optional[str] = Field(None, description="Material finish", max_length=100)
    properties: Dict[str, Any] = Field(
        default_factory=dict, description="Additional properties"
    )


class MaterialSpecificationRequest(BaseSchema):
    """Request schema for material specification."""

    category: MaterialCategory = Field(..., description="Material category")
    properties: MaterialProperties = Field(..., description="Material properties")
    design_elements: List[UUID] = Field(
        default_factory=list, description="Design elements using this material"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "category": "structural",
                "properties": {
                    "type": "Steel",
                    "grade": "A992",
                    "dimensions": "W12x26",
                    "finish": "Painted",
                    "properties": {
                        "yield_strength": "50 ksi",
                        "tensile_strength": "65 ksi",
                    },
                },
                "design_elements": [],
            }
        }
    }


class VendorInfo(BaseSchema):
    """Vendor information for material."""

    vendor_id: UUID = Field(..., description="Vendor ID")
    vendor_name: str = Field(..., description="Vendor name")
    product_code: Optional[str] = Field(None, description="Vendor product code")
    availability: Optional[str] = Field(None, description="Availability status")
    lead_time_days: Optional[int] = Field(None, description="Lead time in days")


class MaterialSpecificationResponse(BaseSchema):
    """Response schema for material specification."""

    id: UUID = Field(..., description="Material specification ID")
    design_id: UUID = Field(..., description="Associated design ID")
    category: MaterialCategory = Field(..., description="Material category")
    properties: MaterialProperties = Field(..., description="Material properties")
    vendor_info: Optional[VendorInfo] = Field(None, description="Vendor information")
    cost_estimate: Optional[Decimal] = Field(None, description="Cost estimate")
    design_elements: List[UUID] = Field(
        default_factory=list, description="Associated design elements"
    )
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")


# ============================================================================
# Space Planning Schemas
# ============================================================================


class SpaceRequirement(BaseSchema):
    """Space requirement specification."""

    space_type: str = Field(
        ..., description="Type of space (e.g., 'bedroom', 'kitchen')", max_length=100
    )
    min_area: float = Field(..., description="Minimum area in square feet", gt=0)
    max_area: Optional[float] = Field(
        None, description="Maximum area in square feet", gt=0
    )
    adjacencies: List[str] = Field(
        default_factory=list, description="Required adjacent spaces"
    )
    requirements: Dict[str, Any] = Field(
        default_factory=dict, description="Additional requirements"
    )


class PlanningConstraints(BaseSchema):
    """Space planning constraints."""

    total_area: Optional[float] = Field(None, description="Total available area", gt=0)
    shape_constraints: Optional[Dict[str, Any]] = Field(
        None, description="Shape and geometry constraints"
    )
    code_requirements: Optional[Dict[str, Any]] = Field(
        None, description="Code-based constraints"
    )


class SpacePlanningRequest(BaseSchema):
    """Request schema for space planning."""

    requirements: List[SpaceRequirement] = Field(
        ..., description="Space requirements", min_length=1
    )
    constraints: PlanningConstraints = Field(..., description="Planning constraints")
    optimization_goals: List[OptimizationGoal] = Field(
        default_factory=list, description="Optimization goals"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "requirements": [
                    {
                        "space_type": "living_room",
                        "min_area": 200,
                        "adjacencies": ["kitchen", "entry"],
                    }
                ],
                "constraints": {"total_area": 2000},
                "optimization_goals": ["maximize_efficiency"],
            }
        }
    }


class LayoutRecommendation(BaseSchema):
    """Layout recommendation."""

    space_type: str = Field(..., description="Space type")
    recommended_area: float = Field(..., description="Recommended area")
    location: Dict[str, Any] = Field(..., description="Recommended location")
    rationale: str = Field(..., description="Rationale for recommendation")


class SpaceMetrics(BaseSchema):
    """Space utilization metrics."""

    area_efficiency: float = Field(
        ..., description="Area efficiency percentage", ge=0, le=100
    )
    circulation_ratio: float = Field(
        ..., description="Circulation to usable area ratio", ge=0
    )
    density: float = Field(
        ..., description="Occupancy density (people per sq ft)", ge=0
    )


class SpacePlanningResponse(BaseSchema):
    """Response schema for space planning."""

    id: UUID = Field(..., description="Space planning ID")
    design_id: UUID = Field(..., description="Associated design ID")
    status: CheckStatus = Field(..., description="Planning status")
    recommendations: List[LayoutRecommendation] = Field(
        default_factory=list, description="Layout recommendations"
    )
    metrics: Optional[SpaceMetrics] = Field(
        None, description="Space utilization metrics"
    )
    space_program: Optional[Dict[str, Any]] = Field(
        None, description="Detailed space program document"
    )
    started_at: datetime = Field(..., description="Planning start time")
    completed_at: Optional[datetime] = Field(
        None, description="Planning completion time"
    )


# ============================================================================
# Accessibility Check Schemas
# ============================================================================


class AccessibilityCheckRequest(BaseSchema):
    """Request schema for accessibility check."""

    standards: List[str] = Field(
        ...,
        description="Accessibility standards (e.g., 'ADA', 'ANSI-A117.1')",
        min_length=1,
    )
    check_areas: List[str] = Field(
        default_factory=list, description="Specific areas to check"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "standards": ["ADA", "ANSI-A117.1"],
                "check_areas": ["entrances", "restrooms", "corridors"],
            }
        }
    }


class AccessibilityViolation(BaseSchema):
    """Accessibility violation detail."""

    standard_section: str = Field(..., description="Standard section reference")
    location: str = Field(..., description="Location of violation")
    description: str = Field(..., description="Violation description")
    required_value: str = Field(..., description="Required value per standard")
    actual_value: str = Field(..., description="Actual value in design")
    remediation: str = Field(..., description="Remediation guidance")


class RouteValidation(BaseSchema):
    """Accessible route validation."""

    route_id: str = Field(..., description="Route identifier")
    from_location: str = Field(..., description="Starting location")
    to_location: str = Field(..., description="Ending location")
    is_accessible: bool = Field(..., description="Whether route is accessible")
    issues: List[str] = Field(default_factory=list, description="Issues found on route")


class AccessibilityCheckResponse(BaseSchema):
    """Response schema for accessibility check."""

    id: UUID = Field(..., description="Accessibility check ID")
    design_id: UUID = Field(..., description="Associated design ID")
    design_version: str = Field(..., description="Design version checked")
    standards: List[str] = Field(..., description="Standards checked")
    status: CheckStatus = Field(..., description="Check status")
    passed: Optional[bool] = Field(None, description="Whether all checks passed")
    violations: List[AccessibilityViolation] = Field(
        default_factory=list, description="Violations found"
    )
    accessible_routes: List[RouteValidation] = Field(
        default_factory=list, description="Accessible route validations"
    )
    started_at: datetime = Field(..., description="Check start time")
    completed_at: Optional[datetime] = Field(None, description="Check completion time")


# ============================================================================
# Energy Analysis Schemas
# ============================================================================


class BuildingParameters(BaseSchema):
    """Building parameters for energy analysis."""

    total_area: float = Field(
        ..., description="Total building area in square feet", gt=0
    )
    number_of_floors: int = Field(..., description="Number of floors", ge=1)
    occupancy_type: str = Field(..., description="Occupancy type", max_length=100)
    hvac_system: Optional[str] = Field(None, description="HVAC system type")
    envelope_properties: Optional[Dict[str, Any]] = Field(
        None, description="Building envelope properties"
    )


class EnergyAnalysisRequest(BaseSchema):
    """Request schema for energy analysis."""

    standards: List[str] = Field(
        ..., description="Energy standards (e.g., 'ASHRAE-90.1', 'LEED')", min_length=1
    )
    climate_zone: str = Field(..., description="Climate zone", max_length=50)
    building_parameters: BuildingParameters = Field(
        ..., description="Building parameters"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "standards": ["ASHRAE-90.1", "LEED"],
                "climate_zone": "4A",
                "building_parameters": {
                    "total_area": 50000,
                    "number_of_floors": 5,
                    "occupancy_type": "office",
                    "hvac_system": "VAV",
                },
            }
        }
    }


class EnvelopeMetrics(BaseSchema):
    """Building envelope performance metrics."""

    wall_r_value: float = Field(..., description="Wall R-value")
    roof_r_value: float = Field(..., description="Roof R-value")
    window_u_factor: float = Field(..., description="Window U-factor")
    infiltration_rate: float = Field(..., description="Air infiltration rate")


class EnergyEstimate(BaseSchema):
    """Energy consumption estimate."""

    annual_consumption_kwh: float = Field(
        ..., description="Annual energy consumption in kWh", ge=0
    )
    heating_kwh: float = Field(..., description="Heating energy in kWh", ge=0)
    cooling_kwh: float = Field(..., description="Cooling energy in kWh", ge=0)
    lighting_kwh: float = Field(..., description="Lighting energy in kWh", ge=0)
    equipment_kwh: float = Field(..., description="Equipment energy in kWh", ge=0)
    estimated_cost: Decimal = Field(..., description="Estimated annual energy cost")


class EfficiencyRecommendation(BaseSchema):
    """Energy efficiency recommendation."""

    category: str = Field(..., description="Recommendation category")
    description: str = Field(..., description="Recommendation description")
    estimated_savings_kwh: float = Field(
        ..., description="Estimated energy savings in kWh", ge=0
    )
    estimated_cost_savings: Decimal = Field(..., description="Estimated cost savings")
    implementation_cost: Optional[Decimal] = Field(
        None, description="Estimated implementation cost"
    )


class EnergyAnalysisResponse(BaseSchema):
    """Response schema for energy analysis."""

    id: UUID = Field(..., description="Energy analysis ID")
    design_id: UUID = Field(..., description="Associated design ID")
    design_version: str = Field(..., description="Design version analyzed")
    standards: List[str] = Field(..., description="Standards used")
    climate_zone: str = Field(..., description="Climate zone")
    status: CheckStatus = Field(..., description="Analysis status")
    envelope_performance: Optional[EnvelopeMetrics] = Field(
        None, description="Envelope performance metrics"
    )
    energy_consumption: Optional[EnergyEstimate] = Field(
        None, description="Energy consumption estimate"
    )
    recommendations: List[EfficiencyRecommendation] = Field(
        default_factory=list, description="Efficiency recommendations"
    )
    certificate_url: Optional[str] = Field(
        None, description="URL to performance certificate"
    )
    started_at: datetime = Field(..., description="Analysis start time")
    completed_at: Optional[datetime] = Field(
        None, description="Analysis completion time"
    )
