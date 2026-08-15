"""
AKAAL Day 29 — P3.8 CDC Multi-Master & Bidirectional Replication Engine Acceptance Suite.
==========================================================================================
Comprehensive unit & integration acceptance suite for P3.8 covering bidirectional topology management,
loop/echo filter suppression, multi-master conflict detection, deterministic conflict resolution policies,
entity quarantine locks, fencing token validation, process restart recovery, and EngineGateway IPC integration.
"""

import os
import uuid
import tempfile
import unittest
from typing import Dict, Any, List

from akaal.cdc.domain.events import CDCEventIdentity, CDCEvent, CDCTransaction, CDCOperationType
from akaal.cdc.domain.positions import PostgresLSNPosition
from akaal.cdc.domain.errors import CDCExecutionError, CDCFailureType
from akaal.cdc.multi_master.domain import (
    CDCReplicationTopology,
    CDCReplicationTopologyState,
    CDCReplicationDirection,
    CDCDirectionState,
    CDCOriginProvenance,
    CDCConflictRecord,
    CDCConflictType,
    CDCConflictState,
    CDCConflictResolutionPolicy,
    CDCConflictResolutionDecision,
    CDCQuarantineRecord,
    CDCQuarantineState,
)
from akaal.cdc.multi_master.loop_filter import CDCReplicationLoopFilter
from akaal.cdc.multi_master.conflict_detector import CDCConflictDetector
from akaal.cdc.multi_master.resolver import CDCConflictResolver
from akaal.cdc.multi_master.quarantine import CDCConflictQuarantineManager
from akaal.cdc.multi_master.topology import CDCBirectionalTopologyManager
from akaal.cdc.ordering.causality import CDCCausalityGraphEngine
from akaal.gateway.engine_gateway import EngineGateway
from akaal.core.state.state_store import CentralStateStore
from akaal.runtime.recovery.coordinator import RecoveryCoordinator


