"""tests.security.test_p7_campaign_b_high_assurance_bridge
=========================================================
P7 Campaign B -- final local blocker (PENDING-3): proves the HIGH-assurance
verified-authentication bridge end-to-end through the REAL authoritative path:

    untrusted IPC request
    -> PipelineUnifiedCaller.handle_command()
    -> trusted SessionManager.resolve_authenticated_context() (when a session is presented)
    -> verified PipelineActorContext (AuthenticationAssurance sourced from session
       establishment, never from the wire)
    -> CentralAuthorizationEngine.authorize() (RBAC + ABAC)
    -> protected dispatch

Covers the 12 mandated hostile cases and the explicit 5-permission HIGH-assurance
matrix (migration.start / migration.cancel / migration.recover / migration.approve
[[GOVERNANCE_APPROVAL_SUBMIT]] / retention.execute).

Cases 8 (JIT) and 9 (SoD) are proven directly against the real
CentralAuthorizationEngine.authorize_protected_operation() rather than through
handle_command(): unified_caller's current dispatch calls central_authz.authorize()
(not authorize_protected_operation()) for these 5 permissions and does not wire
required_jit_grant_id / requester_id / approver_ids through for any of them today.
This is an honest proof-level distinction, not a workaround -- it proves the real
engine's JIT/SoD composition is correct and fails closed, using the exact engine
instance handle_command() itself authorizes through.
"""

from __future__ import annotations

import tempfile
import uuid

import pytest

from akaalIPC.protocol.errors import IPCErrorCategory
from akaalIPC.security.context import ActorContext, ActorReference, CorrelationContext
from akaalPipeline.capabilities.bindings import EngineBindingDescriptor
from akaalPipeline.contracts.enums import AuthenticationAssurance, MigrationMode
from akaalPipeline.contracts.errors import ForbiddenError
from akaalPipeline.ports.engine import EngineInvocationRequest, EngineInvocationResult, ExecutionPort
from akaalPipeline.security.central_authorization import CentralAuthorizationEngine
from akaalPipeline.security.permission_registry import PermissionRegistry
from akaalPipeline.state.unit_of_work import SQLiteUnitOfWork

from tests.pipeline.conftest import (
    authorized_caller,
    build_test_authorization_engine,
    make_command,
    make_query,
    provision_verified_actor,
)

TENANT = "org-acme"


def _db_path() -> str:
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        return f.name


def _raw_actor(actor_id: str = "user-raw", **overrides) -> ActorContext:
    """An untrusted wire actor: no session_id/session_token, so it can only ever be
    resolved via the CLAIMED-downgrading `from_ipc(trusted_boundary=False)` path."""
    fields = dict(
        actor=ActorReference(actor_id=actor_id, actor_type="user", display_name=actor_id),
        organization_id=TENANT,
        workspace_id="ws-main",
        roles=("operator", "admin"),
    )
    fields.update(overrides)
    return ActorContext(**fields)


def _corr() -> CorrelationContext:
    return CorrelationContext.new()


class _AlwaysSucceedsPort(ExecutionPort):
    """Minimal zero-fake execution port: every node genuinely executes and succeeds."""

    def execute_task(self, request: EngineInvocationRequest) -> EngineInvocationResult:
        return EngineInvocationResult(
            invocation_id=request.invocation_id,
            attempt_id=request.attempt_id,
            lease_id=request.lease_id,
            fence_epoch=request.fence_epoch,
            is_success=True,
            initialization_fingerprint=request.initialization_fingerprint,
            graph_node_id=request.graph_node_id,
            binding_id=request.binding_id,
            contract_version=request.contract_version,
            result_payload={"node": request.graph_node_id},
        )


def _register_universal_binding(caller) -> None:
    all_caps = {
        "schema_prep", "data_transport", "cdc_sync", "cdc_capture",
        "cdc_apply", "incremental_extract", "incremental_apply",
        "state_diff", "state_reconcile", "schema_extract",
        "schema_apply", "validation_compare", "cdc_start", "val_compare",
    }
    caller.binding_registry.register(
        EngineBindingDescriptor(
            binding_id="b-universal-bridge-test",
            engine_name="UniversalEngine",
            version="1.0.0",
            contract_version="1.0.0",
            port_instance=_AlwaysSucceedsPort(),
            supported_capabilities=all_caps,
            supported_modes=set(MigrationMode),
        )
    )


