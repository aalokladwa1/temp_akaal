"""
akaalEngine.gateway.routing.dispatcher
=======================================
Canonical Gateway semantic request dispatcher.
Enforces explicit, typed routing by SemanticOperation enum to GatewayCoordinator or canonical authorities.
Rejects arbitrary method dispatch, dynamic string invocation, and malformed requests fail-closed.
"""

import logging
from typing import Any, Dict, Optional

from akaalEngine.gateway.failure.translator import FailureTranslator
from akaalEngine.gateway.models.context import GatewayRequestContext
from akaalEngine.gateway.models.enums import GatewayFailureCategory, SemanticOperation
from akaalEngine.gateway.models.requests import GatewayRequest
from akaalEngine.gateway.models.responses import GatewayResponse
from akaalEngine.gateway.orchestration.coordinator import GatewayCoordinator

logger = logging.getLogger("akaalEngine.gateway.routing")


class GatewayDispatcher:
    """Explicit semantic request router for EngineGateway."""

    def __init__(self, coordinator: Optional[GatewayCoordinator] = None) -> None:
        self.coordinator = coordinator or GatewayCoordinator()

    def dispatch(self, request: Any) -> GatewayResponse[Any]:
        """Routes a GatewayRequest or typed request DTO to its designated semantic handler, catching and translating all exceptions."""
        if not hasattr(request, "context"):
            return GatewayResponse.create_failure(
                operation_id="op-invalid",
                operation_type="UNKNOWN",
                migration_id="unknown",
                run_id="unknown",
                failure_category=GatewayFailureCategory.INVALID_REQUEST.value,
                error_message="Request must be a valid request instance with a context attribute.",
            )

        context: GatewayRequestContext = request.context
        operation = getattr(request, "operation", None)

        if operation is None:
            cls_name = request.__class__.__name__.upper()
            if "TESTCONNECTION" in cls_name:
                operation = SemanticOperation.TEST_CONNECTION
            elif "RESOLVECAPABILITIES" in cls_name:
                operation = SemanticOperation.RESOLVE_CAPABILITIES
            elif "DISCOVERCATALOG" in cls_name:
                operation = SemanticOperation.DISCOVER_CATALOG
            elif "COMPILESCHEMA" in cls_name:
                operation = SemanticOperation.COMPILE_SCHEMA_MAPPING
            elif "VALIDATESCHEMA" in cls_name:
                operation = SemanticOperation.VALIDATE_SCHEMA_COMPATIBILITY
            elif "PREPAREMIGRATION" in cls_name:
                operation = SemanticOperation.PREPARE_MIGRATION_EXECUTION
            elif "EXECUTEBULKMIGRATION" in cls_name:
                operation = SemanticOperation.EXECUTE_BULK_MIGRATION
            elif "INITIALIZECDC" in cls_name:
                operation = SemanticOperation.INITIALIZE_CDC_STREAM
            elif "EXECUTECDCSYNC" in cls_name:
                operation = SemanticOperation.EXECUTE_CDC_SYNC
            elif "EVALUATECUTOVER" in cls_name:
                operation = SemanticOperation.EVALUATE_CUTOVER_READINESS
            elif "RUNVALIDATION" in cls_name:
                operation = SemanticOperation.RUN_FINAL_VALIDATION
            elif "PACKAGEEVIDENCE" in cls_name:
                operation = SemanticOperation.PACKAGE_MACHINE_EVIDENCE
            elif "VERIFYEVIDENCE" in cls_name:
                operation = SemanticOperation.VERIFY_EVIDENCE_INTEGRITY
            elif "EXECUTEATOMICCUTOVER" in cls_name:
                operation = SemanticOperation.EXECUTE_ATOMIC_CUTOVER
            elif "TRIGGERCHECKPOINT" in cls_name:
                operation = SemanticOperation.TRIGGER_CHECKPOINT
            elif "RECOVERFROMCHECKPOINT" in cls_name:
                operation = SemanticOperation.RECOVER_FROM_CHECKPOINT
            elif "PAUSEEXECUTION" in cls_name:
                operation = SemanticOperation.PAUSE_EXECUTION
            elif "RESUMEEXECUTION" in cls_name:
                operation = SemanticOperation.RESUME_EXECUTION
            elif "CANCELEXECUTION" in cls_name:
                operation = SemanticOperation.CANCEL_EXECUTION
            elif "GETPROGRESS" in cls_name:
                operation = SemanticOperation.GET_MIGRATION_PROGRESS
            elif "GETHEALTH" in cls_name:
                operation = SemanticOperation.GET_HEALTH_DIAGNOSTICS
            elif "EXECUTEDATACLEANSING" in cls_name:
                operation = SemanticOperation.EXECUTE_DATA_CLEANSING
            elif "APPLYPRIVACYMASKING" in cls_name:
                operation = SemanticOperation.APPLY_PRIVACY_MASKING
            elif "RECONCILEDISPUTED" in cls_name:
                operation = SemanticOperation.RECONCILE_DISPUTED_RECORDS
            elif "ROLLBACKTRANSACTION" in cls_name:
                operation = SemanticOperation.ROLLBACK_TRANSACTION_BATCH
            elif "FINALIZEMIGRATION" in cls_name:
                operation = SemanticOperation.FINALIZE_MIGRATION_RUN

        if not isinstance(operation, SemanticOperation):
            try:
                operation = SemanticOperation(str(operation))
            except ValueError:
                return GatewayResponse.create_failure(
                    operation_id=context.operation_id,
                    operation_type=str(operation),
                    migration_id=context.migration_id,
                    run_id=context.run_id,
                    failure_category=GatewayFailureCategory.UNSUPPORTED_OPERATION.value,
                    error_message=f"Unsupported semantic operation: '{operation}'",
                )

        payload = getattr(request, "payload", None)
        if payload is None:
            payload = {
                k: v for k, v in getattr(request, "__dict__", {}).items()
                if k not in ("context", "operation")
            }

        op_name = operation.value

        # Zero-Trust Execution Authorization Verification
        if getattr(context, "execution_authorization_artifact", None) is not None:
            from akaalPipeline.security.execution_authorization import verify_execution_authorization
            authz = context.execution_authorization_artifact
            pub_key_pem = payload.get("execution_signing_public_key_pem") or authz.get("public_key_pem")
            if pub_key_pem:
                try:
                    verify_execution_authorization(
                        artifact=authz,
                        public_key_pem=pub_key_pem,
                        expected_tenant_id=context.tenant_id,
                        expected_migration_id=context.migration_id,
                    )
                except Exception as exc:
                    return GatewayResponse.create_failure(
                        operation_id=context.operation_id,
                        operation_type=op_name,
                        migration_id=context.migration_id,
                        run_id=context.run_id,
                        failure_category=GatewayFailureCategory.INVALID_REQUEST.value,
                        error_message=f"Execution authorization verification failed: {exc}",
                        fencing_epoch=context.fencing_epoch,
                    )

        try:
            # Explicit, auditable enum dispatch table (No getattr or eval)
            if operation == SemanticOperation.ACQUIRE_EXECUTION_FENCE:
                resp = self._handle_acquire_execution_fence(context, payload)
            elif operation == SemanticOperation.TEST_CONNECTION:
                resp = self.coordinator.orchestrate_test_connection(context, payload)
            elif operation == SemanticOperation.RESOLVE_CAPABILITIES:
                resp = self.coordinator.orchestrate_resolve_capabilities(context, payload)
            elif operation == SemanticOperation.DISCOVER_CATALOG:
                resp = self.coordinator.orchestrate_discover_catalog(context, payload)
            elif operation == SemanticOperation.COMPILE_SCHEMA_MAPPING:
                resp = self.coordinator.orchestrate_compile_schema(context, payload)
            elif operation == SemanticOperation.VALIDATE_SCHEMA_COMPATIBILITY:
                resp = self._handle_validate_schema_compatibility(context, payload)
            elif operation == SemanticOperation.APPLY_SCHEMA_CHANGES:
                resp = self._handle_apply_schema(context, payload)
            elif operation == SemanticOperation.PREPARE_MIGRATION_EXECUTION:
                resp = self._handle_prepare_migration(context, payload)
            elif operation == SemanticOperation.EXECUTE_BULK_MIGRATION:
                resp = self.coordinator.orchestrate_bulk_migration(context, payload)
            elif operation == SemanticOperation.EXECUTE_INCREMENTAL_EXTRACT:
                resp = self._handle_incremental_extract(context, payload)
            elif operation == SemanticOperation.EXECUTE_INCREMENTAL_APPLY:
                resp = self._handle_incremental_apply(context, payload)
            elif operation == SemanticOperation.INITIALIZE_CDC_STREAM:
                resp = self._handle_initialize_cdc(context, payload)
            elif operation == SemanticOperation.EXECUTE_CDC_SYNC:
                resp = self.coordinator.orchestrate_cdc_sync(context, payload)
            elif operation == SemanticOperation.EVALUATE_CUTOVER_READINESS:
                resp = self.coordinator.orchestrate_cutover_readiness(context, payload)
            elif operation == SemanticOperation.RUN_FINAL_VALIDATION:
                resp = self.coordinator.orchestrate_final_validation(context, payload)
            elif operation == SemanticOperation.PACKAGE_MACHINE_EVIDENCE:
                resp = self.coordinator.orchestrate_package_evidence(context, payload)
            elif operation == SemanticOperation.VERIFY_EVIDENCE_INTEGRITY:
                resp = self.coordinator.orchestrate_verify_evidence(context, payload)
            elif operation == SemanticOperation.EXECUTE_ATOMIC_CUTOVER:
                resp = self._handle_execute_atomic_cutover(context, payload)
            elif operation == SemanticOperation.TRIGGER_CHECKPOINT:
                resp = self._handle_trigger_checkpoint(context, payload)
            elif operation == SemanticOperation.VERIFY_CHECKPOINT:
                resp = self._handle_verify_checkpoint(context, payload)
            elif operation == SemanticOperation.RECOVER_FROM_CHECKPOINT:
                resp = self._handle_recover_checkpoint(context, payload)
            elif operation == SemanticOperation.PAUSE_EXECUTION:
                resp = self._handle_pause_execution(context, payload)
            elif operation == SemanticOperation.RESUME_EXECUTION:
                resp = self._handle_resume_execution(context, payload)
            elif operation == SemanticOperation.CANCEL_EXECUTION:
                resp = self._handle_cancel_execution(context, payload)
            elif operation == SemanticOperation.GET_MIGRATION_PROGRESS:
                resp = self._handle_get_progress(context, payload)
            elif operation == SemanticOperation.GET_HEALTH_DIAGNOSTICS:
                resp = self._handle_get_health(context, payload)
            elif operation == SemanticOperation.EXECUTE_DATA_CLEANSING:
                resp = self._handle_data_cleansing(context, payload)
            elif operation == SemanticOperation.APPLY_PRIVACY_MASKING:
                resp = self._handle_privacy_masking(context, payload)
            elif operation == SemanticOperation.RECONCILE_DISPUTED_RECORDS:
                resp = self._handle_reconcile_disputed(context, payload)
            elif operation == SemanticOperation.ROLLBACK_TRANSACTION_BATCH:
                resp = self._handle_rollback_batch(context, payload)
            elif operation == SemanticOperation.FINALIZE_MIGRATION_RUN:
                resp = self._handle_finalize_run(context, payload)
            else:
                resp = GatewayResponse.create_failure(
                    operation_id=context.operation_id,
                    operation_type=op_name,
                    migration_id=context.migration_id,
                    run_id=context.run_id,
                    failure_category=GatewayFailureCategory.UNSUPPORTED_OPERATION.value,
                    error_message=f"Semantic operation '{op_name}' has no registered handler.",
                )
        except Exception as exc:
            resp = FailureTranslator.translate_exception(exc, context, op_name)

        if resp.execution_receipt and context:
            rcpt = dict(resp.execution_receipt)
            if context.job_id:
                rcpt["gateway_job_id"] = context.job_id
            if getattr(context, "initialization_fingerprint", None):
                rcpt["initialization_fingerprint"] = context.initialization_fingerprint
            from akaalEngine.gateway.models.responses import sign_receipt
            try:
                rcpt["receipt_signature"] = sign_receipt(
                    migration_id=rcpt.get("gateway_migration_id", ""),
                    run_id=rcpt.get("gateway_run_id", ""),
                    operation_id=rcpt.get("gateway_operation_id", ""),
                    fencing_epoch=rcpt.get("gateway_fencing_epoch"),
                    status_code=rcpt.get("gateway_status_code", ""),
                    initialization_fingerprint=rcpt.get("initialization_fingerprint", ""),
                    job_id=rcpt.get("gateway_job_id", ""),
                )
                object.__setattr__(resp, "execution_receipt", rcpt)
            except Exception:
                object.__setattr__(resp, "execution_receipt", None)

        return resp

    def _handle_acquire_execution_fence(self, ctx: GatewayRequestContext, payload: Dict[str, Any]) -> GatewayResponse[Dict[str, Any]]:
        self.coordinator.check_cancellation(ctx)
        resource_id = f"{ctx.migration_id}/{ctx.run_id}/{ctx.job_id}" if ctx.job_id else ctx.migration_id
        worker_id = payload.get("worker_id") or payload.get("owner_id", "gateway_worker")
        token = self.coordinator.durability_authority.issue_fencing_token(resource_id, worker_id)
        envelope = {
            "token_version": "1.0.0",
            "canonical_resource_id": resource_id,
            "resource_id": resource_id,
            "migration_id": ctx.migration_id,
            "run_id": ctx.run_id,
            "job_id": ctx.job_id,
            "worker_id": token.worker_id,
            "fencing_epoch": token.fencing_epoch,
            "epoch": token.fencing_epoch,
            "issued_at": token.issued_at,
            "timestamp": token.issued_at,
            "signature": token.signature,
            "engine_signature": token.signature,
        }
        return GatewayResponse.create_success(
            operation_id=ctx.operation_id, operation_type=SemanticOperation.ACQUIRE_EXECUTION_FENCE.value,
            migration_id=ctx.migration_id, run_id=ctx.run_id,
            payload={"fencing_token_envelope": envelope, "fencing_epoch": token.fencing_epoch, "resource_id": resource_id},
            fencing_epoch=token.fencing_epoch, proof_classification="UNIT_PROVEN"
        )

    def _handle_validate_schema_compatibility(self, ctx: GatewayRequestContext, payload: Dict[str, Any]) -> GatewayResponse[Dict[str, Any]]:
        self.coordinator.check_cancellation(ctx)
        self.coordinator.check_fencing(ctx)
        src = payload.get("source_schema_model", {})
        tgt = payload.get("target_schema_model", {})
        if hasattr(self.coordinator.schema_authority, "assess_compatibility"):
            res = self.coordinator.schema_authority.assess_compatibility(src, tgt)
            is_compat = getattr(res, "is_compatible", getattr(res, "compatible", False))
        elif hasattr(self.coordinator.schema_authority, "compile"):
            from akaalEngine.schema.authority import SchemaCompilationRequest
            target_engine = payload.get("target_dialect") or tgt.get("dialect") or "POSTGRESQL"
            req = SchemaCompilationRequest(source_snapshot=src, target_engine=target_engine)
            res = self.coordinator.schema_authority.compile(req)
            if hasattr(res, "__await__"):
                import asyncio
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        res = asyncio.run_coroutine_threadsafe(res, loop).result()
                    else:
                        res = loop.run_until_complete(res)
                except Exception:
                    res = asyncio.run(res)
            report = getattr(res, "compatibility_report", None)
            is_compat = bool(report and getattr(report, "is_compatible", getattr(report, "compatible", False)))
        else:
            from akaalEngine.schema.models.errors import SchemaError
            raise SchemaError("SchemaAuthority does not support schema compatibility validation.")

        if not is_compat:
            from akaalEngine.gateway.models.enums import GatewayFailureCategory
            return GatewayResponse.create_failure(
                operation_id=ctx.operation_id,
                operation_type=SemanticOperation.VALIDATE_SCHEMA_COMPATIBILITY.value,
                failure_category=GatewayFailureCategory.SCHEMA_FAILURE,
                error_message=f"Schema compatibility validation failed: {res}",
                migration_id=ctx.migration_id, run_id=ctx.run_id, fencing_epoch=ctx.fencing_epoch
            )

        return GatewayResponse.create_success(
            operation_id=ctx.operation_id, operation_type=SemanticOperation.VALIDATE_SCHEMA_COMPATIBILITY.value,
            migration_id=ctx.migration_id, run_id=ctx.run_id,
            payload={"compatible": True, "details": str(res)},
            fencing_epoch=ctx.fencing_epoch, proof_classification="UNIT_PROVEN"
        )

    def _handle_apply_schema(self, ctx: GatewayRequestContext, payload: Dict[str, Any]) -> GatewayResponse[Dict[str, Any]]:
        self.coordinator.check_cancellation(ctx)
        self.coordinator.check_fencing(ctx)
        ddl_statements = payload.get("ddl_statements", payload.get("statements", []))
        tables = payload.get("selected_tables", payload.get("tables", []))
        writer = payload.get("target_writer") or payload.get("writer")

        applied_count = 0
        if writer:
            from akaalEngine.transport.drivers.base import TargetWriter
            if not isinstance(writer, TargetWriter):
                from akaalEngine.schema.models.errors import SchemaError
                raise SchemaError("TargetWriter must inherit from canonical TargetWriter base class.")
            if not ddl_statements:
                from akaalEngine.schema.models.errors import SchemaError
                raise SchemaError("Physical schema deployment requires non-empty DDL statements.")
            for ddl in ddl_statements:
                writer.execute_ddl(ddl)
                applied_count += 1
            if hasattr(writer, "commit"):
                c_res = writer.commit()
                if c_res is False:
                    from akaalEngine.schema.models.errors import SchemaError
                    raise SchemaError("TargetWriter physical schema commit failed.")
        elif hasattr(self.coordinator.schema_authority, "apply_schema"):
            res = self.coordinator.schema_authority.apply_schema(payload)
            if not isinstance(res, dict) or not res.get("applied") or "applied_count" not in res:
                from akaalEngine.schema.models.errors import SchemaError
                raise SchemaError("SchemaAuthority apply_schema did not return verified deployment proof with applied=True.")
            applied_count = res["applied_count"]
        elif hasattr(self.coordinator.transport_authority, "apply_schema"):
            res = self.coordinator.transport_authority.apply_schema(payload)
            if not isinstance(res, dict) or not res.get("applied") or "applied_count" not in res:
                from akaalEngine.schema.models.errors import SchemaError
                raise SchemaError("TransportAuthority apply_schema did not return verified deployment proof with applied=True.")
            applied_count = res["applied_count"]
        else:
            from akaalEngine.schema.models.errors import SchemaError
            raise SchemaError("Schema deployment rejected: Physical schema deployment requires an active TargetWriter driver with execute_ddl() capability or a registered SchemaAuthority deployment connector. Synthetic deployment of raw table names or DDL strings without execution is forbidden.")

        return GatewayResponse.create_success(
            operation_id=ctx.operation_id, operation_type=SemanticOperation.APPLY_SCHEMA_CHANGES.value,
            migration_id=ctx.migration_id, run_id=ctx.run_id,
            payload={"schema_applied": True, "applied_count": applied_count, "tables": tables, "status": "DEPLOYED"},
            fencing_epoch=ctx.fencing_epoch, proof_classification="UNIT_PROVEN"
        )

    def _handle_prepare_migration(self, ctx: GatewayRequestContext, payload: Dict[str, Any]) -> GatewayResponse[Dict[str, Any]]:
        self.coordinator.check_cancellation(ctx)
        self.coordinator.check_fencing(ctx)
        from akaalEngine.durability.models import MigrationCheckpoint, FencingToken
        env = getattr(ctx, "fencing_token_envelope", None)
        if env:
            token = FencingToken(
                resource_id=env.get("resource_id") or env.get("canonical_resource_id") or ctx.migration_id,
                worker_id=env.get("worker_id", "gateway"),
                fencing_epoch=env.get("fencing_epoch", ctx.fencing_epoch or 1),
                issued_at=env.get("issued_at", ""),
                signature=env.get("signature") or env.get("engine_signature", ""),
            )
        else:
            token = self.coordinator.durability_authority.issue_fencing_token(ctx.migration_id, "gateway")
        ckpt = MigrationCheckpoint(migration_id=ctx.migration_id, job_id=ctx.run_id or "job-prep", fencing_epoch=token.fencing_epoch, status="PREPARED")
        self.coordinator.durability_authority.save_checkpoint(ckpt, token)
        return GatewayResponse.create_success(
            operation_id=ctx.operation_id, operation_type=SemanticOperation.PREPARE_MIGRATION_EXECUTION.value,
            migration_id=ctx.migration_id, run_id=ctx.run_id,
            payload={"prepared": True, "checkpoint_id": ckpt.job_id, "status": "READY"},
            fencing_epoch=ctx.fencing_epoch, proof_classification="UNIT_PROVEN"
        )

    def _handle_initialize_cdc(self, ctx: GatewayRequestContext, payload: Dict[str, Any]) -> GatewayResponse[Dict[str, Any]]:
        self.coordinator.check_cancellation(ctx)
        self.coordinator.check_fencing(ctx)
        if hasattr(self.coordinator.cdc_authority, "initialize_stream"):
            res = self.coordinator.cdc_authority.initialize_stream(ctx.migration_id)
        elif hasattr(self.coordinator.cdc_authority, "start_capture"):
            res = self.coordinator.cdc_authority.start_capture()
        else:
            from akaalEngine.cdc.models.errors import CDCCapabilityError
            raise CDCCapabilityError("CDCAuthority does not support physical stream initialization.")

        # Extract provider-established capture and boundary truth directly from active adapter or returned snapshot
        adapter = getattr(self.coordinator.cdc_authority, "active_adapter", None)
        stream_handle = None
        boundary_token = None

        if adapter:
            raw_handle = getattr(adapter, "stream_handle", getattr(adapter, "slot_name", getattr(adapter, "stream_id", None)))
            if raw_handle is not None:
                stream_handle = getattr(raw_handle, "name", str(raw_handle))
            if hasattr(adapter, "get_current_position"):
                pos = adapter.get_current_position()
                boundary_token = getattr(pos, "position_str", str(pos) if pos else None)

        if not stream_handle:
            stream_handle = (
                getattr(res, "stream_handle", None)
                or getattr(res, "slot_name", None)
                or getattr(res, "stream_id", None)
                or (res.to_dict().get("stream_handle") if hasattr(res, "to_dict") else None)
                or (res.get("stream_handle") if isinstance(res, Mapping) else None)
            )
        if not boundary_token:
            boundary_token = (
                getattr(res, "boundary_token", None)
                or getattr(res, "source_position", None)
                or getattr(res, "durable_capture_position", None)
                or getattr(res, "barrier_position", None)
                or (res.to_dict().get("source_position") if hasattr(res, "to_dict") else None)
                or (res.to_dict().get("boundary_token") if hasattr(res, "to_dict") else None)
                or (res.get("source_position") if isinstance(res, Mapping) else None)
            )

        if not stream_handle or not boundary_token:
            from akaalEngine.cdc.models.errors import CDCCapabilityError
            raise CDCCapabilityError(f"CDC stream initialization failed for migration '{ctx.migration_id}': Active CDC provider did not return or establish genuine stream_handle and boundary_position.")

        return GatewayResponse.create_success(
            operation_id=ctx.operation_id, operation_type=SemanticOperation.INITIALIZE_CDC_STREAM.value,
            migration_id=ctx.migration_id, run_id=ctx.run_id,
            payload={
                "cdc_stream_handle": stream_handle,
                "cdc_boundary_token": boundary_token,
                "cdc_snapshot": str(res),
                "status": "ACTIVE_CAPTURING",
            },
            fencing_epoch=ctx.fencing_epoch, proof_classification="UNIT_PROVEN"
        )

    def _handle_execute_atomic_cutover(self, ctx: GatewayRequestContext, payload: Dict[str, Any]) -> GatewayResponse[Dict[str, Any]]:
        self.coordinator.check_cancellation(ctx)
        self.coordinator.check_fencing(ctx)
        pos = payload.get("cdc_boundary_position", "0/200")
        if hasattr(self.coordinator.cdc_authority, "execute_atomic_cutover"):
            res = self.coordinator.cdc_authority.execute_atomic_cutover(pos)
        else:
            from akaalEngine.cdc.models.errors import CDCCutoverNotReadyError
            raise CDCCutoverNotReadyError("CDCAuthority does not support physical atomic cutover execution.")
        return GatewayResponse.create_success(
            operation_id=ctx.operation_id, operation_type=SemanticOperation.EXECUTE_ATOMIC_CUTOVER.value,
            migration_id=ctx.migration_id, run_id=ctx.run_id,
            payload={"cutover_status": "COMMITTED", "boundary_position": pos, "cdc_snapshot": str(res)},
            fencing_epoch=ctx.fencing_epoch, proof_classification="UNIT_PROVEN"
        )

    def _handle_trigger_checkpoint(self, ctx: GatewayRequestContext, payload: Dict[str, Any]) -> GatewayResponse[Dict[str, Any]]:
        self.coordinator.check_cancellation(ctx)
        self.coordinator.check_fencing(ctx)
        from akaalEngine.durability.models import MigrationCheckpoint
        token = self.coordinator.durability_authority.issue_fencing_token(ctx.migration_id, "gateway")
        chk_id = payload.get("checkpoint_id") or payload.get("batch_id") or f"chk-{ctx.operation_id}"
        ckpt = MigrationCheckpoint(migration_id=ctx.migration_id, job_id=chk_id, fencing_epoch=token.fencing_epoch, status="FLUSHED")
        self.coordinator.durability_authority.save_checkpoint(ckpt, token)
        return GatewayResponse.create_success(
            operation_id=ctx.operation_id, operation_type=SemanticOperation.TRIGGER_CHECKPOINT.value,
            migration_id=ctx.migration_id, run_id=ctx.run_id,
            payload={"checkpoint_id": chk_id, "status": "FLUSHED"},
            fencing_epoch=ctx.fencing_epoch, proof_classification="UNIT_PROVEN"
        )

    def _handle_verify_checkpoint(self, ctx: GatewayRequestContext, payload: Dict[str, Any]) -> GatewayResponse[Dict[str, Any]]:
        self.coordinator.check_cancellation(ctx)
        self.coordinator.check_fencing(ctx)
        chk_id = payload.get("checkpoint_id") or payload.get("batch_id")
        chk = None
        if chk_id and hasattr(self.coordinator.durability_authority, "get_checkpoint"):
            chk = self.coordinator.durability_authority.get_checkpoint(chk_id)
        if chk is None:
            chk = self.coordinator.durability_authority.get_latest_checkpoint(ctx.migration_id)
        if chk is None or (chk_id and getattr(chk, "job_id", None) != chk_id):
            from akaalEngine.durability.models.errors import DurabilityError
            raise DurabilityError(f"Checkpoint verification failed: Checkpoint '{chk_id}' not found for migration '{ctx.migration_id}'.")
        return GatewayResponse.create_success(
            operation_id=ctx.operation_id, operation_type=SemanticOperation.VERIFY_CHECKPOINT.value,
            migration_id=ctx.migration_id, run_id=ctx.run_id,
            payload={"checkpoint": str(chk), "checkpoint_id": getattr(chk, "job_id", chk_id), "status": "VERIFIED"},
            fencing_epoch=ctx.fencing_epoch, proof_classification="UNIT_PROVEN"
        )

    def _handle_recover_checkpoint(self, ctx: GatewayRequestContext, payload: Dict[str, Any]) -> GatewayResponse[Dict[str, Any]]:
        self.coordinator.check_cancellation(ctx)
        self.coordinator.check_fencing(ctx)
        chk_id = payload.get("checkpoint_id") or payload.get("batch_id")
        if not chk_id:
            from akaalEngine.durability.models.errors import DurabilityError
            raise DurabilityError(f"Checkpoint recovery failed: 'checkpoint_id' parameter is required for migration '{ctx.migration_id}'.")

        # Exact, non-fallback canonical durability recovery
        chk = self.coordinator.durability_authority.recover_checkpoint(
            chk_id, migration_id=ctx.migration_id, run_id=ctx.run_id
        )

        task_id = (
            payload.get("task_id")
            or getattr(chk, "task_id", None)
            or (chk.metadata.get("task_id") if isinstance(getattr(chk, "metadata", None), dict) else None)
            or (chk.metadata.get("runtime_task_id") if isinstance(getattr(chk, "metadata", None), dict) else None)
        )
        if not task_id:
            from akaalEngine.durability.models.errors import DurabilityError
            raise DurabilityError(f"Checkpoint recovery failed: Checkpoint '{chk_id}' does not contain an authoritative runtime task_id. Arbitrary checkpoint job_id cannot be assumed as runtime task identity.")

        # Restore runtime authority task state without swallowing exceptions
        if not self.coordinator.runtime_authority or not hasattr(self.coordinator.runtime_authority, "restore_task"):
            from akaalEngine.runtime.models import RuntimeEngineException
            raise RuntimeEngineException("Recovery rejected: RuntimeAuthority is required and must support restore_task to reconstruct execution state.")

        from akaalEngine.runtime.models.task import TaskSpec
        spec = TaskSpec(
            task_id=task_id,
            task_type="migration_recovery",
            metadata={"migration_id": ctx.migration_id, "checkpoint_id": chk_id},
        )
        restored_task = self.coordinator.runtime_authority.restore_task(spec)
        if restored_task is None:
            from akaalEngine.runtime.models import RuntimeEngineException
            raise RuntimeEngineException(f"RuntimeAuthority failed to restore task '{task_id}' for checkpoint '{chk_id}'.")

        restored_state = getattr(getattr(restored_task, "state", None), "value", str(getattr(restored_task, "state", "RESTORED")))

        return GatewayResponse.create_success(
            operation_id=ctx.operation_id,
            operation_type=SemanticOperation.RECOVER_FROM_CHECKPOINT.value,
            migration_id=ctx.migration_id,
            run_id=ctx.run_id,
            payload={
                "checkpoint": str(chk),
                "checkpoint_id": getattr(chk, "job_id", chk_id),
                "restored_task_id": restored_task.task_id,
                "restored_state": restored_state,
                "status": "RECOVERED",
                "restored_task": str(restored_task),
            },
            fencing_epoch=ctx.fencing_epoch,
            proof_classification="UNIT_PROVEN",
            job_id=getattr(chk, "job_id", chk_id),
        )

    def _handle_pause_execution(self, ctx: GatewayRequestContext, payload: Dict[str, Any]) -> GatewayResponse[Dict[str, Any]]:
        self.coordinator.check_cancellation(ctx)
        self.coordinator.check_fencing(ctx)
        task_id = payload.get("task_id", f"task-{ctx.operation_id}")
        snap = self.coordinator.runtime_authority.pause_task(task_id)
        return GatewayResponse.create_success(
            operation_id=ctx.operation_id, operation_type=SemanticOperation.PAUSE_EXECUTION.value,
            migration_id=ctx.migration_id, run_id=ctx.run_id,
            payload={"status": str(getattr(snap, "state", "PAUSED"))},
            fencing_epoch=ctx.fencing_epoch, proof_classification="UNIT_PROVEN"
        )

    def _handle_resume_execution(self, ctx: GatewayRequestContext, payload: Dict[str, Any]) -> GatewayResponse[Dict[str, Any]]:
        self.coordinator.check_cancellation(ctx)
        self.coordinator.check_fencing(ctx)
        task_id = payload.get("task_id", f"task-{ctx.operation_id}")
        snap = self.coordinator.runtime_authority.resume_task(task_id)
        return GatewayResponse.create_success(
            operation_id=ctx.operation_id, operation_type=SemanticOperation.RESUME_EXECUTION.value,
            migration_id=ctx.migration_id, run_id=ctx.run_id,
            payload={"status": str(getattr(snap, "state", "RESUMED"))},
            fencing_epoch=ctx.fencing_epoch, proof_classification="UNIT_PROVEN"
        )

    def _handle_cancel_execution(self, ctx: GatewayRequestContext, payload: Dict[str, Any]) -> GatewayResponse[Dict[str, Any]]:
        if ctx.cancellation_event:
            ctx.cancellation_event.set()
        task_id = payload.get("task_id")
        if not task_id:
            from akaalEngine.runtime.models.errors import RuntimeEngineException
            raise RuntimeEngineException("Cancellation rejected: task_id parameter is required.")

        snap = self.coordinator.runtime_authority.cancel_task(task_id)

        # Authoritatively query runtime task state to verify terminal transition
        if hasattr(self.coordinator.runtime_authority, "get_task_snapshot"):
            snap = self.coordinator.runtime_authority.get_task_snapshot(task_id) or snap

        is_terminal = getattr(snap, "is_terminal", False)
        state_str = getattr(getattr(snap, "state", None), "value", str(getattr(snap, "state", "CANCELLED")))
        if not is_terminal and state_str not in ("CANCELLED", "FAILED", "SUCCEEDED", "ABANDONED"):
            return GatewayResponse.create_failure(
                operation_id=ctx.operation_id,
                operation_type=SemanticOperation.CANCEL_EXECUTION.value,
                failure_category=GatewayFailureCategory.INVALID_REQUEST,
                error_message=f"Runtime task '{task_id}' has not transitioned to terminal state; current state is {state_str}.",
                migration_id=ctx.migration_id,
                run_id=ctx.run_id,
                fencing_epoch=ctx.fencing_epoch,
            )

        return GatewayResponse.create_success(
            operation_id=ctx.operation_id, operation_type=SemanticOperation.CANCEL_EXECUTION.value,
            migration_id=ctx.migration_id, run_id=ctx.run_id,
            payload={"status": state_str, "task_id": task_id, "terminal": True},
            fencing_epoch=ctx.fencing_epoch, proof_classification="UNIT_PROVEN"
        )

    def _handle_get_progress(self, ctx: GatewayRequestContext, payload: Dict[str, Any]) -> GatewayResponse[Dict[str, Any]]:
        self.coordinator.check_cancellation(ctx)
        prog = self.coordinator.telemetry_authority.get_progress_snapshot(ctx.migration_id)
        return GatewayResponse.create_success(
            operation_id=ctx.operation_id, operation_type=SemanticOperation.GET_MIGRATION_PROGRESS.value,
            migration_id=ctx.migration_id, run_id=ctx.run_id,
            payload={"progress": str(prog)},
            fencing_epoch=ctx.fencing_epoch, proof_classification="UNIT_PROVEN"
        )

    def _handle_get_health(self, ctx: GatewayRequestContext, payload: Dict[str, Any]) -> GatewayResponse[Dict[str, Any]]:
        self.coordinator.check_cancellation(ctx)
        h_snap = self.coordinator.telemetry_authority.get_health_snapshot()
        return GatewayResponse.create_success(
            operation_id=ctx.operation_id, operation_type=SemanticOperation.GET_HEALTH_DIAGNOSTICS.value,
            migration_id=ctx.migration_id, run_id=ctx.run_id,
            payload={"health": str(h_snap)},
            fencing_epoch=ctx.fencing_epoch, proof_classification="UNIT_PROVEN"
        )

    def _handle_data_cleansing(self, ctx: GatewayRequestContext, payload: Dict[str, Any]) -> GatewayResponse[Dict[str, Any]]:
        self.coordinator.check_cancellation(ctx)
        self.coordinator.check_fencing(ctx)
        recs = payload.get("records", [])
        rules = payload.get("rules", [])
        plan = self.coordinator.data_processing_authority.compile_plan(object_name=ctx.migration_id, rules=rules)
        transformed, _ = self.coordinator.data_processing_authority.transform_batch(recs, plan)
        return GatewayResponse.create_success(
            operation_id=ctx.operation_id, operation_type=SemanticOperation.EXECUTE_DATA_CLEANSING.value,
            migration_id=ctx.migration_id, run_id=ctx.run_id,
            payload={"records_processed": len(transformed), "cleansed_records": transformed},
            fencing_epoch=ctx.fencing_epoch, proof_classification="UNIT_PROVEN"
        )

    def _handle_privacy_masking(self, ctx: GatewayRequestContext, payload: Dict[str, Any]) -> GatewayResponse[Dict[str, Any]]:
        self.coordinator.check_cancellation(ctx)
        self.coordinator.check_fencing(ctx)
        recs = payload.get("records", [])
        rules = payload.get("privacy_rules", payload.get("rules", []))
        plan = self.coordinator.data_processing_authority.compile_plan(object_name=ctx.migration_id, rules=rules)
        transformed, _ = self.coordinator.data_processing_authority.transform_batch(recs, plan)
        return GatewayResponse.create_success(
            operation_id=ctx.operation_id, operation_type=SemanticOperation.APPLY_PRIVACY_MASKING.value,
            migration_id=ctx.migration_id, run_id=ctx.run_id,
            payload={"records_masked": len(transformed), "masked_records": transformed},
            fencing_epoch=ctx.fencing_epoch, proof_classification="UNIT_PROVEN"
        )

    def _handle_reconcile_disputed(self, ctx: GatewayRequestContext, payload: Dict[str, Any]) -> GatewayResponse[Dict[str, Any]]:
        self.coordinator.check_cancellation(ctx)
        self.coordinator.check_fencing(ctx)
        src_recs = payload.get("source_records", payload.get("disputed_records", []))
        tgt_recs = payload.get("target_records", [])
        if not src_recs or not tgt_recs:
            from akaalEngine.validation.models.errors import ReconciliationMismatchError
            raise ReconciliationMismatchError("Reconciliation requires both source_records and target_records to resolve disputed records.")
        key_cols = payload.get("key_columns", ["id"])
        if hasattr(self.coordinator.validation_authority, "reconcile_disputed"):
            res = self.coordinator.validation_authority.reconcile_disputed(ctx.migration_id, src_recs, tgt_recs, key_cols)
        elif hasattr(self.coordinator.validation_authority, "exact_reconciler"):
            res = self.coordinator.validation_authority.exact_reconciler.reconcile_exact(src_recs, tgt_recs, key_cols)
        else:
            from akaalEngine.validation.models.errors import ReconciliationMismatchError
            raise ReconciliationMismatchError("ValidationAuthority does not support disputed record reconciliation.")
        return GatewayResponse.create_success(
            operation_id=ctx.operation_id, operation_type=SemanticOperation.RECONCILE_DISPUTED_RECORDS.value,
            migration_id=ctx.migration_id, run_id=ctx.run_id,
            payload={"result": str(res)},
            fencing_epoch=ctx.fencing_epoch, proof_classification="UNIT_PROVEN"
        )

    def _handle_incremental_extract(self, ctx: GatewayRequestContext, payload: Dict[str, Any]) -> GatewayResponse[Dict[str, Any]]:
        self.coordinator.check_cancellation(ctx)
        self.coordinator.check_fencing(ctx)
        wm_col = payload.get("watermark_column", "updated_at")
        wm_val = payload.get("watermark_value", 0)
        reader = payload.get("source_reader") or payload.get("reader")

        if reader and hasattr(reader, "read_batch"):
            batch = reader.read_batch(partition=payload.get("partition")) if payload.get("partition") else reader.read_batch()
            extracted_records = len(getattr(batch, "rows", [])) if hasattr(batch, "rows") else (len(batch) if isinstance(batch, list) else 0)
            extracted_wm = wm_val + extracted_records if isinstance(wm_val, int) else wm_val
        elif hasattr(self.coordinator.transport_authority, "extract_incremental"):
            res = self.coordinator.transport_authority.extract_incremental(payload)
            extracted_records = res.get("extracted_records", 0)
            extracted_wm = res.get("extracted_watermark", wm_val)
        else:
            from akaalEngine.transport.models.errors import TransportError
            raise TransportError("Incremental extraction requires an active, validated SourceReader driver or registered transport connector. Synthetic record payloads are forbidden.")

        return GatewayResponse.create_success(
            operation_id=ctx.operation_id, operation_type=SemanticOperation.EXECUTE_INCREMENTAL_EXTRACT.value,
            migration_id=ctx.migration_id, run_id=ctx.run_id,
            payload={"extracted_records": extracted_records, "watermark_column": wm_col, "extracted_watermark": extracted_wm, "status": "EXTRACTED"},
            fencing_epoch=ctx.fencing_epoch, proof_classification="UNIT_PROVEN"
        )

    def _handle_incremental_apply(self, ctx: GatewayRequestContext, payload: Dict[str, Any]) -> GatewayResponse[Dict[str, Any]]:
        self.coordinator.check_cancellation(ctx)
        self.coordinator.check_fencing(ctx)
        wm_col = payload.get("watermark_column", "updated_at")
        wm_val = payload.get("watermark_value", 0)
        writer = payload.get("target_writer") or payload.get("writer")

        applied_records = 0
        if writer:
            from akaalEngine.transport.drivers.base import TargetWriter
            if not isinstance(writer, TargetWriter):
                from akaalEngine.transport.models.errors import TransportError
                raise TransportError("TargetWriter must inherit from canonical TargetWriter base class.")
            batch = payload.get("batch")
            if batch is None:
                from akaalEngine.transport.models.errors import TransportError
                raise TransportError("Incremental apply requires a physical batch payload to write to the target.")
            applied_records = writer.write_batch(
                table_name=payload.get("table_name", "default_table"),
                batch=batch,
            )
            c_res = writer.commit()
            if c_res is False:
                from akaalEngine.transport.models.errors import TransportError
                raise TransportError("TargetWriter physical commit failed.")

            # Watermark derived strictly from committed batch records
            rows = getattr(batch, "rows", batch if isinstance(batch, list) else [])
            col_vals = [r.get(wm_col) for r in rows if isinstance(r, dict) and wm_col in r]
            if not col_vals:
                from akaalEngine.transport.models.errors import TransportError
                raise TransportError(f"Committed batch does not contain required watermark column '{wm_col}'. Watermark cannot be derived.")
            committed_wm = max(col_vals)
        elif hasattr(self.coordinator.transport_authority, "apply_incremental"):
            res = self.coordinator.transport_authority.apply_incremental(payload)
            if not isinstance(res, dict) or not res.get("committed") or "target_commit_receipt" not in res:
                from akaalEngine.transport.models.errors import TransportError
                raise TransportError("TransportAuthority apply_incremental returned without verified physical target_commit_receipt and committed=True.")
            applied_records = res.get("applied_records", 0)
            if "committed_watermark" not in res:
                from akaalEngine.transport.models.errors import TransportError
                raise TransportError("TransportAuthority apply_incremental did not return a committed_watermark derived from target commit.")
            committed_wm = res["committed_watermark"]
        else:
            from akaalEngine.transport.models.errors import TransportError
            raise TransportError("Incremental apply requires an active, validated TargetWriter driver or registered transport connector with verified commit proof. Synthetic record payloads are forbidden.")

        # Persist watermark checkpoint ONLY by reconstructing caller's authenticated fencing token
        if hasattr(self.coordinator.durability_authority, "save_checkpoint"):
            from akaalEngine.durability.models import MigrationCheckpoint, FencingToken
            from akaalEngine.durability.models.errors import FencingViolationError

            env = getattr(ctx, "fencing_token_envelope", None)
            if not env:
                raise FencingViolationError("Cannot persist durable watermark checkpoint without an authenticated fencing_token_envelope from DurabilityAuthority.")

            token = FencingToken(
                resource_id=env.get("resource_id") or env.get("canonical_resource_id") or ctx.migration_id,
                worker_id=env.get("worker_id", "gateway"),
                fencing_epoch=env.get("fencing_epoch", ctx.fencing_epoch or 1),
                issued_at=env.get("issued_at", ""),
                signature=env.get("signature") or env.get("engine_signature", ""),
            )
            if hasattr(self.coordinator.durability_authority, "validate_fencing_token"):
                if not self.coordinator.durability_authority.validate_fencing_token(token):
                    raise FencingViolationError("Fencing token HMAC signature validation failed for watermark checkpoint persistence.")

            chk = MigrationCheckpoint(
                migration_id=ctx.migration_id,
                job_id=f"wm-{ctx.operation_id}",
                fencing_epoch=token.fencing_epoch,
                status="COMMITTED",
                metadata={"watermark_column": wm_col, "watermark_value": committed_wm, "applied_records": applied_records, "task_id": f"task-wm-{ctx.operation_id}"},
            )
            self.coordinator.durability_authority.save_checkpoint(chk, token)

        return GatewayResponse.create_success(
            operation_id=ctx.operation_id, operation_type=SemanticOperation.EXECUTE_INCREMENTAL_APPLY.value,
            migration_id=ctx.migration_id, run_id=ctx.run_id,
            payload={"applied_records": applied_records, "committed_watermark": committed_wm, "status": "COMMITTED"},
            fencing_epoch=ctx.fencing_epoch, proof_classification="UNIT_PROVEN"
        )

    def _handle_rollback_batch(self, ctx: GatewayRequestContext, payload: Dict[str, Any]) -> GatewayResponse[Dict[str, Any]]:
        self.coordinator.check_cancellation(ctx)
        self.coordinator.check_fencing(ctx)
        batch_id = payload.get("batch_id", f"batch-{ctx.operation_id}")

        # Stage 1: Verify Durability Authority (#5) batch existence & bound migration_id
        if not self.coordinator.durability_authority.verify_batch_exists(batch_id):
            from akaalEngine.durability.models.errors import DurabilityError
            raise DurabilityError(f"Rollback rejected: no checkpoint, idempotency record, or journal entry found for batch_id '{batch_id}'.")

        durable_mig_id = self.coordinator.durability_authority.get_batch_migration_id(batch_id)
        if durable_mig_id and durable_mig_id != ctx.migration_id:
            from akaalEngine.durability.models.errors import DurabilityError
            raise DurabilityError(f"Rollback rejected: batch_id '{batch_id}' is bound to migration_id '{durable_mig_id}', not context migration '{ctx.migration_id}'.")

        writer = payload.get("target_writer") or payload.get("writer")

        # Stage 2: Strict TargetWriter Identity Verification (Inescapable Identity Binding & Type Safety)
        if writer:
            from akaalEngine.transport.drivers.base import TargetWriter
            if not isinstance(writer, TargetWriter):
                from akaalEngine.durability.models.errors import DurabilityError
                raise DurabilityError("TargetWriter must inherit from canonical TargetWriter base class. Duck-typed payload objects are rejected.")

            writer_mig = getattr(writer, "migration_id", None)
            if writer_mig is None:
                from akaalEngine.durability.models.errors import DurabilityError
                raise DurabilityError(f"TargetWriter has no execution-established migration_id matching context migration '{ctx.migration_id}'. Unbound writer rollback rejected.")
            if writer_mig != ctx.migration_id:
                from akaalEngine.durability.models.errors import DurabilityError
                raise DurabilityError(f"TargetWriter migration identity '{writer_mig}' mismatch with context migration '{ctx.migration_id}'. Cross-migration writer rollback forbidden.")

            writer_batch = getattr(writer, "batch_id", getattr(writer, "job_id", None))
            if writer_batch is None:
                from akaalEngine.durability.models.errors import DurabilityError
                raise DurabilityError(f"TargetWriter has no execution-established batch_id matching requested batch_id '{batch_id}'. Unbound batch writer rollback rejected.")
            if writer_batch != batch_id:
                from akaalEngine.durability.models.errors import DurabilityError
                raise DurabilityError(f"TargetWriter active batch identity '{writer_batch}' mismatch with requested batch_id '{batch_id}'. Unrelated writer rollback forbidden.")

            writer_ep = getattr(writer, "endpoint_identity", None)
            durable_ep = self.coordinator.durability_authority.get_batch_endpoint_identity(batch_id) if hasattr(self.coordinator.durability_authority, "get_batch_endpoint_identity") else None
            req_ep = payload.get("endpoint_identity") or payload.get("target_endpoint")

            if writer_ep is None:
                from akaalEngine.durability.models.errors import DurabilityError
                raise DurabilityError(f"TargetWriter endpoint_identity is missing. Endpoint identity is required for physical target rollback of batch '{batch_id}'.")
            if durable_ep is None:
                from akaalEngine.durability.models.errors import DurabilityError
                raise DurabilityError(f"No durable checkpoint endpoint_identity found for batch_id '{batch_id}'. Independent durable comparison failed.")
            if writer_ep != durable_ep:
                from akaalEngine.durability.models.errors import DurabilityError
                raise DurabilityError(f"TargetWriter endpoint identity '{writer_ep}' mismatch with durable checkpoint endpoint '{durable_ep}'. Unrelated endpoint rollback forbidden.")
            if req_ep and writer_ep != req_ep:
                from akaalEngine.durability.models.errors import DurabilityError
                raise DurabilityError(f"TargetWriter endpoint identity '{writer_ep}' mismatch with requested target endpoint '{req_ep}'.")

        # Stage 3: Stage PENDING_ROLLBACK state in Durability BEFORE TargetWriter rollback
        self.coordinator.durability_authority.stage_pending_rollback(batch_id)

        # Stage 4: Physically execute Target Writer / Transport Authority (#9) rollback matching canonical TargetWriter.rollback()
        target_rolled_back = False
        try:
            if writer and hasattr(writer, "rollback"):
                writer.rollback()
                target_rolled_back = True
            elif hasattr(self.coordinator.transport_authority, "rollback_batch"):
                res_transport = self.coordinator.transport_authority.rollback_batch(batch_id)
                target_rolled_back = bool(res_transport)

            if not target_rolled_back:
                from akaalEngine.durability.models.errors import DurabilityError
                raise DurabilityError(f"Physical transaction batch rollback rejected: active TargetWriter or TransportAuthority with physical rollback capability is required to roll back target data for batch '{batch_id}'.")

        except Exception as exc:
            self.coordinator.durability_authority.record_rollback_failure(batch_id, str(exc))
            from akaalEngine.durability.models.errors import DurabilityError
            raise DurabilityError(f"Target rollback failed for batch '{batch_id}': {exc}") from exc

        # Stage 5: Finalize Durability Authority (#5) batch rollback tombstone (ROLLED_BACK)
        res = self.coordinator.durability_authority.rollback_batch(batch_id)
        return GatewayResponse.create_success(
            operation_id=ctx.operation_id, operation_type=SemanticOperation.ROLLBACK_TRANSACTION_BATCH.value,
            migration_id=ctx.migration_id, run_id=ctx.run_id,
            payload={"batch_id": batch_id, "durability_result": str(res), "target_rolled_back": True, "status": "ROLLED_BACK"},
            fencing_epoch=ctx.fencing_epoch, proof_classification="UNIT_PROVEN"
        )

    def _handle_finalize_run(self, ctx: GatewayRequestContext, payload: Dict[str, Any]) -> GatewayResponse[Dict[str, Any]]:
        self.coordinator.check_cancellation(ctx)
        self.coordinator.check_fencing(ctx)
        exec_art = self.coordinator.evidence_authority.package_execution_evidence(
            migration_id=ctx.migration_id, run_id=ctx.run_id, execution_state="COMPLETED",
            artifact_id=f"art-final-{ctx.operation_id}"
        )
        return GatewayResponse.create_success(
            operation_id=ctx.operation_id, operation_type=SemanticOperation.FINALIZE_MIGRATION_RUN.value,
            migration_id=ctx.migration_id, run_id=ctx.run_id,
            payload={"final_status": "COMPLETED", "evidence_artifact_id": exec_art.artifact_id},
            fencing_epoch=ctx.fencing_epoch, proof_classification="UNIT_PROVEN"
        )
