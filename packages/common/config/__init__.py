"""
Shared configuration classes for DesignSynapse services.

This module provides unified configuration management using Pydantic Settings v2
with proper environment variable validation and clear error messages.
"""

from .base import BaseServiceConfig, Environment
from .database import DatabaseConfig
from .llm import LLMConfig, LLMProvider
from .storage import StorageConfig
from .vector import VectorConfig, VectorMetric, VectorProvider

# New production configuration system
from .loader import ConfigLoader, ConfigValidationError
from .models import ConfigSchema, DatabaseConfig as NewDatabaseConfig, RedisConfig, APIConfig
from .secrets import SecretsManager, SecretNotFoundError, MaskedSecret
from .providers import EnvironmentSecretsProvider, FileSecretsProvider
from .security import SecurityConfig, SSLConfig, SecurityHeadersConfig
from .middleware import SecurityHeadersMiddleware

__all__ = [
    # Legacy configs
    "BaseServiceConfig",
    "Environment",
    "DatabaseConfig",
    "LLMConfig",
    "LLMProvider",
    "StorageConfig",
    "VectorConfig",
    "VectorProvider",
    "VectorMetric",
    
    # New production configuration system
    "ConfigLoader",
    "ConfigValidationError",
    "ConfigSchema",
    "NewDatabaseConfig",
    "RedisConfig",
    "APIConfig",
    
    # Secrets management
    "SecretsManager",
    "SecretNotFoundError",
    "MaskedSecret",
    "EnvironmentSecretsProvider",
    "FileSecretsProvider",
    
    # Security configuration
    "SecurityConfig",
    "SSLConfig",
    "SecurityHeadersConfig",
    "SecurityHeadersMiddleware",
]
