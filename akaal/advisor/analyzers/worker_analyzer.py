"""
Akaal — Worker Recommendation Analyzer
========================================
Analyzes worker thread utilization, concurrency limits, and thread pool allocation.
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


class WorkerRecommendationAnalyzer(RecommendationAnalyzer):
    """Analyzes worker thread allocation and pool sizing."""

    @property
    def name(self) -> str:
        return "WorkerRecommendationAnalyzer"

    @property
    def category(self) -> AdvisoryCategory:
        return AdvisoryCategory.WORKER

    @property
    def description(self) -> str:
        return "Evaluates parallel worker thread count, queue depth, and thread pool contention."

    def analyze(
        self, plan: Any, context: AdvisoryContext
    ) -> List[AdvisoryRecommendation]:
        recs: List[AdvisoryRecommendation] = []
        plan_dict = plan.to_dict() if hasattr(plan, "to_dict") else dict(plan or {})
        resource_schedule = plan_dict.get("resource_schedule", {})
        parallel_strategy = plan_dict.get("parallel_strategy", {})

        worker_count = resource_schedule.get("max_workers", parallel_strategy.get("max_concurrency", 4))

        if worker_count > 16:
            rec_id = "REC-WORKER-001"
            evidence = AdvisoryEvidence(
                source_component="ResourceSchedule.max_workers",
                metric_name="worker_count",
                observed_value=worker_count,
                threshold_value=16,
                evidence_details={"parallel_strategy": parallel_strategy},
            )
            decision = AdvisoryDecision(
                decision_id="DEC-WORKER-001",
                recommendation_id=rec_id,
                rationale="Excessive worker concurrency (>16 threads) causes target database CPU context switching and connection exhaustion.",
                impact_analysis="Potential connection timeout errors on target DB.",
                risk_mitigation="Cap worker pool concurrency to 8 threads.",
                alternatives_considered=("Keep 16+ workers", "Scale DB pool dynamically"),
            )
            recs.append(
                AdvisoryRecommendation(
                    recommendation_id=rec_id,
                    title="Throttle High Concurrency Worker Pool",
                    category=AdvisoryCategory.WORKER,
                    severity=AdvisorySeverity.HIGH,
                    priority=AdvisoryPriority.P1,
                    description=f"Worker concurrency set to {worker_count}, exceeding recommended database pool threshold of 16.",
                    rationale="High worker count risks database connection limit exhaustion.",
                    impact="Target database connection pool saturation.",
                    action_items=("Set max_workers to 8 threads.", "Enable connection pooling on worker threads."),
                    affected_nodes=("worker_pool_0",),
                    evidence=(evidence,),
                    decision=decision,
                    tags=("worker", "concurrency", "performance"),
                )
            )
        else:
            rec_id = "REC-WORKER-002"
            evidence = AdvisoryEvidence(
                source_component="ResourceSchedule.max_workers",
                metric_name="worker_count",
                observed_value=worker_count,
                threshold_value=16,
            )
            recs.append(
                AdvisoryRecommendation(
                    recommendation_id=rec_id,
                    title="Worker Allocation Balanced",
                    category=AdvisoryCategory.WORKER,
                    severity=AdvisorySeverity.INFORMATIONAL,
                    priority=AdvisoryPriority.P4,
                    description=f"Worker count of {worker_count} is optimal for target database capacity.",
                    rationale="Worker allocation maintains good throughput without thread contention.",
                    impact="Balanced resource utilization.",
                    action_items=("Maintain worker pool setting.",),
                    affected_nodes=(),
                    evidence=(evidence,),
                    tags=("worker", "standard"),
                )
            )

        return recs
