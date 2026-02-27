"""Configuration file watcher for detecting changes."""

import json
import os
import time
from pathlib import Path
from typing import Optional

from .loader import ConfigLoader, ConfigValidationError
from .models import ConfigSchema


class ConfigWatcher:
    """Watches configuration files for changes and reloads them."""

    def __init__(self, config_file_path: str):
        self.config_file_path = Path(config_file_path)
        self.loader = ConfigLoader()
        self._last_modified = None
        self._current_config: Optional[ConfigSchema] = None
        self._previous_valid_config: Optional[ConfigSchema] = None

        # Load initial configuration
        self._load_initial_config()

    def _load_initial_config(self):
        """Load the initial configuration."""
        try:
            self._current_config = self.loader.load_from_file(
                str(self.config_file_path)
            )
            self._previous_valid_config = self._current_config
            self._last_modified = self.config_file_path.stat().st_mtime
        except Exception as e:
            raise ConfigValidationError(f"Failed to load initial configuration: {e}")

    def has_changed(self) -> bool:
        """Check if the configuration file has changed."""
        if not self.config_file_path.exists():
            return False

        current_modified = self.config_file_path.stat().st_mtime
        return current_modified != self._last_modified

    def get_current_config(self) -> ConfigSchema:
        """Get the current configuration, reloading if changed."""
        if self.has_changed():
            self._reload_config()

        return self._current_config

    def get_previous_valid_config(self) -> ConfigSchema:
        """Get the last known valid configuration."""
        return self._previous_valid_config

    def _reload_config(self):
        """Reload configuration from file."""
        try:
            new_config = self.loader.load_from_file(str(self.config_file_path))

            # If validation succeeds, update current config
            self._previous_valid_config = self._current_config
            self._current_config = new_config
            self._last_modified = self.config_file_path.stat().st_mtime

        except ConfigValidationError:
            # Don't update _current_config on validation failure
            # This allows get_current_config() to raise the error
            # while get_previous_valid_config() returns the last good config
            self._last_modified = self.config_file_path.stat().st_mtime
            raise
