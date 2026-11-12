"""
Shared testing utilities and infrastructure for DesignSynapse services.

This package provides:
- Base factory classes for consistent test data creation
- Database isolation utilities
- Mock utilities for external services
- Pytest plugins and fixtures
"""

from .base_factory import BaseFactory
from .database import DatabaseTestMixin, create_test_engine, create_test_session
from .mocks import MockLLMService, MockVectorService, MockExternalService
from .fixtures import pytest_plugins

__all__ = [
    "BaseFactory",
    "DatabaseTestMixin", 
    "create_test_engine",
    "create_test_session",
    "MockLLMService",
    "MockVectorService", 
    "MockExternalService",
    "pytest_plugins"
]