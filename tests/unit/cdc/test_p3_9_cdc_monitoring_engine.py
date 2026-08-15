"""
AKAAL CDC Monitoring, Telemetry Aggregation & Enterprise Inspection Engine Tests (P3.9).
==========================================================================================
Verifies backend-authoritative read model CDCMonitoringSnapshot, CDCMonitoringAggregator,
EngineGateway integration, secrets redaction, cutover checklist evaluation, and hostile telemetry edge cases.
"""

import unittest
import json
import tempfile
import shutil
from typing import Dict, Any

from akaal.cdc.monitoring.domain import CDCMonitoringSnapshot
from akaal.cdc.monitoring.aggregator import CDCMonitoringAggregator
from akaal.core.state.state_store import CentralStateStore
from akaal.runtime.recovery.coordinator import RecoveryCoordinator
from akaal.streaming.flow.backpressure import BackpressureController
from akaal.gateway.engine_gateway import EngineGateway
from akaal.cdc.multi_master.topology import CDCBirectionalTopologyManager
from akaal.cdc.multi_master.conflict_detector import CDCConflictDetector
from akaal.cdc.multi_master.quarantine import CDCConflictQuarantineManager
from akaal.cdc.ordering.causality import CDCCausalityGraphEngine
from akaal.cdc.domain.events import CDCTransaction, CDCEvent, CDCOperationType, CDCEventIdentity
from akaal.cdc.multi_master.domain import CDCConflictType


