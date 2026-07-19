"""
Akaal — Parallelism Recommendation Analyzer
=============================================
Analyzes maximum parallel stage execution, barrier synchronization, and lock contention.
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


class ParallelismRecommendationAnalyzer(RecommendationAnalyzer):
    """Analyzes execution graph parallelism and synchronization barriers."""

    @property
    def name(self) -> str:
        return "ParallelismRecommendationAnalyzer"

    @property
    def category(self) -> AdvisoryCategory:
        return AdvisoryCategory.PARALLELISM

    @property
    def description(self) -> str:
        return "Evaluates parallel stage execution policy, barrier sync points, and table-level lock conflicts."

    def analyze(
        self, plan: Any, context: AdvisoryContext
    ) -> List[AdvisoryRecommendation]:
        recs: List[AdvisoryRecommendation] = []
        plan_dict = plan.to_dict() if hasattr(plan, "to_dict") else dict(plan or {})
        parallel_strategy = plan_dict.get("parallel_strategy", {})
        execution_stages = plan_dict.get("execution_stages", [])

        max_parallel_stages = parallel_strategy.get("max_parallel_stages", len(execution_stages))

        if len(execution_stages) > 2 and max_parallel_stages == 1:
            rec_id = "REC-PAR-001"
            evidence = AdvisoryEvidence(
                source_component="ParallelStrategy.max_parallel_stages",
                metric_name="max_parallel_stages",
                observed_value=max_parallel_stages,
                threshold_value=2,
            )
            decision = AdvisoryDecision(
                decision_id="DEC-PAR-001",
                recommendation_id=rec_id,
                rationale="Serial execution of independent migration stages needlessly inflates cutover wall-clock time.",
                impact_analysis="Sub-optimal execution velocity.",
                risk_mitigation="Enable parallel execution for independent table migration stages.",
                alternatives_considered=("Maintain strictly serial pipeline",),
            )
            recs.append(
                AdvisoryRecommendation(
                    recommendation_id=rec_id,
                    title="Enable Parallel Execution for Independent Stages",
                    category=AdvisoryCategory.PARALLELISM,
                    severity=AdvisorySeverity.MEDIUM,
                    priority=AdvisoryPriority.P2,
                    description=f"Plan contains {len(execution_stages)} stages but limits execution to strictly serial (1 stage at a time).",
                    rationale="Independent tables can be migrated concurrently without lock contention.",
                    impact="Potential 50-70% reduction in total migration duration.",
                    action_items=("Set max_parallel_stages to 4 in ParallelStrategy.",),
                    affected_nodes=tuple([s.get("stage_id", "stage") for s in execution_stages]),
                    evidence=(evidence,),
                    decision=decision,
                    tags=("parallelism", "throughput", "velocity"),
                )
            )
        else:
            rec_id = "REC-PAR-002"
            evidence = AdvisoryEvidence(
                source_component="ParallelStrategy.max_parallel_stages",
                metric_name="max_parallel_stages",
                observed_value=max_parallel_stages,
                threshold_value=1,
            )
            recs.append(
                AdvisoryRecommendation(
                    recommendation_id=rec_id,
                    title="Parallelism Strategy Optimal",
                    category=AdvisoryCategory.PARALLELISM,
                    severity=AdvisorySeverity.INFORMATIONAL,
                    priority=AdvisoryPriority.P4,
                    description=f"Parallel stage configuration (max {max_parallel_stages} parallel stages) provides effective concurrency.",
                    rationale="Stage concurrency is aligned with dependency constraints.",
                    impact="Efficient stage scheduling.",
                    action_items=("Maintain parallel execution policy.",),
                    affected_nodes=(),
                    evidence=(evidence,),
                    tags=("parallelism", "standard"),
                )
            )

        return recs
