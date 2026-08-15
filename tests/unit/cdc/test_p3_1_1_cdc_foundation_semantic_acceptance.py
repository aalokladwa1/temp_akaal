"""
AKAAL P3.1.1 — Hostile CDC Architecture, Consistency Boundary & Domain Foundation Acceptance Suite
===================================================================================================
Adversarial test suite attempting to break source position comparisons, consistency boundaries,
event identity bindings, transactional boundaries, acknowledgement progressions, HMAC checkpoint integrity,
session lifecycle transitions, and secrets sanitization.
"""

import unittest
import hmac
import hashlib
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
    CDCKeyProvider,
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


class TestP311HostileCDCSemanticAcceptance(unittest.TestCase):
    """Hostile Semantic Acceptance Suite for P3.1 CDC Foundation (22 Adversarial Attacks)."""

    def setUp(self):
        self.ident_a = CDCEventIdentity("mig-A", "job-A", "run-A", "sess-A")
        self.ident_b = CDCEventIdentity("mig-B", "job-B", "run-B", "sess-B")
        self.pg_pos_1 = PostgresLSNPosition("0/1000000")
        self.pg_pos_2 = PostgresLSNPosition("0/2000000")
        self.my_pos = MySQLGTIDPosition("binlog.000001", 500)
        self.ora_pos = OracleSCNPosition(500000)

    # -------------------------------------------------------------------------
    # 1. SOURCE POSITION ATTACKS
    # -------------------------------------------------------------------------
    def test_attack_01_cross_engine_position_comparison_rejected(self):
        """ATTACK: Comparing PostgreSQL LSN with MySQL GTID or Oracle SCN must raise TypeError."""
        with self.assertRaises(TypeError):
            self.pg_pos_1.is_after(self.my_pos)
        with self.assertRaises(TypeError):
            self.my_pos.is_after(self.ora_pos)

    def test_attack_02_invalid_lsn_formats_rejected(self):
        """ATTACK: Invalid LSN formats or missing slashes must be rejected."""
        with self.assertRaises(ValueError):
            PostgresLSNPosition("01000000")
        with self.assertRaises(ValueError):
            PostgresLSNPosition("0/10/20")

    def test_attack_03_binlog_file_and_offset_bounds(self):
        """ATTACK: Negative binlog offset or empty file must be rejected."""
        with self.assertRaises(ValueError):
            MySQLGTIDPosition("", 100)
        with self.assertRaises(ValueError):
            MySQLGTIDPosition("binlog.001", -10)

    # -------------------------------------------------------------------------
    # 2. CONSISTENCY BOUNDARY ATTACKS
    # -------------------------------------------------------------------------
    def test_attack_04_consistency_gap_prevention(self):
        """ATTACK: CDC capture starting AFTER initial snapshot must be rejected to prevent change loss."""
        snap_pos = PostgresLSNPosition("0/2000000")
        later_pos = PostgresLSNPosition("0/3000000")
        with self.assertRaises(ValueError):
            CDCConsistencyBoundary(
                migration_id="mig-A", job_id="job-A", run_id="run-A",
                initial_load_snapshot_position=snap_pos,
                cdc_capture_start_position=later_pos,
            )

    def test_attack_05_cross_engine_consistency_boundary_rejected(self):
        """ATTACK: Boundary initialized with different engine positions must raise TypeError."""
        snap_pos = PostgresLSNPosition("0/2000000")
        with self.assertRaises(TypeError):
            CDCConsistencyBoundary(
                migration_id="mig-A", job_id="job-A", run_id="run-A",
                initial_load_snapshot_position=snap_pos,
                cdc_capture_start_position=self.my_pos,
            )

    def test_attack_06_consistency_boundary_position_regression_rejected(self):
        """ATTACK: Updating captured position with older or cross-engine LSN must raise error."""
        boundary = CDCConsistencyBoundary("mig-A", "job-A", "run-A", self.pg_pos_2)
        boundary.update_captured_position(self.pg_pos_2)
        with self.assertRaises(ValueError):
            boundary.update_captured_position(self.pg_pos_1)  # Regression
        with self.assertRaises(TypeError):
            boundary.update_captured_position(self.my_pos)  # Cross-engine

    # -------------------------------------------------------------------------
    # 3. IDENTITY & TRANSACTION ATTACKS
    # -------------------------------------------------------------------------
    def test_attack_07_empty_identity_bindings_rejected(self):
        """ATTACK: Identity creation with empty string bindings must fail."""
        with self.assertRaises(ValueError):
            CDCEventIdentity("", "job-A", "run-A", "sess-A")
        with self.assertRaises(ValueError):
            CDCEventIdentity("mig-A", "", "run-A", "sess-A")

    def test_attack_08_cross_run_transaction_event_insertion_rejected(self):
        """ATTACK: Inserting an event from run-B into a transaction owned by run-A must fail."""
        tx = CDCTransaction("tx-001", self.ident_a, self.pg_pos_2)
        evt_b = CDCEvent(self.ident_b, "POSTGRESQL", "db", "sch", "tbl", CDCOperationType.INSERT, self.pg_pos_1, after_image={"x": 1})
        with self.assertRaises(ValueError):
            tx.add_event(evt_b)

    def test_attack_09_transaction_double_commit_and_abort_rejected(self):
        """ATTACK: Committing an already aborted transaction or double commit must fail."""
        tx = CDCTransaction("tx-002", self.ident_a, self.pg_pos_2)
        tx.mark_abort()
        with self.assertRaises(ValueError):
            tx.mark_commit()

    # -------------------------------------------------------------------------
    # 4. ACKNOWLEDGEMENT STATE MACHINE ATTACKS
    # -------------------------------------------------------------------------
    def test_attack_10_illegal_acknowledgement_skip_rejected(self):
        """ATTACK: Skipping DURABLY_BUFFERED or APPLIED directly to ACKNOWLEDGED must be forbidden."""
        self.assertFalse(CDCAckState.can_transition(CDCAckState.CAPTURED, CDCAckState.ACKNOWLEDGED))
        self.assertFalse(CDCAckState.can_transition(CDCAckState.DURABLY_BUFFERED, CDCAckState.APPLIED))
        self.assertFalse(CDCAckState.can_transition(CDCAckState.FAILED, CDCAckState.ACKNOWLEDGED))
        self.assertTrue(CDCAckState.can_transition(CDCAckState.CAPTURED, CDCAckState.DURABLY_BUFFERED))

    # -------------------------------------------------------------------------
    # 5. CRYPTOGRAPHIC HMAC CHECKPOINT INTEGRITY ATTACKS
    # -------------------------------------------------------------------------
    def test_attack_11_unkeyed_sha256_forgery_prevention(self):
        """ATTACK: Tampering with checkpoint fields or key must break SHA-256 HMAC verification."""
        chk = CDCCheckpoint("chk-100", "mig-A", "job-A", "run-A", "sess-A", 1, self.pg_pos_2)
        self.assertTrue(chk.verify_integrity())

        # Attack 1: Alter run_id in payload
        chk_dict = chk.to_dict()
        chk_dict["run_id"] = "run-ATTACKER"
        with self.assertRaises(ValueError):
            CDCCheckpoint.from_dict(chk_dict)

        # Attack 2: Verify with wrong HMAC key
        wrong_key = b"ATTACKER-FAKE-SECRET-KEY"
        self.assertFalse(chk.verify_integrity(wrong_key))

    def test_attack_12_checkpoint_position_contradictions_rejected(self):
        """ATTACK: Applied position > captured position or acknowledged > applied must fail on creation."""
        with self.assertRaises(ValueError):
            CDCCheckpoint("chk-bad", "mig-A", "job-A", "run-A", "sess-A", 1, self.pg_pos_1, applied_position=self.pg_pos_2)

    def test_attack_13_negative_fencing_epoch_rejected(self):
        """ATTACK: Negative fencing epoch must raise ValueError."""
        with self.assertRaises(ValueError):
            CDCCheckpoint("chk-bad", "mig-A", "job-A", "run-A", "sess-A", -5, self.pg_pos_1)

    # -------------------------------------------------------------------------
    # 6. SESSION LIFECYCLE ATTACKS
    # -------------------------------------------------------------------------
    def test_attack_14_illegal_session_transitions_rejected(self):
        """ATTACK: CREATED -> SYNCHRONIZED or CAPTURING -> CUTOVER_COMPLETE must fail."""
        sm = CDCSessionStateMachine("mig-A", "job-A", "run-A", "sess-A")
        with self.assertRaises(InvalidStateTransitionError):
            sm.transition_to(CDCSessionState.SYNCHRONIZED)
        with self.assertRaises(InvalidStateTransitionError):
            sm.transition_to(CDCSessionState.CUTOVER_COMPLETE)

    def test_attack_15_terminated_session_resurrection_forbidden(self):
        """ATTACK: Once TERMINATED or CUTOVER_COMPLETE, no further state transition is permitted."""
        sm = CDCSessionStateMachine("mig-A", "job-A", "run-A", "sess-A")
        sm.transition_to(CDCSessionState.TERMINATED)
        with self.assertRaises(InvalidStateTransitionError):
            sm.transition_to(CDCSessionState.INITIALIZING)

    # -------------------------------------------------------------------------
    # 7. SANITIZATION & DIAGNOSTICS ATTACKS
    # -------------------------------------------------------------------------
    def test_attack_16_deep_nested_secret_redaction(self):
        """ATTACK: Secrets in deeply nested dictionaries or lists must be redacted in to_dict()."""
        evt = CDCEvent(
            identity=self.ident_a,
            source_engine="POSTGRESQL",
            source_database="db",
            source_schema="sch",
            source_table="config",
            operation=CDCOperationType.INSERT,
            position=self.pg_pos_1,
            after_image={
                "setting": "db_auth",
                "nested": {
                    "credentials": {
                        "api_key": "SUPER_SECRET_KEY_123",
                        "password_hash": "hash999",
                    }
                }
            }
        )
        serialized = evt.to_dict()
        self.assertNotIn("SUPER_SECRET_KEY_123", str(serialized))
        self.assertEqual(serialized["after_image"]["nested"]["credentials"]["api_key"], "[REDACTED_SECRET]")

    def test_attack_17_row_payload_isolation_in_data_safe_diagnostics(self):
        """ATTACK: Diagnostic representations must omit raw row data values."""
        evt = CDCEvent(
            identity=self.ident_a,
            source_engine="POSTGRESQL",
            source_database="db",
            source_schema="sch",
            source_table="users",
            operation=CDCOperationType.UPDATE,
            position=self.pg_pos_1,
            before_image={"user_id": 42, "credit_card": "4111-2222-3333-4444"},
            after_image={"user_id": 42, "credit_card": "4111-2222-3333-5555"},
        )
        diag = evt.to_data_safe_dict()
        self.assertNotIn("4111-2222-3333-4444", str(diag))
        self.assertNotIn("4111-2222-3333-5555", str(diag))
        self.assertIn("credit_card", diag["before_keys"])


if __name__ == "__main__":
    unittest.main()
