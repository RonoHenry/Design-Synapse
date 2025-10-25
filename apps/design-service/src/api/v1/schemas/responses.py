"""
Response schemas for the Design Service API.

These schemas define the structure of API responses, serializing
database models into JSON-compatible formats with proper type validation.

Requirements:
- 2.1: Design storage with version control
- 3.1: Design validation against building codes
- 4.1: AI-powered design optimization
- 6.1: Design file management
- 7.1: Design collaboration and comments
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class DesignResponse(BaseModel):
    """
    Response schema for design data.
    
    Serializes Design model instances for API responses,
    including all design metadata, specifications, and audit fields.
    """
    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="Unique design identifier")
    project_id: int = Field(..., description="Project this design belongs to")
    name: str = Field(..., description="Design name")
    description: Optional[str] = Field(None, description="Design description")
    
    # Design specification (structured JSON)
    specification: Dict[str, Any] = Field(
        ...,
        description="Structured design specification in JSON format"
    )
    
    # Metadata
    building_type: str = Field(..., description="Type of building (residential, commercial, industrial)")
    total_area: Optional[float] = Field(None, description="Total area in square meters")
    num_floors: Optional[int] = Field(None, description="Number of floors")
    materials: Optional[List[str]] = Field(None, description="List of materials used")
    
    # AI generation metadata
    generation_prompt: Optional[str] = Field(None, description="AI generation prompt used")
    confidence_score: Optional[float] = Field(None, description="AI confidence score (0-100)")
    ai_model_version: Optional[str] = Field(None, description="AI model version used")
    
    # Version control
    version: int = Field(..., description="Design version number")
    parent_design_id: Optional[int] = Field(None, description="Parent design ID for versioning")
    
    # Status and compliance
    status: str = Field(..., description="Design status (draft, validated, compliant, non_compliant)")
    is_archived: bool = Field(..., description="Whether the design is archived")
    
    # Visual output fields
    floor_plan_url: Optional[str] = Field(None, description="URL to floor plan image")
    rendering_url: Optional[str] = Field(None, description="URL to 3D rendering image")
    model_file_url: Optional[str] = Field(None, description="URL to 3D model file")
    visual_generation_status: str = Field(..., description="Visual generation status (pending, processing, completed, failed)")
    visual_generation_error: Optional[str] = Field(None, description="Error message from visual generation")
    visual_generated_at: Optional[datetime] = Field(None, description="Timestamp when visuals were generated")
    
    # Audit fields
    created_by: int = Field(..., description="User ID who created the design")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")


class ValidationResponse(BaseModel):
    """
    Response schema for validation results.
    
    Serializes DesignValidation model instances, including
    compliance status, violations, and warnings.
    """
    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="Unique validation identifier")
    design_id: int = Field(..., description="Design being validated")
    
    # Validation metadata
    validation_type: str = Field(
        ...,
        description="Type of validation (building_code, structural, safety)"
    )
    rule_set: str = Field(
        ...,
        description="Building code rule set used (e.g., Kenya_Building_Code_2020)"
    )
    
    # Results
    is_compliant: bool = Field(..., description="Whether the design is compliant")
    violations: List[Dict[str, Any]] = Field(
        ...,
        description="List of validation violations"
    )
    warnings: List[Dict[str, Any]] = Field(
        ...,
        description="List of validation warnings"
    )
    
    # Audit
    validated_at: datetime = Field(..., description="Validation timestamp")
    validated_by: int = Field(..., description="User ID who performed validation")


class OptimizationResponse(BaseModel):
    """
    Response schema for optimization suggestions.
    
    Serializes DesignOptimization model instances, including
    optimization details, impact analysis, and application status.
    """
    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="Unique optimization identifier")
    design_id: int = Field(..., description="Design being optimized")
    
    # Optimization details
    optimization_type: str = Field(
        ...,
        description="Type of optimization (cost, structural, sustainability)"
    )
    title: str = Field(..., description="Optimization title")
    description: str = Field(..., description="Detailed optimization description")
    
    # Impact analysis
    estimated_cost_impact: Optional[float] = Field(
        None,
        description="Estimated cost impact as percentage (negative = reduction)"
    )
    implementation_difficulty: str = Field(
        ...,
        description="Implementation difficulty (easy, medium, hard)"
    )
    priority: str = Field(..., description="Priority level (low, medium, high)")
    
    # Application status
    status: str = Field(
        ...,
        description="Optimization status (suggested, applied, rejected)"
    )
    applied_at: Optional[datetime] = Field(None, description="When optimization was applied")
    applied_by: Optional[int] = Field(None, description="User ID who applied optimization")
    
    # Audit
    created_at: datetime = Field(..., description="Creation timestamp")


class DesignFileResponse(BaseModel):
    """
    Response schema for design files.
    
    Serializes DesignFile model instances, including
    file metadata and storage information.
    """
    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="Unique file identifier")
    design_id: int = Field(..., description="Design this file belongs to")
    
    # File metadata
    filename: str = Field(..., description="File name")
    file_type: str = Field(
        ...,
        description="File type (pdf, dwg, dxf, png, jpg, ifc)"
    )
    file_size: int = Field(..., description="File size in bytes")
    storage_path: str = Field(..., description="Storage path")
    
    # Optional description
    description: Optional[str] = Field(None, description="File description")
    
    # Audit
    uploaded_by: int = Field(..., description="User ID who uploaded the file")
    uploaded_at: datetime = Field(..., description="Upload timestamp")


class DesignCommentResponse(BaseModel):
    """
    Response schema for design comments.
    
    Serializes DesignComment model instances, including
    comment content, optional spatial positioning, and audit fields.
    """
    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="Unique comment identifier")
    design_id: int = Field(..., description="Design this comment belongs to")
    
    # Comment content
    content: str = Field(..., description="Comment text content")
    
    # Optional spatial positioning
    position_x: Optional[float] = Field(None, description="X coordinate for spatial annotation")
    position_y: Optional[float] = Field(None, description="Y coordinate for spatial annotation")
    position_z: Optional[float] = Field(None, description="Z coordinate for spatial annotation")
    
    # Audit fields
    created_by: int = Field(..., description="User ID who created the comment")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    is_edited: bool = Field(..., description="Whether the comment has been edited")
