"""Enterprise Plugin Architecture package."""

from akaal.validation.plugins.metadata import PluginMetadata, PluginVersion
from akaal.validation.plugins.registry import PluginRegistry
from akaal.validation.plugins.loader import PluginLoader
from akaal.validation.plugins.discovery import PluginDiscovery

__all__ = [
    "PluginMetadata",
    "PluginVersion",
    "PluginRegistry",
    "PluginLoader",
    "PluginDiscovery",
]
