"""
Data models for monitoring components.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

try:
    from packages.common.service_registry.models import HealthStatus
except ImportError:
    # Fallback for when running tests or in different contexts
    from ...service_registry.models import HealthStatus


class LogLevel(str, Enum):
    """Log levels for structured logging."""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


@dataclass
class LogEntry:
    """Structured log entry model."""

    timestamp: datetime
    level: LogLevel
    service: str
    message: str
    request_id: Optional[str] = None
    user_id: Optional[str] = None
    correlation_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert log entry to dictionary for serialization."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "level": self.level.value,
            "service": self.service,
            "message": self.message,
            "request_id": self.request_id,
            "user_id": self.user_id,
            "correlation_id": self.correlation_id,
            "metadata": self.metadata,
        }


@dataclass
class MetricPoint:
    """Individual metric data point."""

    name: str
    value: float
    labels: Dict[str, str] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        """Convert metric point to dictionary for serialization."""
        return {
            "name": self.name,
            "value": self.value,
            "labels": self.labels,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class LogFilters:
    """Filters for log queries."""

    service: Optional[str] = None
    level: Optional[LogLevel] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    request_id: Optional[str] = None
    user_id: Optional[str] = None
    correlation_id: Optional[str] = None
    limit: int = 100


@dataclass
class ServiceHealth:
    """Health status for a single service."""

    service_name: str
    status: HealthStatus
    message: str
    timestamp: datetime
    response_time_ms: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SystemHealthStatus:
    """Aggregated system health status."""

    overall_status: HealthStatus
    services: List[ServiceHealth]
    timestamp: datetime
    healthy_count: int = 0
    unhealthy_count: int = 0
    unknown_count: int = 0

    def __post_init__(self):
        """Calculate service counts after initialization."""
        self.healthy_count = sum(
            1 for s in self.services if s.status == HealthStatus.HEALTHY
        )
        self.unhealthy_count = sum(
            1 for s in self.services if s.status == HealthStatus.UNHEALTHY
        )
        self.unknown_count = sum(
            1 for s in self.services if s.status == HealthStatus.UNKNOWN
        )
