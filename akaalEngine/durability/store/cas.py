"""
State Compare-And-Swap (CAS) Coordinator for Authority #5 — Durability (DUR-005).
"""

from typing import Dict, Any
from akaalEngine.durability.models.state import StateRecord, StateVersion
from akaalEngine.durability.store.base import BaseDurableStorageBackend


class StateCasCoordinator:
    """Coordinates atomic Compare-And-Swap mutations over a DurableStorageBackend."""

    def __init__(self, backend: BaseDurableStorageBackend) -> None:
        self.backend = backend

    def cas_update(self, key: str, namespace: str, expected_version: int, new_payload: Dict[str, Any]) -> StateVersion:
        """Executes compare-and-swap update or raises CASConflictError."""
        if hasattr(self.backend, "compare_and_swap"):
            return self.backend.compare_and_swap(key, namespace, expected_version, new_payload)
        
        # Fallback for backends without native CAS method
        curr = self.backend.get_state(key, namespace)
        if curr is None:
            if expected_version != 0:
                raise CASConflictError(f"CAS failed: key '{key}' does not exist.")
            rec = StateRecord(key=key, namespace=namespace, payload=new_payload, version=1)
            return self.backend.put_state(rec)
        else:
            if curr.version != expected_version:
                raise CASConflictError(f"CAS conflict: key '{key}' has version {curr.version}, expected {expected_version}.")
            rec = StateRecord(key=key, namespace=namespace, payload=new_payload, version=curr.version + 1)
            return self.backend.put_state(rec)
