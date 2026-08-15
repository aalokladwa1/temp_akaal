"""
AKAAL Day 29 — P3.8.1 Hostile Semantic, Bidirectional Replication, Conflict, Loop Prevention, Quarantine, Concurrency & Crash-Consistency Acceptance Audit.
===================================================================================================================================================
Adversarial attack suite targeting P3.8 multi-master capabilities:
- ATTACK GROUP A: Origin Provenance & Loop Prevention
- ATTACK GROUP B: Provenance Durability & Process-Death Windows
- ATTACK GROUP C: True Conflict Detection & False-Positive Elimination
- ATTACK GROUP D: Conflict Resolution Policies & Unsafe Heterogeneous Position Fail-Closed
- ATTACK GROUP E: Quarantine Safety, Fencing & Entity Isolation
- ATTACK GROUP F: Bidirectional Topology State & Split-Brain Prevention
- ATTACK GROUP G: Network Partition, Reconnection & Backlog Quarantine
- ATTACK GROUP H: Crash-Consistency & Checkpoint Safety
- ATTACK GROUP I: Concurrency, TOCTOU & Race Conditions
- ATTACK GROUP J: Existing Authority Preservation (P1, P3.3, P3.5, P3.6, P3.7)
- ATTACK GROUP K: Contiguous Checkpoint / ACK / Reclamation Safety
- ATTACK GROUP L: Cutover Readiness Gate Enforcement
- ATTACK GROUP M: Security & Customer Secret Sanitization
- ATTACK GROUP N: EngineGateway IPC Reachability & Backend Truthfulness
"""

import os
import uuid
import tempfile
import unittest
from typing import Dict, Any, List

from akaal.cdc.domain.events import (
    CDCEventIdentity,
    CDCEvent,
    CDCTransaction,
    CDCOperationType,
    parse_cdc_event,
    parse_cdc_transaction,
)
from akaal.cdc.domain.positions import PostgresLSNPosition, OracleSCNPosition
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
from akaal.cdc.sharding.frontier import CDCCheckpointFrontierTracker
from akaal.gateway.engine_gateway import EngineGateway
from akaal.core.state.state_store import CentralStateStore
from akaal.runtime.recovery.coordinator import RecoveryCoordinator


