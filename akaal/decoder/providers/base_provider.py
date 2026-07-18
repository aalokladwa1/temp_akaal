"""
Akaal — Base Decoder Provider Interface
======================================
Passive BaseDecoderProvider interface representing Storage Model Families with Governance Metadata.
Providers supply mappings passively without generating SQL or mutating execution context.
"""

import hashlib
from abc import ABC, abstractmethod
from typing import Any, Dict, List
from akaal.decoder.registry.storage_hierarchy import StorageModel
from akaal.decoder.models.canonical_type import CanonicalType, CanonicalTypeFamily


class BaseDecoderProvider(ABC):
    """Abstract Decoder Provider plugin interface."""

    provider_id: str = "base_decoder_provider"
    provider_name: str = "Base Decoder Provider"
    semantic_version: str = "1.0.0"
    supported_storage_model: StorageModel = StorageModel.RELATIONAL
    supported_engine: str = "GENERIC"
    supported_engine_versions: List[str] = ["*"]
    supported_canonical_schema_version: str = "1.0.0"
    lifecycle_state: str = "ACTIVE"

    @abstractmethod
    def type_mappings(self) -> Dict[str, CanonicalType]:
        """Return data type normalization mapping."""

    def metadata(self) -> Dict[str, Any]:
        return {
            "provider_id": self.provider_id,
            "provider_name": self.provider_name,
            "semantic_version": self.semantic_version,
            "supported_storage_model": self.supported_storage_model.value if hasattr(self.supported_storage_model, "value") else str(self.supported_storage_model),
            "supported_engine": self.supported_engine,
            "supported_engine_versions": self.supported_engine_versions,
            "supported_canonical_schema_version": self.supported_canonical_schema_version,
            "lifecycle_state": self.lifecycle_state,
            "checksum": self.checksum(),
        }

    def checksum(self) -> str:
        raw = f"{self.provider_id}:{self.semantic_version}:{self.supported_engine}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def validate(self) -> bool:
        return True
