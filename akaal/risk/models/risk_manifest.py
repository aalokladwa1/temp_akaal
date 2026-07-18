"""
Akaal — Expanded Risk Manifest
==============================
Expanded manifest artifact tracking component versions and model checksums for Risk Platform.
"""

import hashlib
import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict


@dataclass
class RiskManifest:
    manifest_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    risk_schema_version: str = "1.0.0"
    analyzer_registry_version: str = "1.0.0"
    scoring_version: str = "1.0.0"
    decoder_version: str = "1.0.0"
    rulebook_version: str = "1.0.0"
    canonical_schema_version: str = "1.0.0"
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    model_checksum: str = ""

    def compute_model_checksum(self, model_dict: Dict[str, Any]) -> str:
        s = json.dumps(model_dict, default=str, sort_keys=True)
        self.model_checksum = hashlib.sha256(s.encode("utf-8")).hexdigest()
        return self.model_checksum

    def to_dict(self) -> Dict[str, Any]:
        return {
            "manifest_id": self.manifest_id,
            "risk_schema_version": self.risk_schema_version,
            "analyzer_registry_version": self.analyzer_registry_version,
            "scoring_version": self.scoring_version,
            "decoder_version": self.decoder_version,
            "rulebook_version": self.rulebook_version,
            "canonical_schema_version": self.canonical_schema_version,
            "timestamp": self.timestamp,
            "model_checksum": self.model_checksum,
        }
