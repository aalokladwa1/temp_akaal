"""
akaalEngine.schema.core.provenance
==================================
Deterministic SHA-256 provenance fingerprinting for schema models, mappings, and compilation outputs.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping

from akaalEngine.schema.ddl.emitter import StagedDDLPackage
from akaalEngine.schema.models.mapping import CompiledSchemaMapping
from akaalEngine.schema.models.schema import CanonicalSchemaModel


class DeterministicSchemaProvenanceHasher:
    """Computes reproducible SHA-256 fingerprints across canonical schema artifacts."""

    @classmethod
    def hash_dict(cls, data: Mapping[str, Any]) -> str:
        """Serializes dictionary to sorted JSON and computes SHA-256."""
        raw = json.dumps(data, sort_keys=True, ensure_ascii=True, default=str)
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    @classmethod
    def compute_model_fingerprint(cls, model: CanonicalSchemaModel) -> str:
        """Computes deterministic fingerprint for CanonicalSchemaModel."""
        return cls.hash_dict(model.to_dict())

    @classmethod
    def compute_mapping_fingerprint(cls, mapping: CompiledSchemaMapping) -> str:
        """Computes deterministic fingerprint for CompiledSchemaMapping."""
        return cls.hash_dict(mapping.to_dict())

    @classmethod
    def compute_ddl_fingerprint(cls, package: StagedDDLPackage) -> str:
        """Computes deterministic fingerprint for generated StagedDDLPackage."""
        return cls.hash_dict(package.to_dict())

    @classmethod
    def compute_compilation_provenance(
        cls,
        source_model_hash: str,
        mapping_hash: str,
        ddl_package_hash: str,
        target_engine: str,
        target_version: str = "default",
    ) -> str:
        """Computes composite provenance signature for an entire compilation run."""
        combined = f"{source_model_hash}:{mapping_hash}:{ddl_package_hash}:{target_engine.upper()}:{target_version}"
        return hashlib.sha256(combined.encode("utf-8")).hexdigest()
