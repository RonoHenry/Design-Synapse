"""Secrets management implementation."""

import os
from typing import Any, List, Optional, Union


class SecretNotFoundError(Exception):
    """Raised when a required secret is not found."""

    pass


class MaskedSecret:
    """A secret value that masks itself in string representations."""

    def __init__(self, value: str):
        self._value = value

    def __str__(self) -> str:
        return "[MASKED]"

    def __repr__(self) -> str:
        return "MaskedSecret([MASKED])"

    def get_value(self) -> str:
        """Get the actual secret value."""
        return self._value


class SecretsManager:
    """Manages secrets from various providers with fallback support."""

    def __init__(
        self, providers: Union["SecretsProvider", List["SecretsProvider"]] = None
    ):
        """Initialize secrets manager with providers.

        Args:
            providers: Single provider or list of providers (tried in order)
        """
        if providers is None:
            from .providers import EnvironmentSecretsProvider

            providers = EnvironmentSecretsProvider()

        if not isinstance(providers, list):
            providers = [providers]

        self.providers = providers

    def get_secret(
        self, key: str, default: Optional[str] = None, mask_in_logs: bool = False
    ) -> Union[str, MaskedSecret]:
        """Get a secret value from providers.

        Args:
            key: Secret key to retrieve
            default: Default value if secret not found
            mask_in_logs: Whether to return a masked secret for logging safety

        Returns:
            Secret value or MaskedSecret if mask_in_logs=True

        Raises:
            SecretNotFoundError: If secret not found and no default provided
        """
        for provider in self.providers:
            value = provider.get_secret(key)
            if value is not None:
                if mask_in_logs:
                    return MaskedSecret(value)
                return value

        if default is not None:
            if mask_in_logs:
                return MaskedSecret(default)
            return default

        raise SecretNotFoundError(f"Secret '{key}' not found in any provider")
