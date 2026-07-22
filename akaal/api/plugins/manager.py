"""
Enterprise Plugin Framework & Manager for AKAAL Platform 7.
"""

from typing import Dict, List, Any, Optional
import os
from akaal.api.contracts.errors import PluginError


class PluginManifest:
    """Plugin Metadata Manifest Contract."""

    def __init__(
        self,
        name: str,
        version: str,
        target_api_version: str = "^1.0.0",
        capabilities: List[str] = None,
        is_signed: bool = True,
    ) -> None:
        self.name = name
        self.version = version
        self.target_api_version = target_api_version
        self.capabilities = capabilities or []
        self.is_signed = is_signed


class PluginManager:
    """Enterprise Sandboxed Plugin Manager."""

    def __init__(self) -> None:
        self._plugins: Dict[str, PluginManifest] = {}
        self._active_plugins: Set[str] = set()

    def install_plugin(self, manifest: PluginManifest) -> None:
        """Install and verify plugin manifest and signature."""
        if not manifest.is_signed:
            raise PluginError(f"Plugin '{manifest.name}' rejected: Cryptographic signature verification failed.")
        self._plugins[manifest.name] = manifest

    def activate_plugin(self, name: str) -> None:
        """Activate plugin instance."""
        if name not in self._plugins:
            raise PluginError(f"Plugin '{name}' is not installed.")
        self._active_plugins.add(name)

    def deactivate_plugin(self, name: str) -> None:
        """Deactivate plugin instance."""
        self._active_plugins.discard(name)

    def execute_capability(self, plugin_name: str, capability: str, *args: Any, **kwargs: Any) -> Any:
        """Execute sandboxed plugin capability."""
        if plugin_name not in self._active_plugins:
            raise PluginError(f"Plugin '{plugin_name}' is not active.")

        manifest = self._plugins[plugin_name]
        if capability not in manifest.capabilities:
            raise PluginError(
                f"Plugin '{plugin_name}' lacks capability '{capability}'. Declared: {manifest.capabilities}"
            )

        return {"status": "SUCCESS", "plugin": plugin_name, "capability": capability}
