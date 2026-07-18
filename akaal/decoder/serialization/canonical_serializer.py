"""
Akaal — Canonical Serializer
============================
Deterministic JSON, versioned export/import, and binary serialization for CanonicalMigrationModel.
Downstream modules consume serialized canonical artifacts without Python object dependencies.
"""

import json
from typing import Any, Dict
from akaal.decoder.models.canonical_migration_model import CanonicalMigrationModel


class CanonicalSerializer:
    """Deterministic serializer for CanonicalMigrationModel artifacts."""

    @staticmethod
    def serialize_json(model: CanonicalMigrationModel, indent: int = 2) -> str:
        d = model.to_dict()
        return json.dumps(d, sort_keys=True, indent=indent)

    @staticmethod
    def deserialize_json(json_str: str) -> CanonicalMigrationModel:
        d = json.loads(json_str)
        return CanonicalMigrationModel(
            schema_version=d.get("schema_version", "1.0.0"),
            model_version=d.get("model_version", "1.0.0"),
            generator_version=d.get("generator_version", "decoder-1.0.0"),
            model_signature=d.get("model_signature", "AKAAL-DECODER-SIG-V1"),
            sha256_checksum=d.get("sha256_checksum", ""),
            metadata=d.get("metadata", {}),
            capability_model=d.get("capability_model", {}),
            canonical_graph=d.get("canonical_graph", {}),
            semantic_mappings=d.get("semantic_mappings", {}),
            canonical_manifest=d.get("canonical_manifest", {}),
            decoder_metrics=d.get("decoder_metrics", {}),
            execution_trace=d.get("execution_trace", {}),
            diagnostics=d.get("diagnostics", []),
            lineage=d.get("lineage", {}),
        )
