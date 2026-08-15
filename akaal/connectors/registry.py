"""
AKAAL Universal Connector Registry (P4.1).
===========================================
Thread-safe, authoritative registry for all enterprise connector implementations,
manifests, and capability extension providers.
Guarantees duplicate prevention, thread-safe access, and fail-closed resolution.
"""

from typing import Dict, Any, List, Optional, Type
import threading
import logging

from akaal.connectors.taxonomy import ConnectorFamily, ConnectorRole
from akaal.connectors.manifest import UniversalCapabilityManifest
from akaal.connectors.contracts.base import IUniversalConnector

logger = logging.getLogger("akaal.connectors.registry")


class UniversalConnectorRegistry:
    """
    Central Authoritative Registry for all Universal Connectors (P4.1).
    Thread-safe and deterministic.
    """

    _INSTANCE: Optional["UniversalConnectorRegistry"] = None
    _LOCK = threading.RLock()

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._connectors: Dict[str, IUniversalConnector] = {}
        self._manifests: Dict[str, UniversalCapabilityManifest] = {}
        self._connector_classes: Dict[str, Type[IUniversalConnector]] = {}

    @classmethod
    def get_instance(cls) -> "UniversalConnectorRegistry":
        """Singleton accessor with thread-safe double-checked locking."""
        if cls._INSTANCE is None:
            with cls._LOCK:
                if cls._INSTANCE is None:
                    cls._INSTANCE = cls()
                    cls._INSTANCE._bootstrap_default_registry()
        return cls._INSTANCE

    def _bootstrap_default_registry(self) -> None:
        """Bootstraps default connector manifests and bridge adapters."""
        try:
            from akaal.connectors.bridge import register_canonical_bridge_connectors
            register_canonical_bridge_connectors(self)
        except Exception as exc:
            logger.warning("[UniversalConnectorRegistry] Bridge bootstrap notice: %s", exc)

    def register_connector(self, connector: IUniversalConnector) -> None:
        """Registers a live connector instance with authoritative manifest."""
        with self._lock:
            cid = connector.connector_id.lower().strip()
            manifest = connector.manifest
            self._connectors[cid] = connector
            self._manifests[cid] = manifest
            logger.info(f"[UniversalConnectorRegistry] Registered connector '{cid}' ({manifest.vendor_name}, {manifest.family.value}).")

    def register_manifest(self, manifest: UniversalCapabilityManifest) -> None:
        """Registers a capability manifest without requiring immediate live instantiation."""
        with self._lock:
            cid = manifest.connector_id.lower().strip()
            self._manifests[cid] = manifest
            logger.info(f"[UniversalConnectorRegistry] Registered capability manifest '{cid}' ({manifest.vendor_name}).")

    def get_connector(self, connector_id: str) -> Optional[IUniversalConnector]:
        """Retrieves connector instance by connector_id."""
        with self._lock:
            cid = connector_id.lower().strip()
            return self._connectors.get(cid)

    def get_manifest(self, connector_id: str) -> Optional[UniversalCapabilityManifest]:
        """Retrieves capability manifest by connector_id. Fails closed if not found."""
        with self._lock:
            cid = connector_id.lower().strip()
            return self._manifests.get(cid)

    def is_registered(self, connector_id: str) -> bool:
        """Returns True if connector or manifest is registered."""
        with self._lock:
            cid = connector_id.lower().strip()
            return cid in self._manifests or cid in self._connectors

    def list_connectors(self) -> List[str]:
        """Lists all registered connector IDs."""
        with self._lock:
            return sorted(list(self._manifests.keys()))

    def list_manifests(self, family: Optional[ConnectorFamily] = None, role: Optional[ConnectorRole] = None) -> List[Dict[str, Any]]:
        """Lists serialized capability manifests with optional family/role filtering."""
        with self._lock:
            results: List[Dict[str, Any]] = []
            for manifest in self._manifests.values():
                if family is not None and manifest.family != family:
                    continue
                if role is not None:
                    if role == ConnectorRole.SOURCE and not manifest.is_source_capable():
                        continue
                    if role == ConnectorRole.TARGET and not manifest.is_target_capable():
                        continue
                results.append(manifest.to_dict())
            return results

    def clear(self) -> None:
        """Clears all registrations (primarily for isolated test fixtures)."""
        with self._lock:
            self._connectors.clear()
            self._manifests.clear()
            self._connector_classes.clear()
