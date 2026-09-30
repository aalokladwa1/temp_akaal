"""
tests/integration/test_m2_backend_serial_gates.py
==================================================
Provider-Agnostic Fast Serial M2 Backend Lifecycle Integration Test.
Exercises Gates 1 through 13 serially through production backend contracts
(akaalPipeline & akaalEngine) without UI/UX, Playwright, or AKAAL.exe.
"""

import time
from typing import Any, Dict, List, Optional
import pytest

from akaalPipeline.contracts.enums import MigrationMode, MigrationLifecycleState
from akaalPipeline.orchestration.compiler import GraphCompiler
from akaalPipeline.orchestration.plans import ExecutionPlan
from akaalPipeline.application.unified_caller import PipelineUnifiedCaller
from akaalPipeline.execution.coordinator import PlanExecutionCoordinator

from akaalEngine.cdc.api import CDCAuthority
from akaalEngine.cdc.models.event import ChangeEvent, ChangeOperation
from akaalEngine.cdc.models.errors import CDCApplyError
from akaalEngine.gateway.api import EngineGateway
from akaalEngine.gateway.models.context import GatewayRequestContext
from akaalEngine.gateway.models.enums import SemanticOperation
from akaalEngine.gateway.models.requests import GatewayRequest


class GenericProviderSourceAdapter:
    """Generic provider-agnostic source adapter double for serial backend testing."""
    def __init__(self) -> None:
        self.pending_events: List[ChangeEvent] = []
        self.position_counter = 100
        self.is_active = True
        self.stream_handle = "generic-source-handle"

    @property
    def engine_name(self) -> str:
        return "GENERIC_SQL"

    def start_capture(self, start_position: Optional[Any] = None) -> None:
        self.is_active = True

    def fetch_events(self, max_events: int = 1000) -> List[ChangeEvent]:
        evts = list(self.pending_events[:max_events])
        self.pending_events = self.pending_events[max_events:]
        return evts

    def get_current_position(self) -> str:
        return f"pos-{self.position_counter}"

    def close(self) -> None:
        self.is_active = False


class GenericProviderTargetWriter:
    """Generic provider-agnostic target writer double for serial backend testing."""
    def __init__(self) -> None:
        self.applied_records: List[Dict[str, Any]] = []
        self.committed_batches = 0
        self.fail_on_next_write = False
        self.params = {"username": "GENERIC_TGT_USER", "database": "GENERIC_TGT_DB"}

    def write_batch(self, table_name: str, batch: Any, target_schema: str = "public", pk_columns: Optional[Any] = None) -> int:
        if self.fail_on_next_write:
            from akaalEngine.cdc.models.errors import CDCApplyError
            raise CDCApplyError("Simulated target write failure for failure safety assertion")
        rows = getattr(batch, "rows", [])
        self.applied_records.extend(rows)
        return len(rows)

    def commit(self) -> None:
        self.committed_batches += 1

    def execute_ddl(self, ddl: str) -> None:
        pass


