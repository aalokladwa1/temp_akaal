"""
AKAAL Platform 5 — Optimistic Concurrency Controller (OCC)

Validates version sequence consistency and detects concurrent schema modification collisions.
"""

from typing import Dict
import threading

from akaal.schema.domain.errors import VersionConflictError


class OptimisticConcurrencyController:
    """Thread-safe OCC version tracking engine."""

    def __init__(self) -> None:
        self._mutex = threading.RLock()
        self._entity_versions: Dict[str, int] = {}

    def get_version(self, entity_key: str) -> int:
        with self._mutex:
            return self._entity_versions.get(entity_key, 1)

    def validate_and_increment(self, entity_key: str, expected_version: int) -> int:
        with self._mutex:
            current_version = self._entity_versions.get(entity_key, 1)
            if current_version != expected_version:
                raise VersionConflictError(
                    message=f"OCC conflict for '{entity_key}': expected version {expected_version}, actual is {current_version}.",
                    recovery_recommendation="Refresh schema snapshot and re-apply schema evolution changes."
                )
            new_version = current_version + 1
            self._entity_versions[entity_key] = new_version
            return new_version
