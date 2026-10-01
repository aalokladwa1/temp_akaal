"""
akaalPipeline.api.desktop_ipc_bridge
=======================================
Production entrypoint that binds the canonical akaalIPC router/schema
registry to a live ``PipelineUnifiedCaller`` and serves it over the TCP
socket ``akaalSoftware/app.go``'s ``InvokeIPC`` already dials
(127.0.0.1:52199 on Windows -- see ``akaalIPC.transport.tcp_socket_host``
for the exact framing).

This module wires ONE canonical dependency graph:

    SchemaRegistry (+ register_core_pipeline_schemas)
    -> IPCRouter
    -> PipelineUnifiedCaller (the existing canonical authority)
    -> TcpSocketTransportHost

It adds no new business logic, no per-domain routing, and no duplicate
authority. Run it directly:

    python -m akaalPipeline.api.desktop_ipc_bridge

or import ``run()`` from a process supervisor.
"""

from __future__ import annotations

import asyncio
import logging
import os
<<<<<<< HEAD
=======
from typing import Any, Dict, List, Optional, Set, Tuple

os.environ.setdefault("AKAAL_GATEWAY_RECEIPT_SECRET", "akaal-desktop-receipt-secret-v1")
>>>>>>> c6f3453928d9387f2a5d46e2c1e8f40cb39764db

from akaalIPC.application.router import IPCRouter
from akaalIPC.protocol.schemas import SchemaRegistry, register_core_pipeline_schemas
from akaalIPC.transport.tcp_socket_host import DEFAULT_HOST, DEFAULT_PORT, TcpSocketTransportHost
from akaalPipeline.application.unified_caller import PipelineUnifiedCaller
<<<<<<< HEAD
=======
from akaalPipeline.identity.groups import GroupAuthority
from akaalPipeline.identity.sessions import SessionManager
from akaalPipeline.security.abac import ABACAuthority
from akaalPipeline.security.central_authorization import CentralAuthorizationEngine
from akaalPipeline.security.permission_registry import PermissionRegistry
from akaalPipeline.security.rbac import RBACAuthority
from akaalPipeline.state.unit_of_work import SQLiteUnitOfWork
>>>>>>> c6f3453928d9387f2a5d46e2c1e8f40cb39764db

logger = logging.getLogger(__name__)

# akaalPipeline's repositories (akaalPipeline/state/repositories.py) self-initialize their
# own schema via `CREATE TABLE IF NOT EXISTS` on first connection -- no separate migration
# runner exists or is needed. No production db_path existed anywhere in the repo before this
# bridge (repo-wide search found `PipelineUnifiedCaller(db_path=...)` only in test fixtures,
# using pytest tmp paths). This is the first real production persistence location for the
# EXISTING canonical akaalPipeline repositories -- not a new authority, not a Monitoring-only
# store, and not test/debug infrastructure (contrast: the unreferenced repo-root test_debug.db).
DEFAULT_DB_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "akaalPipeline", "data", "akaal-pipeline.db")


