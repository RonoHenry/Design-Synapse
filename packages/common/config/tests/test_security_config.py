"""Tests for security configuration using TDD approach."""

from pathlib import Path

import pytest

from packages.common.config.middleware import SecurityHeadersMiddleware
# These imports will fail initially - implementing with TDD
from packages.common.config.security import (SecurityConfig,
                                             SecurityHeadersConfig, SSLConfig)


class TestSecurityConfig:
    """Test security configuration functionality."""

    def test_ssl_config_can_be_created(self):
        """Test that SSL configuration can be created."""
        ssl_config = SSLConfig(
            enabled=True, cert_file="/path/to/cert.pem", key_file="/path/to/key.pem"
        )

        assert ssl_config.enabled is True
        assert ssl_config.cert_file == "/path/to/cert.pem"
        assert ssl_config.key_file == "/path/to/key.pem"

    def test_ssl_config_validation_requires_files_when_enabled(self):
        """Test that SSL config validation requires cert and key files when enabled."""
        with pytest.raises(ValueError) as exc_info:
            SSLConfig(enabled=True, cert_file=None, key_file="/path/to/key.pem")

        assert "cert_file" in str(exc_info.value)

        with pytest.raises(ValueError) as exc_info:
            SSLConfig(enabled=True, cert_file="/path/to/cert.pem", key_file=None)

        assert "key_file" in str(exc_info.value)

    def test_ssl_config_allows_none_files_when_disabled(self):
        """Test that SSL config allows None files when disabled."""
        ssl_config = SSLConfig(enabled=False, cert_file=None, key_file=None)

        assert ssl_config.enabled is False
        assert ssl_config.cert_file is None
        assert ssl_config.key_file is None

    def test_security_headers_config_has_default_values(self):
        """Test that security headers config has sensible defaults."""
        headers_config = SecurityHeadersConfig()

        assert headers_config.hsts_enabled is True
        assert headers_config.hsts_max_age == 31536000  # 1 year
        assert headers_config.content_security_policy is not None
        assert headers_config.x_frame_options == "DENY"
        assert headers_config.x_content_type_options == "nosniff"

    def test_security_headers_config_can_be_customized(self):
        """Test that security headers can be customized."""
        custom_csp = "default-src 'self'; script-src 'self' 'unsafe-inline'"

        headers_config = SecurityHeadersConfig(
            hsts_enabled=False,
            content_security_policy=custom_csp,
            x_frame_options="SAMEORIGIN",
        )

        assert headers_config.hsts_enabled is False
        assert headers_config.content_security_policy == custom_csp
        assert headers_config.x_frame_options == "SAMEORIGIN"

    def test_security_config_combines_ssl_and_headers(self):
        """Test that SecurityConfig combines SSL and headers configuration."""
        ssl_config = SSLConfig(enabled=True, cert_file="/cert.pem", key_file="/key.pem")
        headers_config = SecurityHeadersConfig(hsts_enabled=True)

        security_config = SecurityConfig(ssl=ssl_config, headers=headers_config)

        assert security_config.ssl.enabled is True
        assert security_config.headers.hsts_enabled is True

    def test_security_config_can_load_from_dict(self):
        """Test that SecurityConfig can be loaded from dictionary."""
        config_data = {
            "ssl": {
                "enabled": True,
                "cert_file": "/path/to/cert.pem",
                "key_file": "/path/to/key.pem",
                "ca_file": "/path/to/ca.pem",
            },
            "headers": {
                "hsts_enabled": True,
                "hsts_max_age": 86400,
                "content_security_policy": "default-src 'self'",
                "x_frame_options": "DENY",
            },
        }

        security_config = SecurityConfig(**config_data)

        assert security_config.ssl.enabled is True
        assert security_config.ssl.ca_file == "/path/to/ca.pem"
        assert security_config.headers.hsts_max_age == 86400


class TestSecurityHeadersMiddleware:
    """Test security headers middleware functionality."""

    def test_middleware_can_be_instantiated(self):
        """Test that security headers middleware can be created."""
        config = SecurityHeadersConfig()
        middleware = SecurityHeadersMiddleware(config)

        assert middleware is not None
        assert middleware.config == config

    def test_middleware_adds_hsts_header_when_enabled(self):
        """Test that middleware adds HSTS header when enabled."""
        config = SecurityHeadersConfig(hsts_enabled=True, hsts_max_age=3600)
        middleware = SecurityHeadersMiddleware(config)

        headers = middleware.get_security_headers()

        assert "Strict-Transport-Security" in headers
        assert headers["Strict-Transport-Security"] == "max-age=3600; includeSubDomains"

    def test_middleware_skips_hsts_header_when_disabled(self):
        """Test that middleware skips HSTS header when disabled."""
        config = SecurityHeadersConfig(hsts_enabled=False)
        middleware = SecurityHeadersMiddleware(config)

        headers = middleware.get_security_headers()

        assert "Strict-Transport-Security" not in headers

    def test_middleware_adds_content_security_policy_header(self):
        """Test that middleware adds CSP header."""
        csp = "default-src 'self'; script-src 'self' 'unsafe-inline'"
        config = SecurityHeadersConfig(content_security_policy=csp)
        middleware = SecurityHeadersMiddleware(config)

        headers = middleware.get_security_headers()

        assert "Content-Security-Policy" in headers
        assert headers["Content-Security-Policy"] == csp

    def test_middleware_adds_x_frame_options_header(self):
        """Test that middleware adds X-Frame-Options header."""
        config = SecurityHeadersConfig(x_frame_options="SAMEORIGIN")
        middleware = SecurityHeadersMiddleware(config)

        headers = middleware.get_security_headers()

        assert "X-Frame-Options" in headers
        assert headers["X-Frame-Options"] == "SAMEORIGIN"

    def test_middleware_adds_x_content_type_options_header(self):
        """Test that middleware adds X-Content-Type-Options header."""
        config = SecurityHeadersConfig(x_content_type_options="nosniff")
        middleware = SecurityHeadersMiddleware(config)

        headers = middleware.get_security_headers()

        assert "X-Content-Type-Options" in headers
        assert headers["X-Content-Type-Options"] == "nosniff"

    def test_middleware_adds_referrer_policy_header(self):
        """Test that middleware adds Referrer-Policy header."""
        config = SecurityHeadersConfig(
            referrer_policy="strict-origin-when-cross-origin"
        )
        middleware = SecurityHeadersMiddleware(config)

        headers = middleware.get_security_headers()

        assert "Referrer-Policy" in headers
        assert headers["Referrer-Policy"] == "strict-origin-when-cross-origin"

    def test_middleware_can_be_integrated_with_fastapi(self):
        """Test that middleware can be integrated with FastAPI."""
        from fastapi import FastAPI
        from starlette.testclient import TestClient

        app = FastAPI()
        config = SecurityHeadersConfig()

        @app.middleware("http")
        async def add_security_headers(request, call_next):
            response = await call_next(request)
            middleware = SecurityHeadersMiddleware(config)
            headers = middleware.get_security_headers()

            for name, value in headers.items():
                response.headers[name] = value

            return response

        @app.get("/test")
        def test_endpoint():
            return {"message": "test"}

        client = TestClient(app)
        response = client.get("/test")

        assert response.status_code == 200
        assert "X-Frame-Options" in response.headers
        assert "X-Content-Type-Options" in response.headers
