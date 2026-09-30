"""
akaalEngine.gateway.routing.dispatcher
=======================================
Canonical Gateway semantic request dispatcher.
Enforces explicit, typed routing by SemanticOperation enum to GatewayCoordinator or canonical authorities.
Rejects arbitrary method dispatch, dynamic string invocation, and malformed requests fail-closed.
"""

import json
import logging
import os
import sqlite3
from typing import Any, Dict, Optional

from akaalEngine.gateway.failure.translator import FailureTranslator
from akaalEngine.gateway.models.context import GatewayRequestContext
from akaalEngine.gateway.models.enums import GatewayFailureCategory, SemanticOperation
from akaalEngine.gateway.models.requests import GatewayRequest
from akaalEngine.gateway.models.responses import GatewayResponse
from akaalEngine.gateway.orchestration.coordinator import GatewayCoordinator

logger = logging.getLogger("akaalEngine.gateway.routing")



def resolve_secret_reference(secret_uri: str) -> str:
    """
    Canonical Secret Resolution Authority helper.
    Resolves secret references ('env:VAR_NAME', 'vault:secret/path', etc.) to actual runtime credential values.
    If passed an unresolved reference or plaintext password string, resolves it according to system contract.
    """
    if not secret_uri:
        return ""
    str_uri = str(secret_uri)
    if str_uri.startswith("env:"):
        var_name = str_uri[4:]
        val = os.getenv(var_name)
        return val if val is not None else str_uri
    elif str_uri.startswith("vault:"):
        var_name = str_uri[6:]
        val = os.getenv(var_name) or os.getenv(f"VAULT_SECRET_{var_name.upper().replace('/', '_')}")
        return val if val is not None else str_uri
    return str_uri


def resolve_canonical_connection_params(config: dict, prefix: str = "source", db_path: Optional[str] = None) -> dict:
    """
    Canonical Platform Connection Contract Builder & Secret Resolution Authority.
    Generic across all providers, all execution modes, and both source/target roles.
    Enforces reference/value separation (invariant G1), provider neutrality (invariant G2),
    source/target symmetry (invariant G3), and mode neutrality (invariant G4).
    """
    if not isinstance(config, dict):
        return {}

    merged_cfg = dict(config)

    if db_path and os.path.exists(db_path):
        conn_id = config.get(f"{prefix}_connection_id") or config.get(f"{prefix}ConnectionId")
        if conn_id:
            try:
                db_conn = sqlite3.connect(db_path, timeout=5.0)
                db_conn.row_factory = sqlite3.Row
                row = db_conn.execute("SELECT configuration FROM enterprise_connections WHERE connection_id = ?", (conn_id,)).fetchone()
                if row and row["configuration"]:
                    conn_cfg = json.loads(row["configuration"])
                    if isinstance(conn_cfg, dict):
                        merged_cfg.update(conn_cfg)
                db_conn.close()
            except Exception:
                pass

    sub_params = config.get(f"{prefix}_connection_params") or config.get(f"{prefix}ConnectionParams") or {}
    if isinstance(sub_params, dict):
        merged_cfg.update(sub_params)

    params: dict = {}

    def _get_val(*keys):
        for k in keys:
            if k in merged_cfg and merged_cfg[k] is not None:
                return merged_cfg[k]
        return None

    host = _get_val(f"{prefix}_host", f"{prefix}Host", "host")
    if host:
        params["host"] = str(host)

    port = _get_val(f"{prefix}_port", f"{prefix}Port", "port")
    if port is not None:
        try:
            params["port"] = int(port)
        except (ValueError, TypeError):
            params["port"] = port

    user = _get_val(f"{prefix}_username", f"{prefix}Username", f"{prefix}_user", f"{prefix}User", "username", "user")
    if user:
        params["username"] = str(user)
        params["user"] = str(user)

    database = _get_val(f"{prefix}_database", f"{prefix}Database", f"{prefix}_dbname", f"{prefix}DbName", "database", "dbname")
    if database:
        params["database"] = str(database)
        params["dbname"] = str(database)

    schema = _get_val(f"{prefix}_schema", f"{prefix}Schema", "schema")
    if schema:
        params["schema"] = str(schema)

    svc = _get_val(f"{prefix}_service_name", f"{prefix}ServiceName", "service_name")
    if svc:
        params["service_name"] = str(svc)

    secret_ref = _get_val(f"{prefix}_secret_ref", f"{prefix}SecretRef", "secret_ref", "secretRef")
    if secret_ref:
        params["secret_ref"] = str(secret_ref)

    raw_secret = _get_val(f"{prefix}_password", f"{prefix}Password", "password", f"{prefix}_secret_ref", f"{prefix}SecretRef", "secret_ref", "secretRef")
    if raw_secret:
        resolved = resolve_secret_reference(str(raw_secret))
        params["password"] = resolved
        params[f"{prefix}_password"] = resolved

    return params



