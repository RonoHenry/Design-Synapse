"""Threat detection and IP blocking for automated security."""

import asyncio
import json
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from .models import (BlockInfo, BlockingRule, ThreatAnalysisResult,
                     ThreatEvent, ThreatLevel)


class ThreatDetector:
    """Detects security threats based on behavioral patterns."""

    def __init__(self, storage=None):
        self.storage = storage  # Redis or similar storage

        # Threat detection thresholds
        self.brute_force_threshold = 5
        self.brute_force_window = 300  # 5 minutes
        self.rate_abuse_threshold = 100
        self.rate_abuse_window = 60  # 1 minute

        # Suspicious patterns
        self.suspicious_user_agents = [
            "sqlmap",
            "nikto",
            "nmap",
            "burp",
            "w3af",
            "dirb",
            "dirbuster",
            "gobuster",
            "wfuzz",
            "hydra",
            "medusa",
            "nessus",
            "openvas",
        ]

        # In-memory tracking for demo (use Redis in production)
        self.event_history = defaultdict(list)
        self.ip_stats = defaultdict(
            lambda: {"requests": 0, "last_reset": datetime.utcnow()}
        )

    async def analyze_event(self, event: ThreatEvent) -> ThreatAnalysisResult:
        """Analyze a security event for threats."""
        threat_types = []
        threat_score = 0
        threat_level = ThreatLevel.LOW

        # Check for brute force attacks
        if await self._is_brute_force_attack(event):
            threat_types.append("brute_force")
            threat_score += 40
            threat_level = ThreatLevel.HIGH

        # Check for rate abuse
        if await self._is_rate_abuse(event):
            threat_types.append("rate_abuse")
            threat_score += 35
            threat_level = ThreatLevel.HIGH

        # Check for suspicious user agents
        if self._is_suspicious_user_agent(event.user_agent):
            threat_types.append("suspicious_user_agent")
            threat_score += 25
            threat_level = ThreatLevel.MEDIUM

        # Check for suspicious patterns in endpoint
        if self._is_suspicious_endpoint_access(event.endpoint):
            threat_types.append("suspicious_endpoint")
            threat_score += 20
            threat_level = ThreatLevel.MEDIUM

        # Store event for future analysis
        await self._store_event(event)

        is_threat = len(threat_types) > 0
        confidence = min(threat_score / 100.0, 1.0)

        # Determine recommended action
        recommended_action = self._get_recommended_action(threat_score, threat_types)

        return ThreatAnalysisResult(
            is_threat=is_threat,
            threat_level=threat_level,
            threat_types=threat_types,
            threat_score=threat_score,
            confidence=confidence,
            recommended_action=recommended_action,
        )

    async def _is_brute_force_attack(self, event: ThreatEvent) -> bool:
        """Check if event indicates brute force attack."""
        if event.event_type != "failed_login":
            return False

        # Count failed attempts from this IP in the time window (including current event)
        cutoff_time = datetime.utcnow() - timedelta(seconds=self.brute_force_window)

        # Get recent events for this IP
        recent_events = await self._get_recent_events(
            event.client_ip, "failed_login", cutoff_time
        )

        # Include the current event in the count
        return len(recent_events) + 1 >= self.brute_force_threshold

    async def _is_rate_abuse(self, event: ThreatEvent) -> bool:
        """Check if event indicates rate abuse/DDoS."""
        # Count requests from this IP in the time window (including current event)
        cutoff_time = datetime.utcnow() - timedelta(seconds=self.rate_abuse_window)

        recent_events = await self._get_recent_events(
            event.client_ip, "api_request", cutoff_time
        )

        # Include the current event in the count
        return len(recent_events) + 1 >= self.rate_abuse_threshold

    def _is_suspicious_user_agent(self, user_agent: str) -> bool:
        """Check if user agent is suspicious."""
        if not user_agent:
            return True  # Empty user agent is suspicious

        user_agent_lower = user_agent.lower()
        return any(
            suspicious in user_agent_lower for suspicious in self.suspicious_user_agents
        )

    def _is_suspicious_endpoint_access(self, endpoint: str) -> bool:
        """Check if endpoint access pattern is suspicious."""
        suspicious_endpoints = [
            "/admin",
            "/.env",
            "/config",
            "/backup",
            "/wp-admin",
            "/phpmyadmin",
            "/mysql",
            "/database",
            "/.git",
        ]

        return any(
            suspicious in endpoint.lower() for suspicious in suspicious_endpoints
        )

    def _get_recommended_action(
        self, threat_score: int, threat_types: List[str]
    ) -> str:
        """Get recommended action based on threat analysis."""
        if threat_score >= 60:
            return "block_ip_permanent"
        elif threat_score >= 40:
            return "block_ip_temporary"
        elif threat_score >= 25:
            return "rate_limit_strict"
        elif threat_score >= 15:
            return "monitor_closely"
        else:
            return "log_only"

    async def _store_event(self, event: ThreatEvent):
        """Store event for analysis."""
        # Always store in memory for analysis (even when using Redis)
        self.event_history[event.client_ip].append(event)

        if self.storage:
            # Also use Redis or database storage for persistence
            event_data = {
                "client_ip": event.client_ip,
                "event_type": event.event_type,
                "timestamp": event.timestamp.isoformat(),
                "user_agent": event.user_agent,
                "endpoint": event.endpoint,
                "user_id": event.user_id,
                "details": event.details,
            }
            await self.storage.set(
                f"security_event:{event.client_ip}:{event.timestamp.timestamp()}",
                json.dumps(event_data),
                ex=3600,  # Expire after 1 hour
            )

    async def _get_recent_events(
        self, client_ip: str, event_type: str, cutoff_time: datetime
    ) -> List[ThreatEvent]:
        """Get recent events for analysis."""
        # Always use in-memory storage for event tracking (even with Redis)
        # In production, this would be replaced with proper Redis queries
        events = self.event_history.get(client_ip, [])
        return [
            event
            for event in events
            if event.event_type == event_type and event.timestamp >= cutoff_time
        ]


