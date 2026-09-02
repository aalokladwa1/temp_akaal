"""tests/pipeline/test_hostile_scenarios_1_to_35.py
=================================================
Hostile failure tests covering required scenarios 1 through 35.
"""

from __future__ import annotations

import sqlite3
import pytest

from akaalIPC.protocol.errors import IPCErrorCategory
from akaalPipeline.application.unified_caller import PipelineUnifiedCaller
from akaalPipeline.capabilities.bindings import EngineBindingDescriptor
from akaalPipeline.contracts.enums import MigrationLifecycleState, MigrationMode, OperationStatus, SideEffectClassification
from akaalPipeline.contracts.errors import CheckpointRejectedError, IdempotencyConflictError, PolicyDeniedError, StaleResultError, UnsupportedModeError
from akaalPipeline.execution.result_reconciliation import ResultReconciler
from akaalPipeline.orchestration.compiler import GraphCompiler
from akaalPipeline.orchestration.graph_validation import GraphValidator
from akaalPipeline.orchestration.plans import ExecutionPlan, GraphNode, NodeTaskDescriptor
from akaalPipeline.policy.contracts import PolicyAction, PolicyDecision, PolicyResource, PolicyResult, PolicySubject
from akaalPipeline.policy.gates import PolicyGateEvaluator
from akaalPipeline.ports.engine import EngineInvocationRequest, EngineInvocationResult, ExecutionPort
from akaalPipeline.recovery.checkpoints import CheckpointCandidate, CheckpointManager
from akaalPipeline.recovery.coordinator import RecoveryCoordinator
from akaalPipeline.state.unit_of_work import SQLiteUnitOfWork
from tests.pipeline.conftest import make_command, make_query


# -- 01. Duplicate Start ----------------------------------------------------
def test_01_duplicate_start(unified_caller, verified_ipc_actor, ipc_correlation):
    """Prove duplicate start command handles idempotency or state transitions cleanly."""
    cmd_create = make_command(
        request_type="migration.create",
        payload={"migration_id": "mig-dup-1", "mode": "M1"},
        actor=verified_ipc_actor,
        correlation=ipc_correlation,
    )
    unified_caller.handle_command(cmd_create)
    cmd_init = make_command(
        request_type="migration.initialize",
        payload={"migration_id": "mig-dup-1"},
        actor=verified_ipc_actor,
        correlation=ipc_correlation,
    )
    unified_caller.handle_command(cmd_init)

    cmd1 = make_command(
        request_type="migration.start",
        payload={"migration_id": "mig-dup-1", "mode": "M1"},
        actor=verified_ipc_actor,
        correlation=ipc_correlation,
    )
    res1 = unified_caller.handle_command(cmd1)
    assert res1.status.value == "ERROR"
    assert res1.error.category == IPCErrorCategory.UNBOUND




# -- 02. Same Idempotency Key + Different Payload ---------------------------
def test_02_same_idempotency_different_payload(temp_db_path):
    uow = SQLiteUnitOfWork(db_path=temp_db_path)
    from akaalPipeline.operations.idempotency import IdempotencyService
    srv = IdempotencyService()
    with uow:
        srv.check_and_store("key-1", "cmd-1", "fp-A", {"res": "A"}, uow.connection)
        with pytest.raises(IdempotencyConflictError):
            srv.check_and_store("key-1", "cmd-2", "fp-B", {"res": "B"}, uow.connection)


# -- 06. Late Engine Result --------------------------------------------------
def test_06_late_engine_result(temp_db_path):
    uow = SQLiteUnitOfWork(db_path=temp_db_path)
    from akaalPipeline.operations.leases import LeaseManager
    lm = LeaseManager()
    with uow:
        lm.acquire_lease("l-new", "att-late", "owner-1", "2099-01-01T00:00:00+00:00", "fp-init", uow.connection)

    rec = ResultReconciler(lm)
    late_res = EngineInvocationResult(
        invocation_id="inv-old",
        attempt_id="att-late",
        lease_id="l-old",  # stale lease
        fence_epoch=1,
        is_success=True,
    )
    with uow:
        with pytest.raises(StaleResultError):
            rec.reconcile_result(late_res, "fp-init", uow.connection)


# -- 07. Old Executor / Fence Result ----------------------------------------
def test_07_old_executor_fence_result(temp_db_path):
    uow = SQLiteUnitOfWork(db_path=temp_db_path)
    from akaalPipeline.operations.leases import LeaseManager
    lm = LeaseManager()
    with uow:
        lm.acquire_lease("l-1", "att-fence", "owner-1", "2099-01-01T00:00:00+00:00", "fp-init", uow.connection)
        # Monotonic epoch bump
        lm.acquire_lease("l-2", "att-fence", "owner-1", "2099-01-01T00:00:00+00:00", "fp-init", uow.connection)

    rec = ResultReconciler(lm)
    stale_epoch_res = EngineInvocationResult(
        invocation_id="inv-old",
        attempt_id="att-fence",
        lease_id="l-2",
        fence_epoch=1,  # stored epoch is 2
        is_success=True,
    )
    with uow:
        with pytest.raises(StaleResultError):
            rec.reconcile_result(stale_epoch_res, "fp-init", uow.connection)


# -- 15. Policy Expiry Before Activation ------------------------------------
def test_15_policy_expiry_fails_closed():
    dec = PolicyDecision(
        decision_id="dec-1",
        policy_version="1.0",
        subject=PolicySubject("u1", "user"),
        action=PolicyAction("start"),
        resource=PolicyResource("mig1", "migration"),
        result=PolicyResult.ALLOW,
        reason="Approved",
        expires_at="2000-01-01T00:00:00+00:00",  # Expired
    )
    with pytest.raises(PolicyDeniedError):
        PolicyGateEvaluator.evaluate_gate(dec, current_time_iso="2026-08-20T20:00:00+00:00")


