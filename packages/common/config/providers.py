"""Secrets providers implementation."""

import json
import os
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, Optional


class SecretsProvider(ABC):
    """Abstract base class for secrets providers."""

    @abstractmethod
    def get_secret(self, key: str) -> Optional[str]:
        """Get a secret value by key.

        Args:
            key: Secret key to retrieve

        Returns:
            Secret value or None if not found
        """
        pass


class EnvironmentSecretsProvider(SecretsProvider):
    """Provides secrets from environment variables."""

    def get_secret(self, key: str) -> Optional[str]:
        """Get secret from environment variable.

        Args:
            key: Environment variable name

        Returns:
            Environment variable value or None if not set
        """
        return os.getenv(key)


class FileSecretsProvider(SecretsProvider):
    """Provides secrets from a JSON file."""

    def __init__(self, file_path: str):
        """Initialize file secrets provider.

        Args:
            file_path: Path to the secrets JSON file
        """
        self.file_path = file_path
        self._secrets: Optional[Dict[str, Any]] = None
        self._load_secrets()

    def _load_secrets(self) -> None:
        """Load secrets from the file."""
        try:
            if Path(self.file_path).exists():
                with open(self.file_path, "r") as f:
                    self._secrets = json.load(f)
            else:
                self._secrets = {}
        except (json.JSONDecodeError, IOError):
            self._secrets = {}

    def get_secret(self, key: str) -> Optional[str]:
        """Get secret from loaded file data.

        Args:
            key: Secret key to retrieve

        Returns:
            Secret value or None if not found
        """
        if self._secrets is None:
            return None

        return self._secrets.get(key)
