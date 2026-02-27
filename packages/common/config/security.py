"""Security configuration models and utilities."""

from typing import Optional

from pydantic import BaseModel, Field, field_validator


class SSLConfig(BaseModel):
    """SSL/TLS configuration model."""

    enabled: bool = Field(False, description="Whether SSL is enabled")
    cert_file: Optional[str] = Field(None, description="Path to SSL certificate file")
    key_file: Optional[str] = Field(None, description="Path to SSL private key file")
    ca_file: Optional[str] = Field(None, description="Path to CA certificate file")
    verify_mode: str = Field("CERT_REQUIRED", description="SSL verification mode")

    @field_validator("cert_file")
    @classmethod
    def validate_cert_file(cls, v, info):
        if info.data.get("enabled") and not v:
            raise ValueError("cert_file is required when SSL is enabled")
        return v

    @field_validator("key_file")
    @classmethod
    def validate_key_file(cls, v, info):
        if info.data.get("enabled") and not v:
            raise ValueError("key_file is required when SSL is enabled")
        return v


class SecurityHeadersConfig(BaseModel):
    """Security headers configuration model."""

    # HSTS (HTTP Strict Transport Security)
    hsts_enabled: bool = Field(True, description="Enable HSTS header")
    hsts_max_age: int = Field(
        31536000, description="HSTS max age in seconds (default: 1 year)"
    )
    hsts_include_subdomains: bool = Field(
        True, description="Include subdomains in HSTS"
    )
    hsts_preload: bool = Field(False, description="Enable HSTS preload")

    # Content Security Policy
    content_security_policy: str = Field(
        "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; font-src 'self' data:; connect-src 'self'; frame-ancestors 'none';",
        description="Content Security Policy header value",
    )

    # X-Frame-Options
    x_frame_options: str = Field("DENY", description="X-Frame-Options header value")

    # X-Content-Type-Options
    x_content_type_options: str = Field(
        "nosniff", description="X-Content-Type-Options header value"
    )

    # Referrer Policy
    referrer_policy: str = Field(
        "strict-origin-when-cross-origin", description="Referrer-Policy header value"
    )

    # X-XSS-Protection (deprecated but still used)
    x_xss_protection: str = Field(
        "1; mode=block", description="X-XSS-Protection header value"
    )

    # Permissions Policy (formerly Feature Policy)
    permissions_policy: Optional[str] = Field(
        "geolocation=(), microphone=(), camera=()",
        description="Permissions-Policy header value",
    )


class SecurityConfig(BaseModel):
    """Main security configuration combining SSL and headers."""

    ssl: SSLConfig = Field(
        default_factory=SSLConfig, description="SSL/TLS configuration"
    )
    headers: SecurityHeadersConfig = Field(
        default_factory=SecurityHeadersConfig,
        description="Security headers configuration",
    )
