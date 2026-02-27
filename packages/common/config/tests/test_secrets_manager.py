"""Tests for secrets management using TDD approach."""

from unittest.mock import MagicMock, patch

import pytest

from packages.common.config.providers import (EnvironmentSecretsProvider,
                                              FileSecretsProvider)
# These imports will fail initially - implementing with TDD
from packages.common.config.secrets import SecretNotFoundError, SecretsManager


class TestSecretsManager:
    """Test secrets management functionality."""

    def test_secrets_manager_can_be_instantiated(self):
        """Test that SecretsManager can be created."""
        manager = SecretsManager()
        assert manager is not None

    def test_get_secret_from_environment_provider(self, mock_env):
        """Test retrieving secret from environment variables."""
        # Arrange
        provider = EnvironmentSecretsProvider()
        manager = SecretsManager(provider)

        # Act
        secret = manager.get_secret("DATABASE_PASSWORD")

        # Assert
        assert secret == "secret123"

    def test_get_nonexistent_secret_raises_error(self):
        """Test that requesting non-existent secret raises appropriate error."""
        provider = EnvironmentSecretsProvider()
        manager = SecretsManager(provider)

        with pytest.raises(SecretNotFoundError):
            manager.get_secret("NONEXISTENT_SECRET")

    def test_get_secret_with_default_value(self):
        """Test getting secret with default value when secret doesn't exist."""
        provider = EnvironmentSecretsProvider()
        manager = SecretsManager(provider)

        secret = manager.get_secret("NONEXISTENT_SECRET", default="default_value")

        assert secret == "default_value"

    def test_file_secrets_provider_loads_from_file(self, temp_config_dir):
        """Test loading secrets from file."""
        # Arrange
        secrets_file = temp_config_dir / "secrets.json"
        secrets_data = {
            "database_password": "file_secret_123",
            "api_key": "file_api_key_456",
        }
        secrets_file.write_text(
            '{"database_password": "file_secret_123", "api_key": "file_api_key_456"}'
        )

        provider = FileSecretsProvider(str(secrets_file))
        manager = SecretsManager(provider)

        # Act
        password = manager.get_secret("database_password")
        api_key = manager.get_secret("api_key")

        # Assert
        assert password == "file_secret_123"
        assert api_key == "file_api_key_456"

    def test_secrets_manager_supports_multiple_providers(
        self, mock_env, temp_config_dir
    ):
        """Test that secrets manager can use multiple providers with fallback."""
        # Arrange
        secrets_file = temp_config_dir / "secrets.json"
        secrets_file.write_text('{"file_only_secret": "from_file"}')

        env_provider = EnvironmentSecretsProvider()
        file_provider = FileSecretsProvider(str(secrets_file))
        manager = SecretsManager([env_provider, file_provider])

        # Act
        env_secret = manager.get_secret("DATABASE_PASSWORD")  # From env
        file_secret = manager.get_secret("file_only_secret")  # From file

        # Assert
        assert env_secret == "secret123"
        assert file_secret == "from_file"

    def test_secrets_are_masked_in_logs(self, mock_env):
        """Test that secrets are properly masked when logged."""
        provider = EnvironmentSecretsProvider()
        manager = SecretsManager(provider)

        # This test ensures secrets don't leak in logs
        secret_repr = repr(manager.get_secret("DATABASE_PASSWORD", mask_in_logs=True))

        assert "secret123" not in secret_repr
        assert "***" in secret_repr or "[MASKED]" in secret_repr


class TestSecretsProviders:
    """Test different secrets providers."""

    def test_environment_provider_gets_env_var(self, mock_env):
        """Test environment provider retrieves environment variables."""
        provider = EnvironmentSecretsProvider()

        secret = provider.get_secret("API_SECRET_KEY")

        assert secret == "super-secret-key"

    def test_environment_provider_returns_none_for_missing_var(self):
        """Test environment provider returns None for missing variables."""
        provider = EnvironmentSecretsProvider()

        secret = provider.get_secret("MISSING_VAR")

        assert secret is None

    def test_file_provider_loads_json_secrets(self, temp_config_dir):
        """Test file provider loads secrets from JSON file."""
        # Arrange
        secrets_file = temp_config_dir / "secrets.json"
        secrets_data = {"secret1": "value1", "secret2": "value2"}
        secrets_file.write_text('{"secret1": "value1", "secret2": "value2"}')

        provider = FileSecretsProvider(str(secrets_file))

        # Act & Assert
        assert provider.get_secret("secret1") == "value1"
        assert provider.get_secret("secret2") == "value2"
        assert provider.get_secret("missing") is None

    def test_file_provider_handles_missing_file(self):
        """Test file provider handles missing secrets file gracefully."""
        provider = FileSecretsProvider("/nonexistent/secrets.json")

        # Should not raise exception, just return None
        secret = provider.get_secret("any_secret")

        assert secret is None

    def test_file_provider_handles_invalid_json(self, temp_config_dir):
        """Test file provider handles invalid JSON gracefully."""
        # Arrange
        secrets_file = temp_config_dir / "invalid.json"
        secrets_file.write_text("{ invalid json }")

        provider = FileSecretsProvider(str(secrets_file))

        # Should not raise exception, just return None
        secret = provider.get_secret("any_secret")

        assert secret is None
