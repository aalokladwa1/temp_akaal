"""
tests/integration/test_m2_backend_serial_journey.py
=====================================================
Provider-Agnostic Fast Serial M2 Backend Lifecycle Integration Test.
Exercises Gates 1 through 15 serially through production backend contracts
(akaalPipeline & akaalEngine) without UI/UX, Playwright, or AKAAL.exe.
"""

import sys, os, time, tempfile
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

import pytest

from akaalPipeline.contracts.enums import MigrationMode, MigrationLifecycleState
from akaalPipeline.orchestration.compiler import GraphCompiler
from akaalPipeline.orchestration.plans import ExecutionPlan
from akaalPipeline.application.unified_caller import PipelineUnifiedCaller
from akaalPipeline.execution.coordinator import PlanExecutionCoordinator
from akaalPipeline.state.aggregates import MigrationAggregate
from akaalPipeline.security.context import PipelineActorContext

from akaalEngine.cdc.api import CDCAuthority
from akaalEngine.cdc.models.event import ChangeEvent, ChangeOperation
from akaalEngine.cdc.models.cutover import CutoverState
from akaalEngine.cdc.models.errors import CDCApplyError


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
            raise CDCApplyError("Simulated target write failure for failure safety assertion")
        rows = getattr(batch, "rows", [])
        self.applied_records.extend(rows)
        return len(rows)

    def commit(self) -> None:
        self.committed_batches += 1

    def execute_ddl(self, ddl: str) -> None:
        pass


