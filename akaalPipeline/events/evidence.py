"""akaalPipeline.events.evidence
===============================
Fingerprinted evidence collection for compliance and validation artifacts.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Mapping
from akaalPipeline.contracts.serialization import canonical_fingerprint, canonical_serialize


@dataclass(frozen=True)
class EvidenceRecord:
    evidence_id: str
    evidence_type: str
    fingerprint: str
    details: Mapping[str, Any]
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class EvidenceCollector:
    @staticmethod
    def collect_evidence(evidence_id: str, evidence_type: str, details: Mapping[str, Any]) -> EvidenceRecord:
        fp = canonical_fingerprint(details)
        return EvidenceRecord(
            evidence_id=evidence_id,
            evidence_type=evidence_type,
            fingerprint=fp,
            details=dict(details),
        )
