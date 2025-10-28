"""
Security hardening measures and threat detection.

This module provides:
- Input validation and sanitization middleware
- Automated threat detection and IP blocking
- Security audit logging and compliance reporting
- Attack vector protection (SQL injection, XSS, etc.)
- Real-time security monitoring and alerting
"""

import asyncio
import hashlib
import html
import re
import secrets
import time
import urllib.parse
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set, Tuple

from .models import CacheConfig, PoolConfig


@dataclass
class SecurityEvent:
    """Security event for audit logging."""

    event_type: str
    details: str
    ip_address: Optional[str] = None
    user_id: Optional[str] = None
    severity: str = "medium"
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class ThreatPattern:
    """Threat detection pattern."""

    name: str
    pattern: str
    severity: str
    description: str


@dataclass
class SecurityAlert:
    """Security alert for real-time monitoring."""

    alert_type: str
    message: str
    severity: str
    count: int
    first_seen: datetime
    last_seen: datetime = field(default_factory=datetime.utcnow)


class SecurityHardening:
    """Security hardening and input validation system."""

    def __init__(self, cache_config: CacheConfig, pool_config: PoolConfig):
        """Initialize security hardening system."""
        self.cache_config = cache_config
        self.pool_config = pool_config

        # Rate limiting for DDoS protection
        self.rate_limits: Dict[str, List[float]] = defaultdict(list)
        self.blocked_ips: Set[str] = set()
        self.ip_block_reasons: Dict[str, str] = {}

        # Threat detection
        self.detected_threats: List[Dict[str, Any]] = []

        # Security patterns
        self.sql_injection_patterns = [
            r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|UNION)\b)",
            r"(--|#|/\*|\*/)",
            r"(\b(OR|AND)\s+\d+\s*=\s*\d+)",
            r"('.*'.*=.*'.*')",
        ]

        self.xss_patterns = [
            r"<script[^>]*>.*?</script>",
            r"<img[^>]*onerror[^>]*>",
            r"javascript:",
            r"<svg[^>]*onload[^>]*>",
            r"<iframe[^>]*>",
        ]

        self.command_injection_patterns = [
            r"[;&|`]",
            r"\$\([^)]*\)",
            r"`[^`]*`",
            r"\|\s*(cat|ls|pwd|whoami|id)",
        ]

        self.path_traversal_patterns = [
            r"\.\./",
            r"\.\.\\",
            r"%2e%2e%2f",
            r"%2e%2e%5c",
        ]

    async def sanitize_input(self, user_input: str) -> str:
        """Sanitize user input to prevent various attacks."""
        if not isinstance(user_input, str):
            return str(user_input)

        # HTML escape to prevent XSS
        sanitized = html.escape(user_input)

        # Remove SQL injection patterns
        for pattern in self.sql_injection_patterns:
            sanitized = re.sub(pattern, "", sanitized, flags=re.IGNORECASE)

        # Remove script tags and event handlers
        for pattern in self.xss_patterns:
            sanitized = re.sub(pattern, "", sanitized, flags=re.IGNORECASE)

        # Remove command injection characters
        for pattern in self.command_injection_patterns:
            sanitized = re.sub(pattern, "", sanitized)

        # URL decode and re-encode to normalize
        try:
            decoded = urllib.parse.unquote(sanitized)
            sanitized = urllib.parse.quote(decoded, safe="")
        except Exception:
            pass

        return sanitized

    async def sanitize_path(self, path: str) -> str:
        """Sanitize file paths to prevent directory traversal."""
        if not isinstance(path, str):
            return str(path)

        # Remove path traversal patterns
        sanitized = path
        for pattern in self.path_traversal_patterns:
            sanitized = re.sub(pattern, "", sanitized, flags=re.IGNORECASE)

        # Remove leading slashes and backslashes
        sanitized = sanitized.lstrip("/\\")

        # URL decode
        try:
            sanitized = urllib.parse.unquote(sanitized)
        except Exception:
            pass

        # Remove any remaining dangerous patterns
        sanitized = sanitized.replace("..", "")
        sanitized = sanitized.replace("/etc/", "")
        sanitized = sanitized.replace("\\windows\\", "")

        return sanitized

    async def check_rate_limit(
        self, client_ip: str, max_requests: int = 100, window_seconds: int = 60
    ) -> bool:
        """Check if client IP is within rate limits."""
        current_time = time.time()

        # Clean old requests outside the window
        self.rate_limits[client_ip] = [
            req_time
            for req_time in self.rate_limits[client_ip]
            if current_time - req_time < window_seconds
        ]

        # Check if within limits
        if len(self.rate_limits[client_ip]) >= max_requests:
            return False

        # Record this request
        self.rate_limits[client_ip].append(current_time)
        return True

    async def block_ip(self, ip_address: str, reason: str = "Security violation"):
        """Block an IP address."""
        self.blocked_ips.add(ip_address)
        self.ip_block_reasons[ip_address] = reason

    async def is_ip_blocked(self, ip_address: str) -> bool:
        """Check if IP address is blocked."""
        return ip_address in self.blocked_ips

    async def check_ip_allowed(self, ip_address: str) -> bool:
        """Check if IP address is allowed to make requests."""
        return not await self.is_ip_blocked(ip_address)

    async def detect_threat(self, input_data: str) -> bool:
        """Detect threats in input data."""
        threats_found = []

        # Check for SQL injection
        for pattern in self.sql_injection_patterns:
            if re.search(pattern, input_data, re.IGNORECASE):
                threats_found.append("SQL Injection")
                break

        # Check for XSS
        for pattern in self.xss_patterns:
            if re.search(pattern, input_data, re.IGNORECASE):
                threats_found.append("XSS")
                break

        # Check for command injection
        for pattern in self.command_injection_patterns:
            if re.search(pattern, input_data):
                threats_found.append("Command Injection")
                break

        # Check for path traversal
        for pattern in self.path_traversal_patterns:
            if re.search(pattern, input_data, re.IGNORECASE):
                threats_found.append("Path Traversal")
                break

        if threats_found:
            self.detected_threats.append(
                {
                    "threats": threats_found,
                    "input": input_data[:100],  # Truncate for logging
                    "timestamp": datetime.utcnow(),
                }
            )
            return True

        return False

    async def get_detected_threats(self) -> List[Dict[str, Any]]:
        """Get list of detected threats."""
        return self.detected_threats

    async def get_security_headers(self) -> Dict[str, str]:
        """Get recommended security headers."""
        return {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
            "Content-Security-Policy": "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'",
            "Referrer-Policy": "strict-origin-when-cross-origin",
            "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
        }

    async def validate_auth_input(self, auth_input: str) -> bool:
        """Validate authentication input for bypass attempts."""
        # Check for common SQL injection auth bypass patterns
        bypass_patterns = [
            r"admin['\s]*--",
            r"'\s*OR\s*'1'\s*=\s*'1",
            r"admin'\s*OR\s*1\s*=\s*1",
            r"';\s*EXEC\s+",
        ]

        for pattern in bypass_patterns:
            if re.search(pattern, auth_input, re.IGNORECASE):
                return False

        return True

    async def generate_secure_token(self, length: int = 32) -> str:
        """Generate cryptographically secure token."""
        return secrets.token_urlsafe(length)

    async def validate_session_token(self, token: str) -> bool:
        """Validate session token format and security."""
        if not token or len(token) < 16:
            return False

        # Check if token contains only safe characters
        safe_chars = set(
            "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_"
        )
        return all(c in safe_chars for c in token)