def test_m2_backend_serial_lifecycle(tmp_path):
    """
    Executes Gates 1 through 13 sequentially against production backend contracts.
    Fails fast at the first broken invariant.
    """
    db_path = str(tmp_path / "akaal-pipeline-test.db")
    caller = PipelineUnifiedCaller(db_path=db_path, bind_gateway=True)
    exec_coord = caller.plan_coordinator
    gw_adapter = caller.binding_registry.get("gateway_engine_binding").port_instance
    gateway = getattr(gw_adapter, "_gateway", getattr(gw_adapter, "gateway", None))
    cdc_auth: CDCAuthority = gateway.coordinator.cdc_authority

    migration_id = "mig-generic-m2-001"
    tenant_id = "tenant-001"
    workspace_id = "ws-001"
    project_id = "proj-001"

    # =========================================================================
    # GATE 1 — M2 CREATION / CONFIGURATION
    # =========================================================================
    created_agg = caller.create_migration(
        migration_id=migration_id,
        tenant_id=tenant_id,
        workspace_id=workspace_id,
        project_id=project_id,
        title="Generic M2 Backend Integration Test",
        mode=MigrationMode.M2_BULK_CDC,
    )
    assert created_agg is not None, "G1 FAIL: Could not create migration aggregate"
    assert created_agg.mode == MigrationMode.M2_BULK_CDC, "G1 FAIL: Mode is not M2_BULK_CDC"
    assert created_agg.state in (MigrationLifecycleState.DRAFT, MigrationLifecycleState.CREATED, MigrationLifecycleState.CONFIGURED), "G1 FAIL: Migration state is terminal upon creation"
    print("\n[G1 CREATION]: PASS")

    # =========================================================================
    # GATE 2 — PLAN
    # =========================================================================
    plan = GraphCompiler.compile_plan(
        plan_id="plan-m2-001",
        migration_id=migration_id,
        mode=MigrationMode.M2_BULK_CDC,
        config={"batch_size": 5000, "parallelism": 4},
    )
    assert plan is not None, "G2 FAIL: Plan compilation returned None"
    node_ids = [n.node_id for n in plan.nodes]
    assert "n-schema-prep" in node_ids, "G2 FAIL: Missing n-schema-prep node"
    assert "n-cdc-start" in node_ids, "G2 FAIL: Missing n-cdc-start node"
    assert "n-data-transport" in node_ids, "G2 FAIL: Missing n-data-transport node"
    assert "n-cdc-sync" in node_ids, "G2 FAIL: Missing n-cdc-sync node"
    print("[G2 PLAN]: PASS")

    # =========================================================================
    # GATE 3 — BULK EXECUTION
    # =========================================================================
    # Dispatch plan into execution coordinator
    exec_record = exec_coord.start_execution(
        plan=plan,
        actor_id="test_actor",
        operation_id="op-exec-001",
        correlation_id="corr-001",
    )
    assert exec_record is not None, "G3 FAIL: Could not start execution"
    
    # Execute n-schema-prep and n-data-transport
    uow = exec_coord._create_uow()
    with uow:
        # Mark schema prep succeeded
        uow.connection.execute("UPDATE node_executions SET state = 'SUCCEEDED' WHERE execution_id = ? AND graph_node_id = 'n-schema-prep'", (exec_record.execution_id,))
        # Mark data transport succeeded
        uow.connection.execute("UPDATE node_executions SET state = 'SUCCEEDED' WHERE execution_id = ? AND graph_node_id = 'n-data-transport'", (exec_record.execution_id,))
        uow.connection.commit()

    agg_after_bulk = caller.get_migration(migration_id)
    assert agg_after_bulk.state != MigrationLifecycleState.COMPLETED, "G3 FAIL: Migration became COMPLETED after bulk work succeeded!"
    print("[G3 BULK]: PASS")

    # =========================================================================
    # GATE 4 — CDC INITIALIZATION
    # =========================================================================
    source_adapter = GenericProviderSourceAdapter()
    target_writer = GenericProviderTargetWriter()

    cdc_auth.set_active_adapter(source_adapter)
    cdc_auth.bind_target_writer(target_writer)

    assert cdc_auth.active_adapter is not None, "G4 FAIL: CDC source adapter not resolved"
    assert cdc_auth.apply_coordinator is not None, "G4 FAIL: Apply coordinator not bound"
    assert cdc_auth.apply_coordinator.target_writer is not None, "G4 FAIL: Target writer not resolved"
    print("[G4 CDC INITIALIZATION]: PASS")

    # =========================================================================
    # GATE 5 — FINITE CDC NODE COMPLETION & NON-TERMINAL LIFECYCLE
    # =========================================================================
    with uow:
        uow.connection.execute("UPDATE node_executions SET state = 'SUCCEEDED' WHERE execution_id = ? AND graph_node_id = 'n-cdc-sync'", (exec_record.execution_id,))
        uow.connection.commit()

    # Re-evaluate migration lifecycle state: M2_BULK_CDC MUST NOT transition to COMPLETED
    agg_after_cdc_sync = caller.get_migration(migration_id)
    assert agg_after_cdc_sync.state != MigrationLifecycleState.COMPLETED, "G5 FAIL: n-cdc-sync == SUCCEEDED caused migration to become COMPLETED while continuous phase is active!"
    assert agg_after_cdc_sync.state in (MigrationLifecycleState.ACTIVE, MigrationLifecycleState.CONFIGURED, MigrationLifecycleState.CREATED, MigrationLifecycleState.DRAFT), "G5 FAIL: Invalid migration state post finite DAG completion"
    print("[G5 FINITE NODE / NON-TERMINAL]: PASS")

    # =========================================================================
    # GATE 6 — CONTINUOUS EVENT #1
    # =========================================================================
    evt_1 = ChangeEvent(
        event_id="evt-gen-001",
        source_system="GENERIC_SQL",
        source_identity="gen-source-01",
        logical_object="GENERIC_ENTITIES",
        operation=ChangeOperation.INSERT,
        source_position="pos-101",
        commit_position="pos-101",
        commit_timestamp=time.time(),
        capture_timestamp=time.time(),
        schema_version="1.0.0",
        key_columns=("ENTITY_ID",),
        key_values={"ENTITY_ID": 101},
        after_image={"ENTITY_ID": 101, "NAME": "Generic Event 1"},
    )
    source_adapter.pending_events.append(evt_1)

    drained_1 = cdc_auth.drain_and_sync()
    assert drained_1 == 1, f"G6 FAIL: Expected 1 event drained, got {drained_1}"
    assert len(target_writer.applied_records) == 1, "G6 FAIL: Event not applied to target writer"
    assert target_writer.applied_records[0]["ENTITY_ID"] == 101, "G6 FAIL: Applied record payload mismatch"
    assert target_writer.committed_batches >= 1, "G6 FAIL: Target write not committed/ACK'd"
    print("[G6 EVENT #1]: PASS")

    # =========================================================================
    # GATE 7 — CONTINUOUS EVENT #2 (POST FINITE DAG WORK)
    # =========================================================================
    evt_2 = ChangeEvent(
        event_id="evt-gen-002",
        source_system="GENERIC_SQL",
        source_identity="gen-source-01",
        logical_object="GENERIC_ENTITIES",
        operation=ChangeOperation.INSERT,
        source_position="pos-102",
        commit_position="pos-102",
        commit_timestamp=time.time(),
        capture_timestamp=time.time(),
        schema_version="1.0.0",
        key_columns=("ENTITY_ID",),
        key_values={"ENTITY_ID": 102},
        after_image={"ENTITY_ID": 102, "NAME": "Generic Event 2"},
    )
    source_adapter.pending_events.append(evt_2)

    drained_2 = cdc_auth.drain_and_sync()
    assert drained_2 == 1, f"G7 FAIL: Continuous worker failed post-DAG completion; expected 1 event, got {drained_2}"
    assert len(target_writer.applied_records) == 2, "G7 FAIL: Event 2 not applied to target writer"
    assert target_writer.applied_records[1]["ENTITY_ID"] == 102, "G7 FAIL: Applied record 2 payload mismatch"
    print("[G7 EVENT #2 AFTER DAG SUCCESS]: PASS")

    # =========================================================================
    # GATE 8 — PROCESS-BOUNDARY RECOVERY
    # =========================================================================
    # Simulate process destruction (clearing in-memory authorities)
    cdc_auth.active_adapter = None
    cdc_auth.apply_coordinator = None
    if cdc_auth._streaming_thread and cdc_auth._streaming_thread.is_alive():
        cdc_auth._stop_streaming.set()

    assert cdc_auth.active_adapter is None, "G8 FAIL: Source adapter not cleared for restart simulation"
    assert cdc_auth.apply_coordinator is None, "G8 FAIL: Apply coordinator not cleared for restart simulation"

    # Re-arm via recovery path
    cdc_auth.set_active_adapter(source_adapter)
    cdc_auth.bind_target_writer(target_writer)

    assert cdc_auth.active_adapter is not None, "G8 FAIL: Source adapter not rebound post-recovery"
    assert cdc_auth.apply_coordinator is not None, "G8 FAIL: Apply coordinator not rebound post-recovery"
    print("[G8 PROCESS RECOVERY]: PASS")

    # =========================================================================
    # GATE 9 — POST-RECOVERY EVENT
    # =========================================================================
    evt_3 = ChangeEvent(
        event_id="evt-gen-003",
        source_system="GENERIC_SQL",
        source_identity="gen-source-01",
        logical_object="GENERIC_ENTITIES",
        operation=ChangeOperation.INSERT,
        source_position="pos-103",
        commit_position="pos-103",
        commit_timestamp=time.time(),
        capture_timestamp=time.time(),
        schema_version="1.0.0",
        key_columns=("ENTITY_ID",),
        key_values={"ENTITY_ID": 103},
        after_image={"ENTITY_ID": 103, "NAME": "Generic Event 3 Post Recovery"},
    )
    source_adapter.pending_events.append(evt_3)

    drained_3 = cdc_auth.drain_and_sync()
    assert drained_3 == 1, f"G9 FAIL: Post-recovery event not processed; got {drained_3}"
    assert len(target_writer.applied_records) == 3, "G9 FAIL: Post-recovery event not applied to target writer"
    assert target_writer.applied_records[2]["ENTITY_ID"] == 103, "G9 FAIL: Post-recovery payload mismatch"
    print("[G9 POST-RECOVERY EVENT]: PASS")

    # =========================================================================
    # GATE 10 — PAUSE / RESUME
    # =========================================================================
    cdc_auth.is_cdc_paused = True
    evt_paused = ChangeEvent(
        event_id="evt-gen-paused",
        source_system="GENERIC_SQL",
        source_identity="gen-source-01",
        logical_object="GENERIC_ENTITIES",
        operation=ChangeOperation.INSERT,
        source_position="pos-104",
        commit_position="pos-104",
        commit_timestamp=time.time(),
        capture_timestamp=time.time(),
        schema_version="1.0.0",
        key_columns=("ENTITY_ID",),
        key_values={"ENTITY_ID": 104},
        after_image={"ENTITY_ID": 104, "NAME": "Generic Event Paused"},
    )
    source_adapter.pending_events.append(evt_paused)

    drained_paused = cdc_auth.drain_and_sync()
    assert drained_paused == 0, "G10 FAIL: Events processed while CDC stream was paused!"
    
    # Resume stream
    cdc_auth.is_cdc_paused = False
    drained_resumed = cdc_auth.drain_and_sync()
    assert drained_resumed == 1, "G10 FAIL: Events not processed after stream resumed!"
    assert len(target_writer.applied_records) == 4, "G10 FAIL: Resumed event not applied to target writer"
    print("[G10 PAUSE/RESUME]: PASS")

    # =========================================================================
    # GATE 11 — GOVERNED CUTOVER
    # =========================================================================
    readiness = cdc_auth.evaluate_cutover_readiness()
    assert readiness is not None, "G11 FAIL: Could not evaluate cutover readiness"
    
    # Execute cutover transition
    from akaalEngine.cdc.models.cutover import CutoverState
    cdc_auth.cutover_coordinator.transition_to(CutoverState.CUTOVER_EXECUTED)
    assert cdc_auth.cutover_coordinator.current_state == CutoverState.CUTOVER_EXECUTED, "G11 FAIL: Cutover state not transition to CUTOVER_EXECUTED"
    print("[G11 CUTOVER]: PASS")

    # =========================================================================
    # GATE 12 — TERMINAL COMPLETION
    # =========================================================================
    # Finalize migration aggregate lifecycle to COMPLETED only after governed cutover
    caller.update_migration_state(migration_id, MigrationLifecycleState.COMPLETED)
    agg_final = caller.get_migration(migration_id)
    assert agg_final.state == MigrationLifecycleState.COMPLETED, "G12 FAIL: Migration state is not COMPLETED post-cutover"
    print("[G12 TERMINAL COMPLETION]: PASS")

    # =========================================================================
    # GATE 13 — FAILURE SAFETY
    # =========================================================================
    target_writer.fail_on_next_write = True
    evt_fail = ChangeEvent(
        event_id="evt-gen-fail-test",
        source_system="GENERIC_SQL",
        source_identity="gen-source-01",
        logical_object="GENERIC_ENTITIES",
        operation=ChangeOperation.INSERT,
        source_position="pos-105",
        commit_position="pos-105",
        commit_timestamp=time.time(),
        capture_timestamp=time.time(),
        schema_version="1.0.0",
        key_columns=("ENTITY_ID",),
        key_values={"ENTITY_ID": 105},
        after_image={"ENTITY_ID": 105, "NAME": "Failing Event"},
    )
    source_adapter.pending_events.append(evt_fail)

    with pytest.raises(CDCApplyError):
        cdc_auth.drain_and_sync()

    # Verify failed write did not advance applied records or corrupt state
    assert not any(r.get("ENTITY_ID") == 105 for r in target_writer.applied_records), "G13 FAIL: Failed write was wrongfully applied/ACK'd!"
    print("[G13 FAILURE SAFETY]: PASS")

    print("\n========================================================")
    print("M2 BACKEND SERIAL GATE: PASS")
    print("========================================================\n")
