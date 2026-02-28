"""Unit tests for configuration management."""

import os
from unittest.mock import patch

import pytest
from src.core.config import Settings, settings


@pytest.mark.unit
class TestSettings:
    """Test Settings configuration."""

    def test_settings_loads_defaults(self):
        """Test that settings loads with default values."""
        test_settings = Settings()

        assert test_settings.app_name == "Engineering Service"
        assert test_settings.app_version == "0.1.0"
        assert test_settings.api_v1_prefix == "/api/v1"

    def test_settings_loads_from_environment(self):
        """Test that settings loads from environment variables."""
        with patch.dict(
            os.environ,
            {
                "ENV": "production",
                "DEBUG": "false",
                "DATABASE_URL": "mysql+asyncmy://user:pass@host:3306/db",
            },
        ):
            test_settings = Settings()

            assert test_settings.environment == "production"
            assert test_settings.debug is False
            assert "user:pass@host:3306" in test_settings.database_url

    def test_settings_database_configuration(self):
        """Test database configuration settings."""
        assert settings.database_pool_size == 20
        assert settings.database_max_overflow == 10
        assert settings.database_pool_timeout == 30
        assert settings.database_pool_recycle == 3600

    def test_settings_redis_configuration(self):
        """Test Redis configuration settings."""
        assert settings.redis_cache_ttl == 300
        assert "redis://" in settings.redis_url

    def test_settings_external_services_configuration(self):
        """Test external services configuration."""
        assert settings.architectural_service_url is not None
        assert settings.design_service_url is not None
        assert settings.knowledge_service_url is not None
        assert settings.project_service_url is not None

    def test_settings_circuit_breaker_configuration(self):
        """Test circuit breaker configuration."""
        assert settings.circuit_breaker_failure_threshold == 5
        assert settings.circuit_breaker_timeout == 60
        assert settings.circuit_breaker_half_open_timeout == 30

    def test_settings_retry_configuration(self):
        """Test retry configuration."""
        assert settings.retry_max_attempts == 3
        assert settings.retry_backoff_factor == 2.0
        assert settings.retry_max_delay == 60

    def test_settings_jwt_configuration(self):
        """Test JWT configuration."""
        assert settings.jwt_algorithm == "HS256"
        assert settings.jwt_access_token_expire_minutes > 0
        assert settings.jwt_secret_key is not None

    def test_settings_cors_configuration(self):
        """Test CORS configuration."""
        assert isinstance(settings.cors_origins, list)
        assert settings.cors_allow_credentials is True
        assert isinstance(settings.cors_allow_methods, list)
        assert isinstance(settings.cors_allow_headers, list)

    def test_settings_pagination_configuration(self):
        """Test pagination configuration."""
        assert settings.default_page_size == 20
        assert settings.max_page_size == 100

    def test_settings_calculation_configuration(self):
        """Test calculation settings."""
        assert settings.calculation_timeout == 30
        assert settings.max_calculation_retries == 2

    def test_global_settings_instance_exists(self):
        """Test that global settings instance exists."""
        assert settings is not None
        assert isinstance(settings, Settings)

    def test_settings_can_be_instantiated_multiple_times(self):
        """Test that Settings can be instantiated multiple times."""
        settings1 = Settings()
        settings2 = Settings()

        # They should have the same values but be different instances
        assert settings1.app_name == settings2.app_name
        assert settings1 is not settings2
