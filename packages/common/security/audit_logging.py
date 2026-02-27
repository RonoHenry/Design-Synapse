"""Security audit logging and compliance reporting."""

import asyncio
import json
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from .models import AuditLevel, ComplianceReport, SecurityEvent


class SecurityAuditor:
    """Handles security event logging and audit trails."""

    def __init__(self, storage=None):
        self.storage = storage  # Redis or similar storage

        # In-memory storage for testing
        self.events = []
        self.event_counts = defaultdict(int)

    async def log_security_event(self, event: SecurityEvent):
        """Log a security event for audit purposes."""
        # Always store in memory for analysis (even when using Redis)
        self.events.append(event)

        if self.storage:
            # Also store in Redis/database for persistence
            event_data = {
                "event_type": event.event_type,
                "action": event.action,
                "timestamp": event.timestamp.isoformat(),
                "client_ip": event.client_ip,
                "user_id": event.user_id,
                "severity": event.severity,
                "details": event.details or {},
            }

            key = f"security_event:{event.timestamp.timestamp()}"
            await self.storage.set(key, json.dumps(event_data), ex=86400)  # 24 hours

        # Update event counts
        self.event_counts[event.event_type] += 1

    async def get_security_events(
        self,
        event_type: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        user_id: Optional[str] = None,
        client_ip: Optional[str] = None,
    ) -> List[SecurityEvent]:
        """Retrieve security events based on filters."""
        # Always use in-memory storage for filtering (even with Redis)
        # In production, this would be replaced with proper Redis/database queries
        filtered_events = self.events

        if event_type:
            filtered_events = [e for e in filtered_events if e.event_type == event_type]

        if start_time:
            filtered_events = [e for e in filtered_events if e.timestamp >= start_time]

        if end_time:
            filtered_events = [e for e in filtered_events if e.timestamp <= end_time]

        if user_id:
            filtered_events = [e for e in filtered_events if e.user_id == user_id]

        if client_ip:
            filtered_events = [e for e in filtered_events if e.client_ip == client_ip]

        return filtered_events

    async def get_audit_summary(
        self, start_time: datetime, end_time: datetime
    ) -> Dict[str, Any]:
        """Get audit summary for a time period."""
        events = await self.get_security_events(
            start_time=start_time, end_time=end_time
        )

        summary = {
            "total_events": len(events),
            "event_types": defaultdict(int),
            "severity_counts": defaultdict(int),
            "top_ips": defaultdict(int),
            "time_period": {
                "start": start_time.isoformat(),
                "end": end_time.isoformat(),
            },
        }

        for event in events:
            summary["event_types"][event.event_type] += 1
            summary["severity_counts"][event.severity] += 1
            if event.client_ip:
                summary["top_ips"][event.client_ip] += 1

        return summary


class ComplianceReporter:
    """Generates compliance reports for various frameworks."""

    def __init__(self, storage=None):
        self.storage = storage
        self.auditor = SecurityAuditor(storage)

    async def generate_gdpr_report(
        self, start_date: datetime, end_date: datetime
    ) -> ComplianceReport:
        """Generate GDPR compliance report."""
        # Get relevant security events
        events = await self.auditor.get_security_events(
            start_time=start_date, end_time=end_date
        )

        # Calculate GDPR-specific metrics
        data_access_events = [e for e in events if e.event_type == "data_access"]
        data_breach_events = [e for e in events if e.event_type == "data_breach"]
        consent_events = [e for e in events if e.event_type == "consent_management"]

        metrics = {
            "data_access_requests": len(data_access_events),
            "data_breach_incidents": len(data_breach_events),
            "consent_updates": len(consent_events),
            "user_data_exports": len([e for e in events if e.action == "data_export"]),
            "user_data_deletions": len(
                [e for e in events if e.action == "data_deletion"]
            ),
            "privacy_violations": len([e for e in events if e.severity == "CRITICAL"]),
        }

        # Calculate compliance score (simplified)
        total_requests = metrics["data_access_requests"]
        violations = metrics["privacy_violations"]
        compliance_score = max(0.0, 1.0 - (violations / max(total_requests, 1)))

        recommendations = []
        if violations > 0:
            recommendations.append("Review and address privacy violations")
        if metrics["data_breach_incidents"] > 0:
            recommendations.append("Implement additional data protection measures")

        return ComplianceReport(
            compliance_framework="GDPR",
            report_period_start=start_date,
            report_period_end=end_date,
            metrics=metrics,
            compliance_score=compliance_score,
            recommendations=recommendations,
        )

    async def generate_sox_report(
        self, start_date: datetime, end_date: datetime
    ) -> ComplianceReport:
        """Generate SOX compliance report."""
        events = await self.auditor.get_security_events(
            start_time=start_date, end_time=end_date
        )

        # SOX-specific metrics
        admin_events = [e for e in events if e.event_type == "admin_action"]
        financial_access = [e for e in events if "financial" in str(e.details)]

        metrics = {
            "admin_actions": len(admin_events),
            "financial_data_access": len(financial_access),
            "unauthorized_access_attempts": len(
                [e for e in events if e.action == "unauthorized_access"]
            ),
            "audit_trail_completeness": 1.0,  # Simplified calculation
        }

        compliance_score = 0.95  # Simplified calculation

        return ComplianceReport(
            compliance_framework="SOX",
            report_period_start=start_date,
            report_period_end=end_date,
            metrics=metrics,
            compliance_score=compliance_score,
            recommendations=["Maintain comprehensive audit trails"],
        )
