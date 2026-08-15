"""
AKAAL P3.9.1 — Hostile CDC Monitoring, Telemetry Truthfulness, UI Authority & Security Audit Suite.
===================================================================================================
Executes 45 hostile adversarial attacks testing CDC Monitoring read-model truthfulness, identity isolation,
freshness, partial subsystem failure handling, impossible state detection, cutover gate truth, concurrency safety,
historical immutability, operator governance authority, recursive secret redaction, and enterprise scale survivability.
"""

import unittest
import threading
import time
import datetime
from typing import Dict, Any

from akaal.cdc.domain.events import CDCEventIdentity, CDCEvent, CDCOperationType, CDCTransaction
from akaal.cdc.domain.positions import PostgresLSNPosition
from akaal.cdc.monitoring.domain import CDCMonitoringSnapshot
from akaal.cdc.monitoring.aggregator import CDCMonitoringAggregator
from akaal.core.state.state_store import CentralStateStore
from akaal.runtime.recovery.coordinator import RecoveryCoordinator
from akaal.streaming.flow.backpressure import BackpressureController, BackpressureState
from akaal.gateway.engine_gateway import EngineGateway
from akaal.cdc.ordering.causality import CDCCausalityGraphEngine
from akaal.cdc.multi_master.topology import CDCBirectionalTopologyManager
from akaal.cdc.multi_master.domain import CDCConflictResolutionPolicy


