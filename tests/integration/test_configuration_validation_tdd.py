"""Configuration Validation Testing (TDD Implementation)

Following strict TDD methodology - these tests define expected behavior
for configuration validation scenarios. All tests will fail initially
and then we implement functionality to make them pass.

Requirements covered:
- 3.4: Configuration validation with clear error messages
- 3.5: Environment variable validation and fallback mechanisms
- 7.3: Consistent error response formats
- 7.5: Proper error handling for configuration failures
"""

import json
import os
import tempfile
from pathlib import Path
from typing import Any, Dict
from unittest.mock import MagicMock, patch

import pytest

# These imports will fail initially - that's the point of TDD!
# We'll implement them after the tests are written
from packages.common.config.loader import ConfigLoader, ConfigValidationError
from packages.common.config.models import (APIConfig, ConfigSchema,
                                           DatabaseConfig, RedisConfig)
from packages.common.config.validators import (ConfigValidator,
                                               EnvironmentValidator,
                                               RangeValidator,
                                               RequiredConfigValidator,
                                               SecretValidator, TypeValidator,
                                               URLValidator, ValidationError,
                                               ValidationResult)


class TestMissingRequiredConfiguration:
    """Test cases for missing required configuration values."""

    def test_missing_database_host_raises_validation_error(self):
        """Test that missing DATABASE_HOST raises clear validation error."""
        # Arrange
        config_data = {
            "database": {
                # "host": "localhost",  # Missing required field
                "port": 5432,
                "name": "test_db",
                "user": "test_user",
            }
        }

        # Act & Assert
        with pytest.raises(Exception) as exc_info:
            DatabaseConfig(**config_data["database"])

        error_message = str(exc_info.value)
        assert "host" in error_message.lower()
        assert "required" in error_message.lower()

    def test_missing_jwt_secret_key_raises_validation_error(self):
        """Test that missing JWT_SECRET_KEY raises validation error."""
        # This will fail initially - we need JWT validation
        with patch.dict(os.environ, {}, clear=True):
            validator = RequiredConfigValidator(["JWT_SECRET_KEY"])

            result = validator.validate()

            assert not result.is_valid
            assert "JWT_SECRET_KEY" in result.errors[0].field_name
            assert "required" in result.errors[0].message.lower()

    def test_missing_database_password_in_production_raises_error(self):
        """Test that missing database password in production raises error."""
        # This will fail initially - we need environment-specific validation
        config_data = {
            "database": {
                "host": "prod-db.example.com",
                "port": 5432,
                "name": "prod_db",
                "user": "prod_user"
                # "password": None  # Missing in production
            }
        }

        with patch.dict(os.environ, {"ENVIRONMENT": "production"}):
            validator = EnvironmentValidator("production")

            result = validator.validate_database_config(
                DatabaseConfig(**config_data["database"])
            )

            assert not result.is_valid
            assert "password" in result.errors[0].field_name
            assert "production" in result.errors[0].message.lower()

    def test_missing_vector_api_key_for_knowledge_service_raises_error(self):
        """Test that missing vector API key for knowledge service raises error."""
        # This will fail initially - we need service-specific validation
        with patch.dict(os.environ, {"SERVICE_NAME": "knowledge-service"}, clear=True):
            validator = RequiredConfigValidator(["PINECONE_API_KEY", "OPENAI_API_KEY"])

            result = validator.validate()

            assert not result.is_valid
            assert len(result.errors) >= 2

            error_fields = [error.field_name for error in result.errors]
            assert "PINECONE_API_KEY" in error_fields
            assert "OPENAI_API_KEY" in error_fields


