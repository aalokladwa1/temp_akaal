"""
AKAAL Platform 10 — Recovery Strategy Recommender.
"""

import uuid
from akaal.recovery_intelligence.domain.models import RecoveryStrategy
from akaal.recovery_intelligence.domain.enums import RecoveryStrategyType


class RecoveryStrategyRecommender:
    """Recommends optimal recovery strategy (Checkpoint Resume vs Rollback Replay)."""

    def recommend_strategy(self, migration_id: str, checkpoint_available: bool = True) -> RecoveryStrategy:
        st_type = RecoveryStrategyType.CHECKPOINT_RESUME if checkpoint_available else RecoveryStrategyType.ROLLBACK_AND_REPLAY
        steps = [
            "Validate last consistent checkpoint",
            "Re-establish CDC stream",
            "Resume migration execution",
        ] if checkpoint_available else [
            "Roll back target schema state",
            "Re-run full baseline snapshot",
        ]

        return RecoveryStrategy(
            strategy_id=f"stg-{uuid.uuid4().hex[:8]}",
            target_migration_id=migration_id,
            strategy_type=st_type,
            steps=steps,
            estimated_cost_units=10.0 if checkpoint_available else 100.0,
        )
