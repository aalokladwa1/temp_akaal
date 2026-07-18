"""
Akaal — Storage Model Hierarchy
===============================
Hierarchy: StorageModel -> StorageFamily -> StorageEngine -> Provider -> VersionAdapter
Decouples Decoder core from specific engine versions.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class StorageModel(str, Enum):
    RELATIONAL = "RELATIONAL"
    DOCUMENT = "DOCUMENT"
    GRAPH = "GRAPH"
    KEYVALUE = "KEYVALUE"
    TIMESERIES = "TIMESERIES"
    WAREHOUSE = "WAREHOUSE"
    LAKEHOUSE = "LAKEHOUSE"
    STREAMING = "STREAMING"
    SEARCH = "SEARCH"
    VECTOR = "VECTOR"
    OBJECT = "OBJECT"
    LEGACY = "LEGACY"
    CUSTOM = "CUSTOM"


@dataclass
class VersionAdapter:
    engine_version: str
    feature_flags: Dict[str, bool] = field(default_factory=dict)
    type_overrides: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "engine_version": self.engine_version,
            "feature_flags": self.feature_flags,
            "type_overrides": self.type_overrides,
        }


@dataclass
class StorageEngine:
    engine_name: str
    storage_model: StorageModel
    supported_versions: List[str] = field(default_factory=list)
    version_adapters: Dict[str, VersionAdapter] = field(default_factory=dict)

    def get_adapter(self, version: str) -> VersionAdapter:
        return self.version_adapters.get(version, VersionAdapter(engine_version=version))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "engine_name": self.engine_name,
            "storage_model": self.storage_model.value if hasattr(self.storage_model, "value") else str(self.storage_model),
            "supported_versions": self.supported_versions,
            "version_adapters": {k: v.to_dict() for k, v in self.version_adapters.items()},
        }
