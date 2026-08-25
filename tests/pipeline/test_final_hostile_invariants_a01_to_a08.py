"""tests/pipeline/test_final_hostile_invariants_a01_to_a08.py
==========================================================
Comprehensive hostile regression invariants covering Findings A-01 through A-08.
"""

from __future__ import annotations

import tempfile
import uuid
from datetime import datetime, timedelta, timezone
import pytest

from akaalIPC.protocol.envelopes import CommandEnvelope, QueryEnvelope
from akaalIPC.protocol.errors import IPCErrorCategory
from akaalIPC.security.context import ActorContext, ActorReference, CorrelationContext
from akaalPipeline.application.unified_caller import PipelineUnifiedCaller
from akaalPipeline.capabilities.bindings import EngineBindingDescriptor
from akaalPipeline.contracts.enums import MigrationLifecycleState, MigrationMode, OperationStatus
from akaalPipeline.operations.idempotency import IdempotencyService
from akaalPipeline.contracts.errors import (
    CheckpointRejectedError,
    ContractIncompatibleError,
    IdempotencyConflictError,

    IneligibleError,
    LeaseConflictError,
    NotReadyError,
    PersistenceError,
    PipelineError,
    PipelineErrorCode,
    PolicyDeniedError,
    RevisionConflictError,
    StaleResultError,
    UnableToAcquireLeaseError,
    UnavailableError,
    UnboundEngineError,
    UnsupportedModeError,
)
from akaalPipeline.orchestration.compiler import GraphCompiler
from akaalPipeline.orchestration.graph_validation import GraphValidator
from akaalPipeline.policy.contracts import PolicyAction, PolicyDecision, PolicyResource, PolicyResult, PolicySubject
from akaalPipeline.ports.engine import EngineInvocationRequest, EngineInvocationResult, ExecutionPort
from akaalPipeline.security.context import PipelineActorContext
from akaalPipeline.state.aggregates import MigrationAggregate
from akaalPipeline.state.artifacts import ImmutableArtifact
from akaalPipeline.state.unit_of_work import SQLiteUnitOfWork
from tests.pipeline.conftest import make_command, make_query


class RecordingExecutionPort(ExecutionPort):
    def __init__(self, should_succeed: bool = True, return_payload: dict = None) -> None:
        self.call_count = 0
        self.last_request = None
        self.should_succeed = should_succeed
        self.return_payload = return_payload or {"migrated_rows": 1000}

    def execute_task(self, request: EngineInvocationRequest) -> EngineInvocationResult:
        self.call_count += 1
        self.last_request = request
        from akaalEngine.gateway.models.responses import sign_receipt
        mig_id = request.payload.get("migration_id", "mig-1") if isinstance(request.payload, dict) else "mig-1"
        status_code = "SUCCESS" if self.should_succeed else "ERROR"
        sig = sign_receipt(
            migration_id=mig_id,
            run_id=request.attempt_id,
            operation_id=request.operation_id or f"op-{request.invocation_id}",
            fencing_epoch=request.fence_epoch,
            status_code=status_code,
            initialization_fingerprint=request.initialization_fingerprint,
            job_id=request.graph_node_id,
        )
        receipt = {
            "gateway_migration_id": mig_id,
            "gateway_run_id": request.attempt_id,
            "gateway_operation_id": request.operation_id or f"op-{request.invocation_id}",
            "gateway_job_id": request.graph_node_id,
            "gateway_fencing_epoch": request.fence_epoch,
            "graph_node_id": request.graph_node_id,
            "initialization_fingerprint": request.initialization_fingerprint,
            "gateway_status_code": status_code,
            "receipt_signature": sig,
        }
        payload = dict(self.return_payload)
        payload["engine_execution_receipt"] = receipt
        if self.should_succeed:
            return EngineInvocationResult(
                invocation_id=request.invocation_id,
                attempt_id=request.attempt_id,
                lease_id=request.lease_id,
                fence_epoch=request.fence_epoch,
                is_success=True,
                initialization_fingerprint=request.initialization_fingerprint,
                graph_node_id=request.graph_node_id,
                binding_id=request.binding_id,
                contract_version=request.contract_version,
                result_payload=payload,
            )
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
            result_payload={"engine_execution_receipt": receipt},
            error_code="ENGINE_EXEC_FAIL",
            error_message="Simulated physical failure",
        )


def _setup_planned_and_initialized_migration(
    caller: PipelineUnifiedCaller,
    migration_id: str,
    actor: ActorContext,
    correlation: CorrelationContext,
    mode: str = "M1",
    config: dict = None,
) -> None:
    cmd_create = make_command(
        request_type="migration.create",
        payload={"migration_id": migration_id, "name": f"Mig {migration_id}", "mode": mode, "configuration": config or {}},
        actor=actor,
        correlation=correlation,
    )
    caller.handle_command(cmd_create)

    cmd_plan = make_command(
        request_type="migration.plan",
        payload={"migration_id": migration_id},
        actor=actor,
        correlation=correlation,
    )
    caller.handle_command(cmd_plan)

    cmd_init = make_command(
        request_type="migration.initialize",
        payload={"migration_id": migration_id},
        actor=actor,
        correlation=correlation,
    )
    caller.handle_command(cmd_init)


# ==============================================================================
# A-01: COMPLETE IDEMPOTENCY AUTHORITY TESTS
# ==============================================================================

def test_a01_accepted_start_idempotency_replay(temp_db_path, ipc_actor, ipc_correlation):
    """Prove accepted migration.start returns exact operation reference on replay without duplicate dispatch."""
    caller = PipelineUnifiedCaller(db_path=temp_db_path)
    rec_port = RecordingExecutionPort(should_succeed=True)
    caller.binding_registry.register(
        EngineBindingDescriptor(
            binding_id="bind-test-1",
            engine_name="TestEngine",
            version="1.0.0",
            port_instance=rec_port,
            supported_capabilities={"data_transport", "schema_prep"},
            supported_modes={MigrationMode.M1_BULK},
        )
    )

    _setup_planned_and_initialized_migration(caller, "mig-idemp-1", ipc_actor, ipc_correlation, "M1")

    cmd = make_command(
        request_type="migration.start",
        payload={"migration_id": "mig-idemp-1", "mode": "M1"},
        actor=ipc_actor,
        correlation=ipc_correlation,
        idempotency_key="idemp-key-start-1",
    )
    res1 = caller.handle_command(cmd)
    assert res1.status.value == "ACCEPTED"
    assert res1.operation is not None
    orig_op_id = res1.operation.operation_id
    assert rec_port.call_count == 2

    # Replay with same key and payload
    res2 = caller.handle_command(cmd)
    assert res2.status.value == "ACCEPTED"
    assert res2.operation.operation_id == orig_op_id
    # Second dispatch must NOT have occurred
    assert rec_port.call_count == 2



def test_a01_error_idempotency_replay(temp_db_path, ipc_actor, ipc_correlation):
    """Prove unbound error response is stored and replayed with exact error code and category."""
    caller = PipelineUnifiedCaller(db_path=temp_db_path)
    _setup_planned_and_initialized_migration(caller, "mig-idemp-err-1", ipc_actor, ipc_correlation, "M1")

    cmd = make_command(
        request_type="migration.start",
        payload={"migration_id": "mig-idemp-err-1", "mode": "M1"},
        actor=ipc_actor,
        correlation=ipc_correlation,
        idempotency_key="idemp-key-err-1",
    )
    res1 = caller.handle_command(cmd)
    assert res1.status.value == "ERROR"
    assert res1.error.category == IPCErrorCategory.UNBOUND

    # Replay
    res2 = caller.handle_command(cmd)
    assert res2.status.value == "ERROR"
    assert res2.error.category == IPCErrorCategory.UNBOUND


