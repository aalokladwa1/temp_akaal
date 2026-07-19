"""
Akaal — Topology Recommendation Analyzer
=========================================
Analyzes network topology, cross-region latency impact, and partition boundaries.
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


class TopologyRecommendationAnalyzer(RecommendationAnalyzer):
    """Analyzes topology layout, network boundaries, and partition alignment."""

    @property
    def name(self) -> str:
        return "TopologyRecommendationAnalyzer"

    @property
    def category(self) -> AdvisoryCategory:
        return AdvisoryCategory.TOPOLOGY

    @property
    def description(self) -> str:
        return "Evaluates source/target deployment topologies, multi-region latency risks, and network partitions."

    def analyze(
        self, plan: Any, context: AdvisoryContext
    ) -> List[AdvisoryRecommendation]:
        recs: List[AdvisoryRecommendation] = []
        plan_dict = plan.to_dict() if hasattr(plan, "to_dict") else dict(plan or {})
        manifest = plan_dict.get("manifest", {})
        execution_graph = plan_dict.get("execution_graph", {})

        cross_region = manifest.get("cross_region", False) or execution_graph.get("cross_region", False)

        if cross_region:
            rec_id = "REC-TOP-001"
            evidence = AdvisoryEvidence(
                source_component="ExecutionGraph.cross_region",
                metric_name="cross_region",
                observed_value=True,
                threshold_value=False,
            )
            decision = AdvisoryDecision(
                decision_id="DEC-TOP-001",
                recommendation_id=rec_id,
                rationale="Cross-region migration transfers introduce variable network latency and inter-region data egress charges.",
                impact_analysis="Throughput degradation due to TCP network round-trip latency.",
                risk_mitigation="Deploy worker agents co-located in the target cloud region with compression enabled.",
                alternatives_considered=("Direct cross-region streaming", "WAN optimization appliance"),
            )
            recs.append(
                AdvisoryRecommendation(
                    recommendation_id=rec_id,
                    title="Co-locate Worker Nodes with Target Cloud Region",
                    category=AdvisoryCategory.TOPOLOGY,
                    severity=AdvisorySeverity.HIGH,
                    priority=AdvisoryPriority.P1,
                    description="Execution graph spans cross-region network topologies.",
                    rationale="Inter-region latency limits bulk migration transfer speed.",
                    impact="Network bottlenecking and elevated data transfer fees.",
                    action_items=(
                        "Deploy worker pool inside target availability zone.",
                        "Enable network payload compression on batch transport.",
                    ),
                    affected_nodes=(),
                    evidence=(evidence,),
                    decision=decision,
                    tags=("topology", "network", "cross_region"),
                )
            )
        else:
            rec_id = "REC-TOP-002"
            evidence = AdvisoryEvidence(
                source_component="ExecutionGraph.cross_region",
                metric_name="cross_region",
                observed_value=False,
                threshold_value=False,
            )
            recs.append(
                AdvisoryRecommendation(
                    recommendation_id=rec_id,
                    title="Network Topology Optimal",
                    category=AdvisoryCategory.TOPOLOGY,
                    severity=AdvisorySeverity.INFORMATIONAL,
                    priority=AdvisoryPriority.P4,
                    description="Source and target systems are deployed within low-latency regional boundaries.",
                    rationale="Minimal network latency overhead expected during transfer.",
                    impact="High network throughput.",
                    action_items=("Maintain current deployment topology.",),
                    affected_nodes=(),
                    evidence=(evidence,),
                    tags=("topology", "standard"),
                )
            )

        return recs
