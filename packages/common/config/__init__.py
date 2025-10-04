"""
Shared configuration classes for DesignSynapse services.

This module provides unified configuration management using Pydantic Settings v2
with proper environment variable validation and clear error messages.
"""

from .base import BaseServiceConfig, Environment
from .database import DatabaseConfig
from .llm import LLMConfig, LLMProvider
from .vector import VectorConfig, VectorProvider, VectorMetric

__all__ = [
    "BaseServiceConfig",
    "Environment", 
    "DatabaseConfig",
    "LLMConfig",
    "LLMProvider",
    "VectorConfig",
    "VectorProvider",
    "VectorMetric",
]