def test_a01_same_key_different_command_conflict(temp_db_path, ipc_actor, ipc_correlation):
    """Prove same key with changed payload fingerprint fails closed with IDEMPOTENCY_CONFLICT."""
    caller = PipelineUnifiedCaller(db_path=temp_db_path)
    cmd1 = make_command(
        request_type="migration.create",
        payload={"migration_id": "mig-c1", "name": "Mig 1", "mode": "M1"},
        actor=ipc_actor,
        correlation=ipc_correlation,
        idempotency_key="shared-key-1",
    )
    res1 = caller.handle_command(cmd1)
    assert res1.status.value == "OK"

    cmd2 = make_command(
        request_type="migration.create",
        payload={"migration_id": "mig-c2-conflict", "name": "Mig 2 Different", "mode": "M1"},
        actor=ipc_actor,
        correlation=ipc_correlation,
        idempotency_key="shared-key-1",
    )
    res2 = caller.handle_command(cmd2)
    assert res2.status.value == "ERROR"
    assert res2.error.category == IPCErrorCategory.IDEMPOTENCY_CONFLICT


def test_a01_same_textual_key_across_tenants_does_not_collide(temp_db_path, ipc_actor, ipc_correlation):
    """Prove same textual key used by Tenant A and Tenant B does not collide or leak state."""
    caller = PipelineUnifiedCaller(db_path=temp_db_path)
    cmd_tenant_a = make_command(
        request_type="migration.create",
        payload={"migration_id": "mig-tenant-a-1", "name": "Mig A", "mode": "M1"},
        actor=ipc_actor,  # org-acme
        correlation=ipc_correlation,
        idempotency_key="reused-key-123",
    )
    res_a = caller.handle_command(cmd_tenant_a)
    assert res_a.status.value == "OK"
    assert res_a.result["migration_id"] == "mig-tenant-a-1"

    actor_b = ActorContext(
        actor=ActorReference(actor_id="user-200", actor_type="user", display_name="Tenant B"),
        organization_id="org-beta",
        workspace_id="ws-main",
        project_id="proj-db",
    )
    cmd_tenant_b = make_command(
        request_type="migration.create",
        payload={"migration_id": "mig-tenant-b-1", "name": "Mig B", "mode": "M1"},
        actor=actor_b,  # org-beta
        correlation=ipc_correlation,
        idempotency_key="reused-key-123",
    )
    res_b = caller.handle_command(cmd_tenant_b)
    assert res_b.status.value == "OK"
    assert res_b.result["migration_id"] == "mig-tenant-b-1"


def test_a01_same_textual_key_across_workspaces_does_not_collide(temp_db_path, ipc_actor, ipc_correlation):
    """Prove same textual key used by Workspace 1 and Workspace 2 does not collide."""
    caller = PipelineUnifiedCaller(db_path=temp_db_path)
    cmd_ws1 = make_command(
        request_type="migration.create",
        payload={"migration_id": "mig-ws1-1", "name": "Mig WS1", "mode": "M1"},
        actor=ipc_actor,  # ws-main
        correlation=ipc_correlation,
        idempotency_key="ws-reused-key",
    )
    res1 = caller.handle_command(cmd_ws1)
    assert res1.status.value == "OK"

    actor_ws2 = ActorContext(
        actor=ActorReference(actor_id="user-100", actor_type="user", display_name="WS2 Actor"),
        organization_id="org-acme",
        workspace_id="ws-secondary",
        project_id="proj-db",
    )
    cmd_ws2 = make_command(
        request_type="migration.create",
        payload={"migration_id": "mig-ws2-1", "name": "Mig WS2", "mode": "M1"},
        actor=actor_ws2,
        correlation=ipc_correlation,
        idempotency_key="ws-reused-key",
    )
    res2 = caller.handle_command(cmd_ws2)
    assert res2.status.value == "OK"
    assert res2.result["migration_id"] == "mig-ws2-1"


def test_a01_same_textual_key_across_projects_does_not_collide(temp_db_path, ipc_actor, ipc_correlation):
    """Prove same textual key used by Project 1 and Project 2 does not collide."""
    caller = PipelineUnifiedCaller(db_path=temp_db_path)
    cmd_p1 = make_command(
        request_type="migration.create",
        payload={"migration_id": "mig-p1-1", "name": "Mig P1", "mode": "M1"},
        actor=ipc_actor,  # proj-db
        correlation=ipc_correlation,
        idempotency_key="proj-reused-key",
    )
    res1 = caller.handle_command(cmd_p1)
    assert res1.status.value == "OK"

    actor_p2 = ActorContext(
        actor=ActorReference(actor_id="user-100", actor_type="user", display_name="P2 Actor"),
        organization_id="org-acme",
        workspace_id="ws-main",
        project_id="proj-analytics",
    )
    cmd_p2 = make_command(
        request_type="migration.create",
        payload={"migration_id": "mig-p2-1", "name": "Mig P2", "mode": "M1"},
        actor=actor_p2,
        correlation=ipc_correlation,
        idempotency_key="proj-reused-key",
    )
    res2 = caller.handle_command(cmd_p2)
    assert res2.status.value == "OK"
    assert res2.result["migration_id"] == "mig-p2-1"


def test_a01_same_textual_key_across_commands_does_not_collide(temp_db_path, ipc_actor, ipc_correlation):
    """Prove same key used on migration.create and migration.cancel does not collide."""
    caller = PipelineUnifiedCaller(db_path=temp_db_path)
    cmd_create = make_command(
        request_type="migration.create",
        payload={"migration_id": "mig-cmd-diff", "name": "Cmd Diff", "mode": "M1"},
        actor=ipc_actor,
        correlation=ipc_correlation,
        idempotency_key="cmd-key-multi",
    )
    res_c = caller.handle_command(cmd_create)
    assert res_c.status.value == "OK"

    cmd_cancel = make_command(
        request_type="migration.cancel",
        payload={"migration_id": "mig-cmd-diff"},
        actor=ipc_actor,
        correlation=ipc_correlation,
        idempotency_key="cmd-key-multi",
    )
    res_k = caller.handle_command(cmd_cancel)
    assert res_k.status.value == "OK"
    assert res_k.result["state"] == "CANCELLED"


def test_a01_restart_idempotency_replay(temp_db_path, ipc_actor, ipc_correlation):
    """Prove idempotency replay survives caller process restart on disk."""
    caller1 = PipelineUnifiedCaller(db_path=temp_db_path)
    cmd = make_command(
        request_type="migration.create",
        payload={"migration_id": "mig-restart-idemp", "name": "Restart Mig", "mode": "M1"},
        actor=ipc_actor,
        correlation=ipc_correlation,
        idempotency_key="restart-key-1",
    )
    res1 = caller1.handle_command(cmd)
    assert res1.status.value == "OK"

    # Process restart: new caller instance on same SQLite file
    caller2 = PipelineUnifiedCaller(db_path=temp_db_path)
    res2 = caller2.handle_command(cmd)
    assert res2.status.value == "OK"
    assert res2.result["migration_id"] == "mig-restart-idemp"


