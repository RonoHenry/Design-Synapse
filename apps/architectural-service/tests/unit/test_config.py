"""Test configuration module."""

import pytest
from src.core.config import Settings


def test_settings_initialization():
    """Test that settings can be initialized."""
    settings = Settings()
    assert settings.app_name == "Architectural Service"
    assert settings.app_version == "0.1.0"
    assert settings.api_v1_prefix == "/api/v1"


def test_settings_database_defaults():
    """Test database configuration defaults."""
    settings = Settings()
    assert settings.database_pool_size == 20
    assert settings.database_max_overflow == 10
    assert settings.database_pool_timeout == 30


def test_settings_pagination_defaults():
    """Test pagination configuration defaults."""
    settings = Settings()
    assert settings.default_page_size == 20
    assert settings.max_page_size == 100


def test_settings_circuit_breaker_defaults():
    """Test circuit breaker configuration defaults."""
    settings = Settings()
    assert settings.circuit_breaker_failure_threshold == 5
    assert settings.circuit_breaker_timeout == 60


def test_settings_retry_defaults():
    """Test retry configuration defaults."""
    settings = Settings()
    assert settings.retry_max_attempts == 3
    assert settings.retry_backoff_factor == 2.0
