"""akaalPipeline.execution.controller
====================================
Pipeline-side execution controller managing attempt admission, lease acquisition, and engine dispatch.
"""

from __future__ import annotations

import sqlite3
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Mapping, Optional
from akaalPipeline.capabilities.bindings import BindingRegistry
from akaalPipeline.capabilities.resolver import CapabilityResolver
from akaalPipeline.contracts.enums import AttemptLifecycleState, MigrationMode, OperationStatus
from akaalPipeline.contracts.errors import UnboundEngineError
from akaalPipeline.operations.leases import ExecutionLease, LeaseManager
from akaalPipeline.operations.service import OperationService
from akaalPipeline.ports.engine import EngineInvocationRequest, EngineInvocationResult, ExecutionPort


class PipelineExecutionController:
    def __init__(
        self,
        capability_resolver: CapabilityResolver,
        binding_registry: BindingRegistry,
        lease_manager: LeaseManager,
        operation_service: OperationService,
    ) -> None:
        self.capability_resolver = capability_resolver
        self.binding_registry = binding_registry
        self.lease_manager = lease_manager
        self.operation_service = operation_service

    def start_attempt(
        self,
        attempt_id: str,
        operation_id: str,
        migration_id: str,
        mode: MigrationMode,
        initialization_fingerprint: str,
        graph_node_id: str,
        conn: sqlite3.Connection,
        owner_id: str = "pipeline-controller-1",
        timeout_seconds: int = 300,
    ) -> EngineInvocationResult:
        """Admit attempt, acquire lease, check physical engine binding. Fail closed if unbound or engine error."""
        # 1. Evaluate capability truth
        eval_res = self.capability_resolver.evaluate_capability(
            capability_id="data_transport",
            mode=mode,
        )

        # 2. Acquire execution lease & fence epoch
        lease_id = f"lease-{uuid.uuid4().hex}"
        expires_at = (datetime.now(timezone.utc) + timedelta(seconds=timeout_seconds)).isoformat()

        lease = self.lease_manager.acquire_lease(
            lease_id=lease_id,
            attempt_id=attempt_id,
            owner_id=owner_id,
            expires_at=expires_at,
            initialization_fingerprint=initialization_fingerprint,
            conn=conn,
        )

        # 3. If capability is not available (e.g. no engine bound) -> FAIL CLOSED WITH UNBOUND
        if not eval_res.is_available:
            error_msg = "; ".join(eval_res.blockers)
            self.operation_service.update_status(
                operation_id,
                OperationStatus.FAILED,
                conn,
                error={"code": "UNBOUND", "message": error_msg},
            )
            return EngineInvocationResult(
                invocation_id=f"inv-unbound-{uuid.uuid4().hex}",
                attempt_id=attempt_id,
                lease_id=lease.lease_id,
                fence_epoch=lease.fence_epoch,
                is_success=False,
                error_code="UNBOUND",
                error_message=error_msg,
            )

        # 4. If engine binding exists, dispatch to physical ExecutionPort
        bindings = self.binding_registry.list_all()
        healthy_binding = next((b for b in bindings if b.is_healthy and isinstance(b.port_instance, ExecutionPort)), None)

        if healthy_binding is None:
            error_msg = "No healthy ExecutionPort engine binding registered (UNBOUND)."
            self.operation_service.update_status(
                operation_id,
                OperationStatus.FAILED,
                conn,
                error={"code": "UNBOUND", "message": error_msg},
            )
            return EngineInvocationResult(
                invocation_id=f"inv-unbound-{uuid.uuid4().hex}",
                attempt_id=attempt_id,
                lease_id=lease.lease_id,
                fence_epoch=lease.fence_epoch,
                is_success=False,
                error_code="UNBOUND",
                error_message=error_msg,
            )

        # Dispatch invocation request to engine port
        inv_id = f"inv-{uuid.uuid4().hex}"

        req = EngineInvocationRequest(
            contract_version="1.0.0",
            binding_id=healthy_binding.binding_id,
            correlation_id=operation_id,
            operation_id=operation_id,
            attempt_id=attempt_id,
            invocation_id=inv_id,
            lease_id=lease.lease_id,
            fence_epoch=lease.fence_epoch,
            graph_node_id=graph_node_id,
            initialization_fingerprint=initialization_fingerprint,
            payload={"migration_id": migration_id, "mode": mode.value},
            timeout_seconds=timeout_seconds,
        )

        exec_port: ExecutionPort = healthy_binding.port_instance
        res = exec_port.execute_task(req)

        if res.is_success:
            self.operation_service.update_status(
                operation_id,
                OperationStatus.SUCCEEDED,
                conn,
                result_payload=res.result_payload,
            )
        else:
            self.operation_service.update_status(
                operation_id,
                OperationStatus.FAILED,
                conn,
                error={"code": res.error_code or "ENGINE_ERROR", "message": res.error_message or "Engine execution failed"},
            )

        return res
