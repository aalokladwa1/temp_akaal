"""
akaalPipeline.adapters.fabric_engine_gateway
================================================
The ONE new `akaalPipeline.ports.engine.ExecutionPort` implementation this Group-2
Pipeline integration adds. It is a THIN, GATING WRAPPER, not a new executor:

  * For every capability, it first re-verifies the bound `FabricPlacementBinding` is
    still fresh/valid (reusing `akaalEngine.fabric.placement.binding.PlacementDecision.
    is_stale` and `akaalEngine.fabric.placement.execution.worker_still_valid` -- the
    EXACT same checks `execute_via_placement`'s composed `live_trust_check` already
    performs, never a second revalidation scheme).
  * For the `data_transport` capability (the one Pipeline capability that performs real
    physical bulk data movement, per `akaalPipeline.adapters.engine_gateway.
    CAPABILITY_SEMANTIC_MAP`), it builds real reader/writer/partition objects via
    `akaalEngine.transport.api.TransportAuthority`'s OWN existing provider-resolution
    methods (`resolve_source_reader_for_provider`/`resolve_target_writer_for_provider`
    -- never reinvented) and routes physical execution through
    `akaalEngine.fabric.placement.execution.execute_via_placement` -- the exact function
    this repository's Group-2 hostile-tested production wiring already proves closes
    every named bypass class.
  * For every OTHER capability (schema_prep, cdc_capture, validation_compare, etc.), it
    delegates unchanged to the existing, real `akaalPipeline.adapters.engine_gateway.
    PipelineEngineGatewayAdapter` -- those are not raw TransportAuthority-shaped
    physical-partition operations and forcing them through `execute_via_placement`'s
    reader/writer/partition contract would be architecturally wrong, not "more secure".
    The Group-2 gate (placement/worker/topology validity) still applies to them, exactly
    like the `data_transport` path -- they simply don't ALSO get re-routed through
    TransportAuthority, because that mechanism does not describe what they do.

NO NEW AUTHORITY: this class has no independent transport, checkpoint, retry, CDC,
validation, authorization, or migration-lifecycle logic of its own. It is a single
`ExecutionPort` adapter -- exactly the shape `PipelineEngineGatewayAdapter` already
establishes -- composed with Group-2's existing, unmodified `execute_via_placement`.
"""

from __future__ import annotations

import logging
from typing import Any, Callable, Mapping, Optional

from akaalEngine.gateway.models.responses import sign_receipt
from akaalEngine.fabric.placement.execution import (
    PlacementExecutionError,
    worker_still_valid,
    execute_via_placement,
)
from akaalEngine.fabric.remote_execution.control_plane import RemoteExecutionControlPlane
from akaalEngine.fabric.worker_fabric.registry import WorkerRegistry
from akaalEngine.transport.models.spec import PartitionStrategy, TransportPartition
from akaalPipeline.adapters.engine_gateway import PipelineEngineGatewayAdapter
from akaalPipeline.contracts.errors import PipelineError, PipelineErrorCode
from akaalPipeline.orchestration.fabric_gate import FabricPlacementBindingStore, is_binding_stale
from akaalPipeline.ports.engine import EngineInvocationRequest, EngineInvocationResult, ExecutionPort

logger = logging.getLogger("akaalPipeline.adapters.fabric_engine_gateway")

_PHYSICAL_DATA_MOVEMENT_CAPABILITY = "data_transport"


