"""Security middleware implementation."""

from typing import Dict

from .security import SecurityHeadersConfig


class SecurityHeadersMiddleware:
    """Middleware for adding security headers to HTTP responses."""

    def __init__(self, config: SecurityHeadersConfig):
        """Initialize security headers middleware.

        Args:
            config: Security headers configuration
        """
        self.config = config

    def get_security_headers(self) -> Dict[str, str]:
        """Get dictionary of security headers to add to responses.

        Returns:
            Dictionary of header names and values
        """
        headers = {}

        # HSTS Header
        if self.config.hsts_enabled:
            hsts_value = f"max-age={self.config.hsts_max_age}"
            if self.config.hsts_include_subdomains:
                hsts_value += "; includeSubDomains"
            if self.config.hsts_preload:
                hsts_value += "; preload"
            headers["Strict-Transport-Security"] = hsts_value

        # Content Security Policy
        if self.config.content_security_policy:
            headers["Content-Security-Policy"] = self.config.content_security_policy

        # X-Frame-Options
        if self.config.x_frame_options:
            headers["X-Frame-Options"] = self.config.x_frame_options

        # X-Content-Type-Options
        if self.config.x_content_type_options:
            headers["X-Content-Type-Options"] = self.config.x_content_type_options

        # Referrer Policy
        if self.config.referrer_policy:
            headers["Referrer-Policy"] = self.config.referrer_policy

        # X-XSS-Protection
        if self.config.x_xss_protection:
            headers["X-XSS-Protection"] = self.config.x_xss_protection

        # Permissions Policy
        if self.config.permissions_policy:
            headers["Permissions-Policy"] = self.config.permissions_policy

        return headers
