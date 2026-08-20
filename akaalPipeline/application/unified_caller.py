"""akaalPipeline.application.unified_caller
=========================================
The pipeline-side Unified Caller satisfying frozen akaalIPC.transport.ports.UnifiedCallerPort.
"""

from __future__ import annotations

import uuid
from typing import Any, Mapping, Optional
from akaalIPC.protocol.envelopes import CommandEnvelope, OperationReference, QueryEnvelope
from akaalIPC.protocol.errors import IPCError, IPCErrorCategory, make_error, sanitize_unexpected_exception
from akaalIPC.transport.ports import CallerResult, CallerResultStatus, UnifiedCallerPort
from akaalPipeline.application.command_handlers import CommandHandlerRegistry
from akaalPipeline.application.query_service import PipelineQueryService
from akaalPipeline.capabilities.bindings import BindingRegistry
from akaalPipeline.capabilities.catalog import CapabilityCatalog
from akaalPipeline.capabilities.resolver import CapabilityResolver
from akaalPipeline.contracts.enums import MigrationMode, OperationStatus
from akaalPipeline.contracts.errors import PipelineError
from akaalPipeline.contracts.serialization import canonical_fingerprint
from akaalPipeline.execution.controller import PipelineExecutionController
from akaalPipeline.operations.idempotency import IdempotencyService
from akaalPipeline.operations.leases import LeaseManager
from akaalPipeline.operations.models import OperationRecord
from akaalPipeline.operations.service import OperationService
from akaalPipeline.security.context import PipelineActorContext
from akaalPipeline.state.repositories import SQLiteMigrationRepository
from akaalPipeline.state.unit_of_work import SQLiteUnitOfWork, UnitOfWorkPort


