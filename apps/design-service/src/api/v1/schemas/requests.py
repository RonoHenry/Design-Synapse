"""Request schemas for design service API."""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class DesignGenerationRequest(BaseModel):
    """Request schema for AI design generation."""

    model_config = ConfigDict(from_attributes=True)

    project_id: int = Field(
        ..., description="Project ID this design belongs to", examples=[1, 15, 42, 123]
    )
    name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Design name",
        examples=[
            "Sustainable Office Building Design",
            "Residential Complex Layout",
            "Green Energy Research Center",
            "Modern Library Architecture",
        ],
    )
    description: str = Field(
        ...,
        description="Natural language design description",
        examples=[
            "Design a modern 5-story office building with sustainable features, natural lighting, and open floor plans",
            "Create a residential complex with 50 units, community spaces, and green areas for families",
            "Design a research facility for renewable energy with laboratories, offices, and demonstration areas",
        ],
    )
    building_type: str = Field(
        ...,
        description="Type of building (e.g., residential, commercial, industrial)",
        examples=[
            "residential",
            "commercial",
            "industrial",
            "institutional",
            "mixed-use",
        ],
    )
    requirements: Dict[str, Any] = Field(
        default_factory=dict,
        description="Specific requirements and parameters for the design",
        examples=[
            {
                "floors": 5,
                "total_area": 10000,
                "parking_spaces": 50,
                "sustainability_rating": "LEED Gold",
            },
            {
                "units": 50,
                "building_height": "4 stories",
                "amenities": ["gym", "pool", "playground"],
            },
            {},
        ],
    )
    generate_visuals: bool = Field(
        default=False,
        description="Whether to automatically generate visual outputs (floor plans, renderings, 3D models)",
        examples=[True, False],
    )


class DesignUpdateRequest(BaseModel):
    """Request schema for updating a design."""

    model_config = ConfigDict(from_attributes=True)

    name: Optional[str] = Field(
        None,
        min_length=1,
        max_length=255,
        description="Updated design name",
        examples=[
            "Updated Sustainable Office Building Design",
            "Revised Residential Complex Layout",
            None,
        ],
    )
    description: Optional[str] = Field(
        None,
        description="Updated description",
        examples=[
            "Updated design with improved sustainability features and enhanced natural lighting",
            "Revised layout with additional community spaces and better traffic flow",
            None,
        ],
    )
    specification: Optional[Dict[str, Any]] = Field(
        None,
        description="Updated design specification",
        examples=[
            {
                "floors": 6,
                "total_area": 12000,
                "sustainability_rating": "LEED Platinum",
            },
            {
                "materials": ["steel", "glass", "concrete"],
                "energy_systems": ["solar", "geothermal"],
            },
            None,
        ],
    )
    status: Optional[str] = Field(
        None,
        description="Updated design status",
        examples=["draft", "validated", "compliant", "non_compliant", None],
    )


class ValidationRequest(BaseModel):
    """Request schema for design validation."""

    model_config = ConfigDict(from_attributes=True)

    validation_type: str = Field(
        ...,
        description="Type of validation to perform (e.g., building_code, structural, safety)",
        examples=[
            "building_code",
            "structural",
            "safety",
            "accessibility",
            "fire_safety",
        ],
    )
    rule_set: str = Field(
        ...,
        description="Building code rule set to use (e.g., Kenya_Building_Code_2020)",
        examples=["Kenya_Building_Code_2020", "IBC_2021", "Eurocode", "ASCE_Standards"],
    )


class OptimizationRequest(BaseModel):
    """Request schema for design optimization."""

    model_config = ConfigDict(from_attributes=True)

    optimization_types: List[str] = Field(
        default=["cost", "structural", "sustainability"],
        description="Types of optimizations to generate",
        examples=[
            ["cost", "structural", "sustainability"],
            ["cost", "energy_efficiency"],
            ["structural", "material_optimization"],
            ["sustainability", "accessibility"],
        ],
    )


class CommentCreateRequest(BaseModel):
    """Request schema for creating a comment."""

    model_config = ConfigDict(from_attributes=True)

    content: str = Field(
        ...,
        min_length=1,
        description="Comment text content",
        examples=[
            "The main entrance needs better accessibility features",
            "Consider adding more natural lighting to this area",
            "This structural element may need reinforcement",
            "Great use of sustainable materials in this section",
        ],
    )
    position_x: Optional[float] = Field(
        None,
        description="Optional X coordinate for spatial annotation",
        examples=[100.5, 250.0, 0.0, None],
    )
    position_y: Optional[float] = Field(
        None,
        description="Optional Y coordinate for spatial annotation",
        examples=[75.2, 180.5, 0.0, None],
    )
    position_z: Optional[float] = Field(
        None,
        description="Optional Z coordinate for spatial annotation",
        examples=[10.0, 25.5, 0.0, None],
    )


class CommentUpdateRequest(BaseModel):
    """Request schema for updating a comment."""

    model_config = ConfigDict(from_attributes=True)

    content: str = Field(..., min_length=1, description="Updated comment text content")
    position_x: Optional[float] = Field(
        None, description="Updated X coordinate for spatial annotation"
    )
    position_y: Optional[float] = Field(
        None, description="Updated Y coordinate for spatial annotation"
    )
    position_z: Optional[float] = Field(
        None, description="Updated Z coordinate for spatial annotation"
    )


class GenerateVisualsRequest(BaseModel):
    """Request schema for generating visuals for an existing design."""

    model_config = ConfigDict(from_attributes=True)

    visual_types: List[str] = Field(
        default=["floor_plan", "rendering", "3d_model"],
        description="Types of visuals to generate (floor_plan, rendering, 3d_model)",
        examples=[
            ["floor_plan", "rendering", "3d_model"],
            ["floor_plan", "rendering"],
            ["3d_model"],
            ["rendering"],
        ],
    )
    size: str = Field(
        default="1024x1024",
        description="Image size (1024x1024, 1792x1024, 1024x1792)",
        examples=["1024x1024", "1792x1024", "1024x1792"],
    )
    quality: str = Field(
        default="standard",
        description="Image quality (standard, hd)",
        examples=["standard", "hd"],
    )
    priority: str = Field(
        default="normal",
        description="Task priority (low, normal, high)",
        examples=["low", "normal", "high"],
    )
