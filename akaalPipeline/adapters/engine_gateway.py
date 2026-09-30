"""akaalPipeline.adapters.engine_gateway
======================================
Canonical thin adapter implementing akaalPipeline.ports.engine protocols
by delegating to EngineGateway (single entry point for Authorities #1-#12).
"""

from __future__ import annotations

import logging
from typing import Any, Mapping, Optional

from akaalEngine.gateway.api import EngineGateway, default_engine_gateway
from akaalEngine.gateway.models.context import GatewayRequestContext
from akaalEngine.gateway.models.enums import SemanticOperation
from akaalEngine.gateway.models.requests import GatewayRequest
from akaalEngine.gateway.models.responses import GatewayResponse
from akaalEngine.transport.drivers.registry import normalize_provider_id
from akaalPipeline.contracts.errors import PipelineError, PipelineErrorCode
from akaalPipeline.ports.engine import (
    AssessmentPort,
    CapabilityProbePort,
    CapabilityProbeResult,
    CheckpointPort,
    DiscoveryPort,
    EngineInvocationRequest,
    EngineInvocationResult,
    EventPort,
    ExecutionPort,
    PlanningPort,
    RecoveryPort,
    ResourcePort,
    SecretResolutionPort,
    ValidationPort,
)

logger = logging.getLogger("akaalPipeline.adapters.engine_gateway")


CAPABILITY_SEMANTIC_MAP: Mapping[str, SemanticOperation] = {
    "schema_prep": SemanticOperation.PREPARE_MIGRATION_EXECUTION,
    "schema_extract": SemanticOperation.DISCOVER_CATALOG,
    "schema_compile": SemanticOperation.COMPILE_SCHEMA_MAPPING,
    "schema_apply": SemanticOperation.APPLY_SCHEMA_CHANGES,
    "data_transport": SemanticOperation.EXECUTE_BULK_MIGRATION,
    "cdc_capture": SemanticOperation.INITIALIZE_CDC_STREAM,
    "cdc_apply": SemanticOperation.EXECUTE_CDC_SYNC,
    "cdc_sync": SemanticOperation.EXECUTE_CDC_SYNC,
    "incremental_extract": SemanticOperation.EXECUTE_INCREMENTAL_EXTRACT,
    "inc_extract": SemanticOperation.EXECUTE_INCREMENTAL_EXTRACT,
    "incremental_apply": SemanticOperation.EXECUTE_INCREMENTAL_APPLY,
    "inc_apply": SemanticOperation.EXECUTE_INCREMENTAL_APPLY,
    "state_diff": SemanticOperation.EXECUTE_STATE_DIFF,
    "state_reconcile": SemanticOperation.EXECUTE_STATE_RECONCILE,
    "reconcile_disputed": SemanticOperation.RECONCILE_DISPUTED_RECORDS,
    "validation_governed_repair": SemanticOperation.RECONCILE_DISPUTED_RECORDS,
    "governed_repair": SemanticOperation.RECONCILE_DISPUTED_RECORDS,
    "governed_repair_revalidation": SemanticOperation.RUN_FINAL_VALIDATION,
    "targeted_revalidation": SemanticOperation.RUN_FINAL_VALIDATION,
    "validation_compare": SemanticOperation.RUN_FINAL_VALIDATION,
    "val_compare": SemanticOperation.RUN_FINAL_VALIDATION,
    "package_evidence": SemanticOperation.PACKAGE_MACHINE_EVIDENCE,
    "verify_evidence": SemanticOperation.VERIFY_EVIDENCE_INTEGRITY,
}


