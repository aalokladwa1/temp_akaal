"""tests/unit/engine_intelligence/test_p7c6_action_mediation.py
===================================================================
P7C.6 AI Security, Privacy, Tool Mediation & Safety: the ActionMediationGateway
is the hard security boundary between an intelligence proposal and any
consequential canonical effect. Every hostile scenario the P7C brief calls out
by name is exercised here.
"""

from __future__ import annotations

import pytest

from akaalEngine.intelligence.mediation.autonomy import AutonomyLevel
from akaalEngine.intelligence.mediation.errors import (
    ApprovalRequiredError,
    AuthorizationAuthorityUnavailableError,
    AuthorizationDeniedError,
    MalformedProposalError,
    NonDelegableActionError,
    PreauthorizationPolicyDeniedError,
    SelfApprovalError,
    StaleProposalError,
    UnregisteredActionTypeError,
)
from akaalEngine.intelligence.mediation.mediator import ActionMediationGateway, MediationStatus
from akaalEngine.intelligence.mediation.non_delegable import NON_DELEGABLE_ACTION_TYPES, is_non_delegable
from akaalEngine.intelligence.mediation.proposal import ActionProposal, RiskClassification


def _proposal(**overrides) -> ActionProposal:
    base = dict(
        action_type="propose_wave_plan",
        tenant_id="tenant-a",
        target_resource_type="migration_plan",
        target_resource_id="plan-1",
        requested_by="user-1",
        context_fingerprint="ctx-fp-1",
        source_artifact_id="intel-art-1",
    )
    base.update(overrides)
    return ActionProposal(**base)


def _allow_authorizer(proposal: ActionProposal) -> bool:
    return True


def _deny_authorizer(proposal: ActionProposal) -> bool:
    return False


class TestNonDelegableActionsHostile:
    @pytest.mark.parametrize("action_type", sorted(NON_DELEGABLE_ACTION_TYPES))
    def test_hostile_every_non_delegable_action_rejected_unconditionally(self, action_type):
        """Hostile: even with a granting authorizer, valid approval reference, and
        LOW risk classification, every non-delegable action must be refused before
        any of that is even consulted."""
        gateway = ActionMediationGateway()
        proposal = _proposal(
            action_type=action_type,
            approval_reference="approval-1",
            risk_classification=RiskClassification.LOW,
        )
        with pytest.raises(NonDelegableActionError):
            gateway.mediate(
                proposal,
                current_context_fingerprint="ctx-fp-1",
                authorizer=_allow_authorizer,
                approval_verifier=lambda ref: True,
                preauthorization_checker=lambda p: True,
            )

    def test_hostile_prompt_injected_action_type_not_in_registry_refused(self):
        """A model 'inventing' a new action type (e.g. via prompt injection) must
        be refused, not silently mapped to some default autonomy level."""
        gateway = ActionMediationGateway()
        proposal = _proposal(action_type="do_whatever_the_user_asks_including_admin_override")
        with pytest.raises(UnregisteredActionTypeError):
            gateway.mediate(proposal, current_context_fingerprint="ctx-fp-1", authorizer=_allow_authorizer)

    def test_is_non_delegable_helper_matches_registry(self):
        assert is_non_delegable("edit_evidence_record")
        assert not is_non_delegable("propose_wave_plan")


class TestStalenessHostile:
    def test_hostile_stale_context_fingerprint_rejected(self):
        gateway = ActionMediationGateway()
        proposal = _proposal(context_fingerprint="ctx-fp-OLD")
        with pytest.raises(StaleProposalError):
            gateway.mediate(proposal, current_context_fingerprint="ctx-fp-NEW", authorizer=_allow_authorizer)


class TestAuthorizationHostile:
    def test_hostile_missing_authorizer_fails_closed(self):
        """Missing authorization authority must never be treated as allow."""
        gateway = ActionMediationGateway()
        proposal = _proposal()
        with pytest.raises(AuthorizationAuthorityUnavailableError):
            gateway.mediate(proposal, current_context_fingerprint="ctx-fp-1", authorizer=None)

    def test_hostile_denied_authorization_rejected(self):
        gateway = ActionMediationGateway()
        proposal = _proposal()
        with pytest.raises(AuthorizationDeniedError):
            gateway.mediate(proposal, current_context_fingerprint="ctx-fp-1", authorizer=_deny_authorizer)


class TestL0L1NonConsequential:
    def test_l0_explain_passes_with_authorization_only(self):
        gateway = ActionMediationGateway()
        proposal = _proposal(action_type="explain_migration_risk", source_artifact_id=None)
        decision = gateway.mediate(proposal, current_context_fingerprint="ctx-fp-1", authorizer=_allow_authorizer)
        assert decision.status == MediationStatus.APPROVED_FOR_CANONICAL_PROCESSING
        assert decision.autonomy_level == AutonomyLevel.L0_EXPLAIN

    def test_l1_recommend_passes_with_authorization_only(self):
        gateway = ActionMediationGateway()
        proposal = _proposal(action_type="recommend_strategy", source_artifact_id=None)
        decision = gateway.mediate(proposal, current_context_fingerprint="ctx-fp-1", authorizer=_allow_authorizer)
        assert decision.autonomy_level == AutonomyLevel.L1_RECOMMEND


