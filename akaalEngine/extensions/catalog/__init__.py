"""
akaalEngine.extensions.catalog
==============================
Registry snapshots, thread-safe ExtensionRegistry, ownership governance, and transactional publication.
"""

from akaalEngine.extensions.catalog.snapshot import (
    RegistrySnapshot,
)
from akaalEngine.extensions.catalog.ownership import (
    OwnershipManager,
)
from akaalEngine.extensions.catalog.transaction import (
    ENGINE_VERSION,
    RegistrationTransaction,
)
from akaalEngine.extensions.catalog.registry import (
    ExtensionRegistry,
    default_extension_registry,
)

__all__ = [
    "RegistrySnapshot",
    "OwnershipManager",
    "ENGINE_VERSION",
    "RegistrationTransaction",
    "ExtensionRegistry",
    "default_extension_registry",
]