class ThreatDetector:
    """Advanced threat detection system."""

    def __init__(self):
        """Initialize threat detector."""
        self.patterns: List[ThreatPattern] = []
        self.blocked_ips: Set[str] = set()
        self.failed_logins: Dict[str, List[datetime]] = defaultdict(list)
        self.request_history: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        self.user_locations: Dict[str, List[Tuple[str, str, datetime]]] = defaultdict(
            list
        )

        # Initialize threat patterns
        self._initialize_patterns()

    def _initialize_patterns(self):
        """Initialize threat detection patterns."""
        self.patterns = [
            ThreatPattern(
                name="SQL Injection",
                pattern=r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|UNION)\b|--|#|/\*|\*/)",
                severity="high",
                description="SQL injection attempt detected",
            ),
            ThreatPattern(
                name="XSS Attack",
                pattern=r"(<script[^>]*>|<img[^>]*onerror|javascript:|<svg[^>]*onload)",
                severity="high",
                description="Cross-site scripting attempt detected",
            ),
            ThreatPattern(
                name="Command Injection",
                pattern=r"([;&|`]|\$\([^)]*\)|`[^`]*`|\|\s*(cat|ls|pwd|whoami|id))",
                severity="critical",
                description="Command injection attempt detected",
            ),
            ThreatPattern(
                name="Path Traversal",
                pattern=r"(\.\./|\.\.\\|%2e%2e%2f|%2e%2e%5c)",
                severity="medium",
                description="Directory traversal attempt detected",
            ),
        ]

    async def detect_sql_injection(self, input_data: str) -> bool:
        """Detect SQL injection patterns."""
        sql_pattern = next(
            (p for p in self.patterns if p.name == "SQL Injection"), None
        )
        if sql_pattern:
            return bool(re.search(sql_pattern.pattern, input_data, re.IGNORECASE))
        return False

    async def detect_xss(self, input_data: str) -> bool:
        """Detect XSS attack patterns."""
        xss_pattern = next((p for p in self.patterns if p.name == "XSS Attack"), None)
        if xss_pattern:
            return bool(re.search(xss_pattern.pattern, input_data, re.IGNORECASE))
        return False

    async def record_failed_login(self, client_ip: str):
        """Record failed login attempt."""
        self.failed_logins[client_ip].append(datetime.utcnow())

        # Keep only recent attempts (last hour)
        cutoff_time = datetime.utcnow() - timedelta(hours=1)
        self.failed_logins[client_ip] = [
            attempt
            for attempt in self.failed_logins[client_ip]
            if attempt > cutoff_time
        ]

    async def detect_brute_force(self, client_ip: str, threshold: int = 5) -> bool:
        """Detect brute force attacks."""
        return len(self.failed_logins[client_ip]) >= threshold

    async def record_request(self, ip: str, size: int, response_time: float):
        """Record request for anomaly detection."""
        self.request_history[ip].append(
            {
                "size": size,
                "response_time": response_time,
                "timestamp": datetime.utcnow(),
            }
        )

        # Keep only recent requests (last hour)
        cutoff_time = datetime.utcnow() - timedelta(hours=1)
        self.request_history[ip] = [
            req for req in self.request_history[ip] if req["timestamp"] > cutoff_time
        ]

    async def detect_anomaly(
        self, ip: str, request_size: int, response_time: float
    ) -> bool:
        """Detect anomalous request patterns."""
        history = self.request_history[ip]

        if len(history) < 10:  # Need baseline
            return False

        # Calculate baseline metrics
        avg_size = sum(req["size"] for req in history) / len(history)
        avg_response_time = sum(req["response_time"] for req in history) / len(history)

        # Detect anomalies (more than 10x normal)
        size_anomaly = request_size > avg_size * 10
        time_anomaly = response_time > avg_response_time * 10

        return size_anomaly or time_anomaly

    async def record_login(self, user_id: str, country: str, ip: str):
        """Record user login location."""
        self.user_locations[user_id].append((country, ip, datetime.utcnow()))

        # Keep only recent logins (last 30 days)
        cutoff_time = datetime.utcnow() - timedelta(days=30)
        self.user_locations[user_id] = [
            login for login in self.user_locations[user_id] if login[2] > cutoff_time
        ]

    async def detect_geographic_anomaly(
        self, user_id: str, country: str, ip: str
    ) -> bool:
        """Detect geographic anomalies in user logins."""
        recent_logins = self.user_locations[user_id]

        if not recent_logins:
            return False

        # Check if user has logged in from this country recently
        recent_countries = [login[0] for login in recent_logins[-10:]]  # Last 10 logins

        # If all recent logins are from different country, it's anomalous
        return country not in recent_countries and len(set(recent_countries)) == 1

    async def detect_threat(self, input_data: str) -> bool:
        """Detect any threat pattern in input."""
        for pattern in self.patterns:
            if re.search(pattern.pattern, input_data, re.IGNORECASE):
                return True
        return False


