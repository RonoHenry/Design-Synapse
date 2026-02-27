"""Request and response models."""

from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class GatewayRequest(BaseModel):
    """Gateway request model."""

    method: str = Field(..., description="HTTP method")
    path: str = Field(..., description="Request path")
    headers: Dict[str, str] = Field(default_factory=dict, description="Request headers")
    query_params: Dict[str, str] = Field(
        default_factory=dict, description="Query parameters"
    )
    body: Optional[bytes] = Field(None, description="Request body")
    client_ip: str = Field(..., description="Client IP address")
    user_agent: Optional[str] = Field(None, description="User agent")
    request_id: str = Field(..., description="Unique request ID")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="Request timestamp"
    )


class GatewayResponse(BaseModel):
    """Gateway response model."""

    status_code: int = Field(..., description="HTTP status code")
    headers: Dict[str, str] = Field(
        default_factory=dict, description="Response headers"
    )
    body: Optional[bytes] = Field(None, description="Response body")
    response_time_ms: float = Field(..., description="Response time in milliseconds")
    service_name: Optional[str] = Field(None, description="Target service name")
    request_id: str = Field(..., description="Request ID")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="Response timestamp"
    )


class ErrorResponse(BaseModel):
    """Standardized error response model."""

    error_code: str = Field(..., description="Error code")
    message: str = Field(..., description="Error message")
    details: Optional[Dict[str, Any]] = Field(
        None, description="Additional error details"
    )
    request_id: str = Field(..., description="Request ID")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="Error timestamp"
    )


class HealthResponse(BaseModel):
    """Health check response model."""

    status: str = Field(..., description="Health status")
    version: str = Field(..., description="Service version")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="Health check timestamp"
    )
    uptime_seconds: float = Field(..., description="Service uptime in seconds")
    dependencies: Dict[str, str] = Field(
        default_factory=dict, description="Dependency health status"
    )