class TestInvalidConfigurationValues:
    """Test cases for invalid configuration values."""

    def test_invalid_database_port_raises_validation_error(self):
        """Test that invalid database port raises validation error."""
        # Arrange
        config_data = {
            "host": "localhost",
            "port": 99999,  # Invalid port (too high)
            "name": "test_db",
            "user": "test_user",
        }

        # Act & Assert
        with pytest.raises(ValueError) as exc_info:
            DatabaseConfig(**config_data)

        error_message = str(exc_info.value)
        assert "port" in error_message.lower()
        assert "65535" in error_message or "range" in error_message.lower()

    def test_invalid_jwt_algorithm_raises_validation_error(self):
        """Test that invalid JWT algorithm raises validation error."""
        # This will fail initially - we need JWT algorithm validation
        validator = TypeValidator(
            "JWT_ALGORITHM",
            str,
            allowed_values=["HS256", "HS384", "HS512", "RS256", "RS384", "RS512"],
        )

        result = validator.validate("INVALID_ALGORITHM")

        assert not result.is_valid
        assert "algorithm" in result.errors[0].message.lower()
        assert "allowed" in result.errors[0].message.lower()

    def test_invalid_url_format_raises_validation_error(self):
        """Test that invalid URL format raises validation error."""
        # This will fail initially - we need URL validation
        validator = URLValidator("DATABASE_URL")

        invalid_urls = [
            "not-a-url",
            "ftp://invalid-scheme.com",
            "http://",
            "postgresql://user@:5432/db",  # Missing host
        ]

        for invalid_url in invalid_urls:
            result = validator.validate(invalid_url)

            assert not result.is_valid
            assert "url" in result.errors[0].message.lower()
            assert "format" in result.errors[0].message.lower()

    def test_weak_secret_key_raises_validation_error(self):
        """Test that weak secret key raises validation error."""
        # This will fail initially - we need secret strength validation
        validator = SecretValidator(
            "JWT_SECRET_KEY", min_length=32, require_complexity=True
        )

        weak_secrets = [
            "short",
            "12345678901234567890123456789012",  # 32 chars but no complexity
            "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",  # 32 chars but repetitive
        ]

        for weak_secret in weak_secrets:
            result = validator.validate(weak_secret)

            assert not result.is_valid
            assert (
                "secret" in result.errors[0].message.lower()
                or "key" in result.errors[0].message.lower()
            )

    def test_out_of_range_values_raise_validation_errors(self):
        """Test that out-of-range values raise validation errors."""
        # This will fail initially - we need range validation
        validators = [
            RangeValidator("MAX_CONNECTIONS", int, min_value=1, max_value=1000),
            RangeValidator("TIMEOUT_SECONDS", int, min_value=1, max_value=3600),
            RangeValidator("CACHE_TTL_MINUTES", int, min_value=1, max_value=1440),
        ]

        invalid_values = [
            ("MAX_CONNECTIONS", 0),  # Below minimum
            ("MAX_CONNECTIONS", 1001),  # Above maximum
            ("TIMEOUT_SECONDS", -1),  # Negative
            ("TIMEOUT_SECONDS", 3601),  # Above maximum
            ("CACHE_TTL_MINUTES", 0),  # Below minimum
            ("CACHE_TTL_MINUTES", 1441),  # Above maximum
        ]

        for field_name, invalid_value in invalid_values:
            validator = next(v for v in validators if v.field_name == field_name)
            result = validator.validate(invalid_value)

            assert not result.is_valid
            assert (
                "range" in result.errors[0].message.lower()
                or "between" in result.errors[0].message.lower()
            )


