"""tests/pipeline/conftest.py
========================
Pytest fixtures and helpers for akaalPipeline test suite.
"""

from __future__ import annotations

import os
import tempfile
import uuid
import pytest

os.environ.setdefault("AKAAL_GATEWAY_RECEIPT_SECRET", "akaal-test-provisioned-secret-v1")

from akaalIPC.protocol.envelopes import CommandEnvelope, QueryEnvelope
from akaalIPC.protocol.schemas import RequestKind
from akaalIPC.security.context import ActorContext, ActorReference, CorrelationContext
from akaalPipeline.application.unified_caller import PipelineUnifiedCaller
from akaalPipeline.contracts.enums import AuthenticationAssurance, CredentialMechanism
from akaalPipeline.identity.groups import GroupAuthority
from akaalPipeline.identity.sessions import SessionManager
from akaalPipeline.security.abac import ABACAuthority
from akaalPipeline.security.central_authorization import CentralAuthorizationEngine
from akaalPipeline.security.context import PipelineActorContext
from akaalPipeline.security.permission_registry import PermissionRegistry
from akaalPipeline.security.rbac import RBACAuthority
from akaalPipeline.state.unit_of_work import SQLiteUnitOfWork


# Actor/tenant name fragments that mark a test identity as INTENTIONALLY adversarial --
# such identities must NEVER be auto-provisioned with a permission grant, or the hostile/
# negative-path tests that use them (expecting denial) would be defeated.
_ADVERSARIAL_NAME_FRAGMENTS = ("attack", "bad", "evil", "unauth", "hostile", "malicious", "rogue", "spoof")


def _looks_adversarial(*names: str) -> bool:
    lowered = " ".join(n.lower() for n in names if n)
    return any(frag in lowered for frag in _ADVERSARIAL_NAME_FRAGMENTS)


def build_test_authorization_engine(uow: SQLiteUnitOfWork) -> CentralAuthorizationEngine:
    """
    Real CentralAuthorizationEngine (RBAC+ABAC, no bypass). Production authorization now
    fails closed when central_authz is unconfigured (see unified_caller.py), so every test
    that drives PipelineUnifiedCaller.handle_command()/handle_query() needs a real engine.
    Returned wrapped in _AutoProvisioningAuthorizationEngine (see below) so that
    dynamically-generated test actor IDs (many tests build actor_id=f"actor-{tenant}" or
    similar at call time, not from a fixed fixture) are legitimately RBAC-granted on
    first use rather than requiring an unmaintainable enumeration of every test's actor.
    """
    uow.initialize_schema()
    ga = GroupAuthority(uow.groups, uow.principals)
    rbac = RBACAuthority(uow.roles, uow.role_permissions, uow.role_grants)
    abac = ABACAuthority(uow.abac_policies)
    real_engine = CentralAuthorizationEngine(uow.tenants, uow.principals, ga, rbac, abac)
    return _AutoProvisioningAuthorizationEngine(real_engine, uow)


class _AutoProvisioningAuthorizationEngine:
    """
    Test-only wrapper around the REAL CentralAuthorizationEngine. Before delegating to the
    real engine's authorize()/authorize_with_decision()/authorize_protected_operation(),
    ensures the requesting actor's tenant/principal exist and hold a genuine, real RBAC
    all-permissions grant -- unless the actor/tenant name looks adversarial, in which case
    it is left deliberately unprovisioned so hostile/negative-path tests (which construct
    an "attacker"/"unauth-*"/"*-bad"/"*-evil" identity and expect denial) still fail
    closed exactly as they did before. The actual authorization DECISION is always made by
    the real engine's real RBAC/ABAC logic -- this wrapper only handles test-fixture
    provisioning, never the decision itself.
    """

    def __init__(self, real_engine: CentralAuthorizationEngine, uow: SQLiteUnitOfWork) -> None:
        self._real = real_engine
        self._uow = uow
        self._provisioned: set[tuple[str, str]] = set()

    def _maybe_provision(self, actor_context) -> None:
        tenant_id = getattr(actor_context, "tenant_id", None) or getattr(actor_context, "organization_id", None)
        principal_id = getattr(actor_context, "principal_id", None) or getattr(actor_context, "actor_id", None)
        if not tenant_id or not principal_id:
            return
        key = (tenant_id, principal_id)
        if key in self._provisioned:
            return
        if _looks_adversarial(tenant_id, principal_id):
            return  # deliberately left unprovisioned -- hostile/negative tests must still see denial
        self._provisioned.add(key)

        uow = self._uow
        if not uow.tenants.get_by_id(tenant_id):
            try:
                uow.tenants.create_tenant(tenant_id, tenant_id)
            except Exception:
                pass
        if not uow.principals.get_by_id(tenant_id, principal_id):
            try:
                uow.principals.create(tenant_id=tenant_id, principal_id=principal_id, principal_type="HUMAN", username=principal_id)
            except Exception:
                pass
        role_id = "test-all-permissions"
        try:
            uow.roles.create_role(role_id=role_id, tenant_id=tenant_id, name="Test All-Permissions Role")
        except Exception:
            pass
        for perm in PermissionRegistry.ALL_PERMISSIONS:
            try:
                uow.role_permissions.assign_permission(tenant_id, role_id, perm, principal_id)
            except Exception:
                pass
        try:
            uow.role_grants.grant_role(f"grant-{role_id}-{principal_id}", tenant_id, "PRINCIPAL", principal_id, role_id, "SYSTEM", "root", principal_id)
        except Exception:
            pass
        uow.connection.commit()

    def authorize(self, actor_context, *args, **kwargs):
        self._maybe_provision(actor_context)
        return self._real.authorize(actor_context, *args, **kwargs)

    def authorize_with_decision(self, actor_context, *args, **kwargs):
        self._maybe_provision(actor_context)
        return self._real.authorize_with_decision(actor_context, *args, **kwargs)

    def authorize_protected_operation(self, actor_context, *args, **kwargs):
        self._maybe_provision(actor_context)
        return self._real.authorize_protected_operation(actor_context, *args, **kwargs)

    def get_authoritative_roles(self, tenant_id: str, principal_id: str, *args, **kwargs):
        return self._real.get_authoritative_roles(tenant_id, principal_id, *args, **kwargs)



