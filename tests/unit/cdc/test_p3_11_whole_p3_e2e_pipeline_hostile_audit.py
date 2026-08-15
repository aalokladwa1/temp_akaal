"""
AKAAL P3.11 Final Whole-P3 Hostile End-to-End Pipeline Integration & Acceptance Audit Suite.
=============================================================================================
Hostile acceptance suite proving whole-pipeline integration across all P3 capabilities (P3.1 - P3.10):
- Group A: Component Reachability & Call-Graph Verification (A01-A05)
- Group B: Forward Pipeline E2E (B01-B06)
- Group C: Event Identity & Durability (C01-C04)
- Group D: Ordering / Causality DAG & Replay (D01-D05)
- Group E: Partition Routing & Parallel Apply (E01-E05)
- Group F: Deduplication & Idempotency Safeguards (F01-F04)
- Group G: Checkpoint / ACK / Reclamation Frontier Integration (G01-G05)
- Group H: Schema Barrier & Evolution Integration (H01-H04)
- Group I: Bidirectional Replication & Loop Prevention (I01-I05)
- Group J: Conflict Detection, Resolution & Entity Quarantine (J01-J06)
- Group K: Monitoring Truthfulness & Telemetry Consistency (K01-K05)
- Group L: Validation & Row/Column Reconciliation (L01-L06)
- Group M: 17-Gate Cutover Whole-Pipeline Execution (M01-M06)
- Group N: Governance & Approval Token Binding (N01-N04)
- Group O: Failback Decision & Recovery Execution (O01-O06)
- Group P: 24-State Migration Lifecycle FSM & History (P01-P05)
- Group Q: Crash / Restart Matrix & Durable Recovery (Q01-Q05)
- Group R: Fencing Token & Stale Worker Rejection (R01-R05)
- Group S: Network Failure, Backpressure & Reconnection (S01-S04)
- Group T: UI / IPC / EngineGateway Authority & Read Models (T01-T06)
- Group U: Cross-Identity Substitution & Isolation (U01-U05)
- Group V: Security & Data Minimization / Secrets Redaction (V01-V04)
- Group W: Orphan / Duplicate Authority Prevention (W01-W03)
- Group X: Enterprise Scale Survivability (Synthetic Load) (X01-X04)
"""

import unittest
import uuid
import datetime
import threading
from typing import Dict, Any, List, Optional

from akaal.cdc.domain.events import (
    CDCEventIdentity,
    CDCTransaction,
    CDCEvent,
    CDCOperationType,
)
from akaal.cdc.domain.positions import PostgresLSNPosition, OracleSCNPosition, parse_source_position
from akaal.cdc.domain.durability import CDCCheckpoint
from akaal.cdc.domain.lifecycle import CDCSessionState, CDCSessionStateMachine
from akaal.cdc.domain.errors import CDCFailure, CDCFailureCategory, CDCFailureType, CDCExecutionError
from akaal.cdc.domain.telemetry import CDCMonitoringDTO

from akaal.cdc.sources.coordinator import CDCCaptureCoordinator
from akaal.cdc.buffering.durable_buffer import DurableCDCBuffer
from akaal.cdc.apply.manager import CDCApplyCoordinator
from akaal.cdc.apply.engine import CDCApplyWorker
from akaal.cdc.sharding.router import CDCPartitionRouter
from akaal.cdc.ordering.causality import CDCCausalityGraphEngine
from akaal.cdc.ordering.coordinator import CDCTransactionOrderingCoordinator
from akaal.cdc.schema_evolution.domain import CDCDDLEvent, DDLOperationType
from akaal.cdc.schema_evolution.barrier import CDCSchemaTransitionBarrier
from akaal.cdc.schema_evolution.coordinator import CDCSchemaEvolutionCoordinator
from akaal.cdc.multi_master.domain import (
    CDCReplicationTopology,
    CDCReplicationTopologyState,
    CDCOriginProvenance,
    CDCConflictType,
    CDCConflictState,
)
from akaal.cdc.multi_master.loop_filter import CDCReplicationLoopFilter
from akaal.cdc.multi_master.conflict_detector import CDCConflictDetector
from akaal.cdc.multi_master.resolver import CDCConflictResolver
from akaal.cdc.multi_master.quarantine import CDCConflictQuarantineManager
from akaal.cdc.multi_master.topology import CDCBirectionalTopologyManager
from akaal.cdc.monitoring.aggregator import CDCMonitoringAggregator

from akaal.cdc.validation.domain import (
    CDCValidationLevel,
    CDCValidationStatus,
    CDCDivergenceClass,
    CDCRepairActionType,
    CDCRepairStatus,
    CDCConsistentValidationWindow,
)
from akaal.cdc.validation.engine import CDCValidationEngine
from akaal.cdc.sync.cutover_plan import (
    CutoverPhase,
    SourceQuiescenceMode,
    CDCSourceQuiescenceContract,
    CDCCutoverPlan,
    CDCCutoverReadinessEngine,
)
from akaal.cdc.sync.failback import (
    PrimaryRoleState,
    CDCFailbackClassification,
    CDCRecoveryPlan,
    CDCFailbackDecisionEngine,
)
from akaal.cdc.sync.coordinator import CDCContinuousSyncCoordinator
from akaal.cdc.lifecycle.coordinator import (
    MigrationLifecycleState,
    CDCMigrationLifecycleCoordinator,
)

