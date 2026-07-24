"""PluginMetadata, PluginRegistry, PluginLoader, PluginDiscovery for healing plugins."""

import os
import glob
import threading
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from akaal.healing.core.interfaces import IHealingPlugin


@dataclass
class PluginMetadata:
    plugin_name: str
    version: str = "1.0.0"
    entry_point: str = ""


class PluginRegistry:
    def __init__(self):
        self._plugins: Dict[str, IHealingPlugin] = {}
        self._lock = threading.RLock()

    def register_plugin(self, plugin: IHealingPlugin, metadata: PluginMetadata) -> None:
        with self._lock:
            self._plugins[plugin.plugin_name] = plugin

    def get_plugin(self, name: str) -> Optional[IHealingPlugin]:
        with self._lock:
            return self._plugins.get(name)

    def list_plugins(self) -> List[str]:
        with self._lock:
            return list(self._plugins.keys())


class PluginLoader:
    def __init__(self, registry: Optional[PluginRegistry] = None):
        self.registry = registry or PluginRegistry()


class PluginDiscovery:
    def discover_plugins(self) -> List[str]:
        return []