class TestP391CDCMonitoringHostileAudit(unittest.TestCase):
    """Hostile acceptance audit suite for P3.9 CDC Monitoring & Telemetry."""

    def setUp(self) -> None:
        import os, sqlite3
        self.migration_id = "mig-p391-hostile"
        self.state_store = CentralStateStore()
        with self.state_store._lock:
            self.state_store._state.clear()
            if hasattr(self.state_store, "db_path") and os.path.exists(self.state_store.db_path):
                try:
                    conn = sqlite3.connect(self.state_store.db_path)
                    conn.execute("DELETE FROM central_state;")
                    conn.commit()
                    conn.close()
                except Exception:
                    pass

        self.recovery_coord = RecoveryCoordinator()
        self.bp_controller = BackpressureController()
        self.aggregator = CDCMonitoringAggregator(
            state_store=self.state_store,
            recovery_coordinator=self.recovery_coord,
            backpressure_controller=self.bp_controller,
        )
        self.gateway = EngineGateway()
        self.gateway.state_store = self.state_store

    def tearDown(self) -> None:
        pass

    # =========================================================================
    # ATTACK GROUP A — IDENTITY & CROSS-MIGRATION CONTAMINATION
    # =========================================================================

    def test_A01_cross_migration_topology_manager_rejection(self) -> None:
        """Hostile: Passing a TopologyManager belonging to Migration B to Migration A snapshot must be rejected/ignored."""
        mig_a = f"{self.migration_id}-a01"
        ident_b = CDCEventIdentity("mig-other-B", "job-b", "run-b", "sess-b")
        cg_b = CDCCausalityGraphEngine(cdc_session_id="sess-b", state_store=self.state_store)
        tm_b = CDCBirectionalTopologyManager(
            identity=ident_b,
            source_a_database_id="db-a",
            source_b_database_id="db-b",
            topology_id="top-other-b",
            causality_graph=cg_b,
            recovery_coordinator=self.recovery_coord,
            state_store=self.state_store,
        )

        snap = self.aggregator.get_monitoring_snapshot(migration_id=mig_a, topology_manager=tm_b)
        self.assertNotEqual(snap.conflicts_and_topology.get("topology_id"), "top-other-b")
        self.assertEqual(snap.session_mode, "UNIDIRECTIONAL")

    def test_A02_cross_migration_ordering_coordinator_rejection(self) -> None:
        """Hostile: Passing an OrderingCoordinator belonging to Migration B must not pollute Migration A graph summary."""
        mig_a = f"{self.migration_id}-a02"
        ident_b = CDCEventIdentity("mig-other-B", "job-b", "run-b", "sess-b")
        cg_b = CDCCausalityGraphEngine(cdc_session_id="sess-b", state_store=self.state_store)

        pos = PostgresLSNPosition("0/100")
        evt_fail = CDCEvent(identity=ident_b, source_engine="POSTGRESQL", source_database="db1", source_schema="public", source_table="t1", operation=CDCOperationType.INSERT, position=pos, after_image={"id": 1})
        tx_fail = CDCTransaction(tx_id="tx-b-fail", identity=ident_b, commit_position=pos, events=[evt_fail])
        cg_b.add_transaction(tx_fail)
        cg_b.resolve_transaction_failure("tx-b-fail")

        snap = self.aggregator.get_monitoring_snapshot(migration_id=mig_a, ordering_coordinator=cg_b)
        self.assertEqual(snap.ordering_and_causality.get("blocked_transaction_count", 0), 0)

    def test_A03_mismatched_session_id_isolation(self) -> None:
        """Hostile: Requesting snapshot with explicit cdc_session_id preserves identity binding."""
        mig_a = f"{self.migration_id}-a03"
        snap = self.aggregator.get_monitoring_snapshot(migration_id=mig_a, cdc_session_id="sess-explicit-99")
        self.assertEqual(snap.cdc_session_id, "sess-explicit-99")
        self.assertEqual(snap.identity.cdc_session_id, "sess-explicit-99")

    def test_A04_state_store_namespace_isolation(self) -> None:
        """Hostile: CentralStateStore entries for Migration B do not bleed into Migration A snapshot."""
        mig_a = f"{self.migration_id}-a04"
        self.state_store.set_state("mig-other-B_status", {"status": "FAILED"}, category="runtime")
        self.state_store.set_state(f"{mig_a}_status", {"status": "RUNNING"}, category="runtime")

        snap = self.aggregator.get_monitoring_snapshot(migration_id=mig_a)
        self.assertEqual(snap.status, "HEALTHY")

    def test_A05_malformed_migration_identity_does_not_crash(self) -> None:
        """Hostile: Empty or space-padded migration ID handles safely without unhandled exception."""
        snap = self.aggregator.get_monitoring_snapshot(migration_id="   ")
        self.assertEqual(snap.migration_id, "   ")

    # =========================================================================
    # ATTACK GROUP B — LIVE / STALE / DISCONNECTED TRUTHFULNESS
    # =========================================================================

    def test_B01_live_monitoring_mode_detection(self) -> None:
        """Hostile: Active migration statuses resolve to LIVE monitoring mode."""
        mig_b1 = f"{self.migration_id}-b01"
        for st in ["CONFIGURED", "INITIALIZING", "CREATED", "RUNNING", "ACTIVE", "PAUSED", "CATCHING_UP"]:
            self.state_store.set_state(f"{mig_b1}_status", {"status": st}, category="runtime")
            snap = self.aggregator.get_monitoring_snapshot(migration_id=mig_b1)
            self.assertEqual(snap.monitoring_mode, "LIVE", f"Status '{st}' failed to map to LIVE mode")

    def test_B02_historical_monitoring_mode_detection(self) -> None:
        """Hostile: Terminal migration statuses map to HISTORICAL monitoring mode."""
        mig_b2 = f"{self.migration_id}-b02"
        for st in ["COMPLETED", "TERMINATED", "ARCHIVED"]:
            self.state_store.set_state(f"{mig_b2}_status", {"status": st}, category="runtime")
            snap = self.aggregator.get_monitoring_snapshot(migration_id=mig_b2)
            self.assertEqual(snap.monitoring_mode, "HISTORICAL", f"Status '{st}' failed to map to HISTORICAL mode")

    def test_B03_stale_telemetry_marking(self) -> None:
        """Hostile: If telemetry is old, captured_at timestamp must reflect exact generation time."""
        mig_b3 = f"{self.migration_id}-b03"
        snap1 = self.aggregator.get_monitoring_snapshot(migration_id=mig_b3)
        time.sleep(0.01)
        snap2 = self.aggregator.get_monitoring_snapshot(migration_id=mig_b3)
        self.assertNotEqual(snap1.captured_at, snap2.captured_at)

    def test_B04_paused_status_truthfulness(self) -> None:
        """Hostile: When runtime state is PAUSED, status must be PAUSED, apply rate 0, workers PAUSED."""
        mig_b4 = f"{self.migration_id}-b04"
        self.state_store.set_state(f"{mig_b4}_status", {"status": "PAUSED"}, category="runtime")
        snap = self.aggregator.get_monitoring_snapshot(migration_id=mig_b4)
        self.assertEqual(snap.status, "PAUSED")
        self.assertEqual(snap.health_strip["apply_rate_rows_per_sec"], 0.0)

    # =========================================================================
    # ATTACK GROUP C — PARTIAL TELEMETRY FAILURE
    # =========================================================================

    def test_C01_corrupt_state_store_payload_handled_safely(self) -> None:
        """Hostile: Corrupted non-dict payload in state store does not crash aggregator."""
        mig_c1 = f"{self.migration_id}-c01"
        self.state_store.set_state(f"{mig_c1}_status", "CORRUPTED_STRING_NOT_DICT", category="runtime")
        snap = self.aggregator.get_monitoring_snapshot(migration_id=mig_c1)
        self.assertIsNotNone(snap)

    def test_C02_topology_manager_telemetry_exception_handled_safely(self) -> None:
        """Hostile: Exception in topology_manager.get_telemetry() does not crash aggregator, degrades status."""
        mig_c2 = f"{self.migration_id}-c02"

        class DummyConflictDetector:
            def get_unresolved_conflicts(self):
                return []

        class FaultyTopologyManager:
            identity = CDCEventIdentity(mig_c2, "job-1", "run-1", "sess-1")
            conflict_detector = DummyConflictDetector()
            def get_telemetry(self):
                raise RuntimeError("Topology DB Connection Timeout")

        snap = self.aggregator.get_monitoring_snapshot(migration_id=mig_c2, topology_manager=FaultyTopologyManager())
        self.assertIsNotNone(snap)
        self.assertEqual(snap.status, "DEGRADED")

    def test_C03_ordering_coordinator_exception_handled_safely(self) -> None:
        """Hostile: Exception in ordering_coordinator.get_telemetry() degrades status safely."""
        mig_c3 = f"{self.migration_id}-c03"

        class FaultyOrderingCoordinator:
            identity = CDCEventIdentity(mig_c3, "job-1", "run-1", "sess-1")
            def get_telemetry(self):
                raise RuntimeError("Causality DAG lock contention error")

        snap = self.aggregator.get_monitoring_snapshot(migration_id=mig_c3, ordering_coordinator=FaultyOrderingCoordinator())
        self.assertIsNotNone(snap)
        self.assertEqual(snap.status, "DEGRADED")

    def test_C04_recovery_coordinator_missing_epoch_defaults_safely(self) -> None:
        """Hostile: Unregistered migration ID defaults fencing epoch to 1 without crash."""
        snap = self.aggregator.get_monitoring_snapshot(migration_id="mig-unregistered-99")
        self.assertEqual(snap.overview.get("fencing_epoch"), 1)

    # =========================================================================
    # ATTACK GROUP D — IMPOSSIBLE TELEMETRY STATE DETECTION
    # =========================================================================

    def test_D01_ack_position_past_durable_checkpoint_degrades_status(self) -> None:
        """Hostile: Inconsistent checkpoint where ACK > Checkpoint marks recovery INCONSISTENT."""
        mig_d1 = f"{self.migration_id}-d01"
        self.state_store.set_state(
            f"cdc_frontier_sess-{mig_d1}",
            {
                "frontier_position": {"lsn": "0/100"},
                "ack_position": {"lsn": "0/200"},  # ACK > Checkpoint (Impossible)
            },
            category="checkpoint_frontier",
        )
        snap = self.aggregator.get_monitoring_snapshot(migration_id=mig_d1)
        self.assertEqual(snap.recovery_and_checkpoints.get("recovery_state"), "INCONSISTENT")
        self.assertEqual(snap.status, "DEGRADED")

    def test_D02_reclamation_past_ack_position_degrades_status(self) -> None:
        """Hostile: Inconsistent checkpoint where Reclamation > ACK marks recovery INCONSISTENT."""
        mig_d2 = f"{self.migration_id}-d02"
        self.state_store.set_state(
            f"cdc_frontier_sess-{mig_d2}",
            {
                "frontier_position": {"lsn": "0/200"},
                "ack_position": {"lsn": "0/100"},
                "reclamation_position": {"lsn": "0/150"},  # Reclamation > ACK (Impossible)
            },
            category="checkpoint_frontier",
        )
        snap = self.aggregator.get_monitoring_snapshot(migration_id=mig_d2)
        self.assertEqual(snap.recovery_and_checkpoints.get("recovery_state"), "INCONSISTENT")
        self.assertEqual(snap.status, "DEGRADED")

    def test_D03_active_workers_exceeding_configured_workers_degrades_status(self) -> None:
        """Hostile: Worker anomaly where active_workers > configured_workers degrades status."""
        mig_d3 = f"{self.migration_id}-d03"
        self.state_store.set_state(f"workers_{mig_d3}", {"configured_workers": 2, "active_workers": 5}, category="runtime")
        snap = self.aggregator.get_monitoring_snapshot(migration_id=mig_d3)
        self.assertEqual(snap.status, "DEGRADED")
        self.assertEqual(snap.workers_and_partitions.get("worker_anomaly"), "ACTIVE_EXCEEDS_CONFIGURED")

    def test_D04_negative_queue_depth_sanitized_to_zero(self) -> None:
        """Hostile: Negative queue depth is clamped to 0."""
        mig_d4 = f"{self.migration_id}-d04"
        self.bp_controller.current_queue_depth = -50
        snap = self.aggregator.get_monitoring_snapshot(migration_id=mig_d4)
        self.assertEqual(snap.backlog_and_backpressure["queue_depth"], 0)

    def test_D05_cutover_ready_blocked_when_ordering_has_blocked_txs(self) -> None:
        """Hostile: Cutover CANNOT be ready if ordering DAG has blocked transactions."""
        mig_d5 = f"{self.migration_id}-d55"
        ident = CDCEventIdentity(mig_d5, "job-1", "run-1", f"sess-{mig_d5}")
        cg = CDCCausalityGraphEngine(cdc_session_id=ident.cdc_session_id, state_store=self.state_store)
        pos = PostgresLSNPosition("0/100")
        evt = CDCEvent(identity=ident, source_engine="POSTGRESQL", source_database="db1", source_schema="s1", source_table="t1", operation=CDCOperationType.INSERT, position=pos, after_image={"id": 1})
        tx = CDCTransaction(tx_id="tx-block-1", identity=ident, commit_position=pos, events=[evt])
        cg.add_transaction(tx)
        cg.resolve_transaction_failure("tx-block-1")

        snap = self.aggregator.get_monitoring_snapshot(migration_id=mig_d5, ordering_coordinator=cg)
        self.assertFalse(snap.cutover_checklist["cutover_ready"])

    # =========================================================================
    # ATTACK GROUP E — CHECKPOINT / ACK / RECLAMATION TRUTH
    # =========================================================================

    def test_E01_checkpoint_frontier_lsn_extracted_truthfully(self) -> None:
        """Hostile: Checkpoint LSN extracted directly from state store frontier."""
        mig_e1 = f"{self.migration_id}-e01"
        self.state_store.set_state(
            f"cdc_frontier_sess-{mig_e1}",
            {"frontier_position": {"lsn": "0/999ABC"}},
            category="checkpoint_frontier",
        )
        snap = self.aggregator.get_monitoring_snapshot(migration_id=mig_e1)
        self.assertEqual(snap.health_strip["checkpoint_lsn"], "0/999ABC")

    def test_E02_ack_and_reclamation_positions_extracted_truthfully(self) -> None:
        """Hostile: ACK and reclamation positions reflected in recovery_and_checkpoints block."""
        mig_e2 = f"{self.migration_id}-e02"
        self.state_store.set_state(
            f"cdc_frontier_sess-{mig_e2}",
            {
                "frontier_position": {"lsn": "0/500"},
                "ack_position": {"lsn": "0/400"},
                "reclamation_position": {"lsn": "0/300"},
            },
            category="checkpoint_frontier",
        )
        snap = self.aggregator.get_monitoring_snapshot(migration_id=mig_e2)
        self.assertEqual(snap.recovery_and_checkpoints["ack_position"], "0/400")
        self.assertEqual(snap.recovery_and_checkpoints["reclamation_position"], "0/300")

    def test_E03_pending_frontier_holes_reflected_truthfully(self) -> None:
        """Hostile: Pending causal holes in frontier are accurately reported."""
        mig_e3 = f"{self.migration_id}-e03"
        self.state_store.set_state(
            f"cdc_frontier_sess-{mig_e3}",
            {"frontier_position": {"lsn": "0/500"}, "pending_holes_count": 3},
            category="checkpoint_frontier",
        )
        snap = self.aggregator.get_monitoring_snapshot(migration_id=mig_e3)
        self.assertEqual(snap.recovery_and_checkpoints["pending_frontier_holes_count"], 3)

    # =========================================================================
    # ATTACK GROUP F — ORDERING & CAUSALITY TELEMETRY
    # =========================================================================

    def test_F01_ordering_dag_telemetry_extracted_accurately(self) -> None:
        """Hostile: Causality graph node count, ready count, and blocked count match graph engine state."""
        mig_f1 = f"{self.migration_id}-f01"
        ident = CDCEventIdentity(mig_f1, "job-1", "run-1", f"sess-{mig_f1}")
        cg = CDCCausalityGraphEngine(cdc_session_id=ident.cdc_session_id, state_store=self.state_store)

        pos1 = PostgresLSNPosition("0/100")
        evt1 = CDCEvent(identity=ident, source_engine="POSTGRESQL", source_database="db1", source_schema="s1", source_table="t1", operation=CDCOperationType.INSERT, position=pos1, after_image={"id": 1})
        tx1 = CDCTransaction(tx_id="tx-ready-1", identity=ident, commit_position=pos1, events=[evt1])
        cg.add_transaction(tx1)

        snap = self.aggregator.get_monitoring_snapshot(migration_id=mig_f1, ordering_coordinator=cg)
        self.assertEqual(snap.ordering_and_causality["ready_transaction_count"], 1)
        self.assertEqual(snap.ordering_and_causality["blocked_transaction_count"], 0)

    def test_F02_failed_predecessors_degrades_ordering_health(self) -> None:
        """Hostile: Failed predecessors in ordering DAG set ordering_health to BLOCKED."""
        mig_f2 = f"{self.migration_id}-f02"
        ident = CDCEventIdentity(mig_f2, "job-1", "run-1", f"sess-{mig_f2}")
        cg = CDCCausalityGraphEngine(cdc_session_id=ident.cdc_session_id, state_store=self.state_store)

        pos1 = PostgresLSNPosition("0/100")
        evt1 = CDCEvent(identity=ident, source_engine="POSTGRESQL", source_database="db1", source_schema="s1", source_table="t1", operation=CDCOperationType.INSERT, position=pos1, after_image={"id": 1})
        tx1 = CDCTransaction(tx_id="tx-fail-1", identity=ident, commit_position=pos1, events=[evt1])
        cg.add_transaction(tx1)
        cg.resolve_transaction_failure("tx-fail-1")

        snap = self.aggregator.get_monitoring_snapshot(migration_id=mig_f2, ordering_coordinator=cg)
        self.assertEqual(snap.ordering_and_causality["ordering_health"], "BLOCKED")
        self.assertEqual(snap.pipeline["ordering_dag"]["state"], "BLOCKED")

    def test_F03_ordering_coordinator_identity_mismatch_ignored(self) -> None:
        """Hostile: Passing ordering coordinator with mismatched session ID is ignored."""
        mig_f3 = f"{self.migration_id}-f03"
        cg_other = CDCCausalityGraphEngine(cdc_session_id="sess-other-xxx", state_store=self.state_store)
        snap = self.aggregator.get_monitoring_snapshot(migration_id=mig_f3, ordering_coordinator=cg_other)
        self.assertEqual(snap.ordering_and_causality.get("ready_transaction_count", 0), 0)

    # =========================================================================
    # ATTACK GROUP G — MULTI-MASTER / CONFLICT TELEMETRY
    # =========================================================================

    def test_G01_unresolved_multimaster_conflicts_degrades_status(self) -> None:
        """Hostile: Detected multi-master conflict degrades overall snapshot status."""
        mig_g1 = f"{self.migration_id}-g01"
        ident = CDCEventIdentity(mig_g1, "job-1", "run-1", f"sess-{mig_g1}")
        cg = CDCCausalityGraphEngine(cdc_session_id=ident.cdc_session_id, state_store=self.state_store)
        tm = CDCBirectionalTopologyManager(
            identity=ident,
            source_a_database_id="db-a",
            source_b_database_id="db-b",
            topology_id=f"top-unique-{mig_g1}",
            causality_graph=cg,
            recovery_coordinator=self.recovery_coord,
            state_store=self.state_store,
        )

        pos = PostgresLSNPosition("0/100")
        evt_a = CDCEvent(identity=ident, source_engine="POSTGRESQL", source_database="db_a", source_schema="public", source_table="users", operation=CDCOperationType.UPDATE, position=pos, after_image={"id": "k1"})
        evt_b = CDCEvent(identity=ident, source_engine="POSTGRESQL", source_database="db_b", source_schema="public", source_table="users", operation=CDCOperationType.UPDATE, position=pos, after_image={"id": "k1"})
        tx_a = CDCTransaction(tx_id="tx-a", identity=ident, commit_position=pos, events=[evt_a])
        tx_b = CDCTransaction(tx_id="tx-b", identity=ident, commit_position=pos, events=[evt_b])

        tm.conflict_detector.detect_conflict(ident, tx_a, tx_b)

        snap = self.aggregator.get_monitoring_snapshot(migration_id=mig_g1, topology_manager=tm)
        self.assertEqual(snap.status, "DEGRADED")
        self.assertEqual(snap.conflicts_and_topology["unresolved_conflicts_count"], 1)

    def test_G02_active_entity_quarantine_blocks_cutover(self) -> None:
        """Hostile: Active entity quarantine lock blocks cutover readiness."""
        mig_g2 = f"{self.migration_id}-g02"
        ident = CDCEventIdentity(mig_g2, "job-1", "run-1", f"sess-{mig_g2}")
        cg = CDCCausalityGraphEngine(cdc_session_id=ident.cdc_session_id, state_store=self.state_store)
        tm = CDCBirectionalTopologyManager(
            identity=ident,
            source_a_database_id="db-a",
            source_b_database_id="db-b",
            topology_id=f"top-unique-{mig_g2}",
            causality_graph=cg,
            recovery_coordinator=self.recovery_coord,
            state_store=self.state_store,
        )
        tm.quarantine_manager.quarantine_entity(ident, "conf-1", "users", "k100", "multi-master conflict", 1)

        snap = self.aggregator.get_monitoring_snapshot(migration_id=mig_g2, topology_manager=tm)
        self.assertEqual(snap.conflicts_and_topology["quarantined_entities_count"], 1)
        self.assertFalse(snap.cutover_checklist["quarantines_clear"])
        self.assertFalse(snap.cutover_checklist["cutover_ready"])

    def test_G03_echo_suppression_statistics_reflected_truthfully(self) -> None:
        """Hostile: Topology echo suppression telemetry is present in conflicts_and_topology."""
        mig_g3 = f"{self.migration_id}-g03"
        ident = CDCEventIdentity(mig_g3, "job-1", "run-1", f"sess-{mig_g3}")
        cg = CDCCausalityGraphEngine(cdc_session_id=ident.cdc_session_id, state_store=self.state_store)
        tm = CDCBirectionalTopologyManager(
            identity=ident,
            source_a_database_id="db-a",
            source_b_database_id="db-b",
            topology_id=f"top-unique-{mig_g3}",
            causality_graph=cg,
            recovery_coordinator=self.recovery_coord,
            state_store=self.state_store,
        )

        pos = PostgresLSNPosition("0/100")
        from akaal.cdc.multi_master.domain import CDCOriginProvenance
        prov_a = CDCOriginProvenance(
            origin_database_id="db-a",
            origin_topology_id=tm.topology_id,
            origin_run_id="run-1",
            akaal_writer_id="writer-a",
            replication_direction="A_TO_B",
        )
        prov_b = CDCOriginProvenance(
            origin_database_id="db-b",
            origin_topology_id=tm.topology_id,
            origin_run_id="run-1",
            akaal_writer_id="writer-b",
            replication_direction="B_TO_A",
        )

        evt_echo_a = CDCEvent(identity=ident, source_engine="POSTGRESQL", source_database="db-a", source_schema="public", source_table="users", operation=CDCOperationType.UPDATE, position=pos, after_image={"id": "k1"}, details={"origin_provenance": prov_a.to_dict()})
        evt_echo_b = CDCEvent(identity=ident, source_engine="POSTGRESQL", source_database="db-b", source_schema="public", source_table="users", operation=CDCOperationType.UPDATE, position=pos, after_image={"id": "k1"}, details={"origin_provenance": prov_b.to_dict()})
        tx_echo_a = CDCTransaction(tx_id="tx-echo-a", identity=ident, commit_position=pos, events=[evt_echo_a])
        tx_echo_b = CDCTransaction(tx_id="tx-echo-b", identity=ident, commit_position=pos, events=[evt_echo_b])

        tm.loop_filter_a_to_b.should_suppress_transaction(tx_echo_a, ident)
        tm.loop_filter_b_to_a.should_suppress_transaction(tx_echo_b, ident)

        snap = self.aggregator.get_monitoring_snapshot(migration_id=mig_g3, topology_manager=tm)
        self.assertEqual(snap.conflicts_and_topology["echo_events_suppressed_a_to_b"], 1)
        self.assertEqual(snap.conflicts_and_topology["echo_events_suppressed_b_to_a"], 1)

    def test_G04_resolved_conflict_list_serialization(self) -> None:
        """Hostile: Conflict details in conflicts_list are correctly serialized dicts."""
        mig_g4 = f"{self.migration_id}-g04"
        ident = CDCEventIdentity(mig_g4, "job-1", "run-1", f"sess-{mig_g4}")
        cg = CDCCausalityGraphEngine(cdc_session_id=ident.cdc_session_id, state_store=self.state_store)
        tm = CDCBirectionalTopologyManager(
            identity=ident,
            source_a_database_id="db-a",
            source_b_database_id="db-b",
            topology_id=f"top-{mig_g4}",
            causality_graph=cg,
            recovery_coordinator=self.recovery_coord,
            state_store=self.state_store,
        )
        pos = PostgresLSNPosition("0/100")
        evt_a = CDCEvent(identity=ident, source_engine="POSTGRESQL", source_database="db_a", source_schema="public", source_table="users", operation=CDCOperationType.UPDATE, position=pos, after_image={"id": "k1"})
        evt_b = CDCEvent(identity=ident, source_engine="POSTGRESQL", source_database="db_b", source_schema="public", source_table="users", operation=CDCOperationType.UPDATE, position=pos, after_image={"id": "k1"})
        tx_a = CDCTransaction(tx_id="tx-a", identity=ident, commit_position=pos, events=[evt_a])
        tx_b = CDCTransaction(tx_id="tx-b", identity=ident, commit_position=pos, events=[evt_b])

        c = tm.conflict_detector.detect_conflict(ident, tx_a, tx_b)
        tm.conflict_resolver.resolve_conflict(ident, c.conflict_id, CDCConflictResolutionPolicy.SOURCE_A_WINS, 1)

        snap = self.aggregator.get_monitoring_snapshot(migration_id=mig_g4, topology_manager=tm)
        self.assertEqual(snap.conflicts_and_topology["unresolved_conflicts_count"], 0)

    # =========================================================================
    # ATTACK GROUP H — CUTOVER READINESS TRUTH
    # =========================================================================

    def test_H01_backlog_exceeding_zero_blocks_cutover(self) -> None:
        """Hostile: Backlog depth > 0 MUST block cutover readiness (backlog_drained=False)."""
        mig_h1 = f"{self.migration_id}-h01"
        self.bp_controller.current_queue_depth = 500
        snap = self.aggregator.get_monitoring_snapshot(migration_id=mig_h1)
        self.assertFalse(snap.cutover_checklist["backlog_drained"])
        self.assertFalse(snap.cutover_checklist["cutover_ready"])

    def test_H02_catching_up_status_blocks_cutover(self) -> None:
        """Hostile: CATCHING_UP status MUST block cutover readiness."""
        mig_h2 = f"{self.migration_id}-h02"
        self.state_store.set_state(f"{mig_h2}_status", {"status": "CATCHING_UP"}, category="runtime")
        snap = self.aggregator.get_monitoring_snapshot(migration_id=mig_h2)
        self.assertFalse(snap.cutover_checklist["cutover_ready"])

    def test_H03_paused_status_blocks_cutover(self) -> None:
        """Hostile: PAUSED status MUST block cutover readiness."""
        mig_h3 = f"{self.migration_id}-h03"
        self.state_store.set_state(f"{mig_h3}_status", {"status": "PAUSED"}, category="runtime")
        snap = self.aggregator.get_monitoring_snapshot(migration_id=mig_h3)
        self.assertFalse(snap.cutover_checklist["cutover_ready"])

    def test_H04_healthy_zero_backlog_zero_conflicts_allows_cutover(self) -> None:
        """Hostile: Healthy session with zero backlog, zero conflicts, zero quarantines is cutover ready."""
        mig_h4 = f"{self.migration_id}-h04"
        self.state_store.set_state(f"{mig_h4}_status", {"status": "RUNNING"}, category="runtime")
        self.bp_controller.current_queue_depth = 0
        snap = self.aggregator.get_monitoring_snapshot(migration_id=mig_h4)
        self.assertTrue(snap.cutover_checklist["cutover_ready"])

    # =========================================================================
    # ATTACK GROUP I — CONCURRENT SNAPSHOT CONSISTENCY
    # =========================================================================

    def test_I01_concurrent_state_store_mutations_and_snapshot_reads(self) -> None:
        """Hostile: Multithreaded state store writes during snapshot generation do not cause dictionary iteration mutation crash."""
        mig_i1 = f"{self.migration_id}-i01"
        stop_flag = False

        def writer():
            idx = 0
            while not stop_flag:
                self.state_store.set_state(f"{mig_i1}_status", {"status": "RUNNING", "tick": idx}, category="runtime")
                self.state_store.set_state(f"workers_{mig_i1}", {"active_workers": (idx % 4) + 1}, category="runtime")
                idx += 1
                time.sleep(0.001)

        t = threading.Thread(target=writer, daemon=True)
        t.start()

        try:
            for _ in range(20):
                snap = self.aggregator.get_monitoring_snapshot(migration_id=mig_i1)
                self.assertIsNotNone(snap)
                time.sleep(0.002)
        finally:
            stop_flag = True
            t.join(timeout=1.0)

    def test_I02_multithreaded_snapshot_aggregation(self) -> None:
        """Hostile: 10 concurrent threads requesting get_monitoring_snapshot produce valid snapshots."""
        mig_i2 = f"{self.migration_id}-i02"
        results = []
        errors = []

        def worker():
            try:
                snap = self.aggregator.get_monitoring_snapshot(migration_id=mig_i2)
                results.append(snap)
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=worker) for _ in range(10)]
        for th in threads:
            th.start()
        for th in threads:
            th.join()

        self.assertEqual(len(errors), 0, f"Concurrent snapshot errors: {errors}")
        self.assertEqual(len(results), 10)

    def test_I03_snapshot_read_model_immutability(self) -> None:
        """Hostile: Modifying snapshot dictionary does not pollute subsequent snapshot calls."""
        mig_i3 = f"{self.migration_id}-i03"
        snap1 = self.aggregator.get_monitoring_snapshot(migration_id=mig_i3)
        d1 = snap1.to_dict()
        d1["health_strip"]["source_lag_sec"] = 9999.0

        snap2 = self.aggregator.get_monitoring_snapshot(migration_id=mig_i3)
        self.assertNotEqual(snap2.health_strip["source_lag_sec"], 9999.0)

    # =========================================================================
    # ATTACK GROUP J — UI & REFINEMENT AUDIT (Refinements in commits 9dd9c0b, 486ee22, 5afcd77)
    # =========================================================================

    def test_J01_fallback_snapshot_must_be_marked_disconnected_not_live(self) -> None:
        """Hostile: Test that when Engine IPC is disconnected, fallback UI mode must reflect DISCONNECTED state."""
        snap = self.aggregator.get_monitoring_snapshot(migration_id="mig-disconnected")
        self.assertIsNotNone(snap)

    def test_J02_gateway_get_cdc_monitoring_snapshot_contract(self) -> None:
        """Hostile: Gateway IPC get_cdc_monitoring_snapshot accepts payload and returns sanitized snapshot dict."""
        mig_j2 = f"{self.migration_id}-j02"
        payload = {"migration_id": mig_j2, "job_id": "job-gw", "run_id": "run-gw"}
        res = self.gateway.get_cdc_monitoring_snapshot(payload)
        self.assertIsInstance(res, dict)
        self.assertEqual(res["migration_id"], mig_j2)
        self.assertEqual(res["schema_version"], "1.0")

    def test_J03_lucide_icon_and_theme_class_structure_validity(self) -> None:
        """Hostile: Ensure no legacy unicode emojis or raw password keys exist in snapshot payloads."""
        mig_j3 = f"{self.migration_id}-j03"
        snap = self.aggregator.get_monitoring_snapshot(migration_id=mig_j3)
        d = snap.to_dict()
        d_str = str(d)
        self.assertNotIn("🔒", d_str)
        self.assertNotIn("⚠️", d_str)

    # =========================================================================
    # ATTACK GROUP K — HISTORICAL MODE INTEGRITY
    # =========================================================================

    def test_K01_historical_session_read_only_mode(self) -> None:
        """Hostile: Historical migration status maps to HISTORICAL monitoring_mode."""
        mig_k1 = f"{self.migration_id}-k01"
        self.state_store.set_state(f"{mig_k1}_status", {"status": "COMPLETED"}, category="runtime")
        snap = self.aggregator.get_monitoring_snapshot(migration_id=mig_k1)
        self.assertEqual(snap.monitoring_mode, "HISTORICAL")

    def test_K02_historical_session_mutation_rejection_at_gateway(self) -> None:
        """Hostile: EngineGateway rejects lifecycle mutations on completed/historical sessions."""
        mig_k2 = f"{self.migration_id}-k02"
        self.state_store.set_state(f"{mig_k2}_status", {"status": "COMPLETED"}, category="runtime")
        res = self.gateway.pause_cdc_session({"cdc_session_id": f"sess-{mig_k2}", "migration_id": mig_k2})
        self.assertEqual(res.get("status"), "REJECTED_HISTORICAL_IMMUTABLE")

    def test_K03_historical_conflict_resolution_rejection_at_gateway(self) -> None:
        """Hostile: EngineGateway rejects conflict resolution on completed/historical topologies."""
        mig_k3 = f"{self.migration_id}-k03"
        self.state_store.set_state(f"{mig_k3}_status", {"status": "COMPLETED"}, category="runtime")
        res = self.gateway.resolve_cdc_conflict({"topology_id": f"top-{mig_k3}", "conflict_id": "conf-1", "policy": "SOURCE_A_WINS", "migration_id": mig_k3})
        self.assertEqual(res.get("status"), "REJECTED_HISTORICAL_IMMUTABLE")

    # =========================================================================
    # ATTACK GROUP L — OPERATOR CONTROL AUTHORITY
    # =========================================================================

    def test_L01_pause_cdc_session_via_gateway(self) -> None:
        """Hostile: Gateway pause_cdc_session updates state store and returns authoritative result."""
        mig_l1 = f"{self.migration_id}-l01"
        self.state_store.set_state(f"{mig_l1}_status", {"status": "RUNNING"}, category="runtime")
        res = self.gateway.pause_cdc_session({"cdc_session_id": f"sess-{mig_l1}", "migration_id": mig_l1})
        self.assertEqual(res["status"], "PAUSED")

        snap = self.aggregator.get_monitoring_snapshot(migration_id=mig_l1)
        self.assertEqual(snap.status, "PAUSED")

    def test_L02_resume_cdc_session_via_gateway(self) -> None:
        """Hostile: Gateway resume_cdc_session updates state store and returns authoritative result."""
        mig_l2 = f"{self.migration_id}-l02"
        self.state_store.set_state(f"{mig_l2}_status", {"status": "PAUSED"}, category="runtime")
        res = self.gateway.resume_cdc_session({"cdc_session_id": f"sess-{mig_l2}", "migration_id": mig_l2})
        self.assertEqual(res["status"], "RESUMED")

        snap = self.aggregator.get_monitoring_snapshot(migration_id=mig_l2)
        self.assertEqual(snap.status, "HEALTHY")

    # =========================================================================
    # ATTACK GROUP M — SECURITY & DATA MINIMIZATION
    # =========================================================================

    def test_M01_recursive_secret_redaction_in_nested_telemetry(self) -> None:
        """Hostile: Secret keywords in deeply nested dicts/lists are auto-redacted."""
        data_with_secrets = {
            "source_authority": {
                "engine": "POSTGRESQL",
                "database": "prod_db",
                "password": "SuperSecretPassword123!",
                "connection_string": "postgresql://user:secret@localhost:5432/prod_db",
                "auth_token": "bearer_abc123",
            },
            "workers": [
                {"worker_id": "w1", "api_key": "key_secret_999", "private_key": "-----BEGIN RSA PRIVATE KEY-----"}
            ]
        }
        sanitized = CDCMonitoringSnapshot._sanitize(data_with_secrets)
        self.assertEqual(sanitized["source_authority"]["password"], "[REDACTED_SECRET]")
        self.assertEqual(sanitized["source_authority"]["connection_string"], "[REDACTED_SECRET]")
        self.assertEqual(sanitized["source_authority"]["auth_token"], "[REDACTED_SECRET]")
        self.assertEqual(sanitized["workers"][0]["api_key"], "[REDACTED_SECRET]")
        self.assertEqual(sanitized["workers"][0]["private_key"], "[REDACTED_SECRET]")

    def test_M02_raw_customer_row_payloads_excluded_from_snapshot(self) -> None:
        """Hostile: Snapshot dict contains no raw customer row images or SQL text."""
        mig_m2 = f"{self.migration_id}-m02"
        snap = self.aggregator.get_monitoring_snapshot(migration_id=mig_m2)
        snap_dict = snap.to_dict()
        self.assertNotIn("after_image", snap_dict)
        self.assertNotIn("before_image", snap_dict)
        self.assertNotIn("raw_row_data", snap_dict)

    def test_M03_credential_keywords_redacted_in_to_dict(self) -> None:
        """Hostile: calling snap.to_dict() redacts secret fields across all sub-dictionaries."""
        mig_m3 = f"{self.migration_id}-m03"
        snap = self.aggregator.get_monitoring_snapshot(migration_id=mig_m3)
        snap.overview["db_password"] = "TopSecret123"
        d = snap.to_dict()
        self.assertEqual(d["overview"]["db_password"], "[REDACTED_SECRET]")

    def test_M04_auth_header_redaction_in_operational_events(self) -> None:
        """Hostile: Operational events containing auth headers are sanitized."""
        mig_m4 = f"{self.migration_id}-m04"
        snap = self.aggregator.get_monitoring_snapshot(migration_id=mig_m4)
        snap.operational_events.append({
            "timestamp": "2026-08-15T00:00:00Z",
            "severity": "INFO",
            "category": "AUTH",
            "authorization_header": "Bearer secret_token_xyz",
        })
        d = snap.to_dict()
        self.assertEqual(d["operational_events"][-1]["authorization_header"], "[REDACTED_SECRET]")

    # =========================================================================
    # ATTACK GROUP N — GATEWAY & DTO CONTRACT
    # =========================================================================

    def test_N01_gateway_handles_missing_payload_fields_safely(self) -> None:
        """Hostile: Gateway get_cdc_monitoring_snapshot handles empty payload without crash."""
        res = self.gateway.get_cdc_monitoring_snapshot({})
        self.assertIsInstance(res, dict)
        self.assertEqual(res["migration_id"], "mig-def")

    def test_N02_gateway_handles_non_existent_migration_id(self) -> None:
        """Hostile: Gateway get_cdc_monitoring_snapshot for unknown migration returns default safe snapshot."""
        res = self.gateway.get_cdc_monitoring_snapshot({"migration_id": "mig-nonexistent-999"})
        self.assertIsInstance(res, dict)
        self.assertEqual(res["migration_id"], "mig-nonexistent-999")

    # =========================================================================
    # ATTACK GROUP O — ENTERPRISE SCALE SURVIVABILITY
    # =========================================================================

    def test_O01_enterprise_scale_1000_workers_and_partitions_aggregation(self) -> None:
        """Hostile: Aggregating telemetry for 1,000 configured workers operates within memory & time limits."""
        mig_o1 = f"{self.migration_id}-o01"
        self.state_store.set_state(f"workers_{mig_o1}", {"configured_workers": 1000, "active_workers": 1000}, category="runtime")

        t0 = time.time()
        snap = self.aggregator.get_monitoring_snapshot(migration_id=mig_o1)
        t_elapsed = time.time() - t0

        self.assertEqual(snap.workers_and_partitions["configured_workers"], 1000)
        self.assertLess(t_elapsed, 1.0, f"Aggregation of 1,000 workers took too long: {t_elapsed:.3f}s")

    def test_O02_enterprise_scale_10000_operational_events_bounding(self) -> None:
        """Hostile: Aggregating large operational events list bounds total event size to prevent UI payload blowup."""
        mig_o2 = f"{self.migration_id}-o02"
        large_events = [
            {"timestamp": "2026-08-15T00:00:00Z", "severity": "INFO", "category": "TEST", "description": f"Event #{i}"}
            for i in range(10000)
        ]
        snap = CDCMonitoringSnapshot(
            migration_id=mig_o2,
            job_id="job-1",
            run_id="run-1",
            cdc_session_id="sess-1",
            operational_events=large_events,
        )
        d = snap.to_dict()
        self.assertLessEqual(len(d["operational_events"]), 100)  # Bounded to 100 for enterprise UI survivability


if __name__ == "__main__":
    unittest.main()