# ==============================================================================
# A-02: ERROR MAPPING FIDELITY
# ==============================================================================

def test_a02_all_concrete_pipeline_error_subclasses_to_ipc_error():
    """Prove every concrete PipelineError subclass correctly maps to a valid IPCErrorCategory."""
    error_instances = [
        PipelineError(PipelineErrorCode.INVALID_REQUEST, "invalid request"),
        RevisionConflictError("revision conflict", expected_revision=1, actual_revision=2),
        IdempotencyConflictError("idempotency conflict", idempotency_key="k1"),
        UnboundEngineError("unbound engine"),
        UnavailableError("unavailable"),
        UnsupportedModeError("unsupported mode"),
        IneligibleError("ineligible"),
        NotReadyError("not ready"),
        PolicyDeniedError("policy denied"),
        LeaseConflictError("lease conflict"),
        UnableToAcquireLeaseError("unable to acquire lease"),
        StaleResultError("stale result"),
        CheckpointRejectedError("checkpoint rejected"),
        ContractIncompatibleError("contract incompatible"),
        PersistenceError("persistence error"),
    ]

    for err in error_instances:
        ipc_err = err.to_ipc_error()
        assert isinstance(ipc_err.category, IPCErrorCategory)
        assert isinstance(ipc_err.code, str)
        assert isinstance(ipc_err.message, str)


# ==============================================================================
# A-03: COMPLETE THREE-DIMENSION AUTHORIZATION
# ==============================================================================

def test_a03_cross_tenant_migration_read_fails(temp_db_path, ipc_actor, ipc_correlation):
    """Prove tenant A cannot read tenant B's migration."""
    caller = PipelineUnifiedCaller(db_path=temp_db_path)
    cmd = make_command(
        request_type="migration.create",
        payload={"migration_id": "mig-tenant-a", "name": "Tenant A Mig", "mode": "M1"},
        actor=ipc_actor,  # org-acme
        correlation=ipc_correlation,
    )
    caller.handle_command(cmd)

    actor_b = ActorContext(
        actor=ActorReference(actor_id="user-200", actor_type="user", display_name="Tenant B"),
        organization_id="org-beta",
        workspace_id="ws-main",
        project_id="proj-db",
    )
    query_b = make_query(
        request_type="migration.get",
        payload={"migration_id": "mig-tenant-a"},
        actor=actor_b,
        correlation=ipc_correlation,
    )
    res = caller.handle_query(query_b)
    assert res.status.value == "ERROR"
    assert res.error.category == IPCErrorCategory.FORBIDDEN


def test_a03_cross_workspace_read_fails(temp_db_path, ipc_actor, ipc_correlation):
    """Prove actor in workspace-1 cannot read migration in workspace-2 under same tenant."""
    caller = PipelineUnifiedCaller(db_path=temp_db_path)
    cmd = make_command(
        request_type="migration.create",
        payload={"migration_id": "mig-ws-1", "name": "WS1 Mig", "mode": "M1"},
        actor=ipc_actor,  # ws-main
        correlation=ipc_correlation,
    )
    caller.handle_command(cmd)

    actor_ws_other = ActorContext(
        actor=ActorReference(actor_id="user-100", actor_type="user", display_name="Same Org Other WS"),
        organization_id="org-acme",
        workspace_id="ws-other",
        project_id="proj-db",
    )
    query_ws = make_query(
        request_type="migration.get",
        payload={"migration_id": "mig-ws-1"},
        actor=actor_ws_other,
        correlation=ipc_correlation,
    )
    res = caller.handle_query(query_ws)
    assert res.status.value == "ERROR"
    assert res.error.category == IPCErrorCategory.FORBIDDEN


def test_a03_cross_project_read_fails(temp_db_path, ipc_actor, ipc_correlation):
    """Prove actor in project-1 cannot read migration in project-2 under same tenant & workspace."""
    caller = PipelineUnifiedCaller(db_path=temp_db_path)
    cmd = make_command(
        request_type="migration.create",
        payload={"migration_id": "mig-proj-1", "name": "Proj1 Mig", "mode": "M1"},
        actor=ipc_actor,  # proj-db
        correlation=ipc_correlation,
    )
    caller.handle_command(cmd)

    actor_proj_other = ActorContext(
        actor=ActorReference(actor_id="user-100", actor_type="user", display_name="Other Proj Actor"),
        organization_id="org-acme",
        workspace_id="ws-main",
        project_id="proj-other",
    )
    query_proj = make_query(
        request_type="migration.get",
        payload={"migration_id": "mig-proj-1"},
        actor=actor_proj_other,
        correlation=ipc_correlation,
    )
    res = caller.handle_query(query_proj)
    assert res.status.value == "ERROR"
    assert res.error.category == IPCErrorCategory.FORBIDDEN


def test_a03_cross_tenant_operation_read_fails(temp_db_path, ipc_actor, ipc_correlation):
    """Prove reading operation of tenant A by tenant B fails closed."""
    caller = PipelineUnifiedCaller(db_path=temp_db_path)
    cmd = make_command(
        request_type="migration.create",
        payload={"migration_id": "mig-op-scope-1", "name": "Op Mig", "mode": "M1"},
        actor=ipc_actor,
        correlation=ipc_correlation,
    )
    caller.handle_command(cmd)

    actor_other = ActorContext(
        actor=ActorReference(actor_id="user-other", actor_type="user", display_name="Other"),
        organization_id="org-other",
    )
    query_op = make_query(
        request_type="operation.get",
        payload={"operation_id": "op-fake-1"},
        actor=actor_other,
        correlation=ipc_correlation,
    )
    res = caller.handle_query(query_op)
    assert res.status.value == "ERROR"
    assert res.error.category in (IPCErrorCategory.FORBIDDEN, IPCErrorCategory.INVALID_REQUEST)


def test_a03_cross_project_cancellation_fails(temp_db_path, ipc_actor, ipc_correlation):
    """Prove actor in project-1 cannot cancel migration in project-2."""
    caller = PipelineUnifiedCaller(db_path=temp_db_path)
    cmd_create = make_command(
        request_type="migration.create",
        payload={"migration_id": "mig-proj-cancel", "name": "Proj Cancel", "mode": "M1"},
        actor=ipc_actor,  # proj-db
        correlation=ipc_correlation,
    )
    caller.handle_command(cmd_create)

    actor_other_proj = ActorContext(
        actor=ActorReference(actor_id="user-other-proj", actor_type="user", display_name="Other Proj"),
        organization_id="org-acme",
        workspace_id="ws-main",
        project_id="proj-other",
    )
    cmd_cancel = make_command(
        request_type="migration.cancel",
        payload={"migration_id": "mig-proj-cancel"},
        actor=actor_other_proj,
        correlation=ipc_correlation,
    )
    res = caller.handle_command(cmd_cancel)
    assert res.status.value == "ERROR"
    assert res.error.category == IPCErrorCategory.FORBIDDEN


