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
    -> EngineGateway (bound via bind_gateway=True)
    -> CentralAuthorizationEngine (bound via central_authz)
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
import sqlite3

from akaalIPC.application.router import IPCRouter
from akaalIPC.protocol.schemas import SchemaRegistry, register_core_pipeline_schemas
from akaalIPC.transport.tcp_socket_host import DEFAULT_HOST, DEFAULT_PORT, TcpSocketTransportHost
from akaalPipeline.application.unified_caller import PipelineUnifiedCaller
from akaalPipeline.identity.groups import GroupAuthority
from akaalPipeline.security.abac import ABACAuthority
from akaalPipeline.security.central_authorization import CentralAuthorizationEngine
from akaalPipeline.security.rbac import RBACAuthority
from akaalPipeline.state.repositories import (
    SQLiteABACPolicyRepository,
    SQLiteGroupRepository,
    SQLitePrincipalRepository,
    SQLiteRoleGrantRepository,
    SQLiteRolePermissionRepository,
    SQLiteRoleRepository,
    SQLiteTenantRepository,
)

logger = logging.getLogger(__name__)

DEFAULT_DB_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "akaalPipeline", "data", "akaal-pipeline.db")


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

    conn = sqlite3.connect(resolved_db_path)
    conn.row_factory = sqlite3.Row
    tenant_repo = SQLiteTenantRepository(conn)
    principal_repo = SQLitePrincipalRepository(conn)
    group_repo = SQLiteGroupRepository(conn)
    role_repo = SQLiteRoleRepository(conn)
    perm_repo = SQLiteRolePermissionRepository(conn)
    grant_repo = SQLiteRoleGrantRepository(conn)
    abac_repo = SQLiteABACPolicyRepository(conn)

    group_auth = GroupAuthority(group_repo, principal_repo)
    rbac_auth = RBACAuthority(role_repo=role_repo, role_perm_repo=perm_repo, role_grant_repo=grant_repo)
    abac_auth = ABACAuthority(policy_repo=abac_repo)

    central_authz = CentralAuthorizationEngine(
        tenant_repo=tenant_repo,
        principal_repo=principal_repo,
        group_authority=group_auth,
        rbac_authority=rbac_auth,
        abac_authority=abac_auth,
    )

    caller = PipelineUnifiedCaller(
        db_path=resolved_db_path,
        bind_gateway=True,
        central_authz=central_authz,
    )

    router = IPCRouter(schema_registry=schema_registry, unified_caller=caller)

    return TcpSocketTransportHost(router, schema_registry, host=host, port=port)


async def run() -> None:
    logging.basicConfig(level=logging.INFO)
    host = build_host()
    logger.info("Desktop IPC bridge starting: canonical akaalIPC router bound to PipelineUnifiedCaller")
    await host.serve_forever()


if __name__ == "__main__":
    asyncio.run(run())
