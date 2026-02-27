"""
Shared configuration classes for DesignSynapse services.

This module provides unified configuration management using Pydantic Settings v2
with proper environment variable validation and clear error messages.
"""

from .base import BaseServiceConfig, Environment
from .database import DatabaseConfig
from .llm import LLMConfig, LLMProvider
# New production configuration system
from .loader import ConfigLoader, ConfigValidationError
from .middleware import SecurityHeadersMiddleware
from .models import APIConfig, ConfigSchema
from .models import DatabaseConfig as NewDatabaseConfig
from .models import RedisConfig
from .providers import EnvironmentSecretsProvider, FileSecretsProvider
from .secrets import MaskedSecret, SecretNotFoundError, SecretsManager
from .security import SecurityConfig, SecurityHeadersConfig, SSLConfig
from .storage import StorageConfig
from .vector import VectorConfig, VectorMetric, VectorProvider

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
