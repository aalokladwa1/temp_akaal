"""
Akaal — Checkpoint Recommendation Analyzer
============================================
Analyzes checkpoint frequency, state persistence policies, and Recovery Point Objectives (RPO).
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


class CheckpointRecommendationAnalyzer(RecommendationAnalyzer):
    """Analyzes checkpoint planning and state recovery strategies."""

    @property
    def name(self) -> str:
        return "CheckpointRecommendationAnalyzer"

    @property
    def category(self) -> AdvisoryCategory:
        return AdvisoryCategory.CHECKPOINT

    @property
    def description(self) -> str:
        return "Evaluates checkpoint frequency, state persistence durability, and restartability."

    def analyze(
        self, plan: Any, context: AdvisoryContext
    ) -> List[AdvisoryRecommendation]:
        recs: List[AdvisoryRecommendation] = []
        plan_dict = plan.to_dict() if hasattr(plan, "to_dict") else dict(plan or {})
        checkpoint_plan = plan_dict.get("checkpoint_plan", {})

        checkpoints_enabled = checkpoint_plan.get("enabled", True)
        interval_records = checkpoint_plan.get("interval_records", 50000)

        if not checkpoints_enabled or interval_records > 100000:
            rec_id = "REC-CHK-001"
            evidence = AdvisoryEvidence(
                source_component="CheckpointPlan.interval_records",
                metric_name="interval_records",
                observed_value=interval_records,
                threshold_value=100000,
            )
            decision = AdvisoryDecision(
                decision_id="DEC-CHK-001",
                recommendation_id=rec_id,
                rationale="Infrequent or disabled checkpoints (>100,000 records) increase recovery time upon transient worker failure.",
                impact_analysis="Incurring massive re-execution penalty if process fails mid-stage.",
                risk_mitigation="Enable checkpointing at 25,000 record intervals.",
                alternatives_considered=("Disable checkpoints", "Stage-level checkpoints only"),
            )
            recs.append(
                AdvisoryRecommendation(
                    recommendation_id=rec_id,
                    title="Increase Checkpoint Frequency for Resiliency",
                    category=AdvisoryCategory.CHECKPOINT,
                    severity=AdvisorySeverity.MEDIUM,
                    priority=AdvisoryPriority.P2,
                    description=f"Checkpoint interval of {interval_records} records is too sparse for high-volume data migration.",
                    rationale="Dense checkpointing minimizes work loss during transient failures.",
                    impact="Reduces recovery restart time from hours to minutes.",
                    action_items=("Configure checkpoint interval to 25,000 records.",),
                    affected_nodes=(),
                    evidence=(evidence,),
                    decision=decision,
                    tags=("checkpoint", "resiliency", "rpo"),
                )
            )
        else:
            rec_id = "REC-CHK-002"
            evidence = AdvisoryEvidence(
                source_component="CheckpointPlan.interval_records",
                metric_name="interval_records",
                observed_value=interval_records,
                threshold_value=100000,
            )
            recs.append(
                AdvisoryRecommendation(
                    recommendation_id=rec_id,
                    title="Checkpoint Strategy Verified",
                    category=AdvisoryCategory.CHECKPOINT,
                    severity=AdvisorySeverity.INFORMATIONAL,
                    priority=AdvisoryPriority.P4,
                    description=f"Checkpoint interval ({interval_records} records) ensures acceptable restartability.",
                    rationale="Checkpoint plan balances persistence I/O with fault recovery speed.",
                    impact="Sufficient fault tolerance.",
                    action_items=("Maintain current checkpoint policy.",),
                    affected_nodes=(),
                    evidence=(evidence,),
                    tags=("checkpoint", "standard"),
                )
            )

        return recs
