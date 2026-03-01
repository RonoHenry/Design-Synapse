"""Pydantic schemas for civil engineering calculations."""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class UnitSystem(str, Enum):
    """Unit system enumeration."""

    IMPERIAL = "imperial"
    METRIC = "metric"


class DesignType(str, Enum):
    """Civil design type enumeration."""

    GRADING = "grading"
    STORMWATER = "stormwater"
    UTILITIES = "utilities"
    PAVING = "paving"


# Grading Design Schemas


class GradingDesignRequest(BaseModel):
    """Request schema for grading design."""

    project_id: UUID = Field(..., description="Project identifier")
    site_data: Dict[str, Any] = Field(..., description="Site parameters and topography")
    target_elevations: Dict[str, Any] = Field(
        ..., description="Target elevation points"
    )
    unit_system: UnitSystem = Field(
        default=UnitSystem.IMPERIAL, description="Unit system for design"
    )

    model_config = {"use_enum_values": True}


class GradingDesignResponse(BaseModel):
    """Response schema for grading design."""

    design_id: UUID = Field(..., description="Design identifier")
    project_id: UUID = Field(..., description="Project identifier")
    cut_volume: float = Field(..., description="Cut volume (cubic yards)")
    fill_volume: float = Field(..., description="Fill volume (cubic yards)")
    net_volume: float = Field(..., description="Net volume change")
    grading_plan: Dict[str, Any] = Field(..., description="Grading plan details")
    unit_system: UnitSystem = Field(..., description="Unit system used")
    created_at: datetime = Field(
        default_factory=datetime.utcnow, description="Creation timestamp"
    )

    model_config = {"use_enum_values": True}


# Stormwater Design Schemas


class StormwaterDesignRequest(BaseModel):
    """Request schema for stormwater management design."""

    project_id: UUID = Field(..., description="Project identifier")
    site_data: Dict[str, Any] = Field(
        ..., description="Site parameters and drainage area"
    )
    rainfall_data: Dict[str, Any] = Field(
        ..., description="Rainfall intensity and duration"
    )
    unit_system: UnitSystem = Field(
        default=UnitSystem.IMPERIAL, description="Unit system for design"
    )

    model_config = {"use_enum_values": True}


class StormwaterDesignResponse(BaseModel):
    """Response schema for stormwater management design."""

    design_id: UUID = Field(..., description="Design identifier")
    project_id: UUID = Field(..., description="Project identifier")
    runoff_rate: float = Field(..., description="Peak runoff rate (CFS)")
    detention_volume: float = Field(
        ..., description="Detention pond volume (cubic feet)"
    )
    pipe_sizing: Dict[str, Any] = Field(..., description="Storm pipe sizing details")
    unit_system: UnitSystem = Field(..., description="Unit system used")
    created_at: datetime = Field(
        default_factory=datetime.utcnow, description="Creation timestamp"
    )

    model_config = {"use_enum_values": True}


# Utility Design Schemas


class UtilityDesignRequest(BaseModel):
    """Request schema for utility system design."""

    project_id: UUID = Field(..., description="Project identifier")
    site_data: Dict[str, Any] = Field(
        ..., description="Site parameters and utility connections"
    )
    utility_loads: Dict[str, Any] = Field(..., description="Utility load requirements")
    unit_system: UnitSystem = Field(
        default=UnitSystem.IMPERIAL, description="Unit system for design"
    )

    model_config = {"use_enum_values": True}


class UtilityDesignResponse(BaseModel):
    """Response schema for utility system design."""

    design_id: UUID = Field(..., description="Design identifier")
    project_id: UUID = Field(..., description="Project identifier")
    water_service: Dict[str, Any] = Field(..., description="Water service sizing")
    sewer_service: Dict[str, Any] = Field(..., description="Sewer service sizing")
    gas_service: Optional[Dict[str, Any]] = Field(
        None, description="Gas service sizing"
    )
    unit_system: UnitSystem = Field(..., description="Unit system used")
    created_at: datetime = Field(
        default_factory=datetime.utcnow, description="Creation timestamp"
    )

    model_config = {"use_enum_values": True}