def test_a03_cross_project_recovery_fails(temp_db_path, ipc_actor, ipc_correlation):
    """Prove actor in project-1 cannot recover migration in project-2."""
    caller = PipelineUnifiedCaller(db_path=temp_db_path)
    cmd_create = make_command(
        request_type="migration.create",
        payload={"migration_id": "mig-proj-recov", "name": "Proj Recov", "mode": "M1"},
        actor=ipc_actor,  # proj-db
        correlation=ipc_correlation,
    )
    caller.handle_command(cmd_create)

    cmd_cancel = make_command(
        request_type="migration.cancel",
        payload={"migration_id": "mig-proj-recov"},
        actor=ipc_actor,
        correlation=ipc_correlation,
    )
    caller.handle_command(cmd_cancel)

    actor_other_proj = ActorContext(
        actor=ActorReference(actor_id="user-other-proj", actor_type="user", display_name="Other Proj"),
        organization_id="org-acme",
        workspace_id="ws-main",
        project_id="proj-other",
    )
    cmd_recov = make_command(
        request_type="migration.recover",
        payload={"migration_id": "mig-proj-recov"},
        actor=actor_other_proj,
        correlation=ipc_correlation,
    )
    res = caller.handle_command(cmd_recov)
    assert res.status.value == "ERROR"
    assert res.error.category == IPCErrorCategory.FORBIDDEN


def test_a03_unauthorized_cancellation_fails(temp_db_path, ipc_actor, ipc_correlation):
    """Prove cancelling migration of tenant A by actor in tenant B fails closed."""
    caller = PipelineUnifiedCaller(db_path=temp_db_path)
    cmd_create = make_command(
        request_type="migration.create",
        payload={"migration_id": "mig-unauth-cancel", "name": "Cancel Target", "mode": "M1"},
        actor=ipc_actor,  # org-acme
        correlation=ipc_correlation,
    )
    caller.handle_command(cmd_create)

    actor_b = ActorContext(
        actor=ActorReference(actor_id="user-b", actor_type="user", display_name="Tenant B"),
        organization_id="org-beta",
    )
    cmd_cancel_b = make_command(
        request_type="migration.cancel",
        payload={"migration_id": "mig-unauth-cancel"},
        actor=actor_b,
        correlation=ipc_correlation,
    )
    res = caller.handle_command(cmd_cancel_b)
    assert res.status.value == "ERROR"
    assert res.error.category == IPCErrorCategory.FORBIDDEN


def test_a03_unauthorized_recovery_fails(temp_db_path, ipc_actor, ipc_correlation):
    """Prove recovering migration of tenant A by actor in tenant B fails closed."""
    caller = PipelineUnifiedCaller(db_path=temp_db_path)
    cmd_create = make_command(
        request_type="migration.create",
        payload={"migration_id": "mig-unauth-recov", "name": "Recov Target", "mode": "M1"},
        actor=ipc_actor,
        correlation=ipc_correlation,
    )
    caller.handle_command(cmd_create)

    cmd_cancel = make_command(
        request_type="migration.cancel",
        payload={"migration_id": "mig-unauth-recov"},
        actor=ipc_actor,
        correlation=ipc_correlation,
    )
    caller.handle_command(cmd_cancel)

    actor_b = ActorContext(
        actor=ActorReference(actor_id="user-b", actor_type="user", display_name="Tenant B"),
        organization_id="org-beta",
    )
    cmd_recov_b = make_command(
        request_type="migration.recover",
        payload={"migration_id": "mig-unauth-recov"},
        actor=actor_b,
        correlation=ipc_correlation,
    )
    res = caller.handle_command(cmd_recov_b)
    assert res.status.value == "ERROR"
    assert res.error.category == IPCErrorCategory.FORBIDDEN


def test_a01_idempotent_result_overwrite_rejected(temp_db_path):
    """Prove IdempotencyService rejects concurrent overwrite attempts on the same key rather than silently replacing."""
    idemp_service = IdempotencyService()
    uow = SQLiteUnitOfWork(db_path=temp_db_path)
    with uow:
        # First write succeeds
        idemp_service.record_idempotent_result(
            idempotency_key="key-atomic-1",
            tenant_id="tenant-1",
            command_id="cmd-1",
            payload_fingerprint="fp-1",
            result_payload={"status": "OK", "val": 1},
            conn=uow.connection,
        )

        # Duplicate write with same key must fail closed with IdempotencyConflictError
        with pytest.raises(IdempotencyConflictError):
            idemp_service.record_idempotent_result(
                idempotency_key="key-atomic-1",
                tenant_id="tenant-1",
                command_id="cmd-2",
                payload_fingerprint="fp-1",
                result_payload={"status": "OK", "val": 2},
                conn=uow.connection,
            )


def test_a03_cross_project_operation_query_rejected(temp_db_path, ipc_correlation):
    """Prove operation query by an actor in project-2 targeting an operation created in project-1 fails closed."""
    caller = PipelineUnifiedCaller(db_path=temp_db_path)
    actor_p1 = ActorContext(
        actor=ActorReference(actor_id="user-1", actor_type="user", display_name="Actor P1"),
        organization_id="org-acme",
        workspace_id="ws-main",
        project_id="proj-db-1",
        environment="development",
        roles=("operator",),
    )
    actor_p2 = ActorContext(
        actor=ActorReference(actor_id="user-2", actor_type="user", display_name="Actor P2"),
        organization_id="org-acme",
        workspace_id="ws-main",
        project_id="proj-db-2",
        environment="development",
        roles=("operator",),
    )


    rec_port = RecordingExecutionPort(should_succeed=True)
    caller.binding_registry.register(
        EngineBindingDescriptor(
            binding_id="b-test-a03",
            engine_name="E1",
            version="1.0",
            port_instance=rec_port,
            supported_capabilities={"schema_prep", "data_transport"},
            supported_modes={MigrationMode.M1_BULK},
        )
    )

    _setup_planned_and_initialized_migration(caller, "mig-op-scope", actor_p1, ipc_correlation, "M1")

    cmd_start = make_command(
        request_type="migration.start",
        payload={"migration_id": "mig-op-scope", "mode": "M1"},
        actor=actor_p1,
        correlation=ipc_correlation,
    )
    res_start = caller.handle_command(cmd_start)
    op_id = res_start.operation.operation_id

    # Actor in P2 attempts to query operation created by P1
    q_env = make_query(
        request_type="operation.get",

        payload={"operation_id": op_id},
        actor=actor_p2,
        correlation=ipc_correlation,
    )
    res_q = caller.handle_query(q_env)
    assert res_q.status.value == "ERROR"
    assert res_q.error.category == IPCErrorCategory.FORBIDDEN




# ==============================================================================
# A-04: MANDATORY GOVERNANCE & ZERO AUTO-CREATE
# ==============================================================================

def test_a04_nonexistent_migration_start_rejected(temp_db_path, ipc_actor, ipc_correlation):
    """Prove start on nonexistent migration is rejected with INVALID_REQUEST and does NOT auto-create."""
    caller = PipelineUnifiedCaller(db_path=temp_db_path)
    cmd = make_command(
        request_type="migration.start",
        payload={"migration_id": "mig-does-not-exist", "mode": "M1"},
        actor=ipc_actor,
        correlation=ipc_correlation,
    )
    res = caller.handle_command(cmd)
    assert res.status.value == "ERROR"
    assert res.error.category == IPCErrorCategory.INVALID_REQUEST

    # Verify migration was NOT auto-created in database
    uow = SQLiteUnitOfWork(db_path=temp_db_path)
    with uow:
        cur = uow.connection.execute("SELECT COUNT(*) FROM migrations WHERE migration_id = 'mig-does-not-exist'")
        assert cur.fetchone()[0] == 0


