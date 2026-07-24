"""
AKAAL Platform 10 — Recovery Point Advisor.
"""

import datetime
import uuid
from akaal.recovery_intelligence.domain.models import RecoveryPointRecommendation


class RecoveryPointAdvisor:
    """Recommends optimal recovery points (RPO) based on migration checkpoints."""

    def recommend_recovery_point(self, migration_id: str, checkpoint_id: str, lag_seconds: float = 2.5) -> RecoveryPointRecommendation:
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        return RecoveryPointRecommendation(
            recommendation_id=f"rpo-{uuid.uuid4().hex[:8]}",
            target_migration_id=migration_id,
            recommended_checkpoint_id=checkpoint_id,
            rpo_lag_seconds=lag_seconds,
            data_loss_risk_score=min(10.0, lag_seconds * 0.1),
            generated_at=now,
        )