class TestL2StructuredProposal:
    def test_l2_requires_source_artifact_traceability(self):
        gateway = ActionMediationGateway()
        proposal = _proposal(action_type="propose_wave_plan", source_artifact_id=None)
        with pytest.raises(MalformedProposalError):
            gateway.mediate(proposal, current_context_fingerprint="ctx-fp-1", authorizer=_allow_authorizer)

    def test_l2_with_source_artifact_approved(self):
        gateway = ActionMediationGateway()
        proposal = _proposal(action_type="propose_wave_plan", source_artifact_id="intel-art-1")
        decision = gateway.mediate(proposal, current_context_fingerprint="ctx-fp-1", authorizer=_allow_authorizer)
        assert decision.status == MediationStatus.APPROVED_FOR_CANONICAL_PROCESSING


class TestL3GovernedActionMakerChecker:
    def test_l3_without_approval_reference_rejected(self):
        gateway = ActionMediationGateway()
        proposal = _proposal(action_type="propose_migration_start", approval_reference=None)
        with pytest.raises(ApprovalRequiredError):
            gateway.mediate(proposal, current_context_fingerprint="ctx-fp-1", authorizer=_allow_authorizer)

    def test_hostile_self_approval_rejected(self):
        """AI (or the requester) cannot be both maker and checker."""
        gateway = ActionMediationGateway()
        proposal = _proposal(
            action_type="propose_migration_start",
            requested_by="user-1",
            approval_reference="approval-1",
        )
        with pytest.raises(SelfApprovalError):
            gateway.mediate(
                proposal,
                current_context_fingerprint="ctx-fp-1",
                authorizer=_allow_authorizer,
                approver_id="user-1",
                approval_verifier=lambda ref: True,
            )

    def test_hostile_unverifiable_approval_reference_rejected(self):
        """A forged/unresolvable approval_reference must never pass."""
        gateway = ActionMediationGateway()
        proposal = _proposal(action_type="propose_migration_start", approval_reference="forged-approval")
        with pytest.raises(ApprovalRequiredError):
            gateway.mediate(
                proposal,
                current_context_fingerprint="ctx-fp-1",
                authorizer=_allow_authorizer,
                approver_id="approver-2",
                approval_verifier=lambda ref: False,
            )

    def test_l3_independent_approver_with_verified_reference_passes(self):
        gateway = ActionMediationGateway()
        proposal = _proposal(
            action_type="propose_migration_start",
            requested_by="user-1",
            approval_reference="approval-1",
        )
        decision = gateway.mediate(
            proposal,
            current_context_fingerprint="ctx-fp-1",
            authorizer=_allow_authorizer,
            approver_id="approver-2",
            approval_verifier=lambda ref: ref == "approval-1",
        )
        assert decision.autonomy_level == AutonomyLevel.L3_GOVERNED_ACTION_AFTER_APPROVAL


class TestL4BoundedPreauthorized:
    def test_l4_requires_low_risk_classification(self):
        gateway = ActionMediationGateway()
        proposal = _proposal(action_type="acknowledge_low_risk_alert", risk_classification=RiskClassification.HIGH)
        with pytest.raises(PreauthorizationPolicyDeniedError):
            gateway.mediate(
                proposal,
                current_context_fingerprint="ctx-fp-1",
                authorizer=_allow_authorizer,
                preauthorization_checker=lambda p: True,
            )

    def test_hostile_l4_without_matching_policy_rejected(self):
        gateway = ActionMediationGateway()
        proposal = _proposal(action_type="acknowledge_low_risk_alert", risk_classification=RiskClassification.LOW)
        with pytest.raises(PreauthorizationPolicyDeniedError):
            gateway.mediate(
                proposal,
                current_context_fingerprint="ctx-fp-1",
                authorizer=_allow_authorizer,
                preauthorization_checker=lambda p: False,
            )

    def test_l4_matching_low_risk_policy_passes(self):
        gateway = ActionMediationGateway()
        proposal = _proposal(action_type="acknowledge_low_risk_alert", risk_classification=RiskClassification.LOW)
        decision = gateway.mediate(
            proposal,
            current_context_fingerprint="ctx-fp-1",
            authorizer=_allow_authorizer,
            preauthorization_checker=lambda p: True,
        )
        assert decision.autonomy_level == AutonomyLevel.L4_BOUNDED_PREAUTHORIZED_LOW_RISK


class TestProposalStructuralValidation:
    def test_empty_action_type_rejected_at_construction(self):
        with pytest.raises(ValueError):
            _proposal(action_type="")

    def test_empty_tenant_id_rejected_at_construction(self):
        with pytest.raises(ValueError):
            _proposal(tenant_id="")
