"""PluginMetadata for healing plugins."""

from dataclasses import dataclass


@dataclass
class PluginMetadata:
    plugin_name: str
    version: str = "1.0.0"
    entry_point: str = ""
