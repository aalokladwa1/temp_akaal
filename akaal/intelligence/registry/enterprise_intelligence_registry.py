"""
AKAAL Enterprise Intelligence Platform — Registry Subsystem
============================================================
Thread-safe, frozen-lifecycle plugin registry for Platform 2 strategic analyzers.
"""

import importlib
import pkgutil
import threading
from typing import Any, Dict, List, Optional, Tuple, Type


class EnterpriseIntelligenceRegistryError(Exception):
    """Exception raised for errors in EnterpriseIntelligenceRegistry operations."""
    pass


class EnterpriseIntelligenceRegistry:
    """
    Thread-safe plugin registry for discovering, registering, and retrieving
    Platform 2 strategic intelligence analyzers.

    Features:
    - Thread-safe state modifications & lookups via threading.RLock().
    - Lifecycle freezing (freeze/unfreeze/is_frozen) to lock registration state during pipeline runs.
    - Duplicate registration protection & deterministic name-sorted analyzer listing.
    - Analyzer metadata storage & dynamic package auto-discovery.
    """

    def __init__(self) -> None:
        self._analyzers: Dict[str, Any] = {}
        self._metadata: Dict[str, Dict[str, Any]] = {}
        self._frozen: bool = False
        self._lock: threading.RLock = threading.RLock()

    def register(
        self,
        name: str,
        analyzer_cls_or_instance: Any,
        metadata: Optional[Dict[str, Any]] = None,
        overwrite: bool = False,
    ) -> None:
        """
        Registers an intelligence analyzer with optional metadata.

        Raises:
            EnterpriseIntelligenceRegistryError: If registry is frozen, name is invalid,
                                                  or duplicate name exists without overwrite=True.
        """
        if not name or not isinstance(name, str):
            raise EnterpriseIntelligenceRegistryError("Analyzer name must be a non-empty string.")

        if analyzer_cls_or_instance is None:
            raise EnterpriseIntelligenceRegistryError("Cannot register a None analyzer.")

        with self._lock:
            if self._frozen:
                raise EnterpriseIntelligenceRegistryError(
                    f"Cannot register '{name}': Registry is frozen."
                )

            if name in self._analyzers and not overwrite:
                raise EnterpriseIntelligenceRegistryError(
                    f"Analyzer '{name}' is already registered. Use overwrite=True to replace."
                )

            self._analyzers[name] = analyzer_cls_or_instance
            self._metadata[name] = dict(metadata) if metadata else {}

    def unregister(self, name: str) -> None:
        """
        Unregisters an analyzer by name.

        Raises:
            EnterpriseIntelligenceRegistryError: If registry is frozen or analyzer is not registered.
        """
        with self._lock:
            if self._frozen:
                raise EnterpriseIntelligenceRegistryError(
                    f"Cannot unregister '{name}': Registry is frozen."
                )

            if name not in self._analyzers:
                raise EnterpriseIntelligenceRegistryError(
                    f"Cannot unregister '{name}': Analyzer is not registered."
                )

            del self._analyzers[name]
            self._metadata.pop(name, None)

    def get(self, name: str) -> Optional[Any]:
        """
        Retrieves a registered analyzer by name. Returns None if absent.
        """
        with self._lock:
            return self._analyzers.get(name)

    def exists(self, name: str) -> bool:
        """
        Checks if an analyzer is registered by name.
        """
        with self._lock:
            return name in self._analyzers

    def list(self) -> List[str]:
        """
        Returns a deterministically sorted list of registered analyzer names.
        """
        with self._lock:
            return sorted(list(self._analyzers.keys()))

    def get_metadata(self, name: str) -> Dict[str, Any]:
        """
        Retrieves metadata associated with a registered analyzer.
        """
        with self._lock:
            return dict(self._metadata.get(name, {}))

    def clear(self) -> None:
        """
        Clears all registered analyzers and metadata.

        Raises:
            EnterpriseIntelligenceRegistryError: If registry is frozen.
        """
        with self._lock:
            if self._frozen:
                raise EnterpriseIntelligenceRegistryError(
                    "Cannot clear registry: Registry is frozen."
                )
            self._analyzers.clear()
            self._metadata.clear()

    def freeze(self) -> None:
        """
        Freezes the registry lifecycle, blocking future register/unregister/clear calls.
        """
        with self._lock:
            self._frozen = True

    def unfreeze(self) -> None:
        """
        Unfreezes the registry lifecycle, restoring mutable registration state.
        """
        with self._lock:
            self._frozen = False

    def is_frozen(self) -> bool:
        """
        Returns True if the registry lifecycle is currently frozen.
        """
        with self._lock:
            return self._frozen

    def discover_analyzers(self, package_path: str = "akaal.intelligence.analyzers") -> int:
        """
        Dynamically discovers and registers analyzers from a Python package directory.
        Returns the count of newly discovered analyzers.
        """
        with self._lock:
            if self._frozen:
                raise EnterpriseIntelligenceRegistryError(
                    "Cannot discover analyzers: Registry is frozen."
                )

            discovered_count = 0
            try:
                pkg = importlib.import_module(package_path)
            except ImportError as ex:
                raise EnterpriseIntelligenceRegistryError(
                    f"Failed to import package '{package_path}': {ex}"
                )

            if hasattr(pkg, "__path__"):
                for _, modname, ispkg in pkgutil.iter_modules(pkg.__path__):
                    if not ispkg and not modname.startswith("_"):
                        full_mod_name = f"{package_path}.{modname}"
                        try:
                            mod = importlib.import_module(full_mod_name)
                            for attr_name in dir(mod):
                                if attr_name.endswith("Analyzer") and not attr_name.startswith("Base"):
                                    attr_val = getattr(mod, attr_name)
                                    if isinstance(attr_val, type):
                                        reg_name = attr_name.lower().replace("analyzer", "")
                                        if reg_name not in self._analyzers:
                                            self._analyzers[reg_name] = attr_val
                                            self._metadata[reg_name] = {"module": full_mod_name}
                                            discovered_count += 1
                        except Exception:
                            continue

            return discovered_count
