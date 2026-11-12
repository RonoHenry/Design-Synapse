"""Pydantic schemas for MEP (Mechanical, Electrical, Plumbing) engineering."""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List
from uuid import UUID

from pydantic import BaseModel, Field


class UnitSystem(str, Enum):
    """Unit system enumeration."""

    IMPERIAL = "imperial"
    METRIC = "metric"


class SystemType(str, Enum):
    """MEP system type enumeration."""

    HVAC = "hvac"
    ELECTRICAL = "electrical"
    PLUMBING = "plumbing"
    FIRE_PROTECTION = "fire_protection"


# HVAC Design Schemas


class HVACDesignRequest(BaseModel):
    """Request schema for HVAC system design."""

    project_id: UUID = Field(..., description="Project identifier")
    building_data: Dict[str, Any] = Field(
        ..., description="Building parameters for HVAC design"
    )
    climate_data: Dict[str, Any] = Field(
        ..., description="Climate data for load calculations"
    )
    unit_system: UnitSystem = Field(
        default=UnitSystem.IMPERIAL, description="Unit system for design"
    )

    model_config = {"use_enum_values": True}


class HVACDesignResponse(BaseModel):
    """Response schema for HVAC system design."""

    design_id: UUID = Field(..., description="Design identifier")
    project_id: UUID = Field(..., description="Project identifier")
    heating_load: float = Field(..., description="Heating load (BTU/hr)")
    cooling_load: float = Field(..., description="Cooling load (BTU/hr)")
    equipment_size: Dict[str, Any] = Field(..., description="Equipment sizing details")
    ductwork: Dict[str, Any] = Field(..., description="Ductwork sizing")
    unit_system: UnitSystem = Field(..., description="Unit system used")
    created_at: datetime = Field(
        default_factory=datetime.utcnow, description="Creation timestamp"
    )

    model_config = {"use_enum_values": True}


# Electrical Design Schemas


class ElectricalDesignRequest(BaseModel):
    """Request schema for electrical system design."""

    project_id: UUID = Field(..., description="Project identifier")
    loads: Dict[str, Any] = Field(..., description="Electrical loads by circuit")
    voltage: float = Field(..., gt=0, description="System voltage")
    unit_system: UnitSystem = Field(
        default=UnitSystem.IMPERIAL, description="Unit system for design"
    )

    model_config = {"use_enum_values": True}


class ElectricalDesignResponse(BaseModel):
    """Response schema for electrical system design."""

    design_id: UUID = Field(..., description="Design identifier")
    project_id: UUID = Field(..., description="Project identifier")
    total_load: float = Field(..., description="Total electrical load (W)")
    panel_size: Dict[str, Any] = Field(..., description="Panel sizing details")
    circuit_sizing: Dict[str, Any] = Field(..., description="Circuit conductor sizing")
    unit_system: UnitSystem = Field(..., description="Unit system used")
    created_at: datetime = Field(
        default_factory=datetime.utcnow, description="Creation timestamp"
    )

    model_config = {"use_enum_values": True}


# Plumbing Design Schemas


class PlumbingDesignRequest(BaseModel):
    """Request schema for plumbing system design."""

    project_id: UUID = Field(..., description="Project identifier")
    fixtures: List[Dict[str, Any]] = Field(..., description="Plumbing fixtures list")
    supply_pressure: float = Field(..., gt=0, description="Water supply pressure (psi)")
    unit_system: UnitSystem = Field(
        default=UnitSystem.IMPERIAL, description="Unit system for design"
    )

    model_config = {"use_enum_values": True}


class PlumbingDesignResponse(BaseModel):
    """Response schema for plumbing system design."""

    design_id: UUID = Field(..., description="Design identifier")
    project_id: UUID = Field(..., description="Project identifier")
    fixture_units: float = Field(..., description="Total fixture units")
    pipe_sizing: Dict[str, Any] = Field(..., description="Pipe sizing details")
    water_demand: float = Field(..., description="Peak water demand (GPM)")
    unit_system: UnitSystem = Field(..., description="Unit system used")
    created_at: datetime = Field(
        default_factory=datetime.utcnow, description="Creation timestamp"
    )

    model_config = {"use_enum_values": True}


# Fire Protection Design Schemas


class FireProtectionDesignRequest(BaseModel):
    """Request schema for fire protection system design."""

    project_id: UUID = Field(..., description="Project identifier")
    building_data: Dict[str, Any] = Field(
        ..., description="Building parameters for fire protection"
    )
    occupancy_type: str = Field(..., description="Building occupancy classification")
    unit_system: UnitSystem = Field(
        default=UnitSystem.IMPERIAL, description="Unit system for design"
    )

    model_config = {"use_enum_values": True}


class FireProtectionDesignResponse(BaseModel):
    """Response schema for fire protection system design."""

    design_id: UUID = Field(..., description="Design identifier")
    project_id: UUID = Field(..., description="Project identifier")
    system_type: str = Field(..., description="Fire protection system type")
    sprinkler_density: float = Field(..., description="Sprinkler density (GPM/sq ft)")
    water_demand: float = Field(..., description="Water demand (GPM)")
    pipe_sizing: Dict[str, Any] = Field(..., description="Pipe sizing details")
    unit_system: UnitSystem = Field(..., description="Unit system used")
    created_at: datetime = Field(
        default_factory=datetime.utcnow, description="Creation timestamp"
    )

    model_config = {"use_enum_values": True}
