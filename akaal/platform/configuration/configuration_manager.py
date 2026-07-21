"""
AKAAL Platform Part 6 - Dynamic Configuration Subsystem.
Zero-Downtime Configuration Registry, Feature Flags, and Runtime Overrides.
"""

from dataclasses import dataclass, field
import threading
import time
from typing import Any, Dict, List, Optional


@dataclass
class ConfigItem:
    key: str
    value: Any
    version: int
    updated_at_ms: int


class ConfigurationRegistry:
    """Versioned thread-safe configuration repository."""

    def __init__(self) -> None:
        self._items: Dict[str, ConfigItem] = {}
        self._lock = threading.Lock()

    def set(self, key: str, value: Any) -> ConfigItem:
        with self._lock:
            prev = self._items.get(key)
            version = (prev.version + 1) if prev else 1
            item = ConfigItem(
                key=key,
                value=value,
                version=version,
                updated_at_ms=int(time.time() * 1000),
            )
            self._items[key] = item
            return item

    def get(self, key: str, default: Any = None) -> Any:
        with self._lock:
            item = self._items.get(key)
            return item.value if item else default


class FeatureFlags:
    """Dynamic feature flag switchboard."""

    def __init__(self, registry: ConfigurationRegistry) -> None:
        self.registry = registry

    def is_enabled(self, feature_name: str, default: bool = False) -> bool:
        val = self.registry.get(f"feature.{feature_name}", default)
        return bool(val)

    def enable_feature(self, feature_name: str) -> None:
        self.registry.set(f"feature.{feature_name}", True)

    def disable_feature(self, feature_name: str) -> None:
        self.registry.set(f"feature.{feature_name}", False)


class ConfigurationManager:
    """Master controller managing dynamic hot-reloading configurations and feature flags."""

    def __init__(self) -> None:
        self.registry = ConfigurationRegistry()
        self.feature_flags = FeatureFlags(self.registry)

    def get_config(self, key: str, default: Any = None) -> Any:
        return self.registry.get(key, default)

    def set_config(self, key: str, value: Any) -> ConfigItem:
        return self.registry.set(key, value)