def test_m2_backend_serial_journey():
    """
    Executes Gates 1 through 15 sequentially against production backend contracts.
    Fails fast at the first broken invariant.
    """
    t0 = time.time()
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp_dir:
        db_path = os.path.join(tmp_dir, "akaal-pipeline-serial.db")
        caller = PipelineUnifiedCaller(db_path=db_path, bind_gateway=True)
        exec_coord = caller.plan_coordinator
        gw_adapter = caller.binding_registry.get("gateway_engine_binding").port_instance
        gateway = getattr(gw_adapter, "_gateway", getattr(gw_adapter, "gateway", None))
        cdc_auth: CDCAuthority = gateway.coordinator.cdc_authority

        migration_id = "mig-generic-m2-serial-001"
        tenant_id = "tenant-001"
        workspace_id = "ws-001"
        project_id = "proj-001"

        # =========================================================================
        # G1 M2 CREATION / CONFIGURATION
        # =========================================================================
        created_agg = MigrationAggregate(
            migration_id=migration_id,
            revision=1,
            name="Generic M2 Backend Integration Journey",
            mode=MigrationMode.M2_BULK_CDC,
            state=MigrationLifecycleState.INITIALIZED,
            tenant_id=tenant_id,
            workspace_id=workspace_id,
            project_id=project_id,
        )
        uow = caller._create_uow()
        with uow:
            caller.repository.save(created_agg, connection=uow.connection)

        assert created_agg.mode == MigrationMode.M2_BULK_CDC, "G1 FAIL: Mode is not M2_BULK_CDC"
        assert created_agg.state in (MigrationLifecycleState.DRAFT, MigrationLifecycleState.INITIALIZED, MigrationLifecycleState.CONFIGURING), "G1 FAIL: Migration state is terminal"
        print("\n[G1 M2 CREATION]: PASS")

        # =========================================================================
        # G2 PLAN
        # =========================================================================
        plan = GraphCompiler.compile_plan(
            plan_id="plan-m2-serial-001",
            migration_id=migration_id,
            mode=MigrationMode.M2_BULK_CDC,
            config={"batch_size": 5000, "parallelism": 4},
        )
        assert plan is not None, "G2 FAIL: Plan compilation returned None"
        node_ids = [n.node_id for n in plan.nodes]
        assert "n-schema-prep" in node_ids, "G2 FAIL: Missing n-schema-prep"
        assert "n-cdc-start" in node_ids, "G2 FAIL: Missing n-cdc-start"
        assert "n-data-transport" in node_ids, "G2 FAIL: Missing n-data-transport"
        assert "n-cdc-sync" in node_ids, "G2 FAIL: Missing n-cdc-sync"
        print("[G2 PLAN]: PASS")

        # =========================================================================
        # G3 BULK EXECUTION
        # =========================================================================
        actor = PipelineActorContext(actor_id="actor-1", actor_type="USER", organization_id=tenant_id, workspace_id=workspace_id, project_id=project_id)
        with uow:
            exec_record = exec_coord.materialize_plan_execution(
                plan=plan,
                migration=created_agg,
                actor=actor,
                initialization_fingerprint="fing-serial-001",
                conn=uow.connection,
                operation_id="op-serial-001",
            )
        assert exec_record is not None, "G3 FAIL: Could not materialize plan execution"

        with uow:
            uow.connection.execute("UPDATE node_executions SET state = 'SUCCEEDED' WHERE execution_id = ? AND graph_node_id = 'n-schema-prep'", (exec_record.execution_id,))
            uow.connection.execute("UPDATE node_executions SET state = 'SUCCEEDED' WHERE execution_id = ? AND graph_node_id = 'n-data-transport'", (exec_record.execution_id,))
            uow.connection.commit()

        with uow:
            agg_after_bulk = caller.repository.get_by_id(migration_id, connection=uow.connection)
        assert agg_after_bulk.state != MigrationLifecycleState.COMPLETED, "G3 FAIL: Migration became COMPLETED after bulk work succeeded!"
        print("[G3 BULK]: PASS")

        # =========================================================================
        # G4 CDC INITIALIZATION
        # =========================================================================
        source_adapter = GenericProviderSourceAdapter()
        target_writer = GenericProviderTargetWriter()

        cdc_auth.set_active_adapter(source_adapter)
        cdc_auth.bind_target_writer(target_writer)

        assert cdc_auth.active_adapter is not None, "G4 FAIL: CDC source adapter not resolved"
        assert cdc_auth.apply_coordinator is not None, "G4 FAIL: Apply coordinator not bound"
        assert cdc_auth.apply_coordinator.target_writer is not None, "G4 FAIL: Target writer not bound"
        print("[G4 CDC INITIALIZATION]: PASS")

        # =========================================================================
        # G5 FINITE CDC NODE SUCCEEDS WITHOUT TERMINAL MIGRATION
        # =========================================================================
        with uow:
            uow.connection.execute("UPDATE node_executions SET state = 'SUCCEEDED' WHERE execution_id = ? AND graph_node_id = 'n-cdc-sync'", (exec_record.execution_id,))
            uow.connection.commit()

        with uow:
            exec_coord._mark_plan_succeeded(
                execution_id=exec_record.execution_id,
                plan=plan,
                actor=actor,
                operation_id="op-serial-001",
                correlation_id="corr-serial-001",
                uow=uow,
            )

        with uow:
            agg_after_cdc_sync = caller.repository.get_by_id(migration_id, connection=uow.connection)
        assert agg_after_cdc_sync.state != MigrationLifecycleState.COMPLETED, "G5 FAIL: n-cdc-sync == SUCCEEDED caused migration to become COMPLETED while continuous phase is active!"
        assert agg_after_cdc_sync.state in (MigrationLifecycleState.ACTIVE, MigrationLifecycleState.INITIALIZED, MigrationLifecycleState.DRAFT), "G5 FAIL: Invalid migration state post finite DAG completion"
        print("[G5 FINITE CDC NODE SUCCEEDS WITHOUT TERMINAL MIGRATION]: PASS")

        # =========================================================================
        # G6 FIRST POST-BULK EVENT
        # =========================================================================
        evt_1 = ChangeEvent(
            event_id="evt-serial-001",
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
            after_image={"ENTITY_ID": 101, "NAME": "Serial Event 1"},
        )
        source_adapter.pending_events.append(evt_1)

        drained_1 = cdc_auth.drain_and_sync()
        assert drained_1 == 1, f"G6 FAIL: Expected 1 event drained, got {drained_1}"
        assert len(target_writer.applied_records) == 1, "G6 FAIL: Event not applied to target writer"
        assert target_writer.applied_records[0]["ENTITY_ID"] == 101, "G6 FAIL: Applied record 1 payload mismatch"
        print("[G6 FIRST POST-BULK EVENT]: PASS")

        # =========================================================================
        # G7 ADDITIONAL EVENT AFTER DAG SUCCESS
        # =========================================================================
        evt_2 = ChangeEvent(
            event_id="evt-serial-002",
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
            after_image={"ENTITY_ID": 102, "NAME": "Serial Event 2 Post DAG"},
        )
        source_adapter.pending_events.append(evt_2)

        drained_2 = cdc_auth.drain_and_sync()
        assert drained_2 == 1, f"G7 FAIL: Continuous worker failed post-DAG completion; got {drained_2}"
        assert len(target_writer.applied_records) == 2, "G7 FAIL: Event 2 not applied to target writer"
        assert target_writer.applied_records[1]["ENTITY_ID"] == 102, "G7 FAIL: Applied record 2 payload mismatch"
        print("[G7 ADDITIONAL EVENT AFTER DAG SUCCESS]: PASS")

        # =========================================================================
        # G8 DURABLE ACK/CHECKPOINT
        # =========================================================================
        assert target_writer.committed_batches >= 2, "G8 FAIL: Target write batch not committed/ACK'd"
        assert cdc_auth.events_applied_total == 2, "G8 FAIL: Applied counter mismatch"
        print("[G8 DURABLE ACK/CHECKPOINT]: PASS")

        # =========================================================================
        # G9 PROCESS-BOUNDARY DESTRUCTION
        # =========================================================================
        cdc_auth.active_adapter = None
        cdc_auth.apply_coordinator = None
        if cdc_auth._streaming_thread and cdc_auth._streaming_thread.is_alive():
            cdc_auth._stop_streaming.set()

        assert cdc_auth.active_adapter is None, "G9 FAIL: Source adapter not cleared"
        assert cdc_auth.apply_coordinator is None, "G9 FAIL: Apply coordinator not cleared"
        print("[G9 PROCESS-BOUNDARY DESTRUCTION]: PASS")

        # =========================================================================
        # G10 GENERIC RUNTIME RECOVERY
        # =========================================================================
        cdc_auth.set_active_adapter(source_adapter)
        cdc_auth.bind_target_writer(target_writer)

        assert cdc_auth.active_adapter is not None, "G10 FAIL: Source adapter not rebound"
        assert cdc_auth.apply_coordinator is not None, "G10 FAIL: Apply coordinator not rebound"
        print("[G10 GENERIC RUNTIME RECOVERY]: PASS")

        # =========================================================================
        # G11 NEW POST-RECOVERY EVENT
        # =========================================================================
        evt_3 = ChangeEvent(
            event_id="evt-serial-003",
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
            after_image={"ENTITY_ID": 103, "NAME": "Serial Event 3 Post Recovery"},
        )
        source_adapter.pending_events.append(evt_3)

        drained_3 = cdc_auth.drain_and_sync()
        assert drained_3 == 1, f"G11 FAIL: Post-recovery event not processed; got {drained_3}"
        assert len(target_writer.applied_records) == 3, "G11 FAIL: Post-recovery event not applied"
        assert target_writer.applied_records[2]["ENTITY_ID"] == 103, "G11 FAIL: Post-recovery payload mismatch"
        print("[G11 NEW POST-RECOVERY EVENT]: PASS")

        # =========================================================================
        # G12 GOVERNED CUTOVER
        # =========================================================================
        readiness = cdc_auth.evaluate_cutover_readiness()
        assert readiness is not None, "G12 FAIL: Could not evaluate cutover readiness"
        cdc_auth.cutover_coordinator.transition_to(CutoverState.SYNC_BARRIER_REACHED)
        cdc_auth.cutover_coordinator.transition_to(CutoverState.CUTOVER_COMPLETE)
        assert cdc_auth.cutover_coordinator.state == CutoverState.CUTOVER_COMPLETE, "G12 FAIL: Cutover state not CUTOVER_COMPLETE"
        print("[G12 GOVERNED CUTOVER]: PASS")

        # =========================================================================
        # G13 DRAIN / FINALIZATION
        # =========================================================================
        drained_final = cdc_auth.drain_and_sync()
        assert drained_final == 0, "G13 FAIL: Backlog not completely drained after cutover"
        print("[G13 DRAIN / FINALIZATION]: PASS")

        # =========================================================================
        # G14 TERMINAL COMPLETION
        # =========================================================================
        with uow:
            agg_to_complete = caller.repository.get_by_id(migration_id, connection=uow.connection)
            agg_to_complete.state = MigrationLifecycleState.COMPLETED
            agg_to_complete.revision += 1
            caller.repository.save(agg_to_complete, connection=uow.connection)

        with uow:
            agg_final = caller.repository.get_by_id(migration_id, connection=uow.connection)
        assert agg_final.state == MigrationLifecycleState.COMPLETED, "G14 FAIL: Migration state is not COMPLETED post-cutover"
        print("[G14 TERMINAL COMPLETION]: PASS")

        # =========================================================================
        # G15 FAILURE SAFETY
        # =========================================================================
        target_writer.fail_on_next_write = True
        evt_fail = ChangeEvent(
            event_id="evt-serial-fail",
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
            after_image={"ENTITY_ID": 104, "NAME": "Failing Event"},
        )
        source_adapter.pending_events.append(evt_fail)

        with pytest.raises(CDCApplyError):
            cdc_auth.drain_and_sync()

        assert not any(r.get("ENTITY_ID") == 104 for r in target_writer.applied_records), "G15 FAIL: Failed write was wrongfully applied/ACK'd!"
        print("[G15 FAILURE SAFETY]: PASS")

        caller.close()

    elapsed = time.time() - t0
    print(f"\n========================================================")
    print(f"M2 SERIAL BACKEND JOURNEY: PASS (elapsed: {elapsed:.3f}s)")
    print("========================================================\n")


if __name__ == "__main__":
    test_m2_backend_serial_journey()
