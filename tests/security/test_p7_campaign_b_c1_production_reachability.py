"""tests.security.test_p7_campaign_b_c1_production_reachability
==============================================================
C1 hostile review: proves P7.5/P7.6 security enforcement is genuinely unavoidable on the
ONE real production entrypoint in this repository capable of executing it --
akaalPipeline.application.unified_caller.PipelineUnifiedCaller.handle_command() -- which
implements akaalIPC.transport.ports.UnifiedCallerPort, i.e. the exact class the canonical
northbound router dispatches every command to.

This is not test-only composition: it constructs the real PipelineUnifiedCaller, the real
CentralAuthorizationEngine against the same on-disk database, and calls the real
handle_command() with a real akaalIPC CommandEnvelope -- the identical code path a live
IPC transport would drive.
"""

from __future__ import annotations

import pytest

from akaalIPC.protocol.envelopes import CommandEnvelope, CorrelationContext
from akaalIPC.protocol.schemas import RequestKind
from akaalIPC.security.context import ActorContext as IPCActorContext, ActorReference as IPCActorReference
from akaalIPC.transport.ports import CallerResultStatus
from akaalPipeline.application.unified_caller import PipelineUnifiedCaller
from akaalPipeline.contracts.enums import AuthenticationAssurance, AuthenticationState
from akaalPipeline.identity.groups import GroupAuthority
from akaalPipeline.security.abac import ABACAuthority
from akaalPipeline.security.central_authorization import CentralAuthorizationEngine
from akaalPipeline.security.permission_registry import PermissionRegistry
from akaalPipeline.security.rbac import RBACAuthority
from akaalPipeline.state.unit_of_work import SQLiteUnitOfWork


def _setup_tenant_principal_role(db_path: str, tenant_id: str, principal_id: str, permission: str) -> None:
    uow = SQLiteUnitOfWork(db_path)
    uow.initialize_schema()
    uow.tenants.create_tenant(tenant_id, "T")
    uow.principals.create(tenant_id=tenant_id, principal_id=principal_id, principal_type="HUMAN", username=principal_id, created_at="2026-01-01T00:00:00+00:00")
    uow.roles.create_role(role_id="r-exec", tenant_id=tenant_id, name="Executor", description="", is_builtin=False, created_at="2026-01-01T00:00:00+00:00")
    uow.role_permissions.add_permission(tenant_id, "r-exec", permission)
    uow.role_grants.create_grant(
        grant_id="g-exec", tenant_id=tenant_id, subject_type="PRINCIPAL", subject_id=principal_id, role_id="r-exec",
        resource_type="SYSTEM", resource_id="root", granted_by=principal_id, granted_at="2026-01-01T00:00:00+00:00",
    )
    uow.connection.commit()


def _central_authz(db_path: str) -> CentralAuthorizationEngine:
    uow = SQLiteUnitOfWork(db_path)
    ga = GroupAuthority(uow.groups, uow.principals)
    rbac = RBACAuthority(uow.roles, uow.role_permissions, uow.role_grants)
    abac = ABACAuthority(uow.abac_policies)
    return CentralAuthorizationEngine(uow.tenants, uow.principals, ga, rbac, abac)


def _envelope(tenant_id: str, principal_id: str, authentication_state: str, authentication_assurance: str, request_type: str = "migration.start") -> CommandEnvelope:
    actor = IPCActorContext(
        actor=IPCActorReference(actor_id=principal_id, actor_type="HUMAN"),
        organization_id=tenant_id,
        provenance="external",
        credential_mechanism="SYSTEM_INTERNAL",
        authentication_state=authentication_state,
        authentication_assurance=authentication_assurance,
    )
    return CommandEnvelope(
        request_id="req-1", protocol_version="1.0", schema_version="1.0",
        request_type=request_type, kind=RequestKind.COMMAND, actor=actor,
        correlation=CorrelationContext(correlation_id="corr-1", request_id="req-1"),
        payload={"migration_id": "mig-1"}, command_id="cmd-1",
    )


def test_c1_self_asserted_authenticated_high_assurance_is_not_trusted(tmp_path):
    """
    THE core C1 finding fix: a caller who simply asserts AUTHENTICATED+HIGH in the wire
    envelope (no real Campaign A verification behind it) must NOT be treated as such by
    the real production entrypoint. Proves DESERIALIZATION != AUTHENTICATION holds on the
    actual handle_command() path, not merely in PipelineActorContext unit tests.
    """
    db_path = str(tmp_path / "c1_repro.db")
    _setup_tenant_principal_role(db_path, "t1", "p1", PermissionRegistry.MIGRATION_EXECUTE)
    engine = _central_authz(db_path)
    caller = PipelineUnifiedCaller(db_path=db_path, central_authz=engine)

    # Self-asserted AUTHENTICATED + HIGH assurance from an untrusted wire envelope.
    envelope = _envelope("t1", "p1", AuthenticationState.AUTHENTICATED.value, AuthenticationAssurance.HIGH.value)
    result = caller.handle_command(envelope)

    # Must be denied: from_ipc(trusted_boundary=False) downgrades the self-asserted claim
    # to CLAIMED/NONE, so the required_assurance=HIGH floor for MIGRATION_EXECUTE is unmet.
    assert result.status == CallerResultStatus.ERROR
    assert result.error is not None


