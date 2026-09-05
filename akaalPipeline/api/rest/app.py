"""
akaalPipeline.api.rest.app
=============================
FastAPI Enterprise REST surface for AKAAL Platform (/api/v1/...).
Strict architectural boundaries:
- Thin public adapter: every route constructs a canonical CommandEnvelope/QueryEnvelope
  and delegates exclusively to PipelineUnifiedCaller.
- Stable versioned public schemas (Pydantic v1 models) distinct from internal dataclasses.
- Strict bounded pagination and SQL-pushed filtering (status, mode) before pagination.
- 1MB request body ceiling middleware and content-type validation.
- Idempotency key and correlation ID propagation.
- Optimistic concurrency support (expected_revision).
- Anti-enumeration equivalence and secret-safe error handling.
"""

from __future__ import annotations

import json
import uuid
from typing import Any, Optional

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request, Response, status
from fastapi.openapi.utils import get_openapi

from akaalIPC.protocol.envelopes import CommandEnvelope, QueryEnvelope
from akaalIPC.protocol.errors import IPCError
from akaalIPC.protocol.schemas import RequestKind
from akaalIPC.security.context import ActorContext, CorrelationContext
from akaalIPC.transport.ports import CallerResultStatus
from akaalPipeline.api.rest.errors import error_body, http_status_for
from akaalPipeline.api.rest.schemas import (
    CancelMigrationRequestV1,
    CreateMigrationRequestV1,
    MigrationListResponseV1,
    MigrationResponseV1,
    OperationResponseV1,
)
from akaalPipeline.api.rest.security import build_actor_context
from akaalPipeline.application.unified_caller import PipelineUnifiedCaller

MAX_PAGE_SIZE = 100
DEFAULT_PAGE_SIZE = 25
MAX_BODY_SIZE_BYTES = 1024 * 1024  # 1 MB ceiling
SUPPORTED_QUERY_PARAMS = frozenset({"limit", "offset", "status", "mode"})


def _correlation(x_correlation_id: Optional[str]) -> CorrelationContext:
    req_id = f"req-{uuid.uuid4().hex}"
    return CorrelationContext(request_id=req_id, correlation_id=x_correlation_id or req_id)


def _raise_for_error(error: IPCError) -> None:
    raise HTTPException(status_code=http_status_for(error), detail=error_body(error))