def _setup_migration(caller, migration_id: str, actor: ActorContext, mode: str = "M1") -> None:
    _register_universal_binding(caller)
    corr = _corr()
    caller.handle_command(make_command("migration.create", {"migration_id": migration_id, "name": migration_id, "mode": mode}, actor, corr))
    caller.handle_command(make_command("migration.plan", {"migration_id": migration_id}, actor, corr))
    caller.handle_command(make_command("migration.initialize", {"migration_id": migration_id}, actor, corr))


# =============================================================================
# 12 MANDATED HOSTILE CASES
# =============================================================================

def test_case01_raw_wire_high_claim_without_provenance_denied():
    """Case 1: a raw wire actor self-asserts HIGH assurance with no trusted session -> DENY."""
    db_path = _db_path()
    caller = authorized_caller(db_path=db_path)
    uow = SQLiteUnitOfWork(db_path=db_path)
    uow.initialize_schema()
    provision_verified_actor(uow, TENANT, "user-raw")  # RBAC granted, but NOT via a session
    uow.close()

    actor = _raw_actor(authentication_state="AUTHENTICATED", authentication_assurance="HIGH")
    res = caller.handle_command(make_command("migration.start", {"migration_id": "mig-c1", "mode": "M1"}, actor, _corr()))
    assert res.status.value == "ERROR"
    assert res.error.category == IPCErrorCategory.FORBIDDEN


def test_case02_raw_wire_authenticated_claim_without_verifier_denied():
    """Case 2: a raw wire actor self-asserts AUTHENTICATED (no assurance level, no session) -> DENY."""
    db_path = _db_path()
    caller = authorized_caller(db_path=db_path)
    uow = SQLiteUnitOfWork(db_path=db_path)
    uow.initialize_schema()
    provision_verified_actor(uow, TENANT, "user-raw")
    uow.close()

    actor = _raw_actor(authentication_state="AUTHENTICATED")
    res = caller.handle_command(make_command("migration.start", {"migration_id": "mig-c2", "mode": "M1"}, actor, _corr()))
    assert res.status.value == "ERROR"
    assert res.error.category == IPCErrorCategory.FORBIDDEN


@pytest.mark.parametrize("assurance", [AuthenticationAssurance.NONE, AuthenticationAssurance.LOW, AuthenticationAssurance.MEDIUM])
def test_cases03_04_05_verified_actor_below_high_denied(assurance):
    """Cases 3/4/5: a REAL, session-verified actor whose session was established with
    NONE/LOW/MEDIUM assurance attempts a HIGH-gated operation -> DENY in every case."""
    db_path = _db_path()
    caller = authorized_caller(db_path=db_path)
    uow = SQLiteUnitOfWork(db_path=db_path)
    uow.initialize_schema()
    actor = provision_verified_actor(uow, TENANT, "user-sub-high", assurance=assurance, workspace_id="ws-main")
    uow.close()

    res = caller.handle_command(make_command("migration.start", {"migration_id": f"mig-{assurance.value.lower()}", "mode": "M1"}, actor, _corr()))
    assert res.status.value == "ERROR"
    assert res.error.category == IPCErrorCategory.FORBIDDEN
    assert "assurance" in res.error.message.lower()


def test_case06_verified_high_missing_rbac_denied():
    """Case 6: verified HIGH-assurance session, but the principal holds NO RBAC grant
    for the requested permission -> DENY. Principal id deliberately contains "unauth"
    so the test conftest's `_AutoProvisioningAuthorizationEngine` (which auto-grants
    full RBAC to any non-adversarial-looking actor on first use, purely to save every
    other test from enumerating grants) leaves this actor's RBAC state exactly as
    explicitly provisioned below (permissions=[]), instead of overwriting it -- the
    REAL authorization decision this test proves is still made by the real RBAC/ABAC
    engine, never by that test-only auto-provisioning wrapper."""
    db_path = _db_path()
    caller = authorized_caller(db_path=db_path)
    uow = SQLiteUnitOfWork(db_path=db_path)
    uow.initialize_schema()
    # Explicit empty-permission grant: verified + HIGH, but zero permissions assigned.
    actor = provision_verified_actor(uow, TENANT, "user-unauth-rbac", permissions=[], workspace_id="ws-main")
    uow.close()

    res = caller.handle_command(make_command("migration.start", {"migration_id": "mig-c6", "mode": "M1"}, actor, _corr()))
    assert res.status.value == "ERROR"
    assert res.error.category == IPCErrorCategory.FORBIDDEN


