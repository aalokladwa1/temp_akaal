"""
AKAAL Platform 11 — Digital Certification Sealer.
"""

import datetime
import hashlib
import uuid
from akaal.trust_certification.domain.models import DigitalCertificationSeal
from akaal.trust_certification.domain.enums import CertificationSealStatus


class DigitalCertificationSealer:
    """Issues digital certification seals signed with SHA-256 cryptographic signatures."""

    def issue_seal(self, migration_id: str, trust_score_val: float) -> DigitalCertificationSeal:
        seal_id = f"seal-{uuid.uuid4().hex[:8]}"
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        signature = hashlib.sha256(f"{migration_id}:{trust_score_val}:{now}".encode('utf-8')).hexdigest()

        return DigitalCertificationSeal(
            seal_id=seal_id,
            target_migration_id=migration_id,
            seal_signature=signature,
            status=CertificationSealStatus.VALID,
            issued_at=now,
        )
