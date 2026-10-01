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

from akaalIPC.application.router import IPCRouter
from akaalIPC.protocol.schemas import SchemaRegistry, register_core_pipeline_schemas
from akaalIPC.transport.tcp_socket_host import DEFAULT_HOST, DEFAULT_PORT, TcpSocketTransportHost
from akaalPipeline.application.unified_caller import PipelineUnifiedCaller

logger = logging.getLogger(__name__)

# akaalPipeline's repositories (akaalPipeline/state/repositories.py) self-initialize their
# own schema via `CREATE TABLE IF NOT EXISTS` on first connection -- no separate migration
# runner exists or is needed. No production db_path existed anywhere in the repo before this
# bridge (repo-wide search found `PipelineUnifiedCaller(db_path=...)` only in test fixtures,
# using pytest tmp paths). This is the first real production persistence location for the
# EXISTING canonical akaalPipeline repositories -- not a new authority, not a Monitoring-only
# store, and not test/debug infrastructure (contrast: the unreferenced repo-root test_debug.db).
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
    caller = PipelineUnifiedCaller(db_path=resolved_db_path)

    router = IPCRouter(schema_registry=schema_registry, unified_caller=caller)

    return TcpSocketTransportHost(router, schema_registry, host=host, port=port)


async def run() -> None:
    logging.basicConfig(level=logging.INFO)
    host = build_host()
    logger.info("Desktop IPC bridge starting: canonical akaalIPC router bound to PipelineUnifiedCaller")
    await host.serve_forever()


if __name__ == "__main__":
    asyncio.run(run())