class TestFallbackMechanisms:
    """Test cases for configuration fallback mechanisms."""

    def test_missing_optional_config_uses_default_values(self):
        """Test that missing optional configuration uses default values."""
        # This will fail initially - we need default value handling
        config_data = {
            "database": {
                "host": "localhost",
                "port": 5432,
                "name": "test_db",
                "user": "test_user"
                # No password - should use default (None)
            }
            # No redis config - should use default (None)
            # No api config - should use defaults
        }

        config = ConfigSchema(**config_data)

        # Database should be present with defaults
        assert config.database.host == "localhost"
        assert config.database.password is None

        # Redis should be None (optional)
        assert config.redis is None

        # API should use defaults if not provided
        if config.api:
            assert config.api.host == "0.0.0.0"
            assert config.api.port == 8000
            assert config.api.debug is False

    def test_environment_variables_override_file_config(self):
        """Test that environment variables override file configuration."""
        # This will fail initially - we need override mechanism
        file_config = {
            "database": {
                "host": "file-host",
                "port": 5432,
                "name": "file_db",
                "user": "file_user",
            }
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(file_config, f)
            config_file = f.name

        try:
            with patch.dict(
                os.environ,
                {
                    "DATABASE_HOST": "env-host",
                    "DATABASE_PORT": "3306",
                    "DATABASE_PASSWORD": "env-password",
                },
            ):
                loader = ConfigLoader()
                config = loader.load_from_file_and_env(config_file)

                # Environment should override file
                assert config.database.host == "env-host"
                assert config.database.port == 3306
                assert config.database.password == "env-password"

                # File values should remain for non-overridden fields
                assert config.database.name == "file_db"
                assert config.database.user == "file_user"
        finally:
            os.unlink(config_file)

    def test_fallback_to_secondary_llm_provider_on_primary_failure(self):
        """Test fallback to secondary LLM provider when primary fails."""
        # This will fail initially - we need provider fallback logic
        from packages.common.config.llm import LLMConfig, LLMProvider

        config_data = {
            "primary_provider": LLMProvider.OPENAI,
            "fallback_providers": [LLMProvider.ANTHROPIC, LLMProvider.COHERE],
            "openai_api_key": "invalid-key",
            "anthropic_api_key": "valid-key",
            "cohere_api_key": "valid-key",
        }

        llm_config = LLMConfig(**config_data)

        # Simulate primary provider failure
        with patch("packages.common.config.llm.test_provider_connection") as mock_test:
            mock_test.side_effect = [False, True, True]  # OpenAI fails, others succeed

            available_provider = llm_config.get_available_provider()

            assert available_provider == LLMProvider.ANTHROPIC

    def test_graceful_degradation_when_optional_services_unavailable(self):
        """Test graceful degradation when optional services are unavailable."""
        # This will fail initially - we need graceful degradation
        config_data = {
            "database": {
                "host": "localhost",
                "port": 5432,
                "name": "test_db",
                "user": "test_user",
            }
            # No Redis config - should degrade gracefully
            # No vector config - should degrade gracefully
        }

        config = ConfigSchema(**config_data)
        validator = ConfigValidator()

        result = validator.validate_with_degradation(config)

        assert result.is_valid  # Should be valid even without optional services
        assert any(
            "redis" in warning.lower() for warning in result.warnings
        )  # Should warn about missing Redis
        assert result.degraded_features  # Should list degraded features
        assert "caching" in result.degraded_features


class TestConfigurationValidationMessages:
    """Test cases for clear and helpful validation error messages."""

    def test_validation_error_includes_field_name_and_expected_format(self):
        """Test that validation errors include field name and expected format."""
        # This will fail initially - we need structured error messages
        validator = TypeValidator("DATABASE_PORT", int, min_value=1, max_value=65535)

        result = validator.validate("not-a-number")

        assert not result.is_valid
        error = result.errors[0]

        # Error should include field name
        assert "DATABASE_PORT" in error.field_name

        # Error should include expected type
        assert "integer" in error.message.lower() or "int" in error.message.lower()

        # Error should include valid range
        assert "1" in error.message and "65535" in error.message

    def test_validation_error_includes_current_value_and_suggestion(self):
        """Test that validation errors include current value and suggestions."""
        # This will fail initially - we need helpful error messages
        validator = URLValidator("DATABASE_URL")

        result = validator.validate("not-a-url")

        assert not result.is_valid
        error = result.errors[0]

        # Error should include the invalid value
        assert "not-a-url" in error.message

        # Error should include suggestion
        assert "example" in error.message.lower() or "format" in error.message.lower()
        assert "postgresql://" in error.message or "mysql://" in error.message

    def test_multiple_validation_errors_are_collected_and_reported(self):
        """Test that multiple validation errors are collected and reported together."""
        # This will fail initially - we need error collection
        config_data = {
            "database": {
                "host": "",  # Invalid: empty
                "port": -1,  # Invalid: negative
                "name": "",  # Invalid: empty
                "user": "",  # Invalid: empty
            }
        }

        validator = ConfigValidator()

        result = validator.validate_database_config(config_data["database"])

        assert not result.is_valid
        assert len(result.errors) >= 4  # Should have multiple errors

        error_fields = [error.field_name for error in result.errors]
        assert "host" in error_fields
        assert "port" in error_fields
        assert "name" in error_fields
        assert "user" in error_fields

    def test_validation_error_includes_service_context(self):
        """Test that validation errors include service context for better debugging."""
        # This will fail initially - we need service context in errors
        with patch.dict(os.environ, {"SERVICE_NAME": "knowledge-service"}):
            validator = RequiredConfigValidator(["PINECONE_API_KEY", "OPENAI_API_KEY"])

            result = validator.validate()

            assert not result.is_valid

            for error in result.errors:
                # Error should include service context
                assert (
                    "knowledge-service" in error.context
                    or "knowledge" in error.context.lower()
                )


class TestEnvironmentSpecificValidation:
    """Test cases for environment-specific configuration validation."""

    def test_development_environment_allows_relaxed_validation(self):
        """Test that development environment allows relaxed validation rules."""
        # This will fail initially - we need environment-specific validation
        config_data = {
            "database": {
                "host": "localhost",
                "port": 5432,
                "name": "dev_db",
                "user": "dev_user"
                # No password in development - should be allowed
            },
            "api": {
                "debug": True,  # Debug allowed in development
                "secret_key": "dev-secret-key-not-very-secure",  # Weak key allowed in dev
            },
        }

        with patch.dict(os.environ, {"ENVIRONMENT": "development"}):
            validator = EnvironmentValidator("development")

            result = validator.validate_config(ConfigSchema(**config_data))

            assert result.is_valid
            # Should have warnings but not errors
            assert len(result.warnings) > 0
            assert "development" in result.warnings[0].lower()

    def test_production_environment_enforces_strict_validation(self):
        """Test that production environment enforces strict validation rules."""
        # This will fail initially - we need strict production validation
        config_data = {
            "database": {
                "host": "localhost",  # Should not be localhost in production
                "port": 5432,
                "name": "prod_db",
                "user": "prod_user"
                # No password - should fail in production
            },
            "api": {
                "debug": True,  # Should not be True in production
                "secret_key": "weak-key",  # Should be strong in production
            },
        }

        with patch.dict(os.environ, {"ENVIRONMENT": "production"}):
            validator = EnvironmentValidator("production")

            result = validator.validate_config(ConfigSchema(**config_data))

            assert not result.is_valid

            error_messages = [error.message.lower() for error in result.errors]

            # Should have errors for production-specific issues
            assert any("password" in msg for msg in error_messages)
            assert any("debug" in msg for msg in error_messages)
            assert any("localhost" in msg for msg in error_messages)

    def test_testing_environment_requires_test_specific_config(self):
        """Test that testing environment requires test-specific configuration."""
        # This will fail initially - we need test environment validation
        config_data = {
            "database": {
                "host": "localhost",
                "port": 5432,
                "name": "prod_db",  # Should be test database
                "user": "test_user",
            }
        }

        with patch.dict(os.environ, {"ENVIRONMENT": "testing"}):
            validator = EnvironmentValidator("testing")

            result = validator.validate_config(ConfigSchema(**config_data))

            assert not result.is_valid

            # Should require test database name
            error_messages = [error.message.lower() for error in result.errors]
            assert any("test" in msg and "database" in msg for msg in error_messages)


class TestConfigurationReloading:
    """Test cases for configuration reloading and change detection."""

    def test_configuration_change_detection_works(self):
        """Test that configuration changes are properly detected."""
        # This will fail initially - we need change detection
        from packages.common.config.watcher import ConfigWatcher

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            initial_config = {
                "database": {
                    "host": "initial-host",
                    "port": 5432,
                    "name": "db",
                    "user": "user",
                }
            }
            json.dump(initial_config, f)
            config_file = f.name

        try:
            watcher = ConfigWatcher(config_file)

            # Initial load
            config1 = watcher.get_current_config()
            assert config1.database.host == "initial-host"

            # Modify file
            with open(config_file, "w") as f:
                updated_config = {
                    "database": {
                        "host": "updated-host",
                        "port": 5432,
                        "name": "db",
                        "user": "user",
                    }
                }
                json.dump(updated_config, f)

            # Should detect change
            assert watcher.has_changed()

            # Should load new config
            config2 = watcher.get_current_config()
            assert config2.database.host == "updated-host"

        finally:
            os.unlink(config_file)

    def test_invalid_configuration_change_is_rejected(self):
        """Test that invalid configuration changes are rejected."""
        # This will fail initially - we need validation on reload
        from packages.common.config.watcher import ConfigWatcher

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            valid_config = {
                "database": {
                    "host": "localhost",
                    "port": 5432,
                    "name": "db",
                    "user": "user",
                }
            }
            json.dump(valid_config, f)
            config_file = f.name

        try:
            watcher = ConfigWatcher(config_file)

            # Initial load should work
            config1 = watcher.get_current_config()
            assert config1.database.host == "localhost"

            # Write invalid config
            with open(config_file, "w") as f:
                invalid_config = {
                    "database": {
                        "host": "localhost",
                        "port": "invalid-port",
                        "name": "db",
                        "user": "user",
                    }
                }
                json.dump(invalid_config, f)

            # Should detect change but reject invalid config
            assert watcher.has_changed()

            with pytest.raises(ConfigValidationError):
                watcher.get_current_config()

            # Should fall back to previous valid config
            config2 = watcher.get_previous_valid_config()
            assert config2.database.host == "localhost"
            assert config2.database.port == 5432

        finally:
            os.unlink(config_file)

    def test_configuration_reload_preserves_runtime_state(self):
        """Test that configuration reload preserves important runtime state."""
        # This will fail initially - we need state preservation
        from packages.common.config.manager import ConfigManager

        manager = ConfigManager()

        # Set some runtime state
        manager.set_runtime_flag("feature_enabled", True)
        manager.increment_counter("reload_count")

        initial_counter = manager.get_counter("reload_count")

        # Simulate config reload
        manager.reload_configuration()

        # Runtime state should be preserved
        assert manager.get_runtime_flag("feature_enabled") is True
        assert manager.get_counter("reload_count") == initial_counter


@pytest.fixture
def temp_config_dir():
    """Create a temporary directory for configuration files."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


@pytest.fixture
def sample_config_data():
    """Sample configuration data for testing."""
    return {
        "database": {
            "host": "localhost",
            "port": 5432,
            "name": "test_db",
            "user": "test_user",
            "password": "test_password",
        },
        "redis": {"host": "localhost", "port": 6379, "db": 0},
        "api": {
            "host": "0.0.0.0",
            "port": 8000,
            "debug": False,
            "secret_key": "test-secret-key-32-characters-long",
        },
    }


@pytest.fixture
def mock_env():
    """Mock environment variables for testing."""
    env_vars = {
        "DATABASE_HOST": "prod-db.example.com",
        "DATABASE_PORT": "5432",
        "DATABASE_PASSWORD": "prod-password",
        "JWT_SECRET_KEY": "super-secret-jwt-key-32-characters-long",
        "ENVIRONMENT": "testing",
    }

    with patch.dict(os.environ, env_vars):
        yield env_vars
