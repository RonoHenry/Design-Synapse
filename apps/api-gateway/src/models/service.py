"""Service-related data models."""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class HealthStatus(str, Enum):
    """Health status enumeration."""

    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class ServiceInfo(BaseModel):
    """Service information model."""

    name: str = Field(..., description="Service name")
    version: str = Field(..., description="Service version")
    host: str = Field(..., description="Service host")
    port: int = Field(..., description="Service port")
    health_check_url: str = Field(..., description="Health check endpoint URL")
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata"
    )
    registered_at: datetime = Field(
        default_factory=datetime.utcnow, description="Registration timestamp"
    )


class ServiceEndpoint(BaseModel):
    """Service endpoint model."""

    service_name: str = Field(..., description="Service name")
    url: str = Field(..., description="Service URL")
    health_status: HealthStatus = Field(
        default=HealthStatus.UNKNOWN, description="Health status"
    )
    last_health_check: Optional[datetime] = Field(
        None, description="Last health check timestamp"
    )
    response_time_ms: Optional[float] = Field(
        None, description="Response time in milliseconds"
    )


class ServiceRoute(BaseModel):
    """Service route configuration model."""

    path_pattern: str = Field(..., description="URL path pattern to match")
    service_name: str = Field(..., description="Target service name")
    strip_prefix: bool = Field(
        default=True, description="Whether to strip the matched prefix"
    )
    timeout_seconds: int = Field(default=30, description="Request timeout in seconds")
    retry_attempts: int = Field(default=3, description="Number of retry attempts")


class HealthCheck(BaseModel):
    """Individual health check result."""

    name: str = Field(..., description="Health check name")
    status: HealthStatus = Field(..., description="Health check status")
    message: str = Field(..., description="Health check message")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="Check timestamp"
    )


class SystemHealthStatus(BaseModel):
    """System-wide health status."""

    status: HealthStatus = Field(..., description="Overall system health status")
    services: List[ServiceEndpoint] = Field(
        ..., description="Individual service health statuses"
    )
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="Health check timestamp"
    )
    total_services: int = Field(..., description="Total number of registered services")
    healthy_services: int = Field(..., description="Number of healthy services")
