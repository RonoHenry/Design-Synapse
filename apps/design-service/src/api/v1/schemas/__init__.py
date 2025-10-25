"""API v1 schemas package for Design Service."""

from .requests import (
    DesignGenerationRequest,
    DesignUpdateRequest,
    ValidationRequest,
    OptimizationRequest,
)
from .responses import (
    DesignResponse,
    ValidationResponse,
    OptimizationResponse,
    DesignFileResponse,
    DesignCommentResponse,
)

__all__ = [
    # Request schemas
    "DesignGenerationRequest",
    "DesignUpdateRequest",
    "ValidationRequest",
    "OptimizationRequest",
    # Response schemas
    "DesignResponse",
    "ValidationResponse",
    "OptimizationResponse",
    "DesignFileResponse",
    "DesignCommentResponse",
]
