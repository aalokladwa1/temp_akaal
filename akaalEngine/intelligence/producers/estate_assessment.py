"""akaalEngine.intelligence.producers.estate_assessment
=========================================================
P7C.7 -- Estate Assessment & Risk Intelligence. Wraps the REAL, existing
deterministic schema assessment engines:
  - akaalEngine.schema.assessment.compatibility.PreMigrationCompatibilityAssessor
  - akaalEngine.schema.assessment.risk.StructuralRiskScorer

Nothing here recomputes compatibility/risk logic -- it packages the canonical
engines' own output as a typed, epistemically-classified IntelligenceResult, and
never turns a model interpretation into canonical compatibility status: findings
here are DERIVED_FACT/DIAGNOSIS from a real deterministic evaluation of the
supplied schema model, not model opinion.
"""

from __future__ import annotations

from typing import Any, Callable, Optional

from akaalEngine.intelligence.models.context import IntelligenceContext
from akaalEngine.intelligence.models.errors import IntelligenceValidationError
from akaalEngine.intelligence.models.request import IntelligenceRequest
from akaalEngine.intelligence.models.result import (
    ConfidenceEvidence,
    DiagnosticFinding,
    EpistemicType,
    Explanation,
    IntelligenceResult,
)
from akaalEngine.schema.assessment.compatibility import PreMigrationCompatibilityAssessor
from akaalEngine.schema.assessment.risk import StructuralRiskScorer

SchemaModelResolver = Callable[[IntelligenceRequest, IntelligenceContext], Any]


def _finding_severity(impact_score: int) -> str:
    if impact_score >= 50:
        return "HIGH"
    if impact_score >= 20:
        return "MEDIUM"
    return "LOW"


def make_estate_assessment_producer(schema_model_resolver: SchemaModelResolver):
    """Returns an IntelligenceKernel-compatible producer for IntelligenceTask.ASSESS.

    `schema_model_resolver` is injected rather than owned here: this producer
    never performs discovery itself. In production it resolves to the actual
    canonical schema model the schema authority already produced for the given
    migration plan; in tests it can return a fixture model directly.
    request.parameters must contain 'target_engine'.
    """

    def producer(request: IntelligenceRequest, context: IntelligenceContext) -> IntelligenceResult:
        target_engine = request.parameters.get("target_engine")
        if not target_engine:
            raise IntelligenceValidationError(
                "Estate assessment requires request.parameters['target_engine']."
            )

        model = schema_model_resolver(request, context)

        compat = PreMigrationCompatibilityAssessor.assess_model(model, str(target_engine))
        risk = StructuralRiskScorer.score_risk(model, compat)

        findings = [
            DiagnosticFinding(
                code=f"RISK:{factor.category}",
                severity=_finding_severity(factor.impact_score),
                message=factor.description,
                evidence_refs=[factor.affected_object] if factor.affected_object else [],
            )
            for factor in risk.risk_factors
        ]

        blockers = [f for f in findings if not compat.is_compatible and f.code.startswith("RISK:UNSUPPORTED")]
        summary = (
            f"Estate assessment against target {target_engine!r}: "
            f"{compat.total_columns} columns evaluated, "
            f"{compat.unsupported_count} unsupported, {compat.lossy_count} lossy, "
            f"overall risk {risk.risk_level.value}."
        )

        return IntelligenceResult(
            task=request.task,
            epistemic_type=EpistemicType.DIAGNOSIS,
            summary=summary,
            explanation=Explanation(
                summary="Derived deterministically from PreMigrationCompatibilityAssessor and StructuralRiskScorer.",
                supporting_facts=[
                    f"total_columns={compat.total_columns}",
                    f"unsupported_count={compat.unsupported_count}",
                    f"lossy_count={compat.lossy_count}",
                    f"risk_score={risk.total_risk_score}",
                ],
                contradictions=[] if compat.is_compatible else [
                    "Schema contains unsupported/lossy/decision-required column conversions."
                ],
            ),
            confidence_evidence=ConfidenceEvidence(
                evidence_coverage=1.0,
                source_freshness="current",
            ),
            findings=findings,
            data={
                "compatibility_breakdown": compat.to_dict(),
                "risk_report": risk.to_dict(),
                "is_compatible": compat.is_compatible,
                "blocker_count": len(blockers),
            },
        )

    return producer
