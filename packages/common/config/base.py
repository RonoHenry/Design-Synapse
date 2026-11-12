"""
Base configuration classes for DesignSynapse services.
"""

from enum import Enum
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Environment(str, Enum):
    """Application environment types."""
    DEVELOPMENT = "development"
    TESTING = "testing"
    PRODUCTION = "production"


class BaseServiceConfig(BaseSettings):
    """Base configuration class for all services."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    # Core service settings
    environment: Environment = Environment.DEVELOPMENT
    debug: bool = False
    service_name: str = "unknown"
    service_version: str = "1.0.0"
    
    # API settings
    host: str = "0.0.0.0"
    port: int = 8000
    
    # Logging settings
    log_level: str = "INFO"
    log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    # Security settings
    secret_key: Optional[str] = None
    
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.environment == Environment.DEVELOPMENT
    
    def is_testing(self) -> bool:
        """Check if running in testing environment."""
        return self.environment == Environment.TESTING
    
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.environment == Environment.PRODUCTION
    
    def validate_required_settings(self) -> None:
        """Validate that required settings are present."""
        if self.is_production() and not self.secret_key:
            raise ValueError(
                "SECRET_KEY environment variable is required in production"
            )