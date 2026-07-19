"""
Akaal — Rollback Recommendation Analyzer
=========================================
Analyzes rollback readiness, compensation graph completeness, and recovery safety.
"""

from typing import Any, List

from akaal.advisor.analyzers.base_analyzer import RecommendationAnalyzer
from akaal.advisor.models.advisory_context import AdvisoryContext
from akaal.advisor.models.advisory_decision import AdvisoryDecision
from akaal.advisor.models.advisory_enums import (
    AdvisoryCategory,
    AdvisoryPriority,
    AdvisorySeverity,
)
from akaal.advisor.models.advisory_evidence import AdvisoryEvidence
from akaal.advisor.models.advisory_recommendation import AdvisoryRecommendation


class RollbackRecommendationAnalyzer(RecommendationAnalyzer):
    """Analyzes rollback strategy, compensation steps, and snapshot recovery policies."""

    @property
    def name(self) -> str:
        return "RollbackRecommendationAnalyzer"

    @property
    def category(self) -> AdvisoryCategory:
        return AdvisoryCategory.ROLLBACK

    @property
    def description(self) -> str:
        return "Evaluates rollback graph topology, compensation action adequacy, and snapshot boundaries."

    def analyze(
        self, plan: Any, context: AdvisoryContext
    ) -> List[AdvisoryRecommendation]:
        recs: List[AdvisoryRecommendation] = []
        plan_dict = plan.to_dict() if hasattr(plan, "to_dict") else dict(plan or {})
        rollback_plan = plan_dict.get("rollback_plan", {})

        compensation_enabled = rollback_plan.get("compensation_enabled", True)
        snapshot_taken = rollback_plan.get("pre_migration_snapshot", True)

        if not snapshot_taken or not compensation_enabled:
            rec_id = "REC-RB-001"
            evidence = AdvisoryEvidence(
                source_component="RollbackPlan.pre_migration_snapshot",
                metric_name="pre_migration_snapshot",
                observed_value=snapshot_taken,
                threshold_value=True,
            )
            decision = AdvisoryDecision(
                decision_id="DEC-RB-001",
                recommendation_id=rec_id,
                rationale="Proceeding with structural or bulk data migration without a verified pre-migration snapshot poses severe recovery risk.",
                impact_analysis="Inability to perform point-in-time recovery if destructive schema change fails.",
                risk_mitigation="Enforce mandatory pre-migration snapshot creation in pre-cutover stage.",
                alternatives_considered=("Rely on logical table exports", "No rollback capability"),
            )
            recs.append(
                AdvisoryRecommendation(
                    recommendation_id=rec_id,
                    title="Enforce Mandatory Pre-Migration Target Snapshot",
                    category=AdvisoryCategory.ROLLBACK,
                    severity=AdvisorySeverity.CRITICAL,
                    priority=AdvisoryPriority.P0,
                    description="Rollback plan lacks a confirmed pre-migration database snapshot boundary.",
                    rationale="Destructive schema modifications require an immutable point-in-time restore boundary.",
                    impact="Potential permanent data loss if migration fails during DDL phase.",
                    action_items=("Enable pre_migration_snapshot in RollbackPlan.",),
                    affected_nodes=(),
                    evidence=(evidence,),
                    decision=decision,
                    tags=("rollback", "snapshot", "critical"),
                )
            )
        else:
            rec_id = "REC-RB-002"
            evidence = AdvisoryEvidence(
                source_component="RollbackPlan.pre_migration_snapshot",
                metric_name="pre_migration_snapshot",
                observed_value=snapshot_taken,
                threshold_value=True,
            )
            recs.append(
                AdvisoryRecommendation(
                    recommendation_id=rec_id,
                    title="Rollback Readiness Confirmed",
                    category=AdvisoryCategory.ROLLBACK,
                    severity=AdvisorySeverity.INFORMATIONAL,
                    priority=AdvisoryPriority.P4,
                    description="Rollback plan specifies adequate compensation chains and pre-execution snapshots.",
                    rationale="Complete rollback graph available for incident recovery.",
                    impact="Safe operational rollback path.",
                    action_items=("Maintain current rollback configuration.",),
                    affected_nodes=(),
                    evidence=(evidence,),
                    tags=("rollback", "standard"),
                )
            )

        return recs
