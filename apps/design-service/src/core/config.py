"""
Design Service Configuration.

This module provides configuration management for the Design Service using
the unified configuration system with proper environment variable validation.
"""

import os
import sys
from pathlib import Path
from typing import Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Add the packages directory to the Python path for shared config access
packages_path = Path(__file__).parent.parent.parent.parent.parent / "packages"
sys.path.insert(0, str(packages_path))

from common.config import (BaseServiceConfig, DatabaseConfig, Environment,
                           LLMConfig)


class DesignSettings(BaseSettings):
    """Design-specific configuration settings."""

    model_config = SettingsConfigDict(
        env_prefix="DESIGN_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Design generation limits
    max_designs_per_project: int = Field(default=50, ge=1, le=500)
    max_design_iterations: int = Field(default=10, ge=1, le=50)
    max_design_name_length: int = Field(default=255, ge=10, le=500)
    max_design_description_length: int = Field(default=2000, ge=50, le=10000)

    # Design generation settings
    enable_auto_generation: bool = Field(default=True)
    generation_timeout_seconds: int = Field(default=120, ge=30, le=600)
    max_concurrent_generations: int = Field(default=3, ge=1, le=10)

    # Design validation
    enable_design_validation: bool = Field(default=True)
    validation_timeout_seconds: int = Field(default=30, ge=5, le=120)


class JWTSettings(BaseSettings):
    """JWT configuration for design service."""

    model_config = SettingsConfigDict(
        env_prefix="JWT_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    secret_key: str = Field(..., min_length=32)
    algorithm: str = Field(default="HS256")
    access_token_expire_minutes: int = Field(default=30, ge=1, le=1440)

    @field_validator("algorithm")
    @classmethod
    def validate_algorithm(cls, v: str) -> str:
        """Validate JWT algorithm."""
        allowed_algorithms = ["HS256", "HS384", "HS512", "RS256", "RS384", "RS512"]
        if v not in allowed_algorithms:
            raise ValueError(
                f"algorithm must be one of: {', '.join(allowed_algorithms)}"
            )
        return v


class DesignServiceConfig:
    """Design Service configuration settings."""

    def __init__(self):
        # Initialize shared configurations
        self.base = BaseServiceConfig(
            service_name="design-service", service_version="1.0.0", port=8004
        )
        self.database = DatabaseConfig()
        self.llm = LLMConfig()
        self.jwt = JWTSettings()
        self.design = DesignSettings()

        # Service URLs for inter-service communication
        self.user_service_url: str = os.getenv(
            "USER_SERVICE_URL", "http://localhost:8001"
        )
        self.project_service_url: str = os.getenv(
            "PROJECT_SERVICE_URL", "http://localhost:8003"
        )
        self.knowledge_service_url: str = os.getenv(
            "KNOWLEDGE_SERVICE_URL", "http://localhost:8002"
        )

        # Rate limiting settings
        self.rate_limit_requests_per_minute: int = int(
            os.getenv("RATE_LIMIT_REQUESTS_PER_MINUTE", "100")
        )
        self.rate_limit_burst: int = int(os.getenv("RATE_LIMIT_BURST", "20"))

        # Validate configuration
        self._validate_design_service_config()

    # Proxy properties for easy access to base configuration
    @property
    def service_name(self) -> str:
        return self.base.service_name

    @property
    def port(self) -> int:
        return self.base.port

    @property
    def environment(self) -> Environment:
        return self.base.environment

    @property
    def debug(self) -> bool:
        return self.base.debug

    @property
    def log_level(self) -> str:
        return self.base.log_level

    def is_development(self) -> bool:
        return self.base.is_development()

    def is_testing(self) -> bool:
        return self.base.is_testing()

    def is_production(self) -> bool:
        return self.base.is_production()

    def _validate_design_service_config(self) -> None:
        """Validate design service specific configuration."""
        # Validate base configuration
        self.base.validate_required_settings()

        # Validate database configuration
        self.database.validate_connection_settings()

        # Validate LLM configuration
        self.llm.validate_configuration()

        # Validate service URLs
        if not self.user_service_url:
            raise ValueError("USER_SERVICE_URL is required")
        if not self.project_service_url:
            raise ValueError("PROJECT_SERVICE_URL is required")
        if not self.knowledge_service_url:
            raise ValueError("KNOWLEDGE_SERVICE_URL is required")

        # Validate rate limiting settings
        if self.rate_limit_requests_per_minute <= 0:
            raise ValueError("RATE_LIMIT_REQUESTS_PER_MINUTE must be positive")
        if self.rate_limit_burst <= 0:
            raise ValueError("RATE_LIMIT_BURST must be positive")

    def get_database_url(self, async_driver: bool = False) -> str:
        """Get database connection URL."""
        return self.database.get_connection_url(async_driver=async_driver)

    def get_database_engine_kwargs(self) -> dict:
        """Get database engine configuration."""
        return self.database.get_engine_kwargs()

    def get_jwt_config(self) -> dict:
        """Get JWT configuration."""
        return {
            "secret_key": self.jwt.secret_key,
            "algorithm": self.jwt.algorithm,
            "access_token_expire_minutes": self.jwt.access_token_expire_minutes,
        }

    def get_llm_config(self) -> dict:
        """Get LLM configuration."""
        return {
            "primary_provider": self.llm.primary_provider,
            "fallback_providers": self.llm.fallback_providers,
            "max_retries": self.llm.max_retries,
            "timeout": self.llm.timeout,
        }

    def get_design_config(self) -> dict:
        """Get design configuration."""
        return {
            "max_designs_per_project": self.design.max_designs_per_project,
            "max_design_iterations": self.design.max_design_iterations,
            "max_design_name_length": self.design.max_design_name_length,
            "max_design_description_length": self.design.max_design_description_length,
            "enable_auto_generation": self.design.enable_auto_generation,
            "generation_timeout_seconds": self.design.generation_timeout_seconds,
            "max_concurrent_generations": self.design.max_concurrent_generations,
            "enable_design_validation": self.design.enable_design_validation,
            "validation_timeout_seconds": self.design.validation_timeout_seconds,
        }

    def get_service_urls(self) -> dict:
        """Get service URLs for inter-service communication."""
        return {
            "user_service": self.user_service_url,
            "project_service": self.project_service_url,
            "knowledge_service": self.knowledge_service_url,
        }

    def get_rate_limit_config(self) -> dict:
        """Get rate limiting configuration."""
        return {
            "requests_per_minute": self.rate_limit_requests_per_minute,
            "burst": self.rate_limit_burst,
        }


# Global settings instance - lazy initialization to avoid issues during testing
_settings = None


def get_settings() -> DesignServiceConfig:
    """Get or create the global settings instance."""
    global _settings
    if _settings is None:
        _settings = DesignServiceConfig()
    return _settings


# For backward compatibility
settings = None
try:
    settings = DesignServiceConfig()
except Exception:
    # Allow import to succeed even if configuration is incomplete
    # This is useful for testing and development
    pass