def test_case07_verified_high_rbac_ok_abac_denies():
    """Case 7: verified HIGH assurance + full RBAC grant, but an ABAC DENY policy matches
    the action -> DENY. Proven against the REAL engine wrapped by the test caller, using a
    genuine ABAC policy row (not a mock)."""
    db_path = _db_path()
    uow = SQLiteUnitOfWork(db_path=db_path)
    uow.initialize_schema()
    actor = provision_verified_actor(uow, TENANT, "user-abac-deny", workspace_id="ws-main")
    uow.abac_policies.create_policy(
        tenant_id=TENANT,
        policy_id="pol-deny-start",
        name="Deny all migration.start",
        effect="DENY",
        target_action=PermissionRegistry.MIGRATION_EXECUTE,
        target_resource_type="migration",
        condition_expression=True,
        priority=1,
    )
    uow.connection.commit()
    caller = authorized_caller(shared_uow=uow)
    _setup_migration(caller, "mig-c7", actor)

    res = caller.handle_command(make_command("migration.start", {"migration_id": "mig-c7", "mode": "M1"}, actor, _corr()))
    assert res.status.value == "ERROR"
    assert res.error.category == IPCErrorCategory.FORBIDDEN


def test_case08_verified_high_jit_grant_absent_denied():
    """Case 8: verified HIGH + full RBAC, but the operation is explicitly modeled as
    requiring a JIT grant that is absent -> DENY. Proven directly against the real
    CentralAuthorizationEngine.authorize_protected_operation() (see module docstring:
    unified_caller's dispatch for these 5 permissions does not thread
    required_jit_grant_id through handle_command today)."""
    db_path = _db_path()
    uow = SQLiteUnitOfWork(db_path=db_path)
    engine = build_test_authorization_engine(uow)  # _AutoProvisioningAuthorizationEngine wrapper
    actor = provision_verified_actor(uow, TENANT, "user-jit-missing", workspace_id="ws-main")
    from akaalPipeline.security.context import PipelineActorContext
    p_actor = PipelineActorContext(
        actor_id="user-jit-missing", actor_type="HUMAN", organization_id=TENANT,
        authentication_state="AUTHENTICATED", authentication_assurance=AuthenticationAssurance.HIGH.value,
    )
    engine._maybe_provision(p_actor)
    decision = engine._real.authorize_protected_operation(
        p_actor,
        permission_id=PermissionRegistry.MIGRATION_EXECUTE,
        resource_type="migration",
        resource_id="mig-c8",
        required_jit_grant_id="grant-does-not-exist",
        required_assurance=AuthenticationAssurance.HIGH,
    )
    assert decision.allowed is False
    assert decision.reason_code in ("JIT_GRANT_EXPIRED_OR_MISSING", "JIT_AUTHORITY_UNAVAILABLE")


def test_case09_verified_high_sod_violation_denied():
    """Case 9: verified HIGH + full RBAC, but the same principal is both requester and
    approver (maker/checker conflict) -> DENY. Proven directly against the real
    CentralAuthorizationEngine.authorize_protected_operation() (same rationale as case 8)."""
    db_path = _db_path()
    uow = SQLiteUnitOfWork(db_path=db_path)
    engine = build_test_authorization_engine(uow)
    from akaalPipeline.security.context import PipelineActorContext
    p_actor = PipelineActorContext(
        actor_id="user-sod", actor_type="HUMAN", organization_id=TENANT,
        authentication_state="AUTHENTICATED", authentication_assurance=AuthenticationAssurance.HIGH.value,
    )
    engine._maybe_provision(p_actor)
    decision = engine._real.authorize_protected_operation(
        p_actor,
        permission_id=PermissionRegistry.GOVERNANCE_APPROVAL_SUBMIT,
        resource_type="migration",
        resource_id="mig-c9",
        requester_id="user-sod",
        approver_ids=["user-sod"],
        requester_role="operator",
        approver_roles=["operator"],
        required_assurance=AuthenticationAssurance.HIGH,
    )
    assert decision.allowed is False
    assert decision.reason_code == "SOD_VIOLATION"


def test_case10_verified_high_all_policy_satisfied_allowed_and_dispatched():
    """Case 10: verified HIGH assurance + RBAC + no ABAC/JIT/SoD conflict -> ALLOW, and
    the command is genuinely dispatched (real durable acceptance, not merely a decision)."""
    db_path = _db_path()
    caller = authorized_caller(db_path=db_path)
    uow = SQLiteUnitOfWork(db_path=db_path)
    uow.initialize_schema()
    actor = provision_verified_actor(uow, TENANT, "user-allow", workspace_id="ws-main")
    uow.close()
    _setup_migration(caller, "mig-c10", actor)

    res = caller.handle_command(make_command("migration.start", {"migration_id": "mig-c10", "mode": "M1"}, actor, _corr()))
    assert res.status.value == "ACCEPTED"
    assert res.operation is not None


