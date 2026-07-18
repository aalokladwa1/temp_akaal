"""
Akaal — Canonical Reference Model
=================================
References canonical objects and canonical rule provenance inside RiskItem instances.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class CanonicalReference:
    canonical_id: str
    source_identifier: str
    object_type: str
    rule_provenance_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "canonical_id": self.canonical_id,
            "source_identifier": self.source_identifier,
            "object_type": self.object_type,
            "rule_provenance_id": self.rule_provenance_id,
        }