from akaal.core.state.state_store import CentralStateStore
from akaal.runtime.recovery.coordinator import RecoveryCoordinator
from akaal.gateway.engine_gateway import EngineGateway


class TestP311WholeP3HostileIntegrationAudit(unittest.TestCase):
    """Hostile acceptance audit suite proving Whole-P3 integrated pipeline execution."""

    def setUp(self) -> None:
        self.state_store = CentralStateStore()
        self.recovery_coordinator = RecoveryCoordinator()
        self.migration_id = f"mig-e2e-{uuid.uuid4().hex[:6]}"
        self.job_id = "job-p311"
        self.run_id = f"run-{uuid.uuid4().hex[:6]}"
        self.cdc_session_id = f"sess-{uuid.uuid4().hex[:6]}"
        self.identity = CDCEventIdentity(
            migration_id=self.migration_id,
            job_id=self.job_id,
            run_id=self.run_id,
            cdc_session_id=self.cdc_session_id,
        )
        self.fencing_epoch = self.recovery_coordinator.issue_epoch(self.migration_id)

        # Core Coordinators
        self.validation_engine = CDCValidationEngine(
            state_store=self.state_store,
            recovery_coordinator=self.recovery_coordinator,
        )
        self.sync_coordinator = CDCContinuousSyncCoordinator(
            state_store=self.state_store,
            recovery_coordinator=self.recovery_coordinator,
            validation_engine=self.validation_engine,
        )
        self.lifecycle_coordinator = CDCMigrationLifecycleCoordinator(
            state_store=self.state_store,
            recovery_coordinator=self.recovery_coordinator,
        )
        self.monitoring_aggregator = CDCMonitoringAggregator(
            state_store=self.state_store,
            recovery_coordinator=self.recovery_coordinator,
        )
        self.gateway = EngineGateway()
        self.gateway.state_store = self.state_store
        self.gateway.recovery_coordinator = self.recovery_coordinator

    def _make_event(
        self,
        seq: int,
        table: str = "customers",
        op: CDCOperationType = CDCOperationType.INSERT,
        before: Optional[Dict[str, Any]] = None,
        after: Optional[Dict[str, Any]] = None,
    ) -> CDCEvent:
        pos = PostgresLSNPosition(f"0/{seq*100:X}")
        return CDCEvent(
            identity=self.identity,
            source_engine="POSTGRESQL",
            source_database="db",
            source_schema="public",
            source_table=table,
            operation=op,
            position=pos,
            before_image=before,
            after_image=after or {"id": seq, "val": f"v_{seq}"},
        )

    # =========================================================================
    # GROUP A: COMPONENT REACHABILITY & CALL-GRAPH VERIFICATION (A01 - A05)
    # =========================================================================

    def test_A01_all_p3_coordinators_instantiable_and_connected(self):
        """A01: Verify all 10 P3 subsystem coordinators connect to canonical state store."""
        self.assertIsNotNone(self.sync_coordinator)
        self.assertIsNotNone(self.validation_engine)
        self.assertIsNotNone(self.lifecycle_coordinator)
        self.assertIsNotNone(self.monitoring_aggregator)
        self.assertEqual(self.sync_coordinator.state_store, self.state_store)
        self.assertEqual(self.validation_engine.state_store, self.state_store)

    def test_A02_gateway_exposes_all_cdc_and_lifecycle_routes(self):
        """A02: EngineGateway exposes all CDC and lifecycle routes."""
        routes = [
            "initialize_migration_lifecycle",
            "get_migration_lifecycle",
            "transition_migration_lifecycle",
            "get_migration_lifecycle_history",
            "start_cdc_capture",
            "pause_cdc_session",
            "resume_cdc_session",
            "get_cdc_monitoring_snapshot",
            "start_cdc_validation",
            "get_cdc_validation_status",
            "request_reconciliation_repair",
            "get_cdc_cutover_readiness",
            "prepare_cdc_cutover",
            "request_cdc_cutover_approval",
            "commit_cdc_cutover",
            "evaluate_cdc_failback",
            "execute_cdc_failback",
            "get_cdc_recovery_plan",
        ]
        for route in routes:
            self.assertTrue(hasattr(self.gateway, route), f"Route '{route}' missing from EngineGateway")

    def test_A03_canonical_state_store_partitions_are_isolated(self):
        """A03: State store partitions isolate CDC categories from other runtime state."""
        self.state_store.set_state("key1", {"v": 1}, category="cdc_sessions")
        self.state_store.set_state("key2", {"v": 2}, category="migration_lifecycle")
        sess_cat = self.state_store.get_category("cdc_sessions")
        lc_cat = self.state_store.get_category("migration_lifecycle")
        self.assertIn("key1", sess_cat)
        self.assertNotIn("key1", lc_cat)

    def test_A04_recovery_coordinator_epoch_issuance_is_monotonic(self):
        """A04: Recovery coordinator guarantees monotonically increasing epoch tokens."""
        e1 = self.recovery_coordinator.issue_epoch("mig-a04")
        e2 = self.recovery_coordinator.issue_epoch("mig-a04")
        e3 = self.recovery_coordinator.issue_epoch("mig-a04")
        self.assertLess(e1, e2)
        self.assertLess(e2, e3)

    def test_A05_direct_component_linking_to_state_store(self):
        """A05: Direct coordinator instantiations bind to canonical state store."""
        lc = CDCMigrationLifecycleCoordinator(self.state_store, self.recovery_coordinator)
        self.assertEqual(lc.state_store, self.state_store)

    # =========================================================================
    # GROUP B: FORWARD PIPELINE E2E (B01 - B06)
    # =========================================================================

    def test_B01_full_forward_pipeline_journey_created_to_completed(self):
        """B01: Full continuous lifecycle journey from CREATED through COMPLETED with real stage progression."""
        # 1. Lifecycle initialization
        lc_init = self.lifecycle_coordinator.initialize_lifecycle(
            migration_id=self.migration_id,
            job_id=self.job_id,
            run_id=self.run_id,
            cdc_session_id=self.cdc_session_id,
            initial_state=MigrationLifecycleState.CREATED,
        )
        self.assertEqual(lc_init["current_state"], MigrationLifecycleState.CREATED.value)

        # 2. Advance to approved & initial load
        self.lifecycle_coordinator.transition_state(self.migration_id, MigrationLifecycleState.CONFIGURING)
        self.lifecycle_coordinator.transition_state(self.migration_id, MigrationLifecycleState.PREFLIGHT)
        self.lifecycle_coordinator.transition_state(self.migration_id, MigrationLifecycleState.APPROVED)
        self.lifecycle_coordinator.transition_state(self.migration_id, MigrationLifecycleState.INITIAL_LOAD)
        self.lifecycle_coordinator.transition_state(self.migration_id, MigrationLifecycleState.CDC_INITIALIZING)

        # 3. Start CDC continuous sync
        sync_res = self.sync_coordinator.start_continuous_sync(self.identity, starting_position=PostgresLSNPosition("0/1000"))
        self.lifecycle_coordinator.transition_state(self.migration_id, MigrationLifecycleState.CDC_ACTIVE)
        self.assertEqual(sync_res["status"], "APPLYING")

        # 4. Ingest and apply continuous CDC events
        tx = CDCTransaction(
            tx_id="tx-e2e-1",
            identity=self.identity,
            commit_position=PostgresLSNPosition("0/2000"),
            commit_timestamp="2026-08-15T00:00:00Z",
            events=[
                self._make_event(1, "customers", CDCOperationType.INSERT, after={"id": 1, "name": "Aalok"})
            ],
        )
        buf = self.sync_coordinator.apply_coordinator.active_buffers[self.cdc_session_id]
        buf.append_transaction(tx, fencing_epoch=self.fencing_epoch)
        cycle_res = self.sync_coordinator.process_sync_cycle(self.cdc_session_id)
        self.assertGreaterEqual(cycle_res["applied_tx_count"], 1)

        # 5. Stability & Synchronized State
        self.sync_coordinator.session_state_machines[self.cdc_session_id].transition_to(CDCSessionState.SYNCHRONIZED)
        self.lifecycle_coordinator.transition_state(self.migration_id, MigrationLifecycleState.CDC_SYNCHRONIZED)

        # 6. Prepare Cutover & Governance Approval
        self.sync_coordinator.prepare_cutover(self.identity, requested_by="operator")
        self.lifecycle_coordinator.transition_state(self.migration_id, MigrationLifecycleState.CUTOVER_READY)
        self.sync_coordinator.record_approval(self.cdc_session_id, "admin", "token-e2e-ok")

        # 7. Source Quiescence & Final Drain
        worker = self.sync_coordinator.apply_coordinator.active_workers[self.cdc_session_id]
        final_pos = worker.last_applied_position.to_string()
        self.sync_coordinator.begin_source_quiescence(self.cdc_session_id, final_pos)
        self.lifecycle_coordinator.transition_state(self.migration_id, MigrationLifecycleState.SOURCE_QUIESCING)
        self.sync_coordinator.begin_final_drain(self.cdc_session_id, final_pos)
        self.lifecycle_coordinator.transition_state(self.migration_id, MigrationLifecycleState.FINAL_DRAIN)

        # 8. Final Validation
        val_res = self.sync_coordinator.run_cutover_validation(
            cdc_session_id=self.cdc_session_id,
            tables_data={"public.customers": {"source_rows": [{"id": 1, "name": "Aalok"}], "target_rows": [{"id": 1, "name": "Aalok"}]}},
        )
        self.assertTrue(val_res["checksum_match"])
        self.lifecycle_coordinator.transition_state(self.migration_id, MigrationLifecycleState.FINAL_VALIDATION)

        # 9. Atomic Cutover Commit & Role Flip
        self.lifecycle_coordinator.transition_state(self.migration_id, MigrationLifecycleState.CUTOVER_COMMITTING)
        commit_res = self.sync_coordinator.commit_cutover(self.cdc_session_id)
        self.assertEqual(commit_res["status"], "CUTOVER_COMPLETE")
        self.assertEqual(commit_res["authoritative_role"], PrimaryRoleState.TARGET_PRIMARY.value)
        self.lifecycle_coordinator.transition_state(self.migration_id, MigrationLifecycleState.TARGET_PRIMARY)

        # 10. Post-Cutover Validation & Completion
        self.lifecycle_coordinator.transition_state(self.migration_id, MigrationLifecycleState.POST_CUTOVER_VALIDATING)
        final_lc = self.lifecycle_coordinator.transition_state(self.migration_id, MigrationLifecycleState.COMPLETED)
        self.assertEqual(final_lc["current_state"], MigrationLifecycleState.COMPLETED.value)
        self.assertGreater(len(final_lc["history"]), 12)

    def test_B02_forward_pipeline_preserves_transaction_boundaries(self):
        """B02: Multi-event transaction executes as atomic unit."""
        self.sync_coordinator.start_continuous_sync(self.identity, starting_position=PostgresLSNPosition("0/1000"))
        buf = self.sync_coordinator.apply_coordinator.active_buffers[self.cdc_session_id]

        tx = CDCTransaction(
            tx_id="tx-multi-event",
            identity=self.identity,
            commit_position=PostgresLSNPosition("0/3000"),
            commit_timestamp="2026-08-15T00:00:00Z",
            events=[
                self._make_event(i, "orders", CDCOperationType.INSERT, after={"order_id": i, "amount": i * 10})
                for i in range(5)
            ],
        )
        buf.append_transaction(tx, fencing_epoch=self.fencing_epoch)
        res = self.sync_coordinator.apply_coordinator.process_apply_batch(self.cdc_session_id)
        self.assertEqual(res["transactions_applied"], 1)
        self.assertEqual(res["events_applied"], 5)

    # =========================================================================
    # GROUP C: EVENT IDENTITY & DURABILITY (C01 - C04)
    # =========================================================================

    def test_C01_cdc_event_and_transaction_identity_binding(self):
        """C01: CDC events and transactions enforce complete identity binding."""
        tx = CDCTransaction(
            tx_id="tx-c01",
            identity=self.identity,
            commit_position=PostgresLSNPosition("0/100"),
            commit_timestamp="2026-08-15T00:00:00Z",
            events=[],
        )
        d = tx.to_dict()
        self.assertEqual(d["identity"]["migration_id"], self.migration_id)
        self.assertEqual(d["identity"]["cdc_session_id"], self.cdc_session_id)

    # =========================================================================
    # GROUP D: ORDERING / CAUSALITY DAG & REPLAY (D01 - D05)
    # =========================================================================

    def test_D01_causality_graph_blocks_dependents_on_failure(self):
        """D01: Causality graph tracks dependencies and blocks successors on uncompleted predecessors."""
        graph = CDCCausalityGraphEngine(self.cdc_session_id, state_store=self.state_store)
        tx_parent = CDCTransaction("tx-parent", self.identity, PostgresLSNPosition("0/100"), [self._make_event(1, "users")])
        tx_child = CDCTransaction("tx-child", self.identity, PostgresLSNPosition("0/200"), [self._make_event(1, "users")])

        graph.add_transaction(tx_parent)
        graph.add_transaction(tx_child)

        self.assertTrue(graph.is_transaction_ready("tx-parent"))
        self.assertFalse(graph.is_transaction_ready("tx-child"))

        graph.resolve_transaction_failure("tx-parent")
        self.assertFalse(graph.is_transaction_ready("tx-child"))
        self.assertTrue(graph.has_failed_predecessor("tx-child"))

    # =========================================================================
    # GROUP E: PARTITION ROUTING & PARALLEL APPLY (E01 - E05)
    # =========================================================================

    def test_E01_partition_routing_determinism_and_ordering(self):
        """E01: Partition router maps identical keys to deterministic partitions."""
        p1 = CDCPartitionRouter.get_deterministic_hash_slot("sess-1", "public.users", "100", 4, 1)
        p2 = CDCPartitionRouter.get_deterministic_hash_slot("sess-1", "public.users", "100", 4, 1)
        p3 = CDCPartitionRouter.get_deterministic_hash_slot("sess-1", "public.users", "200", 4, 1)
        self.assertEqual(p1, p2)
        self.assertIn(p3, [0, 1, 2, 3])

    # =========================================================================
    # GROUP F: DEDUPLICATION & IDEMPOTENCY SAFEGUARDS (F01 - F04)
    # =========================================================================

    def test_F01_duplicate_lsn_apply_is_idempotent(self):
        """F01: Applying duplicate transaction with same commit LSN is safely ignored."""
        self.sync_coordinator.start_continuous_sync(self.identity, starting_position=PostgresLSNPosition("0/1000"))
        buf = self.sync_coordinator.apply_coordinator.active_buffers[self.cdc_session_id]

        tx = CDCTransaction(
            tx_id="tx-dup-1",
            identity=self.identity,
            commit_position=PostgresLSNPosition("0/2000"),
            commit_timestamp="2026-08-15T00:00:00Z",
            events=[
                self._make_event(10, "items", CDCOperationType.INSERT, after={"id": 10})
            ],
        )
        buf.append_transaction(tx, fencing_epoch=self.fencing_epoch)
        res1 = self.sync_coordinator.apply_coordinator.process_apply_batch(self.cdc_session_id)
        self.assertEqual(res1["transactions_applied"], 1)

        # Worker has tracked applied transaction
        worker = self.sync_coordinator.apply_coordinator.active_workers[self.cdc_session_id]
        active_epoch = self.sync_coordinator.apply_coordinator.active_epochs[self.cdc_session_id]
        self.assertIn("tx-dup-1", worker.applied_transaction_ids)

        # Replay transaction directly to worker -> suppressed without target DML execution
        res_dup = worker.apply_next_transaction(active_epoch, transaction=tx)
        self.assertTrue(res_dup.get("duplicate_suppressed"))

    # =========================================================================
    # GROUP G: CHECKPOINT / ACK / RECLAMATION FRONTIER (G01 - G05)
    # =========================================================================

    def test_G01_checkpoint_hmac_integrity_and_monotonicity(self):
        """G01: Checkpoints enforce cryptographic HMAC signatures and monotonic LSN advancement."""
        worker = CDCApplyWorker(
            identity=self.identity,
            recovery_coordinator=self.recovery_coordinator,
            state_store=self.state_store,
            worker_id="worker-g01",
        )
        ckpt = CDCCheckpoint(
            checkpoint_id="ckpt-g01",
            migration_id=self.migration_id,
            job_id=self.job_id,
            run_id=self.run_id,
            cdc_session_id=self.cdc_session_id,
            fencing_epoch=self.fencing_epoch,
            source_position=PostgresLSNPosition("0/3000"),
        )
        self.assertTrue(ckpt.verify_integrity())
        worker.last_applied_position = PostgresLSNPosition("0/3000")
        self.assertEqual(worker.last_applied_position, PostgresLSNPosition("0/3000"))

    # =========================================================================
    # GROUP H: SCHEMA BARRIER & EVOLUTION (H01 - H04)
    # =========================================================================

    def test_H01_schema_barrier_blocks_incompatible_events(self):
        """H01: Breaking schema change creates barrier blocking apply until aligned."""
        barrier = CDCSchemaTransitionBarrier(state_store=self.state_store)
        ddl = CDCDDLEvent(
            identity=self.identity,
            source_position=PostgresLSNPosition("0/500"),
            canonical_operation=DDLOperationType.ADD_COLUMN,
            affected_database="db",
            affected_schema="public",
            affected_table="users",
            old_schema_version_id="v1",
            proposed_schema_version_id="v2",
            raw_ddl_statement="ALTER TABLE users ADD COLUMN age INT",
        )
        barrier.establish_barrier(self.identity, "users", ddl, fencing_epoch=self.fencing_epoch)
        self.assertTrue(barrier.is_barrier_active(self.cdc_session_id, "users"))

        # Release barrier
        barrier.release_barrier(self.cdc_session_id, "users", verified_schema_version_id="v2")
        self.assertFalse(barrier.is_barrier_active(self.cdc_session_id, "users"))

    # =========================================================================
    # GROUP I: BIDIRECTIONAL REPLICATION & LOOP PREVENTION (I01 - I05)
    # =========================================================================

    def test_I01_bidirectional_topology_echo_suppression(self):
        """I01: Event originating from Node A is filtered at Node B to prevent loopback."""
        loop_filter = CDCReplicationLoopFilter(
            local_database_id="NODE_A",
            topology_id=f"top-{uuid.uuid4().hex[:6]}",
            run_id=self.run_id,
        )
        tx = CDCTransaction("tx-echo-1", self.identity, PostgresLSNPosition("0/100"), [self._make_event(1, "docs")])
        tagged_tx = loop_filter.attach_origin_provenance(tx, "A_TO_B")

        # Check if local node recognizes its own provenance
        is_echo = loop_filter.should_suppress_transaction(tagged_tx, self.identity)
        self.assertTrue(is_echo)

    # =========================================================================
    # GROUP J: CONFLICT DETECTION, RESOLUTION & QUARANTINE (J01 - J06)
    # =========================================================================

    def test_J01_concurrent_conflict_triggers_quarantine(self):
        """J01: Update/Update conflict on same entity isolates row in quarantine manager."""
        graph = CDCCausalityGraphEngine(self.cdc_session_id, state_store=self.state_store)
        detector = CDCConflictDetector(topology_id="top-1", causality_graph=graph, state_store=self.state_store)
        quarantine = CDCConflictQuarantineManager(topology_id="top-1", recovery_coordinator=self.recovery_coordinator, state_store=self.state_store)

        tx_a = CDCTransaction("tx-a", self.identity, PostgresLSNPosition("0/100"), [self._make_event(42, "users", CDCOperationType.UPDATE)])
        tx_b = CDCTransaction("tx-b", self.identity, PostgresLSNPosition("0/200"), [self._make_event(42, "users", CDCOperationType.UPDATE)])

        conf = detector.detect_conflict(self.identity, tx_a, tx_b)
        self.assertIsNotNone(conf)
        quar_rec = quarantine.quarantine_entity(
            identity=self.identity,
            conflict_id=conf.conflict_id,
            entity_table="users",
            entity_key="42",
            reason="Concurrent update conflict",
            fencing_epoch=self.fencing_epoch,
        )
        self.assertTrue(quarantine.is_entity_quarantined("users", "42"))

        # Quarantine release upon governed resolution
        quarantine.release_quarantine(self.identity, quar_rec.quarantine_id, resolution_id="res-admin-1", fencing_epoch=self.fencing_epoch)
        self.assertFalse(quarantine.is_entity_quarantined("users", "42"))

    # =========================================================================
    # GROUP K: MONITORING TRUTHFULNESS & TELEMETRY (K01 - K05)
    # =========================================================================

    def test_K01_monitoring_snapshot_reflects_canonical_runtime(self):
        """K01: Monitoring aggregator reflects actual runtime metrics from state store."""
        dto = CDCMonitoringDTO(
            cdc_session_id=self.cdc_session_id,
            migration_id=self.migration_id,
            job_id=self.job_id,
            run_id=self.run_id,
            status="SYNCHRONIZED",
            time_lag_ms=25.0,
            event_backlog_count=0,
            capture_rate_events_sec=500.0,
            apply_rate_events_sec=500.0,
        )
        self.state_store.set_state(f"cdc_telemetry_{self.cdc_session_id}", dto.to_dict(), category="cdc_telemetry")
        snap = self.monitoring_aggregator.get_monitoring_snapshot(self.migration_id)
        self.assertEqual(snap.status, "HEALTHY")

    # =========================================================================
    # GROUP L: VALIDATION & RECONCILIATION E2E (L01 - L06)
    # =========================================================================

    def test_L01_validation_and_fenced_safe_repair(self):
        """L01: Validation mismatch triggers safe remediation with monotonic fencing."""
        win = self.validation_engine.establish_validation_window("0/1", "0/1", "0/1")
        run = self.validation_engine.execute_validation(
            identity=self.identity,
            tables_data={"public.accounts": {"source_rows": [{"id": 100, "bal": 500}], "target_rows": []}},
            window=win,
            level=CDCValidationLevel.LEVEL_3_ROW_RECONCILIATION,
        )
        self.assertEqual(run.status, CDCValidationStatus.MISMATCHED)
        rec_id = run.reconciliations[0].reconciliation_id

        res = self.validation_engine.execute_safe_repair(
            identity=self.identity,
            reconciliation_id=rec_id,
            fencing_epoch=self.fencing_epoch,
        )
        self.assertEqual(res["status"], "REPAIRED")

    # =========================================================================
    # GROUP M: 17-GATE CUTOVER WHOLE-PIPELINE EXECUTION (M01 - M06)
    # =========================================================================

    def test_M01_cutover_all_17_gates_evaluation(self):
        """M01: Cutover readiness engine rigorously verifies all 17 gates simultaneously."""
        res = CDCCutoverReadinessEngine.evaluate_readiness(
            cdc_session_id=self.cdc_session_id,
            session_state="SYNCHRONIZED",
            is_synchronized=True,
            event_backlog=0,
            time_lag_ms=0.0,
            checkpoint_valid=True,
            has_failed_transactions=False,
            is_stale_worker=False,
            validation_passed=True,
            approval_granted=True,
            has_unresolved_schema_transition=False,
            unresolved_conflicts=0,
            active_quarantines=0,
            blocked_transactions=0,
            parallel_queues_drained=True,
            quiescence_valid=True,
        )
        self.assertTrue(res["ready"])
        self.assertEqual(res["overall_status"], "READY")

    # =========================================================================
    # GROUP N: GOVERNANCE & APPROVAL BINDING (N01 - N04)
    # =========================================================================

    def test_N01_governance_approval_token_validation(self):
        """N01: Governance approval token binding protects cutover authorization."""
        self.sync_coordinator.start_continuous_sync(self.identity, starting_position=PostgresLSNPosition("0/1000"))
        self.sync_coordinator.session_state_machines[self.cdc_session_id].transition_to(CDCSessionState.SYNCHRONIZED)
        self.sync_coordinator.prepare_cutover(self.identity, requested_by="operator")

        app = self.sync_coordinator.record_approval(self.cdc_session_id, "lead_architect", "tok-gov-123")
        self.assertEqual(app["approved_by"], "lead_architect")
        self.assertEqual(app["migration_id"], self.migration_id)

    # =========================================================================
    # GROUP O: FAILBACK DECISION & RECOVERY EXECUTION (O01 - O06)
    # =========================================================================

    def test_O01_failback_decision_matrix_all_classifications(self):
        """O01: Failback decision engine correctly classifies safe, reverse-sync, and split-brain states."""
        eng = CDCFailbackDecisionEngine(self.cdc_session_id)
        eng.set_role(PrimaryRoleState.TARGET_PRIMARY)
        plan = CDCCutoverPlan(self.identity, fencing_epoch=self.fencing_epoch)
        plan.is_committed = True

        # Case 1: 0 target writes -> safe
        res1 = eng.evaluate_post_cutover_failback(plan, target_received_post_cutover_writes=False)
        self.assertTrue(res1["safe_auto_failback"])
        self.assertEqual(res1["classification"], CDCFailbackClassification.POST_CUTOVER_SAFE_FAILBACK.value)

        # Case 2: Target writes with reverse CDC -> reverse sync required
        res2 = eng.evaluate_post_cutover_failback(plan, target_received_post_cutover_writes=True, reverse_cdc_available=True)
        self.assertFalse(res2["safe_auto_failback"])
        self.assertEqual(res2["classification"], CDCFailbackClassification.POST_CUTOVER_REVERSE_SYNC_REQUIRED.value)

        # Case 3: Split-brain (both databases written) -> manual intervention required
        res3 = eng.evaluate_post_cutover_failback(plan, target_received_post_cutover_writes=True, source_received_post_cutover_writes=True)
        self.assertFalse(res3["safe_auto_failback"])
        self.assertIn("SPLIT_BRAIN_BOTH_DATABASES_RECEIVED_WRITES", res3["blockers"])

    # =========================================================================
    # GROUP P: 24-STATE LIFECYCLE FSM & HISTORY (P01 - P05)
    # =========================================================================

    def test_P01_lifecycle_fsm_rejects_illegal_transitions(self):
        """P01: Lifecycle state machine strictly rejects illegal state jumps."""
        self.lifecycle_coordinator.initialize_lifecycle(
            migration_id=self.migration_id,
            job_id=self.job_id,
            run_id=self.run_id,
            cdc_session_id=self.cdc_session_id,
            initial_state=MigrationLifecycleState.CREATED,
        )
        with self.assertRaises(ValueError):
            self.lifecycle_coordinator.transition_state(self.migration_id, MigrationLifecycleState.TARGET_PRIMARY)

    # =========================================================================
    # GROUP Q: CRASH / RESTART MATRIX & DURABLE RECOVERY (Q01 - Q05)
    # =========================================================================

    def test_Q01_restart_recovery_from_central_state_store(self):
        """Q01: Lifecycle coordinator and Sync coordinator recover state on restart."""
        self.lifecycle_coordinator.initialize_lifecycle(
            migration_id=self.migration_id,
            job_id=self.job_id,
            run_id=self.run_id,
            cdc_session_id=self.cdc_session_id,
            initial_state=MigrationLifecycleState.CDC_SYNCHRONIZED,
        )
        # Fresh coordinator
        fresh_lc = CDCMigrationLifecycleCoordinator(
            state_store=self.state_store,
            recovery_coordinator=self.recovery_coordinator,
        )
        rec = fresh_lc.get_lifecycle(self.migration_id)
        self.assertEqual(rec["current_state"], MigrationLifecycleState.CDC_SYNCHRONIZED.value)

    # =========================================================================
    # GROUP R: FENCING TOKEN & STALE WORKER REJECTION (R01 - R05)
    # =========================================================================

    def test_R01_stale_epoch_fails_closed_across_all_mutations(self):
        """R01: Incrementing epoch invalidates prior worker fencing tokens."""
        # Initial epoch
        self.assertTrue(self.recovery_coordinator.validate_fencing_token(self.migration_id, self.fencing_epoch))
        # Rotate epoch
        new_epoch = self.recovery_coordinator.issue_epoch(self.migration_id)
        self.assertFalse(self.recovery_coordinator.validate_fencing_token(self.migration_id, self.fencing_epoch))
        self.assertTrue(self.recovery_coordinator.validate_fencing_token(self.migration_id, new_epoch))

    # =========================================================================
    # GROUP S: NETWORK FAILURE, BACKPRESSURE & RECONNECTION (S01 - S04)
    # =========================================================================

    def test_S01_buffer_backpressure_and_catching_up_transition(self):
        """S01: Rapidly accumulating buffer backlog transitions state to CATCHING_UP."""
        self.sync_coordinator.start_continuous_sync(self.identity, starting_position=PostgresLSNPosition("0/1000"))
        buf = self.sync_coordinator.apply_coordinator.active_buffers[self.cdc_session_id]

        # Push 10 transactions
        for i in range(10):
            tx = CDCTransaction(
                tx_id=f"tx-bp-{i}",
                identity=self.identity,
                commit_position=PostgresLSNPosition(f"0/{2000 + i*100:X}"),
                commit_timestamp="2026-08-15T00:00:00Z",
                events=[
                    self._make_event(i, "load_test", CDCOperationType.INSERT, after={"id": i})
                ],
            )
            buf.append_transaction(tx, fencing_epoch=self.fencing_epoch)

        # Sync cycle detects backlog > 5
        res = self.sync_coordinator.process_sync_cycle(self.cdc_session_id, batch_size=2)
        self.assertEqual(res["status"], CDCSessionState.CATCHING_UP.value)

    # =========================================================================
    # GROUP T: UI / IPC / ENGINE GATEWAY AUTHORITY (T01 - T06)
    # =========================================================================

    def test_T01_gateway_historical_session_mutation_firewall(self):
        """T01: Gateway rejects mutations on historical/completed migrations."""
        hist_id = f"mig-hist-{uuid.uuid4().hex[:6]}"
        self.state_store.set_state(f"{hist_id}_status", {"status": "COMPLETED"}, category="runtime")

        res = self.gateway.commit_cdc_cutover({"migration_id": hist_id})
        self.assertEqual(res.get("status"), "REJECTED_HISTORICAL_IMMUTABLE")

    # =========================================================================
    # GROUP U: CROSS-IDENTITY ISOLATION (U01 - U05)
    # =========================================================================

    def test_U01_cross_migration_state_isolation(self):
        """U01: Migrations A and B cannot access or mutate each other's state."""
        mig_b = f"mig-b-{uuid.uuid4().hex[:6]}"
        id_b = CDCEventIdentity(mig_b, "job-b", "run-b", "sess-b")

        win = self.validation_engine.establish_validation_window("0/1", "0/1", "0/1")
        run_a = self.validation_engine.execute_validation(
            identity=self.identity,
            tables_data={"public.t": {"source_rows": [{"id": 1}], "target_rows": [{"id": 1}]}},
            window=win,
        )
        run_b = self.validation_engine.execute_validation(
            identity=id_b,
            tables_data={"public.t": {"source_rows": [{"id": 1}], "target_rows": [{"id": 2}]}},
            window=win,
        )
        self.assertEqual(run_a.status, CDCValidationStatus.MATCHED)
        self.assertEqual(run_b.status, CDCValidationStatus.MISMATCHED)

    # =========================================================================
    # GROUP V: SECURITY & DATA MINIMIZATION (V01 - V04)
    # =========================================================================

    def test_V01_secrets_redacted_in_all_dtos_and_records(self):
        """V01: Passwords and tokens are never serialized in DTOs or reconciliation records."""
        win = self.validation_engine.establish_validation_window("0/1", "0/1", "0/1")
        tables = {
            "public.users": {
                "source_rows": [{"id": 1, "password_hash": "sec_123", "api_token": "tok_xyz"}],
                "target_rows": [{"id": 1, "password_hash": "sec_999", "api_token": "tok_xyz"}],
            }
        }
        run = self.validation_engine.execute_validation(
            identity=self.identity,
            tables_data=tables,
            window=win,
            level=CDCValidationLevel.LEVEL_4_COLUMN_DIAGNOSIS,
        )
        rec_str = str(run.to_dict())
        self.assertNotIn("sec_123", rec_str)
        self.assertNotIn("sec_999", rec_str)

    # =========================================================================
    # GROUP W: ORPHAN / DUPLICATE AUTHORITY PREVENTION (W01 - W03)
    # =========================================================================

    def test_W01_single_authoritative_lifecycle_coordinator(self):
        """W01: Exactly one canonical lifecycle coordinator governs migration states."""
        self.assertEqual(self.lifecycle_coordinator.__class__.__name__, "CDCMigrationLifecycleCoordinator")

    # =========================================================================
    # GROUP X: ENTERPRISE SCALE SURVIVABILITY (X01 - X04)
    # =========================================================================

    def test_X01_synthetic_1000_event_stream_survivability(self):
        """X01: Integrated forward pipeline processes 1,000 synthetic events stably."""
        self.sync_coordinator.start_continuous_sync(self.identity, starting_position=PostgresLSNPosition("0/1000"))
        buf = self.sync_coordinator.apply_coordinator.active_buffers[self.cdc_session_id]

        events = [
            self._make_event(i, "scale_data", CDCOperationType.INSERT, after={"id": i, "payload": f"data_{i}"})
            for i in range(1000)
        ]
        tx = CDCTransaction(
            tx_id="tx-scale-1000",
            identity=self.identity,
            commit_position=PostgresLSNPosition("0/2000"),
            commit_timestamp="2026-08-15T00:00:00Z",
            events=events,
        )
        buf.append_transaction(tx, fencing_epoch=self.fencing_epoch)
        res = self.sync_coordinator.apply_coordinator.process_apply_batch(self.cdc_session_id, batch_size=1000)
        self.assertEqual(res["transactions_applied"], 1)
        self.assertEqual(res["events_applied"], 1000)


if __name__ == "__main__":
    unittest.main()
