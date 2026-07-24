"""
AKAAL Platform 11 — Compliance Evidence Packager.
"""

from typing import List, Dict, Any
import datetime
import hashlib
import json
import uuid
from akaal.trust_certification.domain.models import ComplianceEvidencePackage


class ComplianceEvidencePackager:
    """Assembles cryptographically hashed compliance evidence packages for enterprise audit."""

    def assemble_package(self, migration_id: str, evidence_items: List[Dict[str, Any]]) -> ComplianceEvidencePackage:
        pkg_id = f"pkg-{uuid.uuid4().hex[:8]}"
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        ser = json.dumps(evidence_items, sort_keys=True)
        pkg_hash = hashlib.sha256(ser.encode('utf-8')).hexdigest()

        return ComplianceEvidencePackage(
            package_id=pkg_id,
            target_migration_id=migration_id,
            evidence_items=evidence_items,
            package_hash=pkg_hash,
            created_at=now,
        )
