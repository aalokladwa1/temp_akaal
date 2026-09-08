"""akaalEngine.intelligence.producers.operator_query
=======================================================
P7C.21 -- Conversational & Operator Intelligence. A typed intent router over
ALREADY-COMPUTED P7C.13/14/15/17 summaries -- never a free-form LLM call (none
is wired here), never a direct runtime action. Every answer is grounded:
built only from the real `summary`/`data` fields those producers already
returned, with explicit citations to which capability each fact came from.
Anti-enumeration is inherited structurally: this producer is called only
after the resolver chain's own tenant enforcement already ran (the same
CanonicalRuntimeHealthResolver.resolve enforcement used everywhere else) --
an unauthorized migration never reaches this producer at all.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Optional

from akaalEngine.intelligence.models.context import IntelligenceContext
from akaalEngine.intelligence.models.errors import IntelligenceValidationError
from akaalEngine.intelligence.models.request import IntelligenceRequest
from akaalEngine.intelligence.models.result import (
    ConfidenceEvidence,
    EpistemicType,
    Explanation,
    IntelligenceResult,
)

SUPPORTED_INTENTS = frozenset({
    "what_is_happening", "why", "what_changed", "will_cutover_succeed", "what_are_my_options",
    "estimated_cost", "supporting_evidence", "invalidation_conditions", "at_risk_migrations",
})


@dataclass(frozen=True)
class OperatorQueryInputs:
    migration_id: str
    health_summary: Optional[str] = None
    health_citation: str = "runtime_health"
    anomaly_summary: Optional[str] = None
    anomaly_citation: str = "anomaly_detection"
    rca_summary: Optional[str] = None
    rca_citation: str = "root_cause_analysis"
    rca_supporting_facts: Optional[str] = None  # joined supporting evidence, for "supporting_evidence"/"why"
    rca_invalidation_condition: Optional[str] = None  # for "invalidation_conditions"
    forecast_summary: Optional[str] = None
    forecast_citation: str = "operations_forecast"
    remediation_summary: Optional[str] = None
    remediation_citation: str = "governed_remediation"
    finops_summary: Optional[str] = None
    finops_citation: str = "finops_projection"
    portfolio_summary: Optional[str] = None  # tenant-wide; None for migration-scoped intents
    portfolio_citation: str = "portfolio_intelligence"


OperatorQueryResolver = Callable[[IntelligenceRequest, IntelligenceContext], OperatorQueryInputs]


def make_operator_query_producer(resolver: OperatorQueryResolver):
    def producer(request: IntelligenceRequest, context: IntelligenceContext) -> IntelligenceResult:
        intent = str(request.parameters.get("intent", ""))
        if intent not in SUPPORTED_INTENTS:
            raise IntelligenceValidationError(
                f"Unsupported intent {intent!r}; must be one of {sorted(SUPPORTED_INTENTS)}. "
                "Never falls back to a free-form/unrouted answer."
            )

        inputs = resolver(request, context)
        if inputs is None:
            raise IntelligenceValidationError(
                "Operator query resolver returned no OperatorQueryInputs. Refusing to fabricate "
                "a grounded answer with no underlying facts."
            )

        answer_parts = []
        citations = []

        def _add(summary: Optional[str], citation: str) -> None:
            if summary:
                answer_parts.append(summary)
                citations.append(citation)

        if intent == "what_is_happening":
            _add(inputs.health_summary, inputs.health_citation)
            _add(inputs.anomaly_summary, inputs.anomaly_citation)
        elif intent == "why":
            _add(inputs.rca_summary, inputs.rca_citation)
        elif intent == "what_changed":
            _add(inputs.anomaly_summary, inputs.anomaly_citation)
        elif intent == "will_cutover_succeed":
            _add(inputs.forecast_summary, inputs.forecast_citation)
        elif intent == "what_are_my_options":
            _add(inputs.remediation_summary, inputs.remediation_citation)
        elif intent == "estimated_cost":
            _add(inputs.finops_summary, inputs.finops_citation)
        elif intent == "supporting_evidence":
            _add(inputs.rca_supporting_facts, inputs.rca_citation)
        elif intent == "invalidation_conditions":
            _add(inputs.rca_invalidation_condition, inputs.rca_citation)
        elif intent == "at_risk_migrations":
            _add(inputs.portfolio_summary, inputs.portfolio_citation)

        answer = " ".join(answer_parts) if answer_parts else (
            f"No grounded facts are currently available to answer {intent!r} for migration "
            f"{inputs.migration_id!r} -- reporting this honestly rather than guessing."
        )

        return IntelligenceResult(
            task=request.task,
            epistemic_type=EpistemicType.FACT if answer_parts else EpistemicType.ASSUMPTION,
            summary=answer,
            explanation=Explanation(
                summary="Answer assembled only from already-computed, cited producer summaries -- never a "
                "free-form model response and never a direct runtime action.",
                supporting_facts=list(answer_parts),
            ),
            confidence_evidence=ConfidenceEvidence(
                evidence_coverage=1.0 if answer_parts else 0.0,
                missing_information=[] if answer_parts else [f"No underlying facts available for intent {intent!r}."],
            ),
            data={"migration_id": inputs.migration_id, "intent": intent, "citations": citations},
        )

    return producer
