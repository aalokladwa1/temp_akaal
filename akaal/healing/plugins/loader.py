"""PluginLoader & PluginDiscovery for healing plugins."""

from typing import List


class PluginLoader:
    def __init__(self, registry=None):
        self.registry = registry


class PluginDiscovery:
    def discover_plugins(self) -> List[str]:
        return []
