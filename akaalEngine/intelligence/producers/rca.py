"""akaalEngine.intelligence.producers.rca
===========================================
P7C.15 -- Evidence-Grounded Root Cause Analysis. Consumes ALREADY-COMPUTED
P7C.14 anomaly output (never recomputes detection itself -- reuse, not
duplication) plus P7C.13's FABRIC/VALIDATION dimension statuses, and applies
the deterministic causal-hypothesis ladder in
akaalEngine.intelligence.rca.hypotheses. RCA != Validation #11: this module
never re-derives or overrides Validation #11's own verdict, only relays it as
context for the governance-precedence rule.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Mapping

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
from akaalEngine.intelligence.rca.hypotheses import build_rca_conclusion


@dataclass(frozen=True)
class RCAInputs:
    """Bundled, already-resolved inputs -- this producer performs zero
    canonical discovery or anomaly (re)detection of its own."""

    tenant_id: str
    migration_id: str
    anomaly_data: Mapping[str, Any] = field(default_factory=dict)  # P7C.14 producer's own `data` dict
    fabric_status: str = "UNKNOWN"
    validation_status: str = "UNKNOWN"


RCAResolver = Callable[[IntelligenceRequest, IntelligenceContext], RCAInputs]


def make_rca_producer(resolver: RCAResolver):
    def producer(request: IntelligenceRequest, context: IntelligenceContext) -> IntelligenceResult:
        inputs = resolver(request, context)
        if inputs is None:
            raise IntelligenceValidationError(
                "RCA resolver returned no RCAInputs. Refusing to fabricate a root-cause "
                "conclusion with no anomaly/dimension facts."
            )

        conclusion = build_rca_conclusion(
            overall_anomaly_status=str(inputs.anomaly_data.get("overall_status", "UNKNOWN")),
            bottleneck=str(inputs.anomaly_data.get("bottleneck", "UNKNOWN")),
            detections=inputs.anomaly_data.get("detections", {}),
            fabric_status=inputs.fabric_status,
            validation_status=inputs.validation_status,
        )

        evidence_coverage = 1.0 if not conclusion.missing_evidence else max(0.2, 1.0 - 0.2 * len(conclusion.missing_evidence))

        findings = [
            DiagnosticFinding(
                code="RCA:PRIMARY_HYPOTHESIS",
                severity="HIGH" if inputs.anomaly_data.get("overall_status") == "ANOMALOUS" else "LOW",
                message=conclusion.primary.label,
                evidence_refs=list(conclusion.primary.support),
            )
        ]

        summary = f"RCA for migration {inputs.migration_id!r}: {conclusion.primary.label}"

        return IntelligenceResult(
            task=request.task,
            epistemic_type=EpistemicType.INFERENCE,
            summary=summary,
            explanation=Explanation(
                summary=conclusion.primary.confidence_basis,
                supporting_facts=list(conclusion.primary.support),
                contradictions=list(conclusion.contradictions),
                alternatives_considered=[h.label for h in conclusion.alternatives],
            ),
            confidence_evidence=ConfidenceEvidence(
                evidence_coverage=evidence_coverage,
                missing_information=list(conclusion.missing_evidence),
                contradictory_evidence=list(conclusion.contradictions),
            ),
            findings=findings,
            data={
                "migration_id": inputs.migration_id,
                **conclusion.to_dict(),
            },
        )

    return producer
