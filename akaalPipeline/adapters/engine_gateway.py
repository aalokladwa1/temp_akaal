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
    "state_diff": SemanticOperation.RUN_FINAL_VALIDATION,
    "state_reconcile": SemanticOperation.RECONCILE_DISPUTED_RECORDS,
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
        tenant_id = payload.get("tenant_id") or payload.get("organization_id")
        workspace_id = payload.get("workspace_id")
        project_id = payload.get("project_id")
        fencing_epoch = req.fence_epoch

        if not mig_id or not run_id or not job_id:
            raise PipelineError(
                PipelineErrorCode.INVALID_REQUEST,
                f"Missing required execution identity context: migration_id={mig_id!r}, run_id={run_id!r}, job_id={job_id!r}.",
            )

        return GatewayRequestContext(
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
            execution_mode=payload.get("execution_mode") or payload.get("mode"),
            deadline_seconds=float(req.timeout_seconds) if req.timeout_seconds else None,
        )

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
            retryable=resp.retryable,
            terminal=resp.terminal,
            is_in_progress=not resp.terminal and resp.success,
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

        gw_req = GatewayRequest(
            operation=op,
            context=ctx,
            payload=payload,
        )
        resp = self.gateway.execute(gw_req)
        return self._map_response(request, resp)

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
        valid_prefixes = ("vault:", "secret:", "env:", "kms:")
        if any(secret_ref.startswith(prefix) for prefix in valid_prefixes):
            return secret_ref

        raise PipelineError(
            PipelineErrorCode.INVALID_REQUEST,
            f"Plaintext credentials rejected; must use valid secret reference syntax ('vault:...', 'secret:...', 'env:...', 'kms:...').",
        )
