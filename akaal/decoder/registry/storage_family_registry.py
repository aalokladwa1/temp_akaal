"""
Akaal — Storage Family Registry
===============================
Registry for managing passive BaseDecoderProvider plugins across Storage Model Families.
"""

import threading
from typing import Any, Dict, List, Optional
from akaal.decoder.providers.base_provider import BaseDecoderProvider
from akaal.decoder.providers.relational_provider import RelationalDecoderProvider
from akaal.decoder.providers.document_provider import DocumentDecoderProvider
from akaal.decoder.providers.graph_provider import GraphDecoderProvider
from akaal.decoder.providers.vector_provider import VectorDecoderProvider
from akaal.decoder.providers.warehouse_provider import WarehouseDecoderProvider
from akaal.decoder.models.canonical_type import CanonicalType, OpaqueType


class StorageFamilyRegistry:
    """Registry for Storage Model Family decoder providers."""

    def __init__(self, auto_register_defaults: bool = True) -> None:
        self._lock = threading.RLock()
        self._providers: Dict[str, BaseDecoderProvider] = {}
        if auto_register_defaults:
            self._bootstrap_defaults()

    def _bootstrap_defaults(self) -> None:
        self.register(RelationalDecoderProvider())
        self.register(DocumentDecoderProvider())
        self.register(GraphDecoderProvider())
        self.register(VectorDecoderProvider())
        self.register(WarehouseDecoderProvider())

    def register(self, provider: BaseDecoderProvider) -> None:
        with self._lock:
            self._providers[provider.provider_id] = provider

    def unregister(self, provider_id: str) -> None:
        with self._lock:
            self._providers.pop(provider_id, None)

    def get_provider(self, provider_id: str) -> Optional[BaseDecoderProvider]:
        with self._lock:
            return self._providers.get(provider_id)

    def resolve_type(self, raw_vendor_type: str, vendor_engine: str = "GENERIC") -> CanonicalType:
        with self._lock:
            clean_type = raw_vendor_type.lower().strip()
            for p in self._providers.values():
                mappings = p.type_mappings()
                if clean_type in mappings:
                    return mappings[clean_type]
            return OpaqueType(raw_vendor_type, vendor_engine)

    def list_providers(self) -> List[Dict[str, Any]]:
        with self._lock:
            return [p.metadata() for p in self._providers.values()]

    def manifest(self) -> Dict[str, str]:
        with self._lock:
            return {p_id: p.semantic_version for p_id, p in self._providers.items()}
