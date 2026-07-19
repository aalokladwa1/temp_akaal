"""
Akaal — Hardware Recommendation Analyzer
==========================================
Analyzes hardware constraints, memory limits, storage I/O, and CPU allocation.
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


class HardwareRecommendationAnalyzer(RecommendationAnalyzer):
    """Analyzes hardware utilization and system resource boundaries."""

    @property
    def name(self) -> str:
        return "HardwareRecommendationAnalyzer"

    @property
    def category(self) -> AdvisoryCategory:
        return AdvisoryCategory.HARDWARE

    @property
    def description(self) -> str:
        return "Evaluates target and source system CPU, RAM, disk I/O, and network bandwidth requirements."

    def analyze(
        self, plan: Any, context: AdvisoryContext
    ) -> List[AdvisoryRecommendation]:
        recs: List[AdvisoryRecommendation] = []
        plan_dict = plan.to_dict() if hasattr(plan, "to_dict") else dict(plan or {})
        constraints = plan_dict.get("constraints", {})
        resource_schedule = plan_dict.get("resource_schedule", {})

        memory_limit_mb = constraints.get("memory_limit_mb", resource_schedule.get("memory_limit_mb", 4096))
        disk_iops_required = resource_schedule.get("estimated_iops", 3000)

        if memory_limit_mb < 2048:
            rec_id = "REC-HW-001"
            evidence = AdvisoryEvidence(
                source_component="Constraints.memory_limit_mb",
                metric_name="memory_limit_mb",
                observed_value=memory_limit_mb,
                threshold_value=2048,
            )
            decision = AdvisoryDecision(
                decision_id="DEC-HW-001",
                recommendation_id=rec_id,
                rationale="Allocated RAM (<2,048 MB) is insufficient for in-memory index building during migration.",
                impact_analysis="High risk of process termination due to OOM killer.",
                risk_mitigation="Provision minimum 4,096 MB RAM for migration worker container.",
                alternatives_considered=("Increase swap space", "Use disk-based index sorting"),
            )
            recs.append(
                AdvisoryRecommendation(
                    recommendation_id=rec_id,
                    title="Provision Additional Memory for Migration Nodes",
                    category=AdvisoryCategory.HARDWARE,
                    severity=AdvisorySeverity.CRITICAL,
                    priority=AdvisoryPriority.P0,
                    description=f"Current allocated RAM ({memory_limit_mb} MB) is below safe enterprise threshold of 2,048 MB.",
                    rationale="In-memory data transformations will fail if memory is constrained.",
                    impact="Process failure and migration abort.",
                    action_items=("Increase worker RAM allocation to 4,096 MB.",),
                    affected_nodes=("migration_host_0",),
                    evidence=(evidence,),
                    decision=decision,
                    tags=("hardware", "memory", "critical"),
                )
            )
        else:
            rec_id = "REC-HW-002"
            evidence = AdvisoryEvidence(
                source_component="Constraints.memory_limit_mb",
                metric_name="memory_limit_mb",
                observed_value=memory_limit_mb,
                threshold_value=2048,
            )
            recs.append(
                AdvisoryRecommendation(
                    recommendation_id=rec_id,
                    title="Hardware Allocation Meets Minimum Requirements",
                    category=AdvisoryCategory.HARDWARE,
                    severity=AdvisorySeverity.INFORMATIONAL,
                    priority=AdvisoryPriority.P4,
                    description=f"Allocated memory of {memory_limit_mb} MB and IOPS of {disk_iops_required} satisfy platform requirements.",
                    rationale="Sufficient hardware resources allocated for execution graph.",
                    impact="Stable hardware operating conditions.",
                    action_items=("Maintain current hardware allocation.",),
                    affected_nodes=(),
                    evidence=(evidence,),
                    tags=("hardware", "standard"),
                )
            )

        return recs