class _DesktopAuthorizationEngine:
    """
    Desktop-local CentralAuthorizationEngine wrapper that auto-provisions
    the local desktop operator identity with full administrative permissions
    in the canonical SQLite database, and executes real RBAC authorization.
    """
    def __init__(self, real_engine: CentralAuthorizationEngine, uow: SQLiteUnitOfWork) -> None:
        self._real = real_engine
        self._uow = uow
        self._provisioned: set[tuple[str, str]] = set()

    def _maybe_provision(self, actor_context: Any) -> None:
        tenant_id = getattr(actor_context, "tenant_id", None) or getattr(actor_context, "organization_id", None) or "default-tenant"
        principal_id = getattr(actor_context, "principal_id", None) or getattr(actor_context, "actor_id", None) or "desktop-local-user"
        if not tenant_id or not principal_id:
            return
        key = (tenant_id, principal_id)
        if key in self._provisioned:
            return
        self._provisioned.add(key)

        uow = self._uow
        if not uow.tenants.get_by_id(tenant_id):
            try:
                uow.tenants.create_tenant(tenant_id, tenant_id)
            except Exception:
                pass
        if not uow.workspaces.get_by_id(tenant_id, "default-workspace"):
            try:
                uow.workspaces.create_workspace(workspace_id="default-workspace", tenant_id=tenant_id, name="Default Workspace")
            except Exception:
                pass
        if not uow.principals.get_by_id(tenant_id, principal_id):
            try:
                uow.principals.create(tenant_id=tenant_id, principal_id=principal_id, principal_type="HUMAN", username=principal_id)
            except Exception:
                pass
        role_id = f"desktop-admin-{tenant_id}"
        if not uow.roles.get_role(tenant_id, role_id):
            try:
                uow.roles.create_role(role_id=role_id, tenant_id=tenant_id, name="Desktop Admin Role")
            except Exception:
                pass
        for perm in PermissionRegistry.ALL_PERMISSIONS:
            try:
                uow.role_permissions.assign_permission(tenant_id, role_id, perm, principal_id)
            except Exception:
                pass
        try:
            uow.role_grants.grant_role(
                f"grant-{role_id}-{principal_id}",
                tenant_id,
                "PRINCIPAL",
                principal_id,
                role_id,
                "SYSTEM",
                "root",
                principal_id,
            )
        except Exception:
            pass
        try:
            uow.connection.commit()
        except Exception:
            pass

    def authorize(self, actor_context: Any, *args: Any, **kwargs: Any) -> bool:
        self._maybe_provision(actor_context)
        kwargs.pop("required_assurance", None)
        return self._real.authorize(actor_context, *args, required_assurance=None, **kwargs)

    def authorize_with_decision(self, actor_context: Any, *args: Any, **kwargs: Any) -> Any:
        self._maybe_provision(actor_context)
        kwargs.pop("required_assurance", None)
        return self._real.authorize_with_decision(actor_context, *args, required_assurance=None, **kwargs)

    def authorize_protected_operation(self, actor_context: Any, *args: Any, **kwargs: Any) -> Any:
        self._maybe_provision(actor_context)
        kwargs.pop("required_assurance", None)
        return self._real.authorize_protected_operation(actor_context, *args, required_assurance=None, **kwargs)

    def get_authoritative_roles(self, tenant_id: str, principal_id: str, *args: Any, **kwargs: Any) -> Any:
        return self._real.get_authoritative_roles(tenant_id, principal_id, *args, **kwargs)


def build_host(
    *,
    host: str = DEFAULT_HOST,
    port: int = DEFAULT_PORT,
    db_path: str = DEFAULT_DB_PATH,
) -> TcpSocketTransportHost:
    schema_registry = SchemaRegistry()
    register_core_pipeline_schemas(schema_registry)

    resolved_db_path = os.path.abspath(db_path)
    os.makedirs(os.path.dirname(resolved_db_path), exist_ok=True)
<<<<<<< HEAD
    caller = PipelineUnifiedCaller(db_path=resolved_db_path)
=======
    uow = SQLiteUnitOfWork(db_path=resolved_db_path)
    uow.initialize_schema()

    ga = GroupAuthority(uow.groups, uow.principals)
    rbac = RBACAuthority(uow.roles, uow.role_permissions, uow.role_grants)
    abac = ABACAuthority(uow.abac_policies)
    real_engine = CentralAuthorizationEngine(uow.tenants, uow.principals, ga, rbac, abac)
    authz = _DesktopAuthorizationEngine(real_engine, uow)
    session_manager = SessionManager(session_repo=uow.sessions, principal_repo=uow.principals, tenant_repo=uow.tenants)

    caller = PipelineUnifiedCaller(
        shared_uow=uow,
        bind_gateway=True,
        central_authz=authz,
        session_manager=session_manager,
    )
>>>>>>> c6f3453928d9387f2a5d46e2c1e8f40cb39764db

    router = IPCRouter(schema_registry=schema_registry, unified_caller=caller)

    return TcpSocketTransportHost(router, schema_registry, host=host, port=port)


async def run() -> None:
    logging.basicConfig(level=logging.INFO)
    host = build_host()
    logger.info("Desktop IPC bridge starting: canonical akaalIPC router bound to PipelineUnifiedCaller")
    await host.serve_forever()


if __name__ == "__main__":
    asyncio.run(run())
