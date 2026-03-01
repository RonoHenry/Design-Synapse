"""Pydantic schemas for code compliance validation."""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List
from uuid import UUID

from pydantic import BaseModel, Field


class CodeType(str, Enum):
    """Code type enumeration."""

    STRUCTURAL = "structural"
    MEP = "mep"
    ENERGY = "energy"
    FIRE = "fire"
    ACCESSIBILITY = "accessibility"


class ComplianceStatus(str, Enum):
    """Compliance status enumeration."""

    COMPLIANT = "compliant"
    NON_COMPLIANT = "non_compliant"
    REVIEW_REQUIRED = "review_required"


class ViolationSeverity(str, Enum):
    """Violation severity enumeration."""

    CRITICAL = "critical"
    MAJOR = "major"
    MINOR = "minor"
    WARNING = "warning"


# Code Validation Schemas


class CodeValidationRequest(BaseModel):
    """Request schema for code compliance validation."""

    design_id: UUID = Field(..., description="Design identifier to validate")
    code_type: CodeType = Field(..., description="Type of code to validate")
    jurisdiction: str = Field(..., description="Jurisdiction for code requirements")
    code_version: str = Field(
        ..., description="Specific code version to validate against"
    )

    model_config = {"use_enum_values": True}


class ViolationSchema(BaseModel):
    """Schema for a code violation."""

    code_section: str = Field(..., description="Code section reference")
    severity: ViolationSeverity = Field(..., description="Violation severity")
    description: str = Field(..., description="Violation description")
    recommendation: str = Field(..., description="Recommended corrective action")
    affected_elements: List[str] = Field(..., description="Design elements affected")

    model_config = {"use_enum_values": True}


class CodeValidationResponse(BaseModel):
    """Response schema for code compliance validation."""

    report_id: UUID = Field(..., description="Compliance report identifier")
    design_id: UUID = Field(..., description="Design identifier")
    code_type: CodeType = Field(..., description="Code type validated")
    jurisdiction: str = Field(..., description="Jurisdiction")
    code_version: str = Field(..., description="Code version")
    overall_status: ComplianceStatus = Field(
        ..., description="Overall compliance status"
    )
    checks_performed: List[str] = Field(..., description="List of checks performed")
    violations: List[ViolationSchema] = Field(
        ..., description="List of violations found"
    )
    recommendations: List[str] = Field(..., description="General recommendations")
    generated_at: datetime = Field(
        default_factory=datetime.utcnow, description="Report generation time"
    )

    model_config = {"use_enum_values": True}


# Code Requirements Schemas


class CodeRequirementsRequest(BaseModel):
    """Request schema for retrieving code requirements."""

    code_type: CodeType = Field(..., description="Type of code")
    jurisdiction: str = Field(..., description="Jurisdiction")
    code_version: str = Field(..., description="Code version")

    model_config = {"use_enum_values": True}


class CodeRequirementsResponse(BaseModel):
    """Response schema for code requirements."""

    code_type: CodeType = Field(..., description="Code type")
    jurisdiction: str = Field(..., description="Jurisdiction")
    code_version: str = Field(..., description="Code version")
    requirements: Dict[str, Any] = Field(
        ..., description="Code requirements by section"
    )
    references: List[str] = Field(..., description="Reference documents and standards")

    model_config = {"use_enum_values": True}
