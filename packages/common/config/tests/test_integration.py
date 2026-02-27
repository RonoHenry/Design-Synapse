"""Integration tests for configuration management system."""

import json
import os
import tempfile
from pathlib import Path

import pytest

from packages.common.config.loader import ConfigLoader
from packages.common.config.providers import (EnvironmentSecretsProvider,
                                              FileSecretsProvider)
from packages.common.config.secrets import SecretsManager
from packages.common.config.security import SecurityConfig


class TestConfigurationIntegration:
    """Test complete configuration loading workflow."""

    def test_complete_config_loading_workflow(self, temp_config_dir):
        """Test complete configuration loading from file with environment overrides."""
        # Arrange - Create config files
        base_config = {
            "database": {
                "host": "localhost",
                "port": 5432,
                "name": "app_db",
                "user": "app_user",
            },
            "redis": {"host": "localhost", "port": 6379, "db": 0},
            "api": {"host": "0.0.0.0", "port": 8000, "debug": False},
        }

        config_file = temp_config_dir / "config.json"
        config_file.write_text(json.dumps(base_config))

        # Set environment overrides
        env_vars = {
            "DATABASE_HOST": "prod-db.example.com",
            "DATABASE_PASSWORD": "prod-secret-123",
            "API_SECRET_KEY": "super-secret-api-key",
        }

        original_env = dict(os.environ)
        os.environ.update(env_vars)

        try:
            # Act
            loader = ConfigLoader()
            config = loader.load_from_file_and_env(str(config_file))

            # Assert
            assert config.database.host == "prod-db.example.com"  # From env
            assert config.database.port == 5432  # From file
            assert config.database.password == "prod-secret-123"  # From env
            assert config.api.secret_key == "super-secret-api-key"  # From env

        finally:
            # Cleanup
            os.environ.clear()
            os.environ.update(original_env)

    def test_secrets_integration_with_config_loading(self, temp_config_dir):
        """Test secrets management integration with configuration loading."""
        # Arrange - Create secrets file
        secrets_data = {
            "database_password": "file-secret-password",
            "api_secret_key": "file-secret-api-key",
            "jwt_secret": "file-jwt-secret",
        }

        secrets_file = temp_config_dir / "secrets.json"
        secrets_file.write_text(json.dumps(secrets_data))

        # Set some environment secrets
        env_vars = {
            "DATABASE_PASSWORD": "env-secret-password",  # Should override file
            "REDIS_PASSWORD": "env-redis-password",  # Only in env
        }

        original_env = dict(os.environ)
        os.environ.update(env_vars)

        try:
            # Act
            env_provider = EnvironmentSecretsProvider()
            file_provider = FileSecretsProvider(str(secrets_file))
            secrets_manager = SecretsManager([env_provider, file_provider])

            # Assert - Environment takes precedence
            assert (
                secrets_manager.get_secret("DATABASE_PASSWORD") == "env-secret-password"
            )

            # Assert - File fallback works
            assert secrets_manager.get_secret("api_secret_key") == "file-secret-api-key"
            assert secrets_manager.get_secret("jwt_secret") == "file-jwt-secret"

            # Assert - Environment-only secret
            assert secrets_manager.get_secret("REDIS_PASSWORD") == "env-redis-password"

            # Assert - Non-existent secret with default
            assert (
                secrets_manager.get_secret("MISSING_SECRET", default="default_value")
                == "default_value"
            )

        finally:
            # Cleanup
            os.environ.clear()
            os.environ.update(original_env)

    def test_security_config_integration(self, temp_config_dir):
        """Test security configuration integration."""
        # Arrange
        security_config_data = {
            "ssl": {
                "enabled": True,
                "cert_file": "/etc/ssl/certs/app.crt",
                "key_file": "/etc/ssl/private/app.key",
                "ca_file": "/etc/ssl/certs/ca.crt",
            },
            "headers": {
                "hsts_enabled": True,
                "hsts_max_age": 86400,
                "content_security_policy": "default-src 'self'; script-src 'self' 'unsafe-inline'",
                "x_frame_options": "SAMEORIGIN",
            },
        }

        config_file = temp_config_dir / "security.json"
        config_file.write_text(json.dumps(security_config_data))

        # Act
        with open(config_file, "r") as f:
            config_data = json.load(f)

        security_config = SecurityConfig(**config_data)

        # Assert
        assert security_config.ssl.enabled is True
        assert security_config.ssl.cert_file == "/etc/ssl/certs/app.crt"
        assert security_config.headers.hsts_max_age == 86400
        assert security_config.headers.x_frame_options == "SAMEORIGIN"

    def test_environment_specific_configuration(self, temp_config_dir):
        """Test loading different configurations for different environments."""
        # Arrange - Create environment-specific configs
        dev_config = {
            "database": {
                "host": "localhost",
                "port": 5432,
                "name": "dev_db",
                "user": "dev_user",
            },
            "api": {"debug": True, "port": 8000},
        }

        prod_config = {
            "database": {
                "host": "prod-db.cluster.local",
                "port": 5432,
                "name": "prod_db",
                "user": "prod_user",
            },
            "api": {"debug": False, "port": 80},
        }

        dev_file = temp_config_dir / "config.dev.json"
        prod_file = temp_config_dir / "config.prod.json"

        dev_file.write_text(json.dumps(dev_config))
        prod_file.write_text(json.dumps(prod_config))

        loader = ConfigLoader()

        # Act & Assert - Development
        dev_config_obj = loader.load_from_file(str(dev_file))
        assert dev_config_obj.database.host == "localhost"
        assert dev_config_obj.api.debug is True
        assert dev_config_obj.api.port == 8000

        # Act & Assert - Production
        prod_config_obj = loader.load_from_file(str(prod_file))
        assert prod_config_obj.database.host == "prod-db.cluster.local"
        assert prod_config_obj.api.debug is False
        assert prod_config_obj.api.port == 80

    def test_configuration_validation_across_environments(self, temp_config_dir):
        """Test that configuration validation works consistently across environments."""
        # Arrange - Create configs with validation issues
        invalid_configs = [
            # Missing required database fields
            {"database": {"host": "localhost"}},
            # Invalid port numbers
            {
                "database": {
                    "host": "localhost",
                    "port": -1,
                    "name": "db",
                    "user": "user",
                }
            },
            {
                "database": {
                    "host": "localhost",
                    "port": 70000,
                    "name": "db",
                    "user": "user",
                }
            },
            # Invalid Redis config
            {
                "database": {
                    "host": "localhost",
                    "port": 5432,
                    "name": "db",
                    "user": "user",
                },
                "redis": {"host": "localhost", "port": "invalid", "db": 0},
            },
        ]

        loader = ConfigLoader()

        for i, invalid_config in enumerate(invalid_configs):
            config_file = temp_config_dir / f"invalid_{i}.json"
            config_file.write_text(json.dumps(invalid_config))

            # Act & Assert
            with pytest.raises(Exception):  # Should raise validation error
                loader.load_from_file(str(config_file))