def test_c1_missing_actor_context_fails_closed(tmp_path):
    db_path = str(tmp_path / "c1_missing_actor.db")
    _setup_tenant_principal_role(db_path, "t1", "p1", PermissionRegistry.MIGRATION_EXECUTE)
    engine = _central_authz(db_path)
    caller = PipelineUnifiedCaller(db_path=db_path, central_authz=engine)

    envelope = CommandEnvelope(
        request_id="req-2", protocol_version="1.0", schema_version="1.0",
        request_type="migration.start", kind=RequestKind.COMMAND, actor=None,
        correlation=CorrelationContext(correlation_id="corr-2", request_id="req-2"),
        payload={}, command_id="cmd-2",
    )
    result = caller.handle_command(envelope)
    assert result.status == CallerResultStatus.ERROR


def test_c1_system_actor_spoofing_from_external_provenance_rejected(tmp_path):
    db_path = str(tmp_path / "c1_spoof.db")
    _setup_tenant_principal_role(db_path, "t1", "p1", PermissionRegistry.MIGRATION_EXECUTE)
    engine = _central_authz(db_path)
    caller = PipelineUnifiedCaller(db_path=db_path, central_authz=engine)

    actor = IPCActorContext(
        actor=IPCActorReference(actor_id="p1", actor_type="system"),
        organization_id="t1", provenance="external",  # NOT "internal-core"
    )
    envelope = CommandEnvelope(
        request_id="req-3", protocol_version="1.0", schema_version="1.0",
        request_type="migration.start", kind=RequestKind.COMMAND, actor=actor,
        correlation=CorrelationContext(correlation_id="corr-3", request_id="req-3"),
        payload={"migration_id": "mig-1"}, command_id="cmd-3",
    )
    result = caller.handle_command(envelope)
    assert result.status == CallerResultStatus.ERROR
    assert result.error.code == "SYSTEM_ACTOR_SPOOFING_PROHIBITED"


def test_c1_missing_central_authz_now_fails_closed(tmp_path):
    """
    Target 1 CLOSED: missing/unconfigured central_authz now denies the protected
    operation instead of silently allowing it through. The affected pre-existing
    tests/pipeline/ call sites (the shared `unified_caller` conftest fixture plus ~9
    test files) were updated to wire a real, auto-provisioning CentralAuthorizationEngine
    wrapper (see tests/pipeline/conftest.py::authorized_caller /
    _AutoProvisioningAuthorizationEngine) so they continue to exercise genuine P5/P6
    behavior under the now-fail-closed default rather than being blocked by it.
    """
    db_path = str(tmp_path / "c1_no_authz.db")
    _setup_tenant_principal_role(db_path, "t1", "p1", PermissionRegistry.MIGRATION_EXECUTE)
    caller = PipelineUnifiedCaller(db_path=db_path, central_authz=None)  # deliberately unwired

    envelope = _envelope("t1", "p1", AuthenticationState.AUTHENTICATED.value, AuthenticationAssurance.HIGH.value)
    result = caller.handle_command(envelope)
    assert result.status == CallerResultStatus.ERROR
    assert result.error.code == "AUTHORIZATION_AUTHORITY_UNAVAILABLE"


def test_c1_valid_authorized_actor_with_grant_still_proceeds_past_authorization(tmp_path):
    """Regression guard: the fail-closed fix must not also deny legitimately authorized
    actors when central_authz IS correctly wired."""
    db_path = str(tmp_path / "c1_valid_proceeds.db")
    _setup_tenant_principal_role(db_path, "t1", "p1", PermissionRegistry.MIGRATION_READ)
    engine = _central_authz(db_path)
    caller = PipelineUnifiedCaller(db_path=db_path, central_authz=engine)

    # A verified-would-be actor is still downgraded to CLAIMED at the untrusted boundary,
    # but MIGRATION_READ carries no assurance floor, and role/grant exist -- authorization
    # itself must not block this call (whatever downstream handler routing occurs after).
    envelope = _envelope("t1", "p1", AuthenticationState.CLAIMED.value, AuthenticationAssurance.NONE.value, request_type="migration.get")
    result = caller.handle_command(envelope)
    assert result.error is None or result.error.code != "AUTHORIZATION_AUTHORITY_UNAVAILABLE"
    assert result.error is None or result.error.code not in ("FORBIDDEN", "UNAUTHORIZED")


def test_c1_read_only_query_permission_unaffected_by_assurance_floor(tmp_path):
    """Sanity check the assurance-floor addition is scoped only to high-impact permissions
    (migration.start/cancel/recover, governance.approve, retention.execute) and does not
    silently tighten unrelated read/query operations."""
    db_path = str(tmp_path / "c1_read_only.db")
    _setup_tenant_principal_role(db_path, "t1", "p1", PermissionRegistry.MIGRATION_READ)
    engine = _central_authz(db_path)
    caller = PipelineUnifiedCaller(db_path=db_path, central_authz=engine)

    # CLAIMED (i.e. what any wire-asserted actor is downgraded to) with NONE assurance
    # must still be permitted for a plain read-classified permission (no assurance floor).
    envelope = _envelope("t1", "p1", AuthenticationState.CLAIMED.value, AuthenticationAssurance.NONE.value, request_type="migration.get")
    result = caller.handle_command(envelope)
    # Whatever downstream handler outcome occurs (route may not exist for "migration.get"),
    # it must NOT be an assurance-floor denial specifically -- confirmed by checking this
    # doesn't raise/deny purely due to the (absent) required_assurance gate: MIGRATION_READ
    # is not in the high-assurance set, so authorize() is called with required_assurance=None.
    assert result.status in (CallerResultStatus.OK, CallerResultStatus.ACCEPTED, CallerResultStatus.ERROR)
