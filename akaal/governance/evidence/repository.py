"""
AKAAL Platform 6 — Governance Evidence Repository.
"""

from typing import Dict, Optional, List
import datetime
import hashlib
import uuid

from akaal.governance.domain.models import EvidenceArtifact


class EvidenceRepository:
    """Stores supporting governance evidence artifacts, review notes, and cryptographic proofs."""

    def __init__(self) -> None:
        self._artifacts: Dict[str, EvidenceArtifact] = {}

    def store_evidence(self, artifact_type: str, storage_uri: str, raw_content: bytes) -> EvidenceArtifact:
        evidence_id = f"evd-{uuid.uuid4().hex[:8]}"
        content_hash = hashlib.sha256(raw_content).hexdigest()
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()

        artifact = EvidenceArtifact(
            evidence_id=evidence_id,
            artifact_type=artifact_type,
            storage_uri=storage_uri,
            content_hash=content_hash,
            created_at=now,
        )
        self._artifacts[evidence_id] = artifact
        return artifact

    def get_evidence(self, evidence_id: str) -> Optional[EvidenceArtifact]:
        return self._artifacts.get(evidence_id)
