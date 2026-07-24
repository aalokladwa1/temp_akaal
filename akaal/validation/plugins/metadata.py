"""Plugin metadata, versioning, and dependency resolution."""

from typing import List, Dict, Any
from dataclasses import dataclass, field


@dataclass
class PluginVersion:
    """Semantic versioning representation for plugins."""

    major: int = 1
    minor: int = 0
    patch: int = 0

    def __str__(self) -> str:
        return f"{self.major}.{self.minor}.{self.patch}"


@dataclass
class PluginMetadata:
    """Metadata definition for enterprise validation plugins."""

    plugin_name: str
    version: PluginVersion = field(default_factory=PluginVersion)
    author: str = "Unknown"
    description: str = ""
    dependencies: List[str] = field(default_factory=list)
    supported_capabilities: List[str] = field(default_factory=list)
    entry_point: str = ""
    enabled: bool = True
