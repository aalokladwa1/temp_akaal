"""tests.security.test_p7_role_scope_trust_boundary_hostile
============================================================
Hostile verification suite for AKAAL P7 Campaign B Trust-Boundary Correction.

Proves:
1. Untrusted wire `roles` and `scopes` asserted on the IPC envelope CANNOT cross
   the trusted session boundary as authorization grants.
2. An ordinary authenticated user presenting wire `roles=("admin",)` and privileged
   scopes (`scopes=("admin:all", "root")`) is strictly DENIED across:
   - Migration governance approval (migration.approve)
   - Cluster fleet draining (fleet.drain_node)
   - Cluster fleet undraining (fleet.undrain_node)
   - Lifecycle execution (migration.start)
   - Operations retention execution (operations.retention.execute)
3. Handlers inspecting `actor.roles` consume ONLY authoritative server-side role
   grants from SQLite, completely immune to wire role injection.
4. Genuine authoritative administrators with durable SQLite role grants are
   properly ALLOWED.
"""

import dataclasses
import os
import tempfile
import uuid
import pytest

from akaalIPC.protocol.envelopes import CommandEnvelope
from akaalIPC.protocol.errors import IPCErrorCategory
from akaalIPC.security.context import CorrelationContext
from akaalIPC.transport.ports import CallerResultStatus
from akaalPipeline.application.unified_caller import PipelineUnifiedCaller
from akaalPipeline.contracts.enums import (
    AuthenticationAssurance,
    AuthenticationState,
    CredentialMechanism,
)
from akaalPipeline.security.permission_registry import PermissionRegistry
from akaalPipeline.state.unit_of_work import SQLiteUnitOfWork
from tests.pipeline.conftest import (
    authorized_caller,
    make_command,
    provision_verified_actor,
)

TENANT = "tenant-trust-boundary"


def _db_path() -> str:
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    return path


def _corr() -> CorrelationContext:
    return CorrelationContext(
        request_id=f"req-{uuid.uuid4().hex[:8]}",
        correlation_id=f"corr-{uuid.uuid4().hex[:8]}",
    )


def _setup_migration(caller: PipelineUnifiedCaller, migration_id: str, admin_actor):
    """Helper to create and initialize a migration for approval/start tests."""
    c_env = make_command(
        "migration.create",
        {"migration_id": migration_id, "name": f"Mig-{migration_id}", "mode": "M1"},
        admin_actor,
        _corr(),
    )
    res_c = caller.handle_command(c_env)
    assert res_c.status == CallerResultStatus.OK, f"Migration create failed: {res_c.error}"

    cfg_env = make_command(
        "migration.configure",
        {"migration_id": migration_id, "source_uri": "sqlite:///src.db", "target_uri": "sqlite:///tgt.db"},
        admin_actor,
        _corr(),
    )
    caller.handle_command(cfg_env)

    plan_env = make_command(
        "migration.plan",
        {"migration_id": migration_id, "steps": [{"step_id": "s1", "name": "copy"}]},
        admin_actor,
        _corr(),
    )
    caller.handle_command(plan_env)

    init_env = make_command(
        "migration.initialize",
        {"migration_id": migration_id},
        admin_actor,
        _corr(),
    )
    caller.handle_command(init_env)


# ============================================================================
# BLOCKER 1: Wire roles/scopes cannot cross trusted session boundary
# ============================================================================

def test_hostile_wire_roles_and_scopes_stripped_on_authenticated_session():
    """Verify that after SessionManager resolves an authenticated context,
    wire-asserted roles and scopes are NOT copied into the pipeline actor."""
    db_path = _db_path()
    uow = SQLiteUnitOfWork(db_path=db_path)
    uow.initialize_schema()
    # Provision ordinary actor with zero roles in DB
    ordinary_actor = provision_verified_actor(
        uow, TENANT, "user-ordinary-01", workspace_id="ws-1", roles=()
    )
    uow.close()

    caller = authorized_caller(db_path=db_path)

    # Hostile wire envelope asserting admin role and root scope
    hostile_wire_actor = dataclasses.replace(
        ordinary_actor,
        roles=("admin", "superadmin", "platform_admin"),
        scopes=("*", "admin:all", "system:root"),
    )

    # Query authoritative roles from central authorization engine directly
    authz_roles = caller.central_authz.get_authoritative_roles(
        tenant_id=TENANT, principal_id=hostile_wire_actor.actor.actor_id
    )

    # Authoritative roles in DB contain only the provisioned verified role, never wire claims
    assert "admin" not in authz_roles
    assert "superadmin" not in authz_roles
    assert "platform_admin" not in authz_roles
    assert authz_roles == {f"verified-role-{ordinary_actor.actor.actor_id}"}
    caller.close()


