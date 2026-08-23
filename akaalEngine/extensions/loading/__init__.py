"""
akaalEngine.extensions.loading
==============================
Controlled extension loading from explicit modules and entry points, with truthful isolation reporting.
"""

from akaalEngine.extensions.loading.isolation import IsolationManager
from akaalEngine.extensions.loading.module_source import ModuleExtensionSource
from akaalEngine.extensions.loading.entry_point_source import EntryPointExtensionSource
from akaalEngine.extensions.loading.loader import (
    ExtensionLoader,
    default_extension_loader,
)

__all__ = [
    "IsolationManager",
    "ModuleExtensionSource",
    "EntryPointExtensionSource",
    "ExtensionLoader",
    "default_extension_loader",
]