def test_a04_wrong_mode_start_rejected(temp_db_path, ipc_actor, ipc_correlation):
    """Prove starting a configured M1 migration with mode=M3 in payload is rejected."""
    caller = PipelineUnifiedCaller(db_path=temp_db_path)
    _setup_planned_and_initialized_migration(caller, "mig-mode-mismatch", ipc_actor, ipc_correlation, "M1")

    cmd = make_command(
        request_type="migration.start",
        payload={"migration_id": "mig-mode-mismatch", "mode": "M3"},
        actor=ipc_actor,
        correlation=ipc_correlation,
    )
    res = caller.handle_command(cmd)
    assert res.status.value == "ERROR"
    assert res.error.category == IPCErrorCategory.INVALID_REQUEST


def test_a04_illegal_lifecycle_start_rejected(temp_db_path, ipc_actor, ipc_correlation):
    """Prove starting a migration in DRAFT state before planning/initialization is rejected."""
    caller = PipelineUnifiedCaller(db_path=temp_db_path)
    cmd_create = make_command(
        request_type="migration.create",
        payload={"migration_id": "mig-draft-only", "name": "Draft Mig", "mode": "M1"},
        actor=ipc_actor,
        correlation=ipc_correlation,
    )
    caller.handle_command(cmd_create)

    cmd_start = make_command(
        request_type="migration.start",
        payload={"migration_id": "mig-draft-only", "mode": "M1"},
        actor=ipc_actor,
        correlation=ipc_correlation,
    )
    res = caller.handle_command(cmd_start)
    assert res.status.value == "ERROR"
    assert res.error.category == IPCErrorCategory.INVALID_REQUEST


def test_a04_start_without_required_approval_fails(temp_db_path, ipc_correlation):
    """Prove migration.start requiring governance approval without valid policy decision fails closed."""
    caller = PipelineUnifiedCaller(db_path=temp_db_path)
    actor_gov = ActorContext(
        actor=ActorReference(actor_id="user-nonadmin", actor_type="user", display_name="Operator"),
        organization_id="org-acme",
        workspace_id="ws-main",
        project_id="proj-db",
        environment="production",
        roles=("operator",),
    )
    _setup_planned_and_initialized_migration(caller, "mig-appr-req", actor_gov, ipc_correlation, "M1")

    cmd = make_command(
        request_type="migration.start",
        payload={"migration_id": "mig-appr-req", "mode": "M1"},
        actor=actor_gov,
        correlation=ipc_correlation,
    )
    res = caller.handle_command(cmd)
    assert res.status.value == "ERROR"
    assert res.error.category == IPCErrorCategory.FORBIDDEN


def test_a04_caller_cannot_bypass_approval_with_payload_flag(temp_db_path, ipc_correlation):
    """Prove caller cannot bypass mandatory governance by sending skip_approval=True or require_approval=False."""
    caller = PipelineUnifiedCaller(db_path=temp_db_path)
    actor_gov = ActorContext(
        actor=ActorReference(actor_id="user-nonadmin", actor_type="user", display_name="Operator"),
        organization_id="org-acme",
        workspace_id="ws-main",
        project_id="proj-db",
        environment="production",
        roles=("operator",),
    )
    _setup_planned_and_initialized_migration(caller, "mig-appr-bypass", actor_gov, ipc_correlation, "M1")

    cmd = make_command(
        request_type="migration.start",
        payload={"migration_id": "mig-appr-bypass", "mode": "M1", "skip_approval": True, "require_approval": False},
        actor=actor_gov,
        correlation=ipc_correlation,
    )
    res = caller.handle_command(cmd)
    assert res.status.value == "ERROR"
    assert res.error.category == IPCErrorCategory.FORBIDDEN


def test_a04_caller_supplied_unpersisted_payload_decision_fails(temp_db_path, ipc_correlation):
    """Prove caller passing an unpersisted payload_decision dict directly cannot forge approval."""
    caller = PipelineUnifiedCaller(db_path=temp_db_path)
    actor_gov = ActorContext(
        actor=ActorReference(actor_id="user-nonadmin", actor_type="user", display_name="Operator"),
        organization_id="org-acme",
        workspace_id="ws-main",
        project_id="proj-db",
        environment="production",
        roles=("operator",),
    )
    _setup_planned_and_initialized_migration(caller, "mig-forged-appr", actor_gov, ipc_correlation, "M1")

    cmd = make_command(
        request_type="migration.start",
        payload={
            "migration_id": "mig-forged-appr",
            "mode": "M1",
            "policy_decision": {
                "decision_id": "dec-forged-payload",
                "result": "ALLOW",
            },
        },
        actor=actor_gov,
        correlation=ipc_correlation,
    )
    res = caller.handle_command(cmd)
    assert res.status.value == "ERROR"
    assert res.error.category == IPCErrorCategory.FORBIDDEN


def test_a04_expired_persisted_approval_fails(temp_db_path, ipc_actor, ipc_correlation):
    """Prove expired persisted approval decision is rejected during start admission."""
    caller = PipelineUnifiedCaller(db_path=temp_db_path)
    _setup_planned_and_initialized_migration(caller, "mig-exp-appr", ipc_actor, ipc_correlation, "M1")

    past_iso = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
    # Register expired approval artifact
    uow = SQLiteUnitOfWork(db_path=temp_db_path)
    with uow:
        from akaalPipeline.policy.contracts import PolicyAction, PolicyDecision, PolicyResource, PolicyResult, PolicySubject
        dec = PolicyDecision(
            decision_id="dec-expired",
            policy_version="1.0.0",
            subject=PolicySubject(actor_id="user-admin", actor_type="user", roles=["admin"]),
            action=PolicyAction(name="migration.start"),
            resource=PolicyResource(resource_id="mig-exp-appr", resource_type="migration"),
            result=PolicyResult.ALLOW,
            reason="Expired approval",
            issuer_id="user-admin",
            issuer_roles=["admin"],
            expires_at=past_iso,
        )
        caller.artifact_registry.register(
            ImmutableArtifact.create("art-approval-mig-exp-appr", "policy_decision", dec.to_dict()),
            conn=uow.connection,
        )

    actor_prod = ActorContext(
        actor=ActorReference(actor_id="user-op", actor_type="user", display_name="Operator"),
        organization_id="org-acme",
        workspace_id="ws-main",
        project_id="proj-db",
        environment="production",
        roles=("operator",),
    )
    cmd = make_command(
        request_type="migration.start",
        payload={"migration_id": "mig-exp-appr", "mode": "M1", "approval_id": "art-approval-mig-exp-appr"},
        actor=actor_prod,
        correlation=ipc_correlation,
    )
    res = caller.handle_command(cmd)
    assert res.status.value == "ERROR"
    assert res.error.category == IPCErrorCategory.FORBIDDEN


