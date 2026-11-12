"""Pydantic schemas for document management."""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class DocumentType(str, Enum):
    """Document type enumeration."""

    CALCULATION_SHEET = "calculation_sheet"
    SPECIFICATION = "specification"
    REPORT = "report"
    DRAWING = "drawing"


class DocumentStatus(str, Enum):
    """Document status enumeration."""

    DRAFT = "draft"
    REVIEW = "review"
    APPROVED = "approved"
    REJECTED = "rejected"
    ARCHIVED = "archived"


class SpecificationFormat(str, Enum):
    """Specification format enumeration."""

    CSI_MASTERFORMAT = "csi_masterformat"
    UNIFORMAT = "uniformat"


# Calculation Sheet Schemas


class CalculationSheetCreateRequest(BaseModel):
    """Request schema for creating a calculation sheet."""

    project_id: UUID = Field(..., description="Project identifier")
    discipline: str = Field(
        ..., description="Engineering discipline (structural, mep, civil)"
    )
    calculation_type: str = Field(..., description="Type of calculation")
    inputs: Dict[str, Any] = Field(..., description="Calculation input parameters")
    results: Dict[str, Any] = Field(..., description="Calculation results")
    formulas: Dict[str, Any] = Field(..., description="Formulas and references used")
    unit_system: str = Field(..., description="Unit system (imperial, metric)")

    model_config = {"use_enum_values": True}


class CalculationSheetUpdateRequest(BaseModel):
    """Request schema for updating a calculation sheet."""

    inputs: Optional[Dict[str, Any]] = Field(
        None, description="Updated input parameters"
    )
    results: Optional[Dict[str, Any]] = Field(None, description="Updated results")
    formulas: Optional[Dict[str, Any]] = Field(None, description="Updated formulas")

    model_config = {"use_enum_values": True}


class CalculationSheetResponse(BaseModel):
    """Response schema for calculation sheet."""

    id: UUID = Field(..., description="Calculation sheet identifier")
    project_id: UUID = Field(..., description="Project identifier")
    discipline: str = Field(..., description="Engineering discipline")
    calculation_type: str = Field(..., description="Type of calculation")
    version: int = Field(..., description="Document version number")
    inputs: Dict[str, Any] = Field(..., description="Input parameters")
    results: Dict[str, Any] = Field(..., description="Calculation results")
    formulas: Dict[str, Any] = Field(..., description="Formulas used")
    unit_system: str = Field(..., description="Unit system")
    created_by: UUID = Field(..., description="Creator user ID")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    model_config = {"use_enum_values": True}


# Document History Schemas


class DocumentVersionSchema(BaseModel):
    """Schema for a document version."""

    version: int = Field(..., description="Version number")
    changes: Dict[str, Any] = Field(..., description="Changes made")
    updated_by: UUID = Field(..., description="User who made changes")
    updated_at: datetime = Field(..., description="Update timestamp")

    model_config = {"use_enum_values": True}


class DocumentHistoryResponse(BaseModel):
    """Response schema for document history."""

    document_id: UUID = Field(..., description="Document identifier")
    current_version: int = Field(..., description="Current version number")
    versions: List[DocumentVersionSchema] = Field(..., description="Version history")

    model_config = {"use_enum_values": True}


# Specification Generation Schemas


class SpecificationGenerateRequest(BaseModel):
    """Request schema for generating a technical specification."""

    project_id: UUID = Field(..., description="Project identifier")
    design_ids: List[UUID] = Field(
        ..., description="Design IDs to include in specification"
    )
    format: SpecificationFormat = Field(..., description="Specification format")
    sections: List[str] = Field(..., description="Specification sections to include")

    model_config = {"use_enum_values": True}


class SpecificationResponse(BaseModel):
    """Response schema for generated specification."""

    specification_id: UUID = Field(..., description="Specification identifier")
    project_id: UUID = Field(..., description="Project identifier")
    format: SpecificationFormat = Field(..., description="Format used")
    sections: Dict[str, Any] = Field(
        ..., description="Specification sections and content"
    )
    generated_at: datetime = Field(
        default_factory=datetime.utcnow, description="Generation timestamp"
    )

    model_config = {"use_enum_values": True}


# Document Search Schemas


class DocumentSearchRequest(BaseModel):
    """Request schema for document search."""

    project_id: Optional[UUID] = Field(None, description="Filter by project")
    discipline: Optional[str] = Field(None, description="Filter by discipline")
    document_type: Optional[DocumentType] = Field(
        None, description="Filter by document type"
    )
    status: Optional[DocumentStatus] = Field(None, description="Filter by status")
    search_text: Optional[str] = Field(None, description="Text search query")

    model_config = {"use_enum_values": True}


class DocumentSearchResponse(BaseModel):
    """Response schema for document search results."""

    total_count: int = Field(..., description="Total number of results")
    documents: List[CalculationSheetResponse] = Field(
        ..., description="List of matching documents"
    )

    model_config = {"use_enum_values": True}
