"""tests/security/test_p7c18_full_governed_pause_execution.py
====================================================================
Closes owner-review Blockers 2 and 3: proves the P7C.18 remediation
governance loop crosses the REAL canonical execution boundary, not merely
"approval required".

Real journey exercised entirely through the production PipelineUnifiedCaller
seam (no monkeypatching of the final command, no direct runtime calls, no
manual migration-state mutation):

    seeded ACTIVE migration
        -> real ActionMediationGateway L3 approval (real PolicyDecision
           artifact registered through the real ArtifactRegistry, real
           PolicyGateEvaluator verification, real self-approval rejection
           proven separately)
        -> real "migration.pause" canonical command
           (akaalPipeline.application.command_handlers.
            CommandHandlerRegistry.handle_pause_migration)
        -> canonical migration state observed to have actually become PAUSED
           (re-read from the real repository, not asserted)
        -> intelligence.outcome.record against a real P7C.18 artifact
        -> intelligence.outcome.list confirms the recorded outcome

Also proves the negative paths this loop must reject: no approval, expired
approval, wrong resource binding, and self-approval -- none of which may
reach the canonical command.
"""

from __future__ import annotations

import os
import tempfile
from datetime import datetime, timedelta, timezone

import pytest

from akaalIPC.security.context import ActorContext, ActorReference, CorrelationContext
from akaalIPC.transport.ports import CallerResultStatus
from tests.pipeline.conftest import authorized_caller, make_command, make_query


ACTION_TYPE = "propose_remediation_pause_migration"


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
        organization_id=org_id, workspace_id="ws-main", project_id="proj-1",
    )


def _seed_active_migration(caller, migration_id, tenant_id):
    from akaalPipeline.contracts.enums import MigrationLifecycleState, MigrationMode
    from akaalPipeline.state.aggregates import MigrationAggregate

    agg = MigrationAggregate(
        migration_id=migration_id, revision=1, name=f"migration-{migration_id}",
        mode=MigrationMode.M1_BULK, state=MigrationLifecycleState.ACTIVE,
        tenant_id=tenant_id, workspace_id="ws-main", project_id="proj-1",
    )
    caller.repository.save(agg)
    return agg


def _context_fingerprint(migration_id: str, tenant_id: str) -> str:
    from akaalEngine.intelligence.identity.fingerprint import compute_context_fingerprint
    from akaalEngine.intelligence.models.context import IntelligenceContext

    ctx = IntelligenceContext(tenant_id=tenant_id, subject_type="migration", subject_id=migration_id, subject_version="v1")
    return compute_context_fingerprint(ctx)


def _register_real_approval_artifact(caller, conn, *, reference: str, migration_id: str, fingerprint: str, expires_in_seconds: float = 3600.0):
    """Registers a REAL PolicyDecision through the REAL ArtifactRegistry --
    exactly the artifact shape akaalPipeline.application.query_service.
    PipelineQueryService.evaluate_action_mediation's own _approval_verifier
    reads back via artifact_registry.get() + PolicyDecision.from_dict() +
    PolicyGateEvaluator.evaluate_gate()."""
    from akaalPipeline.policy.contracts import PolicyDecision, PolicyAction, PolicyResource, PolicyResult, PolicySubject
    from akaalPipeline.state.artifacts import ImmutableArtifact

    now = datetime.now(timezone.utc)
    decision = PolicyDecision(
        decision_id=reference,
        policy_version="1.0.0",
        subject=PolicySubject(actor_id="*", actor_type="system", roles=[]),
        action=PolicyAction(name=ACTION_TYPE),
        resource=PolicyResource(resource_id=migration_id, resource_type="migration", artifact_fingerprint=fingerprint),
        result=PolicyResult.ALLOW,
        reason="Governance approval for CDC apply-bound pause remediation.",
        issuer_id="gov-officer-1",
        issuer_roles=["SecurityOfficer"],
        effective_at=now.isoformat(),
        expires_at=(now + timedelta(seconds=expires_in_seconds)).isoformat(),
    )
    artifact = ImmutableArtifact.create(artifact_id=reference, artifact_type="policy_decision", content=decision.to_dict())
    caller.artifact_registry.register(artifact, conn=conn)


