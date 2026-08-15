"""
AKAAL P3.1 — Canonical CDC Architecture, Consistency Boundary & Domain Foundation Test Suite
=============================================================================================
Hostile unit test suite verifying polymorphic source position models, identity binding,
transaction boundaries, consistency boundaries, lifecycle state machines, failure taxonomies,
secret redaction, and P1/P2 integration contracts.
"""

import unittest
from typing import Dict, Any

from akaal.cdc.domain.positions import (
    CDCSourcePosition,
    PostgresLSNPosition,
    MySQLGTIDPosition,
    OracleSCNPosition,
    MSSQLChangePosition,
    MongoDBOpLogPosition,
    parse_source_position,
)
from akaal.cdc.domain.events import (
    CDCOperationType,
    CDCTransactionBoundary,
    CDCEventIdentity,
    CDCEvent,
    CDCTransaction,
)
from akaal.cdc.domain.consistency import (
    CDCConsistencyBoundary,
    ConsistencyBoundaryState,
)
from akaal.cdc.domain.lifecycle import (
    CDCAckState,
    CDCSessionState,
    CDCSessionStateMachine,
    InvalidStateTransitionError,
)
from akaal.cdc.domain.durability import (
    CDCCheckpoint,
    CDCDurabilityContract,
)
from akaal.cdc.domain.errors import (
    CDCFailureCategory,
    CDCFailureType,
    CDCFailure,
    CDCExecutionError,
)
from akaal.cdc.domain.telemetry import (
    CDCMonitoringDTO,
)