class TestP38CDCMultiMasterConflictEngine(unittest.TestCase):

    def setUp(self):
        self.migration_id = f"mig-p38-{uuid.uuid4().hex[:6]}"
        self.job_id = "job-p38-test"
        self.run_id = "run-p38-test"
        self.cdc_session_id = f"sess-p38-{uuid.uuid4().hex[:6]}"
        self.identity = CDCEventIdentity(self.migration_id, self.job_id, self.run_id, self.cdc_session_id)

        self.state_store = CentralStateStore()
        self.recovery_coord = RecoveryCoordinator()
        self.fencing_epoch = self.recovery_coord.issue_epoch(self.migration_id)

        self.source_a_db = "db_node_a"
        self.source_b_db = "db_node_b"

        self.topology_mgr = CDCBirectionalTopologyManager(
            identity=self.identity,
            source_a_database_id=self.source_a_db,
            source_b_database_id=self.source_b_db,
            designated_primary_database_id=self.source_a_db,
            state_store=self.state_store,
            recovery_coordinator=self.recovery_coord,
        )

    def _make_event(
        self,
        seq: int,
        table_name: str = "users",
        entity_key: str = "100",
        op: CDCOperationType = CDCOperationType.UPDATE,
        details: Dict[str, Any] = None,
    ) -> CDCEvent:
        return CDCEvent(
            identity=self.identity,
            source_engine="POSTGRESQL",
            source_database="db",
            source_schema="public",
            source_table=table_name,
            operation=op,
            position=PostgresLSNPosition(f"0/{seq*100:X}"),
            before_image={"id": entity_key, "val": f"old_{seq}"},
            after_image={"id": entity_key, "val": f"new_{seq}"},
            details=details or {},
        )

    def _make_tx(self, tx_id: str, events: List[CDCEvent], pos_seq: int = 1) -> CDCTransaction:
        return CDCTransaction(
            identity=self.identity,
            tx_id=tx_id,
            events=events,
            commit_position=PostgresLSNPosition(f"0/{pos_seq*100:X}"),
        )

    # 1. Topology lifecycle states
    def test_01_topology_initialization_and_states(self):
        top = self.topology_mgr.topology
        self.assertEqual(top.state, CDCReplicationTopologyState.ACTIVE)
        self.assertEqual(top.source_a_database_id, self.source_a_db)
        self.assertEqual(top.source_b_database_id, self.source_b_db)

    # 2. Dual-stream state tracking
    def test_02_dual_stream_direction_tracking(self):
        top = self.topology_mgr.topology
        self.assertIsNotNone(top.direction_a_to_b)
        self.assertIsNotNone(top.direction_b_to_a)
        self.assertEqual(top.direction_a_to_b.source_database_id, self.source_a_db)
        self.assertEqual(top.direction_b_to_a.source_database_id, self.source_b_db)

    # 3. Topology pause and resume with fencing epoch
    def test_03_topology_pause_and_resume(self):
        paused_top = self.topology_mgr.pause_topology(self.fencing_epoch)
        self.assertEqual(paused_top.state, CDCReplicationTopologyState.PAUSED)

        resumed_top = self.topology_mgr.resume_topology(self.fencing_epoch)
        self.assertEqual(resumed_top.state, CDCReplicationTopologyState.ACTIVE)

    # 4. Stale fencing token pause rejection
    def test_04_stale_fencing_token_pause_rejection(self):
        new_epoch = self.recovery_coord.issue_epoch(self.migration_id)
        with self.assertRaises(CDCExecutionError) as ctx:
            self.topology_mgr.pause_topology(self.fencing_epoch)  # Stale epoch 1 vs active epoch 2
        self.assertEqual(ctx.exception.failure.failure_type.value, "STALE_WORKER")

    # 5. Loop filter provenance attachment
    def test_05_loop_filter_attach_provenance(self):
        lf = self.topology_mgr.loop_filter_a_to_b
        tx = self._make_tx("tx-lf-1", [self._make_event(1)])
        tagged_tx = lf.attach_origin_provenance(tx, "A_TO_B")

        prov_dict = tagged_tx.events[0].details.get("origin_provenance")
        self.assertIsNotNone(prov_dict)
        self.assertEqual(prov_dict["origin_database_id"], self.source_a_db)

    # 6. A -> B -> A Echo Event Suppression
    def test_06_echo_event_suppression(self):
        lf_a_b = self.topology_mgr.loop_filter_a_to_b
        tx = self._make_tx("tx-echo-1", [self._make_event(1)])
        tagged_tx = lf_a_b.attach_origin_provenance(tx, "A_TO_B")

        # When Node A loop filter evaluates tagged transaction that originated from Node A
        should_suppress = lf_a_b.should_suppress_transaction(tagged_tx, self.identity)
        self.assertTrue(should_suppress)
        self.assertEqual(lf_a_b.echo_events_suppressed_count, 1)

    # 7. Legitimate local mutation non-suppression
    def test_07_legitimate_local_mutation_non_suppression(self):
        lf_a_b = self.topology_mgr.loop_filter_a_to_b
        tx_native = self._make_tx("tx-native-1", [self._make_event(1)])  # No origin tag
        should_suppress = lf_a_b.should_suppress_transaction(tx_native, self.identity)
        self.assertFalse(should_suppress)

    # 8. Bounded hop count overflow loop detection
    def test_08_bounded_hop_count_overflow(self):
        lf = CDCReplicationLoopFilter(self.source_a_db, self.topology_mgr.topology_id, self.run_id, max_hops=3)
        prov = CDCOriginProvenance(self.source_b_db, self.topology_mgr.topology_id, self.run_id, "writer-b", "B_TO_A", hop_count=4)
        tx = self._make_tx("tx-hop-overflow", [self._make_event(1, details={"origin_provenance": prov.to_dict()})])

        with self.assertRaises(CDCExecutionError) as ctx:
            lf.should_suppress_transaction(tx, self.identity)
        self.assertEqual(ctx.exception.failure.failure_type.value, "REPLICATION_LOOP_DETECTED")

    # 9. Malformed origin provenance rejection
    def test_09_malformed_origin_provenance_rejection(self):
        lf = self.topology_mgr.loop_filter_a_to_b
        tx = self._make_tx("tx-malformed-prov", [self._make_event(1, details={"origin_provenance": "INVALID_STRING"})])

        with self.assertRaises(CDCExecutionError) as ctx:
            lf.should_suppress_transaction(tx, self.identity)
        self.assertEqual(ctx.exception.failure.failure_type.value, "INVALID_ORIGIN_PROVENANCE")

    # 10. Cross-topology origin substitution rejection
    def test_10_cross_topology_provenance_rejection(self):
        lf = self.topology_mgr.loop_filter_a_to_b
        prov = CDCOriginProvenance(self.source_b_db, "other-topology-id", self.run_id, "writer-b", "B_TO_A")
        tx = self._make_tx("tx-cross-top", [self._make_event(1, details={"origin_provenance": prov.to_dict()})])

        with self.assertRaises(CDCExecutionError) as ctx:
            lf.should_suppress_transaction(tx, self.identity)
        self.assertEqual(ctx.exception.failure.failure_type.value, "TOPOLOGY_IDENTITY_MISMATCH")

    # 11. Cross-run provenance rejection
    def test_11_cross_run_provenance_rejection(self):
        lf = self.topology_mgr.loop_filter_a_to_b
        prov = CDCOriginProvenance(self.source_b_db, self.topology_mgr.topology_id, "other-run-id", "writer-b", "B_TO_A")
        tx = self._make_tx("tx-cross-run", [self._make_event(1, details={"origin_provenance": prov.to_dict()})])

        with self.assertRaises(CDCExecutionError) as ctx:
            lf.should_suppress_transaction(tx, self.identity)
        self.assertEqual(ctx.exception.failure.failure_type.value, "TOPOLOGY_IDENTITY_MISMATCH")

    # 12. Concurrent UPDATE_UPDATE conflict detection
    def test_12_concurrent_update_update_conflict_detection(self):
        detector = self.topology_mgr.conflict_detector
        tx_a = self._make_tx("tx-a-u", [self._make_event(1, entity_key="u100", op=CDCOperationType.UPDATE)], pos_seq=1)
        tx_b = self._make_tx("tx-b-u", [self._make_event(2, entity_key="u100", op=CDCOperationType.UPDATE)], pos_seq=2)

        # Add nodes without creating a causality dependency edge between them
        self.topology_mgr.causality_graph.add_transaction(tx_a)
        self.topology_mgr.causality_graph.add_transaction(tx_b)

        conf = detector.detect_conflict(self.identity, tx_a, tx_b)
        self.assertIsNotNone(conf)
        self.assertEqual(conf.conflict_type, CDCConflictType.UPDATE_UPDATE)
        self.assertEqual(conf.conflict_state, CDCConflictState.DETECTED)

    # 13. Concurrent UPDATE_DELETE conflict detection
    def test_13_concurrent_update_delete_conflict_detection(self):
        detector = self.topology_mgr.conflict_detector
        tx_a = self._make_tx("tx-a-ud", [self._make_event(1, entity_key="u200", op=CDCOperationType.UPDATE)], pos_seq=1)
        tx_b = self._make_tx("tx-b-ud", [self._make_event(2, entity_key="u200", op=CDCOperationType.DELETE)], pos_seq=2)

        self.topology_mgr.causality_graph.add_transaction(tx_a)
        self.topology_mgr.causality_graph.add_transaction(tx_b)

        conf = detector.detect_conflict(self.identity, tx_a, tx_b)
        self.assertIsNotNone(conf)
        self.assertEqual(conf.conflict_type, CDCConflictType.UPDATE_DELETE)

    # 14. Concurrent DELETE_UPDATE conflict detection
    def test_14_concurrent_delete_update_conflict_detection(self):
        detector = self.topology_mgr.conflict_detector
        tx_a = self._make_tx("tx-a-du", [self._make_event(1, entity_key="u300", op=CDCOperationType.DELETE)], pos_seq=1)
        tx_b = self._make_tx("tx-b-du", [self._make_event(2, entity_key="u300", op=CDCOperationType.UPDATE)], pos_seq=2)

        self.topology_mgr.causality_graph.add_transaction(tx_a)
        self.topology_mgr.causality_graph.add_transaction(tx_b)

        conf = detector.detect_conflict(self.identity, tx_a, tx_b)
        self.assertIsNotNone(conf)
        self.assertEqual(conf.conflict_type, CDCConflictType.DELETE_UPDATE)

    # 15. Concurrent INSERT_INSERT conflict detection
    def test_15_concurrent_insert_insert_conflict_detection(self):
        detector = self.topology_mgr.conflict_detector
        tx_a = self._make_tx("tx-a-ii", [self._make_event(1, entity_key="u400", op=CDCOperationType.INSERT)], pos_seq=1)
        tx_b = self._make_tx("tx-b-ii", [self._make_event(2, entity_key="u400", op=CDCOperationType.INSERT)], pos_seq=2)

        self.topology_mgr.causality_graph.add_transaction(tx_a)
        self.topology_mgr.causality_graph.add_transaction(tx_b)

        conf = detector.detect_conflict(self.identity, tx_a, tx_b)
        self.assertIsNotNone(conf)
        self.assertEqual(conf.conflict_type, CDCConflictType.INSERT_INSERT)

    # 16. DELETE_DELETE idempotent non-conflict resolution
    def test_16_delete_delete_idempotent_non_conflict(self):
        detector = self.topology_mgr.conflict_detector
        tx_a = self._make_tx("tx-a-dd", [self._make_event(1, entity_key="u500", op=CDCOperationType.DELETE)], pos_seq=1)
        tx_b = self._make_tx("tx-b-dd", [self._make_event(2, entity_key="u500", op=CDCOperationType.DELETE)], pos_seq=2)

        self.topology_mgr.causality_graph.add_transaction(tx_a)
        self.topology_mgr.causality_graph.add_transaction(tx_b)

        conf = detector.detect_conflict(self.identity, tx_a, tx_b)
        self.assertIsNone(conf)

    # 17. Causally ordered mutations non-conflict differentiation
    def test_17_causally_ordered_mutations_non_conflict(self):
        detector = self.topology_mgr.conflict_detector
        tx_a = self._make_tx("tx-a-causal", [self._make_event(1, entity_key="u600", op=CDCOperationType.UPDATE)], pos_seq=1)
        tx_b = self._make_tx("tx-b-causal", [self._make_event(2, entity_key="u600", op=CDCOperationType.UPDATE)], pos_seq=2)

        self.topology_mgr.causality_graph.add_transaction(tx_a)
        self.topology_mgr.causality_graph.resolve_transaction_completion(tx_a.tx_id)  # tx_a completed!
        self.topology_mgr.causality_graph.add_transaction(tx_b)

        conf = detector.detect_conflict(self.identity, tx_a, tx_b)
        self.assertIsNone(conf)  # Causally ordered -> NOT a multi-master conflict!

    # 18. SOURCE_A_WINS policy resolution
    def test_18_source_a_wins_policy_resolution(self):
        detector = self.topology_mgr.conflict_detector
        resolver = self.topology_mgr.conflict_resolver

        tx_a = self._make_tx("tx-saw-a", [self._make_event(1, entity_key="u700")], pos_seq=1)
        tx_b = self._make_tx("tx-saw-b", [self._make_event(2, entity_key="u700")], pos_seq=2)
        self.topology_mgr.causality_graph.add_transaction(tx_a)
        self.topology_mgr.causality_graph.add_transaction(tx_b)

        conf = detector.detect_conflict(self.identity, tx_a, tx_b)
        dec = resolver.resolve_conflict(self.identity, conf.conflict_id, CDCConflictResolutionPolicy.SOURCE_A_WINS, self.fencing_epoch)

        self.assertEqual(dec.selected_winner, "SOURCE_A")
        self.assertEqual(conf.conflict_state, CDCConflictState.RESOLVED)

    # 19. SOURCE_B_WINS policy resolution
    def test_19_source_b_wins_policy_resolution(self):
        detector = self.topology_mgr.conflict_detector
        resolver = self.topology_mgr.conflict_resolver

        tx_a = self._make_tx("tx-sbw-a", [self._make_event(1, entity_key="u800")], pos_seq=1)
        tx_b = self._make_tx("tx-sbw-b", [self._make_event(2, entity_key="u800")], pos_seq=2)
        self.topology_mgr.causality_graph.add_transaction(tx_a)
        self.topology_mgr.causality_graph.add_transaction(tx_b)

        conf = detector.detect_conflict(self.identity, tx_a, tx_b)
        dec = resolver.resolve_conflict(self.identity, conf.conflict_id, CDCConflictResolutionPolicy.SOURCE_B_WINS, self.fencing_epoch)

        self.assertEqual(dec.selected_winner, "SOURCE_B")

    # 20. DESIGNATED_PRIMARY_WINS policy resolution
    def test_20_designated_primary_wins_policy_resolution(self):
        detector = self.topology_mgr.conflict_detector
        resolver = self.topology_mgr.conflict_resolver

        tx_a = self._make_tx("tx-dpw-a", [self._make_event(1, entity_key="u900")], pos_seq=1)
        tx_b = self._make_tx("tx-dpw-b", [self._make_event(2, entity_key="u900")], pos_seq=2)
        self.topology_mgr.causality_graph.add_transaction(tx_a)
        self.topology_mgr.causality_graph.add_transaction(tx_b)

        conf = detector.detect_conflict(self.identity, tx_a, tx_b)
        dec = resolver.resolve_conflict(self.identity, conf.conflict_id, CDCConflictResolutionPolicy.DESIGNATED_PRIMARY_WINS, self.fencing_epoch)

        self.assertEqual(dec.selected_winner, "SOURCE_A")

    # 21. LATEST_VERSION_WINS policy resolution
    def test_21_latest_version_wins_policy_resolution(self):
        detector = self.topology_mgr.conflict_detector
        resolver = self.topology_mgr.conflict_resolver

        tx_a = self._make_tx("tx-lvw-a", [self._make_event(1, entity_key="u1000")], pos_seq=10)
        tx_b = self._make_tx("tx-lvw-b", [self._make_event(2, entity_key="u1000")], pos_seq=20)  # LSN pos_seq 20 > 10
        self.topology_mgr.causality_graph.add_transaction(tx_a)
        self.topology_mgr.causality_graph.add_transaction(tx_b)

        conf = detector.detect_conflict(self.identity, tx_a, tx_b)
        dec = resolver.resolve_conflict(self.identity, conf.conflict_id, CDCConflictResolutionPolicy.LATEST_VERSION_WINS, self.fencing_epoch)

        self.assertEqual(dec.selected_winner, "SOURCE_B")

    # 22. MANUAL_GOVERNANCE_REQUIRED policy resolution
    def test_22_manual_governance_required_resolution(self):
        detector = self.topology_mgr.conflict_detector
        resolver = self.topology_mgr.conflict_resolver

        tx_a = self._make_tx("tx-mgr-a", [self._make_event(1, entity_key="u1100")], pos_seq=1)
        tx_b = self._make_tx("tx-mgr-b", [self._make_event(2, entity_key="u1100")], pos_seq=2)
        self.topology_mgr.causality_graph.add_transaction(tx_a)
        self.topology_mgr.causality_graph.add_transaction(tx_b)

        conf = detector.detect_conflict(self.identity, tx_a, tx_b)
        with self.assertRaises(CDCExecutionError) as ctx:
            resolver.resolve_conflict(self.identity, conf.conflict_id, CDCConflictResolutionPolicy.MANUAL_GOVERNANCE_REQUIRED, self.fencing_epoch)
        self.assertEqual(ctx.exception.failure.failure_type.value, "CONFLICT_RESOLUTION_REJECTED")

        # Now pass explicit manual_winner
        dec = resolver.resolve_conflict(self.identity, conf.conflict_id, CDCConflictResolutionPolicy.MANUAL_GOVERNANCE_REQUIRED, self.fencing_epoch, manual_winner="SOURCE_B", reason="Operator approved")
        self.assertEqual(dec.selected_winner, "SOURCE_B")

    # 23. Stale resolver fencing token rejection
    def test_23_stale_resolver_fencing_token_rejection(self):
        new_epoch = self.recovery_coord.issue_epoch(self.migration_id)
        detector = self.topology_mgr.conflict_detector
        resolver = self.topology_mgr.conflict_resolver

        tx_a = self._make_tx("tx-stale-a", [self._make_event(1, entity_key="u1200")], pos_seq=1)
        tx_b = self._make_tx("tx-stale-b", [self._make_event(2, entity_key="u1200")], pos_seq=2)
        self.topology_mgr.causality_graph.add_transaction(tx_a)
        self.topology_mgr.causality_graph.add_transaction(tx_b)

        conf = detector.detect_conflict(self.identity, tx_a, tx_b)
        with self.assertRaises(CDCExecutionError) as ctx:
            resolver.resolve_conflict(self.identity, conf.conflict_id, CDCConflictResolutionPolicy.SOURCE_A_WINS, self.fencing_epoch)
        self.assertEqual(ctx.exception.failure.failure_type.value, "STALE_CONFLICT_RESOLVER")

    # 24. Entity-scoped quarantine lock creation
    def test_24_entity_scoped_quarantine_lock(self):
        qm = self.topology_mgr.quarantine_manager
        qrec = qm.quarantine_entity(self.identity, "conf-101", "users", "100", "Unresolved conflict", self.fencing_epoch)

        self.assertTrue(qm.is_entity_quarantined("users", "100"))
        self.assertFalse(qm.is_entity_quarantined("users", "200"))  # Unrelated key is NOT quarantined!
        self.assertEqual(qrec.state, CDCQuarantineState.ACTIVE)

    # 25. Quarantine release with fencing token validation
    def test_25_quarantine_release_with_fencing(self):
        qm = self.topology_mgr.quarantine_manager
        qrec = qm.quarantine_entity(self.identity, "conf-102", "users", "200", "Unresolved conflict", self.fencing_epoch)

        released = qm.release_quarantine(self.identity, qrec.quarantine_id, "dec-102", self.fencing_epoch)
        self.assertEqual(released.state, CDCQuarantineState.RELEASED)
        self.assertFalse(qm.is_entity_quarantined("users", "200"))

    # 26. Stale worker quarantine release rejection
    def test_26_stale_worker_quarantine_release_rejection(self):
        qm = self.topology_mgr.quarantine_manager
        qrec = qm.quarantine_entity(self.identity, "conf-103", "users", "300", "Unresolved conflict", self.fencing_epoch)

        new_epoch = self.recovery_coord.issue_epoch(self.migration_id)
        with self.assertRaises(CDCExecutionError) as ctx:
            qm.release_quarantine(self.identity, qrec.quarantine_id, "dec-103", self.fencing_epoch)
        self.assertEqual(ctx.exception.failure.failure_type.value, "STALE_WORKER")

    # 27. Process restart recovery of topology state
    def test_27_process_restart_recovery_of_topology(self):
        top_mgr2 = CDCBirectionalTopologyManager(
            identity=self.identity,
            source_a_database_id=self.source_a_db,
            source_b_database_id=self.source_b_db,
            topology_id=self.topology_mgr.topology_id,
            state_store=self.state_store,
            recovery_coordinator=self.recovery_coord,
        )
        self.assertEqual(top_mgr2.topology.topology_id, self.topology_mgr.topology_id)
        self.assertEqual(top_mgr2.topology.state, CDCReplicationTopologyState.ACTIVE)

    # 28. Cutover gate blocking under active conflicts/quarantines
    def test_28_cutover_gate_blocking(self):
        self.assertTrue(self.topology_mgr.is_cutover_eligible())

        qm = self.topology_mgr.quarantine_manager
        qm.quarantine_entity(self.identity, "conf-cutover", "users", "999", "Active conflict", self.fencing_epoch)

        self.assertFalse(self.topology_mgr.is_cutover_eligible())

    # 29. EngineGateway IPC capability: create_cdc_bidirectional_topology
    def test_29_engine_gateway_create_topology(self):
        gw = EngineGateway()
        res = gw.create_cdc_bidirectional_topology({
            "migration_id": self.migration_id,
            "job_id": self.job_id,
            "run_id": self.run_id,
            "cdc_session_id": self.cdc_session_id,
            "source_a_database_id": "db_a_gw",
            "source_b_database_id": "db_b_gw",
        })
        self.assertEqual(res["status"], "CREATED")
        self.assertIn("topology_id", res)

    # 30. EngineGateway IPC capability: get_cdc_bidirectional_status
    def test_30_engine_gateway_get_status(self):
        gw = EngineGateway()
        gw._cdc_topology_managers = {self.topology_mgr.topology_id: self.topology_mgr}
        res = gw.get_cdc_bidirectional_status({"topology_id": self.topology_mgr.topology_id})
        self.assertEqual(res["topology_state"], "ACTIVE")

    # 31. EngineGateway IPC capability: pause & resume topology
    def test_31_engine_gateway_pause_resume(self):
        gw = EngineGateway()
        gw._cdc_topology_managers = {self.topology_mgr.topology_id: self.topology_mgr}

        res_p = gw.pause_cdc_bidirectional_topology({"topology_id": self.topology_mgr.topology_id, "fencing_epoch": self.fencing_epoch})
        self.assertEqual(res_p["status"], "PAUSED")

        res_r = gw.resume_cdc_bidirectional_topology({"topology_id": self.topology_mgr.topology_id, "fencing_epoch": self.fencing_epoch})
        self.assertEqual(res_r["status"], "RESUMED")

    # 32. EngineGateway IPC capability: get_cdc_conflicts & resolve_cdc_conflict
    def test_32_engine_gateway_conflicts_and_resolution(self):
        gw = EngineGateway()
        gw._cdc_topology_managers = {self.topology_mgr.topology_id: self.topology_mgr}

        tx_a = self._make_tx("tx-gw-a", [self._make_event(1, entity_key="u-gw")], pos_seq=1)
        tx_b = self._make_tx("tx-gw-b", [self._make_event(2, entity_key="u-gw")], pos_seq=2)
        self.topology_mgr.causality_graph.add_transaction(tx_a)
        self.topology_mgr.causality_graph.add_transaction(tx_b)

        conf = self.topology_mgr.conflict_detector.detect_conflict(self.identity, tx_a, tx_b)
        res_list = gw.get_cdc_conflicts({"topology_id": self.topology_mgr.topology_id})
        self.assertEqual(res_list["unresolved_conflict_count"], 1)

        res_dec = gw.resolve_cdc_conflict({
            "topology_id": self.topology_mgr.topology_id,
            "conflict_id": conf.conflict_id,
            "policy": "SOURCE_A_WINS",
            "fencing_epoch": self.fencing_epoch,
        })
        self.assertEqual(res_dec["status"], "RESOLVED")

    # 33. Telemetry secret redaction verification
    def test_33_telemetry_secret_redaction(self):
        telem = self.topology_mgr.get_telemetry()
        telem_str = str(telem)
        self.assertNotIn("password", telem_str.lower())
        self.assertNotIn("secret", telem_str.lower())


if __name__ == "__main__":
    unittest.main()
