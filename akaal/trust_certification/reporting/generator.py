"""
AKAAL Platform 11 — Enterprise Certification Generator.
"""

import datetime
import uuid
from akaal.trust_certification.domain.models import EnterpriseCertificationReport, MigrationTrustScore


class EnterpriseCertificationGenerator:
    """Generates official enterprise certification reports and verification certificates."""

    def generate_certificate(self, trust_score: MigrationTrustScore, certified_by: str = "AKAAL_AUTOMATED_CERTIFIER") -> EnterpriseCertificationReport:
        rpt_id = f"cert-{uuid.uuid4().hex[:8]}"
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        uri = f"https://cert.akaal.io/v1/{trust_score.target_migration_id}/{rpt_id}"

        return EnterpriseCertificationReport(
            report_id=rpt_id,
            target_migration_id=trust_score.target_migration_id,
            trust_score=trust_score.trust_score,
            grade=trust_score.grade,
            certified_by=certified_by,
            issued_at=now,
            certificate_uri=uri,
        )
