"""
Akaal — ETA Recommendation Analyzer
====================================
Analyzes estimated completion time (ETA), critical path velocity, and potential completion bottlenecks.
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


class ETARecommendationAnalyzer(RecommendationAnalyzer):
    """Analyzes execution timeline and completion ETA bounds."""

    @property
    def name(self) -> str:
        return "ETARecommendationAnalyzer"

    @property
    def category(self) -> AdvisoryCategory:
        return AdvisoryCategory.ETA

    @property
    def description(self) -> str:
        return "Evaluates estimated completion window against maintenance window constraints."

    def analyze(
        self, plan: Any, context: AdvisoryContext
    ) -> List[AdvisoryRecommendation]:
        recs: List[AdvisoryRecommendation] = []
        plan_dict = plan.to_dict() if hasattr(plan, "to_dict") else dict(plan or {})
        timeline = plan_dict.get("execution_timeline", {})
        constraints = plan_dict.get("constraints", {})

        estimated_minutes = timeline.get("estimated_duration_minutes", 120.0)
        max_allowed_minutes = constraints.get("max_execution_window_minutes", 180.0)

        if estimated_minutes > max_allowed_minutes:
            rec_id = "REC-ETA-001"
            evidence = AdvisoryEvidence(
                source_component="ExecutionTimeline.estimated_duration_minutes",
                metric_name="estimated_duration_minutes",
                observed_value=estimated_minutes,
                threshold_value=max_allowed_minutes,
            )
            decision = AdvisoryDecision(
                decision_id="DEC-ETA-001",
                recommendation_id=rec_id,
                rationale="Estimated execution time exceeds the allocated business maintenance window.",
                impact_analysis="High risk of cutover overrunning into business hours.",
                risk_mitigation="Increase stage parallelism or split migration into multiple phased maintenance windows.",
                alternatives_considered=("Extend maintenance window", "Defer non-essential index creation"),
            )
            recs.append(
                AdvisoryRecommendation(
                    recommendation_id=rec_id,
                    title="Estimated Duration Exceeds Maintenance Window",
                    category=AdvisoryCategory.ETA,
                    severity=AdvisorySeverity.HIGH,
                    priority=AdvisoryPriority.P0,
                    description=f"Estimated duration ({estimated_minutes} mins) exceeds maintenance window limit ({max_allowed_minutes} mins).",
                    rationale="Cutover timeline risk jeopardizes application uptime SLA.",
                    impact="Migration overrun into active production window.",
                    action_items=(
                        "Increase parallelism on independent stages.",
                        "Postpone non-critical index rebuilds to post-cutover window.",
                    ),
                    affected_nodes=(),
                    evidence=(evidence,),
                    decision=decision,
                    tags=("eta", "timeline", "maintenance"),
                )
            )
        else:
            rec_id = "REC-ETA-002"
            evidence = AdvisoryEvidence(
                source_component="ExecutionTimeline.estimated_duration_minutes",
                metric_name="estimated_duration_minutes",
                observed_value=estimated_minutes,
                threshold_value=max_allowed_minutes,
            )
            recs.append(
                AdvisoryRecommendation(
                    recommendation_id=rec_id,
                    title="Timeline Complies With Maintenance Window",
                    category=AdvisoryCategory.ETA,
                    severity=AdvisorySeverity.INFORMATIONAL,
                    priority=AdvisoryPriority.P4,
                    description=f"Estimated duration of {estimated_minutes} mins is well within the {max_allowed_minutes} mins window.",
                    rationale="Execution plan fits safely inside approved cutover schedule.",
                    impact="Low risk of timeline overrun.",
                    action_items=("Proceed with current schedule.",),
                    affected_nodes=(),
                    evidence=(evidence,),
                    tags=("eta", "standard"),
                )
            )

        return recs
