"""Enums for API schemas."""

from enum import Enum


class BuildingType(str, Enum):
    """Building type classification."""

    RESIDENTIAL = "residential"
    COMMERCIAL = "commercial"
    INDUSTRIAL = "industrial"
    INSTITUTIONAL = "institutional"
    MIXED_USE = "mixed_use"
    AGRICULTURAL = "agricultural"


class DesignStatus(str, Enum):
    """Design document status."""

    DRAFT = "draft"
    IN_REVIEW = "in_review"
    APPROVED = "approved"
    ARCHIVED = "archived"


class DrawingType(str, Enum):
    """Architectural drawing types."""

    FLOOR_PLAN = "floor_plan"
    ELEVATION = "elevation"
    SECTION = "section"
    SITE_PLAN = "site_plan"
    DETAIL = "detail"
    ROOF_PLAN = "roof_plan"
    REFLECTED_CEILING_PLAN = "reflected_ceiling_plan"
    THREE_D_VIEW = "3d_view"


class ComplianceCheckType(str, Enum):
    """Types of compliance checks."""

    BUILDING_CODE = "building_code"
    ZONING = "zoning"
    ACCESSIBILITY = "accessibility"
    ENERGY = "energy"
    FIRE_SAFETY = "fire_safety"
    STRUCTURAL = "structural"
    PLUMBING = "plumbing"
    ELECTRICAL = "electrical"
    MECHANICAL = "mechanical"


class StructuralSystem(str, Enum):
    """Structural system types."""

    STEEL_FRAME = "steel_frame"
    CONCRETE = "concrete"
    WOOD_FRAME = "wood_frame"
    MASONRY = "masonry"
    HYBRID = "hybrid"
    PRECAST_CONCRETE = "precast_concrete"
    POST_TENSIONED = "post_tensioned"


class MaterialCategory(str, Enum):
    """Material categories."""

    STRUCTURAL = "structural"
    FINISHES = "finishes"
    MECHANICAL = "mechanical"
    ELECTRICAL = "electrical"
    PLUMBING = "plumbing"
    INSULATION = "insulation"
    ROOFING = "roofing"
    GLAZING = "glazing"
    DOORS_WINDOWS = "doors_windows"
    HARDWARE = "hardware"


class CheckStatus(str, Enum):
    """Status for analysis and check operations."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class AnalysisType(str, Enum):
    """Types of structural analysis."""

    STATIC = "static"
    DYNAMIC = "dynamic"
    SEISMIC = "seismic"
    WIND = "wind"
    THERMAL = "thermal"
    MODAL = "modal"


class OptimizationGoal(str, Enum):
    """Space planning optimization goals."""

    MAXIMIZE_EFFICIENCY = "maximize_efficiency"
    MINIMIZE_CIRCULATION = "minimize_circulation"
    MAXIMIZE_NATURAL_LIGHT = "maximize_natural_light"
    OPTIMIZE_ADJACENCIES = "optimize_adjacencies"
    MINIMIZE_COST = "minimize_cost"
