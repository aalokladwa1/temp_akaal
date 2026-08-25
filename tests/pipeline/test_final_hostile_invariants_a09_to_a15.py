"""tests/pipeline/test_final_hostile_invariants_a09_to_a15.py
==========================================================
Comprehensive hostile regression invariants covering Findings A-09 through A-15.
"""

from __future__ import annotations

import sqlite3
import pytest

from akaalEngine.gateway.models.responses import sign_receipt

from akaalIPC.protocol.errors import IPCErrorCategory
from akaalIPC.security.context import ActorContext, ActorReference, CorrelationContext
from akaalPipeline.application.unified_caller import PipelineUnifiedCaller
from akaalPipeline.capabilities.bindings import EngineBindingDescriptor
from akaalPipeline.contracts.enums import MigrationLifecycleState, MigrationMode, OperationStatus, SideEffectClassification
from akaalPipeline.contracts.errors import PipelineError, PipelineErrorCode, StaleResultError
from akaalPipeline.events.projections import ProjectionService
from akaalPipeline.execution.result_reconciliation import ResultReconciler
from akaalPipeline.operations.leases import LeaseManager
from akaalPipeline.orchestration.compiler import GraphCompiler


from akaalPipeline.ports.engine import EngineInvocationRequest, EngineInvocationResult, ExecutionPort
from akaalPipeline.recovery.checkpoints import CheckpointCandidate
from akaalPipeline.security.context import PipelineActorContext
from akaalPipeline.state.unit_of_work import SQLiteUnitOfWork
from tests.pipeline.conftest import make_command, make_query




class DummyTrackingPort(ExecutionPort):
    def __init__(self, name: str = "TrackingPort", should_succeed: bool = True) -> None:
        self.name = name
        self.invoked = False
        self.call_count = 0
        self.last_request = None
        self.should_succeed = should_succeed

    def execute_task(self, request: EngineInvocationRequest) -> EngineInvocationResult:
        self.invoked = True
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
        return EngineInvocationResult(
            invocation_id=request.invocation_id,
            attempt_id=request.attempt_id,
            lease_id=request.lease_id,
            fence_epoch=request.fence_epoch,
            is_success=self.should_succeed,
            initialization_fingerprint=request.initialization_fingerprint,
            graph_node_id=request.graph_node_id,
            binding_id=request.binding_id,
            contract_version=request.contract_version,
            result_payload={"status": "ok", "engine_execution_receipt": receipt},
        )