class TestSecurityIntegration:
    """Test security configuration integration."""

    def test_ssl_configuration_validation_in_production_mode(self):
        """Test SSL configuration validation for production deployment."""
        from packages.common.config.security import SSLConfig

        # Production SSL config should require all necessary files
        with pytest.raises(ValueError):
            SSLConfig(enabled=True, cert_file=None, key_file="/path/to/key.pem")

        with pytest.raises(ValueError):
            SSLConfig(enabled=True, cert_file="/path/to/cert.pem", key_file=None)

        # Valid production SSL config
        ssl_config = SSLConfig(
            enabled=True,
            cert_file="/etc/ssl/certs/app.crt",
            key_file="/etc/ssl/private/app.key",
            ca_file="/etc/ssl/certs/ca.crt",
        )

        assert ssl_config.enabled is True
        assert ssl_config.cert_file is not None
        assert ssl_config.key_file is not None

    def test_security_headers_production_defaults(self):
        """Test that security headers have production-ready defaults."""
        from packages.common.config.middleware import SecurityHeadersMiddleware
        from packages.common.config.security import SecurityHeadersConfig

        # Default config should be production-ready
        config = SecurityHeadersConfig()
        middleware = SecurityHeadersMiddleware(config)
        headers = middleware.get_security_headers()

        # Check critical security headers are present
        assert "Strict-Transport-Security" in headers
        assert "Content-Security-Policy" in headers
        assert "X-Frame-Options" in headers
        assert "X-Content-Type-Options" in headers
        assert "Referrer-Policy" in headers

        # Check HSTS is configured for at least 1 year
        assert "max-age=31536000" in headers["Strict-Transport-Security"]

        # Check X-Frame-Options is restrictive
        assert headers["X-Frame-Options"] in ["DENY", "SAMEORIGIN"]

        # Check X-Content-Type-Options prevents MIME sniffing
        assert headers["X-Content-Type-Options"] == "nosniff"

    def test_configuration_loading_with_secrets_masking(self, temp_config_dir):
        """Test that secrets are properly masked when configuration is logged."""
        # Arrange
        secrets_data = {"database_password": "super-secret-password"}
        secrets_file = temp_config_dir / "secrets.json"
        secrets_file.write_text(json.dumps(secrets_data))

        # Act
        file_provider = FileSecretsProvider(str(secrets_file))
        secrets_manager = SecretsManager(file_provider)

        masked_secret = secrets_manager.get_secret(
            "database_password", mask_in_logs=True
        )

        # Assert
        assert str(masked_secret) == "[MASKED]"
        assert repr(masked_secret) == "MaskedSecret([MASKED])"
        assert "super-secret-password" not in str(masked_secret)
        assert "super-secret-password" not in repr(masked_secret)

        # But we can still get the actual value when needed
        assert masked_secret.get_value() == "super-secret-password"
