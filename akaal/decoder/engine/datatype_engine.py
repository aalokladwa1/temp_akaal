"""
Akaal — Datatype Normalization Engine
=====================================
Single-responsibility engine converting vendor database data types to CanonicalType algebra.
"""

from typing import Dict, Any, Optional
from akaal.decoder.models.canonical_type import CanonicalType, CanonicalTypeFamily, OpaqueType
from akaal.decoder.models.decoder_context import DecoderContext
from akaal.decoder.registry.storage_family_registry import StorageFamilyRegistry


class DatatypeEngine:
    """Normalizes vendor data types to CanonicalType algebra."""

    def __init__(self, registry: Optional[StorageFamilyRegistry] = None) -> None:
        self.registry = registry or StorageFamilyRegistry(auto_register_defaults=True)

    def normalize_datatype(self, raw_type: str, vendor_engine: str = "GENERIC") -> CanonicalType:
        if not raw_type:
            return OpaqueType("UNKNOWN", vendor_engine)
        return self.registry.resolve_type(raw_type, vendor_engine)
