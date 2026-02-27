"""Configuration loader implementation."""

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional

from .models import ConfigSchema


class ConfigValidationError(Exception):
    """Raised when configuration validation fails."""

    pass


class ConfigLoader:
    """Loads and validates configuration from various sources."""

    def __init__(self):
        """Initialize the configuration loader."""
        pass

    def load_from_file(self, file_path: str) -> ConfigSchema:
        """Load configuration from a JSON file.

        Args:
            file_path: Path to the configuration file

        Returns:
            ConfigSchema: Validated configuration object

        Raises:
            FileNotFoundError: If the configuration file doesn't exist
            ConfigValidationError: If the configuration is invalid
        """
        if not Path(file_path).exists():
            raise FileNotFoundError(f"Configuration file not found: {file_path}")

        try:
            with open(file_path, "r") as f:
                config_data = json.load(f)
        except json.JSONDecodeError as e:
            raise ConfigValidationError(f"Invalid JSON in configuration file: {e}")

        try:
            return ConfigSchema(**config_data)
        except Exception as e:
            raise ConfigValidationError(f"Configuration validation failed: {e}")

    def load_from_env(self) -> ConfigSchema:
        """Load configuration from environment variables.

        Returns:
            ConfigSchema: Configuration object built from environment variables
        """
        config_data = {
            "database": {
                "host": os.getenv("DATABASE_HOST", "localhost"),
                "port": int(os.getenv("DATABASE_PORT", "5432")),
                "name": os.getenv("DATABASE_NAME", "app_db"),
                "user": os.getenv("DATABASE_USER", "app_user"),
                "password": os.getenv("DATABASE_PASSWORD"),
            }
        }

        # Add Redis config if Redis URL is provided
        redis_url = os.getenv("REDIS_URL")
        if redis_url:
            # Simple parsing for redis://host:port/db format
            if redis_url.startswith("redis://"):
                url_parts = redis_url[8:].split("/")
                host_port = url_parts[0].split(":")
                config_data["redis"] = {
                    "host": host_port[0],
                    "port": int(host_port[1]) if len(host_port) > 1 else 6379,
                    "db": int(url_parts[1]) if len(url_parts) > 1 else 0,
                }

        # Add API config from environment
        if os.getenv("API_SECRET_KEY"):
            config_data["api"] = {
                "host": os.getenv("API_HOST", "0.0.0.0"),
                "port": int(os.getenv("API_PORT", "8000")),
                "debug": os.getenv("API_DEBUG", "false").lower() == "true",
                "secret_key": os.getenv("API_SECRET_KEY"),
            }

        try:
            return ConfigSchema(**config_data)
        except Exception as e:
            raise ConfigValidationError(
                f"Environment configuration validation failed: {e}"
            )

    def load_from_file_and_env(self, file_path: str) -> ConfigSchema:
        """Load configuration from file and override with environment variables.

        Args:
            file_path: Path to the base configuration file

        Returns:
            ConfigSchema: Configuration with environment overrides
        """
        # Load base config from file
        file_config = self.load_from_file(file_path)
        file_data = file_config.model_dump()

        # Override with environment variables
        env_overrides = {}

        # Database overrides
        if os.getenv("DATABASE_HOST"):
            env_overrides.setdefault("database", {})["host"] = os.getenv(
                "DATABASE_HOST"
            )
        if os.getenv("DATABASE_PORT"):
            env_overrides.setdefault("database", {})["port"] = int(
                os.getenv("DATABASE_PORT")
            )
        if os.getenv("DATABASE_PASSWORD"):
            env_overrides.setdefault("database", {})["password"] = os.getenv(
                "DATABASE_PASSWORD"
            )

        # API overrides
        if os.getenv("API_SECRET_KEY"):
            env_overrides.setdefault("api", {})["secret_key"] = os.getenv(
                "API_SECRET_KEY"
            )
        if os.getenv("API_HOST"):
            env_overrides.setdefault("api", {})["host"] = os.getenv("API_HOST")
        if os.getenv("API_PORT"):
            env_overrides.setdefault("api", {})["port"] = int(os.getenv("API_PORT"))
        if os.getenv("API_DEBUG"):
            env_overrides.setdefault("api", {})["debug"] = (
                os.getenv("API_DEBUG").lower() == "true"
            )

        # Merge overrides
        self._deep_merge(file_data, env_overrides)

        try:
            return ConfigSchema(**file_data)
        except Exception as e:
            raise ConfigValidationError(f"Merged configuration validation failed: {e}")

    def _deep_merge(self, base: Dict[str, Any], override: Dict[str, Any]) -> None:
        """Deep merge override dictionary into base dictionary."""
        for key, value in override.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._deep_merge(base[key], value)
            else:
                base[key] = value
