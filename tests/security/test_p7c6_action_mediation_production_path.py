"""tests/security/test_p7c6_action_mediation_production_path.py
====================================================================
P7C.6 Action Mediation Gateway: production-path proof through the real
PipelineUnifiedCaller / CentralAuthorizationEngine, not a mocked handler.
"""

from __future__ import annotations

import os
import tempfile

import pytest

from akaalIPC.security.context import ActorContext, ActorReference, CorrelationContext
from akaalIPC.transport.ports import CallerResultStatus
from tests.pipeline.conftest import authorized_caller, make_query


@pytest.fixture
def temp_db_path():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    yield path
    try:
        os.remove(path)
    except OSError:
        pass


@pytest.fixture
def caller(temp_db_path):
    uc = authorized_caller(db_path=temp_db_path)
    yield uc
    uc.close()


def _actor(org_id: str, actor_id: str = None) -> ActorContext:
    return ActorContext(
        actor=ActorReference(actor_id=actor_id or f"actor-{org_id}", actor_type="human", display_name="Test User"),
        organization_id=org_id,
        workspace_id="ws-main",
        project_id="proj-1",
    )


def _payload(**overrides) -> dict:
    payload = {
        "action_type": "propose_wave_plan",
        "target_resource_type": "migration_plan",
        "target_resource_id": "plan-1",
        "context_fingerprint": "ctx-fp-1",
        "current_context_fingerprint": "ctx-fp-1",
        "source_artifact_id": "intel-art-1",
    }
    payload.update(overrides)
    return payload


class TestActionMediationProductionPath:
    def test_authorized_actor_l2_proposal_approved(self, caller):
        actor = _actor("tenant-alpha")
        result = caller.handle_query(make_query("intelligence.mediation.evaluate", _payload(), actor, CorrelationContext.new()))
        assert result.status == CallerResultStatus.OK
        assert result.result["decision"]["status"] == "APPROVED_FOR_CANONICAL_PROCESSING"

    def test_non_delegable_action_rejected_through_real_seam(self, caller):
        actor = _actor("tenant-alpha")
        payload = _payload(action_type="edit_evidence_record")
        result = caller.handle_query(make_query("intelligence.mediation.evaluate", payload, actor, CorrelationContext.new()))
        assert result.status == CallerResultStatus.ERROR

    def test_hostile_unauthorized_actor_denied(self, caller):
        actor = _actor("tenant-alpha", actor_id="attacker-unauth-user")
        result = caller.handle_query(make_query("intelligence.mediation.evaluate", _payload(), actor, CorrelationContext.new()))
        assert result.status == CallerResultStatus.ERROR

    def test_hostile_stale_proposal_rejected_through_real_seam(self, caller):
        actor = _actor("tenant-alpha")
        payload = _payload(context_fingerprint="ctx-fp-STALE", current_context_fingerprint="ctx-fp-CURRENT")
        result = caller.handle_query(make_query("intelligence.mediation.evaluate", payload, actor, CorrelationContext.new()))
        assert result.status == CallerResultStatus.ERROR

    def test_hostile_missing_source_artifact_for_l2_rejected(self, caller):
        actor = _actor("tenant-alpha")
        payload = _payload(source_artifact_id=None)
        result = caller.handle_query(make_query("intelligence.mediation.evaluate", payload, actor, CorrelationContext.new()))
        assert result.status == CallerResultStatus.ERROR

    def test_hostile_forged_approval_reference_rejected_for_l3(self, caller):
        actor = _actor("tenant-alpha")
        payload = _payload(action_type="propose_migration_start", approval_reference="forged-approval-does-not-exist")
        result = caller.handle_query(make_query("intelligence.mediation.evaluate", payload, actor, CorrelationContext.new()))
        assert result.status == CallerResultStatus.ERROR

    def test_hostile_cross_tenant_actor_gets_own_tenant_binding_not_target_tenant(self, caller):
        """The proposal's tenant_id is always derived from the actor's own
        authenticated tenant, never from anything the caller can put in the
        payload -- there is no tenant_id field accepted from payload at all."""
        actor = _actor("tenant-beta")
        result = caller.handle_query(make_query("intelligence.mediation.evaluate", _payload(), actor, CorrelationContext.new()))
        assert result.status == CallerResultStatus.OK
        assert result.result["proposal"]["tenant_id"] == "tenant-beta"