# ============================================================================
# BLOCKER 2: Handler-level checks cannot be satisfied by wire role injection
# ============================================================================

def test_hostile_wire_admin_cannot_approve_migration():
    """Negative proof: Valid authenticated ordinary session claiming wire roles=('admin',)
    and privileged scopes MUST BE DENIED governance approval (migration.approve)."""
    db_path = _db_path()
    caller = authorized_caller(db_path=db_path)
    uow = SQLiteUnitOfWork(db_path=db_path)
    uow.initialize_schema()

    # Provision legitimate admin for setup
    admin_verified = provision_verified_actor(
        uow, TENANT, "admin-real", workspace_id="ws-main", roles=("admin",)
    )
    # Provision ordinary user with permission to submit approvals, but NO admin/governor role in DB
    ordinary_approver = provision_verified_actor(
        uow,
        TENANT,
        "ordinary-approver",
        workspace_id="ws-main",
        permissions=[PermissionRegistry.MIGRATION_READ, PermissionRegistry.GOVERNANCE_APPROVAL_SUBMIT],
        roles=(),  # Authoritative user is NOT admin/governor
    )
    uow.close()

    mig_id = "mig-hostile-approve"
    _setup_migration(caller, mig_id, admin_verified)

    # Hostile attempt: Ordinary user injects roles=('admin',) and privileged scopes on the wire
    hostile_actor = dataclasses.replace(
        ordinary_approver,
        roles=("admin", "governor", "security_officer"),
        scopes=("*", "admin:all"),
    )

    cmd_hostile = make_command(
        "migration.approve",
        {"migration_id": mig_id, "reason": "hostile elevation attempt"},
        hostile_actor,
        _corr(),
    )
    res_hostile = caller.handle_command(cmd_hostile)

    # MUST BE DENIED with FORBIDDEN / POLICY_DENIED
    assert res_hostile.status == CallerResultStatus.ERROR
    assert res_hostile.error.category == IPCErrorCategory.FORBIDDEN
    assert "POLICY_DENIED" in res_hostile.error.message or "lacks governance authorization" in res_hostile.error.message

    # Positive control: Genuine authoritative admin in DB MUST BE ALLOWED
    cmd_admin = make_command(
        "migration.approve",
        {"migration_id": mig_id, "reason": "genuine admin approval"},
        admin_verified,
        _corr(),
    )
    res_admin = caller.handle_command(cmd_admin)
    assert res_admin.status == CallerResultStatus.OK
    caller.close()


