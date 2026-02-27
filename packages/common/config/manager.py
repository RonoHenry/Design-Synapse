"""Configuration manager for runtime state and reloading."""

from threading import Lock
from typing import Any, Dict, Optional

from .models import ConfigSchema
from .watcher import ConfigWatcher


class ConfigManager:
    """Manages configuration with runtime state preservation."""

    def __init__(self, config_file_path: Optional[str] = None):
        self._runtime_flags: Dict[str, Any] = {}
        self._counters: Dict[str, int] = {}
        self._lock = Lock()
        self._watcher: Optional[ConfigWatcher] = None

        if config_file_path:
            self._watcher = ConfigWatcher(config_file_path)

    def set_runtime_flag(self, key: str, value: Any):
        """Set a runtime flag that persists across config reloads."""
        with self._lock:
            self._runtime_flags[key] = value

    def get_runtime_flag(self, key: str, default: Any = None) -> Any:
        """Get a runtime flag value."""
        with self._lock:
            return self._runtime_flags.get(key, default)

    def increment_counter(self, key: str) -> int:
        """Increment a counter and return the new value."""
        with self._lock:
            self._counters[key] = self._counters.get(key, 0) + 1
            return self._counters[key]

    def get_counter(self, key: str) -> int:
        """Get the current counter value."""
        with self._lock:
            return self._counters.get(key, 0)

    def reload_configuration(self):
        """Reload configuration while preserving runtime state."""
        if self._watcher:
            # Runtime state is preserved in memory during reload
            self._watcher.get_current_config()

    def get_config(self) -> Optional[ConfigSchema]:
        """Get the current configuration."""
        if self._watcher:
            return self._watcher.get_current_config()
        return None