class SecurityAuditLogger:
    """Security audit logging and compliance reporting."""

    def __init__(self, retention_days: int = 90):
        """Initialize security audit logger."""
        self.log_buffer: deque = deque(maxlen=10000)
        self.retention_days = retention_days
        self.alert_thresholds: Dict[str, Tuple[int, timedelta]] = {}
        self.active_alerts: List[SecurityAlert] = []

    async def log_threat_detected(
        self, threat_type: str, ip_address: str, details: str
    ):
        """Log threat detection event."""
        event = SecurityEvent(
            event_type="threat_detected",
            details=f"{threat_type}: {details}",
            ip_address=ip_address,
            severity="high",
        )
        self.log_buffer.append(event)

    async def log_ip_blocked(self, ip_address: str, reason: str):
        """Log IP blocking event."""
        event = SecurityEvent(
            event_type="ip_blocked",
            details=reason,
            ip_address=ip_address,
            severity="medium",
        )
        self.log_buffer.append(event)

    async def log_auth_failure(self, user_id: str, ip_address: str, reason: str):
        """Log authentication failure."""
        event = SecurityEvent(
            event_type="auth_failure",
            details=reason,
            ip_address=ip_address,
            user_id=user_id,
            severity="medium",
        )
        self.log_buffer.append(event)

    async def log_data_access(self, user_id: str, resource: str, action: str):
        """Log data access for compliance."""
        event = SecurityEvent(
            event_type="data_access",
            details=f"{action} on {resource}",
            user_id=user_id,
            severity="low",
        )
        self.log_buffer.append(event)

    async def log_privilege_escalation(self, user_id: str, new_role: str, action: str):
        """Log privilege changes."""
        event = SecurityEvent(
            event_type="privilege_change",
            details=f"{action} role {new_role}",
            user_id=user_id,
            severity="high",
        )
        self.log_buffer.append(event)

    async def log_security_event(
        self,
        event_type: str,
        details: str,
        ip_address: Optional[str] = None,
        user_id: Optional[str] = None,
        timestamp: Optional[datetime] = None,
    ):
        """Log generic security event."""
        event = SecurityEvent(
            event_type=event_type,
            details=details,
            ip_address=ip_address,
            user_id=user_id,
            timestamp=timestamp or datetime.utcnow(),
        )
        self.log_buffer.append(event)

    async def get_security_events(
        self, event_type: Optional[str] = None
    ) -> List[SecurityEvent]:
        """Get security events, optionally filtered by type."""
        events = list(self.log_buffer)

        if event_type:
            events = [event for event in events if event.event_type == event_type]

        return events

    async def generate_compliance_report(
        self, start_date: datetime, end_date: datetime
    ) -> Dict[str, Any]:
        """Generate compliance report for date range."""
        events = [
            event
            for event in self.log_buffer
            if start_date <= event.timestamp <= end_date
        ]

        # Group events by type
        event_counts = defaultdict(int)
        for event in events:
            event_counts[event.event_type] += 1

        # Data access events
        data_access_events = [e for e in events if e.event_type == "data_access"]

        # Privilege changes
        privilege_changes = [e for e in events if e.event_type == "privilege_change"]

        return {
            "report_period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat(),
            },
            "total_events": len(events),
            "event_counts": dict(event_counts),
            "data_access_events": len(data_access_events),
            "privilege_changes": len(privilege_changes),
            "high_severity_events": len([e for e in events if e.severity == "high"]),
            "critical_events": len([e for e in events if e.severity == "critical"]),
        }

    async def cleanup_old_events(self):
        """Clean up events older than retention period."""
        cutoff_date = datetime.utcnow() - timedelta(days=self.retention_days)

        # Filter out old events
        recent_events = [
            event for event in self.log_buffer if event.timestamp > cutoff_date
        ]

        # Replace buffer with recent events
        self.log_buffer.clear()
        self.log_buffer.extend(recent_events)

    async def set_alert_threshold(
        self, event_type: str, count: int, time_window: timedelta
    ):
        """Set alert threshold for event type."""
        self.alert_thresholds[event_type] = (count, time_window)

    async def get_active_alerts(self) -> List[SecurityAlert]:
        """Get active security alerts."""
        current_time = datetime.utcnow()

        # Check thresholds
        for event_type, (threshold_count, time_window) in self.alert_thresholds.items():
            cutoff_time = current_time - time_window

            # Count recent events of this type
            recent_events = [
                event
                for event in self.log_buffer
                if event.event_type == event_type and event.timestamp > cutoff_time
            ]

            if len(recent_events) >= threshold_count:
                # Check if alert already exists
                existing_alert = next(
                    (
                        alert
                        for alert in self.active_alerts
                        if alert.alert_type == event_type
                    ),
                    None,
                )

                if existing_alert:
                    existing_alert.count = len(recent_events)
                    existing_alert.last_seen = current_time
                else:
                    # Create new alert
                    alert = SecurityAlert(
                        alert_type=event_type,
                        message=f"High frequency of {event_type} events: {len(recent_events)} in {time_window}",
                        severity="high",
                        count=len(recent_events),
                        first_seen=recent_events[0].timestamp,
                    )
                    self.active_alerts.append(alert)

        return self.active_alerts