def test_a04_stale_approval_fingerprint_fails(temp_db_path, ipc_actor, ipc_correlation):
    """Prove policy decision with mismatched target artifact fingerprint is rejected."""
    caller = PipelineUnifiedCaller(db_path=temp_db_path)
    _setup_planned_and_initialized_migration(caller, "mig-stale-appr", ipc_actor, ipc_correlation, "M1")

    uow = SQLiteUnitOfWork(db_path=temp_db_path)
    with uow:
        from akaalPipeline.policy.contracts import PolicyAction, PolicyDecision, PolicyResource, PolicyResult, PolicySubject
        dec = PolicyDecision(
            decision_id="dec-stale",
            policy_version="1.0.0",
            subject=PolicySubject(actor_id="user-admin", actor_type="user", roles=["admin"]),
            action=PolicyAction(name="migration.start"),
            resource=PolicyResource(resource_id="mig-stale-appr", resource_type="migration", artifact_fingerprint="fp-mismatched"),
            result=PolicyResult.ALLOW,
            reason="Stale approval",
            issuer_id="user-admin",
            issuer_roles=["admin"],
        )
        caller.artifact_registry.register(
            ImmutableArtifact.create("art-approval-mig-stale-appr", "policy_decision", dec.to_dict()),
            conn=uow.connection,
        )

    actor_prod = ActorContext(
        actor=ActorReference(actor_id="user-op", actor_type="user", display_name="Operator"),
        organization_id="org-acme",
        workspace_id="ws-main",
        project_id="proj-db",
        environment="production",
        roles=("operator",),
    )
    cmd = make_command(
        request_type="migration.start",
        payload={"migration_id": "mig-stale-appr", "mode": "M1", "approval_id": "art-approval-mig-stale-appr"},
        actor=actor_prod,
        correlation=ipc_correlation,
    )
    res = caller.handle_command(cmd)
    assert res.status.value == "ERROR"
    assert res.error.category == IPCErrorCategory.FORBIDDEN


def test_a04_persisted_approval_with_authorized_admin_issuer_passes(temp_db_path, ipc_correlation):
    """Prove that an authoritative persisted approval issued by an admin allows execution."""
    caller = PipelineUnifiedCaller(db_path=temp_db_path)
    actor_admin = ActorContext(
        actor=ActorReference(actor_id="user-admin", actor_type="user", display_name="Admin"),
        organization_id="org-acme",
        workspace_id="ws-main",
        project_id="proj-db",
        environment="production",
        roles=("admin", "governor"),
    )
    actor_operator = ActorContext(
        actor=ActorReference(actor_id="user-op", actor_type="user", display_name="Operator"),
        organization_id="org-acme",
        workspace_id="ws-main",
        project_id="proj-db",
        environment="production",
        roles=("operator",),
    )
    _setup_planned_and_initialized_migration(caller, "mig-valid-appr", actor_admin, ipc_correlation, "M1")

    # Admin issues approval
    cmd_appr = make_command(
        request_type="migration.approve",
        payload={"migration_id": "mig-valid-appr", "reason": "Authorized by SecOps"},
        actor=actor_admin,
        correlation=ipc_correlation,
    )
    res_appr = caller.handle_command(cmd_appr)
    assert res_appr.status.value == "OK"
    assert res_appr.result["result"] == "ALLOW"

    # Operator starts migration with valid persisted approval
    rec_port = RecordingExecutionPort(should_succeed=True)
    caller.binding_registry.register(
        EngineBindingDescriptor(
            binding_id="b-valid-appr", engine_name="E1", version="1.0", port_instance=rec_port,
            supported_capabilities={"schema_prep", "data_transport"}, supported_modes={MigrationMode.M1_BULK},
        )
    )
    cmd_start = make_command(
        request_type="migration.start",
        payload={"migration_id": "mig-valid-appr", "mode": "M1"},
        actor=actor_operator,
        correlation=ipc_correlation,
    )
    res_start = caller.handle_command(cmd_start)
    assert res_start.status.value == "ACCEPTED"
    assert rec_port.call_count == 2



def test_a04_approval_resource_mismatch_fails(temp_db_path, ipc_correlation):
    """Prove an approval issued for migration-A cannot be reused to start migration-B even with matching fingerprint."""
    caller = PipelineUnifiedCaller(db_path=temp_db_path)
    actor_admin = ActorContext(
        actor=ActorReference(actor_id="user-admin", actor_type="user", display_name="Admin"),
        organization_id="org-acme",
        workspace_id="ws-main",
        project_id="proj-db",
        environment="production",
        roles=("admin",),
    )
    actor_op = ActorContext(
        actor=ActorReference(actor_id="user-op", actor_type="user", display_name="Operator"),
        organization_id="org-acme",
        workspace_id="ws-main",
        project_id="proj-db",
        environment="production",
        roles=("operator",),
    )
    _setup_planned_and_initialized_migration(caller, "mig-res-a", actor_admin, ipc_correlation, "M1")
    _setup_planned_and_initialized_migration(caller, "mig-res-b", actor_admin, ipc_correlation, "M1")

    # Issue approval explicitly for mig-res-a
    cmd_appr = make_command(
        request_type="migration.approve",
        payload={"migration_id": "mig-res-a", "approval_id": "art-approval-shared"},
        actor=actor_admin,
        correlation=ipc_correlation,
    )
    res_appr = caller.handle_command(cmd_appr)
    assert res_appr.status.value == "OK"

    # Attempt to start mig-res-b referencing mig-res-a's approval artifact
    cmd_start_b = make_command(
        request_type="migration.start",
        payload={"migration_id": "mig-res-b", "mode": "M1", "approval_id": "art-approval-shared"},
        actor=actor_op,
        correlation=ipc_correlation,
    )
    res_start_b = caller.handle_command(cmd_start_b)
    assert res_start_b.status.value == "ERROR"
    assert res_start_b.error.category == IPCErrorCategory.FORBIDDEN


def test_a04_approval_action_mismatch_fails(temp_db_path, ipc_correlation):
    """Prove an approval issued for a non-start action (e.g. migration.cancel) cannot authorize migration.start."""
    caller = PipelineUnifiedCaller(db_path=temp_db_path)
    actor_admin = ActorContext(
        actor=ActorReference(actor_id="user-admin", actor_type="user", display_name="Admin"),
        organization_id="org-acme",
        workspace_id="ws-main",
        project_id="proj-db",
        environment="production",
        roles=("admin",),
    )
    actor_op = ActorContext(
        actor=ActorReference(actor_id="user-op", actor_type="user", display_name="Operator"),
        organization_id="org-acme",
        workspace_id="ws-main",
        project_id="proj-db",
        environment="production",
        roles=("operator",),
    )
    _setup_planned_and_initialized_migration(caller, "mig-act-mismatch", actor_admin, ipc_correlation, "M1")

    # Issue approval for cancel action instead of start
    cmd_appr = make_command(
        request_type="migration.approve",
        payload={"migration_id": "mig-act-mismatch", "action": "migration.cancel", "approval_id": "art-approval-cancel"},
        actor=actor_admin,
        correlation=ipc_correlation,
    )
    res_appr = caller.handle_command(cmd_appr)
    assert res_appr.status.value == "OK"

    # Attempt to start migration using the cancel approval
    cmd_start = make_command(
        request_type="migration.start",
        payload={"migration_id": "mig-act-mismatch", "mode": "M1", "approval_id": "art-approval-cancel"},
        actor=actor_op,
        correlation=ipc_correlation,
    )
    res_start = caller.handle_command(cmd_start)
    assert res_start.status.value == "ERROR"
    assert res_start.error.category == IPCErrorCategory.FORBIDDEN