class IPBlocker:
    """Manages IP blocking functionality."""

    def __init__(self, storage=None):
        self.storage = storage

        # In-memory storage for testing
        self.blocked_ips = {}
        self.blocking_rules = []

    async def block_ip(
        self,
        ip_address: str,
        duration_minutes: Optional[int] = None,
        reason: str = "security_violation",
        is_permanent: bool = False,
    ) -> bool:
        """Block an IP address."""
        expires_at = None
        if not is_permanent and duration_minutes:
            expires_at = datetime.utcnow() + timedelta(minutes=duration_minutes)

        block_info = BlockInfo(
            ip_address=ip_address,
            reason=reason,
            blocked_at=datetime.utcnow(),
            expires_at=expires_at,
            is_permanent=is_permanent,
            block_count=1,
        )

        if self.storage:
            # Store in Redis (or mock Redis for testing)
            block_data = {
                "ip_address": ip_address,
                "reason": reason,
                "blocked_at": block_info.blocked_at.isoformat(),
                "expires_at": expires_at.isoformat() if expires_at else None,
                "is_permanent": is_permanent,
                "block_count": 1,
            }

            key = f"blocked_ip:{ip_address}"
            await self.storage.set(key, json.dumps(block_data))

            if expires_at and not is_permanent:
                # Set expiration
                ttl = int((expires_at - datetime.utcnow()).total_seconds())
                await self.storage.expire(key, ttl)

            # Also store in memory for testing
            self.blocked_ips[ip_address] = block_info
        else:
            # In-memory storage
            self.blocked_ips[ip_address] = block_info

        return True

    async def unblock_ip(self, ip_address: str) -> bool:
        """Unblock an IP address."""
        # Remove from in-memory storage
        removed_from_memory = False
        if ip_address in self.blocked_ips:
            del self.blocked_ips[ip_address]
            removed_from_memory = True

        # Remove from storage if available
        if self.storage:
            key = f"blocked_ip:{ip_address}"
            result = await self.storage.delete(key)
            return result > 0 or removed_from_memory

        return removed_from_memory

    async def is_ip_blocked(self, ip_address: str) -> bool:
        """Check if an IP address is blocked."""
        # Check in-memory storage first (works for both real and mock Redis)
        if ip_address in self.blocked_ips:
            block_info = self.blocked_ips[ip_address]
            # Check if temporary block has expired
            if block_info.expires_at and datetime.utcnow() > block_info.expires_at:
                del self.blocked_ips[ip_address]
                if self.storage:
                    await self.unblock_ip(ip_address)
                return False
            return True

        # If using storage and not found in memory, check storage
        if self.storage:
            key = f"blocked_ip:{ip_address}"
            result = await self.storage.get(key)
            if result:
                try:
                    block_data = json.loads(result)
                    # Check if temporary block has expired
                    if block_data.get("expires_at"):
                        expires_at = datetime.fromisoformat(block_data["expires_at"])
                        if datetime.utcnow() > expires_at:
                            await self.unblock_ip(ip_address)
                            return False
                    return True
                except (json.JSONDecodeError, ValueError):
                    # Invalid data, consider not blocked
                    return False
            return False

        return False

    async def get_block_info(self, ip_address: str) -> Optional[BlockInfo]:
        """Get blocking information for an IP."""
        # Check in-memory storage first
        if ip_address in self.blocked_ips:
            return self.blocked_ips[ip_address]

        # Check storage if available
        if self.storage:
            key = f"blocked_ip:{ip_address}"
            result = await self.storage.get(key)
            if result:
                try:
                    block_data = json.loads(result)
                    return BlockInfo(
                        ip_address=block_data["ip_address"],
                        reason=block_data["reason"],
                        blocked_at=datetime.fromisoformat(block_data["blocked_at"]),
                        expires_at=datetime.fromisoformat(block_data["expires_at"])
                        if block_data.get("expires_at")
                        else None,
                        is_permanent=block_data["is_permanent"],
                        block_count=block_data["block_count"],
                    )
                except (json.JSONDecodeError, ValueError):
                    return None

        return None

    async def add_blocking_rule(self, rule: BlockingRule) -> bool:
        """Add a new blocking rule."""
        if self.storage:
            rule_data = {
                "name": rule.name,
                "condition": rule.condition,
                "action": rule.action,
                "priority": rule.priority,
                "enabled": rule.enabled,
                "created_at": rule.created_at.isoformat()
                if rule.created_at
                else datetime.utcnow().isoformat(),
            }
            key = f"blocking_rule:{rule.name}"
            await self.storage.set(key, json.dumps(rule_data))
        else:
            # In-memory storage
            self.blocking_rules.append(rule)

        return True

    async def get_blocked_ips(self) -> List[BlockInfo]:
        """Get list of all blocked IPs."""
        blocked_ips = []

        if self.storage:
            # In production, scan Redis keys
            # This is a simplified implementation
            pass
        else:
            # In-memory storage
            for ip, block_info in self.blocked_ips.items():
                # Check if temporary blocks have expired
                if block_info.expires_at and datetime.utcnow() > block_info.expires_at:
                    continue
                blocked_ips.append(block_info)

        return blocked_ips