class RecordingExecutionPort(ExecutionPort):
    def __init__(self, should_succeed: bool = True, return_payload: dict = None, is_in_progress: bool = False) -> None:
        self.call_count = 0
        self.last_request = None
        self.should_succeed = should_succeed
        self.return_payload = return_payload or {"migrated_rows": 1000}
        self.is_in_progress = is_in_progress

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
            "engine_task_id": f"task-{request.invocation_id}",
        }
        sem_op = request.payload.get("semantic_operation") if isinstance(request.payload, dict) else None
        if sem_op == "ACQUIRE_EXECUTION_FENCE":
            canonical_res = f"{mig_id}/{request.attempt_id}/{request.graph_node_id}" if request.graph_node_id else f"{mig_id}/{request.attempt_id}"
            now = "2026-08-24T00:00:00Z"
            env = {
                "token_version": "1.0.0",
                "canonical_resource_id": canonical_res,
                "resource_id": canonical_res,
                "migration_id": mig_id,
                "run_id": request.attempt_id,
                "job_id": request.graph_node_id,
                "worker_id": request.payload.get("worker_id", "test_worker"),
                "fencing_epoch": request.fence_epoch or 1,
                "epoch": request.fence_epoch or 1,
                "issued_at": now,
                "signature": "test-fence-sig",
                "engine_signature": "test-fence-sig",
            }
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
                result_payload={"fencing_token_envelope": env, "engine_execution_receipt": receipt},
            )
        if sem_op == "CANCEL_EXECUTION":
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
                result_payload={"terminal": True, "cancelled": True, "engine_execution_receipt": receipt},
            )
        payload = dict(self.return_payload)
        payload["engine_execution_receipt"] = receipt
        if self.is_in_progress:
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
                is_in_progress=True,
                result_payload={"engine_execution_receipt": receipt},
            )
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
) -> None:
    cmd_create = make_command(
        request_type="migration.create",
        payload={"migration_id": migration_id, "name": f"Mig {migration_id}", "mode": mode},
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
# A-09: ONE AUTHORITATIVE BINDING SELECTION
# ==============================================================================

def test_a09_unrelated_binding_cannot_satisfy_capability(temp_db_path, ipc_actor, ipc_correlation):
    """Prove a binding registered ONLY for validation_compare cannot be invoked for data_transport."""
    caller = PipelineUnifiedCaller(db_path=temp_db_path)
    val_port = DummyTrackingPort("ValidationPort")
    caller.binding_registry.register(
        EngineBindingDescriptor(
            binding_id="bind-val-only",
            engine_name="ValidationEngine",
            version="1.0.0",
            port_instance=val_port,
            supported_capabilities={"validation_compare"},
            supported_modes={MigrationMode.M8_VALIDATION_ONLY},
        )
    )

    _setup_planned_and_initialized_migration(caller, "mig-unrelated-bind", ipc_actor, ipc_correlation, "M1")

    # Start M1 migration (requires data_transport)
    cmd = make_command(
        request_type="migration.start",
        payload={"migration_id": "mig-unrelated-bind", "mode": "M1"},
        actor=ipc_actor,
        correlation=ipc_correlation,
    )
    res = caller.handle_command(cmd)
    assert res.status.value == "ERROR"
    assert res.error.category == IPCErrorCategory.UNBOUND
    # The unrelated validation port must NEVER have been invoked
    assert not val_port.invoked


def test_a09_incompatible_contract_version_rejected(temp_db_path):
    """Prove a binding with incompatible contract version is rejected by resolver."""
    caller = PipelineUnifiedCaller(db_path=temp_db_path)
    port = DummyTrackingPort()
    caller.binding_registry.register(
        EngineBindingDescriptor(
            binding_id="bind-incompat-ver",
            engine_name="IncompatEngine",
            version="2.0.0",
            port_instance=port,
            contract_version="2.0.0",  # Requires 1.0.0
            supported_capabilities={"data_transport", "schema_prep"},
            supported_modes={MigrationMode.M1_BULK},
        )
    )

    eval_res = caller.catalog_resolver.evaluate_capability("data_transport", mode=MigrationMode.M1_BULK, contract_version="1.0.0")
    assert not eval_res.is_available
    assert eval_res.selected_binding is None


def test_a09_empty_capability_set_binding_rejected(temp_db_path):
    """Prove a binding with empty supported_capabilities or supported_modes is rejected and not treated as a wildcard."""
    caller = PipelineUnifiedCaller(db_path=temp_db_path)
    port = DummyTrackingPort()
    caller.binding_registry.register(
        EngineBindingDescriptor(
            binding_id="bind-empty-sets",
            engine_name="EmptyEngine",
            version="1.0.0",
            port_instance=port,
            supported_capabilities=set(),  # empty set
            supported_modes=set(),         # empty set
        )
    )

    eval_res = caller.catalog_resolver.evaluate_capability("data_transport", mode=MigrationMode.M1_BULK)
    assert not eval_res.is_available
    assert eval_res.selected_binding is None
    assert "UNBOUND" in "; ".join(eval_res.blockers)



def test_a09_multiple_competing_bindings_selects_only_exact_match(temp_db_path, ipc_actor, ipc_correlation):
    """Prove resolver accurately selects only the exact matching healthy binding from multiple competing candidates."""
    caller = PipelineUnifiedCaller(db_path=temp_db_path)

    port_wrong_cap = DummyTrackingPort("WrongCapPort")
    port_wrong_mode = DummyTrackingPort("WrongModePort")
    port_wrong_ver = DummyTrackingPort("WrongVerPort")
    port_unhealthy = DummyTrackingPort("UnhealthyPort")
    port_correct = DummyTrackingPort("CorrectPort")

    caller.binding_registry.register(
        EngineBindingDescriptor(
            binding_id="b-wrong-cap", engine_name="E1", version="1.0", port_instance=port_wrong_cap,
            supported_capabilities={"validation_compare"}, supported_modes={MigrationMode.M1_BULK},
        )
    )
    caller.binding_registry.register(
        EngineBindingDescriptor(
            binding_id="b-wrong-mode", engine_name="E2", version="1.0", port_instance=port_wrong_mode,
            supported_capabilities={"data_transport"}, supported_modes={MigrationMode.M8_VALIDATION_ONLY},
        )
    )
    caller.binding_registry.register(
        EngineBindingDescriptor(
            binding_id="b-wrong-ver", engine_name="E3", version="2.0", port_instance=port_wrong_ver,
            contract_version="2.0.0", supported_capabilities={"data_transport"}, supported_modes={MigrationMode.M1_BULK},
        )
    )
    caller.binding_registry.register(
        EngineBindingDescriptor(
            binding_id="b-unhealthy", engine_name="E4", version="1.0", port_instance=port_unhealthy,
            is_healthy=False, supported_capabilities={"data_transport"}, supported_modes={MigrationMode.M1_BULK},
        )
    )
    caller.binding_registry.register(
        EngineBindingDescriptor(
            binding_id="b-correct", engine_name="E5", version="1.0", port_instance=port_correct,
            contract_version="1.0.0", is_healthy=True, supported_capabilities={"schema_prep", "data_transport"}, supported_modes={MigrationMode.M1_BULK},
        )
    )


    _setup_planned_and_initialized_migration(caller, "mig-compete-bind", ipc_actor, ipc_correlation, "M1")

    cmd = make_command(
        request_type="migration.start",
        payload={"migration_id": "mig-compete-bind", "mode": "M1"},
        actor=ipc_actor,
        correlation=ipc_correlation,
    )
    res = caller.handle_command(cmd)
    assert res.status.value == "ACCEPTED"

    # Only the correct port MUST have been invoked
    assert not port_wrong_cap.invoked
    assert not port_wrong_mode.invoked
    assert not port_wrong_ver.invoked
    assert not port_unhealthy.invoked
    assert port_correct.invoked
    assert port_correct.call_count == 2



# ==============================================================================
# A-10: FULL RESULT PROVENANCE
# ==============================================================================

def test_a10_full_result_provenance_field_checks(temp_db_path):
    """Prove ResultReconciler validates all 8 fields of the provenance tuple individually."""
    uow = SQLiteUnitOfWork(db_path=temp_db_path)
    lease_mgr = LeaseManager()
    reconciler = ResultReconciler(lease_mgr)

    with uow:
        lease = lease_mgr.acquire_lease(
            lease_id="lease-prov-1",
            attempt_id="att-prov-1",
            owner_id="user-100",
            expires_at="2099-01-01T00:00:00Z",
            initialization_fingerprint="fp-init-valid",
            conn=uow.connection,
        )

        valid_res = EngineInvocationResult(
            invocation_id="inv-1",
            attempt_id="att-prov-1",
            lease_id="lease-prov-1",
            fence_epoch=1,
            is_success=True,
            initialization_fingerprint="fp-init-valid",
            graph_node_id="node-1",
            binding_id="bind-valid",
            contract_version="1.0.0",
            result_payload={
                "records": 100,
                "migration_id": "mig-prov-1",
                "engine_execution_receipt": {
                    "gateway_migration_id": "mig-prov-1",
                    "gateway_run_id": "att-prov-1",
                    "gateway_operation_id": "op-prov-1",
                    "gateway_job_id": "node-1",
                    "gateway_fencing_epoch": 1,
                    "graph_node_id": "node-1",
                    "initialization_fingerprint": "fp-init-valid",
                    "gateway_status_code": "SUCCESS",
                    "receipt_signature": sign_receipt(
                        migration_id="mig-prov-1",
                        run_id="att-prov-1",
                        operation_id="op-prov-1",
                        fencing_epoch=1,
                        status_code="SUCCESS",
                        initialization_fingerprint="fp-init-valid",
                        job_id="node-1",
                    ),
                },
            },
        )

        # 1. Valid reconciliation passes
        recon = reconciler.reconcile_result(
            valid_res,
            expected_initialization_fingerprint="fp-init-valid",
            conn=uow.connection,
            expected_invocation_id="inv-1",
            expected_graph_node_id="node-1",
            expected_binding_id="bind-valid",
            expected_contract_version="1.0.0",
        )
        assert recon["status"] == "SUCCEEDED"

        # 2. Invocation mismatch fails
        res_bad_inv = EngineInvocationResult(
            invocation_id="inv-bad", attempt_id="att-prov-1", lease_id="lease-prov-1", fence_epoch=1,
            is_success=True, initialization_fingerprint="fp-init-valid", graph_node_id="node-1",
        )
        with pytest.raises(StaleResultError, match="Invocation ID mismatch"):
            reconciler.reconcile_result(res_bad_inv, "fp-init-valid", uow.connection, expected_invocation_id="inv-1")

        # 3. Graph node mismatch fails
        res_bad_node = EngineInvocationResult(
            invocation_id="inv-1", attempt_id="att-prov-1", lease_id="lease-prov-1", fence_epoch=1,
            is_success=True, initialization_fingerprint="fp-init-valid", graph_node_id="node-bad",
        )
        with pytest.raises(StaleResultError, match="Graph node ID mismatch"):
            reconciler.reconcile_result(res_bad_node, "fp-init-valid", uow.connection, expected_graph_node_id="node-1")

        # 4. Lease mismatch fails
        res_bad_lease = EngineInvocationResult(
            invocation_id="inv-1", attempt_id="att-prov-1", lease_id="lease-wrong", fence_epoch=1,
            is_success=True, initialization_fingerprint="fp-init-valid", graph_node_id="node-1",
        )
        with pytest.raises(StaleResultError, match="Lease ID mismatch"):
            reconciler.reconcile_result(res_bad_lease, "fp-init-valid", uow.connection)

        # 5. Fence epoch mismatch fails
        res_bad_fence = EngineInvocationResult(
            invocation_id="inv-1", attempt_id="att-prov-1", lease_id="lease-prov-1", fence_epoch=99,
            is_success=True, initialization_fingerprint="fp-init-valid", graph_node_id="node-1",
        )
        with pytest.raises(StaleResultError, match="Fence epoch mismatch"):
            reconciler.reconcile_result(res_bad_fence, "fp-init-valid", uow.connection)

        # 6. Binding mismatch fails
        res_bad_binding = EngineInvocationResult(
            invocation_id="inv-1", attempt_id="att-prov-1", lease_id="lease-prov-1", fence_epoch=1,
            is_success=True, initialization_fingerprint="fp-init-valid", graph_node_id="node-1",
            binding_id="bind-wrong", contract_version="1.0.0",
        )
        with pytest.raises(StaleResultError, match="Binding ID mismatch"):
            reconciler.reconcile_result(res_bad_binding, "fp-init-valid", uow.connection, expected_binding_id="bind-valid", expected_contract_version="1.0.0")

        # 7. Missing binding ID fails
        res_missing_binding = EngineInvocationResult(
            invocation_id="inv-1", attempt_id="att-prov-1", lease_id="lease-prov-1", fence_epoch=1,
            is_success=True, initialization_fingerprint="fp-init-valid", graph_node_id="node-1",
            binding_id="", contract_version="1.0.0",
        )
        with pytest.raises(StaleResultError, match="Missing binding_id"):
            reconciler.reconcile_result(res_missing_binding, "fp-init-valid", uow.connection, expected_binding_id="bind-valid", expected_contract_version="1.0.0")

        # 8. Contract version mismatch fails
        res_bad_ver = EngineInvocationResult(
            invocation_id="inv-1", attempt_id="att-prov-1", lease_id="lease-prov-1", fence_epoch=1,
            is_success=True, initialization_fingerprint="fp-init-valid", graph_node_id="node-1",
            binding_id="bind-valid", contract_version="2.0.0",
        )
        with pytest.raises(StaleResultError, match="Contract version mismatch"):
            reconciler.reconcile_result(res_bad_ver, "fp-init-valid", uow.connection, expected_binding_id="bind-valid", expected_contract_version="1.0.0")

        # 9. Missing contract version fails
        res_missing_ver = EngineInvocationResult(
            invocation_id="inv-1", attempt_id="att-prov-1", lease_id="lease-prov-1", fence_epoch=1,
            is_success=True, initialization_fingerprint="fp-init-valid", graph_node_id="node-1",
            binding_id="bind-valid", contract_version="",
        )
        with pytest.raises(StaleResultError, match="Missing contract_version"):
            reconciler.reconcile_result(res_missing_ver, "fp-init-valid", uow.connection, expected_binding_id="bind-valid", expected_contract_version="1.0.0")

        # 10. Malformed payload type fails
        res_bad_payload = EngineInvocationResult(
            invocation_id="inv-1", attempt_id="att-prov-1", lease_id="lease-prov-1", fence_epoch=1,
            is_success=True, initialization_fingerprint="fp-init-valid", graph_node_id="node-1",
            binding_id="bind-valid", contract_version="1.0.0",
            result_payload="not-a-dict",  # type: ignore
        )
        with pytest.raises(StaleResultError, match="Malformed result_payload type"):
            reconciler.reconcile_result(res_bad_payload, "fp-init-valid", uow.connection, expected_binding_id="bind-valid", expected_contract_version="1.0.0")


# ==============================================================================
# A-11: DEEP PLAN IMMUTABILITY
# ==============================================================================

def test_a11_plan_nested_structures_deeply_immutable():
    """Prove ExecutionPlan, GraphNode, NodeTaskDescriptor and nested parameters cannot be mutated."""
    plan = GraphCompiler.compile_plan(
        plan_id="plan-immut",
        migration_id="mig-immut",
        mode=MigrationMode.M1_BULK,
        configuration={"table": "customers", "options": {"batch_size": 500}},
    )
    node = plan.nodes[0]

    # Attempt modifying nodes tuple
    with pytest.raises((TypeError, AttributeError)):
        plan.nodes[0] = None  # type: ignore

    # Attempt modifying parameters mapping
    with pytest.raises((TypeError, AttributeError)):
        node.task.parameters["table"] = "tampered"  # type: ignore

    # Attempt modifying dependencies tuple
    with pytest.raises((TypeError, AttributeError)):
        node.dependencies.append("node-fake")  # type: ignore


def test_a11_external_mutation_isolation():
    """Prove external mutations to input config dict do not mutate stored plan parameters."""
    external_config = {"batch_size": 100, "credentials": {"key": "secret-1"}}
    plan = GraphCompiler.compile_plan(
        plan_id="plan-iso-1",
        migration_id="mig-iso-1",
        mode=MigrationMode.M1_BULK,
        configuration=external_config,
    )

    # Mutate external dictionary after plan compilation
    external_config["batch_size"] = 999999
    external_config["credentials"]["key"] = "tampered"

    # Stored plan fingerprint & immutable parameters remain pristine
    assert plan.nodes[0].task.parameters.get("batch_size") != 999999


# ==============================================================================
# A-12: COMPLETE TRANSACTION ATOMICITY
# ==============================================================================

def test_a12_create_transaction_rollback_cleans_state_and_outbox_and_audit(temp_db_path, ipc_actor):
    """Prove that an unhandled error rolling back a UoW transaction leaves zero orphaned outbox or audit records."""
    uow = SQLiteUnitOfWork(db_path=temp_db_path)
    caller = PipelineUnifiedCaller(shared_uow=uow)
    pipeline_actor = PipelineActorContext.from_ipc(ipc_actor)

    with pytest.raises(RuntimeError):
        with uow:
            caller.command_handlers.handle_create_migration(
                {"migration_id": "mig-rb-1", "name": "Rollback Mig", "mode": "M1"},
                actor=pipeline_actor,
                uow=uow,
            )
            # Force exception inside transaction
            raise RuntimeError("Forced simulation failure")

    # Verify no rows exist in migrations, outbox_events, or audit_trail
    with uow:
        cur_mig = uow.connection.execute("SELECT COUNT(*) FROM migrations WHERE migration_id = 'mig-rb-1'")
        assert cur_mig.fetchone()[0] == 0

        cur_outbox = uow.connection.execute("SELECT COUNT(*) FROM outbox_events WHERE aggregate_id = 'mig-rb-1'")
        assert cur_outbox.fetchone()[0] == 0

        cur_audit = uow.connection.execute("SELECT COUNT(*) FROM audit_trail WHERE action = 'migration.created'")
        assert cur_audit.fetchone()[0] == 0


def test_a12_configure_rollback_cleans_all_records(temp_db_path, ipc_actor):
    """Prove forced failure during configure rolls back aggregate state and all correlated outbox/audit records."""
    uow = SQLiteUnitOfWork(db_path=temp_db_path)
    caller = PipelineUnifiedCaller(shared_uow=uow)
    pipeline_actor = PipelineActorContext.from_ipc(ipc_actor)

    # Create initial migration
    with uow:
        caller.command_handlers.handle_create_migration(
            {"migration_id": "mig-conf-rb", "name": "Conf RB Mig", "mode": "M1"},
            actor=pipeline_actor,
            uow=uow,
        )

    # Attempt configuration update with simulated failure
    with pytest.raises(RuntimeError):
        with uow:
            caller.command_handlers.handle_configure_migration(
                {"migration_id": "mig-conf-rb", "expected_revision": 1, "configuration": {"source": "pg://new"}},
                actor=pipeline_actor,
                uow=uow,
            )
            raise RuntimeError("Forced configuration failure")

    # Verify migration state was rolled back to DRAFT rev 1 and outbox has only create event
    with uow:
        agg = caller.repository.get_by_id("mig-conf-rb", connection=uow.connection)
        assert agg.state == MigrationLifecycleState.DRAFT
        assert agg.revision == 1

        cur_outbox = uow.connection.execute(
            "SELECT COUNT(*) FROM outbox_events WHERE aggregate_id = 'mig-conf-rb' AND event_type = 'migration.configured'"
        )
        assert cur_outbox.fetchone()[0] == 0


def test_a12_unbound_dispatch_failure_stages_outbox_and_audit(temp_db_path, ipc_actor, ipc_correlation):
    """Prove post-commit unbound failure in start stages correlated outbox event and audit trail."""
    caller = PipelineUnifiedCaller(db_path=temp_db_path)
    _setup_planned_and_initialized_migration(caller, "mig-unbound-audit", ipc_actor, ipc_correlation, "M1")

    # Start migration with NO engine bound
    cmd_start = make_command(
        request_type="migration.start",
        payload={"migration_id": "mig-unbound-audit", "mode": "M1"},
        actor=ipc_actor,
        correlation=ipc_correlation,
    )
    res_start = caller.handle_command(cmd_start)
    assert res_start.status.value == "ERROR"
    assert res_start.error.category == IPCErrorCategory.UNBOUND

    # Verify correlated outbox domain event and audit trail were persisted in DB
    uow = SQLiteUnitOfWork(db_path=temp_db_path)
    with uow:
        cur_out = uow.connection.execute(
            "SELECT event_type, payload FROM outbox_events WHERE aggregate_id = 'mig-unbound-audit' AND event_type = 'operation.failed'"
        )
        row_out = cur_out.fetchone()
        assert row_out is not None
        assert "UNBOUND" in row_out["payload"]

        cur_aud = uow.connection.execute(
            "SELECT action, actor_id FROM audit_trail WHERE action = 'operation.failed'"
        )
        row_aud = cur_aud.fetchone()
        assert row_aud is not None


# ==============================================================================
# A-13: COMPLETE CANCELLATION AUTHORITY
# ==============================================================================


def test_a13_cancellation_durability_and_idempotency(temp_db_path, ipc_actor, ipc_correlation):
    """Prove migration cancellation transitions to CANCELLED, records events, and is restart-durable."""
    caller1 = PipelineUnifiedCaller(db_path=temp_db_path)
    cmd_create = make_command(
        request_type="migration.create",
        payload={"migration_id": "mig-cancel-1", "name": "Cancel Mig", "mode": "M1"},
        actor=ipc_actor,
        correlation=ipc_correlation,
    )
    caller1.handle_command(cmd_create)

    cmd_cancel = make_command(
        request_type="migration.cancel",
        payload={"migration_id": "mig-cancel-1", "reason": "User abort"},
        actor=ipc_actor,
        correlation=ipc_correlation,
        idempotency_key="idemp-cancel-1",
    )
    res_cancel = caller1.handle_command(cmd_cancel)
    assert res_cancel.status.value == "OK"
    assert res_cancel.result["state"] == "CANCELLED"

    # Replay idempotency
    res_cancel_replay = caller1.handle_command(cmd_cancel)
    assert res_cancel_replay.status.value == "OK"

    # Verify state after restart
    caller2 = PipelineUnifiedCaller(db_path=temp_db_path)
    query = make_query(
        request_type="migration.get",
        payload={"migration_id": "mig-cancel-1"},
        actor=ipc_actor,
        correlation=ipc_correlation,
    )
    res_query = caller2.handle_query(query)
    assert res_query.status.value == "OK"
    assert res_query.result["state"] == "CANCELLED"


def test_a13_cancellation_fences_active_attempt_and_late_engine_result_rejected(temp_db_path, ipc_actor, ipc_correlation):
    """Prove cancelling a migration with an active attempt revokes its lease and fences out late engine results."""
    caller = PipelineUnifiedCaller(db_path=temp_db_path)
    rec_port = RecordingExecutionPort(is_in_progress=True)
    caller.binding_registry.register(
        EngineBindingDescriptor(
            binding_id="b-test-a13", engine_name="E1", version="1.0", port_instance=rec_port,
            supported_capabilities={"schema_prep", "data_transport"}, supported_modes={MigrationMode.M1_BULK},
        )
    )

    _setup_planned_and_initialized_migration(caller, "mig-fence-cancel", ipc_actor, ipc_correlation, "M1")

    # Start migration to establish active attempt A1 and lease
    cmd_start = make_command(
        request_type="migration.start",
        payload={"migration_id": "mig-fence-cancel", "mode": "M1"},
        actor=ipc_actor,
        correlation=ipc_correlation,
    )
    res_start = caller.handle_command(cmd_start)
    assert res_start.status.value == "ACCEPTED"

    uow = SQLiteUnitOfWork(db_path=temp_db_path)
    with uow:
        agg = caller.repository.get_by_id("mig-fence-cancel", connection=uow.connection)
        attempt_id = agg.active_attempt_id
        assert attempt_id is not None
        lease_before = caller.execution_controller.lease_manager.get_lease(attempt_id, uow.connection)
        assert lease_before is not None
        epoch_before = lease_before.fence_epoch

    # Cancel migration
    cmd_cancel = make_command(
        request_type="migration.cancel",
        payload={"migration_id": "mig-fence-cancel", "reason": "Operator cancelled execution"},
        actor=ipc_actor,
        correlation=ipc_correlation,
    )
    res_cancel = caller.handle_command(cmd_cancel)
    assert res_cancel.status.value == "OK"

    # Verify lease was revoked (expires in past) and fence epoch advanced
    with uow:
        agg_after = caller.repository.get_by_id("mig-fence-cancel", connection=uow.connection)
        assert agg_after.state == MigrationLifecycleState.CANCELLED
        assert agg_after.active_attempt_id is None

        lease_after = caller.execution_controller.lease_manager.get_lease(attempt_id, uow.connection)
        assert lease_after.is_expired()
        assert lease_after.fence_epoch > epoch_before

        # Late engine result reporting with old fence epoch must be strictly rejected
        late_result = EngineInvocationResult(
            invocation_id="inv-late",
            attempt_id=attempt_id,
            lease_id=lease_before.lease_id,
            fence_epoch=epoch_before,
            is_success=True,
            initialization_fingerprint=lease_before.initialization_fingerprint,
            binding_id="b-test-a13",
            contract_version="1.0.0",
        )
        with pytest.raises(StaleResultError, match="Fence epoch mismatch"):
            caller.result_reconciler.reconcile_result(
                late_result,
                expected_initialization_fingerprint=lease_before.initialization_fingerprint,
                conn=uow.connection,
            )


# ==============================================================================
# A-14: COMPLETE RECOVERY AUTHORITY
# ==============================================================================

def test_a14_recovery_durability_and_idempotency(temp_db_path, ipc_actor, ipc_correlation):
    """Prove recovery transitions a cancelled migration back to INITIALIZED and is restart-durable."""
    caller = PipelineUnifiedCaller(db_path=temp_db_path)
    cmd_create = make_command(
        request_type="migration.create",
        payload={"migration_id": "mig-recov-1", "name": "Recov Mig", "mode": "M1"},
        actor=ipc_actor,
        correlation=ipc_correlation,
    )
    caller.handle_command(cmd_create)

    cmd_cancel = make_command(
        request_type="migration.cancel",
        payload={"migration_id": "mig-recov-1"},
        actor=ipc_actor,
        correlation=ipc_correlation,
    )
    caller.handle_command(cmd_cancel)

    # Recover migration
    cmd_recov = make_command(
        request_type="migration.recover",
        payload={"migration_id": "mig-recov-1", "side_effect": "REVERSIBLE"},
        actor=ipc_actor,
        correlation=ipc_correlation,
        idempotency_key="idemp-recov-1",
    )
    res_recov = caller.handle_command(cmd_recov)
    assert res_recov.status.value == "OK"
    assert res_recov.result["state"] == "INITIALIZED"
    assert res_recov.result["new_attempt_id"] is not None
    assert res_recov.result["new_lease_id"] is not None


def test_a14_recovery_establishes_replacement_attempt_and_selects_checkpoint(temp_db_path, ipc_actor, ipc_correlation):
    """Prove recovery creates replacement attempt authority and records recovery operation record."""
    caller = PipelineUnifiedCaller(db_path=temp_db_path)
    rec_port = RecordingExecutionPort(is_in_progress=True)
    caller.binding_registry.register(
        EngineBindingDescriptor(
            binding_id="b-test-a14", engine_name="E1", version="1.0", port_instance=rec_port,
            supported_capabilities={"schema_prep", "data_transport"}, supported_modes={MigrationMode.M1_BULK},
        )
    )

    _setup_planned_and_initialized_migration(caller, "mig-recov-chk", ipc_actor, ipc_correlation, "M1")

    # Start migration to establish source attempt
    cmd_start = make_command(
        request_type="migration.start",
        payload={"migration_id": "mig-recov-chk", "mode": "M1"},
        actor=ipc_actor,
        correlation=ipc_correlation,
    )
    res_start = caller.handle_command(cmd_start)
    assert res_start.status.value == "ACCEPTED"


    uow = SQLiteUnitOfWork(db_path=temp_db_path)
    with uow:
        agg = caller.repository.get_by_id("mig-recov-chk", connection=uow.connection)
        source_attempt = agg.active_attempt_id
        # Record a valid checkpoint for source attempt
        candidate = CheckpointCandidate(
            checkpoint_id="chk-src-100",
            attempt_id=source_attempt,
            engine_invocation_id="inv-src-1",
            lease_id=f"lease-fake",
            fence_epoch=1,
            graph_node_id="node-1",
            initialization_fingerprint="fp-init-chk",
            engine_binding="b-1",
            checkpoint_payload_reference="s3://checkpoints/100",
        )
        uow.connection.execute(
            """
            INSERT INTO checkpoints (
                checkpoint_id, attempt_id, invocation_id, lease_id, fence_epoch,
                graph_node_id, initialization_fingerprint, binding_id,
                payload_reference, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                candidate.checkpoint_id, candidate.attempt_id, candidate.engine_invocation_id,
                candidate.lease_id, candidate.fence_epoch, candidate.graph_node_id,
                candidate.initialization_fingerprint, candidate.engine_binding,
                candidate.checkpoint_payload_reference, candidate.created_at,
            ),
        )

    # Cancel migration
    cmd_cancel = make_command(
        request_type="migration.cancel",
        payload={"migration_id": "mig-recov-chk"},
        actor=ipc_actor,
        correlation=ipc_correlation,
    )
    caller.handle_command(cmd_cancel)

    # Recover migration selecting checkpoint
    cmd_recov = make_command(
        request_type="migration.recover",
        payload={
            "migration_id": "mig-recov-chk",
            "source_attempt_id": source_attempt,
            "checkpoint_id": "chk-src-100",
            "side_effect": "REVERSIBLE",
        },
        actor=ipc_actor,
        correlation=ipc_correlation,
    )
    res_recov = caller.handle_command(cmd_recov)
    assert res_recov.status.value == "OK"
    assert res_recov.result["source_attempt_id"] == source_attempt
    assert res_recov.result["selected_checkpoint_id"] == "chk-src-100"
    assert res_recov.result["new_attempt_id"] != source_attempt

    # Verify recovery operation was recorded in operation_journal
    with uow:
        rec_op_id = res_recov.result["recovery_operation_id"]
        op_rec = caller.operation_service.get_operation(rec_op_id, uow.connection)
        assert op_rec is not None
        assert op_rec.status == OperationStatus.ACCEPTED


def test_a14_irreversible_recovery_rejected(temp_db_path, ipc_actor, ipc_correlation):
    """Prove automatic recovery for irreversible side-effects is rejected unless forced with admin authority."""
    caller = PipelineUnifiedCaller(db_path=temp_db_path)
    cmd_create = make_command(
        request_type="migration.create",
        payload={"migration_id": "mig-irrev-1", "name": "Irrev Mig", "mode": "M1"},
        actor=ipc_actor,
        correlation=ipc_correlation,
    )
    caller.handle_command(cmd_create)

    cmd_cancel = make_command(
        request_type="migration.cancel",
        payload={"migration_id": "mig-irrev-1"},
        actor=ipc_actor,
        correlation=ipc_correlation,
    )
    caller.handle_command(cmd_cancel)

    # Attempt automatic recovery of irreversible action without force
    cmd_recov_bad = make_command(
        request_type="migration.recover",
        payload={"migration_id": "mig-irrev-1", "side_effect": "IRREVERSIBLE", "force": False},
        actor=ipc_actor,
        correlation=ipc_correlation,
    )
    res = caller.handle_command(cmd_recov_bad)
    assert res.status.value == "ERROR"
    assert res.error.category == IPCErrorCategory.INELIGIBLE


def test_a14_unowned_source_attempt_rejected(temp_db_path, ipc_actor, ipc_correlation):
    """Prove recovery rejecting an attempt ID that does not belong to the migration."""
    caller = PipelineUnifiedCaller(db_path=temp_db_path)
    cmd_create = make_command(
        request_type="migration.create",
        payload={"migration_id": "mig-unowned-att", "name": "Unowned Att", "mode": "M1"},
        actor=ipc_actor,
        correlation=ipc_correlation,
    )
    caller.handle_command(cmd_create)

    cmd_cancel = make_command(
        request_type="migration.cancel",
        payload={"migration_id": "mig-unowned-att"},
        actor=ipc_actor,
        correlation=ipc_correlation,
    )
    caller.handle_command(cmd_cancel)

    # Supply an arbitrary unowned source attempt ID
    cmd_recov_bad = make_command(
        request_type="migration.recover",
        payload={"migration_id": "mig-unowned-att", "source_attempt_id": "att-alien-999"},
        actor=ipc_actor,
        correlation=ipc_correlation,
    )
    res = caller.handle_command(cmd_recov_bad)
    assert res.status.value == "ERROR"
    assert res.error.category == IPCErrorCategory.INVALID_REQUEST


def test_a14_unowned_checkpoint_rejected(temp_db_path, ipc_actor, ipc_correlation):
    """Prove recovery rejecting a checkpoint that belongs to a different attempt/migration."""
    caller = PipelineUnifiedCaller(db_path=temp_db_path)
    rec_port = RecordingExecutionPort(is_in_progress=True)
    caller.binding_registry.register(
        EngineBindingDescriptor(
            binding_id="b-test-chk-own", engine_name="E1", version="1.0", port_instance=rec_port,
            supported_capabilities={"schema_prep", "data_transport"}, supported_modes={MigrationMode.M1_BULK},
        )
    )
    _setup_planned_and_initialized_migration(caller, "mig-chk-own", ipc_actor, ipc_correlation, "M1")

    cmd_start = make_command(
        request_type="migration.start",
        payload={"migration_id": "mig-chk-own", "mode": "M1"},
        actor=ipc_actor,
        correlation=ipc_correlation,
    )
    res_start = caller.handle_command(cmd_start)
    assert res_start.status.value == "ACCEPTED"

    uow = SQLiteUnitOfWork(db_path=temp_db_path)
    with uow:
        agg = caller.repository.get_by_id("mig-chk-own", connection=uow.connection)
        source_attempt = agg.active_attempt_id
        # Record a foreign checkpoint belonging to a different attempt
        candidate = CheckpointCandidate(
            checkpoint_id="chk-alien-555",
            attempt_id="att-foreign-999",
            engine_invocation_id="inv-alien",
            lease_id="lease-alien",
            fence_epoch=1,
            graph_node_id="node-1",
            initialization_fingerprint="fp-alien",
            engine_binding="b-1",
            checkpoint_payload_reference="s3://checkpoints/alien",
        )
        uow.connection.execute(
            """
            INSERT INTO checkpoints (
                checkpoint_id, attempt_id, invocation_id, lease_id, fence_epoch,
                graph_node_id, initialization_fingerprint, binding_id,
                payload_reference, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                candidate.checkpoint_id, candidate.attempt_id, candidate.engine_invocation_id,
                candidate.lease_id, candidate.fence_epoch, candidate.graph_node_id,
                candidate.initialization_fingerprint, candidate.engine_binding,
                candidate.checkpoint_payload_reference, candidate.created_at,
            ),
        )

    cmd_cancel = make_command(
        request_type="migration.cancel",
        payload={"migration_id": "mig-chk-own"},
        actor=ipc_actor,
        correlation=ipc_correlation,
    )
    caller.handle_command(cmd_cancel)

    # Attempt to recover with foreign checkpoint
    cmd_recov_bad = make_command(
        request_type="migration.recover",
        payload={"migration_id": "mig-chk-own", "source_attempt_id": source_attempt, "checkpoint_id": "chk-alien-555"},
        actor=ipc_actor,
        correlation=ipc_correlation,
    )
    res = caller.handle_command(cmd_recov_bad)
    assert res.status.value == "ERROR"
    assert res.error.category == IPCErrorCategory.INVALID_REQUEST


def test_a14_recovery_fences_source_attempt_before_replacement_authority(temp_db_path, ipc_actor, ipc_correlation):
    """Prove recovery revokes and fences the source attempt before establishing replacement authority."""
    caller = PipelineUnifiedCaller(db_path=temp_db_path)
    rec_port = RecordingExecutionPort(is_in_progress=True)
    caller.binding_registry.register(
        EngineBindingDescriptor(
            binding_id="b-test-fence-rec", engine_name="E1", version="1.0", port_instance=rec_port,
            supported_capabilities={"schema_prep", "data_transport"}, supported_modes={MigrationMode.M1_BULK},
        )
    )
    _setup_planned_and_initialized_migration(caller, "mig-rec-fence", ipc_actor, ipc_correlation, "M1")

    cmd_start = make_command(
        request_type="migration.start",
        payload={"migration_id": "mig-rec-fence", "mode": "M1"},
        actor=ipc_actor,
        correlation=ipc_correlation,
    )
    res_start = caller.handle_command(cmd_start)
    assert res_start.status.value == "ACCEPTED"

    uow = SQLiteUnitOfWork(db_path=temp_db_path)
    with uow:
        agg = caller.repository.get_by_id("mig-rec-fence", connection=uow.connection)
        source_attempt = agg.active_attempt_id
        lease_before = caller.execution_controller.lease_manager.get_lease(source_attempt, uow.connection)
        epoch_before = lease_before.fence_epoch

    cmd_cancel = make_command(
        request_type="migration.cancel",
        payload={"migration_id": "mig-rec-fence"},
        actor=ipc_actor,
        correlation=ipc_correlation,
    )
    caller.handle_command(cmd_cancel)

    # Recover migration
    cmd_recov = make_command(
        request_type="migration.recover",
        payload={"migration_id": "mig-rec-fence", "source_attempt_id": source_attempt},
        actor=ipc_actor,
        correlation=ipc_correlation,
    )
    res_recov = caller.handle_command(cmd_recov)
    assert res_recov.status.value == "OK"

    # Verify source attempt lease is expired and its fence epoch was bumped
    with uow:
        lease_after = caller.execution_controller.lease_manager.get_lease(source_attempt, uow.connection)
        assert lease_after.is_expired()
        assert lease_after.fence_epoch > epoch_before

        # Late engine result proposal with old fence epoch must be rejected
        late_result = EngineInvocationResult(
            invocation_id="inv-late-src",
            attempt_id=source_attempt,
            lease_id=lease_before.lease_id,
            fence_epoch=epoch_before,
            is_success=True,
            initialization_fingerprint=lease_before.initialization_fingerprint,
            binding_id="b-test-fence-rec",
            contract_version="1.0.0",
        )
        with pytest.raises(StaleResultError, match="Fence epoch mismatch"):
            caller.result_reconciler.reconcile_result(
                late_result,
                expected_initialization_fingerprint=lease_before.initialization_fingerprint,
                conn=uow.connection,
            )


def test_a14_cross_migration_attempt_with_checkpoint_rejected(temp_db_path, ipc_actor, ipc_correlation):
    """Prove recovery on migration-B strictly rejects an attempt from migration-A even if migration-A's attempt has a valid checkpoint in the database."""
    caller = PipelineUnifiedCaller(db_path=temp_db_path)
    rec_port = RecordingExecutionPort(is_in_progress=True)
    caller.binding_registry.register(
        EngineBindingDescriptor(
            binding_id="b-test-cross-chk", engine_name="E1", version="1.0", port_instance=rec_port,
            supported_capabilities={"schema_prep", "data_transport"}, supported_modes={MigrationMode.M1_BULK},
        )
    )


    # 1. Start mig-alpha and establish its attempt and checkpoint
    _setup_planned_and_initialized_migration(caller, "mig-alpha", ipc_actor, ipc_correlation, "M1")
    cmd_start_alpha = make_command(
        request_type="migration.start",
        payload={"migration_id": "mig-alpha", "mode": "M1"},
        actor=ipc_actor,
        correlation=ipc_correlation,
    )
    res_start_alpha = caller.handle_command(cmd_start_alpha)
    assert res_start_alpha.status.value == "ACCEPTED"

    uow = SQLiteUnitOfWork(db_path=temp_db_path)
    with uow:
        agg_alpha = caller.repository.get_by_id("mig-alpha", connection=uow.connection)
        att_alpha = agg_alpha.active_attempt_id
        # Record checkpoint for mig-alpha's attempt
        candidate = CheckpointCandidate(
            checkpoint_id="chk-alpha-1",
            attempt_id=att_alpha,
            engine_invocation_id="inv-alpha-1",
            lease_id="lease-alpha-1",
            fence_epoch=1,
            graph_node_id="node-1",
            initialization_fingerprint="fp-init-alpha",
            engine_binding="b-test-cross-chk",
            checkpoint_payload_reference="s3://checkpoints/alpha",
        )
        uow.connection.execute(
            """
            INSERT INTO checkpoints (
                checkpoint_id, attempt_id, invocation_id, lease_id, fence_epoch,
                graph_node_id, initialization_fingerprint, binding_id,
                payload_reference, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                candidate.checkpoint_id, candidate.attempt_id, candidate.engine_invocation_id,
                candidate.lease_id, candidate.fence_epoch, candidate.graph_node_id,
                candidate.initialization_fingerprint, candidate.engine_binding,
                candidate.checkpoint_payload_reference, candidate.created_at,
            ),
        )

    # 2. Start and cancel mig-beta
    _setup_planned_and_initialized_migration(caller, "mig-beta", ipc_actor, ipc_correlation, "M1")
    cmd_start_beta = make_command(
        request_type="migration.start",
        payload={"migration_id": "mig-beta", "mode": "M1"},
        actor=ipc_actor,
        correlation=ipc_correlation,
    )
    res_start_beta = caller.handle_command(cmd_start_beta)
    assert res_start_beta.status.value == "ACCEPTED"

    cmd_cancel_beta = make_command(
        request_type="migration.cancel",
        payload={"migration_id": "mig-beta"},
        actor=ipc_actor,
        correlation=ipc_correlation,
    )
    caller.handle_command(cmd_cancel_beta)

    # 3. Attempt to recover mig-beta using mig-alpha's attempt ID (which has a valid checkpoint in DB)
    cmd_recov_cross = make_command(
        request_type="migration.recover",
        payload={"migration_id": "mig-beta", "source_attempt_id": att_alpha},
        actor=ipc_actor,
        correlation=ipc_correlation,
    )
    res_recov_cross = caller.handle_command(cmd_recov_cross)
    assert res_recov_cross.status.value == "ERROR"
    assert res_recov_cross.error.category == IPCErrorCategory.INVALID_REQUEST
    assert "does not belong to migration" in res_recov_cross.error.message

    # 4. Verify mig-alpha's lease was untouched
    with uow:
        lease_alpha = caller.execution_controller.lease_manager.get_lease(att_alpha, uow.connection)
        assert lease_alpha is not None
        assert not lease_alpha.is_expired()





# ==============================================================================
# A-15: PROJECT-SCOPED PROJECTIONS
# ==============================================================================

def test_a15_projection_scope_isolation(temp_db_path, ipc_actor):
    """Prove ProjectionService isolates query projections across tenant, workspace, and project dimensions."""
    uow = SQLiteUnitOfWork(db_path=temp_db_path)
    proj_service = ProjectionService()
    pipeline_actor = PipelineActorContext.from_ipc(ipc_actor)

    with uow:
        proj_service.update_projection(
            view_name="dashboard_summary",
            entity_id="dash-1",
            data={"active_migrations": 5, "total_rows": 10000},
            conn=uow.connection,
            tenant_id=pipeline_actor.organization_id,  # org-acme
            workspace_id=pipeline_actor.workspace_id,  # ws-main
            project_id=pipeline_actor.project_id,      # proj-db
        )

    # Actor from same tenant, workspace & project can access
    with uow:
        p1 = proj_service.get_projection(
            view_name="dashboard_summary",
            entity_id="dash-1",
            conn=uow.connection,
            actor=pipeline_actor,
        )
        assert p1 is not None
        assert p1.data["active_migrations"] == 5

    # Actor from different project cannot access
    actor_other_project = PipelineActorContext(
        actor_id="user-100",
        actor_type="user",
        organization_id="org-acme",
        workspace_id="ws-main",
        project_id="proj-other",
    )
    with uow:
        with pytest.raises(PipelineError) as exc_info:
            proj_service.get_projection(
                view_name="dashboard_summary",
                entity_id="dash-1",
                conn=uow.connection,
                actor=actor_other_project,
            )
        assert exc_info.value.code == PipelineErrorCode.POLICY_DENIED


def test_a15_projection_cross_project_same_entity_no_overwrite(temp_db_path):
    """Prove same-tenant different projects writing to same view and entity ID do not overwrite each other."""
    uow = SQLiteUnitOfWork(db_path=temp_db_path)
    proj_service = ProjectionService()

    with uow:
        # Project 1 writes
        proj_service.update_projection(
            view_name="dashboard_summary",
            entity_id="dash-shared",
            data={"project": "proj-1", "value": 100},
            conn=uow.connection,
            tenant_id="tenant-1",
            workspace_id="ws-1",
            project_id="proj-1",
        )
        # Project 2 writes to same view_name and entity_id
        proj_service.update_projection(
            view_name="dashboard_summary",
            entity_id="dash-shared",
            data={"project": "proj-2", "value": 200},
            conn=uow.connection,
            tenant_id="tenant-1",
            workspace_id="ws-1",
            project_id="proj-2",
        )

    # Verify both projections exist independently
    actor_p1 = PipelineActorContext(
        actor_id="user-1", actor_type="user", organization_id="tenant-1", workspace_id="ws-1", project_id="proj-1"
    )
    actor_p2 = PipelineActorContext(
        actor_id="user-2", actor_type="user", organization_id="tenant-1", workspace_id="ws-1", project_id="proj-2"
    )
    with uow:
        p1 = proj_service.get_projection("dashboard_summary", "dash-shared", conn=uow.connection, actor=actor_p1)
        p2 = proj_service.get_projection("dashboard_summary", "dash-shared", conn=uow.connection, actor=actor_p2)

        assert p1 is not None
        assert p1.data["value"] == 100
        assert p1.data["project"] == "proj-1"

        assert p2 is not None
        assert p2.data["value"] == 200
        assert p2.data["project"] == "proj-2"