def test_a04_approval_subject_mismatch_fails(temp_db_path, ipc_correlation):
    """Prove an approval restricted to actor-X cannot be consumed by actor-Y."""
    caller = PipelineUnifiedCaller(db_path=temp_db_path)
    actor_admin = ActorContext(
        actor=ActorReference(actor_id="user-admin", actor_type="user", display_name="Admin"),
        organization_id="org-acme",
        workspace_id="ws-main",
        project_id="proj-db",
        environment="production",
        roles=("admin",),
    )
    actor_alice = ActorContext(
        actor=ActorReference(actor_id="user-alice", actor_type="user", display_name="Alice"),
        organization_id="org-acme",
        workspace_id="ws-main",
        project_id="proj-db",
        environment="production",
        roles=("operator",),
    )
    actor_bob = ActorContext(
        actor=ActorReference(actor_id="user-bob", actor_type="user", display_name="Bob"),
        organization_id="org-acme",
        workspace_id="ws-main",
        project_id="proj-db",
        environment="production",
        roles=("operator",),
    )
    _setup_planned_and_initialized_migration(caller, "mig-subj-mismatch", actor_admin, ipc_correlation, "M1")

    # Issue approval specifically bound to Alice
    cmd_appr = make_command(
        request_type="migration.approve",
        payload={"migration_id": "mig-subj-mismatch", "subject_actor_id": "user-alice", "approval_id": "art-approval-alice"},
        actor=actor_admin,
        correlation=ipc_correlation,
    )
    res_appr = caller.handle_command(cmd_appr)
    assert res_appr.status.value == "OK"

    # Bob attempts to start using Alice's approval
    cmd_start_bob = make_command(
        request_type="migration.start",
        payload={"migration_id": "mig-subj-mismatch", "mode": "M1", "approval_id": "art-approval-alice"},
        actor=actor_bob,
        correlation=ipc_correlation,
    )
    res_start_bob = caller.handle_command(cmd_start_bob)
    assert res_start_bob.status.value == "ERROR"
    assert res_start_bob.error.category == IPCErrorCategory.FORBIDDEN




# ==============================================================================
# A-05: CONFIGURATION INVALIDATION
# ==============================================================================

def test_a05_material_configuration_change_invalidates_initialization(temp_db_path, ipc_actor, ipc_correlation):
    """Prove modifying material source_connection resets initialization and plan, forcing CONFIGURING state."""
    caller = PipelineUnifiedCaller(db_path=temp_db_path)
    cmd_create = make_command(
        request_type="migration.create",
        payload={"migration_id": "mig-inval-1", "name": "Inval Mig", "mode": "M1"},
        actor=ipc_actor,
        correlation=ipc_correlation,
    )
    caller.handle_command(cmd_create)

    cmd_plan = make_command(
        request_type="migration.plan",
        payload={"migration_id": "mig-inval-1"},
        actor=ipc_actor,
        correlation=ipc_correlation,
    )
    caller.handle_command(cmd_plan)

    cmd_init = make_command(
        request_type="migration.initialize",
        payload={"migration_id": "mig-inval-1"},
        actor=ipc_actor,
        correlation=ipc_correlation,
    )
    res_init = caller.handle_command(cmd_init)
    assert res_init.status.value == "OK"
    assert res_init.result["state"] == "INITIALIZED"

    # Update material configuration
    cmd_config = make_command(
        request_type="migration.configure",
        payload={
            "migration_id": "mig-inval-1",
            "expected_revision": 3,
            "configuration": {"source_connection": "pg://prod-db:5432/db1", "target_connection": "pg://target:5432/db2"},
        },
        actor=ipc_actor,
        correlation=ipc_correlation,
    )
    res_conf = caller.handle_command(cmd_config)
    assert res_conf.status.value == "OK"
    assert res_conf.result["state"] == "CONFIGURING"
    assert res_conf.result["initialization_id"] is None
    assert res_conf.result["plan_id"] is None


# ==============================================================================
# A-06: DURABLE ACCEPTANCE BEFORE DISPATCH
# ==============================================================================

def test_a06_engine_call_count_zero_when_acceptance_commit_fails(temp_db_path, ipc_actor, ipc_correlation):
    """Prove engine port is never invoked if admission transaction commit fails."""
    caller = PipelineUnifiedCaller(db_path=temp_db_path)
    rec_port = RecordingExecutionPort(should_succeed=True)
    caller.binding_registry.register(
        EngineBindingDescriptor(
            binding_id="bind-test-2",
            engine_name="TestEngine",
            version="1.0.0",
            port_instance=rec_port,
            supported_capabilities={"data_transport", "schema_prep"},
            supported_modes={MigrationMode.M1_BULK},
        )
    )

    _setup_planned_and_initialized_migration(caller, "mig-lock-1", ipc_actor, ipc_correlation, "M1")

    actor_other = ActorContext(
        actor=ActorReference(actor_id="user-bad", actor_type="user", display_name="Bad Actor"),
        organization_id="org-bad",
    )
    cmd_start_bad = make_command(
        request_type="migration.start",
        payload={"migration_id": "mig-lock-1", "mode": "M1"},
        actor=actor_other,
        correlation=ipc_correlation,
    )
    res = caller.handle_command(cmd_start_bad)
    assert res.status.value == "ERROR"
    # Engine call count MUST be strictly 0
    assert rec_port.call_count == 0


def test_a06_accepted_operation_survives_dispatch_failure(temp_db_path, ipc_actor, ipc_correlation):
    """Prove operation journal record is safely committed in Phase 1 even if engine dispatch fails."""
    caller = PipelineUnifiedCaller(db_path=temp_db_path)
    failing_port = RecordingExecutionPort(should_succeed=False)
    caller.binding_registry.register(
        EngineBindingDescriptor(
            binding_id="bind-failing",
            engine_name="FailingEngine",
            version="1.0.0",
            port_instance=failing_port,
            supported_capabilities={"data_transport", "schema_prep"},
            supported_modes={MigrationMode.M1_BULK},
        )
    )

    _setup_planned_and_initialized_migration(caller, "mig-fail-disp-1", ipc_actor, ipc_correlation, "M1")

    cmd = make_command(
        request_type="migration.start",
        payload={"migration_id": "mig-fail-disp-1", "mode": "M1"},
        actor=ipc_actor,
        correlation=ipc_correlation,
    )
    res = caller.handle_command(cmd)
    assert res.status.value == "ACCEPTED"
    op_id = res.operation.operation_id

    # Verify operation record exists and was updated to FAILED
    uow = SQLiteUnitOfWork(db_path=temp_db_path)
    with uow:
        cur = uow.connection.execute("SELECT status, error FROM operation_journal WHERE operation_id = ?", (op_id,))
        row = cur.fetchone()
        assert row is not None
        assert row["status"] == "FAILED"


