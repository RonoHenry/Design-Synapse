"""Security hardening middleware for FastAPI applications."""

import asyncio
import time
from datetime import datetime
from typing import Callable, Dict, List, Optional, Set

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from .audit_logging import SecurityAuditor
from .input_validation import InputSanitizer, InputValidator
from .models import SecurityEvent, ThreatEvent, ValidationResult
from .threat_detection import IPBlocker, ThreatDetector


class SecurityHardeningMiddleware(BaseHTTPMiddleware):
    """Comprehensive security hardening middleware."""

    def __init__(
        self,
        app: ASGIApp,
        enable_input_validation: bool = True,
        enable_threat_detection: bool = True,
        enable_audit_logging: bool = True,
        enable_ip_blocking: bool = True,
        blocked_ips: Optional[List[str]] = None,
        whitelist_paths: Optional[List[str]] = None,
        rate_limit_requests: int = 100,
        rate_limit_window: int = 60,
        storage=None,
    ):
        super().__init__(app)

        # Configuration
        self.enable_input_validation = enable_input_validation
        self.enable_threat_detection = enable_threat_detection
        self.enable_audit_logging = enable_audit_logging
        self.enable_ip_blocking = enable_ip_blocking

        # IP management
        self.blocked_ips = set(blocked_ips or [])
        self.whitelist_paths = set(whitelist_paths or [])

        # Rate limiting
        self.rate_limit_requests = rate_limit_requests
        self.rate_limit_window = rate_limit_window
        self.request_counts = {}

        # Security components
        self.input_validator = InputValidator() if enable_input_validation else None
        self.input_sanitizer = InputSanitizer() if enable_input_validation else None
        self.threat_detector = (
            ThreatDetector(storage) if enable_threat_detection else None
        )
        self.ip_blocker = IPBlocker(storage) if enable_ip_blocking else None
        self.auditor = SecurityAuditor(storage) if enable_audit_logging else None

        # Security headers
        self.security_headers = {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
            "Content-Security-Policy": "default-src 'self'",
            "Referrer-Policy": "strict-origin-when-cross-origin",
        }

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Main middleware dispatch method."""
        start_time = time.time()

        try:
            # Get client IP
            client_ip = self._get_client_ip(request)

            # Check if path is whitelisted
            if self._is_whitelisted_path(request.url.path):
                response = await call_next(request)
                self._add_security_headers(response)
                return response

            # Check IP blocking
            if self.enable_ip_blocking and await self._is_ip_blocked(client_ip):
                return self._create_error_response(
                    403, "ip_blocked", "Access denied from this IP address"
                )

            # Rate limiting
            if not await self._check_rate_limit(client_ip):
                return self._create_error_response(
                    429, "rate_limit_exceeded", "Too many requests"
                )

            # Input validation
            if self.enable_input_validation:
                validation_result = await self._validate_request(request)
                if (
                    not validation_result.is_valid
                    and validation_result.risk_level == "HIGH"
                ):
                    await self._log_security_event(
                        "input_validation",
                        "validation_failed",
                        client_ip,
                        request,
                        {"threats": validation_result.threats_detected},
                    )
                    return self._create_error_response(
                        400,
                        "input_validation_failed",
                        f"Invalid input detected: {', '.join(validation_result.threats_detected)}",
                    )

            # Threat detection
            if self.enable_threat_detection:
                threat_result = await self._detect_threats(request, client_ip)
                if threat_result and threat_result.is_threat:
                    await self._handle_threat(threat_result, client_ip, request)
                    return self._create_error_response(
                        429,
                        "threat_detected",
                        f"Suspicious activity detected: {', '.join(threat_result.threat_types)}",
                    )

            # Process request
            response = await call_next(request)

            # Add security headers
            self._add_security_headers(response)

            # Add rate limit headers
            self._add_rate_limit_headers(response, client_ip)

            # Log successful request
            await self._log_security_event(
                "request",
                "api_request",
                client_ip,
                request,
                {
                    "status_code": response.status_code,
                    "processing_time": time.time() - start_time,
                },
            )

            return response

        except Exception as e:
            # Log error and return graceful response
            await self._log_security_event(
                "error",
                "middleware_error",
                self._get_client_ip(request),
                request,
                {"error": str(e)},
            )

            # Graceful degradation - continue with request
            try:
                response = await call_next(request)
                self._add_security_headers(response)
                return response
            except Exception:
                return self._create_error_response(
                    500, "internal_error", "Internal server error"
                )

    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP from request."""
        # Check for forwarded headers first
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()

        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip

        # Fallback to client host
        if hasattr(request, "client") and request.client:
            return request.client.host

        return "unknown"

    def _is_whitelisted_path(self, path: str) -> bool:
        """Check if path is whitelisted."""
        return any(path.startswith(whitelist) for whitelist in self.whitelist_paths)

    async def _is_ip_blocked(self, client_ip: str) -> bool:
        """Check if IP is blocked."""
        if client_ip in self.blocked_ips:
            return True

        if self.ip_blocker:
            return await self.ip_blocker.is_ip_blocked(client_ip)

        return False

    async def _check_rate_limit(self, client_ip: str) -> bool:
        """Check rate limiting for client IP."""
        current_time = time.time()
        window_start = current_time - self.rate_limit_window

        # Clean old entries
        if client_ip in self.request_counts:
            self.request_counts[client_ip] = [
                timestamp
                for timestamp in self.request_counts[client_ip]
                if timestamp > window_start
            ]
        else:
            self.request_counts[client_ip] = []

        # Check if under limit
        if len(self.request_counts[client_ip]) >= self.rate_limit_requests:
            return False

        # Add current request
        self.request_counts[client_ip].append(current_time)
        return True

    async def _validate_request(self, request: Request) -> ValidationResult:
        """Validate request input."""
        if not self.input_validator:
            return ValidationResult(
                is_valid=True, threats_detected=[], risk_level="LOW"
            )

        try:
            return await self.input_validator.validate_request(request)
        except Exception:
            # Graceful degradation
            return ValidationResult(
                is_valid=True, threats_detected=[], risk_level="LOW"
            )

    async def _detect_threats(self, request: Request, client_ip: str):
        """Detect security threats."""
        if not self.threat_detector:
            return None

        try:
            # Create threat event - determine event type based on endpoint and method
            event_type = "api_request"
            if "auth" in str(request.url.path) and request.method == "POST":
                event_type = (
                    "failed_login"  # Assume auth POST requests are login attempts
                )

            threat_event = ThreatEvent(
                client_ip=client_ip,
                event_type=event_type,
                timestamp=datetime.utcnow(),
                user_agent=request.headers.get("User-Agent", ""),
                endpoint=str(request.url.path),
            )

            return await self.threat_detector.analyze_event(threat_event)
        except Exception:
            # Graceful degradation
            return None

    async def _handle_threat(self, threat_result, client_ip: str, request: Request):
        """Handle detected threat."""
        # Log threat
        await self._log_security_event(
            "threat_detection",
            "threat_detected",
            client_ip,
            request,
            {
                "threat_types": threat_result.threat_types,
                "threat_score": threat_result.threat_score,
                "recommended_action": threat_result.recommended_action,
            },
        )

        # Take action based on recommendation
        if threat_result.recommended_action == "block_ip_temporary" and self.ip_blocker:
            await self.ip_blocker.block_ip(
                client_ip, duration_minutes=60, reason="automated_threat_detection"
            )
        elif (
            threat_result.recommended_action == "block_ip_permanent" and self.ip_blocker
        ):
            await self.ip_blocker.block_ip(
                client_ip, is_permanent=True, reason="high_threat_score"
            )

    async def _log_security_event(
        self,
        event_type: str,
        action: str,
        client_ip: str,
        request: Request,
        details: Optional[Dict] = None,
    ):
        """Log security event."""
        if not self.auditor:
            return

        try:
            event = SecurityEvent(
                event_type=event_type,
                action=action,
                timestamp=datetime.utcnow(),
                client_ip=client_ip,
                details={
                    "endpoint": str(request.url.path),
                    "method": request.method,
                    "user_agent": request.headers.get("User-Agent", ""),
                    **(details or {}),
                },
            )

            await self.auditor.log_security_event(event)
        except Exception:
            # Don't let logging errors break the request
            pass

    def _add_security_headers(self, response: Response):
        """Add security headers to response."""
        for header, value in self.security_headers.items():
            response.headers[header] = value

    def _add_rate_limit_headers(self, response: Response, client_ip: str):
        """Add rate limiting headers."""
        if client_ip in self.request_counts:
            remaining = max(
                0, self.rate_limit_requests - len(self.request_counts[client_ip])
            )
            response.headers["X-RateLimit-Limit"] = str(self.rate_limit_requests)
            response.headers["X-RateLimit-Remaining"] = str(remaining)
            response.headers["X-RateLimit-Reset"] = str(
                int(time.time() + self.rate_limit_window)
            )

    def _create_error_response(
        self, status_code: int, error_code: str, message: str
    ) -> JSONResponse:
        """Create standardized error response."""
        return JSONResponse(
            status_code=status_code,
            content={
                "error_code": error_code,
                "message": message,
                "timestamp": datetime.utcnow().isoformat(),
            },
        )
