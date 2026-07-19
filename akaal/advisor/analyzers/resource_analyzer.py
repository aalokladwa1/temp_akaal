"""
Akaal — Resource Recommendation Analyzer
=========================================
Analyzes system resource utilization, temp space allocation, buffer pools, and disk I/O limits.
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


class ResourceRecommendationAnalyzer(RecommendationAnalyzer):
    """Analyzes system resource allocation, disk space, and temporary table storage."""

    @property
    def name(self) -> str:
        return "ResourceRecommendationAnalyzer"

    @property
    def category(self) -> AdvisoryCategory:
        return AdvisoryCategory.RESOURCE

    @property
    def description(self) -> str:
        return "Evaluates temp table space, log file sizing, and disk space headroom on target system."

    def analyze(
        self, plan: Any, context: AdvisoryContext
    ) -> List[AdvisoryRecommendation]:
        recs: List[AdvisoryRecommendation] = []
        plan_dict = plan.to_dict() if hasattr(plan, "to_dict") else dict(plan or {})
        resource_schedule = plan_dict.get("resource_schedule", {})
        constraints = plan_dict.get("constraints", {})

        estimated_temp_space_gb = resource_schedule.get("estimated_temp_space_gb", 50.0)
        available_disk_gb = constraints.get("available_disk_gb", 100.0)

        if estimated_temp_space_gb > (available_disk_gb * 0.8):
            rec_id = "REC-RES-001"
            evidence = AdvisoryEvidence(
                source_component="ResourceSchedule.estimated_temp_space_gb",
                metric_name="estimated_temp_space_gb",
                observed_value=estimated_temp_space_gb,
                threshold_value=available_disk_gb * 0.8,
            )
            decision = AdvisoryDecision(
                decision_id="DEC-RES-001",
                recommendation_id=rec_id,
                rationale="Estimated temp table and write-ahead log storage (>80% available disk) risks target disk space exhaustion.",
                impact_analysis="Critical database crash due to full disk volume.",
                risk_mitigation="Expand target storage volume or enable immediate WAL archiving during bulk load.",
                alternatives_considered=("Disable WAL logging during import", "Compress temp files"),
            )
            recs.append(
                AdvisoryRecommendation(
                    recommendation_id=rec_id,
                    title="Expand Target System Disk Space Headroom",
                    category=AdvisoryCategory.RESOURCE,
                    severity=AdvisorySeverity.CRITICAL,
                    priority=AdvisoryPriority.P0,
                    description=f"Estimated temporary space ({estimated_temp_space_gb} GB) exceeds 80% of available disk space ({available_disk_gb} GB).",
                    rationale="Database import and index creation demand significant temporary storage.",
                    impact="Target volume full error causing hard database shutdown.",
                    action_items=("Expand target volume storage by at least 100 GB.",),
                    affected_nodes=(),
                    evidence=(evidence,),
                    decision=decision,
                    tags=("resource", "storage", "disk", "critical"),
                )
            )
        else:
            rec_id = "REC-RES-002"
            evidence = AdvisoryEvidence(
                source_component="ResourceSchedule.estimated_temp_space_gb",
                metric_name="estimated_temp_space_gb",
                observed_value=estimated_temp_space_gb,
                threshold_value=available_disk_gb * 0.8,
            )
            recs.append(
                AdvisoryRecommendation(
                    recommendation_id=rec_id,
                    title="Storage Headroom Adequate",
                    category=AdvisoryCategory.RESOURCE,
                    severity=AdvisorySeverity.INFORMATIONAL,
                    priority=AdvisoryPriority.P4,
                    description=f"Estimated temporary storage ({estimated_temp_space_gb} GB) is well within available capacity ({available_disk_gb} GB).",
                    rationale="Target storage volume provides adequate headroom for index building and logs.",
                    impact="Sufficient disk capacity.",
                    action_items=("Maintain current storage allocation.",),
                    affected_nodes=(),
                    evidence=(evidence,),
                    tags=("resource", "standard"),
                )
            )

        return recs
