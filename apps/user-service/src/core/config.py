"""Configuration settings management for the application.

This module handles application-wide settings including:
- Environment variables loading
- Security configuration (JWT settings)
- Token expiration times
- Other application-specific settings

User Service Configuration.

This module provides configuration management for the User Service using
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

from common.config import BaseServiceConfig, DatabaseConfig, Environment


class JWTSettings(BaseSettings):
    """JWT-specific configuration settings."""
    
    model_config = SettingsConfigDict(
        env_prefix="JWT_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False
    )
    
    # JWT Configuration
    secret_key: str = Field(..., min_length=32)
    algorithm: str = Field(default="HS256")
    access_token_expire_minutes: int = Field(default=30, ge=1, le=1440)  # Max 24 hours
    refresh_token_expire_days: int = Field(default=7, ge=1, le=30)  # Max 30 days
    
    # Token settings
    issuer: str = Field(default="designsynapse-user-service")
    audience: str = Field(default="designsynapse-users")
    
    @field_validator("algorithm")
    @classmethod
    def validate_algorithm(cls, v: str) -> str:
        """Validate JWT algorithm."""
        allowed_algorithms = ["HS256", "HS384", "HS512", "RS256", "RS384", "RS512"]
        if v not in allowed_algorithms:
            raise ValueError(f"algorithm must be one of: {', '.join(allowed_algorithms)}")
        return v
    
    @field_validator("secret_key")
    @classmethod
    def validate_secret_key(cls, v: str) -> str:
        """Validate secret key strength."""
        if len(v) < 32:
            raise ValueError("secret_key must be at least 32 characters long")
        return v


class UserServiceSettings:
    """User Service configuration settings."""
    
    def __init__(self):
        # Initialize shared configurations
        self.base = BaseServiceConfig(
            service_name="user-service",
            service_version="1.0.0",
            port=8001
        )
        self.database = DatabaseConfig()
        self.jwt = JWTSettings()
        
        # User service specific settings
        self.max_login_attempts: int = int(os.getenv("MAX_LOGIN_ATTEMPTS", "5"))
        self.account_lockout_minutes: int = int(os.getenv("ACCOUNT_LOCKOUT_MINUTES", "15"))
        self.password_min_length: int = int(os.getenv("PASSWORD_MIN_LENGTH", "8"))
        self.require_email_verification: bool = os.getenv("REQUIRE_EMAIL_VERIFICATION", "true").lower() == "true"
        
        # Email settings (if email verification is enabled)
        self.smtp_host: Optional[str] = os.getenv("SMTP_HOST")
        self.smtp_port: int = int(os.getenv("SMTP_PORT", "587"))
        self.smtp_username: Optional[str] = os.getenv("SMTP_USERNAME")
        self.smtp_password: Optional[str] = os.getenv("SMTP_PASSWORD")
        self.smtp_use_tls: bool = os.getenv("SMTP_USE_TLS", "true").lower() == "true"
        
        # Rate limiting settings
        self.rate_limit_requests_per_minute: int = int(os.getenv("RATE_LIMIT_REQUESTS_PER_MINUTE", "60"))
        self.rate_limit_burst: int = int(os.getenv("RATE_LIMIT_BURST", "10"))
        
        # Validate configuration
        self._validate_user_service_config()
    
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
    
    def _validate_user_service_config(self) -> None:
        """Validate user service specific configuration."""
        # Validate base configuration
        self.base.validate_required_settings()
        
        # Validate database configuration
        self.database.validate_connection_settings()
        
        # Validate user service specific settings
        if self.max_login_attempts <= 0:
            raise ValueError("MAX_LOGIN_ATTEMPTS must be positive")
        
        if self.account_lockout_minutes <= 0:
            raise ValueError("ACCOUNT_LOCKOUT_MINUTES must be positive")
        
        if self.password_min_length < 6:
            raise ValueError("PASSWORD_MIN_LENGTH must be at least 6")
        
        # Validate email settings if email verification is required
        if self.require_email_verification:
            if not self.smtp_host:
                raise ValueError("SMTP_HOST is required when email verification is enabled")
            if not self.smtp_username:
                raise ValueError("SMTP_USERNAME is required when email verification is enabled")
            if not self.smtp_password:
                raise ValueError("SMTP_PASSWORD is required when email verification is enabled")
        
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
        """Get JWT configuration for token creation."""
        return {
            "secret_key": self.jwt.secret_key,
            "algorithm": self.jwt.algorithm,
            "access_token_expire_minutes": self.jwt.access_token_expire_minutes,
            "refresh_token_expire_days": self.jwt.refresh_token_expire_days,
            "issuer": self.jwt.issuer,
            "audience": self.jwt.audience,
        }
    
    def get_email_config(self) -> dict:
        """Get email configuration."""
        return {
            "smtp_host": self.smtp_host,
            "smtp_port": self.smtp_port,
            "smtp_username": self.smtp_username,
            "smtp_password": self.smtp_password,
            "smtp_use_tls": self.smtp_use_tls,
        }
    
    def get_security_config(self) -> dict:
        """Get security configuration."""
        return {
            "max_login_attempts": self.max_login_attempts,
            "account_lockout_minutes": self.account_lockout_minutes,
            "password_min_length": self.password_min_length,
            "require_email_verification": self.require_email_verification,
        }
    
    def get_rate_limit_config(self) -> dict:
        """Get rate limiting configuration."""
        return {
            "requests_per_minute": self.rate_limit_requests_per_minute,
            "burst": self.rate_limit_burst,
        }


# Global settings instance
settings = UserServiceSettings()


# Legacy compatibility - maintain the old interface for existing code
class Settings:
    """Legacy settings class for backward compatibility."""
    
    def __init__(self):
        self._settings = settings
    
    @property
    def SECRET_KEY(self) -> str:
        return self._settings.jwt.secret_key
    
    @property
    def ALGORITHM(self) -> str:
        return self._settings.jwt.algorithm
    
    @property
    def ACCESS_TOKEN_EXPIRE_MINUTES(self) -> int:
        return self._settings.jwt.access_token_expire_minutes
    
    @property
    def REFRESH_TOKEN_EXPIRE_DAYS(self) -> int:
        return self._settings.jwt.refresh_token_expire_days


# Legacy settings instance for backward compatibility
legacy_settings = Settings()