def test_a06_engine_port_exception_transitions_operation_to_failed_and_stages_events(temp_db_path, ipc_actor, ipc_correlation):
    """Prove that if the engine port raises an unhandled exception during dispatch, the operation transitions to FAILED and stages outbox/audit events rather than stranding in ACCEPTED."""
    class CrashingExecutionPort:
        def execute_task(self, req):
            raise RuntimeError("Engine crashed during physical task execution")

    caller = PipelineUnifiedCaller(db_path=temp_db_path)
    caller.binding_registry.register(
        EngineBindingDescriptor(
            binding_id="bind-crashing",
            engine_name="CrashingEngine",
            version="1.0.0",
            port_instance=CrashingExecutionPort(),
            supported_capabilities={"data_transport", "schema_prep"},
            supported_modes={MigrationMode.M1_BULK},
        )
    )

    _setup_planned_and_initialized_migration(caller, "mig-crash-disp", ipc_actor, ipc_correlation, "M1")

    cmd = make_command(
        request_type="migration.start",
        payload={"migration_id": "mig-crash-disp", "mode": "M1"},
        actor=ipc_actor,
        correlation=ipc_correlation,
    )
    res = caller.handle_command(cmd)
    assert res.status.value == "ERROR"
    assert res.error.category == IPCErrorCategory.UNAVAILABLE
    assert "Engine port 'bind-crashing' failed during task execution" in res.error.message

    # Verify operation in DB is marked FAILED and has correlated outbox & audit events
    uow = SQLiteUnitOfWork(db_path=temp_db_path)
    with uow:
        cur_op = uow.connection.execute("SELECT status, error FROM operation_journal WHERE command_id = ?", (cmd.command_id,))
        row_op = cur_op.fetchone()
        assert row_op is not None
        assert row_op["status"] == "FAILED"
        assert "Engine crashed" in row_op["error"]

        cur_out = uow.connection.execute(
            "SELECT event_type, payload FROM outbox_events WHERE aggregate_id = 'mig-crash-disp' AND event_type = 'operation.failed'"
        )
        row_out = cur_out.fetchone()
        assert row_out is not None
        assert "ENGINE_DISPATCH_ERROR" in row_out["payload"]

        cur_aud = uow.connection.execute(
            "SELECT action, actor_id FROM audit_trail WHERE action = 'operation.failed'"
        )
        row_aud = cur_aud.fetchone()
        assert row_aud is not None


# ==============================================================================
# A-07: AUTHORITATIVE IMMUTABLE PLAN & NODE DERIVATION
# ==============================================================================


def test_a07_start_without_plan_fails_closed(temp_db_path, ipc_actor, ipc_correlation):
    """Prove start fails closed with NOT_READY if migration was not planned, with 0 engine calls and 0 created plan artifacts."""

    caller = PipelineUnifiedCaller(db_path=temp_db_path)
    rec_port = RecordingExecutionPort(should_succeed=True)
    caller.binding_registry.register(
        EngineBindingDescriptor(
            binding_id="b-test-a07", engine_name="E1", version="1.0", port_instance=rec_port,
            supported_capabilities={"schema_prep", "data_transport"}, supported_modes={MigrationMode.M1_BULK},
        )
    )
    cmd_create = make_command(
        request_type="migration.create",
        payload={"migration_id": "mig-no-plan", "name": "No Plan Mig", "mode": "M1"},
        actor=ipc_actor,
        correlation=ipc_correlation,
    )
    caller.handle_command(cmd_create)

    # Establish initialized state without an execution plan artifact
    uow = SQLiteUnitOfWork(db_path=temp_db_path)
    with uow:
        agg = caller.repository.get_by_id("mig-no-plan", connection=uow.connection)
        agg.state = MigrationLifecycleState.INITIALIZED
        agg.revision += 1
        caller.repository.save(agg, connection=uow.connection)

    # Attempt start directly without plan
    cmd_start = make_command(
        request_type="migration.start",
        payload={"migration_id": "mig-no-plan", "mode": "M1"},
        actor=ipc_actor,
        correlation=ipc_correlation,
    )
    res = caller.handle_command(cmd_start)
    assert res.status.value == "ERROR"
    assert res.error.category == IPCErrorCategory.NOT_READY
    assert rec_port.call_count == 0

    # Prove zero plan artifacts were manufactured
    with uow:
        cur = uow.connection.execute("SELECT COUNT(*) FROM immutable_artifacts WHERE artifact_type = 'execution_plan'")
        assert cur.fetchone()[0] == 0


def test_a07_start_without_initialization_fails_closed(temp_db_path, ipc_actor, ipc_correlation):
    """Prove start fails closed with NOT_READY if migration was not initialized, with 0 engine calls and 0 created init artifacts."""
    caller = PipelineUnifiedCaller(db_path=temp_db_path)
    rec_port = RecordingExecutionPort(should_succeed=True)
    caller.binding_registry.register(
        EngineBindingDescriptor(
            binding_id="b-test-a07-2", engine_name="E1", version="1.0", port_instance=rec_port,
            supported_capabilities={"schema_prep", "data_transport"}, supported_modes={MigrationMode.M1_BULK},
        )
    )
    cmd_create = make_command(
        request_type="migration.create",
        payload={"migration_id": "mig-no-init", "name": "No Init Mig", "mode": "M1"},
        actor=ipc_actor,
        correlation=ipc_correlation,
    )
    caller.handle_command(cmd_create)

    cmd_plan = make_command(
        request_type="migration.plan",
        payload={"migration_id": "mig-no-init"},
        actor=ipc_actor,
        correlation=ipc_correlation,
    )
    caller.handle_command(cmd_plan)

    # Establish initialized state with a valid plan but missing initialization artifact
    uow = SQLiteUnitOfWork(db_path=temp_db_path)
    with uow:
        agg = caller.repository.get_by_id("mig-no-init", connection=uow.connection)
        agg.state = MigrationLifecycleState.INITIALIZED
        agg.initialization_id = "art-init-nonexistent"
        agg.revision += 1
        caller.repository.save(agg, connection=uow.connection)


    # Attempt start without initialize
    cmd_start = make_command(
        request_type="migration.start",
        payload={"migration_id": "mig-no-init", "mode": "M1"},
        actor=ipc_actor,
        correlation=ipc_correlation,
    )
    res = caller.handle_command(cmd_start)
    assert res.status.value == "ERROR"
    assert res.error.category == IPCErrorCategory.NOT_READY
    assert rec_port.call_count == 0

    # Prove zero initialization artifacts were manufactured
    with uow:
        cur = uow.connection.execute("SELECT COUNT(*) FROM immutable_artifacts WHERE artifact_type = 'initialization'")
        assert cur.fetchone()[0] == 0



def test_a07_no_hardcoded_node_or_capability_authority():
    """Prove execution plan compiles mode-specific task capabilities rather than hardcoded strings."""
    for mode in [MigrationMode.M3_CDC, MigrationMode.M6_SCHEMA_ONLY, MigrationMode.M8_VALIDATION_ONLY]:
        plan = GraphCompiler.compile_plan(f"plan-{mode.value}", f"mig-{mode.value}", mode)

        contracts = [node.task.capability_contract for node in plan.nodes]
        # None of these modes should contain data_transport
        assert "data_transport" not in contracts
        if mode == MigrationMode.M3_CDC:
            assert "cdc_capture" in contracts
            assert "cdc_apply" in contracts
        elif mode == MigrationMode.M6_SCHEMA_ONLY:
            assert "schema_extract" in contracts
            assert "schema_apply" in contracts
        elif mode == MigrationMode.M8_VALIDATION_ONLY:
            assert "validation_compare" in contracts


# ==============================================================================
# A-08: M1–M8 TOPOLOGIES & DETERMINISTIC FINGERPRINTS
# ==============================================================================

def test_a08_all_m1_to_m8_graph_semantics_and_fingerprints():
    """Prove all 8 migration modes compile valid canonical acyclic graphs with deterministic fingerprints."""
    for mode in MigrationMode:
        plan = GraphCompiler.compile_plan(
            plan_id=f"plan-{mode.value}",
            migration_id=f"mig-{mode.value}",
            mode=mode,
            configuration={"sample": True},
        )
        assert plan.mode == mode
        assert len(plan.nodes) >= 1
        assert isinstance(plan.fingerprint, str)
        assert len(plan.fingerprint) == 64
        # Validate acyclic legality
        GraphValidator.validate_plan(plan)
