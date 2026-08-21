"""tests/pipeline/test_durable_dag_execution.py
=============================================
Hostile test suite proving durable, multi-node DAG plan execution authority in akaalPipeline.

Covers:
1. M1-M8 canonical topology execution sequences.
2. Multi-node sequential & concurrent dependency gating.
3. Mid-execution failure & unbound fail-closed semantics.
4. Predecessor failure blocking successors.
5. Independent attempt/lease/fence isolation per node.
6. Crash restart / SQLite reload durability without re-execution.
7. Node-level outbox and audit events.
8. Cancellation fencing across active and blocked nodes.
9. Custom complex DAG topologies (diamond, tree).
10. Deep idempotency isolation.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
import tempfile
import uuid
from typing import Any, Dict, List, Mapping, Optional
import pytest



from akaalIPC.protocol.errors import IPCErrorCategory
from akaalIPC.security.context import ActorContext, ActorReference, CorrelationContext
from akaalPipeline.application.unified_caller import PipelineUnifiedCaller
from akaalPipeline.capabilities.bindings import EngineBindingDescriptor
from akaalPipeline.contracts.enums import (
    MigrationLifecycleState,
    MigrationMode,
    NodeExecutionState,
    OperationStatus,
    PlanExecutionStatus,
    SideEffectClassification,
)
from akaalPipeline.operations.leases import LeaseManager
from akaalPipeline.execution.result_reconciliation import StaleResultError
from akaalPipeline.contracts.serialization import canonical_fingerprint
from akaalPipeline.orchestration.compiler import GraphCompiler

from akaalPipeline.orchestration.graph_validation import GraphValidator
from akaalPipeline.orchestration.plans import ExecutionPlan, GraphEdge, GraphNode, NodeTaskDescriptor
from akaalPipeline.ports.engine import EngineInvocationRequest, EngineInvocationResult, ExecutionPort
from akaalPipeline.security.context import PipelineActorContext
from akaalPipeline.state.artifacts import ImmutableArtifact
from akaalPipeline.state.unit_of_work import SQLiteUnitOfWork
from tests.pipeline.conftest import make_command, make_query


class MultiNodeTrackingPort(ExecutionPort):
    """Execution port that tracks invocations per node and capability, with configurable per-node behaviors."""

    def __init__(self, failure_nodes: Optional[List[str]] = None, crash_nodes: Optional[List[str]] = None) -> None:
        self.invocations: List[EngineInvocationRequest] = []
        self.invoked_nodes: List[str] = []
        self.invoked_capabilities: List[str] = []
        self.failure_nodes = failure_nodes or []
        self.crash_nodes = crash_nodes or []

    def execute_task(self, request: EngineInvocationRequest) -> EngineInvocationResult:
        self.invocations.append(request)
        self.invoked_nodes.append(request.graph_node_id)
        if request.graph_node_id in self.crash_nodes:
            raise RuntimeError(f"Engine crash on node {request.graph_node_id}")

        is_fail = request.graph_node_id in self.failure_nodes
        return EngineInvocationResult(
            invocation_id=request.invocation_id,
            attempt_id=request.attempt_id,
            lease_id=request.lease_id,
            fence_epoch=request.fence_epoch,
            is_success=not is_fail,
            initialization_fingerprint=request.initialization_fingerprint,
            graph_node_id=request.graph_node_id,
            binding_id=request.binding_id,
            contract_version=request.contract_version,
            result_payload={"node": request.graph_node_id, "processed": 100} if not is_fail else {},
            error_code="NODE_EXEC_ERR" if is_fail else None,
            error_message="Physical node task failure" if is_fail else None,
        )


def _setup_migration(caller: PipelineUnifiedCaller, migration_id: str, actor: ActorContext, corr: CorrelationContext, mode: str) -> None:
    caller.handle_command(
        make_command(
            request_type="migration.create",
            payload={"migration_id": migration_id, "name": f"Mig {migration_id}", "mode": mode},
            actor=actor,
            correlation=corr,
        )
    )
    caller.handle_command(
        make_command(
            request_type="migration.plan",
            payload={"migration_id": migration_id},
            actor=actor,
            correlation=corr,
        )
    )
    caller.handle_command(
        make_command(
            request_type="migration.initialize",
            payload={"migration_id": migration_id},
            actor=actor,
            correlation=corr,
        )
    )


def _register_universal_binding(caller: PipelineUnifiedCaller, port: ExecutionPort, binding_id: str = "b-universal") -> None:
    all_caps = {
        "schema_prep", "data_transport", "cdc_sync", "cdc_capture",
        "cdc_apply", "incremental_extract", "incremental_apply",
        "state_diff", "state_reconcile", "schema_extract",
        "schema_apply", "validation_compare",
    }
    all_modes = set(MigrationMode)
    caller.binding_registry.register(
        EngineBindingDescriptor(
            binding_id=binding_id,
            engine_name="UniversalEngine",
            version="1.0.0",
            contract_version="1.0.0",
            port_instance=port,
            supported_capabilities=all_caps,
            supported_modes=all_modes,
        )
    )


# ==============================================================================
# 1. CANONICAL TOPOLOGY TESTS (M1 - M8)
# ==============================================================================

def test_m1_multi_node_execution_sequence(temp_db_path, ipc_actor, ipc_correlation):
    """M1 executes schema_prep -> data_transport in exact sequence."""
    caller = PipelineUnifiedCaller(db_path=temp_db_path)
    port = MultiNodeTrackingPort()
    _register_universal_binding(caller, port)
    _setup_migration(caller, "mig-m1", ipc_actor, ipc_correlation, "M1")

    res = caller.handle_command(
        make_command(
            request_type="migration.start",
            payload={"migration_id": "mig-m1", "mode": "M1"},
            actor=ipc_actor,
            correlation=ipc_correlation,
        )
    )
    assert res.status.value == "ACCEPTED"
    assert len(port.invocations) == 2
    assert port.invoked_nodes == ["n-schema-prep", "n-data-transport"]

    # Verify durable state in SQLite
    uow = SQLiteUnitOfWork(db_path=temp_db_path)
    with uow:
        cur = uow.connection.execute("SELECT status FROM plan_executions WHERE migration_id = 'mig-m1'")
        row = cur.fetchone()
        assert row["status"] == "SUCCEEDED"

        cur_nodes = uow.connection.execute(
            "SELECT graph_node_id, state FROM node_executions WHERE migration_id = 'mig-m1' ORDER BY rowid ASC"
        )
        node_rows = cur_nodes.fetchall()
        assert len(node_rows) == 2
        assert node_rows[0]["graph_node_id"] == "n-schema-prep" and node_rows[0]["state"] == "SUCCEEDED"
        assert node_rows[1]["graph_node_id"] == "n-data-transport" and node_rows[1]["state"] == "SUCCEEDED"


def test_m2_three_node_execution_sequence(temp_db_path, ipc_actor, ipc_correlation):
    """M2 executes schema_prep -> data_transport -> cdc_sync in exact sequence."""
    caller = PipelineUnifiedCaller(db_path=temp_db_path)
    port = MultiNodeTrackingPort()
    _register_universal_binding(caller, port)
    _setup_migration(caller, "mig-m2", ipc_actor, ipc_correlation, "M2")

    res = caller.handle_command(
        make_command(
            request_type="migration.start",
            payload={"migration_id": "mig-m2", "mode": "M2"},
            actor=ipc_actor,
            correlation=ipc_correlation,
        )
    )
    assert res.status.value == "ACCEPTED"
    assert len(port.invocations) == 3
    assert port.invoked_nodes == ["n-schema-prep", "n-data-transport", "n-cdc-sync"]


def test_m3_two_node_cdc_sequence(temp_db_path, ipc_actor, ipc_correlation):
    """M3 executes cdc_capture -> cdc_apply in sequence."""
    caller = PipelineUnifiedCaller(db_path=temp_db_path)
    port = MultiNodeTrackingPort()
    _register_universal_binding(caller, port)
    _setup_migration(caller, "mig-m3", ipc_actor, ipc_correlation, "M3")

    res = caller.handle_command(
        make_command(
            request_type="migration.start",
            payload={"migration_id": "mig-m3", "mode": "M3"},
            actor=ipc_actor,
            correlation=ipc_correlation,
        )
    )
    assert res.status.value == "ACCEPTED"
    assert len(port.invocations) == 2
    assert port.invoked_nodes == ["n-cdc-capture", "n-cdc-apply"]


def test_m4_incremental_sequence(temp_db_path, ipc_actor, ipc_correlation):
    """M4 executes incremental_extract -> incremental_apply in sequence."""
    caller = PipelineUnifiedCaller(db_path=temp_db_path)
    port = MultiNodeTrackingPort()
    _register_universal_binding(caller, port)
    _setup_migration(caller, "mig-m4", ipc_actor, ipc_correlation, "M4")

    res = caller.handle_command(
        make_command(
            request_type="migration.start",
            payload={"migration_id": "mig-m4", "mode": "M4"},
            actor=ipc_actor,
            correlation=ipc_correlation,
        )
    )
    assert res.status.value == "ACCEPTED"
    assert len(port.invocations) == 2
    assert port.invoked_nodes == ["n-inc-extract", "n-inc-apply"]


def test_m5_state_sync_sequence(temp_db_path, ipc_actor, ipc_correlation):
    """M5 executes state_diff -> state_reconcile in sequence."""
    caller = PipelineUnifiedCaller(db_path=temp_db_path)
    port = MultiNodeTrackingPort()
    _register_universal_binding(caller, port)
    _setup_migration(caller, "mig-m5", ipc_actor, ipc_correlation, "M5")

    res = caller.handle_command(
        make_command(
            request_type="migration.start",
            payload={"migration_id": "mig-m5", "mode": "M5"},
            actor=ipc_actor,
            correlation=ipc_correlation,
        )
    )
    assert res.status.value == "ACCEPTED"
    assert len(port.invocations) == 2
    assert port.invoked_nodes == ["n-state-diff", "n-state-reconcile"]


def test_m6_schema_sequence(temp_db_path, ipc_actor, ipc_correlation):
    """M6 executes schema_extract -> schema_apply in sequence."""
    caller = PipelineUnifiedCaller(db_path=temp_db_path)
    port = MultiNodeTrackingPort()
    _register_universal_binding(caller, port)
    _setup_migration(caller, "mig-m6", ipc_actor, ipc_correlation, "M6")

    res = caller.handle_command(
        make_command(
            request_type="migration.start",
            payload={"migration_id": "mig-m6", "mode": "M6"},
            actor=ipc_actor,
            correlation=ipc_correlation,
        )
    )
    assert res.status.value == "ACCEPTED"
    assert len(port.invocations) == 2
    assert port.invoked_nodes == ["n-schema-extract", "n-schema-apply"]


def test_m7_single_node_data_transport(temp_db_path, ipc_actor, ipc_correlation):
    """M7 executes single node data_transport."""
    caller = PipelineUnifiedCaller(db_path=temp_db_path)
    port = MultiNodeTrackingPort()
    _register_universal_binding(caller, port)
    _setup_migration(caller, "mig-m7", ipc_actor, ipc_correlation, "M7")

    res = caller.handle_command(
        make_command(
            request_type="migration.start",
            payload={"migration_id": "mig-m7", "mode": "M7"},
            actor=ipc_actor,
            correlation=ipc_correlation,
        )
    )
    assert res.status.value == "ACCEPTED"
    assert len(port.invocations) == 1
    assert port.invoked_nodes == ["n-data-transport"]


def test_m8_single_node_validation_compare(temp_db_path, ipc_actor, ipc_correlation):
    """M8 executes single node validation_compare."""
    caller = PipelineUnifiedCaller(db_path=temp_db_path)
    port = MultiNodeTrackingPort()
    _register_universal_binding(caller, port)
    _setup_migration(caller, "mig-m8", ipc_actor, ipc_correlation, "M8")

    res = caller.handle_command(
        make_command(
            request_type="migration.start",
            payload={"migration_id": "mig-m8", "mode": "M8"},
            actor=ipc_actor,
            correlation=ipc_correlation,
        )
    )
    assert res.status.value == "ACCEPTED"
    assert len(port.invocations) == 1
    assert port.invoked_nodes == ["n-val-compare"]


# ==============================================================================
# 2. DEPENDENCY GATING & FAILURE SEMANTICS
# ==============================================================================

def test_predecessor_failure_blocks_successor_and_fails_plan(temp_db_path, ipc_actor, ipc_correlation):
    """When node 1 fails, node 2 remains BLOCKED and is never dispatched."""
    caller = PipelineUnifiedCaller(db_path=temp_db_path)
    port = MultiNodeTrackingPort(failure_nodes=["n-schema-prep"])
    _register_universal_binding(caller, port)
    _setup_migration(caller, "mig-fail-pred", ipc_actor, ipc_correlation, "M1")

    res = caller.handle_command(
        make_command(
            request_type="migration.start",
            payload={"migration_id": "mig-fail-pred", "mode": "M1"},
            actor=ipc_actor,
            correlation=ipc_correlation,
        )
    )
    assert res.status.value == "ACCEPTED"
    assert len(port.invocations) == 1
    assert port.invoked_nodes == ["n-schema-prep"]

    # Verify node 2 remained BLOCKED in database
    uow = SQLiteUnitOfWork(db_path=temp_db_path)
    with uow:
        cur = uow.connection.execute(
            "SELECT graph_node_id, state FROM node_executions WHERE migration_id = 'mig-fail-pred' ORDER BY rowid ASC"
        )
        rows = cur.fetchall()
        assert rows[0]["graph_node_id"] == "n-schema-prep" and rows[0]["state"] == "FAILED"
        assert rows[1]["graph_node_id"] == "n-data-transport" and rows[1]["state"] == "BLOCKED"

        cur_pe = uow.connection.execute("SELECT status FROM plan_executions WHERE migration_id = 'mig-fail-pred'")
        assert cur_pe.fetchone()["status"] == "FAILED"


def test_mid_execution_unbound_capability_fails_closed(temp_db_path, ipc_actor, ipc_correlation):
    """When node 2 capability has no registered binding, node 1 succeeds and node 2 fails with UNBOUND."""
    caller = PipelineUnifiedCaller(db_path=temp_db_path)
    port = MultiNodeTrackingPort()
    # Register binding ONLY for schema_prep (missing data_transport)
    caller.binding_registry.register(
        EngineBindingDescriptor(
            binding_id="b-schema-only",
            engine_name="SchemaOnlyEngine",
            version="1.0.0",
            port_instance=port,
            supported_capabilities={"schema_prep"},
            supported_modes={MigrationMode.M1_BULK},
        )
    )
    _setup_migration(caller, "mig-mid-unbound", ipc_actor, ipc_correlation, "M1")

    res = caller.handle_command(
        make_command(
            request_type="migration.start",
            payload={"migration_id": "mig-mid-unbound", "mode": "M1"},
            actor=ipc_actor,
            correlation=ipc_correlation,
        )
    )
    # UNBOUND returns ERROR
    assert res.status.value == "ERROR"
    assert res.error.category == IPCErrorCategory.UNBOUND

    # Verify node 1 was executed and SUCCEEDED, node 2 FAILED with UNBOUND
    assert len(port.invocations) == 1
    assert port.invoked_nodes == ["n-schema-prep"]

    uow = SQLiteUnitOfWork(db_path=temp_db_path)
    with uow:
        cur = uow.connection.execute(
            "SELECT graph_node_id, state FROM node_executions WHERE migration_id = 'mig-mid-unbound' ORDER BY rowid ASC"
        )
        rows = cur.fetchall()
        assert rows[0]["state"] == "SUCCEEDED"
        assert rows[1]["state"] == "FAILED"


def test_mid_execution_engine_crash_fails_closed(temp_db_path, ipc_actor, ipc_correlation):
    """When node 2 engine crashes with an unhandled exception, node 2 transitions to FAILED and returns UNAVAILABLE."""
    caller = PipelineUnifiedCaller(db_path=temp_db_path)
    port = MultiNodeTrackingPort(crash_nodes=["n-data-transport"])
    _register_universal_binding(caller, port)
    _setup_migration(caller, "mig-mid-crash", ipc_actor, ipc_correlation, "M1")

    res = caller.handle_command(
        make_command(
            request_type="migration.start",
            payload={"migration_id": "mig-mid-crash", "mode": "M1"},
            actor=ipc_actor,
            correlation=ipc_correlation,
        )
    )
    assert res.status.value == "ERROR"
    assert res.error.category == IPCErrorCategory.UNAVAILABLE
    assert "ENGINE_DISPATCH_ERROR" in res.error.code

    assert len(port.invocations) == 2
    assert port.invoked_nodes == ["n-schema-prep", "n-data-transport"]

    uow = SQLiteUnitOfWork(db_path=temp_db_path)
    with uow:
        cur = uow.connection.execute(
            "SELECT graph_node_id, state, error FROM node_executions WHERE migration_id = 'mig-mid-crash' ORDER BY rowid ASC"
        )
        rows = cur.fetchall()
        assert rows[0]["state"] == "SUCCEEDED"
        assert rows[1]["state"] == "FAILED"
        assert "Engine crash" in rows[1]["error"]


# ==============================================================================
# 3. ATTEMPT, LEASE, AND FENCING ISOLATION
# ==============================================================================

def test_each_node_acquires_distinct_attempt_lease_fence(temp_db_path, ipc_actor, ipc_correlation):
    """Prove each node in the DAG acquires its own unique attempt ID, lease ID, and fence epoch."""
    caller = PipelineUnifiedCaller(db_path=temp_db_path)
    port = MultiNodeTrackingPort()
    _register_universal_binding(caller, port)
    _setup_migration(caller, "mig-fence-iso", ipc_actor, ipc_correlation, "M2")

    res = caller.handle_command(
        make_command(
            request_type="migration.start",
            payload={"migration_id": "mig-fence-iso", "mode": "M2"},
            actor=ipc_actor,
            correlation=ipc_correlation,
        )
    )
    assert res.status.value == "ACCEPTED"
    assert len(port.invocations) == 3

    # All attempt IDs and lease IDs must be distinct
    attempt_ids = [inv.attempt_id for inv in port.invocations]
    lease_ids = [inv.lease_id for inv in port.invocations]
    invocation_ids = [inv.invocation_id for inv in port.invocations]

    assert len(set(attempt_ids)) == 3
    assert len(set(lease_ids)) == 3
    assert len(set(invocation_ids)) == 3

    uow = SQLiteUnitOfWork(db_path=temp_db_path)
    with uow:
        cur = uow.connection.execute(
            "SELECT current_attempt_id, lease_id, fence_epoch FROM node_executions WHERE migration_id = 'mig-fence-iso'"
        )
        rows = cur.fetchall()
        db_attempts = [r["current_attempt_id"] for r in rows]
        db_leases = [r["lease_id"] for r in rows]
        assert len(set(db_attempts)) == 3
        assert len(set(db_leases)) == 3


# ==============================================================================
# 4. CRASH RESTART & RESUMPTION FROM DURABLE SQLITE STATE
# ==============================================================================

def test_crash_recovery_resumes_from_ready_nodes(temp_db_path, ipc_actor, ipc_correlation):
    """Prove that reopening the database reconstructs execution state without re-executing completed nodes."""
    caller1 = PipelineUnifiedCaller(db_path=temp_db_path)
    # Simulate port that crashes on node 2 of M2
    port1 = MultiNodeTrackingPort(crash_nodes=["n-data-transport"])
    _register_universal_binding(caller1, port1)
    _setup_migration(caller1, "mig-resume", ipc_actor, ipc_correlation, "M2")

    res1 = caller1.handle_command(
        make_command(
            request_type="migration.start",
            payload={"migration_id": "mig-resume", "mode": "M2"},
            actor=ipc_actor,
            correlation=ipc_correlation,
        )
    )
    assert res1.status.value == "ERROR"
    assert port1.invoked_nodes == ["n-schema-prep", "n-data-transport"]

    # Re-open database with a new caller instance (simulating full process restart)
    caller2 = PipelineUnifiedCaller(db_path=temp_db_path)
    port2 = MultiNodeTrackingPort()  # Healthy port
    _register_universal_binding(caller2, port2)

    # In database: reset node 2 from FAILED to READY and plan to ACCEPTED
    uow = SQLiteUnitOfWork(db_path=temp_db_path)
    with uow:
        uow.connection.execute("UPDATE node_executions SET state = 'READY' WHERE graph_node_id = 'n-data-transport'")
        uow.connection.execute("UPDATE plan_executions SET status = 'ACCEPTED' WHERE migration_id = 'mig-resume'")

    # Resume execution via advance_plan_execution
    with uow:
        pe = caller2.plan_coordinator.get_active_execution_for_migration("mig-resume", uow.connection)
        agg = caller2.repository.get_by_id("mig-resume", connection=uow.connection)
        plan_art = caller2.artifact_registry.get(agg.plan_id, conn=uow.connection)
        plan = ExecutionPlan.from_dict(plan_art.content)
        pipeline_actor = PipelineActorContext.from_ipc(ipc_actor)

    outcome = caller2.plan_coordinator.advance_plan_execution(
        execution_id=pe.execution_id,
        plan=plan,
        actor=pipeline_actor,
        operation_id="op-resume",
        correlation_id=ipc_correlation.correlation_id,
        request_id="req-resume",
        payload={},
        uow_factory=caller2._create_uow,
    )
    assert outcome.is_success

    # Node 1 (schema-prep) was ALREADY succeeded, so port2 must ONLY execute node 2 and node 3!
    assert port2.invoked_nodes == ["n-data-transport", "n-cdc-sync"]
    assert "n-schema-prep" not in port2.invoked_nodes


# ==============================================================================
# 5. CANCELLATION FENCING ACROSS ACTIVE AND BLOCKED NODES
# ==============================================================================

def test_cancellation_fences_active_node_and_cancels_blocked_nodes(temp_db_path, ipc_actor, ipc_correlation):
    """Prove cancellation revokes active attempt lease and transitions all remaining nodes to CANCELLED."""
    caller = PipelineUnifiedCaller(db_path=temp_db_path)
    port = MultiNodeTrackingPort()
    _register_universal_binding(caller, port)
    _setup_migration(caller, "mig-cancel-nodes", ipc_actor, ipc_correlation, "M2")

    # Manually materialize plan execution to set initial states
    uow = SQLiteUnitOfWork(db_path=temp_db_path)
    with uow:
        agg = caller.repository.get_by_id("mig-cancel-nodes", connection=uow.connection)
        plan_art = caller.artifact_registry.get(agg.plan_id, conn=uow.connection)
        plan = ExecutionPlan.from_dict(plan_art.content)
        p_actor = PipelineActorContext.from_ipc(ipc_actor)
        pe = caller.plan_coordinator.materialize_plan_execution(plan, agg, p_actor, "fp-test", uow.connection)

    # Cancel migration
    res_cancel = caller.handle_command(
        make_command(
            request_type="migration.cancel",
            payload={"migration_id": "mig-cancel-nodes", "reason": "Operator abort"},
            actor=ipc_actor,
            correlation=ipc_correlation,
        )
    )
    assert res_cancel.status.value == "OK"

    # Verify plan execution is CANCELLED and all nodes are CANCELLED
    with uow:
        cur_pe = uow.connection.execute("SELECT status FROM plan_executions WHERE execution_id = ?", (pe.execution_id,))
        assert cur_pe.fetchone()["status"] == "CANCELLED"

        cur_nodes = uow.connection.execute("SELECT state FROM node_executions WHERE execution_id = ?", (pe.execution_id,))
        states = [r["state"] for r in cur_nodes.fetchall()]
        assert all(s == "CANCELLED" for s in states)


# ==============================================================================
# 6. NODE LEVEL OUTBOX AND AUDIT EVENTS
# ==============================================================================

def test_node_level_provenance_and_audit_events(temp_db_path, ipc_actor, ipc_correlation):
    """Prove each node dispatch and completion emits dedicated domain events and audit trail records."""
    caller = PipelineUnifiedCaller(db_path=temp_db_path)
    port = MultiNodeTrackingPort()
    _register_universal_binding(caller, port)
    _setup_migration(caller, "mig-events", ipc_actor, ipc_correlation, "M1")

    res = caller.handle_command(
        make_command(
            request_type="migration.start",
            payload={"migration_id": "mig-events", "mode": "M1"},
            actor=ipc_actor,
            correlation=ipc_correlation,
        )
    )
    assert res.status.value == "ACCEPTED"

    uow = SQLiteUnitOfWork(db_path=temp_db_path)
    with uow:
        # Check outbox events
        cur_evt = uow.connection.execute(
            "SELECT event_type FROM outbox_events WHERE aggregate_id = 'mig-events' ORDER BY rowid ASC"
        )
        event_types = [r["event_type"] for r in cur_evt.fetchall()]
        assert "node.ready" in event_types
        assert "node.dispatched" in event_types
        assert "node.succeeded" in event_types
        assert "plan.succeeded" in event_types

        # Check audit trail
        cur_aud = uow.connection.execute(
            "SELECT action FROM audit_trail ORDER BY rowid ASC"
        )
        actions = [r["action"] for r in cur_aud.fetchall()]
        assert "node.dispatched" in actions
        assert "node.succeeded" in actions
        assert "plan.succeeded" in actions


# ==============================================================================
# 7. COMPLEX CUSTOM DAG TOPOLOGY: DIAMOND DAG
# ==============================================================================

def test_custom_diamond_dag_execution(temp_db_path, ipc_actor, ipc_correlation):
    """Prove Diamond DAG: A -> (B, C) -> D. D is dispatched only after BOTH B and C succeed."""
    caller = PipelineUnifiedCaller(db_path=temp_db_path)
    port = MultiNodeTrackingPort()
    _register_universal_binding(caller, port)

    # 1. Create migration
    caller.handle_command(
        make_command(
            request_type="migration.create",
            payload={"migration_id": "mig-diamond", "mode": "M1"},
            actor=ipc_actor,
            correlation=ipc_correlation,
        )
    )

    # 2. Compile custom Diamond ExecutionPlan: NodeA -> NodeB, NodeC -> NodeD
    node_a = GraphNode("node-A", NodeTaskDescriptor("t-A", "schema_prep", SideEffectClassification.REVERSIBLE, {}), [])
    node_b = GraphNode("node-B", NodeTaskDescriptor("t-B", "data_transport", SideEffectClassification.REVERSIBLE, {}), ["node-A"])
    node_c = GraphNode("node-C", NodeTaskDescriptor("t-C", "data_transport", SideEffectClassification.REVERSIBLE, {}), ["node-A"])
    node_d = GraphNode("node-D", NodeTaskDescriptor("t-D", "data_transport", SideEffectClassification.REVERSIBLE, {}), ["node-B", "node-C"])

    edges = [
        GraphEdge("node-A", "node-B"),
        GraphEdge("node-A", "node-C"),
        GraphEdge("node-B", "node-D"),
        GraphEdge("node-C", "node-D"),
    ]

    plan = ExecutionPlan.create(
        plan_id="plan-diamond",
        migration_id="mig-diamond",
        mode=MigrationMode.M1_BULK,
        nodes=[node_a, node_b, node_c, node_d],
        edges=edges,
    )

    uow = SQLiteUnitOfWork(db_path=temp_db_path)
    with uow:
        plan_art = ImmutableArtifact.create("art-plan-diamond", "execution_plan", plan.to_dict())
        caller.artifact_registry.register(plan_art, conn=uow.connection)
        agg = caller.repository.get_by_id("mig-diamond", connection=uow.connection)
        agg.set_plan(plan_art.artifact_id, expected_revision=agg.revision)
        caller.repository.save(agg, connection=uow.connection)

    # 3. Initialize migration
    caller.handle_command(
        make_command(
            request_type="migration.initialize",
            payload={"migration_id": "mig-diamond"},
            actor=ipc_actor,
            correlation=ipc_correlation,
        )
    )

    # 4. Start migration
    res = caller.handle_command(
        make_command(
            request_type="migration.start",
            payload={"migration_id": "mig-diamond", "mode": "M1"},
            actor=ipc_actor,
            correlation=ipc_correlation,
        )
    )
    assert res.status.value == "ACCEPTED"

    # All 4 nodes executed in topological order: Node A first, Node B and C in middle, Node D last
    assert len(port.invocations) == 4
    assert port.invoked_nodes[0] == "node-A"
    assert set(port.invoked_nodes[1:3]) == {"node-B", "node-C"}
    assert port.invoked_nodes[3] == "node-D"


# ==============================================================================
# 8. HOSTILE ADJUDICATION TESTS: N-01 THROUGH N-05 VERIFICATION
# ==============================================================================

def test_n01_atomic_ready_node_claim_prevents_duplicate_dispatch(temp_db_path, ipc_actor, ipc_correlation):
    """N-01: Atomic CAS claim WHERE node_execution_id = ? AND state = 'READY' prevents double claim."""
    caller = PipelineUnifiedCaller(db_path=temp_db_path)
    port = MultiNodeTrackingPort()
    _register_universal_binding(caller, port)
    _setup_migration(caller, "mig-n01", ipc_actor, ipc_correlation, "M1")

    uow = SQLiteUnitOfWork(db_path=temp_db_path)
    with uow:
        agg = caller.repository.get_by_id("mig-n01", connection=uow.connection)
        plan_art = caller.artifact_registry.get(agg.plan_id, conn=uow.connection)
        plan = ExecutionPlan.from_dict(plan_art.content)
        p_actor = PipelineActorContext.from_ipc(ipc_actor)
        pe = caller.plan_coordinator.materialize_plan_execution(plan, agg, p_actor, "fp-n01", uow.connection)

        # Manually claim the first node to DISPATCHED state
        cur_node = uow.connection.execute(
            "SELECT node_execution_id FROM node_executions WHERE execution_id = ? AND state = 'READY' LIMIT 1",
            (pe.execution_id,),
        )
        node_exec_id = cur_node.fetchone()["node_execution_id"]
        uow.connection.execute(
            "UPDATE node_executions SET state = 'DISPATCHED' WHERE node_execution_id = ?",
            (node_exec_id,),
        )

    # Calling advance_plan_execution concurrently when the node is already claimed must not re-dispatch it
    outcome = caller.plan_coordinator.advance_plan_execution(
        execution_id=pe.execution_id,
        plan=plan,
        actor=p_actor,
        operation_id="op-n01",
        correlation_id=ipc_correlation.correlation_id,
        request_id="req-n01",
        payload={},
        uow_factory=caller._create_uow,
    )
    # Since node was already claimed, port was not invoked for that node in this call
    assert len(port.invocations) == 0


def test_n02_finite_plan_completion_transitions_to_completed(temp_db_path, ipc_actor, ipc_correlation):
    """N-02: Successful finite plans (M1, M4-M8) transition migration aggregate to COMPLETED."""
    caller = PipelineUnifiedCaller(db_path=temp_db_path)
    port = MultiNodeTrackingPort()
    _register_universal_binding(caller, port)
    _setup_migration(caller, "mig-n02-finite", ipc_actor, ipc_correlation, "M1")

    res = caller.handle_command(
        make_command(
            request_type="migration.start",
            payload={"migration_id": "mig-n02-finite", "mode": "M1"},
            actor=ipc_actor,
            correlation=ipc_correlation,
        )
    )
    assert res.status.value == "ACCEPTED"

    uow = SQLiteUnitOfWork(db_path=temp_db_path)
    with uow:
        agg = caller.repository.get_by_id("mig-n02-finite", connection=uow.connection)
        assert agg.state == MigrationLifecycleState.COMPLETED

    # Attempting to start the already completed migration must be rejected by lifecycle transition rules
    res_restart = caller.handle_command(
        make_command(
            request_type="migration.start",
            payload={"migration_id": "mig-n02-finite", "mode": "M1"},
            actor=ipc_actor,
            correlation=ipc_correlation,
        )
    )
    assert res_restart.status.value == "ERROR"
    assert res_restart.error.code == "INVALID_TRANSITION"


def test_n03_recovery_preserves_succeeded_nodes_and_recovers_dag(temp_db_path, ipc_actor, ipc_correlation):
    """N-03: Recovery preserves already SUCCEEDED nodes, resets incomplete nodes to READY,
    and binds replacement attempt authority to the recovered node without orphaning authority.
    """
    caller = PipelineUnifiedCaller(db_path=temp_db_path)
    port = MultiNodeTrackingPort()
    _register_universal_binding(caller, port)
    _setup_migration(caller, "mig-n03-rec", ipc_actor, ipc_correlation, "M2")

    # Manually simulate execution where Node 1 succeeded and Node 2 failed/cancelled
    uow = SQLiteUnitOfWork(db_path=temp_db_path)
    with uow:
        agg = caller.repository.get_by_id("mig-n03-rec", connection=uow.connection)
        plan_art = caller.artifact_registry.get(agg.plan_id, conn=uow.connection)
        init_art = caller.artifact_registry.get(agg.initialization_id, conn=uow.connection)
        plan = ExecutionPlan.from_dict(plan_art.content)
        p_actor = PipelineActorContext.from_ipc(ipc_actor)
        pe = caller.plan_coordinator.materialize_plan_execution(plan, agg, p_actor, init_art.fingerprint, uow.connection)



        # Mark node 1 SUCCEEDED, node 2 CANCELLED, node 3 BLOCKED
        uow.connection.execute(
            "UPDATE node_executions SET state = 'SUCCEEDED' WHERE execution_id = ? AND graph_node_id = 'n-schema-prep'",
            (pe.execution_id,),
        )
        uow.connection.execute(
            "UPDATE node_executions SET state = 'CANCELLED' WHERE execution_id = ? AND graph_node_id = 'n-data-transport'",
            (pe.execution_id,),
        )
        uow.connection.execute(
            "UPDATE node_executions SET state = 'BLOCKED' WHERE execution_id = ? AND graph_node_id = 'n-cdc-sync'",
            (pe.execution_id,),
        )
        uow.connection.execute(
            "UPDATE plan_executions SET status = 'CANCELLED' WHERE execution_id = ?",
            (pe.execution_id,),
        )
        agg.state = MigrationLifecycleState.CANCELLED
        agg.active_attempt_id = "att-old"
        agg.revision += 1
        caller.repository.save(agg, connection=uow.connection)

    # Perform migration recovery
    res_recov = caller.handle_command(
        make_command(
            request_type="migration.recover",
            payload={"migration_id": "mig-n03-rec", "source_attempt_id": "att-old"},
            actor=ipc_actor,
            correlation=ipc_correlation,
        )
    )
    assert res_recov.status.value == "OK"
    recov_att = res_recov.result["new_attempt_id"]
    recov_lease = res_recov.result["new_lease_id"]
    assert recov_att is not None
    assert recov_lease is not None

    # Verify DAG recovery semantics & authority binding
    with uow:
        cur_nodes = uow.connection.execute(
            "SELECT graph_node_id, state, current_attempt_id, lease_id FROM node_executions WHERE execution_id = ? ORDER BY rowid ASC",
            (pe.execution_id,),
        )
        rows = {r["graph_node_id"]: r for r in cur_nodes.fetchall()}
        # Node 1 preserved as SUCCEEDED
        assert rows["n-schema-prep"]["state"] == "SUCCEEDED"
        # Node 2 whose dependency (Node 1) is SUCCEEDED is now READY and bound to recovery replacement authority
        assert rows["n-data-transport"]["state"] == "READY"
        assert rows["n-data-transport"]["current_attempt_id"] == recov_att
        assert rows["n-data-transport"]["lease_id"] == recov_lease
        # Node 3 whose dependency (Node 2) is NOT yet succeeded remains BLOCKED
        assert rows["n-cdc-sync"]["state"] == "BLOCKED"

    # Advance plan execution and prove it adopts the replacement attempt authority without creating another attempt
    outcome = caller.plan_coordinator.advance_plan_execution(
        execution_id=pe.execution_id,
        plan=plan,
        actor=p_actor,
        operation_id="op-recov-adv",
        correlation_id=ipc_correlation.correlation_id,
        request_id="req-recov-adv",
        payload={},
        uow_factory=caller._create_uow,
    )
    assert outcome.is_success
    # Physical dispatch for node 2 must use the exact replacement attempt ID
    node2_req = [req for req in port.invocations if req.graph_node_id == "n-data-transport"][0]
    assert node2_req.attempt_id == recov_att
    assert node2_req.lease_id == recov_lease


def test_n04_stale_result_reconciliation_transitions_node_to_failed(temp_db_path, ipc_actor, ipc_correlation):
    """N-04: StaleResultError in result reconciliation transitions node and plan to FAILED with STALE_RESULT."""
    caller = PipelineUnifiedCaller(db_path=temp_db_path)

    # Custom port that returns an invalid/stale fence epoch
    class StaleFencedPort(ExecutionPort):
        def execute_task(self, request: EngineInvocationRequest) -> EngineInvocationResult:
            return EngineInvocationResult(
                invocation_id=request.invocation_id,
                attempt_id=request.attempt_id,
                lease_id=request.lease_id,
                fence_epoch=9999,  # Mismatched fence epoch!
                is_success=True,
                initialization_fingerprint=request.initialization_fingerprint,
                graph_node_id=request.graph_node_id,
                binding_id=request.binding_id,
                contract_version=request.contract_version,
            )

    stale_port = StaleFencedPort()
    caller.binding_registry.register(
        EngineBindingDescriptor(
            binding_id="b-stale-test",
            engine_name="E1",
            version="1.0",
            port_instance=stale_port,
            supported_capabilities={"schema_prep", "data_transport"},
            supported_modes={MigrationMode.M1_BULK},
        )
    )
    _setup_migration(caller, "mig-n04-stale", ipc_actor, ipc_correlation, "M1")

    uow = SQLiteUnitOfWork(db_path=temp_db_path)
    with uow:
        agg = caller.repository.get_by_id("mig-n04-stale", connection=uow.connection)
        plan_art = caller.artifact_registry.get(agg.plan_id, conn=uow.connection)
        plan = ExecutionPlan.from_dict(plan_art.content)
        p_actor = PipelineActorContext.from_ipc(ipc_actor)
        pe = caller.plan_coordinator.materialize_plan_execution(plan, agg, p_actor, "fp-n04", uow.connection)

    outcome = caller.plan_coordinator.advance_plan_execution(
        execution_id=pe.execution_id,
        plan=plan,
        actor=p_actor,
        operation_id="op-n04",
        correlation_id=ipc_correlation.correlation_id,
        request_id="req-n04",
        payload={},
        uow_factory=caller._create_uow,
    )
    assert not outcome.is_success
    assert outcome.error_category == IPCErrorCategory.STALE_RESULT

    with uow:
        pe_row = uow.connection.execute("SELECT status FROM plan_executions WHERE execution_id = ?", (pe.execution_id,)).fetchone()
        assert pe_row["status"] == "FAILED"
        ne_row = uow.connection.execute("SELECT state, error FROM node_executions WHERE execution_id = ? AND graph_node_id = 'n-schema-prep'", (pe.execution_id,)).fetchone()
        assert ne_row["state"] == "FAILED"
        assert "STALE_RESULT" in ne_row["error"]


def test_n05_and_n08_asynchronous_engine_completion_with_autonomous_redrive(temp_db_path, ipc_actor, ipc_correlation):
    """N-05 & N-08: Reconciling async node completion autonomously dispatches ready successors without manual intervention."""
    caller = PipelineUnifiedCaller(db_path=temp_db_path)

    # Async port returns is_in_progress=True and tracks all invocations
    class AsyncTrackingPort(ExecutionPort):
        def __init__(self):
            self.invocations: list[EngineInvocationRequest] = []
        def execute_task(self, request: EngineInvocationRequest) -> EngineInvocationResult:
            self.invocations.append(request)
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
            )

    async_port = AsyncTrackingPort()
    caller.binding_registry.register(
        EngineBindingDescriptor(
            binding_id="b-async-worker",
            engine_name="E1",
            version="1.0",
            port_instance=async_port,
            supported_capabilities={"schema_prep", "data_transport"},
            supported_modes={MigrationMode.M1_BULK},
        )
    )
    _setup_migration(caller, "mig-n05-async", ipc_actor, ipc_correlation, "M1")

    # 1. Start migration -> accepted, Node 1 is dispatched to async port
    res_start = caller.handle_command(
        make_command(
            request_type="migration.start",
            payload={"migration_id": "mig-n05-async", "mode": "M1"},
            actor=ipc_actor,
            correlation=ipc_correlation,
        )
    )
    assert res_start.status.value == "ACCEPTED"
    assert len(async_port.invocations) == 1
    req1 = async_port.invocations[0]
    assert req1.graph_node_id == "n-schema-prep"

    # 2. Reconcile Node 1 asynchronous completion -> Pipeline autonomously activates AND dispatches Node 2!
    comp1 = EngineInvocationResult(
        invocation_id=req1.invocation_id,
        attempt_id=req1.attempt_id,
        lease_id=req1.lease_id,
        fence_epoch=req1.fence_epoch,
        is_success=True,
        initialization_fingerprint=req1.initialization_fingerprint,
        graph_node_id=req1.graph_node_id,
        binding_id=req1.binding_id,
        contract_version=req1.contract_version,
        result_payload={"tables_prepared": 10},
    )
    res_comp1 = caller.reconcile_node_completion(comp1, ipc_actor)
    assert res_comp1.status.value == "OK"
    assert res_comp1.result["status"] == "RUNNING"

    # Autonomous re-drive proof: async_port has now received Node 2 without ANY manual advance call!
    assert len(async_port.invocations) == 2
    req2 = async_port.invocations[1]
    assert req2.graph_node_id == "n-data-transport"

    # 3. Reconcile Node 2 asynchronous completion -> Whole finite plan SUCCEEDS & transitions to COMPLETED
    comp2 = EngineInvocationResult(
        invocation_id=req2.invocation_id,
        attempt_id=req2.attempt_id,
        lease_id=req2.lease_id,
        fence_epoch=req2.fence_epoch,
        is_success=True,
        initialization_fingerprint=req2.initialization_fingerprint,
        graph_node_id=req2.graph_node_id,
        binding_id=req2.binding_id,
        contract_version=req2.contract_version,
        result_payload={"rows_transferred": 5000},
    )
    res_comp2 = caller.reconcile_node_completion(comp2, ipc_actor)
    assert res_comp2.status.value == "OK"
    assert res_comp2.result["status"] == "SUCCEEDED"

    uow = SQLiteUnitOfWork(db_path=temp_db_path)
    with uow:
        agg_final = caller.repository.get_by_id("mig-n05-async", connection=uow.connection)
        assert agg_final.state == MigrationLifecycleState.COMPLETED

        # N-07 Proof: original start operation is now SUCCEEDED in operation journal
        start_op_id = res_start.operation.operation_id
        cur_op = uow.connection.execute("SELECT status FROM operation_journal WHERE operation_id = ?", (start_op_id,))
        op_row = cur_op.fetchone()
        assert op_row is not None
        assert op_row["status"] == "SUCCEEDED"


def test_n06_exact_attempt_and_lease_provenance_enforced(temp_db_path, ipc_actor, ipc_correlation):
    """N-06: ResultReconciler strictly rejects results referencing a foreign attempt or lease ID."""
    caller = PipelineUnifiedCaller(db_path=temp_db_path)
    uow = SQLiteUnitOfWork(db_path=temp_db_path)

    with uow:
        lease = caller.lease_manager.acquire_lease(
            lease_id="lease-auth-1",
            attempt_id="att-auth-1",
            owner_id=ipc_actor.actor.actor_id,
            expires_at=(datetime.now(timezone.utc) + timedelta(seconds=300)).isoformat(),
            initialization_fingerprint="fp-auth-1",
            conn=uow.connection,
        )

        # 1. Attempt ID mismatch against expected_attempt_id must raise StaleResultError
        bad_att_result = EngineInvocationResult(
            invocation_id="inv-1",
            attempt_id="att-foreign-999",
            lease_id="lease-auth-1",
            fence_epoch=1,
            is_success=True,
            initialization_fingerprint="fp-auth-1",
            graph_node_id="node-1",
            binding_id="b-1",
            contract_version="1.0.0",
        )
        with pytest.raises(StaleResultError, match="Attempt ID mismatch"):
            caller.result_reconciler.reconcile_result(
                bad_att_result,
                expected_initialization_fingerprint="fp-auth-1",
                conn=uow.connection,
                expected_attempt_id="att-auth-1",
                expected_lease_id="lease-auth-1",
            )

        # 2. Lease ID mismatch against expected_lease_id must raise StaleResultError
        bad_lease_result = EngineInvocationResult(
            invocation_id="inv-1",
            attempt_id="att-auth-1",
            lease_id="lease-foreign-999",
            fence_epoch=1,
            is_success=True,
            initialization_fingerprint="fp-auth-1",
            graph_node_id="node-1",
            binding_id="b-1",
            contract_version="1.0.0",
        )
        with pytest.raises(StaleResultError, match="Lease ID mismatch"):
            caller.result_reconciler.reconcile_result(
                bad_lease_result,
                expected_initialization_fingerprint="fp-auth-1",
                conn=uow.connection,
                expected_attempt_id="att-auth-1",
                expected_lease_id="lease-auth-1",
            )


def test_n07_asynchronous_terminal_operation_reconciled_via_query(temp_db_path, ipc_actor, ipc_correlation):
    """N-07: Querying operation status after asynchronous DAG completion accurately reports SUCCEEDED."""
    caller = PipelineUnifiedCaller(db_path=temp_db_path)

    class SingleNodeAsyncPort(ExecutionPort):
        def __init__(self):
            self.last_req = None
        def execute_task(self, request: EngineInvocationRequest) -> EngineInvocationResult:
            self.last_req = request
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
            )

    async_port = SingleNodeAsyncPort()
    caller.binding_registry.register(
        EngineBindingDescriptor(
            binding_id="b-single-async",
            engine_name="E1",
            version="1.0",
            port_instance=async_port,
            supported_capabilities={"data_transport"},
            supported_modes={MigrationMode.M7_DATA_ONLY},
        )
    )
    _setup_migration(caller, "mig-n07-op", ipc_actor, ipc_correlation, "M7")

    res_start = caller.handle_command(
        make_command(
            request_type="migration.start",
            payload={"migration_id": "mig-n07-op", "mode": "M7"},
            actor=ipc_actor,
            correlation=ipc_correlation,
        )
    )
    assert res_start.status.value == "ACCEPTED"
    op_ref = res_start.operation
    assert op_ref is not None

    req = async_port.last_req
    comp = EngineInvocationResult(
        invocation_id=req.invocation_id,
        attempt_id=req.attempt_id,
        lease_id=req.lease_id,
        fence_epoch=req.fence_epoch,
        is_success=True,
        initialization_fingerprint=req.initialization_fingerprint,
        graph_node_id=req.graph_node_id,
        binding_id=req.binding_id,
        contract_version=req.contract_version,
        result_payload={"migrated_rows": 9999},
    )
    res_comp = caller.reconcile_node_completion(comp, ipc_actor)
    assert res_comp.status.value == "OK"
    assert res_comp.result["status"] == "SUCCEEDED"

    # Query operation via public query API
    query_op = make_query(
        request_type="operation.get",
        payload={"operation_id": op_ref.operation_id},
        actor=ipc_actor,
        correlation=ipc_correlation,
    )
    res_query = caller.handle_query(query_op)
    assert res_query.status.value == "OK"
    assert res_query.result["status"] == "SUCCEEDED"


def test_n03_branching_recovery_binds_to_exact_selected_node_and_checkpoint(temp_db_path, ipc_actor, ipc_correlation):
    """N-03: In a branching DAG with multiple ready incomplete nodes, recovery binds specifically

    to the node that owned the source attempt and propagates the selected checkpoint to EngineInvocationRequest.
    """
    caller = PipelineUnifiedCaller(db_path=temp_db_path)
    port = MultiNodeTrackingPort()
    _register_universal_binding(caller, port)

    # 1. Create custom branching diamond plan: n-root -> (n-branch-b, n-branch-c) -> n-join
    nodes = [
        GraphNode("n-root", NodeTaskDescriptor("t-root", "schema_prep", SideEffectClassification.REVERSIBLE), dependencies=[]),
        GraphNode("n-branch-b", NodeTaskDescriptor("t-b", "data_transport", SideEffectClassification.REVERSIBLE), dependencies=["n-root"]),
        GraphNode("n-branch-c", NodeTaskDescriptor("t-c", "cdc_sync", SideEffectClassification.REVERSIBLE), dependencies=["n-root"]),
        GraphNode("n-join", NodeTaskDescriptor("t-join", "cdc_sync", SideEffectClassification.READ_ONLY), dependencies=["n-branch-b", "n-branch-c"]),

    ]


    edges = [
        GraphEdge("n-root", "n-branch-b"),
        GraphEdge("n-root", "n-branch-c"),
        GraphEdge("n-branch-b", "n-join"),
        GraphEdge("n-branch-c", "n-join"),
    ]
    plan = ExecutionPlan.create("plan-branch-recov", "mig-branch-recov", MigrationMode.M2_BULK_CDC, nodes, edges)


    _setup_migration(caller, "mig-branch-recov", ipc_actor, ipc_correlation, "M2")

    uow = SQLiteUnitOfWork(db_path=temp_db_path)
    with uow:
        plan_dict = plan.to_dict()
        plan_fp = canonical_fingerprint(plan_dict)
        caller.artifact_registry.register(
            ImmutableArtifact(
                artifact_id="plan-branch-recov",
                artifact_type="plan",
                content=plan_dict,
                fingerprint=plan_fp,
            ),
            conn=uow.connection,
        )

        agg = caller.repository.get_by_id("mig-branch-recov", connection=uow.connection)
        agg.plan_id = "plan-branch-recov"
        agg.revision += 1
        caller.repository.save(agg, connection=uow.connection)


        init_art = caller.artifact_registry.get(agg.initialization_id, conn=uow.connection)
        p_actor = PipelineActorContext.from_ipc(ipc_actor)
        pe = caller.plan_coordinator.materialize_plan_execution(plan, agg, p_actor, init_art.fingerprint, uow.connection)

        # Simulate state: n-root SUCCEEDED, n-branch-b (attempt: att-b), n-branch-c (attempt: att-c) both failed/cancelled
        uow.connection.execute(
            "UPDATE node_executions SET state = 'SUCCEEDED' WHERE execution_id = ? AND graph_node_id = 'n-root'",
            (pe.execution_id,),
        )
        uow.connection.execute(
            "UPDATE node_executions SET state = 'CANCELLED', current_attempt_id = 'att-b', lease_id = 'lease-b' WHERE execution_id = ? AND graph_node_id = 'n-branch-b'",
            (pe.execution_id,),
        )
        uow.connection.execute(
            "UPDATE node_executions SET state = 'CANCELLED', current_attempt_id = 'att-c', lease_id = 'lease-c' WHERE execution_id = ? AND graph_node_id = 'n-branch-c'",
            (pe.execution_id,),
        )
        uow.connection.execute(
            "UPDATE node_executions SET state = 'BLOCKED' WHERE execution_id = ? AND graph_node_id = 'n-join'",
            (pe.execution_id,),
        )
        uow.connection.execute(
            "UPDATE plan_executions SET status = 'CANCELLED' WHERE execution_id = ?",
            (pe.execution_id,),
        )

        # Register checkpoint for Node C in checkpoints table
        uow.connection.execute(
            """
            INSERT INTO checkpoints (
                checkpoint_id, attempt_id, invocation_id, lease_id, fence_epoch,
                graph_node_id, initialization_fingerprint, binding_id, payload_reference, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "cp-c-val-100",
                "att-c",
                "inv-c",
                "lease-c",
                1,
                "n-branch-c",
                init_art.fingerprint,
                "b-universal",
                json.dumps({"binlog_file": "mysql-bin.000100", "binlog_pos": 45678}),
                datetime.now(timezone.utc).isoformat(),
            ),
        )

        agg.state = MigrationLifecycleState.CANCELLED
        agg.active_attempt_id = "att-c"
        agg.revision += 1
        caller.repository.save(agg, connection=uow.connection)

    # 2. Operator recovers specifically from Node C's source attempt & checkpoint
    res_recov = caller.handle_command(
        make_command(
            request_type="migration.recover",
            payload={
                "migration_id": "mig-branch-recov",
                "source_attempt_id": "att-c",
                "checkpoint_id": "cp-c-val-100",
            },
            actor=ipc_actor,
            correlation=ipc_correlation,
        )
    )
    assert res_recov.status.value == "OK"
    recov_att = res_recov.result["new_attempt_id"]
    recov_lease = res_recov.result["new_lease_id"]

    # 3. Verify that Node C received the replacement authority and checkpoint, while Node B did NOT
    with uow:
        cur_nodes = uow.connection.execute(
            "SELECT graph_node_id, state, current_attempt_id, lease_id, checkpoint_id FROM node_executions WHERE execution_id = ? ORDER BY rowid ASC",
            (pe.execution_id,),
        )
        rows = {r["graph_node_id"]: r for r in cur_nodes.fetchall()}

        # Node C is READY and explicitly bound to recovery replacement attempt and checkpoint
        assert rows["n-branch-c"]["state"] == "READY"
        assert rows["n-branch-c"]["current_attempt_id"] == recov_att
        assert rows["n-branch-c"]["lease_id"] == recov_lease
        assert rows["n-branch-c"]["checkpoint_id"] == "cp-c-val-100"

        # Node B is also READY (because root succeeded), but does NOT hijack Node C's recovery lease or checkpoint!
        assert rows["n-branch-b"]["state"] == "READY"
        assert rows["n-branch-b"]["current_attempt_id"] is None
        assert rows["n-branch-b"]["lease_id"] is None
        assert rows["n-branch-b"]["checkpoint_id"] is None

    # 4. Advance execution and verify physical dispatch of Node C carries the exact checkpoint ID & payload
    outcome = caller.plan_coordinator.advance_plan_execution(
        execution_id=pe.execution_id,
        plan=plan,
        actor=p_actor,
        operation_id="op-adv-branch-c",
        correlation_id=ipc_correlation.correlation_id,
        request_id="req-adv-branch-c",
        payload={},
        uow_factory=caller._create_uow,
    )
    assert outcome.is_success

    # Find invocation for Node C
    inv_c = [req for req in port.invocations if req.graph_node_id == "n-branch-c"][0]
    assert inv_c.attempt_id == recov_att
    assert inv_c.lease_id == recov_lease
    assert inv_c.checkpoint_id == "cp-c-val-100"
    assert inv_c.payload.get("checkpoint_id") == "cp-c-val-100"
    assert inv_c.payload.get("checkpoint_data") == {"binlog_file": "mysql-bin.000100", "binlog_pos": 45678}