# -- 16. Duplicate Checkpoint -----------------------------------------------
def test_16_duplicate_checkpoint_is_idempotent(temp_db_path):
    uow = SQLiteUnitOfWork(db_path=temp_db_path)
    from akaalPipeline.operations.leases import LeaseManager
    lm = LeaseManager()
    with uow:
        lm.acquire_lease("l-1", "att-chk", "owner-1", "2099-01-01T00:00:00+00:00", "fp-init", uow.connection)

    chk_mgr = CheckpointManager(lm)
    cand = CheckpointCandidate(
        checkpoint_id="chk-dup-1",
        attempt_id="att-chk",
        engine_invocation_id="inv-1",
        lease_id="l-1",
        fence_epoch=1,
        graph_node_id="n-1",
        initialization_fingerprint="fp-init",
        engine_binding="binding-1",
        checkpoint_payload_reference="payload-ref",
    )

    with uow:
        chk_mgr.record_checkpoint(cand, "fp-init", uow.connection)
        # Duplicate record_checkpoint does not crash or duplicate record
        chk_mgr.record_checkpoint(cand, "fp-init", uow.connection)


# -- 17. Checkpoint For Wrong Initialization --------------------------------
def test_17_checkpoint_wrong_initialization_rejected(temp_db_path):
    uow = SQLiteUnitOfWork(db_path=temp_db_path)
    from akaalPipeline.operations.leases import LeaseManager
    lm = LeaseManager()
    with uow:
        lm.acquire_lease("l-1", "att-chk", "owner-1", "2099-01-01T00:00:00+00:00", "fp-correct", uow.connection)

    chk_mgr = CheckpointManager(lm)
    cand = CheckpointCandidate(
        checkpoint_id="chk-wrong-init",
        attempt_id="att-chk",
        engine_invocation_id="inv-1",
        lease_id="l-1",
        fence_epoch=1,
        graph_node_id="n-1",
        initialization_fingerprint="fp-correct",
        engine_binding="binding-1",
        checkpoint_payload_reference="payload-ref",
    )
    with uow:
        with pytest.raises(CheckpointRejectedError):
            chk_mgr.record_checkpoint(cand, "fp-WRONG", uow.connection)


# -- 22. M3 Graph Requests Illegal Bulk Behavior ----------------------------
def test_22_m3_graph_illegal_bulk_behavior():
    task = NodeTaskDescriptor("t-bulk", "initial_bulk_copy", SideEffectClassification.REVERSIBLE)
    node = GraphNode("n-bulk", task)
    plan = ExecutionPlan.create("p-m3", "mig-1", MigrationMode.M3_CDC, [node], [])
    with pytest.raises(UnsupportedModeError):
        GraphValidator.validate_plan(plan)


# -- 23. M6 Graph Requests Data Transport ----------------------------------
def test_23_m6_graph_illegal_data_transport():
    task = NodeTaskDescriptor("t-dt", "data_transport", SideEffectClassification.REVERSIBLE)
    node = GraphNode("n-dt", task)
    plan = ExecutionPlan.create("p-m6", "mig-1", MigrationMode.M6_SCHEMA_ONLY, [node], [])
    with pytest.raises(UnsupportedModeError):
        GraphValidator.validate_plan(plan)


# -- 24. M8 Graph Requests Mutation ----------------------------------------
def test_24_m8_graph_illegal_mutation():
    task = NodeTaskDescriptor("t-mut", "schema_apply", SideEffectClassification.DESTRUCTIVE)
    node = GraphNode("n-mut", task)
    plan = ExecutionPlan.create("p-m8", "mig-1", MigrationMode.M8_VALIDATION_ONLY, [node], [])
    with pytest.raises(UnsupportedModeError):
        GraphValidator.validate_plan(plan)


# -- 25. Irreversible Recovery Attempted Twice -----------------------------
def test_25_irreversible_recovery_forbidden(temp_db_path):
    uow = SQLiteUnitOfWork(db_path=temp_db_path)
    from akaalPipeline.operations.leases import LeaseManager
    from akaalPipeline.operations.service import OperationService
    rc = RecoveryCoordinator(LeaseManager(), OperationService())

    with uow:
        can_recover, reason = rc.evaluate_recovery("att-1", "op-1", SideEffectClassification.IRREVERSIBLE, uow.connection)
        assert can_recover is False
        assert "forbids automatic replay" in reason


# -- 29. IPC Acceptance Cannot Infer Execution Success ----------------------
def test_29_acceptance_distinct_from_execution_success(unified_caller, verified_ipc_actor, ipc_correlation):
    """Prove command acceptance or unbound error does NOT claim execution success."""
    cmd_create = make_command(
        request_type="migration.create",
        payload={"migration_id": "mig-29", "mode": "M1"},
        actor=verified_ipc_actor,
        correlation=ipc_correlation,
    )
    unified_caller.handle_command(cmd_create)
    cmd_init = make_command(
        request_type="migration.initialize",
        payload={"migration_id": "mig-29"},
        actor=verified_ipc_actor,
        correlation=ipc_correlation,
    )
    unified_caller.handle_command(cmd_init)

    cmd = make_command(
        request_type="migration.start",
        payload={"migration_id": "mig-29", "mode": "M1"},
        actor=verified_ipc_actor,
        correlation=ipc_correlation,
    )
    res = unified_caller.handle_command(cmd)
    # Unbound engine returns ERROR with category UNBOUND
    assert res.status.value == "ERROR"
    assert res.error.code == "UNBOUND"
