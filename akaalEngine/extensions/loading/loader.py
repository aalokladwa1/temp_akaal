"""
akaalEngine.extensions.loading.loader
=====================================
Coordinates explicit loading from modules, package entry points, and in-memory bundles.
"""

from __future__ import annotations

from typing import Optional, Sequence

from akaalEngine.extensions.loading.entry_point_source import EntryPointExtensionSource
from akaalEngine.extensions.loading.isolation import IsolationManager
from akaalEngine.extensions.loading.module_source import ModuleExtensionSource
from akaalEngine.extensions.models.extension import ExtensionManifest


class ExtensionLoader:
    """
    Coordinates discovery and loading of ExtensionManifest instances.
    """

    @classmethod
    def load_from_module(cls, module_path: str) -> ExtensionManifest:
        manifest = ModuleExtensionSource.load_from_module(module_path)
        # Verify isolation mode
        effective_iso = IsolationManager.verify_isolation_mode(
            manifest.isolation_mode,
            manifest.trust_tier,
        )
        return manifest

    @classmethod
    def discover_entry_points(cls, group: Optional[str] = None) -> Sequence[ExtensionManifest]:
        if group:
            return EntryPointExtensionSource.discover_entry_points(group=group)
        return EntryPointExtensionSource.discover_entry_points()


default_extension_loader = ExtensionLoader()