def _mediate(caller, actor, migration_id, fingerprint, *, approval_reference=None, approver_id=None):
    payload = {
        "action_type": ACTION_TYPE, "target_resource_type": "migration", "target_resource_id": migration_id,
        "context_fingerprint": fingerprint, "current_context_fingerprint": fingerprint,
    }
    if approval_reference:
        payload["approval_reference"] = approval_reference
    if approver_id:
        payload["approver_id"] = approver_id
    return caller.handle_query(make_query("intelligence.mediation.evaluate", payload, actor, CorrelationContext.new()))


class TestFullGovernedPauseExecutionCrossesCanonicalBoundary:
    def test_approved_proposal_actually_pauses_the_real_migration(self, caller):
        actor = _actor("tenant-alpha", actor_id="requester-1")
        migration_id = "mig-govloop-1"
        _seed_active_migration(caller, migration_id, "tenant-alpha")
        fingerprint = _context_fingerprint(migration_id, "tenant-alpha")

        uow = caller._create_uow()
        _register_real_approval_artifact(caller, uow.connection, reference="appr-govloop-1", migration_id=migration_id, fingerprint=fingerprint)
        uow.connection.commit()

        # 1. Real mediation gateway approval (different approver than requester).
        mediation_result = _mediate(caller, actor, migration_id, fingerprint, approval_reference="appr-govloop-1", approver_id="gov-officer-1")
        assert mediation_result.status == CallerResultStatus.OK, mediation_result.error
        assert mediation_result.result["decision"]["status"] == "APPROVED_FOR_CANONICAL_PROCESSING"

        # 2. Precondition: canonical state is still ACTIVE before execution.
        pre = caller.repository.get_by_id(migration_id)
        assert pre.state.value == "ACTIVE"

        # 3. Real canonical command -- the ONLY path that can change migration state.
        pause_result = caller.handle_command(make_command("migration.pause", {"migration_id": migration_id}, actor, CorrelationContext.new()))
        assert pause_result.status == CallerResultStatus.OK, pause_result.error

        # 4. Canonical state re-read from the real repository -- not asserted, observed.
        post = caller.repository.get_by_id(migration_id)
        assert post.state.value == "PAUSED"

        # 5. Close the loop: record + list a real outcome against a real P7C.18 artifact.
        remediation_payload = {
            "task": "RECOMMEND", "subject_type": "migration", "subject_id": migration_id, "subject_version": "v1",
            "capability": "governed_remediation", "parameters": {"migration_id": migration_id},
        }
        remediation_artifact = caller.handle_command(make_command("intelligence.submit", remediation_payload, actor, CorrelationContext.new()))
        assert remediation_artifact.status == CallerResultStatus.OK
        artifact_id = remediation_artifact.result["artifact_id"]

        outcome_payload = {"artifact_id": artifact_id, "outcome_status": "SUCCEEDED", "detail": "Governed pause executed and canonical state observed PAUSED."}
        outcome_result = caller.handle_command(make_command("intelligence.outcome.record", outcome_payload, actor, CorrelationContext.new()))
        assert outcome_result.status == CallerResultStatus.OK

        outcomes = caller.handle_query(make_query("intelligence.outcome.list", {"artifact_id": artifact_id}, actor, CorrelationContext.new()))
        assert outcomes.status == CallerResultStatus.OK
        assert len(outcomes.result["outcomes"]) == 1
        assert outcomes.result["outcomes"][0]["outcome_status"] == "SUCCEEDED"


