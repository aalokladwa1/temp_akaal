"""
akaalEngine.extensions.loading.module_source
============================================
Explicit Python module source loader for extensions.
Loads manifests from an explicit module path containing a get_manifest() callable or EXTENSION_MANIFEST attribute.
"""

from __future__ import annotations

import importlib
from typing import Optional

from akaalEngine.extensions.errors.taxonomy import ExtensionLoadingError
from akaalEngine.extensions.models.extension import ExtensionManifest


class ModuleExtensionSource:
    """
    Loads an ExtensionManifest from a specified Python module path.
    """

    @classmethod
    def load_from_module(cls, module_path: str) -> ExtensionManifest:
        try:
            mod = importlib.import_module(module_path)
        except Exception as exc:
            raise ExtensionLoadingError(
                f"Failed to import extension module '{module_path}': {exc}"
            ) from exc

        # Check get_manifest()
        if hasattr(mod, "get_manifest") and callable(mod.get_manifest):
            try:
                manifest = mod.get_manifest()
                if isinstance(manifest, ExtensionManifest):
                    return manifest
                raise ExtensionLoadingError(
                    f"Module '{module_path}' get_manifest() returned {type(manifest).__name__}, expected ExtensionManifest."
                )
            except Exception as exc:
                if isinstance(exc, ExtensionLoadingError):
                    raise
                raise ExtensionLoadingError(
                    f"Error invoking get_manifest() in '{module_path}': {exc}"
                ) from exc

        # Check EXTENSION_MANIFEST
        if hasattr(mod, "EXTENSION_MANIFEST"):
            manifest = getattr(mod, "EXTENSION_MANIFEST")
            if isinstance(manifest, ExtensionManifest):
                return manifest
            raise ExtensionLoadingError(
                f"Module '{module_path}' EXTENSION_MANIFEST is of type {type(manifest).__name__}, expected ExtensionManifest."
            )

        raise ExtensionLoadingError(
            f"Module '{module_path}' does not define 'get_manifest()' or 'EXTENSION_MANIFEST'."
        )
