"""Pydantic schemas for structural engineering calculations."""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class UnitSystem(str, Enum):
    """Unit system enumeration."""

    IMPERIAL = "imperial"
    METRIC = "metric"


class LoadType(str, Enum):
    """Load type enumeration."""

    DEAD = "dead"
    LIVE = "live"
    WIND = "wind"
    SEISMIC = "seismic"


# Load Calculation Schemas


class LoadCalculationRequest(BaseModel):
    """Request schema for load calculations."""

    project_id: UUID = Field(..., description="Project identifier")
    building_data: Dict[str, Any] = Field(
        ..., description="Building parameters for load calculation"
    )
    load_types: List[LoadType] = Field(..., description="Types of loads to calculate")
    unit_system: UnitSystem = Field(
        default=UnitSystem.IMPERIAL, description="Unit system for calculations"
    )

    model_config = {"use_enum_values": True}


class LoadCalculationResponse(BaseModel):
    """Response schema for load calculations."""

    calculation_id: UUID = Field(..., description="Calculation identifier")
    project_id: UUID = Field(..., description="Project identifier")
    dead_load: float = Field(..., description="Dead load value")
    live_load: float = Field(..., description="Live load value")
    wind_load: Optional[float] = Field(None, description="Wind load value")
    seismic_load: Optional[float] = Field(None, description="Seismic load value")
    total_load: float = Field(..., description="Total combined load")
    unit_system: UnitSystem = Field(..., description="Unit system used")
    created_at: datetime = Field(
        default_factory=datetime.utcnow, description="Creation timestamp"
    )

    model_config = {"use_enum_values": True}


# Beam Design Schemas


class BeamDesignRequest(BaseModel):
    """Request schema for beam design."""

    project_id: UUID = Field(..., description="Project identifier")
    loads: Dict[str, Any] = Field(..., description="Beam loads")
    span: float = Field(..., gt=0, description="Beam span length")
    material: Dict[str, Any] = Field(..., description="Material properties")
    unit_system: UnitSystem = Field(
        default=UnitSystem.IMPERIAL, description="Unit system for design"
    )

    model_config = {"use_enum_values": True}


class BeamDesignResponse(BaseModel):
    """Response schema for beam design."""

    design_id: UUID = Field(..., description="Design identifier")
    project_id: UUID = Field(..., description="Project identifier")
    required_section: str = Field(..., description="Required beam section")
    deflection: float = Field(..., description="Maximum deflection")
    stress_ratio: float = Field(..., description="Stress utilization ratio")
    is_adequate: bool = Field(..., description="Whether design is adequate")
    unit_system: UnitSystem = Field(..., description="Unit system used")
    created_at: datetime = Field(
        default_factory=datetime.utcnow, description="Creation timestamp"
    )

    model_config = {"use_enum_values": True}


# Column Design Schemas


class ColumnDesignRequest(BaseModel):
    """Request schema for column design."""

    project_id: UUID = Field(..., description="Project identifier")
    axial_load: float = Field(..., gt=0, description="Axial load on column")
    moment: float = Field(..., description="Bending moment on column")
    length: float = Field(..., gt=0, description="Column length")
    material: Dict[str, Any] = Field(..., description="Material properties")
    unit_system: UnitSystem = Field(
        default=UnitSystem.IMPERIAL, description="Unit system for design"
    )

    model_config = {"use_enum_values": True}


class ColumnDesignResponse(BaseModel):
    """Response schema for column design."""

    design_id: UUID = Field(..., description="Design identifier")
    project_id: UUID = Field(..., description="Project identifier")
    required_section: str = Field(..., description="Required column section")
    axial_capacity: float = Field(..., description="Axial load capacity")
    buckling_ratio: float = Field(..., description="Buckling utilization ratio")
    stress_ratio: float = Field(..., description="Stress utilization ratio")
    is_adequate: bool = Field(..., description="Whether design is adequate")
    unit_system: UnitSystem = Field(..., description="Unit system used")
    created_at: datetime = Field(
        default_factory=datetime.utcnow, description="Creation timestamp"
    )

    model_config = {"use_enum_values": True}


# Foundation Design Schemas


class FoundationDesignRequest(BaseModel):
    """Request schema for foundation design."""

    project_id: UUID = Field(..., description="Project identifier")
    loads: Dict[str, Any] = Field(..., description="Foundation loads")
    soil_properties: Dict[str, Any] = Field(..., description="Soil properties")
    unit_system: UnitSystem = Field(
        default=UnitSystem.IMPERIAL, description="Unit system for design"
    )

    @field_validator("soil_properties")
    @classmethod
    def validate_bearing_capacity(cls, v: Dict[str, Any]) -> Dict[str, Any]:
        """Validate bearing capacity is positive."""
        if "bearing_capacity" in v and v["bearing_capacity"] <= 0:
            raise ValueError("bearing_capacity must be positive")
        return v

    model_config = {"use_enum_values": True}


class FoundationDesignResponse(BaseModel):
    """Response schema for foundation design."""

    design_id: UUID = Field(..., description="Design identifier")
    project_id: UUID = Field(..., description="Project identifier")
    foundation_type: str = Field(..., description="Type of foundation")
    dimensions: Dict[str, Any] = Field(..., description="Foundation dimensions")
    bearing_pressure: float = Field(..., description="Bearing pressure")
    settlement: float = Field(..., description="Expected settlement")
    reinforcement: Dict[str, Any] = Field(..., description="Reinforcement details")
    is_adequate: bool = Field(..., description="Whether design is adequate")
    unit_system: UnitSystem = Field(..., description="Unit system used")
    created_at: datetime = Field(
        default_factory=datetime.utcnow, description="Creation timestamp"
    )

    model_config = {"use_enum_values": True}
