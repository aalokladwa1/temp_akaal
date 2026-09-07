"""akaalEngine.intelligence.producers.remediation
=====================================================
P7C.18 -- Governed Recovery & Remediation Intelligence. Consumes P7C.15's
ALREADY-COMPUTED RCA conclusion (never recomputes RCA itself) and, via the
deterministic recipe ladder in akaalEngine.intelligence.remediation.recipes,
produces AT MOST one typed ActionProposal (akaalEngine.intelligence.
mediation.proposal.ActionProposal) referencing an action_type already
registered in the Group-1 ActionMediationGateway's closed autonomy allow-list.

This producer NEVER mediates, authorizes, approves, or executes its own
proposal -- it only builds the typed request. Submitting the resulting
proposal to akaalEngine.intelligence.mediation.mediator.ActionMediationGateway
(reachable today via the existing 'intelligence.mediation.evaluate' IPC
query) and then to the real canonical command handler are separate, later,
independently-governed steps.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Mapping

from akaalEngine.intelligence.mediation.proposal import ActionProposal
from akaalEngine.intelligence.models.context import IntelligenceContext
from akaalEngine.intelligence.models.errors import IntelligenceValidationError
from akaalEngine.intelligence.models.request import IntelligenceRequest
from akaalEngine.intelligence.models.result import (
    ConfidenceEvidence,
    EpistemicType,
    Explanation,
    IntelligenceResult,
)
from akaalEngine.intelligence.remediation.recipes import select_recipe


@dataclass(frozen=True)
class RemediationInputs:
    """Bundled, already-resolved inputs -- zero RCA recomputation here."""

    tenant_id: str
    migration_id: str
    requested_by: str
    context_fingerprint: str
    rca_data: Mapping[str, Any] = field(default_factory=dict)  # P7C.15 producer's own `data` dict
    fabric_status: str = "UNKNOWN"
    validation_status: str = "UNKNOWN"


RemediationResolver = Callable[[IntelligenceRequest, IntelligenceContext], RemediationInputs]


def make_remediation_producer(resolver: RemediationResolver):
    def producer(request: IntelligenceRequest, context: IntelligenceContext) -> IntelligenceResult:
        inputs = resolver(request, context)
        if inputs is None:
            raise IntelligenceValidationError(
                "Remediation resolver returned no RemediationInputs. Refusing to fabricate a "
                "remediation recommendation with no RCA facts."
            )

        primary_hypothesis = str(inputs.rca_data.get("primary_hypothesis", ""))
        recipe = select_recipe(
            primary_hypothesis_label=primary_hypothesis,
            fabric_status=inputs.fabric_status,
            validation_status=inputs.validation_status,
        )

        if recipe is None:
            return IntelligenceResult(
                task=request.task,
                epistemic_type=EpistemicType.RECOMMENDATION,
                summary=f"No governed automated remediation recipe matches this cause for migration "
                f"{inputs.migration_id!r}; human escalation recommended.",
                explanation=Explanation(
                    summary="No canonical action exists for this specific RCA conclusion -- this module never "
                    "fabricates support for an action the canonical runtime does not have.",
                    supporting_facts=[f"primary_hypothesis={primary_hypothesis!r}"],
                ),
                confidence_evidence=ConfidenceEvidence(evidence_coverage=1.0),
                data={"migration_id": inputs.migration_id, "action_proposal": None, "recipe": None},
            )

        proposal = ActionProposal(
            action_type=recipe.action_type,
            tenant_id=inputs.tenant_id,
            target_resource_type="migration",
            target_resource_id=inputs.migration_id,
            requested_by=inputs.requested_by,
            context_fingerprint=inputs.context_fingerprint,
            risk_classification=recipe.risk,
            parameters={"primary_hypothesis": primary_hypothesis},
        )

        return IntelligenceResult(
            task=request.task,
            epistemic_type=EpistemicType.PROPOSAL,
            summary=f"Proposing governed remediation {recipe.action_type!r} for migration "
            f"{inputs.migration_id!r} (requires approval before any canonical effect).",
            explanation=Explanation(
                summary=recipe.trigger_description,
                supporting_facts=[f"primary_hypothesis={primary_hypothesis!r}", f"recipe_id={recipe.recipe_id}"],
                assumptions=[recipe.reversibility_note, recipe.verification_note],
            ),
            confidence_evidence=ConfidenceEvidence(evidence_coverage=1.0),
            data={
                "migration_id": inputs.migration_id,
                "recipe": recipe.to_dict(),
                "action_proposal": proposal.to_dict(),
            },
        )

    return producer
