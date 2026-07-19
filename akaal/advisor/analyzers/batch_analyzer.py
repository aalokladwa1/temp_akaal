"""
Akaal — Batch Recommendation Analyzer
=======================================
Analyzes migration batching strategy, chunk sizes, and transaction boundaries.
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


class BatchRecommendationAnalyzer(RecommendationAnalyzer):
    """Analyzes batching configuration and chunking strategy."""

    @property
    def name(self) -> str:
        return "BatchRecommendationAnalyzer"

    @property
    def category(self) -> AdvisoryCategory:
        return AdvisoryCategory.BATCHING

    @property
    def description(self) -> str:
        return "Evaluates batch sizes, chunking limits, and memory footprint per stage."

    def analyze(
        self, plan: Any, context: AdvisoryContext
    ) -> List[AdvisoryRecommendation]:
        recs: List[AdvisoryRecommendation] = []
        plan_dict = plan.to_dict() if hasattr(plan, "to_dict") else dict(plan or {})
        strategy = plan_dict.get("strategy", {})
        execution_stages = plan_dict.get("execution_stages", [])

        batch_size = strategy.get("batch_size", 1000)
        chunk_size = strategy.get("chunk_size", 500)

        if batch_size > 10000:
            rec_id = f"REC-BATCH-001"
            evidence = AdvisoryEvidence(
                source_component="Strategy.batch_size",
                metric_name="batch_size",
                observed_value=batch_size,
                threshold_value=10000,
                evidence_details={"chunk_size": chunk_size},
                references=("ADVISOR-BATCH-SPEC-V1",),
            )
            decision = AdvisoryDecision(
                decision_id="DEC-BATCH-001",
                recommendation_id=rec_id,
                rationale="Large batch sizes (>10,000) increase buffer pool memory consumption and lock hold duration.",
                impact_analysis="High risk of OOM and long transaction lock times.",
                risk_mitigation="Reduce batch size to 5,000 and enable dynamic chunk scaling.",
                alternatives_considered=("Keep current batch size", "Use fixed 1,000 chunking"),
            )
            recs.append(
                AdvisoryRecommendation(
                    recommendation_id=rec_id,
                    title="Optimize Migration Batch Size",
                    category=AdvisoryCategory.BATCHING,
                    severity=AdvisorySeverity.HIGH,
                    priority=AdvisoryPriority.P1,
                    description="Current migration batch size exceeds recommended enterprise memory limit of 10,000 records.",
                    rationale="Excessive batch sizes cause buffer pool pressure and database lock contention.",
                    impact="Potential transaction failure or memory exhaustion during cutover.",
                    action_items=(
                        "Reduce batch_size configuration to 5,000 records.",
                        "Enable adaptive chunking based on target row length.",
                    ),
                    affected_nodes=tuple([s.get("stage_id", "stage") for s in execution_stages[:3]]),
                    evidence=(evidence,),
                    decision=decision,
                    tags=("batching", "memory", "performance"),
                )
            )
        else:
            rec_id = f"REC-BATCH-002"
            evidence = AdvisoryEvidence(
                source_component="Strategy.batch_size",
                metric_name="batch_size",
                observed_value=batch_size,
                threshold_value=5000,
                evidence_details={"chunk_size": chunk_size},
                references=("ADVISOR-BATCH-SPEC-V1",),
            )
            recs.append(
                AdvisoryRecommendation(
                    recommendation_id=rec_id,
                    title="Batch Size Within Safe Threshold",
                    category=AdvisoryCategory.BATCHING,
                    severity=AdvisorySeverity.INFORMATIONAL,
                    priority=AdvisoryPriority.P4,
                    description=f"Batch size of {batch_size} records is within recommended operational parameters.",
                    rationale="Batch size configuration balances throughput with memory usage.",
                    impact="Stable record processing performance.",
                    action_items=("Maintain current batching configuration.",),
                    affected_nodes=(),
                    evidence=(evidence,),
                    tags=("batching", "standard"),
                )
            )

        return recs
