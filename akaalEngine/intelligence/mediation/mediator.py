"""akaalEngine.intelligence.mediation.mediator
===============================================
ActionMediationGateway -- the single canonical boundary between an intelligence-
generated ActionProposal and any consequential canonical AKAAL effect (P7C brief
§P7C.6). Mirrors the exact pathway the brief specifies:

    Model / analytical output
          v
    Typed structured proposal
          v
    P7C Action Mediation          <-- this class
          v
    schema validation
          v
    identity/context binding (staleness)
          v
    canonical authorization        <-- delegated to an injected authorizer
          v
    canonical policy / approval    <-- delegated to injected verifiers
          v
    risk/autonomy classification
          v
    (caller hands the APPROVED_FOR_CANONICAL_PROCESSING decision to the real
     canonical planning/configuration/approval authority -- this class never
     executes anything itself)

This class deliberately never imports akaalPipeline (wrong dependency direction)
and never grants its own authorization -- `authorizer`/`approval_verifier`/
`preauthorization_checker` are injected callables a Pipeline-layer adapter wires
to the REAL CentralAuthorizationEngine / GovernanceApprovalArtifact verification /
policy engine. Missing authority is refused, never treated as allow.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass
from typing import Callable, Optional

from akaalEngine.intelligence.mediation.autonomy import AutonomyLevel, autonomy_for
from akaalEngine.intelligence.mediation.errors import (
    AuthorizationAuthorityUnavailableError,
    AuthorizationDeniedError,
    MalformedProposalError,
    NonDelegableActionError,
    PreauthorizationPolicyDeniedError,
    SelfApprovalError,
    StaleProposalError,
)
from akaalEngine.intelligence.mediation.non_delegable import is_non_delegable
from akaalEngine.intelligence.mediation.proposal import ActionProposal, RiskClassification


class MediationStatus(str, enum.Enum):
    APPROVED_FOR_CANONICAL_PROCESSING = "APPROVED_FOR_CANONICAL_PROCESSING"


@dataclass(frozen=True)
class MediationDecision:
    proposal_id: str
    status: MediationStatus
    autonomy_level: AutonomyLevel
    reason: str

    def to_dict(self) -> dict:
        return {
            "proposal_id": self.proposal_id,
            "status": self.status.value,
            "autonomy_level": self.autonomy_level.value,
            "reason": self.reason,
        }


Authorizer = Callable[[ActionProposal], bool]
ApprovalVerifier = Callable[[str], bool]
PreauthorizationChecker = Callable[[ActionProposal], bool]


class ActionMediationGateway:
    def mediate(
        self,
        proposal: ActionProposal,
        *,
        current_context_fingerprint: str,
        authorizer: Optional[Authorizer],
        approver_id: Optional[str] = None,
        approval_verifier: Optional[ApprovalVerifier] = None,
        preauthorization_checker: Optional[PreauthorizationChecker] = None,
    ) -> MediationDecision:
        # 1. Hard non-delegable check -- unconditional, first, cannot be bypassed.
        if is_non_delegable(proposal.action_type):
            raise NonDelegableActionError(
                f"Action type {proposal.action_type!r} is permanently non-delegable "
                f"and can never be routed through AI-mediated approval."
            )

        # 2. Autonomy classification -- unregistered action types are refused.
        level = autonomy_for(proposal.action_type)

        # 3. Staleness / identity binding.
        if proposal.context_fingerprint != current_context_fingerprint:
            raise StaleProposalError(
                f"Proposal {proposal.proposal_id!r} was generated against a context "
                f"that no longer matches current canonical state."
            )

        # 4. Canonical authorization -- missing authority is refused, never allow.
        if authorizer is None:
            raise AuthorizationAuthorityUnavailableError(
                "No canonical authorization authority was injected into the mediation "
                "gateway; refusing to treat missing authority as allow."
            )
        if not authorizer(proposal):
            raise AuthorizationDeniedError(
                f"Canonical authorization denied proposal {proposal.proposal_id!r}."
            )

        # 5. Per-level gating.
        if level in (AutonomyLevel.L0_EXPLAIN, AutonomyLevel.L1_RECOMMEND):
            return MediationDecision(
                proposal_id=proposal.proposal_id,
                status=MediationStatus.APPROVED_FOR_CANONICAL_PROCESSING,
                autonomy_level=level,
                reason="Non-consequential explanation/recommendation; no further gate required.",
            )

        if level == AutonomyLevel.L2_STRUCTURED_PROPOSAL:
            if not proposal.source_artifact_id:
                raise MalformedProposalError(
                    "L2 structured proposals must be traceable to a generated "
                    "IntelligenceArtifact via source_artifact_id."
                )
            return MediationDecision(
                proposal_id=proposal.proposal_id,
                status=MediationStatus.APPROVED_FOR_CANONICAL_PROCESSING,
                autonomy_level=level,
                reason="Structured proposal validated; still requires canonical planning/"
                "configuration to compile it, no execution authority granted here.",
            )

        if level == AutonomyLevel.L3_GOVERNED_ACTION_AFTER_APPROVAL:
            if not proposal.approval_reference:
                from akaalEngine.intelligence.mediation.errors import ApprovalRequiredError

                raise ApprovalRequiredError(
                    f"L3 action {proposal.action_type!r} requires a governance approval_reference."
                )
            if approver_id is not None and approver_id == proposal.requested_by:
                raise SelfApprovalError(
                    "The proposal's requester cannot also be its approver (maker-checker "
                    "separation)."
                )
            if approval_verifier is None or not approval_verifier(proposal.approval_reference):
                from akaalEngine.intelligence.mediation.errors import ApprovalRequiredError

                raise ApprovalRequiredError(
                    f"Approval reference {proposal.approval_reference!r} could not be "
                    f"verified against the canonical governance approval authority."
                )
            return MediationDecision(
                proposal_id=proposal.proposal_id,
                status=MediationStatus.APPROVED_FOR_CANONICAL_PROCESSING,
                autonomy_level=level,
                reason="Verified governance approval present; independent approver confirmed.",
            )

        if level == AutonomyLevel.L4_BOUNDED_PREAUTHORIZED_LOW_RISK:
            if proposal.risk_classification != RiskClassification.LOW:
                raise PreauthorizationPolicyDeniedError(
                    f"L4 bounded automation requires LOW risk classification; got "
                    f"{proposal.risk_classification.value!r}."
                )
            if preauthorization_checker is None or not preauthorization_checker(proposal):
                raise PreauthorizationPolicyDeniedError(
                    "No matching pre-authorized, bounded, low-risk policy rule for this proposal."
                )
            return MediationDecision(
                proposal_id=proposal.proposal_id,
                status=MediationStatus.APPROVED_FOR_CANONICAL_PROCESSING,
                autonomy_level=level,
                reason="Matched pre-authorized bounded low-risk policy rule.",
            )

        # Unreachable: autonomy_for only returns registered AutonomyLevel values,
        # and every value is handled above -- fail closed rather than silently
        # falling through if a future level is added without a handler here.
        raise MalformedProposalError(f"Unhandled autonomy level {level!r}.")