class PipelineUnifiedCaller(UnifiedCallerPort):
    def __init__(
        self,
        db_path: Optional[str] = None,
        shared_uow: Optional[SQLiteUnitOfWork] = None,
    ) -> None:
        if db_path is None and shared_uow is None:
            raise ValueError("PipelineUnifiedCaller requires an explicit db_path or shared_uow persistence dependency.")

        self.db_path = db_path or (shared_uow.db_path if shared_uow else "")
        self._shared_uow = shared_uow

        self.repository = SQLiteMigrationRepository(db_path=self.db_path)

        self.operation_service = OperationService()
        self.idempotency_service = IdempotencyService()
        self.catalog = CapabilityCatalog()
        self._init_catalog()
        self.binding_registry = BindingRegistry()

        self.capability_resolver = CapabilityResolver(self.catalog, self.binding_registry)
        self.lease_manager = LeaseManager()
        self.execution_controller = PipelineExecutionController(
            self.capability_resolver,
            self.binding_registry,
            self.lease_manager,
            self.operation_service,
        )
        self.command_handlers = CommandHandlerRegistry(
            self.repository,
            self.operation_service,
            self.idempotency_service,
            self.execution_controller,
        )
        self.query_service = PipelineQueryService(
            self.repository,
            self.operation_service,
        )

    def _init_catalog(self) -> None:
        from akaalPipeline.capabilities.catalog import CapabilityDescriptor
        from akaalPipeline.contracts.enums import MigrationMode, SideEffectClassification
        self.catalog.register(
            CapabilityDescriptor(
                capability_id="data_transport",
                name="Data Transport",
                supported_modes={
                    MigrationMode.M1_BULK,
                    MigrationMode.M2_BULK_CDC,
                    MigrationMode.M4_INCREMENTAL,
                    MigrationMode.M5_STATE_SYNC,
                    MigrationMode.M7_DATA_ONLY,
                },
                side_effect=SideEffectClassification.REVERSIBLE,
            )
        )

    def _create_uow(self) -> SQLiteUnitOfWork:

        if self._shared_uow:
            return self._shared_uow
        return SQLiteUnitOfWork(db_path=self.db_path)

    def handle_command(self, envelope: CommandEnvelope) -> CallerResult:
        correlation_id = envelope.correlation.correlation_id
        request_id = envelope.request_id

        # Convert IPC ActorContext to PipelineActorContext
        if envelope.actor is None or envelope.actor.actor is None:
            return CallerResult(
                status=CallerResultStatus.ERROR,
                error=make_error(
                    IPCErrorCategory.UNAUTHORIZED,
                    code="MISSING_ACTOR_CONTEXT",
                    message="Command envelope has no actor context.",
                    correlation_id=correlation_id,
                    request_id=request_id,
                ),
            )
        pipeline_actor = PipelineActorContext.from_ipc(envelope.actor)

        payload_fp = canonical_fingerprint(envelope.payload)
        uow = self._create_uow()

        try:
            with uow:
                # Idempotency Check
                if envelope.idempotency_key:
                    cached_result = self.idempotency_service.check_and_store(
                        idempotency_key=envelope.idempotency_key,
                        command_id=envelope.command_id,
                        payload_fingerprint=payload_fp,
                        result_payload={},  # pre-check

                        conn=uow.connection,
                    )
                    if cached_result is not None:
                        return CallerResult(status=CallerResultStatus.OK, result=cached_result)

                # Dispatch Command
                request_type = envelope.request_type
                if request_type in ("migration.create", "create_migration"):
                    res = self.command_handlers.handle_create_migration(envelope.payload, pipeline_actor, uow)
                elif request_type in ("migration.configure", "configure_migration"):
                    res = self.command_handlers.handle_configure_migration(envelope.payload, pipeline_actor, uow)
                elif request_type in ("migration.start", "start_migration"):
                    # Asynchronous execution command -> create operation journal record
                    op_id = f"op-{uuid.uuid4().hex}"
                    op_rec = OperationRecord(
                        operation_id=op_id,
                        command_id=envelope.command_id,
                        idempotency_key=envelope.idempotency_key,
                        status=OperationStatus.ACCEPTED,
                        actor=pipeline_actor,
                        payload_fingerprint=payload_fp,
                    )
                    self.operation_service.create_operation(op_rec, uow.connection)

                    # Trigger execution controller attempt
                    att_id = f"att-{uuid.uuid4().hex}"

                    mig_id = envelope.payload.get("migration_id", "mig-1")
                    mode_val = MigrationMode(envelope.payload.get("mode", "M1"))

                    exec_res = self.execution_controller.start_attempt(
                        attempt_id=att_id,
                        operation_id=op_id,
                        migration_id=mig_id,
                        mode=mode_val,
                        initialization_fingerprint=payload_fp,
                        graph_node_id="node-1",
                        conn=uow.connection,
                    )

                    from datetime import datetime, timezone
                    op_ref = OperationReference(
                        operation_id=op_id,
                        accepted_at=datetime.now(timezone.utc).isoformat(),
                        query_request_type="operation.get",
                        correlation_id=correlation_id,
                    )


                    if not exec_res.is_success:
                        # Truthful fail closed response when unbound
                        err = make_error(
                            IPCErrorCategory.UNBOUND if exec_res.error_code == "UNBOUND" else IPCErrorCategory.INTERNAL_ERROR,
                            code=exec_res.error_code or "UNBOUND",
                            message=exec_res.error_message or "Execution failed closed (UNBOUND)",
                            correlation_id=correlation_id,
                            request_id=request_id,
                        )
                        return CallerResult(status=CallerResultStatus.ERROR, error=err)

                    return CallerResult(status=CallerResultStatus.ACCEPTED, operation=op_ref)
                else:
                    raise PipelineError(
                        PipelineErrorCode.INVALID_REQUEST,
                        f"Unsupported command request_type {request_type!r}",
                        correlation_id=correlation_id,
                    )

                # Store idempotency result if key was provided
                if envelope.idempotency_key:
                    import json
                    uow.connection.execute(
                        "UPDATE idempotency_records SET result_payload = ? WHERE idempotency_key = ?",
                        (json.dumps(res), envelope.idempotency_key),
                    )


                return CallerResult(status=CallerResultStatus.OK, result=dict(res))

        except PipelineError as pe:
            return CallerResult(status=CallerResultStatus.ERROR, error=pe.to_ipc_error())
        except Exception as unexpected:  # noqa: BLE001
            sanitized = sanitize_unexpected_exception(unexpected, correlation_id=correlation_id, request_id=request_id)


            return CallerResult(status=CallerResultStatus.ERROR, error=sanitized)

    def handle_query(self, envelope: QueryEnvelope) -> CallerResult:
        correlation_id = envelope.correlation.correlation_id
        request_id = envelope.request_id

        uow = self._create_uow()
        try:
            request_type = envelope.request_type
            if request_type in ("migration.get", "get_migration"):
                mig_id = envelope.payload.get("migration_id")
                agg = self.query_service.get_migration(mig_id, conn=uow.connection)
                return CallerResult(status=CallerResultStatus.OK, result=agg.to_dict())
            elif request_type in ("migration.list", "list_migrations"):
                tenant_id = envelope.payload.get("tenant_id")
                aggs = self.query_service.list_migrations(tenant_id=tenant_id, conn=uow.connection)
                return CallerResult(status=CallerResultStatus.OK, result={"migrations": [a.to_dict() for a in aggs]})
            elif request_type in ("operation.get", "get_operation"):
                op_id = envelope.payload.get("operation_id")
                op = self.query_service.get_operation(op_id, conn=uow.connection)
                return CallerResult(status=CallerResultStatus.OK, result=op.to_dict())
            else:
                raise PipelineError(
                    PipelineErrorCode.INVALID_REQUEST,
                    f"Unsupported query request_type {request_type!r}",
                    correlation_id=correlation_id,
                )
        except PipelineError as pe:
            return CallerResult(status=CallerResultStatus.ERROR, error=pe.to_ipc_error())
        except Exception as unexpected:  # noqa: BLE001
            sanitized = sanitize_unexpected_exception(unexpected, correlation_id=correlation_id, request_id=request_id)
            return CallerResult(status=CallerResultStatus.ERROR, error=sanitized)