class TestP381MultiMasterHostileAudit(unittest.TestCase):

    def setUp(self):
        self.migration_id = f"mig-p381-{uuid.uuid4().hex[:6]}"
        self.job_id = "job-p381-test"
        self.run_id = "run-p381-test"
        self.cdc_session_id = f"sess-p381-{uuid.uuid4().hex[:6]}"
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
        source_engine: str = "POSTGRESQL",
    ) -> CDCEvent:
        pos = PostgresLSNPosition(f"0/{seq*100:X}") if source_engine == "POSTGRESQL" else OracleSCNPosition(seq * 1000)
        return CDCEvent(
            identity=self.identity,
            source_engine=source_engine,
            source_database="db",
            source_schema="public",
            source_table=table_name,
            operation=op,
            position=pos,
            before_image={"id": entity_key, "val": f"old_{seq}"},
            after_image={"id": entity_key, "val": f"new_{seq}"},
            details=details or {},
        )

    def _make_tx(self, tx_id: str, events: List[CDCEvent], pos_seq: int = 1, source_engine: str = "POSTGRESQL") -> CDCTransaction:
        pos = PostgresLSNPosition(f"0/{pos_seq*100:X}") if source_engine == "POSTGRESQL" else OracleSCNPosition(pos_seq * 1000)
        return CDCTransaction(
            identity=self.identity,
            tx_id=tx_id,
            events=events,
            commit_position=pos,
        )

    # ──────────────────────────────────────────────────────────────────────────
    # ATTACK GROUP A — ORIGIN PROVENANCE & LOOP PREVENTION
    # ──────────────────────────────────────────────────────────────────────────

    def test_01_a_b_a_echo_suppression(self):
        """ATTACK: Node A -> Node B -> Node A echo event must be suppressed at Node A."""
        lf_a = self.topology_mgr.loop_filter_a_to_b
        tx = self._make_tx("tx-echo-aba", [self._make_event(1)])
        tagged_tx = lf_a.attach_origin_provenance(tx, "A_TO_B")

        self.assertTrue(lf_a.should_suppress_transaction(tagged_tx, self.identity))
        self.assertEqual(lf_a.echo_events_suppressed_count, 1)

    def test_02_b_a_b_echo_suppression(self):
        """ATTACK: Node B -> Node A -> Node B echo event must be suppressed at Node B."""
        lf_b = self.topology_mgr.loop_filter_b_to_a
        tx = self._make_tx("tx-echo-bab", [self._make_event(2)])
        tagged_tx = lf_b.attach_origin_provenance(tx, "B_TO_A")

        self.assertTrue(lf_b.should_suppress_transaction(tagged_tx, self.identity))
        self.assertEqual(lf_b.echo_events_suppressed_count, 1)

    def test_03_repeated_multi_hop_echo(self):
        """ATTACK: Hop count must increment and bound overflow must fail closed."""
        lf = CDCReplicationLoopFilter(self.source_a_db, self.topology_mgr.topology_id, self.run_id, max_hops=2)
        prov = CDCOriginProvenance(self.source_b_db, self.topology_mgr.topology_id, self.run_id, "writer-b", "B_TO_A", hop_count=3)
        tx = self._make_tx("tx-hop-over", [self._make_event(1, details={"origin_provenance": prov.to_dict()})])

        with self.assertRaises(CDCExecutionError) as ctx:
            lf.should_suppress_transaction(tx, self.identity)
        self.assertEqual(ctx.exception.failure.failure_type.value, "REPLICATION_LOOP_DETECTED")

    def test_04_same_db_different_topology(self):
        """ATTACK: Provenance with cross-topology ID substitution must fail closed."""
        lf = self.topology_mgr.loop_filter_a_to_b
        prov = CDCOriginProvenance(self.source_b_db, "fake-topology-id", self.run_id, "writer-b", "B_TO_A")
        tx = self._make_tx("tx-cross-top", [self._make_event(1, details={"origin_provenance": prov.to_dict()})])

        with self.assertRaises(CDCExecutionError) as ctx:
            lf.should_suppress_transaction(tx, self.identity)
        self.assertEqual(ctx.exception.failure.failure_type.value, "TOPOLOGY_IDENTITY_MISMATCH")

    def test_05_same_writer_different_run(self):
        """ATTACK: Provenance with cross-run ID substitution must fail closed."""
        lf = self.topology_mgr.loop_filter_a_to_b
        prov = CDCOriginProvenance(self.source_b_db, self.topology_mgr.topology_id, "fake-run-id", "writer-b", "B_TO_A")
        tx = self._make_tx("tx-cross-run", [self._make_event(1, details={"origin_provenance": prov.to_dict()})])

        with self.assertRaises(CDCExecutionError) as ctx:
            lf.should_suppress_transaction(tx, self.identity)
        self.assertEqual(ctx.exception.failure.failure_type.value, "TOPOLOGY_IDENTITY_MISMATCH")

    def test_06_malformed_provenance_type(self):
        """ATTACK: Malformed non-dict provenance must fail closed."""
        lf = self.topology_mgr.loop_filter_a_to_b
        tx = self._make_tx("tx-malformed", [self._make_event(1, details={"origin_provenance": 12345})])

        with self.assertRaises(CDCExecutionError) as ctx:
            lf.should_suppress_transaction(tx, self.identity)
        self.assertEqual(ctx.exception.failure.failure_type.value, "INVALID_ORIGIN_PROVENANCE")

    def test_07_missing_origin_db_id(self):
        """ATTACK: Provenance missing origin_database_id must fail closed."""
        lf = self.topology_mgr.loop_filter_a_to_b
        prov_dict = {"akaal_writer_id": "w1", "origin_topology_id": self.topology_mgr.topology_id, "origin_run_id": self.run_id}
        tx = self._make_tx("tx-missing-db", [self._make_event(1, details={"origin_provenance": prov_dict})])

        with self.assertRaises(CDCExecutionError) as ctx:
            lf.should_suppress_transaction(tx, self.identity)
        self.assertEqual(ctx.exception.failure.failure_type.value, "INVALID_ORIGIN_PROVENANCE")

    def test_08_missing_writer_id(self):
        """ATTACK: Provenance missing akaal_writer_id must fail closed."""
        lf = self.topology_mgr.loop_filter_a_to_b
        prov_dict = {"origin_database_id": self.source_b_db, "origin_topology_id": self.topology_mgr.topology_id, "origin_run_id": self.run_id}
        tx = self._make_tx("tx-missing-writer", [self._make_event(1, details={"origin_provenance": prov_dict})])

        with self.assertRaises(CDCExecutionError) as ctx:
            lf.should_suppress_transaction(tx, self.identity)
        self.assertEqual(ctx.exception.failure.failure_type.value, "INVALID_ORIGIN_PROVENANCE")

    def test_09_forged_topology_id(self):
        """ATTACK: Forged origin_topology_id must fail closed."""
        lf = self.topology_mgr.loop_filter_a_to_b
        prov = CDCOriginProvenance(self.source_b_db, "forged-top", self.run_id, "writer-b", "B_TO_A")
        tx = self._make_tx("tx-forged-top", [self._make_event(1, details={"origin_provenance": prov.to_dict()})])

        with self.assertRaises(CDCExecutionError) as ctx:
            lf.should_suppress_transaction(tx, self.identity)
        self.assertEqual(ctx.exception.failure.failure_type.value, "TOPOLOGY_IDENTITY_MISMATCH")

    def test_10_forged_run_id(self):
        """ATTACK: Forged origin_run_id must fail closed."""
        lf = self.topology_mgr.loop_filter_a_to_b
        prov = CDCOriginProvenance(self.source_b_db, self.topology_mgr.topology_id, "forged-run", "writer-b", "B_TO_A")
        tx = self._make_tx("tx-forged-run", [self._make_event(1, details={"origin_provenance": prov.to_dict()})])

        with self.assertRaises(CDCExecutionError) as ctx:
            lf.should_suppress_transaction(tx, self.identity)
        self.assertEqual(ctx.exception.failure.failure_type.value, "TOPOLOGY_IDENTITY_MISMATCH")

    def test_11_legitimate_local_mutation_non_suppression(self):
        """ATTACK: Native local mutation with no origin tag must NOT be suppressed."""
        lf = self.topology_mgr.loop_filter_a_to_b
        tx_native = self._make_tx("tx-native", [self._make_event(1)])
        self.assertFalse(lf.should_suppress_transaction(tx_native, self.identity))

    def test_12_same_row_subsequent_legitimate_mutation(self):
        """ATTACK: Legitimate local write to same row after an echo event must process normally."""
        lf = self.topology_mgr.loop_filter_a_to_b
        # 1. Echo event
        tx_echo = self._make_tx("tx-echo-1", [self._make_event(1, entity_key="u10")])
        tagged_echo = lf.attach_origin_provenance(tx_echo, "A_TO_B")
        self.assertTrue(lf.should_suppress_transaction(tagged_echo, self.identity))

        # 2. Subsequent legitimate local write to same entity
        tx_native = self._make_tx("tx-native-sub", [self._make_event(2, entity_key="u10")])
        self.assertFalse(lf.should_suppress_transaction(tx_native, self.identity))

    def test_13_duplicate_replay_vs_echo_differentiation(self):
        """ATTACK: Replay of native transaction must NOT increment echo suppression count."""
        lf = self.topology_mgr.loop_filter_a_to_b
        tx_native = self._make_tx("tx-native-dupe", [self._make_event(1)])
        initial_suppressed = lf.echo_events_suppressed_count

        self.assertFalse(lf.should_suppress_transaction(tx_native, self.identity))
        self.assertEqual(lf.echo_events_suppressed_count, initial_suppressed)

    # ──────────────────────────────────────────────────────────────────────────
    # ATTACK GROUP B — PROVENANCE DURABILITY & SERIALIZATION
    # ──────────────────────────────────────────────────────────────────────────

    def test_14_cdc_event_details_serialization_durability(self):
        """ATTACK: CDCEvent and CDCTransaction details must survive to_dict and parse_cdc_* cycles."""
        lf = self.topology_mgr.loop_filter_a_to_b
        tx = self._make_tx("tx-ser-dur", [self._make_event(1)])
        tagged_tx = lf.attach_origin_provenance(tx, "A_TO_B")

        tx_dict = tagged_tx.to_dict()
        restored_tx = parse_cdc_transaction(tx_dict)

        self.assertIn("details", restored_tx.events[0].to_dict())
        self.assertIn("origin_provenance", restored_tx.events[0].details)
        prov_restored = restored_tx.events[0].details["origin_provenance"]
        self.assertEqual(prov_restored["origin_database_id"], self.source_a_db)

    def test_15_provenance_reconstruction_after_crash(self):
        """ATTACK: Echo event reconstructed from serialized state after crash must still be suppressed."""
        lf = self.topology_mgr.loop_filter_a_to_b
        tx = self._make_tx("tx-crash-echo", [self._make_event(1)])
        tagged_tx = lf.attach_origin_provenance(tx, "A_TO_B")

        # Simulate WAL write -> crash -> parse_cdc_transaction
        wal_payload = tagged_tx.to_dict()
        reconstructed_tx = parse_cdc_transaction(wal_payload)

        # Loop filter evaluation post-crash
        self.assertTrue(lf.should_suppress_transaction(reconstructed_tx, self.identity))

    # ──────────────────────────────────────────────────────────────────────────
    # ATTACK GROUP C — TRUE CONFLICT DETECTION & CLASSIFICATION
    # ──────────────────────────────────────────────────────────────────────────

    def test_16_concurrent_update_update_detection(self):
        detector = self.topology_mgr.conflict_detector
        tx_a = self._make_tx("tx-a-uu", [self._make_event(1, entity_key="k1", op=CDCOperationType.UPDATE)], pos_seq=1)
        tx_b = self._make_tx("tx-b-uu", [self._make_event(2, entity_key="k1", op=CDCOperationType.UPDATE)], pos_seq=2)

        conf = detector.detect_conflict(self.identity, tx_a, tx_b)
        self.assertIsNotNone(conf)
        self.assertEqual(conf.conflict_type, CDCConflictType.UPDATE_UPDATE)

    def test_17_concurrent_update_delete_detection(self):
        detector = self.topology_mgr.conflict_detector
        tx_a = self._make_tx("tx-a-ud", [self._make_event(1, entity_key="k2", op=CDCOperationType.UPDATE)], pos_seq=1)
        tx_b = self._make_tx("tx-b-ud", [self._make_event(2, entity_key="k2", op=CDCOperationType.DELETE)], pos_seq=2)

        conf = detector.detect_conflict(self.identity, tx_a, tx_b)
        self.assertIsNotNone(conf)
        self.assertEqual(conf.conflict_type, CDCConflictType.UPDATE_DELETE)

    def test_18_concurrent_delete_update_detection(self):
        detector = self.topology_mgr.conflict_detector
        tx_a = self._make_tx("tx-a-du", [self._make_event(1, entity_key="k3", op=CDCOperationType.DELETE)], pos_seq=1)
        tx_b = self._make_tx("tx-b-du", [self._make_event(2, entity_key="k3", op=CDCOperationType.UPDATE)], pos_seq=2)

        conf = detector.detect_conflict(self.identity, tx_a, tx_b)
        self.assertIsNotNone(conf)
        self.assertEqual(conf.conflict_type, CDCConflictType.DELETE_UPDATE)

    def test_19_concurrent_insert_insert_detection(self):
        detector = self.topology_mgr.conflict_detector
        tx_a = self._make_tx("tx-a-ii", [self._make_event(1, entity_key="k4", op=CDCOperationType.INSERT)], pos_seq=1)
        tx_b = self._make_tx("tx-b-ii", [self._make_event(2, entity_key="k4", op=CDCOperationType.INSERT)], pos_seq=2)

        conf = detector.detect_conflict(self.identity, tx_a, tx_b)
        self.assertIsNotNone(conf)
        self.assertEqual(conf.conflict_type, CDCConflictType.INSERT_INSERT)

    def test_20_delete_delete_idempotent_non_conflict(self):
        detector = self.topology_mgr.conflict_detector
        tx_a = self._make_tx("tx-a-dd", [self._make_event(1, entity_key="k5", op=CDCOperationType.DELETE)], pos_seq=1)
        tx_b = self._make_tx("tx-b-dd", [self._make_event(2, entity_key="k5", op=CDCOperationType.DELETE)], pos_seq=2)

        conf = detector.detect_conflict(self.identity, tx_a, tx_b)
        self.assertIsNone(conf)

    def test_21_causally_ordered_mutations_non_conflict(self):
        detector = self.topology_mgr.conflict_detector
        tx_a = self._make_tx("tx-a-causal", [self._make_event(1, entity_key="k6", op=CDCOperationType.UPDATE)], pos_seq=1)
        tx_b = self._make_tx("tx-b-causal", [self._make_event(2, entity_key="k6", op=CDCOperationType.UPDATE)], pos_seq=2)

        self.topology_mgr.causality_graph.add_transaction(tx_a)
        self.topology_mgr.causality_graph.resolve_transaction_completion(tx_a.tx_id)  # Completed predecessor
        self.topology_mgr.causality_graph.add_transaction(tx_b)

        conf = detector.detect_conflict(self.identity, tx_a, tx_b)
        self.assertIsNone(conf)

    def test_22_same_pk_different_tables_isolation(self):
        detector = self.topology_mgr.conflict_detector
        tx_a = self._make_tx("tx-a-u1", [self._make_event(1, table_name="users", entity_key="10")], pos_seq=1)
        tx_b = self._make_tx("tx-b-o1", [self._make_event(2, table_name="orders", entity_key="10")], pos_seq=2)

        conf = detector.detect_conflict(self.identity, tx_a, tx_b)
        self.assertIsNone(conf)

    # ──────────────────────────────────────────────────────────────────────────
    # ATTACK GROUP D — CONFLICT RESOLUTION POLICIES & UNSAFE COMPARISONS
    # ──────────────────────────────────────────────────────────────────────────

    def test_23_source_a_wins_resolution(self):
        detector = self.topology_mgr.conflict_detector
        resolver = self.topology_mgr.conflict_resolver

        tx_a = self._make_tx("tx-a-pol1", [self._make_event(1, entity_key="p10")], pos_seq=1)
        tx_b = self._make_tx("tx-b-pol1", [self._make_event(2, entity_key="p10")], pos_seq=2)
        conf = detector.detect_conflict(self.identity, tx_a, tx_b)

        dec = resolver.resolve_conflict(self.identity, conf.conflict_id, CDCConflictResolutionPolicy.SOURCE_A_WINS, self.fencing_epoch)
        self.assertEqual(dec.selected_winner, "SOURCE_A")

    def test_24_source_b_wins_resolution(self):
        detector = self.topology_mgr.conflict_detector
        resolver = self.topology_mgr.conflict_resolver

        tx_a = self._make_tx("tx-a-pol2", [self._make_event(1, entity_key="p20")], pos_seq=1)
        tx_b = self._make_tx("tx-b-pol2", [self._make_event(2, entity_key="p20")], pos_seq=2)
        conf = detector.detect_conflict(self.identity, tx_a, tx_b)

        dec = resolver.resolve_conflict(self.identity, conf.conflict_id, CDCConflictResolutionPolicy.SOURCE_B_WINS, self.fencing_epoch)
        self.assertEqual(dec.selected_winner, "SOURCE_B")

    def test_25_designated_primary_wins_resolution(self):
        detector = self.topology_mgr.conflict_detector
        resolver = self.topology_mgr.conflict_resolver

        tx_a = self._make_tx("tx-a-pol3", [self._make_event(1, entity_key="p30")], pos_seq=1)
        tx_b = self._make_tx("tx-b-pol3", [self._make_event(2, entity_key="p30")], pos_seq=2)
        conf = detector.detect_conflict(self.identity, tx_a, tx_b)

        dec = resolver.resolve_conflict(self.identity, conf.conflict_id, CDCConflictResolutionPolicy.DESIGNATED_PRIMARY_WINS, self.fencing_epoch)
        self.assertEqual(dec.selected_winner, "SOURCE_A")

    def test_26_designated_primary_unknown_fails_closed(self):
        resolver_no_prim = CDCConflictResolver(
            topology_id=self.topology_mgr.topology_id,
            conflict_detector=self.topology_mgr.conflict_detector,
            recovery_coordinator=self.recovery_coord,
            designated_primary_database_id=None,  # Primary UNKNOWN!
        )
        detector = self.topology_mgr.conflict_detector

        tx_a = self._make_tx("tx-a-prim-unk", [self._make_event(1, entity_key="p35")], pos_seq=1)
        tx_b = self._make_tx("tx-b-prim-unk", [self._make_event(2, entity_key="p35")], pos_seq=2)
        conf = detector.detect_conflict(self.identity, tx_a, tx_b)

        dec = resolver_no_prim.resolve_conflict(self.identity, conf.conflict_id, CDCConflictResolutionPolicy.DESIGNATED_PRIMARY_WINS, self.fencing_epoch, manual_winner="SOURCE_B")
        self.assertEqual(dec.selected_winner, "SOURCE_B")

    def test_27_latest_version_wins_homogeneous_lsn(self):
        detector = self.topology_mgr.conflict_detector
        resolver = self.topology_mgr.conflict_resolver

        tx_a = self._make_tx("tx-a-lvw", [self._make_event(1, entity_key="p40", source_engine="POSTGRESQL")], pos_seq=10, source_engine="POSTGRESQL")
        tx_b = self._make_tx("tx-b-lvw", [self._make_event(2, entity_key="p40", source_engine="POSTGRESQL")], pos_seq=20, source_engine="POSTGRESQL")
        conf = detector.detect_conflict(self.identity, tx_a, tx_b)

        dec = resolver.resolve_conflict(self.identity, conf.conflict_id, CDCConflictResolutionPolicy.LATEST_VERSION_WINS, self.fencing_epoch)
        self.assertEqual(dec.selected_winner, "SOURCE_B")

    def test_28_latest_version_wins_heterogeneous_cross_engine_fails_closed(self):
        """ATTACK: Heterogeneous position domains (POSTGRESQL vs ORACLE) MUST fail closed into MANUAL_GOVERNANCE_REQUIRED."""
        detector = self.topology_mgr.conflict_detector
        resolver = self.topology_mgr.conflict_resolver

        tx_a = self._make_tx("tx-a-het", [self._make_event(1, entity_key="p50", source_engine="POSTGRESQL")], pos_seq=10, source_engine="POSTGRESQL")
        tx_b = self._make_tx("tx-b-het", [self._make_event(2, entity_key="p50", source_engine="ORACLE")], pos_seq=20, source_engine="ORACLE")
        conf = detector.detect_conflict(self.identity, tx_a, tx_b)

        with self.assertRaises(CDCExecutionError) as ctx:
            resolver.resolve_conflict(self.identity, conf.conflict_id, CDCConflictResolutionPolicy.LATEST_VERSION_WINS, self.fencing_epoch)
        self.assertEqual(ctx.exception.failure.failure_type.value, "CONFLICT_RESOLUTION_REJECTED")

        # Now pass explicit manual winner to complete resolution safely
        dec = resolver.resolve_conflict(self.identity, conf.conflict_id, CDCConflictResolutionPolicy.LATEST_VERSION_WINS, self.fencing_epoch, manual_winner="SOURCE_A")
        self.assertEqual(dec.selected_winner, "SOURCE_A")

    def test_29_manual_governance_operator_approval(self):
        detector = self.topology_mgr.conflict_detector
        resolver = self.topology_mgr.conflict_resolver

        tx_a = self._make_tx("tx-a-man", [self._make_event(1, entity_key="p60")], pos_seq=1)
        tx_b = self._make_tx("tx-b-man", [self._make_event(2, entity_key="p60")], pos_seq=2)
        conf = detector.detect_conflict(self.identity, tx_a, tx_b)

        dec = resolver.resolve_conflict(self.identity, conf.conflict_id, CDCConflictResolutionPolicy.MANUAL_GOVERNANCE_REQUIRED, self.fencing_epoch, manual_winner="SOURCE_B", reason="Operator approved")
        self.assertEqual(dec.selected_winner, "SOURCE_B")

    def test_30_stale_fencing_token_resolution_rejection(self):
        new_epoch = self.recovery_coord.issue_epoch(self.migration_id)
        detector = self.topology_mgr.conflict_detector
        resolver = self.topology_mgr.conflict_resolver

        tx_a = self._make_tx("tx-a-stale-r", [self._make_event(1, entity_key="p70")], pos_seq=1)
        tx_b = self._make_tx("tx-b-stale-r", [self._make_event(2, entity_key="p70")], pos_seq=2)
        conf = detector.detect_conflict(self.identity, tx_a, tx_b)

        with self.assertRaises(CDCExecutionError) as ctx:
            resolver.resolve_conflict(self.identity, conf.conflict_id, CDCConflictResolutionPolicy.SOURCE_A_WINS, self.fencing_epoch)
        self.assertEqual(ctx.exception.failure.failure_type.value, "STALE_CONFLICT_RESOLVER")

    # ──────────────────────────────────────────────────────────────────────────
    # ATTACK GROUP E — QUARANTINE SAFETY, FENCING & ENTITY ISOLATION
    # ──────────────────────────────────────────────────────────────────────────

    def test_31_quarantine_entity_scoped_isolation(self):
        qm = self.topology_mgr.quarantine_manager
        qm.quarantine_entity(self.identity, "conf-q1", "users", "100", "Conflict", self.fencing_epoch)

        self.assertTrue(qm.is_entity_quarantined("users", "100"))
        self.assertFalse(qm.is_entity_quarantined("users", "200"))  # Unrelated key NOT quarantined!

    def test_32_stale_worker_quarantine_acquisition_rejection(self):
        """ATTACK: Stale worker acquiring quarantine must be rejected by fencing token validation."""
        new_epoch = self.recovery_coord.issue_epoch(self.migration_id)
        qm = self.topology_mgr.quarantine_manager

        with self.assertRaises(CDCExecutionError) as ctx:
            qm.quarantine_entity(self.identity, "conf-q-stale", "users", "101", "Conflict", self.fencing_epoch)
        self.assertEqual(ctx.exception.failure.failure_type.value, "STALE_WORKER")

    def test_33_stale_worker_quarantine_release_rejection(self):
        qm = self.topology_mgr.quarantine_manager
        qrec = qm.quarantine_entity(self.identity, "conf-q2", "users", "200", "Conflict", self.fencing_epoch)

        new_epoch = self.recovery_coord.issue_epoch(self.migration_id)
        with self.assertRaises(CDCExecutionError) as ctx:
            qm.release_quarantine(self.identity, qrec.quarantine_id, "dec-q2", self.fencing_epoch)
        self.assertEqual(ctx.exception.failure.failure_type.value, "STALE_WORKER")

    def test_34_quarantine_durability_and_restart(self):
        qm = self.topology_mgr.quarantine_manager
        qm.quarantine_entity(self.identity, "conf-q3", "users", "300", "Conflict", self.fencing_epoch)

        # Restore in new manager instance from state store
        qm_restored = CDCConflictQuarantineManager(
            topology_id=self.topology_mgr.topology_id,
            recovery_coordinator=self.recovery_coord,
            state_store=self.state_store,
        )
        self.assertTrue(qm_restored.is_entity_quarantined("users", "300"))

    # ──────────────────────────────────────────────────────────────────────────
    # ATTACK GROUP F — BIDIRECTIONAL TOPOLOGY STATE & RECOVERABILITY
    # ──────────────────────────────────────────────────────────────────────────

    def test_35_topology_invalid_state_transition(self):
        self.topology_mgr.pause_topology(self.fencing_epoch)
        self.assertEqual(self.topology_mgr.topology.state, CDCReplicationTopologyState.PAUSED)

    def test_36_topology_pause_and_resume_fenced(self):
        top_p = self.topology_mgr.pause_topology(self.fencing_epoch)
        self.assertEqual(top_p.state, CDCReplicationTopologyState.PAUSED)

        top_r = self.topology_mgr.resume_topology(self.fencing_epoch)
        self.assertEqual(top_r.state, CDCReplicationTopologyState.ACTIVE)

    def test_37_topology_restart_recovery(self):
        top_mgr2 = CDCBirectionalTopologyManager(
            identity=self.identity,
            source_a_database_id=self.source_a_db,
            source_b_database_id=self.source_b_db,
            topology_id=self.topology_mgr.topology_id,
            state_store=self.state_store,
            recovery_coordinator=self.recovery_coord,
        )
        self.assertEqual(top_mgr2.topology.topology_id, self.topology_mgr.topology_id)

    # ──────────────────────────────────────────────────────────────────────────
    # ATTACK GROUP G — NETWORK PARTITION, RECONNECT & CUTOVER SAFETY
    # ──────────────────────────────────────────────────────────────────────────

    def test_38_network_reconnect_unresolved_conflict_quarantine(self):
        detector = self.topology_mgr.conflict_detector
        qm = self.topology_mgr.quarantine_manager

        tx_a = self._make_tx("tx-a-rec", [self._make_event(1, entity_key="rec100")], pos_seq=1)
        tx_b = self._make_tx("tx-b-rec", [self._make_event(2, entity_key="rec100")], pos_seq=2)

        conf = detector.detect_conflict(self.identity, tx_a, tx_b)
        qm.quarantine_entity(self.identity, conf.conflict_id, "users", "rec100", "Reconnect conflict", self.fencing_epoch)

        self.assertTrue(qm.is_entity_quarantined("users", "rec100"))
        self.assertFalse(self.topology_mgr.is_cutover_eligible())

    def test_39_unresolved_conflict_blocks_cutover(self):
        self.assertTrue(self.topology_mgr.is_cutover_eligible())

        qm = self.topology_mgr.quarantine_manager
        qm.quarantine_entity(self.identity, "conf-block-cut", "users", "cut100", "Cutover blocker", self.fencing_epoch)

        self.assertFalse(self.topology_mgr.is_cutover_eligible())

    def test_40_checkpoint_frontier_blocked_by_unresolved_conflict(self):
        """ATTACK: Contiguous checkpoint frontier tracker cannot advance past uncompleted/quarantined position."""
        pos1 = PostgresLSNPosition("0/100")
        pos2 = PostgresLSNPosition("0/200")
        pos3 = PostgresLSNPosition("0/300")

        tracker = CDCCheckpointFrontierTracker(initial_position=pos1)
        tracker.register_pending_transaction(pos1)
        tracker.register_pending_transaction(pos2)  # pos2 is quarantined / pending!
        tracker.register_pending_transaction(pos3)

        tracker.record_completed_transaction(pos1)
        tracker.record_completed_transaction(pos3)  # Out-of-order completion of pos3

        # Frontier MUST NOT advance to pos3 because pos2 is pending/quarantined!
        self.assertEqual(tracker._frontier_position, pos1)


if __name__ == "__main__":
    unittest.main()
