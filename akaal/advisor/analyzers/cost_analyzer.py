"""
Akaal — Cost Recommendation Analyzer
=====================================
Analyzes cloud infrastructure costs, compute efficiency, and resource optimization opportunity.
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


class CostRecommendationAnalyzer(RecommendationAnalyzer):
    """Analyzes financial cost efficiency of migration infrastructure strategy."""

    @property
    def name(self) -> str:
        return "CostRecommendationAnalyzer"

    @property
    def category(self) -> AdvisoryCategory:
        return AdvisoryCategory.COST

    @property
    def description(self) -> str:
        return "Evaluates cloud resource tiering, spot vs on-demand instance allocation, and compute expenditure."

    def analyze(
        self, plan: Any, context: AdvisoryContext
    ) -> List[AdvisoryRecommendation]:
        recs: List[AdvisoryRecommendation] = []
        plan_dict = plan.to_dict() if hasattr(plan, "to_dict") else dict(plan or {})
        resource_schedule = plan_dict.get("resource_schedule", {})
        statistics = plan_dict.get("statistics", {})

        estimated_duration_hours = statistics.get("estimated_duration_hours", 4.0)
        use_on_demand = resource_schedule.get("instance_type", "on-demand") == "on-demand"

        if estimated_duration_hours > 6.0 and use_on_demand:
            rec_id = "REC-COST-001"
            evidence = AdvisoryEvidence(
                source_component="ResourceSchedule.instance_type",
                metric_name="estimated_duration_hours",
                observed_value=estimated_duration_hours,
                threshold_value=6.0,
            )
            decision = AdvisoryDecision(
                decision_id="DEC-COST-001",
                recommendation_id=rec_id,
                rationale="Long-running migrations (>6h) on standard on-demand compute instances incur unoptimized compute charges.",
                impact_analysis="Higher cloud infrastructure cost.",
                risk_mitigation="Leverage spot/preemptible instances for non-critical batch stages with checkpointing.",
                alternatives_considered=("Remain on on-demand instances", "Reserved instance commitment"),
            )
            recs.append(
                AdvisoryRecommendation(
                    recommendation_id=rec_id,
                    title="Leverage Spot Instances for Long-Running Batch Stages",
                    category=AdvisoryCategory.COST,
                    severity=AdvisorySeverity.MEDIUM,
                    priority=AdvisoryPriority.P2,
                    description=f"Migration duration estimated at {estimated_duration_hours}h using on-demand compute.",
                    rationale="Spot instances can reduce compute cost by up to 60% for fault-tolerant batch workloads.",
                    impact="Estimated 40-60% reduction in migration infrastructure cost.",
                    action_items=("Enable spot instance pool for non-blocking stages.",),
                    affected_nodes=(),
                    evidence=(evidence,),
                    decision=decision,
                    tags=("cost", "cloud", "optimization"),
                )
            )
        else:
            rec_id = "REC-COST-002"
            evidence = AdvisoryEvidence(
                source_component="Statistics.estimated_duration_hours",
                metric_name="estimated_duration_hours",
                observed_value=estimated_duration_hours,
                threshold_value=6.0,
            )
            recs.append(
                AdvisoryRecommendation(
                    recommendation_id=rec_id,
                    title="Compute Cost Model Optimized",
                    category=AdvisoryCategory.COST,
                    severity=AdvisorySeverity.INFORMATIONAL,
                    priority=AdvisoryPriority.P4,
                    description="Current infrastructure sizing presents an optimal balance of cost and execution speed.",
                    rationale="Infrastructure expenditure is aligned with migration duration.",
                    impact="Cost-effective execution.",
                    action_items=("Maintain current compute sizing.",),
                    affected_nodes=(),
                    evidence=(evidence,),
                    tags=("cost", "standard"),
                )
            )

        return recs
