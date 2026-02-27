"""Data models for security hardening components."""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class ThreatLevel(Enum):
    """Threat severity levels."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class AuditLevel(Enum):
    """Audit logging levels."""

    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


@dataclass
class ValidationResult:
    """Result of input validation."""

    is_valid: bool
    threats_detected: List[str]
    risk_level: str
    details: Optional[Dict[str, Any]] = None
    sanitized_value: Optional[str] = None


@dataclass
class SanitizationResult:
    """Result of input sanitization."""

    sanitized_value: str
    was_modified: bool
    modifications: List[str]
    sanitized_data: Optional[Dict[str, Any]] = None


@dataclass
class ThreatEvent:
    """Represents a security threat event."""

    client_ip: str
    event_type: str
    timestamp: datetime
    user_agent: str
    endpoint: str
    user_id: Optional[str] = None
    country_code: Optional[str] = None
    details: Optional[Dict[str, Any]] = None


@dataclass
class ThreatAnalysisResult:
    """Result of threat analysis."""

    is_threat: bool
    threat_level: ThreatLevel
    threat_types: List[str]
    threat_score: int
    confidence: float
    recommended_action: str


@dataclass
class BlockingRule:
    """IP blocking rule configuration."""

    name: str
    condition: str
    action: str
    priority: int
    enabled: bool = True
    created_at: Optional[datetime] = None


@dataclass
class BlockInfo:
    """Information about a blocked IP."""

    ip_address: str
    reason: str
    blocked_at: datetime
    expires_at: Optional[datetime] = None
    is_permanent: bool = False
    block_count: int = 1


@dataclass
class SecurityEvent:
    """Security audit event."""

    event_type: str
    action: str
    timestamp: datetime
    client_ip: Optional[str] = None
    user_id: Optional[str] = None
    severity: str = "INFO"
    details: Optional[Dict[str, Any]] = None


@dataclass
class ComplianceReport:
    """Compliance report data."""

    compliance_framework: str
    report_period_start: datetime
    report_period_end: datetime
    metrics: Dict[str, Any]
    compliance_score: float
    recommendations: List[str]


class SecurityConfig(BaseModel):
    """Security configuration model."""

    enable_input_validation: bool = True
    enable_threat_detection: bool = True
    enable_audit_logging: bool = True
    enable_ip_blocking: bool = True

    # Input validation settings
    max_input_length: int = 10000
    allowed_file_types: List[str] = [".txt", ".json", ".csv"]

    # Threat detection settings
    brute_force_threshold: int = 5
    brute_force_window_minutes: int = 5
    rate_abuse_threshold: int = 100
    rate_abuse_window_minutes: int = 1

    # IP blocking settings
    auto_block_duration_minutes: int = 60
    permanent_block_threshold: int = 10
    whitelist_ips: List[str] = []
    blocked_countries: List[str] = []

    # Audit logging settings
    log_all_requests: bool = False
    log_failed_auth: bool = True
    log_admin_actions: bool = True
    log_data_access: bool = True


@dataclass
class SecurityMetrics:
    """Security metrics for monitoring."""

    total_requests: int
    blocked_requests: int
    threats_detected: int
    ips_blocked: int
    validation_failures: int
    timestamp: datetime
