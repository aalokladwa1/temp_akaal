"""
Akaal — Canonical Manifest & Provider Governance
================================================
Expanded manifest artifact with provider version governance and checksum verification.
"""

import hashlib
import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict


@dataclass
class CanonicalManifest:
    manifest_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    schema_version: str = "1.0.0"
    capability_model_version: str = "1.0.0"
    compatibility_matrix_version: str = "1.0.0"
    function_library_version: str = "1.0.0"
    expression_ast_version: str = "1.0.0"
    dependency_graph_version: str = "1.0.0"
    provider_versions: Dict[str, str] = field(default_factory=dict)
    decoder_version: str = "1.0.0"
    fingerprint_version: str = "1.0.0"
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    model_checksum: str = ""

    def compute_model_checksum(self, model_dict: Dict[str, Any]) -> str:
        s = json.dumps(model_dict, sort_keys=True)
        self.model_checksum = hashlib.sha256(s.encode("utf-8")).hexdigest()
        return self.model_checksum

    def to_dict(self) -> Dict[str, Any]:
        return {
            "manifest_id": self.manifest_id,
            "schema_version": self.schema_version,
            "capability_model_version": self.capability_model_version,
            "compatibility_matrix_version": self.compatibility_matrix_version,
            "function_library_version": self.function_library_version,
            "expression_ast_version": self.expression_ast_version,
            "dependency_graph_version": self.dependency_graph_version,
            "provider_versions": self.provider_versions,
            "decoder_version": self.decoder_version,
            "fingerprint_version": self.fingerprint_version,
            "timestamp": self.timestamp,
            "model_checksum": self.model_checksum,
        }
