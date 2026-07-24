"""PluginRegistry: Manages active enterprise validation plugins and hot registration."""

import threading
from typing import Dict, List, Optional
from akaal.validation.core.interfaces import IPlugin
from akaal.validation.plugins.metadata import PluginMetadata


class PluginRegistry:
    """Thread-safe registry for managing enterprise plugins."""

    def __init__(self):
        self._plugins: Dict[str, IPlugin] = {}
        self._metadata: Dict[str, PluginMetadata] = {}
        self._lock = threading.RLock()

    def register_plugin(self, plugin: IPlugin, metadata: PluginMetadata) -> None:
        """Register a plugin instance with metadata."""
        with self._lock:
            self._plugins[plugin.plugin_name] = plugin
            self._metadata[plugin.plugin_name] = metadata

    def unregister_plugin(self, plugin_name: str) -> None:
        """Unregister a plugin by name."""
        with self._lock:
            self._plugins.pop(plugin_name, None)
            self._metadata.pop(plugin_name, None)

    def get_plugin(self, plugin_name: str) -> Optional[IPlugin]:
        """Retrieve plugin instance."""
        with self._lock:
            return self._plugins.get(plugin_name)

    def list_plugins(self) -> List[str]:
        """List active plugin names."""
        with self._lock:
            return list(self._plugins.keys())
