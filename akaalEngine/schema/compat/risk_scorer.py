"""
akaalEngine.schema.compat.risk_scorer
======================================
Explainable Schema Migration Risk Scorer (CONS-002).
Computes deterministic, explainable risk assessment reports from structured SchemaDifferences,
providing normalized 0–100 risk scores, severity breakdowns, and continuation safety flags.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Sequence, Tuple

from akaalEngine.schema.compat.comparator import (
    CompatibilityClassification,
    DifferenceCategory,
    RiskSeverity,
    SchemaDifference,
)


@dataclass(frozen=True)
class RiskFinding:
    """Individual explainable risk evidence finding."""
    finding_id: str
    category: str  # STRUCTURAL, DATATYPE, CONSTRAINT, DEPENDENCY, PROGRAMMABLE, DRIFT
    severity: RiskSeverity
    explanation: str
    recommendation: str
    score_weight: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "finding_id": self.finding_id,
            "category": self.category,
            "severity": self.severity.value,
            "explanation": self.explanation,
            "recommendation": self.recommendation,
            "score_weight": self.score_weight,
        }


@dataclass(frozen=True)
class RiskAssessment:
    """Deterministic, explainable risk assessment report."""
    risk_score: int  # Normalized 0 to 100
    overall_compatibility: CompatibilityClassification
    findings: Tuple[RiskFinding, ...]
    breakdown: Dict[str, int]
    blocking_findings_count: int
    is_safe_to_continue: bool

    def to_dict(self) -> Dict[str, Any]:
        return {
            "risk_score": self.risk_score,
            "overall_compatibility": self.overall_compatibility.value,
            "findings": [f.to_dict() for f in self.findings],
            "breakdown": dict(self.breakdown),
            "blocking_findings_count": self.blocking_findings_count,
            "is_safe_to_continue": self.is_safe_to_continue,
        }


class CanonicalRiskScorer:
    """
    Universal Explainable Risk Assessment Authority for #4 Schema.
    Evaluates a sequence of SchemaDifferences and computes a deterministic RiskAssessment.
    """

    @classmethod
    def evaluate_risk(
        cls,
        differences: Sequence[SchemaDifference],
        source_engine: str = "GENERIC",
        target_engine: str = "GENERIC",
        allow_manual_waiver: bool = False,
    ) -> RiskAssessment:
        findings: List[RiskFinding] = []
        breakdown = {
            "STRUCTURAL": 0,
            "DATATYPE": 0,
            "CONSTRAINT": 0,
            "DEPENDENCY": 0,
            "PROGRAMMABLE": 0,
            "DRIFT": 0,
        }
        total_score_weight = 0
        blocking_count = 0
        worst_compat = CompatibilityClassification.COMPATIBLE

        compat_priority = {
            CompatibilityClassification.BLOCKING: 6,
            CompatibilityClassification.UNSUPPORTED: 5,
            CompatibilityClassification.LOSSY: 4,
            CompatibilityClassification.POTENTIALLY_LOSSY: 3,
            CompatibilityClassification.MANUAL_REVIEW_REQUIRED: 2,
            CompatibilityClassification.COMPATIBLE_WITH_CONVERSION: 1,
            CompatibilityClassification.COMPATIBLE: 0,
        }

        # Sort input differences deterministically by difference_id
        sorted_diffs = sorted(differences, key=lambda d: d.difference_id)

        for idx, diff in enumerate(sorted_diffs):
            weight = 0
            cat_name = "STRUCTURAL"

            if diff.category in (DifferenceCategory.ADDED, DifferenceCategory.REMOVED):
                weight = 15 if diff.severity in (RiskSeverity.HIGH, RiskSeverity.CRITICAL) else 5
                cat_name = "STRUCTURAL"
            elif diff.category == DifferenceCategory.TYPE_CHANGED:
                weight = 25
                cat_name = "DATATYPE"
            elif diff.category == DifferenceCategory.MODIFIED:
                weight = 20 if diff.severity in (RiskSeverity.HIGH, RiskSeverity.CRITICAL) else 5
                cat_name = "DATATYPE"
            elif diff.category == DifferenceCategory.CONSTRAINT_CHANGED:
                weight = 15
                cat_name = "CONSTRAINT"
            elif diff.category == DifferenceCategory.MANUAL_REVIEW_REQUIRED:
                weight = 30
                cat_name = "PROGRAMMABLE"
            elif diff.category == DifferenceCategory.UNSUPPORTED:
                weight = 40
                cat_name = "STRUCTURAL"

            # Evaluate severity & worst compatibility classification
            if diff.severity == RiskSeverity.BLOCKING or diff.compatibility == CompatibilityClassification.BLOCKING:
                blocking_count += 1

            if compat_priority.get(diff.compatibility, 0) > compat_priority.get(worst_compat, 0):
                worst_compat = diff.compatibility

            breakdown[cat_name] = breakdown.get(cat_name, 0) + weight
            total_score_weight += weight

            findings.append(
                RiskFinding(
                    finding_id=f"rf-{idx+1}-{diff.difference_id}",
                    category=cat_name,
                    severity=diff.severity,
                    explanation=diff.explanation,
                    recommendation=diff.recommended_action,
                    score_weight=weight,
                )
            )

        final_score = min(100, max(0, total_score_weight))

        unsafe_compatibilities = {
            CompatibilityClassification.BLOCKING,
            CompatibilityClassification.UNSUPPORTED,
            CompatibilityClassification.LOSSY,
            CompatibilityClassification.POTENTIALLY_LOSSY,
            CompatibilityClassification.MANUAL_REVIEW_REQUIRED,
        }
        if allow_manual_waiver:
            unsafe_compatibilities -= {
                CompatibilityClassification.MANUAL_REVIEW_REQUIRED,
                CompatibilityClassification.POTENTIALLY_LOSSY,
            }

        is_safe = (blocking_count == 0) and (worst_compat not in unsafe_compatibilities)

        return RiskAssessment(
            risk_score=final_score,
            overall_compatibility=worst_compat,
            findings=tuple(findings),
            breakdown=breakdown,
            blocking_findings_count=blocking_count,
            is_safe_to_continue=is_safe,
        )