def authorized_caller(db_path: str = None, shared_uow: SQLiteUnitOfWork = None, **kwargs) -> PipelineUnifiedCaller:
    """
    Drop-in replacement for `PipelineUnifiedCaller(db_path=...)` /
    `PipelineUnifiedCaller(shared_uow=...)` that also wires a real, auto-provisioning
    CentralAuthorizationEngine wrapper, so tests continue to exercise real P5/P6 behavior
    rather than being blocked by the (correct) fail-closed authorization default.
    """
    uow = shared_uow or SQLiteUnitOfWork(db_path=db_path)
    engine = build_test_authorization_engine(uow)
    kwargs.setdefault("session_manager", build_session_manager(uow))
    return PipelineUnifiedCaller(shared_uow=uow, central_authz=engine, **kwargs)


def build_session_manager(uow: SQLiteUnitOfWork) -> SessionManager:
    """Real SessionManager wired to this test's UnitOfWork -- the same durable session
    authority PipelineUnifiedCaller's trusted bridge resolves through in production."""
    return SessionManager(session_repo=uow.sessions, principal_repo=uow.principals, tenant_repo=uow.tenants)


def provision_verified_actor(
    uow: SQLiteUnitOfWork,
    tenant_id: str,
    principal_id: str,
    *,
    assurance: AuthenticationAssurance = AuthenticationAssurance.HIGH,
    credential_mechanism: CredentialMechanism = CredentialMechanism.OIDC_ID_TOKEN,
    permissions=None,
    workspace_id: str = None,
    project_id: str = None,
    environment: str = None,
    roles: tuple = (),
    display_name: str = None,
) -> ActorContext:
    """
    Explicitly establishes a REAL, durable, trusted authentication session for a test
    actor -- simulating what a genuine Campaign A federation/MFA verification would have
    already produced -- and grants exactly the RBAC permissions requested (defaulting to
    every registered permission for convenience). This is provisioning by EXPLICIT
    scenario setup, never by inspecting the actor's name/tenant string, so it works
    identically for a HIGH-assurance positive test as it does for one deliberately named
    to look adversarial.

    Returns an IPC-level `ActorContext` carrying `session_id`/`session_token` so callers
    can hand it straight to PipelineUnifiedCaller.handle_command() and exercise the real
    trusted-session bridge (akaalPipeline.identity.sessions.SessionManager.
    resolve_authenticated_context) instead of the untrusted wire-claim path.
    """
    if not uow.tenants.get_by_id(tenant_id):
        uow.tenants.create_tenant(tenant_id, tenant_id)
    if not uow.principals.get_by_id(tenant_id, principal_id):
        uow.principals.create(tenant_id=tenant_id, principal_id=principal_id, principal_type="HUMAN", username=principal_id)

    role_id = f"verified-role-{principal_id}"
    try:
        uow.roles.create_role(role_id=role_id, tenant_id=tenant_id, name="Explicitly Provisioned Verified-Actor Role")
    except Exception:
        pass
    for perm in (permissions if permissions is not None else PermissionRegistry.ALL_PERMISSIONS):
        try:
            uow.role_permissions.assign_permission(tenant_id, role_id, perm, principal_id)
        except Exception:
            pass
    try:
        uow.role_grants.grant_role(f"grant-{role_id}", tenant_id, "PRINCIPAL", principal_id, role_id, "SYSTEM", "root", principal_id)
    except Exception:
        pass
    for r in (roles or ()):
        try:
            uow.roles.create_role(role_id=r, tenant_id=tenant_id, name=f"Explicitly Provisioned Role {r}")
        except Exception:
            pass
        try:
            uow.role_grants.grant_role(f"grant-{r}-{principal_id}", tenant_id, "PRINCIPAL", principal_id, r, "SYSTEM", "root", principal_id)
        except Exception:
            pass
    uow.connection.commit()

    session_mgr = build_session_manager(uow)
    session = session_mgr.create_session(
        tenant_id=tenant_id,
        principal_id=principal_id,
        authentication_assurance=assurance,
        credential_mechanism=credential_mechanism,
        trust_domain=tenant_id,
    )
    uow.connection.commit()

    return ActorContext(
        actor=ActorReference(actor_id=principal_id, actor_type="user", display_name=display_name or principal_id),
        organization_id=tenant_id,
        workspace_id=workspace_id,
        project_id=project_id,
        environment=environment,
        roles=tuple(roles),
        session_id=session.session_id,
        session_token=session.token,
        provenance="verified-test-session",
    )