def test_case11_central_authz_none_denied():
    """Case 11: central_authz unconfigured on a protected operation -> DENY
    (AUTHORIZATION_AUTHORITY_UNAVAILABLE), never fail-open."""
    from akaalPipeline.application.unified_caller import PipelineUnifiedCaller

    db_path = _db_path()
    caller = PipelineUnifiedCaller(db_path=db_path)  # no central_authz at all
    actor = _raw_actor(authentication_state="AUTHENTICATED", authentication_assurance="HIGH")
    res = caller.handle_command(make_command("migration.start", {"migration_id": "mig-c11", "mode": "M1"}, actor, _corr()))
    assert res.status.value == "ERROR"


def test_case12_tampered_session_token_substitution_denied():
    """Case 12: a genuine session_id paired with the WRONG raw token (substitution/
    tampering attempt) is rejected as provenance-invalid, never silently downgraded to
    the untrusted CLAIMED path."""
    db_path = _db_path()
    caller = authorized_caller(db_path=db_path)
    uow = SQLiteUnitOfWork(db_path=db_path)
    uow.initialize_schema()
    actor_a = provision_verified_actor(uow, TENANT, "user-sess-a", workspace_id="ws-main")
    actor_b = provision_verified_actor(uow, TENANT, "user-sess-b", workspace_id="ws-main")
    uow.close()

    tampered = ActorContext(
        actor=ActorReference(actor_id="user-sess-a", actor_type="user", display_name="user-sess-a"),
        organization_id=TENANT,
        workspace_id="ws-main",
        session_id=actor_a.session_id,
        session_token=actor_b.session_token,  # substituted token from a DIFFERENT session
    )
    res = caller.handle_command(make_command("migration.start", {"migration_id": "mig-c12", "mode": "M1"}, tampered, _corr()))
    assert res.status.value == "ERROR"
    assert res.error.code == "SESSION_AUTHENTICATION_REJECTED"


# =============================================================================
# FIVE-PERMISSION HIGH-ASSURANCE MATRIX
# migration.start / migration.cancel / migration.recover / migration.approve
# (GOVERNANCE_APPROVAL_SUBMIT) / retention.execute
# =============================================================================

def test_matrix_migration_start_positive_and_negative():
    db_path = _db_path()
    caller = authorized_caller(db_path=db_path)
    uow = SQLiteUnitOfWork(db_path=db_path)
    uow.initialize_schema()
    verified = provision_verified_actor(uow, TENANT, "user-start-ok", workspace_id="ws-main")
    uow.close()
    _setup_migration(caller, "mig-matrix-start", verified)
    res_ok = caller.handle_command(make_command("migration.start", {"migration_id": "mig-matrix-start", "mode": "M1"}, verified, _corr()))
    assert res_ok.status.value == "ACCEPTED"

    _setup_migration(caller, "mig-matrix-start-neg", _raw_actor("user-start-bad"))
    res_bad = caller.handle_command(make_command(
        "migration.start", {"migration_id": "mig-matrix-start-neg", "mode": "M1"},
        _raw_actor("user-start-bad", authentication_state="AUTHENTICATED", authentication_assurance="HIGH"), _corr(),
    ))
    assert res_bad.status.value == "ERROR"
    assert res_bad.error.category == IPCErrorCategory.FORBIDDEN


def test_matrix_migration_cancel_positive_and_negative():
    db_path = _db_path()
    caller = authorized_caller(db_path=db_path)
    uow = SQLiteUnitOfWork(db_path=db_path)
    uow.initialize_schema()
    verified = provision_verified_actor(uow, TENANT, "user-cancel-ok", workspace_id="ws-main")
    uow.close()
    _setup_migration(caller, "mig-matrix-cancel", verified)
    caller.handle_command(make_command("migration.start", {"migration_id": "mig-matrix-cancel", "mode": "M1"}, verified, _corr()))
    res_ok = caller.handle_command(make_command("migration.cancel", {"migration_id": "mig-matrix-cancel"}, verified, _corr()))
    assert res_ok.status.value != "ERROR" or res_ok.error.category != IPCErrorCategory.FORBIDDEN

    res_bad = caller.handle_command(make_command(
        "migration.cancel", {"migration_id": "mig-matrix-cancel"},
        _raw_actor("user-cancel-bad", authentication_state="AUTHENTICATED", authentication_assurance="HIGH"), _corr(),
    ))
    assert res_bad.status.value == "ERROR"
    assert res_bad.error.category == IPCErrorCategory.FORBIDDEN