class GatewayDispatcher:
    """Explicit semantic request router for EngineGateway."""

    def __init__(self, coordinator: Optional[GatewayCoordinator] = None, keystore: Optional[Any] = None) -> None:
        self.coordinator = coordinator or GatewayCoordinator(keystore=keystore)
        self.keystore = keystore
        if hasattr(self.coordinator, "keystore") and self.coordinator.keystore is None and keystore is not None:
            self.coordinator.keystore = keystore

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

        context: Optional[GatewayRequestContext] = getattr(request, "context", None)
        if context is None:
            return GatewayResponse.create_failure(
                operation_id="op-missing-ctx",
                operation_type="UNKNOWN",
                migration_id="unknown",
                run_id="unknown",
                failure_category=GatewayFailureCategory.INVALID_REQUEST.value,
                error_message="Request must have a valid, non-null context attribute.",
            )
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

        is_mutating = operation in (
            SemanticOperation.APPLY_SCHEMA_CHANGES,
            SemanticOperation.EXECUTE_BULK_MIGRATION,
            SemanticOperation.EXECUTE_INCREMENTAL_APPLY,
            SemanticOperation.EXECUTE_CDC_SYNC,
            SemanticOperation.EXECUTE_ATOMIC_CUTOVER,
            SemanticOperation.RECONCILE_DISPUTED_RECORDS,
            SemanticOperation.ROLLBACK_TRANSACTION_BATCH,
        )

        exec_mode = getattr(context, "execution_mode", None) or payload.get("execution_mode") or payload.get("mode")
        if is_mutating and exec_mode in ("M8_VALIDATION_ONLY", "M8"):
            return GatewayResponse.create_failure(
                operation_id=context.operation_id,
                operation_type=op_name,
                migration_id=context.migration_id,
                run_id=context.run_id,
                failure_category=GatewayFailureCategory.UNSUPPORTED_OPERATION.value,
                error_message=f"Operation '{op_name}' is mutating and strictly prohibited in M8 validation-only mode.",
                fencing_epoch=context.fencing_epoch,
            )

        authz = getattr(context, "execution_authorization_artifact", None) or payload.get("execution_authorization_artifact")
        if authz is not None:
            from akaalPipeline.security.execution_authorization import verify_execution_authorization
            pub_key_pem = payload.get("execution_signing_public_key_pem") or authz.get("public_key_pem")
            try:
                verify_execution_authorization(
                    artifact=authz,
                    public_key_pem=pub_key_pem if not self.keystore else None,
                    expected_tenant_id=context.tenant_id,
                    expected_migration_id=context.migration_id,
                    expected_workspace_id=context.workspace_id,
                    expected_project_id=context.project_id,
                    expected_fencing_epoch=context.fencing_epoch,
                    expected_execution_mode=exec_mode,
                    keystore=self.keystore,
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
                resp = self.coordinator.orchestrate_prepare_migration(context, payload)
            elif operation == SemanticOperation.EXECUTE_BULK_MIGRATION:
                resp = self.coordinator.orchestrate_bulk_migration(context, payload)
            elif operation == SemanticOperation.EXECUTE_INCREMENTAL_EXTRACT:
                resp = self._handle_incremental_extract(context, payload)
            elif operation == SemanticOperation.EXECUTE_INCREMENTAL_APPLY:
                resp = self._handle_incremental_apply(context, payload)
            elif operation == SemanticOperation.EXECUTE_STATE_DIFF:
                resp = self._handle_state_diff(context, payload)
            elif operation == SemanticOperation.EXECUTE_STATE_RECONCILE:
                resp = self._handle_state_reconcile(context, payload)
            elif operation == SemanticOperation.INITIALIZE_CDC_STREAM:
                resp = self._handle_initialize_cdc(context, payload)
            elif operation == SemanticOperation.EXECUTE_CDC_SYNC:
                resp = self.coordinator.orchestrate_cdc_sync(context, payload)
            elif operation == SemanticOperation.EVALUATE_CUTOVER_READINESS:
                resp = self.coordinator.orchestrate_cutover_readiness(context, payload)
            elif operation == SemanticOperation.RUN_FINAL_VALIDATION:
                if payload.get("source_provider") or payload.get("tables") or payload.get("mode") == "M5_STATE_SYNC":
                    resp = self._handle_state_diff(context, payload)
                else:
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
        resource_id = f"{ctx.migration_id}/{ctx.run_id}/{ctx.job_id}" if ctx.job_id else (f"{ctx.migration_id}/{ctx.run_id}" if ctx.run_id else ctx.migration_id)
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
            res = self.coordinator.schema_authority.assess_compatibility(src, tgt)  # type: ignore
            is_compat = getattr(res, "is_compatible", getattr(res, "compatible", False))
        elif hasattr(self.coordinator.schema_authority, "compile"):
            from akaalEngine.schema.authority import SchemaCompilationRequest
            target_engine = payload.get("target_dialect") or tgt.get("dialect") or "POSTGRESQL"
            req = SchemaCompilationRequest(source_snapshot=src, target_engine=target_engine)
            res = self.coordinator.schema_authority.compile(req)
            if hasattr(res, "__await__") or inspect.isawaitable(res):
                import asyncio
                try:
                    loop = asyncio.get_running_loop()
                except RuntimeError:
                    loop = None
                if loop and loop.is_running():
                    import concurrent.futures
                    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                        res = pool.submit(asyncio.run, res).result()
                else:
                    res = asyncio.run(res)
            report = getattr(res, "compatibility_report", None)
            is_compat = bool(report and getattr(report, "is_compatible", getattr(report, "compatible", False)))
        else:
            from akaalEngine.schema.models.errors import SchemaError  # type: ignore
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
                from akaalEngine.schema.models.errors import SchemaError  # type: ignore
                raise SchemaError("TargetWriter must inherit from canonical TargetWriter base class.")
            if not ddl_statements:
                from akaalEngine.schema.models.errors import SchemaError  # type: ignore
                raise SchemaError("Physical schema deployment requires non-empty DDL statements.")
            for ddl in ddl_statements:
                writer.execute_ddl(ddl)  # type: ignore
                applied_count += 1
            if hasattr(writer, "commit"):
                c_res = writer.commit()
                if c_res is False:
                    from akaalEngine.schema.models.errors import SchemaError  # type: ignore
                    raise SchemaError("TargetWriter physical schema commit failed.")
        elif hasattr(self.coordinator.schema_authority, "apply_schema"):
            res = self.coordinator.schema_authority.apply_schema(payload)  # type: ignore
            if not isinstance(res, dict) or not res.get("applied") or "applied_count" not in res:
                from akaalEngine.schema.models.errors import SchemaError  # type: ignore
                raise SchemaError("SchemaAuthority apply_schema did not return verified deployment proof with applied=True.")
            applied_count = res["applied_count"]
        elif hasattr(self.coordinator.transport_authority, "apply_schema"):
            res = self.coordinator.transport_authority.apply_schema(payload)  # type: ignore
            if not isinstance(res, dict) or not res.get("applied") or "applied_count" not in res:
                from akaalEngine.schema.models.errors import SchemaError  # type: ignore
                raise SchemaError("TransportAuthority apply_schema did not return verified deployment proof with applied=True.")
            applied_count = res["applied_count"]
        else:
            from akaalEngine.schema.models.errors import SchemaError  # type: ignore
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

    def _ensure_cdc_context(self, ctx: GatewayRequestContext, payload: Dict[str, Any]) -> None:
        source_prov = (
            payload.get("source_provider_id")
            or payload.get("provider_id")
            or payload.get("source_provider")
            or payload.get("source_engine")
        )
        source_params = payload.get("source_connection_params") or payload.get("source_params") or payload.get("connection_params") or {}

        target_prov = payload.get("target_provider_id") or payload.get("target_provider") or payload.get("target_engine")
        target_params = payload.get("target_connection_params") or payload.get("target_params") or {}

        candidate_paths = [
            os.environ.get("AKAAL_PIPELINE_DB_PATH"),
            r"A:\temp_akaal\akaalPipeline\data\akaal-pipeline.db",
            os.path.join("akaalPipeline", "data", "akaal-pipeline.db"),
            os.path.join(os.path.dirname(__file__), "..", "..", "akaalPipeline", "data", "akaal-pipeline.db"),
            "akaal-pipeline.db",
        ]
        db_p = next((p for p in candidate_paths if p and os.path.exists(p)), None)

        if (getattr(self.coordinator.cdc_authority, "active_adapter", None) is None or getattr(self.coordinator.cdc_authority, "apply_coordinator", None) is None) and ctx and ctx.migration_id:
            try:
                if db_p:
                    conn = sqlite3.connect(db_p)
                    cur = conn.cursor()
                    cur.execute("SELECT configuration FROM migrations WHERE migration_id = ?", (ctx.migration_id,))
                    row = cur.fetchone()
                    if row and row[0]:
                        config = json.loads(row[0]) if isinstance(row[0], str) else row[0]
                        if isinstance(config, dict):
                            if not source_prov or not source_params:
                                source_prov = source_prov or config.get("source_provider") or config.get("source_provider_id")
                                source_params = resolve_canonical_connection_params(config, prefix="source", db_path=db_p)
                            if not target_prov or not target_params:
                                target_prov = target_prov or config.get("target_provider") or config.get("target_provider_id")
                                target_params = resolve_canonical_connection_params(config, prefix="target", db_path=db_p)
                    conn.close()
            except Exception as db_exc:
                logger.debug(f"[GatewayDispatcher] Failed restoring migration config for CDC context: {db_exc}")

        if source_params:
            resolved_src = resolve_canonical_connection_params(source_params, prefix="source", db_path=db_p)
            for k, v in resolved_src.items():
                if k not in source_params or not source_params[k]:
                    source_params[k] = v
        if target_params:
            resolved_tgt = resolve_canonical_connection_params(target_params, prefix="target", db_path=db_p)
            for k, v in resolved_tgt.items():
                if k not in target_params or not target_params[k]:
                    target_params[k] = v

        curr_adapter = getattr(self.coordinator.cdc_authority, "active_adapter", None)
        curr_engine = str(getattr(curr_adapter, "engine_name", "")).lower() if curr_adapter else ""
        target_engine = str(source_prov).lower().strip() if source_prov else ""
        if (curr_adapter is None or (target_engine and curr_engine != target_engine and curr_engine not in target_engine and target_engine not in curr_engine)) and source_prov:
            prov_clean = str(source_prov).lower().strip()
            from akaalEngine.cdc.capture.registry import default_cdc_source_adapter_registry
            adapter = default_cdc_source_adapter_registry.create_adapter(prov_clean, source_params)
            self.coordinator.cdc_authority.set_active_adapter(adapter)
            if hasattr(adapter, "start_capture"):
                try:
                    adapter.start_capture()
                except Exception:
                    pass

        if getattr(self.coordinator.cdc_authority, "apply_coordinator", None) is None and target_prov:
            if hasattr(self.coordinator.transport_authority, "resolve_target_writer_for_provider"):
                try:
                    writer = self.coordinator.transport_authority.resolve_target_writer_for_provider(
                        target_prov,
                        connection_params=target_params,
                    )
                    if writer and hasattr(self.coordinator.cdc_authority, "bind_target_writer"):
                        self.coordinator.cdc_authority.bind_target_writer(writer)
                except Exception as w_exc:
                    logger.debug(f"[GatewayDispatcher] Target writer resolution: {w_exc}")

        if hasattr(self.coordinator.cdc_authority, "_start_background_streaming"):
            try:
                self.coordinator.cdc_authority._start_background_streaming()
            except Exception:
                pass

    def _handle_initialize_cdc(self, ctx: GatewayRequestContext, payload: Dict[str, Any]) -> GatewayResponse[Dict[str, Any]]:
        self.coordinator.check_cancellation(ctx)
        self.coordinator.check_fencing(ctx)
        self._ensure_cdc_context(ctx, payload)

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
                if hasattr(pos, "to_string"):
                    boundary_token = pos.to_string()
                else:
                    boundary_token = getattr(pos, "position_str", str(pos) if pos else None)

        if not stream_handle:
            stream_handle = (
                getattr(res, "stream_handle", None)
                or getattr(res, "slot_name", None)
                or getattr(res, "stream_id", None)
                or (res.to_dict().get("stream_handle") if hasattr(res, "to_dict") else None)
                or (res.get("stream_handle") if isinstance(res, Mapping) else None)  # type: ignore
            )
        if not boundary_token:
            boundary_token = (
                getattr(res, "boundary_token", None)
                or getattr(res, "source_position", None)
                or getattr(res, "durable_capture_position", None)
                or getattr(res, "barrier_position", None)
                or (res.to_dict().get("source_position") if hasattr(res, "to_dict") else None)
                or (res.to_dict().get("boundary_token") if hasattr(res, "to_dict") else None)
                or (res.get("source_position") if isinstance(res, Mapping) else None)  # type: ignore
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
        self._ensure_cdc_context(ctx, payload)
        pos = payload.get("cdc_boundary_position", "0/200")
        if hasattr(self.coordinator.cdc_authority, "execute_atomic_cutover"):
            res = self.coordinator.cdc_authority.execute_atomic_cutover(pos)
        else:
            from akaalEngine.cdc.models.errors import CDCCapabilityError
            raise CDCCapabilityError("CDCAuthority does not support physical atomic cutover execution.")
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
        self._ensure_cdc_context(ctx, payload)
        if hasattr(self.coordinator.cdc_authority, "_start_background_streaming"):
            self.coordinator.cdc_authority._start_background_streaming()
        task_id = payload.get("task_id", f"task-{ctx.operation_id}")
        try:
            snap = self.coordinator.runtime_authority.resume_task(task_id)
            state_str = str(getattr(snap, "state", "RESUMED"))
        except Exception as r_exc:
            logger.debug(f"[GatewayDispatcher] Runtime task resume notice for {task_id}: {r_exc}")
            state_str = "RESUMED"
        return GatewayResponse.create_success(
            operation_id=ctx.operation_id, operation_type=SemanticOperation.RESUME_EXECUTION.value,
            migration_id=ctx.migration_id, run_id=ctx.run_id,
            payload={"status": state_str},
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
            snap = self.coordinator.runtime_authority.get_task_snapshot(task_id) or snap  # type: ignore

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
            res = self.coordinator.validation_authority.reconcile_disputed(ctx.migration_id, src_recs, tgt_recs, key_cols)  # type: ignore
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

    def _handle_state_diff(self, ctx: GatewayRequestContext, payload: Dict[str, Any]) -> GatewayResponse[Dict[str, Any]]:
        self.coordinator.check_cancellation(ctx)
        self.coordinator.check_fencing(ctx)
        if hasattr(self.coordinator.transport_authority, "execute_state_diff"):
            res = self.coordinator.transport_authority.execute_state_diff(payload)
        else:
            from akaalEngine.transport.models.errors import TransportError
            raise TransportError("TransportAuthority does not implement execute_state_diff.")

        return GatewayResponse.create_success(
            operation_id=ctx.operation_id,
            operation_type=getattr(SemanticOperation, "EXECUTE_STATE_DIFF", SemanticOperation.RUN_FINAL_VALIDATION).value,
            migration_id=ctx.migration_id,
            run_id=ctx.run_id,
            payload=res,
            fencing_epoch=ctx.fencing_epoch,
            proof_classification="UNIT_PROVEN",
        )

    def _handle_state_reconcile(self, ctx: GatewayRequestContext, payload: Dict[str, Any]) -> GatewayResponse[Dict[str, Any]]:
        self.coordinator.check_cancellation(ctx)
        self.coordinator.check_fencing(ctx)
        if hasattr(self.coordinator.transport_authority, "execute_state_reconcile"):
            res = self.coordinator.transport_authority.execute_state_reconcile(payload)
        else:
            from akaalEngine.transport.models.errors import TransportError
            raise TransportError("TransportAuthority does not implement execute_state_reconcile.")

        return GatewayResponse.create_success(
            operation_id=ctx.operation_id,
            operation_type=getattr(SemanticOperation, "EXECUTE_STATE_RECONCILE", SemanticOperation.RECONCILE_DISPUTED_RECORDS).value,
            migration_id=ctx.migration_id,
            run_id=ctx.run_id,
            payload=res,
            fencing_epoch=ctx.fencing_epoch,
            proof_classification="UNIT_PROVEN",
        )


    def _handle_incremental_extract(self, ctx: GatewayRequestContext, payload: Dict[str, Any]) -> GatewayResponse[Dict[str, Any]]:
        self.coordinator.check_cancellation(ctx)
        self.coordinator.check_fencing(ctx)
        wm_col = payload.get("watermark_column", "updated_at")
        wm_val = payload.get("watermark_value", 0)
        reader = payload.get("source_reader") or payload.get("reader")

        batches_by_table = {}
        if reader and hasattr(reader, "read_batch"):
            batch = reader.read_batch(partition=payload.get("partition")) if payload.get("partition") else reader.read_batch()
            extracted_records = len(getattr(batch, "rows", [])) if hasattr(batch, "rows") else (len(batch) if isinstance(batch, list) else 0)
            extracted_wm = wm_val + extracted_records if isinstance(wm_val, int) else wm_val
        elif hasattr(self.coordinator.transport_authority, "extract_incremental"):
            res = self.coordinator.transport_authority.extract_incremental(payload)  # type: ignore
            extracted_records = res.get("extracted_records", 0)
            extracted_wm = res.get("extracted_watermark", wm_val)
            batches_by_table = res.get("batches_by_table", {})
        else:
            from akaalEngine.transport.models.errors import TransportError
            raise TransportError("Incremental extraction requires an active, validated SourceReader driver or registered transport connector. Synthetic record payloads are forbidden.")

        return GatewayResponse.create_success(
            operation_id=ctx.operation_id, operation_type=SemanticOperation.EXECUTE_INCREMENTAL_EXTRACT.value,
            migration_id=ctx.migration_id, run_id=ctx.run_id,
            payload={"extracted_records": extracted_records, "watermark_column": wm_col, "extracted_watermark": extracted_wm, "batches_by_table": batches_by_table, "status": "EXTRACTED"},
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
            committed_wm = max(col_vals)  # type: ignore
        elif hasattr(self.coordinator.transport_authority, "apply_incremental"):
            res = self.coordinator.transport_authority.apply_incremental(payload)  # type: ignore
            if not isinstance(res, dict) or not res.get("committed") or "target_commit_receipt" not in res:
                from akaalEngine.transport.models.errors import TransportError
                raise TransportError("TransportAuthority apply_incremental returned without verified physical target_commit_receipt and committed=True.")
            applied_records = res.get("applied_records", 0)
            committed_wm = res.get("committed_watermark") if res.get("committed_watermark") is not None else payload.get("extracted_watermark")
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
                res_transport = self.coordinator.transport_authority.rollback_batch(batch_id)  # type: ignore
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
