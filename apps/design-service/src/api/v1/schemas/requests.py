"""Request schemas for design service API."""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, ConfigDict


class DesignGenerationRequest(BaseModel):
    """Request schema for AI design generation."""

    model_config = ConfigDict(from_attributes=True)

    project_id: int = Field(..., description="Project ID this design belongs to")
    name: str = Field(..., min_length=1, max_length=255, description="Design name")
    description: str = Field(..., description="Natural language design description")
    building_type: str = Field(..., description="Type of building (e.g., residential, commercial, industrial)")
    requirements: Dict[str, Any] = Field(
        default_factory=dict,
        description="Specific requirements and parameters for the design"
    )
    generate_visuals: bool = Field(
        default=False,
        description="Whether to automatically generate visual outputs (floor plans, renderings, 3D models)"
    )


class DesignUpdateRequest(BaseModel):
    """Request schema for updating a design."""

    model_config = ConfigDict(from_attributes=True)

    name: Optional[str] = Field(None, min_length=1, max_length=255, description="Updated design name")
    description: Optional[str] = Field(None, description="Updated description")
    specification: Optional[Dict[str, Any]] = Field(None, description="Updated design specification")
    status: Optional[str] = Field(None, description="Updated design status")


class ValidationRequest(BaseModel):
    """Request schema for design validation."""

    model_config = ConfigDict(from_attributes=True)

    validation_type: str = Field(
        ...,
        description="Type of validation to perform (e.g., building_code, structural, safety)"
    )
    rule_set: str = Field(
        ...,
        description="Building code rule set to use (e.g., Kenya_Building_Code_2020)"
    )


class OptimizationRequest(BaseModel):
    """Request schema for design optimization."""

    model_config = ConfigDict(from_attributes=True)

    optimization_types: List[str] = Field(
        default=["cost", "structural", "sustainability"],
        description="Types of optimizations to generate"
    )


class CommentCreateRequest(BaseModel):
    """Request schema for creating a comment."""

    model_config = ConfigDict(from_attributes=True)

    content: str = Field(..., min_length=1, description="Comment text content")
    position_x: Optional[float] = Field(None, description="Optional X coordinate for spatial annotation")
    position_y: Optional[float] = Field(None, description="Optional Y coordinate for spatial annotation")
    position_z: Optional[float] = Field(None, description="Optional Z coordinate for spatial annotation")


class CommentUpdateRequest(BaseModel):
    """Request schema for updating a comment."""

    model_config = ConfigDict(from_attributes=True)

    content: str = Field(..., min_length=1, description="Updated comment text content")
    position_x: Optional[float] = Field(None, description="Updated X coordinate for spatial annotation")
    position_y: Optional[float] = Field(None, description="Updated Y coordinate for spatial annotation")
    position_z: Optional[float] = Field(None, description="Updated Z coordinate for spatial annotation")


class GenerateVisualsRequest(BaseModel):
    """Request schema for generating visuals for an existing design."""

    model_config = ConfigDict(from_attributes=True)

    visual_types: List[str] = Field(
        default=["floor_plan", "rendering", "3d_model"],
        description="Types of visuals to generate (floor_plan, rendering, 3d_model)"
    )
    size: str = Field(
        default="1024x1024",
        description="Image size (1024x1024, 1792x1024, 1024x1792)"
    )
    quality: str = Field(
        default="standard",
        description="Image quality (standard, hd)"
    )
    priority: str = Field(
        default="normal",
        description="Task priority (low, normal, high)"
    )