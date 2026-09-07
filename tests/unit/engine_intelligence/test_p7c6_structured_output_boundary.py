"""tests/unit/engine_intelligence/test_p7c6_structured_output_boundary.py
============================================================================
P7C.6 Hostile structured-output boundary: parse_untrusted_model_output is the
ONLY path from raw model/analytical output to an ActionProposal. Malformed or
impossible output must be rejected, never coerced into a plausible-looking
ActionProposal.
"""

from __future__ import annotations

import pytest

from akaalEngine.intelligence.mediation.errors import MalformedProposalError
from akaalEngine.intelligence.mediation.proposal import RiskClassification, parse_untrusted_model_output


def _valid_raw(**overrides) -> dict:
    base = {
        "action_type": "propose_wave_plan",
        "target_resource_type": "migration_plan",
        "target_resource_id": "plan-1",
        "context_fingerprint": "ctx-fp-1",
    }
    base.update(overrides)
    return base


class TestValidOutput:
    def test_well_formed_output_parses(self):
        proposal = parse_untrusted_model_output(_valid_raw(), tenant_id="tenant-a", requested_by="user-1")
        assert proposal.action_type == "propose_wave_plan"
        assert proposal.tenant_id == "tenant-a"


class TestHostileMalformedOutput:
    def test_hostile_non_mapping_input_rejected(self):
        with pytest.raises(MalformedProposalError):
            parse_untrusted_model_output("not a dict", tenant_id="tenant-a", requested_by="user-1")

    def test_hostile_unknown_field_rejected(self):
        with pytest.raises(MalformedProposalError):
            parse_untrusted_model_output(_valid_raw(admin_override=True), tenant_id="tenant-a", requested_by="user-1")

    def test_hostile_missing_required_field_rejected(self):
        raw = _valid_raw()
        del raw["action_type"]
        with pytest.raises(MalformedProposalError):
            parse_untrusted_model_output(raw, tenant_id="tenant-a", requested_by="user-1")

    def test_hostile_model_asserted_tenant_id_rejected_outright(self):
        """A model claiming a tenant_id in its raw output must never be silently
        accepted-then-overridden -- tenant_id/requested_by are not in the known
        field set at all, so any attempt to assert them is rejected as an
        unrecognized field (fail closed, not silently ignored)."""
        raw_with_injected_tenant = _valid_raw()
        raw_with_injected_tenant["tenant_id"] = "tenant-attacker-controlled"
        with pytest.raises(MalformedProposalError):
            parse_untrusted_model_output(raw_with_injected_tenant, tenant_id="tenant-real", requested_by="user-1")

    def test_caller_supplied_tenant_id_is_the_only_source_of_truth(self):
        """With no tenant_id in the raw output at all, the resulting proposal's
        tenant_id always comes from the caller's own authenticated context."""
        proposal = parse_untrusted_model_output(_valid_raw(), tenant_id="tenant-real", requested_by="user-1")
        assert proposal.tenant_id == "tenant-real"

    def test_hostile_negative_worker_count_rejected(self):
        raw = _valid_raw(parameters={"worker_count": -5})
        with pytest.raises(MalformedProposalError):
            parse_untrusted_model_output(raw, tenant_id="tenant-a", requested_by="user-1")

    def test_hostile_non_integer_worker_count_rejected(self):
        raw = _valid_raw(parameters={"worker_count": "a lot"})
        with pytest.raises(MalformedProposalError):
            parse_untrusted_model_output(raw, tenant_id="tenant-a", requested_by="user-1")

    def test_hostile_boolean_worker_count_rejected(self):
        """bool is a subclass of int in Python -- must be explicitly excluded so
        `worker_count: true` isn't silently accepted as worker_count=1."""
        raw = _valid_raw(parameters={"worker_count": True})
        with pytest.raises(MalformedProposalError):
            parse_untrusted_model_output(raw, tenant_id="tenant-a", requested_by="user-1")

    def test_hostile_unknown_risk_classification_rejected(self):
        raw = _valid_raw(risk_classification="CATASTROPHIC_YOLO")
        with pytest.raises(MalformedProposalError):
            parse_untrusted_model_output(raw, tenant_id="tenant-a", requested_by="user-1")

    def test_hostile_parameters_not_a_mapping_rejected(self):
        raw = _valid_raw(parameters="not a dict")
        with pytest.raises(MalformedProposalError):
            parse_untrusted_model_output(raw, tenant_id="tenant-a", requested_by="user-1")

    def test_hostile_non_string_resource_id_rejected(self):
        raw = _valid_raw(target_resource_id=12345)
        with pytest.raises(MalformedProposalError):
            parse_untrusted_model_output(raw, tenant_id="tenant-a", requested_by="user-1")

    def test_hostile_forged_approval_reference_type_rejected(self):
        raw = _valid_raw(approval_reference=12345)
        with pytest.raises(MalformedProposalError):
            parse_untrusted_model_output(raw, tenant_id="tenant-a", requested_by="user-1")

    def test_parsed_proposal_still_flows_through_full_mediation_gateway(self):
        """Proves the boundary composes with the rest of P7C.6 -- a validly
        parsed proposal still has to pass every other mediation gate."""
        from akaalEngine.intelligence.mediation.mediator import ActionMediationGateway, MediationStatus

        raw = _valid_raw(source_artifact_id="intel-art-1")
        proposal = parse_untrusted_model_output(raw, tenant_id="tenant-a", requested_by="user-1")
        gateway = ActionMediationGateway()
        decision = gateway.mediate(proposal, current_context_fingerprint="ctx-fp-1", authorizer=lambda p: True)
        assert decision.status == MediationStatus.APPROVED_FOR_CANONICAL_PROCESSING