class FabricPlacementExecutionPort(ExecutionPort):
    def __init__(
        self,
        *,
        binding_store: FabricPlacementBindingStore,
        topology_provider: Callable[[str], Any],
        worker_registry: WorkerRegistry,
        control_plane: RemoteExecutionControlPlane,
        site_authorization_callback: Any,
        signing_key: bytes,
        transport_authority_factory: Callable[[], Any],
        delegate: Optional[PipelineEngineGatewayAdapter] = None,
        ownership_manager: Optional[Any] = None,
        evidence_authority: Optional[Any] = None,
        telemetry_authority: Optional[Any] = None,
    ) -> None:
        self._binding_store = binding_store
        self._topology_provider = topology_provider
        self._worker_registry = worker_registry
        self._control_plane = control_plane
        self._site_authorization_callback = site_authorization_callback
        self._signing_key = signing_key
        self._transport_authority_factory = transport_authority_factory
        self._delegate = delegate or PipelineEngineGatewayAdapter()
        # P7B Group-3 (P7B.25) -- see akaalPipeline.orchestration.fabric_gate.
        # FabricGateDependencies.ownership_manager for the mandatory-when-applicable
        # discipline; this adapter merely threads whatever it was constructed with
        # through to execute_via_placement unchanged, never substituting its own default.
        self._ownership_manager = ownership_manager
        # P7B.34 -- optional, purely additive (Evidence != authorization).
        self._evidence_authority = evidence_authority
        # P7B.32 -- optional, purely additive (Telemetry != execution truth).
        self._telemetry_authority = telemetry_authority

    def _require_valid_binding(self, execution_id: str):
        binding = self._binding_store.require(execution_id)
        current_topology = self._topology_provider(binding.decision.tenant_id)
        if is_binding_stale(binding, current_topology):
            raise PipelineError(
                PipelineErrorCode.POLICY_DENIED,
                f"Fabric placement decision {binding.decision.decision_id!r} for execution "
                f"{execution_id!r} is stale (expired or topology drifted since placement); "
                f"refusing dispatch. A fresh placement cycle is required.",
            )
        if not worker_still_valid(self._worker_registry, binding.worker):
            raise PipelineError(
                PipelineErrorCode.POLICY_DENIED,
                f"Bound worker {binding.worker.worker_id!r} for execution {execution_id!r} "
                f"is no longer valid (revoked/unhealthy/stale/replaced); refusing dispatch.",
            )
        return binding

    def execute_task(self, request: EngineInvocationRequest) -> EngineInvocationResult:
        payload = request.payload or {}
        execution_id = payload.get("execution_id")
        if not execution_id:
            raise PipelineError(
                PipelineErrorCode.INVALID_REQUEST,
                "FabricPlacementExecutionPort requires payload['execution_id'] to look up "
                "the bound Group-2 PlacementDecision; none was supplied.",
            )

        binding = self._require_valid_binding(execution_id)

        capability = payload.get("capability_contract") or payload.get("capability_id")
        if capability != _PHYSICAL_DATA_MOVEMENT_CAPABILITY:
            # Non-physical-movement capability in a fabric-required plan: Group-2's gate
            # already ran above; delegate the actual (schema/CDC-control) work to the
            # existing, unmodified gateway adapter.
            return self._delegate.execute_task(request)

        fabric_cfg = payload.get("configuration", {}).get("fabric_placement", {}) if isinstance(payload.get("configuration"), Mapping) else {}
        source_provider = fabric_cfg.get("source_provider")
        target_provider = fabric_cfg.get("target_provider")
        if not source_provider or not target_provider:
            raise PipelineError(
                PipelineErrorCode.INVALID_REQUEST,
                "fabric_placement configuration must declare source_provider and "
                "target_provider for the data_transport capability.",
            )

        transport_authority = self._transport_authority_factory()
        reader = transport_authority.resolve_source_reader_for_provider(
            source_provider, **fabric_cfg.get("source_params", {})
        )
        writer = transport_authority.resolve_target_writer_for_provider(
            target_provider, **fabric_cfg.get("target_params", {})
        )
        partition = TransportPartition(
            partition_id=request.graph_node_id,
            table_name=fabric_cfg.get("table_name", payload.get("migration_id", "unknown")),
            schema_name=source_provider,
            target_schema=target_provider,
            strategy=list(PartitionStrategy)[0],
        )

        try:
            rows_written = execute_via_placement(
                decision=binding.decision, site=binding.site, worker=binding.worker,
                control_plane=self._control_plane, worker_registry=self._worker_registry,
                transport_authority=transport_authority, signing_key=self._signing_key,
                site_authorization_callback=self._site_authorization_callback,
                reader=reader, writer=writer, partition=partition,
                current_topology_provider=lambda: self._topology_provider(binding.decision.tenant_id),
                run_id=request.attempt_id,
                ownership_manager=self._ownership_manager,
                execution_id=execution_id,
                evidence_authority=self._evidence_authority,
                telemetry_authority=self._telemetry_authority,
            )
        except PlacementExecutionError:
            raise
        except Exception as exc:
            raise PipelineError(
                PipelineErrorCode.POLICY_DENIED,
                f"Group-2 fabric-placed physical execution refused/failed for execution "
                f"{execution_id!r}: {exc}",
            ) from exc

        receipt_sig = sign_receipt(
            migration_id=payload.get("migration_id", ""), run_id=request.attempt_id,
            operation_id=request.operation_id or f"op-{request.invocation_id}",
            fencing_epoch=request.fence_epoch, status_code="SUCCESS",
            initialization_fingerprint=request.initialization_fingerprint, job_id=request.graph_node_id,
        )
        receipt = {
            "gateway_migration_id": payload.get("migration_id", ""),
            "gateway_run_id": request.attempt_id,
            "gateway_operation_id": request.operation_id or f"op-{request.invocation_id}",
            "gateway_job_id": request.graph_node_id,
            "gateway_fencing_epoch": request.fence_epoch,
            "graph_node_id": request.graph_node_id,
            "initialization_fingerprint": request.initialization_fingerprint,
            "gateway_status_code": "SUCCESS",
            "receipt_signature": receipt_sig,
        }
        return EngineInvocationResult(
            invocation_id=request.invocation_id,
            attempt_id=request.attempt_id,
            lease_id=request.lease_id,
            fence_epoch=request.fence_epoch,
            is_success=True,
            initialization_fingerprint=request.initialization_fingerprint,
            terminal=True,
            is_in_progress=False,
            graph_node_id=request.graph_node_id,
            binding_id=request.binding_id,
            contract_version=request.contract_version,
            result_payload={
                "rows_written": rows_written, "fabric_site_id": binding.site.site_id,
                "fabric_decision_id": binding.decision.decision_id, "engine_execution_receipt": receipt,
            },
        )