def create_app(caller: PipelineUnifiedCaller) -> FastAPI:
    """
    Builds the REST app bound to one PipelineUnifiedCaller instance.
    All orchestration, authorization, and data access are delegated to the canonical caller.
    """
    app = FastAPI(
        title="AKAAL Enterprise REST Platform",
        version="1.0.0",
        docs_url="/docs",
        openapi_url="/openapi.json",
    )

    # 1. Request body ceiling & correlation propagation middleware
    @app.middleware("http")
    async def _body_limit_and_correlation_middleware(request: Request, call_next):
        content_length = request.headers.get("content-length")
        if content_length:
            try:
                if int(content_length) > MAX_BODY_SIZE_BYTES:
                    return Response(
                        content=json.dumps({"error": "Request body exceeds 1MB limit."}),
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        media_type="application/json",
                    )
            except ValueError:
                pass

        # Validate content-type on mutating requests with body
        if request.method in ("POST", "PUT", "PATCH") and content_length and int(content_length) > 0:
            ct = request.headers.get("content-type", "")
            if not ct.startswith("application/json"):
                return Response(
                    content=json.dumps({"error": f"Unsupported Media Type '{ct}'. Expected 'application/json'."}),
                    status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                    media_type="application/json",
                )

        response: Response = await call_next(request)
        cid = request.headers.get("X-Correlation-Id")
        if cid:
            response.headers["X-Correlation-Id"] = cid
        return response

    # 2. Canonical Migration Routes
    @app.post(
        "/api/v1/migrations",
        status_code=status.HTTP_201_CREATED,
        response_model=MigrationResponseV1,
        operation_id="createMigrationV1",
    )
    def create_migration(
        body: CreateMigrationRequestV1,
        actor: ActorContext = Depends(build_actor_context),
        x_correlation_id: Optional[str] = Header(default=None, alias="X-Correlation-Id"),
        idempotency_key: Optional[str] = Header(default=None, alias="Idempotency-Key"),
    ):
        req_id = f"req-{uuid.uuid4().hex}"
        payload = {
            "name": body.name,
            "mode": body.mode,
            "configuration": body.configuration or {},
        }
        envelope = CommandEnvelope(
            request_id=req_id,
            protocol_version="1.0",
            schema_version="1.0",
            request_type="migration.create",
            kind=RequestKind.COMMAND,
            actor=actor,
            correlation=_correlation(x_correlation_id),
            payload=payload,
            command_id=req_id,
            idempotency_key=idempotency_key,
        )
        result = caller.handle_command(envelope)
        if result.status == CallerResultStatus.ERROR:
            _raise_for_error(result.error)
        return result.result

    @app.get(
        "/api/v1/migrations/{migration_id}",
        response_model=MigrationResponseV1,
        operation_id="getMigrationV1",
    )
    def get_migration(
        migration_id: str,
        actor: ActorContext = Depends(build_actor_context),
        x_correlation_id: Optional[str] = Header(default=None, alias="X-Correlation-Id"),
    ):
        envelope = QueryEnvelope(
            request_id=f"req-{uuid.uuid4().hex}",
            protocol_version="1.0",
            schema_version="1.0",
            request_type="migration.get",
            kind=RequestKind.QUERY,
            actor=actor,
            correlation=_correlation(x_correlation_id),
            payload={"migration_id": migration_id},
        )
        result = caller.handle_query(envelope)
        if result.status == CallerResultStatus.ERROR:
            _raise_for_error(result.error)
        return result.result

    @app.get(
        "/api/v1/migrations",
        response_model=MigrationListResponseV1,
        operation_id="listMigrationsV1",
    )
    def list_migrations(
        request: Request,
        limit: int = Query(default=DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
        offset: int = Query(default=0, ge=0),
        status_filter: Optional[str] = Query(default=None, alias="status"),
        mode_filter: Optional[str] = Query(default=None, alias="mode"),
        actor: ActorContext = Depends(build_actor_context),
        x_correlation_id: Optional[str] = Header(default=None, alias="X-Correlation-Id"),
    ):
        # Strict filter allowlisting: reject unsupported query parameters with 400
        for param in request.query_params.keys():
            if param not in SUPPORTED_QUERY_PARAMS:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Unsupported query filter parameter '{param}'. Supported filters are: status, mode.",
                )

        envelope = QueryEnvelope(
            request_id=f"req-{uuid.uuid4().hex}",
            protocol_version="1.0",
            schema_version="1.0",
            request_type="migration.list",
            kind=RequestKind.QUERY,
            actor=actor,
            correlation=_correlation(x_correlation_id),
            payload={
                "limit": limit,
                "offset": offset,
                "status": status_filter,
                "mode": mode_filter,
            },
        )
        result = caller.handle_query(envelope)
        if result.status == CallerResultStatus.ERROR:
            _raise_for_error(result.error)
        return result.result

    @app.post(
        "/api/v1/migrations/{migration_id}/cancel",
        status_code=status.HTTP_202_ACCEPTED,
        operation_id="cancelMigrationV1",
    )
    def cancel_migration(
        migration_id: str,
        body: Optional[CancelMigrationRequestV1] = None,
        actor: ActorContext = Depends(build_actor_context),
        x_correlation_id: Optional[str] = Header(default=None, alias="X-Correlation-Id"),
        idempotency_key: Optional[str] = Header(default=None, alias="Idempotency-Key"),
    ):
        req_id = f"req-{uuid.uuid4().hex}"
        payload: dict[str, Any] = {"migration_id": migration_id}
        if body and body.expected_revision is not None:
            payload["expected_revision"] = body.expected_revision

        envelope = CommandEnvelope(
            request_id=req_id,
            protocol_version="1.0",
            schema_version="1.0",
            request_type="migration.cancel",
            kind=RequestKind.COMMAND,
            actor=actor,
            correlation=_correlation(x_correlation_id),
            payload=payload,
            command_id=req_id,
            idempotency_key=idempotency_key,
        )
        result = caller.handle_command(envelope)
        if result.status == CallerResultStatus.ERROR:
            _raise_for_error(result.error)
        return result.result

    @app.get(
        "/api/v1/operations/{operation_id}",
        response_model=OperationResponseV1,
        operation_id="getOperationV1",
    )
    def get_operation(
        operation_id: str,
        actor: ActorContext = Depends(build_actor_context),
        x_correlation_id: Optional[str] = Header(default=None, alias="X-Correlation-Id"),
    ):
        envelope = QueryEnvelope(
            request_id=f"req-{uuid.uuid4().hex}",
            protocol_version="1.0",
            schema_version="1.0",
            request_type="operation.get",
            kind=RequestKind.QUERY,
            actor=actor,
            correlation=_correlation(x_correlation_id),
            payload={"operation_id": operation_id},
        )
        result = caller.handle_query(envelope)
        if result.status == CallerResultStatus.ERROR:
            _raise_for_error(result.error)
        return result.result

    return app
