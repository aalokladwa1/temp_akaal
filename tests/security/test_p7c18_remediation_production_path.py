"""tests/security/test_p7c18_remediation_production_path.py
==================================================================
P7C.18 production-path proof: real PipelineUnifiedCaller -> intelligence.
submit (task=RECOMMEND, capability=governed_remediation) -> real P7C.15 RCA
reuse. Proves the resulting ActionProposal integrates correctly with the
EXISTING, already-hostile-tested Group-1 ActionMediationGateway (via the
existing 'intelligence.mediation.evaluate' query) -- specifically that the
newly-registered L3 action_type requires governance approval and is never
self-executable, without re-testing the whole gateway (already covered by
P7C.1/P7C.6's own hostile suite, unaffected by this addition).
"""

from __future__ import annotations

import os
import tempfile

import pytest

from akaalIPC.security.context import ActorContext, ActorReference, CorrelationContext
from akaalIPC.transport.ports import CallerResultStatus
from tests.pipeline.conftest import authorized_caller, make_command, make_query


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


def _actor(org_id: str) -> ActorContext:
    return ActorContext(
        actor=ActorReference(actor_id=f"actor-{org_id}", actor_type="human", display_name="Test User"),
        organization_id=org_id, workspace_id="ws-main", project_id="proj-1",
    )


def _seed_migration(caller, migration_id, tenant_id):
    from akaalPipeline.contracts.enums import MigrationLifecycleState, MigrationMode
    from akaalPipeline.state.aggregates import MigrationAggregate

    agg = MigrationAggregate(
        migration_id=migration_id, revision=1, name=f"migration-{migration_id}",
        mode=MigrationMode.M1_BULK, state=MigrationLifecycleState.DRAFT,
        tenant_id=tenant_id, workspace_id="ws-main", project_id="proj-1",
    )
    caller.repository.save(agg)


def _submit_remediation(caller, actor, migration_id):
    payload = {
        "task": "RECOMMEND", "subject_type": "migration", "subject_id": migration_id,
        "subject_version": "v1", "capability": "governed_remediation",
        "parameters": {"migration_id": migration_id},
    }
    return caller.handle_command(make_command("intelligence.submit", payload, actor, CorrelationContext.new()))


class TestNoActionableCauseYieldsRecommendationOnly:
    def test_insufficient_rca_data_yields_no_proposal(self, caller):
        actor = _actor("tenant-alpha")
        _seed_migration(caller, "mig-1", "tenant-alpha")
        result = _submit_remediation(caller, actor, "mig-1")
        assert result.status == CallerResultStatus.OK
        assert result.result["result"]["data"]["action_proposal"] is None
        assert result.result["result"]["epistemic_type"] == "RECOMMENDATION"


class TestProposalIntegratesWithRealMediationGateway:
    def test_l3_action_requires_approval_through_real_gateway(self, caller):
        """Proves the newly-registered propose_remediation_pause_migration
        action_type is correctly gated L3 by the REAL, unmodified
        ActionMediationGateway/autonomy registry -- submitting it without an
        approval_reference is refused, exactly like every other L3 action."""
        actor = _actor("tenant-alpha")
        mediation_payload = {
            "action_type": "propose_remediation_pause_migration",
            "target_resource_type": "migration",
            "target_resource_id": "mig-1",
            "context_fingerprint": "ctx-fp-1",
            "current_context_fingerprint": "ctx-fp-1",
        }
        result = caller.handle_query(make_query("intelligence.mediation.evaluate", mediation_payload, actor, CorrelationContext.new()))
        assert result.status == CallerResultStatus.ERROR

    def test_self_approval_rejected_for_new_action_type(self, caller):
        actor = _actor("tenant-alpha")
        mediation_payload = {
            "action_type": "propose_remediation_pause_migration",
            "target_resource_type": "migration",
            "target_resource_id": "mig-1",
            "context_fingerprint": "ctx-fp-1",
            "current_context_fingerprint": "ctx-fp-1",
            "approval_reference": "some-approval-ref",
            "approver_id": actor.actor.actor_id,
        }
        result = caller.handle_query(make_query("intelligence.mediation.evaluate", mediation_payload, actor, CorrelationContext.new()))
        assert result.status == CallerResultStatus.ERROR
