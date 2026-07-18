"""
Akaal — Canonical Type Registry
===============================
Registry for registered CanonicalType definitions.
"""

from typing import Dict, Optional
from akaal.decoder.models.canonical_type import CanonicalType, CanonicalTypeFamily


class CanonicalTypeRegistry:
    """Registry mapping vendor types to canonical types."""

    def __init__(self) -> None:
        self._registry: Dict[str, CanonicalType] = {}

    def register(self, vendor_type: str, canonical_type: CanonicalType) -> None:
        self._registry[vendor_type.lower()] = canonical_type

    def resolve(self, vendor_type: str) -> Optional[CanonicalType]:
        return self._registry.get(vendor_type.lower())
