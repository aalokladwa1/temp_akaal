"""
akaalIPC.transport.tcp_socket_host
=====================================
Generic TCP transport host binding a running ``IPCRouter`` to a real
listening socket, so a desktop (Wails) client's ``App.InvokeIPC`` can
reach akaalIPC instead of dialing a socket nothing listens on.

This is the "production dependency binding" `akaalIPC.transport.ports`
deliberately leaves unimplemented (see that module's docstring) -- it is
transport plumbing, not a business authority. It knows nothing about
Monitoring, Migration, Dashboard, Reports, Administration, or Settings as
domains; it only translates the generic wire shape
``akaalSoftware/app.go``'s ``InvokeIPC`` already speaks --
``{endpoint, action, payload}`` newline-delimited JSON in,
``{status, data, error}`` newline-delimited JSON out, one request per
connection -- into ``IPCRouter.handle_request``'s ``CommandEnvelope`` /
``QueryEnvelope`` shape, and back.

Identity note: every request synthesizes a local, unauthenticated desktop
actor (see ``_build_local_desktop_actor``). ``akaalSoftware/app.go``'s
``IPCRequest`` struct carries no session_id/session_token, so
``PipelineUnifiedCaller._resolve_trusted_actor`` (which always downgrades
wire-asserted claims via ``trusted_boundary=False``) cannot re-derive real
roles/scopes for it. Queries proceed under default-tenant scope. Commands
that require an RBAC permission correctly fail closed
(``PERMISSION_DENIED``) until a real desktop session/login mechanism is
wired into ``IPCRequest`` -- that is a separate, larger identity gap this
host does not attempt to solve, and it must never be papered over by
fabricating trust here.
"""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from typing import Optional

from akaalIPC.application.router import IPCRouter
from akaalIPC.protocol.envelopes import CommandEnvelope, QueryEnvelope, ResponseStatus
from akaalIPC.protocol.schemas import RequestKind, SchemaRegistry
from akaalIPC.security.context import ActorContext, ActorReference, CorrelationContext

logger = logging.getLogger(__name__)

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 52199
SCHEMA_VERSION = "1.0"
PROTOCOL_VERSION = "1.0.0"

# See module docstring "Identity note" above -- this is a provenance label,
# not a trust grant.
DESKTOP_BRIDGE_PROVENANCE = "wails-desktop-local"


def _build_local_desktop_actor() -> ActorContext:
    return ActorContext(
        actor=ActorReference(actor_id="desktop-local-user", actor_type="HUMAN"),
        organization_id="default",
        provenance=DESKTOP_BRIDGE_PROVENANCE,
    )


class TcpSocketTransportHost:
    """Binds an ``IPCRouter`` to a plain TCP socket, one request per
    connection, using the exact framing ``akaalSoftware/app.go``'s
    ``InvokeIPC`` client already dials against.
    """

    def __init__(
        self,
        router: IPCRouter,
        schema_registry: SchemaRegistry,
        *,
        host: str = DEFAULT_HOST,
        port: int = DEFAULT_PORT,
    ) -> None:
        self._router = router
        self._schema_registry = schema_registry
        self._host = host
        self._port = port
        self._server: Optional[asyncio.base_events.Server] = None

    async def start(self) -> None:
        self._server = await asyncio.start_server(self._handle_connection, self._host, self._port)
        logger.info("TcpSocketTransportHost listening on %s:%s", self._host, self._port)

    async def serve_forever(self) -> None:
        if self._server is None:
            await self.start()
        assert self._server is not None
        async with self._server:
            await self._server.serve_forever()

    async def stop(self) -> None:
        if self._server is not None:
            self._server.close()
            await self._server.wait_closed()
            self._server = None

    async def _handle_connection(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        try:
            line = await reader.readline()
            if not line:
                return
            response_payload = self._dispatch(line)
            writer.write((json.dumps(response_payload) + "\n").encode("utf-8"))
            await writer.drain()
        except Exception:  # noqa: BLE001 - boundary sanitization, never crash the listener
            logger.exception("TcpSocketTransportHost: unhandled connection error")
            try:
                writer.write((json.dumps({"status": "ERROR", "error": "INTERNAL_TRANSPORT_ERROR"}) + "\n").encode("utf-8"))
                await writer.drain()
            except Exception:  # noqa: BLE001
                pass
        finally:
            writer.close()

    def _dispatch(self, raw_line: bytes) -> dict:
        try:
            wire_request = json.loads(raw_line.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return {"status": "ERROR", "error": "MALFORMED_JSON_REQUEST"}

        if not isinstance(wire_request, dict):
            return {"status": "ERROR", "error": "REQUEST_MUST_BE_JSON_OBJECT"}

        endpoint = wire_request.get("endpoint")
        action = wire_request.get("action")
        payload = wire_request.get("payload")
        if payload is None:
            payload = {}

        if not isinstance(endpoint, str) or not endpoint or not isinstance(action, str) or not action:
            return {"status": "ERROR", "error": "MISSING_ENDPOINT_OR_ACTION"}
        if not isinstance(payload, dict):
            return {"status": "ERROR", "error": "PAYLOAD_MUST_BE_OBJECT"}

        # Generic, mechanical join -- this host has no per-domain knowledge
        # of what "endpoint"/"action" mean; it only mirrors the request_type
        # naming convention akaalIPC's own SchemaRegistry already uses
        # (see akaalIPC/protocol/schemas.py: "incident.list", "fleet.status", ...).
        request_type = f"{endpoint}.{action}"

        descriptor = self._schema_registry.get(request_type, SCHEMA_VERSION)
        if descriptor is None:
            return {"status": "ERROR", "error": f"UNKNOWN_REQUEST_TYPE:{request_type}"}

        request_id = str(uuid.uuid4())
        correlation = CorrelationContext(request_id=request_id, correlation_id=request_id)
        actor = _build_local_desktop_actor()

        if descriptor.kind == RequestKind.COMMAND:
            envelope = CommandEnvelope(
                request_id=request_id,
                protocol_version=PROTOCOL_VERSION,
                schema_version=SCHEMA_VERSION,
                request_type=request_type,
                kind=RequestKind.COMMAND,
                actor=actor,
                correlation=correlation,
                payload=payload,
                command_id=request_id,
            )
        else:
            envelope = QueryEnvelope(
                request_id=request_id,
                protocol_version=PROTOCOL_VERSION,
                schema_version=SCHEMA_VERSION,
                request_type=request_type,
                kind=RequestKind.QUERY,
                actor=actor,
                correlation=correlation,
                payload=payload,
            )

        response = self._router.handle_request(envelope)

        if response.status == ResponseStatus.OK:
            return {"status": "SUCCESS", "data": dict(response.result or {})}
        if response.status == ResponseStatus.ACCEPTED:
            op = response.operation
            return {
                "status": "SUCCESS",
                "data": {
                    "operation_id": op.operation_id if op else None,
                    "accepted_at": op.accepted_at if op else None,
                    "query_request_type": op.query_request_type if op else None,
                },
            }
        error_dict = response.error.to_dict() if response.error else {"code": "UNKNOWN_ERROR"}
        return {"status": "ERROR", "error": json.dumps(error_dict)}