class PipelineEngineGatewayAdapter(
    CapabilityProbePort,
    DiscoveryPort,
    AssessmentPort,
    PlanningPort,
    ExecutionPort,
    CheckpointPort,
    RecoveryPort,
    ValidationPort,
    ResourcePort,
    EventPort,
    SecretResolutionPort,
):
    """Canonical Thin Adapter routing akaalPipeline port protocols to EngineGateway."""

    def __init__(self, gateway: Optional[EngineGateway] = None, owns_gateway: Optional[bool] = None) -> None:
        if gateway is None:
            self.gateway = default_engine_gateway()
            self._owns_gateway = True if owns_gateway is None else owns_gateway
        else:
            self.gateway = gateway
            self._owns_gateway = False if owns_gateway is None else owns_gateway

    def close(self) -> None:
        """Closes owned EngineGateway resources cleanly."""
        if self._owns_gateway and self.gateway and hasattr(self.gateway, "coordinator"):
            coord = self.gateway.coordinator
            if hasattr(coord, "runtime_authority") and hasattr(coord.runtime_authority, "shutdown"):
                try:
                    coord.runtime_authority.shutdown()
                except Exception as exc:
                    logger.warning("Failed shutting down RuntimeAuthority during adapter close: %s", exc)
            if hasattr(coord, "durability_authority") and hasattr(coord.durability_authority, "close"):
                try:
                    coord.durability_authority.close()
                except Exception as exc:
                    logger.warning("Failed closing DurabilityAuthority during adapter close: %s", exc)

    def _build_context(self, req: EngineInvocationRequest) -> GatewayRequestContext:
        payload = dict(req.payload or {})
        mig_id = payload.get("migration_id") or req.payload.get("migration_id")
        run_id = req.attempt_id or payload.get("run_id") or payload.get("attempt_id")
        job_id = req.graph_node_id or req.checkpoint_id or payload.get("job_id") or payload.get("batch_id")
        # P7.10/P7.13: tenant/workspace/project scope MUST come from the trusted
        # EngineInvocationRequest fields (set by the Pipeline caller from its own
        # already-verified PipelineActorContext), never from `payload` -- payload
        # may echo untrusted caller-supplied request fields (e.g. a wire envelope's
        # own payload dict), and trusting a "tenant_id"/"organization_id" key found
        # there would let a caller influence the security-context an Engine
        # operation executes/is tagged under merely by including that key.
        tenant_id = req.tenant_id
        workspace_id = req.workspace_id
        project_id = req.project_id
        fencing_epoch = req.fence_epoch

        if not mig_id or not run_id or not job_id:
            raise PipelineError(
                PipelineErrorCode.INVALID_REQUEST,
                f"Missing required execution identity context: migration_id={mig_id!r}, run_id={run_id!r}, job_id={job_id!r}.",
            )

        authz_art = payload.get("execution_authorization_artifact") or getattr(req, "execution_authorization_artifact", None)

        ctx = GatewayRequestContext(
            migration_id=mig_id,
            run_id=run_id,
            job_id=job_id,
            tenant_id=tenant_id,
            workspace_id=workspace_id,
            project_id=project_id,
            operation_id=req.operation_id or f"op-{req.invocation_id}",
            fencing_epoch=fencing_epoch,
            fencing_token_envelope=req.fencing_token_envelope,
            initialization_fingerprint=req.initialization_fingerprint,
            execution_authorization_artifact=authz_art,
            execution_mode=payload.get("execution_mode") or payload.get("mode"),
            deadline_seconds=float(req.timeout_seconds) if req.timeout_seconds else None,
        )

        if ctx.fencing_token_envelope is None and hasattr(self, "gateway") and self.gateway is not None:
            try:
                fence_gw_req = GatewayRequest(
                    operation=SemanticOperation.ACQUIRE_EXECUTION_FENCE,
                    context=ctx,
                    payload={"worker_id": "pipeline_engine_adapter"},
                )
                fence_resp = self.gateway.execute(fence_gw_req)
                if fence_resp.success and isinstance(fence_resp.payload, dict) and "fencing_token_envelope" in fence_resp.payload:
                    ctx.fencing_token_envelope = fence_resp.payload["fencing_token_envelope"]
                    if isinstance(ctx.fencing_token_envelope, dict) and ctx.fencing_token_envelope.get("fencing_epoch"):
                        ctx.fencing_epoch = ctx.fencing_token_envelope["fencing_epoch"]
            except Exception as fence_exc:
                logger.debug("Automatic execution fence acquisition skipped or failed: %s", fence_exc)

        return ctx

    def _map_response(self, req: EngineInvocationRequest, resp: GatewayResponse) -> EngineInvocationResult:
        err_code = resp.failure_category or resp.status_code
        err_msg = resp.error_message or ("; ".join(resp.reasons) if resp.reasons else (None if resp.success else "Gateway operation failed"))

        payload = dict(resp.payload) if isinstance(resp.payload, dict) else ({"result": resp.payload} if resp.payload is not None else {})
        if resp.proof_classification:
            payload["proof_classification"] = resp.proof_classification

        if resp.execution_receipt:
            payload["engine_execution_receipt"] = dict(resp.execution_receipt)

        return EngineInvocationResult(
            invocation_id=req.invocation_id,
            attempt_id=req.attempt_id,
            lease_id=req.lease_id,
            fence_epoch=req.fence_epoch,
            is_success=resp.success,
            initialization_fingerprint=req.initialization_fingerprint,
            graph_node_id=req.graph_node_id,
            binding_id=req.binding_id,
            contract_version=req.contract_version,
            result_payload=payload,
            error_code=err_code if not resp.success else None,
            error_message=err_msg,
            terminal=getattr(resp, "terminal", True) if resp.success else False,
            is_in_progress=bool(getattr(resp, "in_progress", False)),
        )

    # -------------------------------------------------------------------------
    # Protocol Implementations
    # -------------------------------------------------------------------------

    def probe_capability(self, provider_id: str, capability_id: str) -> CapabilityProbeResult:
        ctx = GatewayRequestContext(migration_id="probe-mig", run_id="probe-run", job_id="probe-job", fencing_epoch=1)
        gw_req = GatewayRequest(
            operation=SemanticOperation.RESOLVE_CAPABILITIES,
            context=ctx,
            payload={"provider_id": provider_id, "required_capabilities": [capability_id]},
        )
        try:
            resp = self.gateway.execute(gw_req)
            if not resp.success or not resp.payload:
                return CapabilityProbeResult(
                    provider_id=provider_id, capability_id=capability_id, supported=False, is_healthy=False, reasons=tuple(resp.reasons or ["Unresolved"])
                )
            if isinstance(resp.payload, dict):
                sup = resp.payload.get("supported") is True
                return CapabilityProbeResult(
                    provider_id=provider_id,
                    capability_id=capability_id,
                    supported=sup,
                    is_healthy=sup and resp.success,
                    proof_classification=resp.proof_classification,
                    reasons=tuple(resp.reasons),
                )
            return CapabilityProbeResult(provider_id=provider_id, capability_id=capability_id, supported=False, is_healthy=False)
        except Exception as exc:
            logger.warning("Capability probe failed for %s/%s: %s", provider_id, capability_id, exc)
            return CapabilityProbeResult(provider_id=provider_id, capability_id=capability_id, supported=False, is_healthy=False, reasons=(str(exc),))

    def discover_schema(self, request: EngineInvocationRequest) -> EngineInvocationResult:
        ctx = self._build_context(request)
        payload = dict(request.payload or {})
        gw_req = GatewayRequest(
            operation=SemanticOperation.DISCOVER_CATALOG,
            context=ctx,
            payload={
                "endpoint_spec": payload.get("endpoint_spec", payload),
                "auth_spec": payload.get("auth_spec", {}),
                "depth": payload.get("depth", "FULL"),
                "scope_schemas": payload.get("scope_schemas", []),
            },
        )
        resp = self.gateway.execute(gw_req)
        return self._map_response(request, resp)

    def assess_migration(self, request: EngineInvocationRequest) -> EngineInvocationResult:
        ctx = self._build_context(request)
        payload = dict(request.payload or {})
        gw_req = GatewayRequest(
            operation=SemanticOperation.VALIDATE_SCHEMA_COMPATIBILITY,
            context=ctx,
            payload=payload,
        )
        resp = self.gateway.execute(gw_req)
        return self._map_response(request, resp)

    def generate_plan(self, request: EngineInvocationRequest) -> EngineInvocationResult:
        ctx = self._build_context(request)
        payload = dict(request.payload or {})
        gw_req = GatewayRequest(
            operation=SemanticOperation.COMPILE_SCHEMA_MAPPING,
            context=ctx,
            payload={
                "source_discovery_snapshot": payload.get("source_discovery_snapshot", payload),
                "target_dialect": payload.get("target_dialect", "postgres"),
                "type_overrides": payload.get("type_overrides", {}),
            },
        )
        resp = self.gateway.execute(gw_req)
        return self._map_response(request, resp)

    def execute_task(self, request: EngineInvocationRequest) -> EngineInvocationResult:
        ctx = self._build_context(request)
        payload = dict(request.payload or {})
        op_str = payload.get("semantic_operation") or payload.get("operation")

        op: Optional[SemanticOperation] = None
        if op_str and hasattr(SemanticOperation, str(op_str)):
            op = SemanticOperation(op_str)
        else:
            raw_target = str(payload.get("capability_contract") or payload.get("capability_id") or request.graph_node_id or "")
            target_clean = raw_target
            if target_clean.startswith("n-") or target_clean.startswith("t-"):
                target_clean = target_clean[2:]
            norm_target = target_clean.replace("-", "_")

            for k, v in CAPABILITY_SEMANTIC_MAP.items():
                if k == norm_target or k in norm_target:
                    op = v
                    break

        if op is None:
            return EngineInvocationResult(
                invocation_id=request.invocation_id,
                attempt_id=request.attempt_id,
                lease_id=request.lease_id,
                fence_epoch=request.fence_epoch,
                is_success=False,
                initialization_fingerprint=request.initialization_fingerprint,
                graph_node_id=request.graph_node_id,
                binding_id=request.binding_id,
                contract_version=request.contract_version,
                error_code="UNSUPPORTED_CAPABILITY",
                error_message=f"No explicit Gateway SemanticOperation mapping for capability/task intent '{request.graph_node_id}'. Implicit bulk fallback is forbidden.",
                retryable=False,
                terminal=True,
            )

        if op in (
            SemanticOperation.EXECUTE_BULK_MIGRATION,
            SemanticOperation.PREPARE_MIGRATION_EXECUTION,
            SemanticOperation.APPLY_SCHEMA_CHANGES,
            SemanticOperation.COMPILE_SCHEMA_MAPPING,
            SemanticOperation.DISCOVER_CATALOG,
            SemanticOperation.INITIALIZE_CDC_STREAM,
            SemanticOperation.EXECUTE_CDC_SYNC,
            SemanticOperation.EVALUATE_CUTOVER_READINESS,
            SemanticOperation.EXECUTE_ATOMIC_CUTOVER,
            SemanticOperation.RUN_FINAL_VALIDATION,
        ):
            self._enrich_bulk_payload(ctx, payload)

        gw_req = GatewayRequest(
            operation=op,
            context=ctx,
            payload=payload,
        )
        resp = self.gateway.execute(gw_req)
        return self._map_response(request, resp)

    def _enrich_bulk_payload(self, ctx: GatewayRequestContext, payload: dict) -> None:
        """Dynamically resolves source/target connection parameters and selected tables from migration state and connection vault."""
        import json
        import os
        import sqlite3

        db_path = getattr(self, "db_path", None) or os.environ.get("AKAAL_PIPELINE_DB_PATH") or os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "akaal-pipeline.db"))
        if not db_path or not os.path.exists(db_path):
            return

        mig_id = ctx.migration_id or payload.get("migration_id")
        mig_config = {}

        try:
            conn = sqlite3.connect(db_path, timeout=10.0)
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()

            if mig_id:
                cur.execute("SELECT configuration FROM migrations WHERE migration_id = ?", (mig_id,))
                row = cur.fetchone()
                if row and row["configuration"]:
                    try:
                        mig_config = json.loads(row["configuration"])
                    except Exception:
                        mig_config = {}

            # 1. Resolve Tables
            if not payload.get("tables") and not payload.get("selected_tables") and not payload.get("selectedTopologyNodes"):
                tables = mig_config.get("selectedTopologyNodes") or payload.get("selectedTopologyNodes")
                if tables:
                    payload["tables"] = tables

            # 2. Resolve Source Connection
            source_conn_id = payload.get("source_connection_id") or mig_config.get("source_connection_id")
            if not payload.get("source_reader") or not payload.get("source_connection_params"):
                if source_conn_id:
                    cur.execute("SELECT provider_id, configuration FROM enterprise_connections WHERE connection_id = ?", (source_conn_id,))
                    s_row = cur.fetchone()
                    if s_row:
                        prov = normalize_provider_id(s_row["provider_id"] or "mysql")
                        s_cfg = json.loads(s_row["configuration"] or "{}")
                        payload["source_provider_id"] = prov
                        payload["source_connection_params"] = s_cfg
                        if not payload.get("source_schema") and s_cfg.get("database"):
                            payload["source_schema"] = s_cfg["database"]
                        elif not payload.get("source_schema") and s_cfg.get("username"):
                            payload["source_schema"] = s_cfg["username"]
                elif mig_config.get("sourceHost") or mig_config.get("source_host") or mig_config.get("source_provider") or mig_config.get("sourceProvider"):
                    raw_prov = str(mig_config.get("sourceProvider") or mig_config.get("source_provider") or "mysql")
                    prov = normalize_provider_id(raw_prov)
                    payload["source_provider_id"] = prov
                    s_params = dict(mig_config.get("source_connection_params") or {})
                    if not s_params:
                        s_host = mig_config.get("sourceHost") or mig_config.get("source_host") or "localhost"
                        s_port_raw = mig_config.get("sourcePort") or mig_config.get("source_port")
                        s_user = mig_config.get("sourceUsername") or mig_config.get("source_username") or mig_config.get("sourceUser")
                        s_secret_raw = mig_config.get("sourceSecretRef") or mig_config.get("source_secret_ref") or mig_config.get("sourcePassword") or mig_config.get("source_password")
                        s_pass = self.resolve_secret_reference(s_secret_raw) if s_secret_raw else ""
                        s_db = mig_config.get("sourceDatabase") or mig_config.get("source_database") or ""
                        s_sch = mig_config.get("sourceSchema") or mig_config.get("source_schema") or s_db
                        s_params = {
                            "host": s_host,
                            "port": int(s_port_raw) if s_port_raw else (3306 if "mysql" in prov else (5432 if "postgres" in prov else 1521)),
                            "database": s_db,
                            "username": s_user,
                            "user": s_user,
                            "password": s_pass,
                            "secret_ref": s_secret_raw or s_pass,
                            "schema": s_sch,
                        }
                    payload["source_connection_params"] = s_params

            # 3. Resolve Target Connection
            if not payload.get("target_writer") or not payload.get("target_connection_params"):
                target_conn_id = payload.get("target_connection_id") or mig_config.get("target_connection_id")
                if target_conn_id:
                    cur.execute("SELECT provider_id, configuration FROM enterprise_connections WHERE connection_id = ?", (target_conn_id,))
                    t_row = cur.fetchone()
                    if t_row:
                        prov = normalize_provider_id(t_row["provider_id"] or "oracle")
                        payload["target_provider_id"] = prov
                        payload["target_connection_params"] = json.loads(t_row["configuration"] or "{}")
                elif mig_config.get("targetHost") or mig_config.get("target_host") or mig_config.get("target_provider") or mig_config.get("targetProvider") or payload.get("target_provider_id") or payload.get("target_provider"):
                    raw_prov = str(mig_config.get("targetProvider") or mig_config.get("target_provider") or payload.get("target_provider_id") or payload.get("target_provider") or "oracle")
                    prov = normalize_provider_id(raw_prov)
                    payload["target_provider_id"] = prov
                    t_params = dict(mig_config.get("target_connection_params") or {})
                    if not t_params:
                        t_host = mig_config.get("targetHost") or mig_config.get("target_host") or "localhost"
                        t_port_raw = mig_config.get("targetPort") or mig_config.get("target_port")
                        t_user = mig_config.get("targetUsername") or mig_config.get("target_username") or mig_config.get("targetUser")
                        t_secret_raw = mig_config.get("targetSecretRef") or mig_config.get("target_secret_ref") or mig_config.get("targetPassword") or mig_config.get("target_password")
                        t_pass = self.resolve_secret_reference(t_secret_raw) if t_secret_raw else ""
                        t_db = mig_config.get("targetDatabase") or mig_config.get("target_database") or mig_config.get("targetServiceName") or mig_config.get("target_service_name") or ""
                        t_sch = mig_config.get("targetSchema") or mig_config.get("target_schema") or t_user or "public"

                        t_params = {
                            "host": t_host,
                            "port": int(t_port_raw) if t_port_raw else (1521 if "oracle" in prov else (5432 if "postgres" in prov else (3306 if "mysql" in prov else 1433))),
                            "service_name": mig_config.get("targetServiceName") or mig_config.get("target_service_name") or t_db,
                            "database": t_db,
                            "username": t_user,
                            "user": t_user,
                            "password": t_pass,
                            "secret_ref": t_secret_raw or t_pass,
                            "schema": t_sch,
                        }
                    payload["target_connection_params"] = t_params
                else:
                    # Look up active target connection from vault, excluding source connection
                    if source_conn_id:
                        cur.execute("SELECT provider_id, configuration FROM enterprise_connections WHERE connection_id != ? AND role_applicability IN ('TARGET', 'SOURCE_AND_TARGET') ORDER BY updated_at DESC LIMIT 1", (source_conn_id,))
                    else:
                        cur.execute("SELECT provider_id, configuration FROM enterprise_connections WHERE role_applicability IN ('TARGET', 'SOURCE_AND_TARGET') ORDER BY updated_at DESC LIMIT 1")
                    t_row = cur.fetchone()
                    if t_row:
                        prov = normalize_provider_id(t_row["provider_id"] or "oracle")
                        payload["target_provider_id"] = prov
                        payload["target_connection_params"] = json.loads(t_row["configuration"] or "{}")

            if payload.get("target_connection_params") and not payload.get("target_schema"):
                payload["target_schema"] = (
                    payload["target_connection_params"].get("schema")
                    or payload["target_connection_params"].get("username")
                    or payload["target_connection_params"].get("user")
                )

            conn.close()
        except Exception as exc:
            logger.warning("Could not enrich bulk transport payload from database: %s", exc)

    def verify_checkpoint(self, request: EngineInvocationRequest) -> EngineInvocationResult:
        ctx = self._build_context(request)
        payload = dict(request.payload or {})
        gw_req = GatewayRequest(
            operation=SemanticOperation.VERIFY_CHECKPOINT,
            context=ctx,
            payload={"checkpoint_id": request.checkpoint_id or request.graph_node_id or payload.get("checkpoint_id") or payload.get("batch_id") or ctx.job_id},
        )
        resp = self.gateway.execute(gw_req)
        return self._map_response(request, resp)

    def trigger_checkpoint(self, request: EngineInvocationRequest) -> EngineInvocationResult:
        ctx = self._build_context(request)
        payload = dict(request.payload or {})
        gw_req = GatewayRequest(
            operation=SemanticOperation.TRIGGER_CHECKPOINT,
            context=ctx,
            payload={"checkpoint_id": request.checkpoint_id or request.graph_node_id or payload.get("checkpoint_id") or payload.get("batch_id") or ctx.job_id},
        )
        resp = self.gateway.execute(gw_req)
        return self._map_response(request, resp)

    def perform_recovery_action(self, request: EngineInvocationRequest) -> EngineInvocationResult:
        ctx = self._build_context(request)
        payload = dict(request.payload or {})
        gw_req = GatewayRequest(
            operation=SemanticOperation.RECOVER_FROM_CHECKPOINT,
            context=ctx,
            payload={"checkpoint_id": request.checkpoint_id or request.graph_node_id or payload.get("checkpoint_id") or payload.get("batch_id") or ctx.job_id},
        )
        resp = self.gateway.execute(gw_req)
        return self._map_response(request, resp)

    def validate_data(self, request: EngineInvocationRequest) -> EngineInvocationResult:
        ctx = self._build_context(request)
        payload = dict(request.payload or {})
        gw_req = GatewayRequest(
            operation=SemanticOperation.RUN_FINAL_VALIDATION,
            context=ctx,
            payload=payload,
        )
        resp = self.gateway.execute(gw_req)
        return self._map_response(request, resp)

    def evaluate_resource_readiness(self, request: EngineInvocationRequest) -> EngineInvocationResult:
        ctx = self._build_context(request)
        payload = dict(request.payload or {})
        gw_req = GatewayRequest(
            operation=SemanticOperation.TEST_CONNECTION,
            context=ctx,
            payload=payload,
        )
        resp = self.gateway.execute(gw_req)
        return self._map_response(request, resp)

    def publish_engine_event(self, event_data: Mapping[str, Any]) -> None:
        if hasattr(self.gateway, "coordinator") and hasattr(self.gateway.coordinator, "telemetry_authority"):
            try:
                self.gateway.coordinator.telemetry_authority.record_event(dict(event_data))
            except Exception as exc:
                logger.warning("Failed recording engine telemetry event: %s", exc)

    def resolve_secret_reference(self, secret_ref: str) -> str:
        if not secret_ref:
            return ""
        str_ref = str(secret_ref)
        if str_ref.startswith("env:"):
            var_name = str_ref[4:]
            val = os.getenv(var_name)
            return val if val is not None else str_ref
        elif str_ref.startswith("vault:"):
            var_name = str_ref[6:]
            val = os.getenv(var_name) or os.getenv(f"VAULT_SECRET_{var_name.upper().replace('/', '_')}")
            return val if val is not None else str_ref
        return str_ref
