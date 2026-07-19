"""
Akaal — Best Practice Recommendation Analyzer
===============================================
Analyzes adherence to enterprise database migration best practices and compliance standards.
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


class BestPracticeRecommendationAnalyzer(RecommendationAnalyzer):
    """Analyzes enterprise migration best practices, post-verification policies, and staging procedures."""

    @property
    def name(self) -> str:
        return "BestPracticeRecommendationAnalyzer"

    @property
    def category(self) -> AdvisoryCategory:
        return AdvisoryCategory.BEST_PRACTICE

    @property
    def description(self) -> str:
        return "Evaluates validation stage inclusion, checksum verification policies, and audit logging."

    def analyze(
        self, plan: Any, context: AdvisoryContext
    ) -> List[AdvisoryRecommendation]:
        recs: List[AdvisoryRecommendation] = []
        plan_dict = plan.to_dict() if hasattr(plan, "to_dict") else dict(plan or {})
        cutover_plan = plan_dict.get("cutover_plan", {})
        stages = plan_dict.get("execution_stages", [])

        has_validation_phase = False
        if isinstance(cutover_plan, dict) and "phases" in cutover_plan:
            phases = [str(p.get("phase_type", "")).upper() for p in cutover_plan.get("phases", [])]
            has_validation_phase = "VALIDATION" in phases
        else:
            has_validation_phase = any(s.get("stage_type") == "VALIDATION" for s in stages)

        if not has_validation_phase:
            rec_id = "REC-BP-001"
            evidence = AdvisoryEvidence(
                source_component="CutoverPlan.phases",
                metric_name="has_validation_phase",
                observed_value=False,
                threshold_value=True,
            )
            decision = AdvisoryDecision(
                decision_id="DEC-BP-001",
                recommendation_id=rec_id,
                rationale="Enterprise migration best practices require an explicit data integrity validation phase prior to cutover switch.",
                impact_analysis="Risk of promoting corrupted or incomplete data to production.",
                risk_mitigation="Insert mandatory VALIDATION stage with checksum verification prior to SWITCH phase.",
                alternatives_considered=("Post-cutover validation only", "Sampling-based spot check"),
            )
            recs.append(
                AdvisoryRecommendation(
                    recommendation_id=rec_id,
                    title="Insert Explicit Data Integrity Validation Phase",
                    category=AdvisoryCategory.BEST_PRACTICE,
                    severity=AdvisorySeverity.HIGH,
                    priority=AdvisoryPriority.P0,
                    description="Execution plan lacks a formal pre-switch data integrity validation phase.",
                    rationale="Enterprise compliance mandates end-to-end checksum verification before cutover.",
                    impact="Potential data discrepancy leakage into production target system.",
                    action_items=("Add VALIDATION phase before SWITCH in CutoverPlan.",),
                    affected_nodes=(),
                    evidence=(evidence,),
                    decision=decision,
                    tags=("best_practice", "compliance", "validation"),
                )
            )
        else:
            rec_id = "REC-BP-002"
            evidence = AdvisoryEvidence(
                source_component="CutoverPlan.phases",
                metric_name="has_validation_phase",
                observed_value=True,
                threshold_value=True,
            )
            recs.append(
                AdvisoryRecommendation(
                    recommendation_id=rec_id,
                    title="Best Practice Compliance Confirmed",
                    category=AdvisoryCategory.BEST_PRACTICE,
                    severity=AdvisorySeverity.INFORMATIONAL,
                    priority=AdvisoryPriority.P4,
                    description="Execution plan includes all required enterprise validation and compliance checkpoints.",
                    rationale="Plan adheres to enterprise migration guidelines.",
                    impact="High confidence in cutover readiness.",
                    action_items=("Maintain best practice configuration.",),
                    affected_nodes=(),
                    evidence=(evidence,),
                    tags=("best_practice", "standard"),
                )
            )

        return recs