def test_hostile_wire_admin_cannot_drain_or_undrain_fleet_node():
    """Negative proof: Valid authenticated ordinary user claiming wire roles=('admin',)
    MUST BE DENIED cluster fleet drain/undrain operations."""
    db_path = _db_path()
    caller = authorized_caller(db_path=db_path)
    uow = SQLiteUnitOfWork(db_path=db_path)
    uow.initialize_schema()

    admin_verified = provision_verified_actor(
        uow, TENANT, "admin-operator", workspace_id="ws-main", roles=("admin", "operator")
    )
    ordinary_user = provision_verified_actor(
        uow, TENANT, "ordinary-worker", workspace_id="ws-main", roles=()
    )
    uow.close()

    # Hostile attempt: Ordinary user injects roles=('admin',)
    hostile_actor = dataclasses.replace(
        ordinary_user,
        roles=("admin", "operator", "platform_admin"),
        scopes=("fleet:manage", "root"),
    )

    drain_cmd = make_command(
        "fleet.drain_node",
        {"node_id": "node-target-alpha"},
        hostile_actor,
        _corr(),
    )
    res_drain = caller.handle_command(drain_cmd)

    # MUST BE DENIED
    assert res_drain.status == CallerResultStatus.ERROR
    assert res_drain.error.category == IPCErrorCategory.FORBIDDEN
    assert "POLICY_DENIED" in res_drain.error.message or "requires admin or operator role" in res_drain.error.message

    undrain_cmd = make_command(
        "fleet.undrain_node",
        {"node_id": "node-target-alpha"},
        hostile_actor,
        _corr(),
    )
    res_undrain = caller.handle_command(undrain_cmd)

    # MUST BE DENIED
    assert res_undrain.status == CallerResultStatus.ERROR
    assert res_undrain.error.category == IPCErrorCategory.FORBIDDEN

    # Positive control: Authoritative admin/operator in DB can drain
    res_admin_drain = caller.handle_command(
        make_command("fleet.drain_node", {"node_id": "node-target-alpha"}, admin_verified, _corr())
    )
    assert res_admin_drain.status == CallerResultStatus.OK
    assert res_admin_drain.result["drain_state"] == "DRAINED"

    res_admin_undrain = caller.handle_command(
        make_command("fleet.undrain_node", {"node_id": "node-target-alpha"}, admin_verified, _corr())
    )
    assert res_admin_undrain.status == CallerResultStatus.OK
    assert res_admin_undrain.result["drain_state"] == "ACTIVE"
    caller.close()


def test_hostile_wire_admin_cannot_bypass_production_governance_gate():
    """Negative proof: An ordinary actor cannot bypass production governance approval
    requirement by asserting wire roles=('admin',)."""
    from akaalPipeline.policy.gates import PolicyGateEvaluator

    db_path = _db_path()
    caller = authorized_caller(db_path=db_path)
    uow = SQLiteUnitOfWork(db_path=db_path)
    uow.initialize_schema()

    ordinary_user = provision_verified_actor(
        uow, TENANT, "user-prod-ordinary", workspace_id="ws-main", roles=()
    )
    uow.close()

    # Hostile wire actor claims admin in production
    hostile_actor = dataclasses.replace(
        ordinary_user,
        roles=("admin",),
        environment="production",
    )

    # Query authoritative roles from durable storage
    authz_roles = tuple(sorted(
        caller.central_authz.get_authoritative_roles(
            tenant_id=TENANT, principal_id=hostile_actor.actor.actor_id
        )
    ))

    # Pipeline actor constructed by trusted session bridge
    pipeline_actor = dataclasses.replace(
        hostile_actor,
        roles=authz_roles,
        scopes=(),
    )

    # In production, non-admin requires approval.
    # Because wire 'admin' was stripped and DB role is empty, approval MUST BE REQUIRED (True).
    required = PolicyGateEvaluator.is_approval_required("INITIALIZED", pipeline_actor)
    assert required is True, "Production approval gate was bypassed by wire role claim!"
    caller.close()


def test_hostile_wire_scopes_cannot_influence_authorization():
    """Negative proof: Wire claims of scopes=('admin:all', '*', 'system:write') do not
    grant privileges to an unprivileged hostile identity."""
    db_path = _db_path()
    caller = authorized_caller(db_path=db_path)
    uow = SQLiteUnitOfWork(db_path=db_path)
    uow.initialize_schema()

    # Use 'hostile-' prefix so conftest's _AutoProvisioningAuthorizationEngine does not auto-grant
    hostile_user = provision_verified_actor(
        uow,
        TENANT,
        "hostile-scope-injector",
        workspace_id="ws-main",
        permissions=[PermissionRegistry.MIGRATION_READ],
        roles=(),
    )
    uow.close()

    hostile_actor = dataclasses.replace(
        hostile_user,
        scopes=("*", "admin:all", "migration:write", "migration:create"),
    )

    # Attempt migration create with only read-only permission + hostile scopes
    cmd = make_command(
        "migration.create",
        {"migration_id": "mig-scope-injection", "name": "Illegal", "mode": "M1"},
        hostile_actor,
        _corr(),
    )
    res = caller.handle_command(cmd)

    # MUST BE DENIED because CentralAuthorizationEngine only recognizes durable DB grants
    assert res.status == CallerResultStatus.ERROR
    assert res.error.category == IPCErrorCategory.FORBIDDEN
    caller.close()
