"""
Akaal — Risk Item Model
=======================
Immutable dataclass representing an individual detected risk item.
"""

import hashlib
import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from akaal.risk.models.risk_taxonomy import RiskTaxonomyNode
from akaal.risk.models.severity import Severity
from akaal.risk.models.confidence import ConfidenceScore
from akaal.risk.models.evidence import EvidenceNode
from akaal.risk.models.canonical_reference import CanonicalReference
from akaal.risk.models.mitigation import MitigationStrategy


@dataclass(frozen=True)
class RiskItem:
    """Immutable Risk Item model."""
    risk_id: str
    domain: str
    category: str
    risk_type: str
    severity: Severity
    confidence: ConfidenceScore
    affected_objects: List[str] = field(default_factory=list)
    canonical_references: List[CanonicalReference] = field(default_factory=list)
    root_cause: str = ""
    impact: str = ""
    suggested_mitigations: List[MitigationStrategy] = field(default_factory=list)
    detection_engine: str = "RiskPlatform"
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    risk_fingerprint: str = ""

    def to_dict(self) -> Dict[str, Any]:
        d = {
            "risk_id": self.risk_id,
            "domain": self.domain,
            "category": self.category,
            "risk_type": self.risk_type,
            "severity": self.severity.value if hasattr(self.severity, "value") else str(self.severity),
            "confidence": self.confidence.to_dict(),
            "affected_objects": self.affected_objects,
            "canonical_references": [r.to_dict() for r in self.canonical_references],
            "root_cause": self.root_cause,
            "impact": self.impact,
            "suggested_mitigations": [m.to_dict() for m in self.suggested_mitigations],
            "detection_engine": self.detection_engine,
            "timestamp": self.timestamp,
            "risk_fingerprint": self.risk_fingerprint,
        }
        return d
