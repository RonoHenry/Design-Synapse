"""Configuration settings for API Gateway."""

import os
from typing import List, Optional

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """API Gateway configuration settings."""

    # Application settings
    app_name: str = "DesignSynapse API Gateway"
    debug: bool = Field(default=False, description="Enable debug mode")
    host: str = Field(default="0.0.0.0", description="Host to bind to")
    port: int = Field(default=8000, description="Port to bind to")

    # CORS settings
    allowed_origins: List[str] = Field(
        default=["*"], description="Allowed CORS origins"
    )

    # Service Registry settings
    service_registry_url: str = Field(
        default="http://localhost:8001", description="Service registry URL"
    )

    # Authentication settings
    jwt_secret_key: str = Field(
        default="your-secret-key-change-in-production", description="JWT secret key"
    )
    jwt_algorithm: str = Field(default="HS256", description="JWT algorithm")
    jwt_expiration_hours: int = Field(default=24, description="JWT expiration in hours")

    # Rate limiting settings
    rate_limit_requests: int = Field(default=100, description="Requests per minute")
    rate_limit_window: int = Field(
        default=60, description="Rate limit window in seconds"
    )

    # Circuit breaker settings
    circuit_breaker_failure_threshold: int = Field(
        default=5, description="Circuit breaker failure threshold"
    )
    circuit_breaker_recovery_timeout: int = Field(
        default=60, description="Circuit breaker recovery timeout in seconds"
    )

    # Redis settings for caching and rate limiting
    redis_url: str = Field(
        default="redis://localhost:6379", description="Redis connection URL"
    )

    # Monitoring settings
    enable_metrics: bool = Field(default=True, description="Enable metrics collection")
    enable_tracing: bool = Field(default=True, description="Enable distributed tracing")

    class Config:
        env_file = ".env"
        env_prefix = "GATEWAY_"


# Global settings instance
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """Get application settings singleton."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
