"""Service Registry data models."""

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
    """Service information model for registration."""

    name: str = Field(..., min_length=1, description="Service name")
    version: str = Field(..., min_length=1, description="Service version")
    host: str = Field(..., min_length=1, description="Service host")
    port: int = Field(..., ge=1, le=65535, description="Service port")
    health_check_url: str = Field(..., description="Health check endpoint URL")
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata"
    )
    tags: List[str] = Field(
        default_factory=list, description="Service tags for filtering"
    )

    class Config:
        """Pydantic configuration."""

        json_encoders = {datetime: lambda v: v.isoformat()}


class ServiceEndpoint(BaseModel):
    """Service endpoint model with health information."""

    service_name: str = Field(..., description="Service name")
    instance_id: str = Field(..., description="Unique instance identifier")
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
    consecutive_failures: int = Field(
        default=0, description="Number of consecutive health check failures"
    )
    registered_at: datetime = Field(
        default_factory=datetime.utcnow, description="Registration timestamp"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata"
    )
    tags: List[str] = Field(default_factory=list, description="Service tags")

    class Config:
        """Pydantic configuration."""

        json_encoders = {datetime: lambda v: v.isoformat()}


class HealthCheck(BaseModel):
    """Individual health check result."""

    name: str = Field(..., description="Health check name")
    status: HealthStatus = Field(..., description="Health check status")
    message: str = Field(..., description="Health check message")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="Check timestamp"
    )
    response_time_ms: Optional[float] = Field(
        None, description="Response time in milliseconds"
    )

    class Config:
        """Pydantic configuration."""

        json_encoders = {datetime: lambda v: v.isoformat()}


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
    unhealthy_services: int = Field(..., description="Number of unhealthy services")
    unknown_services: int = Field(
        ..., description="Number of services with unknown status"
    )

    class Config:
        """Pydantic configuration."""

        json_encoders = {datetime: lambda v: v.isoformat()}


class ServiceRegistrationRequest(BaseModel):
    """Request model for service registration."""

    service: ServiceInfo = Field(..., description="Service information")
    health_check_interval: int = Field(
        default=30, description="Health check interval in seconds"
    )
    failure_threshold: int = Field(
        default=3, description="Number of failures before marking unhealthy"
    )

    class Config:
        """Pydantic configuration."""

        json_encoders = {datetime: lambda v: v.isoformat()}


class ServiceDiscoveryFilter(BaseModel):
    """Filter criteria for service discovery."""

    service_name: Optional[str] = Field(None, description="Filter by service name")
    tags: List[str] = Field(
        default_factory=list, description="Filter by tags (all must match)"
    )
    health_status: Optional[HealthStatus] = Field(
        None, description="Filter by health status"
    )
    min_response_time: Optional[float] = Field(
        None, description="Minimum response time filter"
    )
    max_response_time: Optional[float] = Field(
        None, description="Maximum response time filter"
    )

    class Config:
        """Pydantic configuration."""

        json_encoders = {datetime: lambda v: v.isoformat()}