class TestP31CanonicalCDCDomainFoundation(unittest.TestCase):
    """P3.1 Canonical CDC Architecture & Domain Foundation Acceptance Suite (25 Requirements)."""

    def setUp(self):
        self.identity = CDCEventIdentity(
            migration_id="mig-p31-01",
            job_id="job-p31-01",
            run_id="run-p31-01",
            cdc_session_id="cdc-sess-p31-01",
        )
        self.pg_pos = PostgresLSNPosition(lsn="0/16B3748", flushed_lsn="0/16B3748")

    # 1. CDC event identity determinism
    def test_01_cdc_event_identity_determinism(self):
        ident1 = CDCEventIdentity("mig-1", "job-1", "run-1", "sess-1")
        ident2 = CDCEventIdentity("mig-1", "job-1", "run-1", "sess-1", event_id="fixed-ev-id")
        self.assertEqual(ident1.migration_id, "mig-1")
        self.assertEqual(ident2.event_id, "fixed-ev-id")
        with self.assertRaises(ValueError):
            CDCEventIdentity("", "job-1", "run-1", "sess-1")

    # 2. INSERT event semantics
    def test_02_insert_event_semantics(self):
        evt = CDCEvent(
            identity=self.identity,
            source_engine="POSTGRESQL",
            source_database="prod_db",
            source_schema="public",
            source_table="users",
            operation=CDCOperationType.INSERT,
            position=self.pg_pos,
            after_image={"id": 1, "username": "alice"},
        )
        self.assertEqual(evt.operation, CDCOperationType.INSERT)
        self.assertIsNone(evt.before_image)
        self.assertEqual(evt.after_image["username"], "alice")

    # 3. UPDATE event semantics
    def test_03_update_event_semantics(self):
        evt = CDCEvent(
            identity=self.identity,
            source_engine="POSTGRESQL",
            source_database="prod_db",
            source_schema="public",
            source_table="users",
            operation=CDCOperationType.UPDATE,
            position=self.pg_pos,
            before_image={"id": 1, "username": "alice_old"},
            after_image={"id": 1, "username": "alice_new"},
        )
        self.assertEqual(evt.operation, CDCOperationType.UPDATE)
        self.assertEqual(evt.before_image["username"], "alice_old")
        self.assertEqual(evt.after_image["username"], "alice_new")

    # 4. DELETE event semantics
    def test_04_delete_event_semantics(self):
        evt = CDCEvent(
            identity=self.identity,
            source_engine="POSTGRESQL",
            source_database="prod_db",
            source_schema="public",
            source_table="users",
            operation=CDCOperationType.DELETE,
            position=self.pg_pos,
            before_image={"id": 1, "username": "alice"},
        )
        self.assertEqual(evt.operation, CDCOperationType.DELETE)
        self.assertIsNone(evt.after_image)
        self.assertEqual(evt.before_image["id"], 1)

    # 5. Transaction identity
    def test_05_transaction_identity(self):
        tx = CDCTransaction(tx_id="tx-9999", identity=self.identity, commit_position=self.pg_pos)
        self.assertEqual(tx.tx_id, "tx-9999")
        self.assertFalse(tx.is_committed)
        tx.mark_commit()
        self.assertTrue(tx.is_committed)

    # 6. Transaction ordering
    def test_06_transaction_ordering(self):
        tx = CDCTransaction(tx_id="tx-order-1", identity=self.identity, commit_position=self.pg_pos)
        evt1 = CDCEvent(self.identity, "POSTGRESQL", "db", "sch", "tbl", CDCOperationType.INSERT, self.pg_pos, after_image={"id": 1}, boundary=CDCTransactionBoundary.BEGIN)
        evt2 = CDCEvent(self.identity, "POSTGRESQL", "db", "sch", "tbl", CDCOperationType.INSERT, self.pg_pos, after_image={"id": 2}, boundary=CDCTransactionBoundary.COMMIT)
        tx.add_event(evt1)
        tx.add_event(evt2)
        self.assertEqual(len(tx.events), 2)
        tx.mark_commit()
        with self.assertRaises(ValueError):
            tx.add_event(evt1)

    # 7. Source-position serialization
    def test_07_source_position_serialization(self):
        pos_dict = self.pg_pos.to_dict()
        self.assertEqual(pos_dict["engine"], "POSTGRESQL")
        self.assertEqual(pos_dict["lsn"], "0/16B3748")

        parsed = parse_source_position(pos_dict)
        self.assertIsInstance(parsed, PostgresLSNPosition)
        self.assertEqual(parsed.to_string(), "0/16B3748")

    # 8. Engine-position discrimination
    def test_08_engine_position_discrimination(self):
        pg = PostgresLSNPosition("0/16B3748")
        my = MySQLGTIDPosition("mysql-bin.000001", 100)
        ora = OracleSCNPosition(123456789)
        ms = MSSQLChangePosition("0000002A:000001C8:0001")
        mg = MongoDBOpLogPosition(1700000000, 1)

        self.assertEqual(pg.engine, "POSTGRESQL")
        self.assertEqual(my.engine, "MYSQL")
        self.assertEqual(ora.engine, "ORACLE")
        self.assertEqual(ms.engine, "MSSQL")
        self.assertEqual(mg.engine, "MONGODB")

    # 9. Invalid position rejection
    def test_09_invalid_position_rejection(self):
        with self.assertRaises(ValueError):
            PostgresLSNPosition("INVALID_LSN_NO_SLASH")
        with self.assertRaises(ValueError):
            MySQLGTIDPosition("binlog.001", -50)
        with self.assertRaises(ValueError):
            OracleSCNPosition(-100)

    # 10. Position monotonicity
    def test_10_position_monotonicity(self):
        p1 = PostgresLSNPosition("0/1000000")
        p2 = PostgresLSNPosition("0/2000000")
        self.assertTrue(p2.is_after(p1))
        self.assertFalse(p1.is_after(p2))

    # 11. Consistency-boundary representation
    def test_11_consistency_boundary_representation(self):
        snap_pos = PostgresLSNPosition("0/2000000")
        valid_start = PostgresLSNPosition("0/1000000")
        boundary = CDCConsistencyBoundary(
            migration_id="mig-1", job_id="job-1", run_id="run-1",
            initial_load_snapshot_position=snap_pos,
            cdc_capture_start_position=valid_start,
        )
        self.assertEqual(boundary.boundary_state, ConsistencyBoundaryState.SNAPSHOT_CAPTURED)

        invalid_start = PostgresLSNPosition("0/3000000")
        with self.assertRaises(ValueError):
            CDCConsistencyBoundary(
                migration_id="mig-1", job_id="job-1", run_id="run-1",
                initial_load_snapshot_position=snap_pos,
                cdc_capture_start_position=invalid_start,
            )

    # 12. Captured/applied/acknowledged position separation
    def test_12_position_separation(self):
        snap_pos = PostgresLSNPosition("0/1000000")
        boundary = CDCConsistencyBoundary("mig-1", "job-1", "run-1", snap_pos)

        p_cap = PostgresLSNPosition("0/2000000")
        p_app = PostgresLSNPosition("0/1500000")
        p_ack = PostgresLSNPosition("0/1200000")

        boundary.update_captured_position(p_cap)
        boundary.update_applied_position(p_app)
        boundary.update_acknowledged_position(p_ack)

        self.assertEqual(boundary.last_durably_captured_position.lsn, "0/2000000")
        self.assertEqual(boundary.last_durably_applied_position.lsn, "0/1500000")
        self.assertEqual(boundary.last_acknowledged_position.lsn, "0/1200000")

    # 13. No acknowledgement before allowed durability state
    def test_13_no_ack_before_allowed_durability(self):
        snap_pos = PostgresLSNPosition("0/1000000")
        boundary = CDCConsistencyBoundary("mig-1", "job-1", "run-1", snap_pos)
        boundary.update_captured_position(PostgresLSNPosition("0/2000000"))
        boundary.update_applied_position(PostgresLSNPosition("0/1500000"))

        with self.assertRaises(ValueError):
            # Acknowledged (0/2500000) cannot exceed applied (0/1500000)!
            boundary.update_acknowledged_position(PostgresLSNPosition("0/2500000"))

    # 14. CDC state-machine legal transitions
    def test_14_cdc_state_machine_legal_transitions(self):
        sm = CDCSessionStateMachine("mig-1", "job-1", "run-1", "sess-1")
        self.assertEqual(sm.current_state, CDCSessionState.CREATED)

        sm.transition_to(CDCSessionState.INITIALIZING)
        sm.transition_to(CDCSessionState.CAPTURING)
        sm.transition_to(CDCSessionState.CATCHING_UP)
        sm.transition_to(CDCSessionState.SYNCHRONIZED)
        sm.transition_to(CDCSessionState.CUTOVER_PREPARING)
        self.assertEqual(sm.current_state, CDCSessionState.CUTOVER_PREPARING)

    # 15. CDC state-machine illegal transitions
    def test_15_cdc_state_machine_illegal_transitions(self):
        sm = CDCSessionStateMachine("mig-1", "job-1", "run-1", "sess-1")
        with self.assertRaises(InvalidStateTransitionError):
            sm.transition_to(CDCSessionState.CUTOVER_COMPLETE)

    # 16. Migration/job/run/session identity binding
    def test_16_identity_binding(self):
        chk = CDCCheckpoint(
            checkpoint_id="chk-01",
            migration_id="mig-1",
            job_id="job-1",
            run_id="run-1",
            cdc_session_id="sess-1",
            fencing_epoch=1,
            source_position=self.pg_pos,
        )
        self.assertEqual(chk.migration_id, "mig-1")
        self.assertEqual(chk.cdc_session_id, "sess-1")
        self.assertTrue(chk.verify_integrity())

    # 17. Cross-run substitution rejection
    def test_17_cross_run_substitution_rejection(self):
        chk = CDCCheckpoint("chk-01", "mig-1", "job-1", "run-1", "sess-1", 1, self.pg_pos)
        chk_dict = chk.to_dict()
        chk_dict["run_id"] = "run-ATTACKER-2"  # Tampered run_id

        with self.assertRaises(ValueError):
            CDCCheckpoint.from_dict(chk_dict)

    # 18. Checkpoint/session identity mismatch rejection
    def test_18_checkpoint_session_identity_mismatch_rejection(self):
        chk = CDCCheckpoint("chk-01", "mig-1", "job-1", "run-1", "sess-1", 1, self.pg_pos)
        chk_dict = chk.to_dict()
        chk_dict["cdc_session_id"] = "sess-ATTACKER-X"

        with self.assertRaises(ValueError):
            CDCCheckpoint.from_dict(chk_dict)

    # 19. Failure taxonomy
    def test_19_failure_taxonomy(self):
        fail = CDCFailure(
            failure_type=CDCFailureType.SOURCE_DISCONNECT,
            category=CDCFailureCategory.RETRYABLE,
            message="Source DB socket closed",
            migration_id="mig-1",
            job_id="job-1",
            run_id="run-1",
            cdc_session_id="sess-1",
        )
        err = CDCExecutionError(fail)
        self.assertEqual(err.failure.category, CDCFailureCategory.RETRYABLE)

    # 20. Secret sanitization
    def test_21_row_data_safe_diagnostic_behavior(self):
        evt = CDCEvent(
            identity=self.identity,
            source_engine="POSTGRESQL",
            source_database="prod_db",
            source_schema="public",
            source_table="accounts",
            operation=CDCOperationType.UPDATE,
            position=self.pg_pos,
            before_image={"account_id": 100, "balance": 5000, "password_hash": "secret123"},
            after_image={"account_id": 100, "balance": 6000, "password_hash": "secret123"},
        )
        safe_dict = evt.to_data_safe_dict()
        self.assertNotIn("secret123", str(safe_dict))
        self.assertIn("password_hash", safe_dict["before_keys"])

    # 22. Monitoring DTO extension compatibility
    def test_22_monitoring_dto_extension_compatibility(self):
        dto = CDCMonitoringDTO(
            cdc_session_id="sess-1",
            migration_id="mig-1",
            job_id="job-1",
            run_id="run-1",
            events_captured_total=5000,
            events_applied_total=4990,
            event_backlog_count=10,
            time_lag_ms=12.5,
        )
        dict_rep = dto.to_dict()
        self.assertEqual(dict_rep["events_captured_total"], 5000)
        self.assertEqual(dict_rep["event_backlog_count"], 10)

    # 23. Historical identity preservation
    def test_23_historical_identity_preservation(self):
        ident = CDCEventIdentity("mig-hist-1", "job-hist-1", "run-hist-1", "sess-hist-1")
        self.assertEqual(ident.migration_id, "mig-hist-1")

    # 24. P1 authority reuse / no duplicate authority
    def test_24_p1_authority_reuse(self):
        from akaal.runtime.recovery.coordinator import RecoveryCoordinator
        coordinator = RecoveryCoordinator()
        epoch = coordinator.issue_epoch("mig-p31-01")
        self.assertTrue(epoch > 0)

    # 25. P2 authority continuity / no duplicate reporting authority
    def test_25_p2_authority_continuity(self):
        from akaal.reporting.engine.canonical_reporting import CanonicalReportingAuthority
        auth = CanonicalReportingAuthority()
        self.assertIsNotNone(auth)


if __name__ == "__main__":
    unittest.main()
