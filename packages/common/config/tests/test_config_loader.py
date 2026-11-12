"""Tests for configuration loader using TDD approach."""

import json
import os
from pathlib import Path
from unittest.mock import mock_open, patch

import pytest

# These imports will fail initially - that's the point of TDD!
# We'll implement them after the tests are written
from packages.common.config.loader import ConfigLoader, ConfigValidationError
from packages.common.config.models import (ConfigSchema, DatabaseConfig,
                                           RedisConfig)


class TestConfigLoader:
    """Test configuration loader functionality."""

    def test_config_loader_can_be_instantiated(self):
        """Test that ConfigLoader can be created."""
        loader = ConfigLoader()
        assert loader is not None

    def test_load_config_from_file_returns_config_object(
        self, temp_config_dir, sample_config_data
    ):
        """Test loading configuration from JSON file."""
        # Arrange
        config_file = temp_config_dir / "config.json"
        config_file.write_text(json.dumps(sample_config_data))
        loader = ConfigLoader()

        # Act
        config = loader.load_from_file(str(config_file))

        # Assert
        assert isinstance(config, ConfigSchema)
        assert config.database.host == "localhost"
        assert config.database.port == 5432

    def test_load_config_from_nonexistent_file_raises_error(self):
        """Test that loading from non-existent file raises appropriate error."""
        loader = ConfigLoader()

        with pytest.raises(FileNotFoundError):
            loader.load_from_file("/nonexistent/config.json")

    def test_load_config_with_invalid_json_raises_validation_error(
        self, temp_config_dir
    ):
        """Test that invalid JSON raises ConfigValidationError."""
        # Arrange
        config_file = temp_config_dir / "invalid.json"
        config_file.write_text("{ invalid json }")
        loader = ConfigLoader()

        # Act & Assert
        with pytest.raises(ConfigValidationError):
            loader.load_from_file(str(config_file))

    def test_load_config_with_missing_required_fields_raises_validation_error(
        self, temp_config_dir
    ):
        """Test that missing required fields raise validation error."""
        # Arrange
        incomplete_config = {"database": {"host": "localhost"}}  # Missing port
        config_file = temp_config_dir / "incomplete.json"
        config_file.write_text(json.dumps(incomplete_config))
        loader = ConfigLoader()

        # Act & Assert
        with pytest.raises(ConfigValidationError) as exc_info:
            loader.load_from_file(str(config_file))

        assert "port" in str(exc_info.value)

    def test_load_config_from_environment_variables(self, mock_env):
        """Test loading configuration from environment variables."""
        # Arrange
        loader = ConfigLoader()

        # Act
        config = loader.load_from_env()

        # Assert
        assert isinstance(config, ConfigSchema)
        assert config.database.host == "prod-db.example.com"
        assert config.database.port == 5432

    def test_environment_variables_override_file_config(
        self, temp_config_dir, sample_config_data, mock_env
    ):
        """Test that environment variables override file configuration."""
        # Arrange
        config_file = temp_config_dir / "config.json"
        config_file.write_text(json.dumps(sample_config_data))
        loader = ConfigLoader()

        # Act
        config = loader.load_from_file_and_env(str(config_file))

        # Assert
        assert config.database.host == "prod-db.example.com"  # From env
        assert config.database.name == "test_db"  # From file (not overridden)

    def test_config_validation_with_invalid_port_number(self, temp_config_dir):
        """Test validation fails with invalid port number."""
        # Arrange
        invalid_config = {
            "database": {
                "host": "localhost",
                "port": "not_a_number",
                "name": "test_db",
                "user": "test_user",
            }
        }
        config_file = temp_config_dir / "invalid_port.json"
        config_file.write_text(json.dumps(invalid_config))
        loader = ConfigLoader()

        # Act & Assert
        with pytest.raises(ConfigValidationError) as exc_info:
            loader.load_from_file(str(config_file))

        assert "port" in str(exc_info.value)

    def test_config_loader_supports_multiple_environments(self, temp_config_dir):
        """Test that config loader can handle different environments."""
        # Arrange
        dev_config = {
            "database": {
                "host": "localhost",
                "port": 5432,
                "name": "dev_db",
                "user": "dev_user",
            }
        }
        prod_config = {
            "database": {
                "host": "prod-db",
                "port": 5432,
                "name": "prod_db",
                "user": "prod_user",
            }
        }

        dev_file = temp_config_dir / "config.dev.json"
        prod_file = temp_config_dir / "config.prod.json"

        dev_file.write_text(json.dumps(dev_config))
        prod_file.write_text(json.dumps(prod_config))

        loader = ConfigLoader()

        # Act
        dev_config_obj = loader.load_from_file(str(dev_file))
        prod_config_obj = loader.load_from_file(str(prod_file))

        # Assert
        assert dev_config_obj.database.name == "dev_db"
        assert prod_config_obj.database.name == "prod_db"


class TestConfigValidation:
    """Test configuration validation logic."""

    def test_database_config_validation_success(self):
        """Test successful database configuration validation."""
        # This will fail initially - we need to implement DatabaseConfig
        config_data = {
            "host": "localhost",
            "port": 5432,
            "name": "test_db",
            "user": "test_user",
        }

        db_config = DatabaseConfig(**config_data)

        assert db_config.host == "localhost"
        assert db_config.port == 5432
        assert db_config.name == "test_db"
        assert db_config.user == "test_user"

    def test_database_config_validation_with_invalid_port(self):
        """Test database config validation fails with invalid port."""
        config_data = {
            "host": "localhost",
            "port": -1,  # Invalid port
            "name": "test_db",
            "user": "test_user",
        }

        with pytest.raises(ValueError):
            DatabaseConfig(**config_data)

    def test_redis_config_validation_success(self):
        """Test successful Redis configuration validation."""
        config_data = {"host": "localhost", "port": 6379, "db": 0}

        redis_config = RedisConfig(**config_data)

        assert redis_config.host == "localhost"
        assert redis_config.port == 6379
        assert redis_config.db == 0

    def test_config_schema_combines_all_configs(self):
        """Test that ConfigSchema properly combines all configuration sections."""
        config_data = {
            "database": {
                "host": "localhost",
                "port": 5432,
                "name": "test_db",
                "user": "test_user",
            },
            "redis": {"host": "localhost", "port": 6379, "db": 0},
        }

        config = ConfigSchema(**config_data)

        assert isinstance(config.database, DatabaseConfig)
        assert isinstance(config.redis, RedisConfig)
        assert config.database.host == "localhost"
        assert config.redis.port == 6379