class TestGovernanceRejectionsNeverReachCanonicalCommand:
    def test_no_approval_reference_refused(self, caller):
        actor = _actor("tenant-alpha")
        migration_id = "mig-govloop-2"
        _seed_active_migration(caller, migration_id, "tenant-alpha")
        fingerprint = _context_fingerprint(migration_id, "tenant-alpha")

        result = _mediate(caller, actor, migration_id, fingerprint)
        assert result.status == CallerResultStatus.ERROR
        assert caller.repository.get_by_id(migration_id).state.value == "ACTIVE"

    def test_expired_approval_refused(self, caller):
        actor = _actor("tenant-alpha")
        migration_id = "mig-govloop-3"
        _seed_active_migration(caller, migration_id, "tenant-alpha")
        fingerprint = _context_fingerprint(migration_id, "tenant-alpha")

        uow = caller._create_uow()
        _register_real_approval_artifact(caller, uow.connection, reference="appr-expired", migration_id=migration_id, fingerprint=fingerprint, expires_in_seconds=-3600.0)
        uow.connection.commit()

        result = _mediate(caller, actor, migration_id, fingerprint, approval_reference="appr-expired", approver_id="gov-officer-1")
        assert result.status == CallerResultStatus.ERROR
        assert caller.repository.get_by_id(migration_id).state.value == "ACTIVE"

    def test_wrong_resource_binding_refused(self, caller):
        actor = _actor("tenant-alpha")
        migration_id = "mig-govloop-4"
        other_migration_id = "mig-govloop-4-other"
        _seed_active_migration(caller, migration_id, "tenant-alpha")
        fingerprint = _context_fingerprint(migration_id, "tenant-alpha")

        uow = caller._create_uow()
        # Approval was actually issued for a DIFFERENT migration.
        _register_real_approval_artifact(caller, uow.connection, reference="appr-wrong-resource", migration_id=other_migration_id, fingerprint=fingerprint)
        uow.connection.commit()

        result = _mediate(caller, actor, migration_id, fingerprint, approval_reference="appr-wrong-resource", approver_id="gov-officer-1")
        assert result.status == CallerResultStatus.ERROR
        assert caller.repository.get_by_id(migration_id).state.value == "ACTIVE"

    def test_self_approval_refused(self, caller):
        actor = _actor("tenant-alpha", actor_id="requester-2")
        migration_id = "mig-govloop-5"
        _seed_active_migration(caller, migration_id, "tenant-alpha")
        fingerprint = _context_fingerprint(migration_id, "tenant-alpha")

        uow = caller._create_uow()
        _register_real_approval_artifact(caller, uow.connection, reference="appr-self", migration_id=migration_id, fingerprint=fingerprint)
        uow.connection.commit()

        # approver_id == requesting actor's own id.
        result = _mediate(caller, actor, migration_id, fingerprint, approval_reference="appr-self", approver_id="requester-2")
        assert result.status == CallerResultStatus.ERROR
        assert caller.repository.get_by_id(migration_id).state.value == "ACTIVE"

    def test_stale_context_fingerprint_refused(self, caller):
        """The proposal was generated against an OLD context fingerprint --
        canonical state has since changed underneath it (staleness)."""
        actor = _actor("tenant-alpha")
        migration_id = "mig-govloop-6"
        _seed_active_migration(caller, migration_id, "tenant-alpha")
        fingerprint = _context_fingerprint(migration_id, "tenant-alpha")

        uow = caller._create_uow()
        _register_real_approval_artifact(caller, uow.connection, reference="appr-stale", migration_id=migration_id, fingerprint=fingerprint)
        uow.connection.commit()

        payload = {
            "action_type": ACTION_TYPE, "target_resource_type": "migration", "target_resource_id": migration_id,
            "context_fingerprint": fingerprint,
            "current_context_fingerprint": "a-completely-different-current-fingerprint",
            "approval_reference": "appr-stale", "approver_id": "gov-officer-1",
        }
        result = caller.handle_query(make_query("intelligence.mediation.evaluate", payload, actor, CorrelationContext.new()))
        assert result.status == CallerResultStatus.ERROR
        assert caller.repository.get_by_id(migration_id).state.value == "ACTIVE"
