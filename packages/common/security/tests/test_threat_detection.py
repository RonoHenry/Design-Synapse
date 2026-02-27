"""Tests for threat detection and IP blocking - RED phase (failing tests)."""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, Mock

import pytest

from packages.common.security.models import (BlockingRule, ThreatEvent,
                                             ThreatLevel)
from packages.common.security.threat_detection import IPBlocker, ThreatDetector


class TestThreatDetector:
    """Test automated threat detection functionality."""

    @pytest.mark.asyncio
    async def test_brute_force_detection(self, suspicious_patterns, mock_redis):
        """Test detection of brute force attacks."""
        detector = ThreatDetector(storage=mock_redis)

        client_ip = "192.168.1.100"

        # Simulate multiple failed login attempts
        for i in range(suspicious_patterns["brute_force"]["failed_attempts"]):
            event = ThreatEvent(
                client_ip=client_ip,
                event_type="failed_login",
                timestamp=datetime.utcnow(),
                user_agent="Mozilla/5.0",
                endpoint="/api/v1/auth/login",
            )

            result = await detector.analyze_event(event)

            if i >= 4:  # After 5 failed attempts
                assert result.is_threat
                assert result.threat_level == ThreatLevel.HIGH
                assert "brute_force" in result.threat_types

    @pytest.mark.asyncio
    async def test_rate_abuse_detection(self, suspicious_patterns, mock_redis):
        """Test detection of rate abuse/DDoS attempts."""
        detector = ThreatDetector(storage=mock_redis)

        client_ip = "192.168.1.101"

        # Simulate rapid requests
        for i in range(suspicious_patterns["rate_abuse"]["requests_per_minute"]):
            event = ThreatEvent(
                client_ip=client_ip,
                event_type="api_request",
                timestamp=datetime.utcnow(),
                user_agent="Mozilla/5.0",
                endpoint="/api/v1/data",
            )

            result = await detector.analyze_event(event)

            if i >= suspicious_patterns["rate_abuse"]["threshold"]:
                assert result.is_threat
                assert result.threat_level == ThreatLevel.HIGH
                assert "rate_abuse" in result.threat_types

    @pytest.mark.asyncio
    async def test_suspicious_user_agent_detection(
        self, suspicious_patterns, mock_redis
    ):
        """Test detection of suspicious user agents."""
        detector = ThreatDetector(storage=mock_redis)

        for user_agent in suspicious_patterns["suspicious_user_agents"]:
            event = ThreatEvent(
                client_ip="192.168.1.102",
                event_type="api_request",
                timestamp=datetime.utcnow(),
                user_agent=user_agent,
                endpoint="/api/v1/data",
            )

            result = await detector.analyze_event(event)
            assert result.is_threat
            assert result.threat_level == ThreatLevel.MEDIUM
            assert "suspicious_user_agent" in result.threat_types

    @pytest.mark.asyncio
    async def test_legitimate_traffic_passes(self, mock_redis):
        """Test that legitimate traffic is not flagged as threats."""
        detector = ThreatDetector(storage=mock_redis)

        # Normal user behavior
        event = ThreatEvent(
            client_ip="192.168.1.200",
            event_type="api_request",
            timestamp=datetime.utcnow(),
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            endpoint="/api/v1/data",
        )

        result = await detector.analyze_event(event)
        assert not result.is_threat
        assert result.threat_level == ThreatLevel.LOW
        assert len(result.threat_types) == 0


class TestIPBlocker:
    """Test IP blocking functionality."""

    @pytest.mark.asyncio
    async def test_temporary_ip_blocking(self, mock_redis):
        """Test temporary IP blocking functionality."""
        blocker = IPBlocker(storage=mock_redis)

        client_ip = "192.168.1.105"

        # Block IP temporarily
        await blocker.block_ip(
            client_ip, duration_minutes=30, reason="brute_force_attack"
        )

        # Check if IP is blocked
        is_blocked = await blocker.is_ip_blocked(client_ip)
        assert is_blocked

        # Get blocking details
        block_info = await blocker.get_block_info(client_ip)
        assert block_info.ip_address == client_ip
        assert block_info.reason == "brute_force_attack"
        assert block_info.expires_at > datetime.utcnow()

    @pytest.mark.asyncio
    async def test_ip_unblocking(self, mock_redis):
        """Test IP unblocking functionality."""
        blocker = IPBlocker(storage=mock_redis)

        client_ip = "192.168.1.107"

        # Block IP
        await blocker.block_ip(client_ip, duration_minutes=30, reason="test")
        assert await blocker.is_ip_blocked(client_ip)

        # Unblock IP
        await blocker.unblock_ip(client_ip)
        assert not await blocker.is_ip_blocked(client_ip)
