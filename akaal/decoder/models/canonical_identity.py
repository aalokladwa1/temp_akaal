"""
Akaal — Universal Object Identity
=================================
Stable, deterministic identity model for all normalized canonical objects.
"""

import uuid
import hashlib
from dataclasses import dataclass, field
from typing import Any, Dict


@dataclass
class CanonicalIdentity:
    """Universal Object Identity model."""
    canonical_id: str = ""
    source_identifier: str = ""
    fingerprint: str = ""
    checksum: str = ""
    origin: str = "DECODER_NORMALIZATION"
    lineage_id: str = ""

    def __post_init__(self):
        if self.source_identifier:
            if not self.canonical_id:
                self.canonical_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, self.source_identifier))
            if not self.lineage_id:
                self.lineage_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"lineage:{self.source_identifier}"))
        else:
            if not self.canonical_id:
                self.canonical_id = str(uuid.uuid4())
            if not self.lineage_id:
                self.lineage_id = str(uuid.uuid4())

    def compute_identity_hash(self) -> str:
        raw = f"{self.source_identifier}:{self.origin}"
        self.checksum = hashlib.sha256(raw.encode("utf-8")).hexdigest()
        return self.checksum

    def to_dict(self) -> Dict[str, Any]:
        return {
            "canonical_id": self.canonical_id,
            "source_identifier": self.source_identifier,
            "fingerprint": self.fingerprint,
            "checksum": self.checksum,
            "origin": self.origin,
            "lineage_id": self.lineage_id,
        }
