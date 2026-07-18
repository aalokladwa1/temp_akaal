"""
Akaal — Canonical Migration Model
=================================
The single canonical, immutable, versioned, checksum-protected output artifact produced by Decoder.
Consumed exclusively by downstream intelligence modules (Risk, Planner, Advisor, Enterprise Intelligence).
"""

import json
import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class CanonicalMigrationModel:
    """
    Immutable, versioned CanonicalMigrationModel artifact.
    Single public output produced by Decoder Platform.
    """
    schema_version: str = "1.0.0"
    model_version: str = "1.0.0"
    generator_version: str = "decoder-1.0.0"
    model_signature: str = "AKAAL-DECODER-SIG-V1"
    sha256_checksum: str = ""

    metadata: Dict[str, Any] = field(default_factory=dict)
    capability_model: Dict[str, Any] = field(default_factory=dict)
    canonical_graph: Dict[str, Any] = field(default_factory=dict)
    semantic_mappings: Dict[str, Any] = field(default_factory=dict)
    canonical_manifest: Dict[str, Any] = field(default_factory=dict)
    decoder_metrics: Dict[str, Any] = field(default_factory=dict)
    execution_trace: Dict[str, Any] = field(default_factory=dict)
    diagnostics: List[Dict[str, Any]] = field(default_factory=list)
    lineage: Dict[str, Any] = field(default_factory=dict)

    def compute_sha256_checksum(self) -> str:
        d = self.to_dict()
        d.pop("sha256_checksum", None)
        canonical = json.dumps(d, sort_keys=True)
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    def to_dict(self) -> Dict[str, Any]:
        res = {
            "schema_version": self.schema_version,
            "model_version": self.model_version,
            "generator_version": self.generator_version,
            "model_signature": self.model_signature,
            "sha256_checksum": self.sha256_checksum,
            "metadata": self.metadata,
            "capability_model": self.capability_model,
            "canonical_graph": self.canonical_graph,
            "semantic_mappings": self.semantic_mappings,
            "canonical_manifest": self.canonical_manifest,
            "decoder_metrics": self.decoder_metrics,
            "execution_trace": self.execution_trace,
            "diagnostics": self.diagnostics,
            "lineage": self.lineage,
        }
        if not res["sha256_checksum"]:
            canonical = json.dumps(res, sort_keys=True)
            res["sha256_checksum"] = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        return res

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)