class TestP39CDCMonitoringEngine(unittest.TestCase):
    """Dedicated P3.9 CDC Monitoring & Telemetry Test Suite."""

    def setUp(self) -> None:
        self.test_dir = tempfile.mkdtemp()
        self.state_store = CentralStateStore(db_path=f"{self.test_dir}/state.db")
        self.recovery_coord = RecoveryCoordinator()
        self.bp_controller = BackpressureController()
        self.aggregator = CDCMonitoringAggregator(
            state_store=self.state_store,
            recovery_coordinator=self.recovery_coord,
            backpressure_controller=self.bp_controller,
        )
        self.gateway = EngineGateway()
        self.migration_id = "mig-p39-test"

    def tearDown(self) -> None:
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_01_healthy_cdc_snapshot_aggregation(self) -> None:
        """Test healthy snapshot generation from backend authorities."""
        snap = self.aggregator.get_monitoring_snapshot(migration_id=self.migration_id)
        self.assertEqual(snap.migration_id, self.migration_id)
        self.assertEqual(snap.monitoring_mode, "LIVE")
        self.assertEqual(snap.status, "HEALTHY")
        self.assertEqual(snap.health_strip["cdc_state"], "HEALTHY")
        self.assertTrue(snap.cutover_checklist["cutover_ready"])

    def test_02_catchup_state_and_high_lag(self) -> None:
        """Test catchup state and lag evaluation."""
        self.state_store.set_state(f"{self.migration_id}_status", {"status": "CATCHING_UP"}, category="runtime")
        snap = self.aggregator.get_monitoring_snapshot(migration_id=self.migration_id)
        self.assertEqual(snap.status, "CATCHING_UP")
        self.assertEqual(snap.pipeline["source_capture"]["state"], "HEALTHY")

    def test_03_backpressure_active_and_backlog_critical(self) -> None:
        """Test backpressure state propagation to monitoring snapshot."""
        self.bp_controller.current_queue_depth = 950
        self.bp_controller.max_queue_depth = 1000
        snap = self.aggregator.get_monitoring_snapshot(migration_id=self.migration_id)
        self.assertEqual(snap.backlog_and_backpressure["queue_depth"], 950)
        self.assertEqual(snap.backlog_and_backpressure["utilization_pct"], 95.0)

    def test_04_worker_and_partition_telemetry(self) -> None:
        """Test worker and partition telemetry structure."""
        self.state_store.set_state(f"workers_{self.migration_id}", {"configured_workers": 8, "active_workers": 8}, category="runtime")
        snap = self.aggregator.get_monitoring_snapshot(migration_id=self.migration_id)
        self.assertEqual(snap.workers_and_partitions["configured_workers"], 8)
        self.assertEqual(len(snap.workers_and_partitions["worker_statuses"]), 8)

    def test_05_ordering_causality_blocker(self) -> None:
        """Test ordering DAG blocked transactions telemetry."""
        from akaal.cdc.domain.positions import PostgresLSNPosition
        pos = PostgresLSNPosition("0/100")
        cg = CDCCausalityGraphEngine(cdc_session_id="sess-1", state_store=self.state_store)
        cg.add_transaction(CDCTransaction(tx_id="tx-p39-block", identity=CDCEventIdentity(self.migration_id, "job-1", "run-1", "sess-1"), commit_position=pos, events=[]))
        cg.failed_txs.add("tx-p39-block")

        class DummyCoordinator:
            def __init__(self, graph):
                self.causality_graph = graph
            def get_telemetry(self):
                return {
                    "causal_graph_summary": {
                        "total_nodes": 1,
                        "blocked_count": 0,
                        "ready_count": 0,
                        "failed_predecessor_count": len(self.causality_graph.failed_txs),
                    }
                }

        coord = DummyCoordinator(cg)
        snap = self.aggregator.get_monitoring_snapshot(migration_id=self.migration_id, ordering_coordinator=coord)
        self.assertEqual(snap.ordering_and_causality["failed_predecessors_count"], 1)

    def test_06_unresolved_multimaster_conflicts_degrades_status_and_blocks_cutover(self) -> None:
        """Test unresolved conflict detection degrades state and blocks cutover."""
        from akaal.cdc.domain.positions import PostgresLSNPosition
        pos = PostgresLSNPosition("0/100")
        self.state_store.set_state(f"{self.migration_id}_status", {"status": "RUNNING"}, category="runtime")
        ident = CDCEventIdentity(self.migration_id, "job-1", "run-1", "sess-1")
        cg = CDCCausalityGraphEngine(cdc_session_id="sess-1", state_store=self.state_store)
        tm = CDCBirectionalTopologyManager(
            identity=ident,
            source_a_database_id="node-a",
            source_b_database_id="node-b",
            topology_id="top-p39",
            causality_graph=cg,
            recovery_coordinator=self.recovery_coord,
            state_store=self.state_store,
        )

        evt_a = CDCEvent(identity=ident, source_engine="POSTGRESQL", source_database="db_a", source_schema="public", source_table="users", operation=CDCOperationType.UPDATE, position=pos, after_image={"id": "k1"})
        evt_b = CDCEvent(identity=ident, source_engine="POSTGRESQL", source_database="db_b", source_schema="public", source_table="users", operation=CDCOperationType.UPDATE, position=pos, after_image={"id": "k1"})
        tx_a = CDCTransaction(tx_id="tx-a", identity=ident, commit_position=pos, events=[evt_a])
        tx_b = CDCTransaction(tx_id="tx-b", identity=ident, commit_position=pos, events=[evt_b])

        tm.conflict_detector.detect_conflict(ident, tx_a, tx_b)

        snap = self.aggregator.get_monitoring_snapshot(migration_id=self.migration_id, topology_manager=tm)
        self.assertEqual(snap.conflicts_and_topology["unresolved_conflicts_count"], 1)
        self.assertEqual(snap.status, "DEGRADED")
        self.assertFalse(snap.cutover_checklist["cutover_ready"])
        self.assertFalse(snap.cutover_checklist["conflicts_resolved"])

    def test_07_quarantine_active_blocks_cutover(self) -> None:
        """Test quarantined entity blocks cutover readiness."""
        ident = CDCEventIdentity(self.migration_id, "job-1", "run-1", "sess-1")
        cg = CDCCausalityGraphEngine(cdc_session_id="sess-1", state_store=self.state_store)
        tm = CDCBirectionalTopologyManager(
            identity=ident,
            source_a_database_id="node-a",
            source_b_database_id="node-b",
            topology_id="top-p39-q",
            causality_graph=cg,
            recovery_coordinator=self.recovery_coord,
            state_store=self.state_store,
        )

        tm.quarantine_manager.quarantine_entity(ident, "conf-100", "users", "100", "multi-master conflict", 1)

        snap = self.aggregator.get_monitoring_snapshot(migration_id=self.migration_id, topology_manager=tm)
        self.assertEqual(snap.conflicts_and_topology["quarantined_entities_count"], 1)
        self.assertFalse(snap.cutover_checklist["quarantines_clear"])

    def test_08_secrets_redaction_in_snapshot(self) -> None:
        """Test safe-by-default redaction of sensitive credentials."""
        raw_dict = {
            "password": "SuperSecretPassword123!",
            "connection_string": "postgres://admin:secret@localhost:5432/db",
            "normal_field": "public_value",
        }
        sanitized = CDCMonitoringSnapshot._sanitize(raw_dict)
        self.assertEqual(sanitized["password"], "[REDACTED_SECRET]")
        self.assertEqual(sanitized["connection_string"], "[REDACTED_SECRET]")
        self.assertEqual(sanitized["normal_field"], "public_value")

    def test_09_gateway_integration(self) -> None:
        """Test EngineGateway get_cdc_monitoring_snapshot capability."""
        res = self.gateway.get_cdc_monitoring_snapshot({"migration_id": self.migration_id})
        self.assertEqual(res["migration_id"], self.migration_id)
        self.assertIn("health_strip", res)
        self.assertIn("pipeline", res)
        self.assertIn("cutover_checklist", res)

    def test_10_read_model_does_not_mutate_runtime_state(self) -> None:
        """Test that generating a monitoring snapshot does not mutate backend state."""
        state_before = self.state_store.get_state(f"{self.migration_id}_status", category="runtime")
        _ = self.aggregator.get_monitoring_snapshot(migration_id=self.migration_id)
        state_after = self.state_store.get_state(f"{self.migration_id}_status", category="runtime")
        self.assertEqual(state_before, state_after)

    def test_11_historical_mode_read_only(self) -> None:
        """Test snapshot detection for historical completed migration."""
        self.state_store.set_state(f"{self.migration_id}_status", {"status": "COMPLETED"}, category="runtime")
        snap = self.aggregator.get_monitoring_snapshot(migration_id=self.migration_id)
        self.assertEqual(snap.monitoring_mode, "HISTORICAL")


if __name__ == "__main__":
    unittest.main()