def make_command(request_type: str, payload: dict, actor: ActorContext, correlation: CorrelationContext, idempotency_key: str = None) -> CommandEnvelope:
    return CommandEnvelope(
        request_id=f"req-{uuid.uuid4().hex[:12]}",
        command_id=f"cmd-{uuid.uuid4().hex[:12]}",
        request_type=request_type,
        protocol_version="1.0.0",
        schema_version="1.0",
        payload=payload,
        kind=RequestKind.COMMAND,
        actor=actor,
        correlation=correlation,
        idempotency_key=idempotency_key,
    )


def make_query(request_type: str, payload: dict, actor: ActorContext, correlation: CorrelationContext) -> QueryEnvelope:
    return QueryEnvelope(
        request_id=f"req-{uuid.uuid4().hex[:12]}",
        request_type=request_type,
        protocol_version="1.0.0",
        schema_version="1.0",
        payload=payload,
        kind=RequestKind.QUERY,
        actor=actor,
        correlation=correlation,
    )



@pytest.fixture
def temp_db_path():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        path = f.name
    return path


@pytest.fixture
def sqlite_uow(temp_db_path):
    uow = SQLiteUnitOfWork(db_path=temp_db_path)
    yield uow
    uow.close()


@pytest.fixture
def unified_caller(temp_db_path):
    return authorized_caller(db_path=temp_db_path)


@pytest.fixture
def ipc_actor():
    return ActorContext(
        actor=ActorReference(actor_id="user-100", actor_type="user", display_name="Test Operator"),
        organization_id="org-acme",
        workspace_id="ws-main",
        project_id="proj-db",
        environment="production",
        roles=("operator", "admin"),
        scopes=("migration.read", "migration.write"),
    )


@pytest.fixture
def verified_ipc_actor(temp_db_path):
    """
    Opt-in variant of `ipc_actor` for tests that need to exercise a HIGH-assurance-gated
    operation (migration.start/cancel/recover, governance.approve, retention.execute)
    through the REAL trusted session bridge, instead of getting denied for lacking
    assurance evidence they were never meant to be testing. Carries a REAL, durably
    provisioned session (via akaalPipeline.identity.sessions.SessionManager, the same
    trusted authority PipelineUnifiedCaller's production bridge resolves through) bound
    to the SAME `temp_db_path` the test's own `authorized_caller(db_path=temp_db_path)`
    must be constructed against. Kept separate from the default `ipc_actor` (which stays
    cheap and session-less) so this real per-test session establishment is only paid for
    by tests that actually need it, and so tests exercising DENIAL for insufficient/absent
    assurance are unaffected.
    """
    uow = SQLiteUnitOfWork(db_path=temp_db_path)
    uow.initialize_schema()
    actor = provision_verified_actor(uow, tenant_id="org-acme", principal_id="user-100", roles=("operator", "admin"))
    uow.close()
    return ActorContext(
        actor=ActorReference(actor_id="user-100", actor_type="user", display_name="Test Operator"),
        organization_id="org-acme",
        workspace_id="ws-main",
        project_id="proj-db",
        environment="production",
        roles=("operator", "admin"),
        scopes=("migration.read", "migration.write"),
        session_id=actor.session_id,
        session_token=actor.session_token,
    )


@pytest.fixture
def pipeline_actor(ipc_actor):
    return PipelineActorContext.from_ipc(ipc_actor)


@pytest.fixture
def ipc_correlation():
    return CorrelationContext.new()
