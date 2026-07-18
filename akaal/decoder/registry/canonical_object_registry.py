"""
Akaal — Canonical Object Registry
=================================
Repository holding normalized CanonicalObject instances.
"""

from typing import Dict, List, Optional
from akaal.decoder.models.canonical_object import CanonicalObject


class CanonicalObjectRegistry:
    """Registry for normalized CanonicalObjects."""

    def __init__(self) -> None:
        self._objects: Dict[str, CanonicalObject] = {}

    def register(self, obj: CanonicalObject) -> None:
        self._objects[obj.identity.canonical_id] = obj

    def get(self, canonical_id: str) -> Optional[CanonicalObject]:
        return self._objects.get(canonical_id)

    def list_all(self) -> List[CanonicalObject]:
        return list(self._objects.values())