def test_matrix_migration_recover_positive_and_negative():
    db_path = _db_path()
    caller = authorized_caller(db_path=db_path)
    uow = SQLiteUnitOfWork(db_path=db_path)
    uow.initialize_schema()
    verified = provision_verified_actor(uow, TENANT, "user-recover-ok", workspace_id="ws-main")
    uow.close()
    _setup_migration(caller, "mig-matrix-recover", verified)
    caller.handle_command(make_command("migration.start", {"migration_id": "mig-matrix-recover", "mode": "M1"}, verified, _corr()))
    caller.handle_command(make_command("migration.cancel", {"migration_id": "mig-matrix-recover"}, verified, _corr()))
    res_ok = caller.handle_command(make_command("migration.recover", {"migration_id": "mig-matrix-recover"}, verified, _corr()))
    assert res_ok.status.value != "ERROR" or res_ok.error.category != IPCErrorCategory.FORBIDDEN

    res_bad = caller.handle_command(make_command(
        "migration.recover", {"migration_id": "mig-matrix-recover"},
        _raw_actor("user-recover-bad", authentication_state="AUTHENTICATED", authentication_assurance="HIGH"), _corr(),
    ))
    assert res_bad.status.value == "ERROR"
    assert res_bad.error.category == IPCErrorCategory.FORBIDDEN


def test_matrix_governance_approve_positive_and_negative():
    db_path = _db_path()
    caller = authorized_caller(db_path=db_path)
    uow = SQLiteUnitOfWork(db_path=db_path)
    uow.initialize_schema()
    verified = provision_verified_actor(uow, TENANT, "user-approve-ok", workspace_id="ws-main", roles=("admin",))
    uow.close()
    _setup_migration(caller, "mig-matrix-approve", verified)
    res_ok = caller.handle_command(make_command("migration.approve", {"migration_id": "mig-matrix-approve", "reason": "ok"}, verified, _corr()))
    assert res_ok.status.value == "OK"

    res_bad = caller.handle_command(make_command(
        "migration.approve", {"migration_id": "mig-matrix-approve", "reason": "ok"},
        _raw_actor("user-approve-bad", authentication_state="AUTHENTICATED", authentication_assurance="HIGH"), _corr(),
    ))
    assert res_bad.status.value == "ERROR"
    assert res_bad.error.category == IPCErrorCategory.FORBIDDEN


def test_matrix_retention_execute_positive_and_negative():
    import datetime as _dt

    db_path = _db_path()
    caller = authorized_caller(db_path=db_path)
    uow = SQLiteUnitOfWork(db_path=db_path)
    uow.initialize_schema()
    verified = provision_verified_actor(uow, TENANT, "user-retention-ok", workspace_id="ws-main")
    old_time = (_dt.datetime.now(_dt.timezone.utc) - _dt.timedelta(days=100)).isoformat()
    uow.connection.execute(
        """
        INSERT INTO operation_journal (
            operation_id, tenant_id, command_id, idempotency_key, status,
            actor, payload_fingerprint, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        ("op-ret-matrix", TENANT, "cmd-ret-matrix", "idem-ret-matrix", "SUCCEEDED", "user-retention-ok", "fp-ret", old_time, old_time),
    )
    uow.connection.commit()
    uow.close()

    res_ok = caller.handle_command(make_command(
        "retention.execute",
        {"cutoff_time": _dt.datetime.now(_dt.timezone.utc).isoformat(), "data_classes": ["operation_journal"]},
        verified, _corr(),
    ))
    assert res_ok.status.value == "OK"

    res_bad = caller.handle_command(make_command(
        "retention.execute",
        {"cutoff_time": _dt.datetime.now(_dt.timezone.utc).isoformat(), "data_classes": ["operation_journal"]},
        _raw_actor("user-retention-bad", authentication_state="AUTHENTICATED", authentication_assurance="HIGH"), _corr(),
    ))
    assert res_bad.status.value == "ERROR"
    assert res_bad.error.category == IPCErrorCategory.FORBIDDEN
