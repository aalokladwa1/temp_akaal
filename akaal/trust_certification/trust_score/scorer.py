"""
AKAAL Platform 11 — Migration Trust Scorer.
"""

import datetime
from akaal.trust_certification.domain.models import MigrationTrustScore
from akaal.trust_certification.domain.enums import TrustGrade


class MigrationTrustScorer:
    """Calculates overall Migration Trust Score (0.0 to 100.0) and assigns enterprise audit grade."""

    def compute_trust_score(self, target_migration_id: str, integrity_pct: float = 100.0, reliability_pct: float = 100.0) -> MigrationTrustScore:
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        score = round((integrity_pct * 0.6) + (reliability_pct * 0.4), 2)

        if score >= 99.0:
            grade = TrustGrade.GRADE_AAA
        elif score >= 90.0:
            grade = TrustGrade.GRADE_AA
        elif score >= 75.0:
            grade = TrustGrade.GRADE_A
        else:
            grade = TrustGrade.UNTRUSTED

        return MigrationTrustScore(
            target_migration_id=target_migration_id,
            trust_score=score,
            grade=grade,
            calculated_at=now,
        )
