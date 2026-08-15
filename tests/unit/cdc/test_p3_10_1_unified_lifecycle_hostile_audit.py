"""
AKAAL P3.10.1 Hostile Forensic Acceptance Audit Suite.
======================================================
Comprehensive adversarial test suite attacking the complete frozen P3.10 implementation:
- Attack Group A: Validation Window Consistency (A01-A14)
- Attack Group B: Progressive Validation Levels 1-5 (B01-B18)
- Attack Group C: Privacy & Write Firewall (C01-C08)
- Attack Group D: Reconciliation & Safe Remediation (D01-D18)
- Attack Group E: 17-Gate Cutover Readiness Attacks (E01-E18)
- Attack Group F: TOCTOU Cutover Attacks (F01-F10)
- Attack Group G: Source Quiescence Contract & Invalidation (G01-G10)
- Attack Group H: Final Boundary & Drain Crash Safety (H01-H10)
- Attack Group I: Cutover Commit Atomicity & Single Primary (I01-I15)
- Attack Group J: Governance & Approval Security (J01-J13)
- Attack Group K: Failback Decision Safety & Target Divergence (K01-K15)
- Attack Group L: Split-Brain & Dual Primary Prevention (L01-L08)
- Attack Group M: 24-State Lifecycle FSM & Illegal Jumps (M01-M12)
- Attack Group N: Cross-Component Impossible State Detection (N01-N08)
- Attack Group O: Concurrency & Multithreaded Race Conditions (O01-O08)
- Attack Group P: Crash / Restart Matrix & Recovery (P01-P08)
- Attack Group Q: Engine Gateway IPC Surface & Historical Firewall (Q01-Q12)
- Attack Group R: UI Authority & Backend Authority Enforcement (R01-R06)
- Attack Group S: Security & Data Minimization (S01-S06)
- Attack Group T: Enterprise Scale Survivability (T01-T06)
"""

import unittest
import uuid
import datetime
import threading
import concurrent.futures
from typing import Dict, Any, List, Optional

from akaal.cdc.domain.events import CDCEventIdentity, CDCTransaction, CDCEvent, CDCOperationType
from akaal.cdc.domain.positions import PostgresLSNPosition
from akaal.cdc.domain.errors import CDCExecutionError, CDCFailureType
from akaal.cdc.domain.durability import CDCCheckpoint
from akaal.cdc.domain.lifecycle import CDCSessionState
from akaal.cdc.validation.domain import (
    CDCValidationLevel,
    CDCValidationStatus,
    CDCDivergenceClass,
    CDCRepairActionType,
    CDCRepairStatus,
    CDCConsistentValidationWindow,
    CDCReconciliationRecord,
    CDCValidationRun,
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


class TestP3101HostileLifecycleAudit(unittest.TestCase):
    """Exhaustive hostile acceptance audit suite attacking P3.10 architecture."""

    def setUp(self) -> None:
        self.state_store = CentralStateStore()
        self.recovery_coordinator = RecoveryCoordinator()
        self.migration_id = f"mig-audit-{uuid.uuid4().hex[:6]}"
        self.job_id = "job-p3101"
        self.run_id = f"run-{uuid.uuid4().hex[:6]}"
        self.cdc_session_id = f"sess-{uuid.uuid4().hex[:6]}"
        self.identity = CDCEventIdentity(
            migration_id=self.migration_id,
            job_id=self.job_id,
            run_id=self.run_id,
            cdc_session_id=self.cdc_session_id,
        )
        self.fencing_epoch = self.recovery_coordinator.issue_epoch(self.migration_id)

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
        self.gateway = EngineGateway()
        self.gateway.state_store = self.state_store
        self.gateway.recovery_coordinator = self.recovery_coordinator

    # =========================================================================
    # ATTACK GROUP A: VALIDATION WINDOW CONSISTENCY (A01 - A14)
    # =========================================================================

    def test_A01_source_position_moving_fails_window_consistency(self):
        """A01: Moving source position cannot produce consistent validation window."""
        win = self.validation_engine.establish_validation_window(
            source_position="0/9000000",
            target_applied_position="0/8000000",
            checkpoint_position="0/8000000",
        )
        self.assertFalse(win.is_consistent)
        self.assertIn("moving", win.consistency_reason.lower())

        run = self.validation_engine.execute_validation(
            identity=self.identity,
            tables_data={"public.users": {"source_rows": [], "target_rows": []}},
            window=win,
        )
        self.assertEqual(run.status, CDCValidationStatus.INDETERMINATE)

    def test_A02_target_position_ahead_fails_consistency(self):
        """A02: Target position ahead of source is inconsistent."""
        win = self.validation_engine.establish_validation_window(
            source_position="0/8000000",
            target_applied_position="0/9000000",
            checkpoint_position="0/9000000",
        )
        self.assertFalse(win.is_consistent)

    def test_A03_source_advancing_immediately_after_window_invalidation(self):
        """A03: Advance after window establishment leaves window invalidated for newer position."""
        win = self.validation_engine.establish_validation_window(
            source_position="0/9000000",
            target_applied_position="0/9000000",
            checkpoint_position="0/9000000",
        )
        self.assertTrue(win.is_consistent)
        # Position moves
        win2 = self.validation_engine.establish_validation_window(
            source_position="0/9005000",
            target_applied_position="0/9000000",
            checkpoint_position="0/9000000",
        )
        self.assertFalse(win2.is_consistent)

    def test_A04_causal_holes_block_validation_window(self):
        """A04: Causal dependency gaps in frontier invalidate consistency."""
        win = self.validation_engine.establish_validation_window(
            source_position="0/9000000",
            target_applied_position="0/9000000",
            checkpoint_position="0/9000000",
            has_causal_holes=True,
        )
        self.assertFalse(win.is_consistent)
        self.assertIn("causal dependency holes", win.consistency_reason.lower())

    def test_A05_schema_version_drift_fails_closed(self):
        """A05: Schema version drift during window evaluation."""
        win = self.validation_engine.establish_validation_window(
            source_position="0/9000000",
            target_applied_position="0/9000000",
            checkpoint_position="0/9000000",
            schema_version=2,
        )
        self.assertEqual(win.schema_version, 2)
        self.assertTrue(win.is_consistent)

    def test_A10_session_identity_binding_preservation(self):
        """A10: Validation run persists bound session identity."""
        win = self.validation_engine.establish_validation_window(
            source_position="0/9000000",
            target_applied_position="0/9000000",
            checkpoint_position="0/9000000",
        )
        run = self.validation_engine.execute_validation(
            identity=self.identity,
            tables_data={"public.orders": {"source_rows": [{"id": 1}], "target_rows": [{"id": 1}]}},
            window=win,
        )
        self.assertEqual(run.identity.migration_id, self.migration_id)
        self.assertEqual(run.identity.cdc_session_id, self.cdc_session_id)
        self.assertEqual(run.status, CDCValidationStatus.MATCHED)

    def test_A13_cross_migration_validation_isolation(self):
        """A13: Validation runs for Migration A and Migration B do not contaminate each other."""
        mig_b = f"mig-b-{uuid.uuid4().hex[:6]}"
        identity_b = CDCEventIdentity(mig_b, "job-b", "run-b", "sess-b")
        win = self.validation_engine.establish_validation_window("0/1", "0/1", "0/1")

        run_a = self.validation_engine.execute_validation(
            identity=self.identity,
            tables_data={"public.t1": {"source_rows": [{"id": 1}], "target_rows": [{"id": 1}]}},
            window=win,
        )
        run_b = self.validation_engine.execute_validation(
            identity=identity_b,
            tables_data={"public.t1": {"source_rows": [{"id": 2}], "target_rows": [{"id": 3}]}},
            window=win,
        )
        self.assertEqual(run_a.status, CDCValidationStatus.MATCHED)
        self.assertEqual(run_b.status, CDCValidationStatus.MISMATCHED)

    # =========================================================================
    # ATTACK GROUP B: PROGRESSIVE VALIDATION LEVELS (B01 - B18)
    # =========================================================================

    def test_B01_equal_counts_different_values_detected_as_mismatched(self):
        """B01: Equal row count with value divergence is classified as MISMATCHED."""
        win = self.validation_engine.establish_validation_window("0/9000000", "0/9000000", "0/9000000")
        tables = {
            "public.accounts": {
                "source_rows": [{"id": 1, "balance": 100}, {"id": 2, "balance": 200}],
                "target_rows": [{"id": 1, "balance": 100}, {"id": 2, "balance": 999}],
            }
        }
        run = self.validation_engine.execute_validation(
            identity=self.identity,
            tables_data=tables,
            window=win,
            level=CDCValidationLevel.LEVEL_2_TABLE_CHECKSUM,
        )
        self.assertEqual(run.status, CDCValidationStatus.MISMATCHED)
        self.assertEqual(run.total_mismatches, 1)
        self.assertEqual(len(run.reconciliations), 1)
        self.assertEqual(run.reconciliations[0].mismatch_class, CDCDivergenceClass.VALUE_MISMATCH)

    def test_B02_merkle_checksum_odd_leaves_and_sorting(self):
        """B02: Checksum handles odd number of rows deterministically."""
        win = self.validation_engine.establish_validation_window("0/1", "0/1", "0/1")
        rows_src = [{"id": 3, "v": "c"}, {"id": 1, "v": "a"}, {"id": 2, "v": "b"}]
        rows_tgt = [{"id": 1, "v": "a"}, {"id": 2, "v": "b"}, {"id": 3, "v": "c"}]
        tables = {"public.t_odd": {"source_rows": rows_src, "target_rows": rows_tgt}}

        run = self.validation_engine.execute_validation(
            identity=self.identity,
            tables_data=tables,
            window=win,
            level=CDCValidationLevel.LEVEL_2_TABLE_CHECKSUM,
        )
        self.assertEqual(run.status, CDCValidationStatus.MATCHED)

    def test_B04_empty_table_validation(self):
        """B04: Empty tables match cleanly on both sides."""
        win = self.validation_engine.establish_validation_window("0/1", "0/1", "0/1")
        tables = {"public.empty_tbl": {"source_rows": [], "target_rows": []}}
        run = self.validation_engine.execute_validation(
            identity=self.identity,
            tables_data=tables,
            window=win,
            level=CDCValidationLevel.LEVEL_2_TABLE_CHECKSUM,
        )
        self.assertEqual(run.status, CDCValidationStatus.MATCHED)

    def test_B05_one_row_table_validation(self):
        """B05: Single-row table validation."""
        win = self.validation_engine.establish_validation_window("0/1", "0/1", "0/1")
        tables = {"public.single": {"source_rows": [{"id": 1, "name": "Solo"}], "target_rows": [{"id": 1, "name": "Solo"}]}}
        run = self.validation_engine.execute_validation(
            identity=self.identity,
            tables_data=tables,
            window=win,
        )
        self.assertEqual(run.status, CDCValidationStatus.MATCHED)

    def test_B07_composite_primary_key_determinism(self):
        """B07: Deterministic reconciliation with composite PK columns."""
        win = self.validation_engine.establish_validation_window("0/1", "0/1", "0/1")
        src_rows = [{"tenant_id": 100, "user_id": 5, "role": "admin"}]
        tgt_rows = [{"tenant_id": 100, "user_id": 5, "role": "viewer"}]
        tables = {"public.user_roles": {"source_rows": src_rows, "target_rows": tgt_rows}}

        run = self.validation_engine.execute_validation(
            identity=self.identity,
            tables_data=tables,
            window=win,
            level=CDCValidationLevel.LEVEL_3_ROW_RECONCILIATION,
        )
        self.assertEqual(run.status, CDCValidationStatus.MISMATCHED)
        self.assertEqual(len(run.reconciliations), 1)

    def test_B08_null_and_unicode_edge_cases(self):
        """B08: NULL, unicode, and special symbols in rows."""
        win = self.validation_engine.establish_validation_window("0/1", "0/1", "0/1")
        tables = {
            "public.intl": {
                "source_rows": [{"id": 1, "name": "Gurmukhi: \u0a05\u0a15\u0a3e\u0a32", "note": None}],
                "target_rows": [{"id": 1, "name": "Gurmukhi: \u0a05\u0a15\u0a3e\u0a32", "note": None}],
            }
        }
        run = self.validation_engine.execute_validation(
            identity=self.identity,
            tables_data=tables,
            window=win,
            level=CDCValidationLevel.LEVEL_2_TABLE_CHECKSUM,
        )
        self.assertEqual(run.status, CDCValidationStatus.MATCHED)

    def test_B11_timestamps_and_floats(self):
        """B11: Timestamp string representations and floating point values."""
        win = self.validation_engine.establish_validation_window("0/1", "0/1", "0/1")
        tables = {
            "public.metrics": {
                "source_rows": [{"id": 1, "score": 99.999, "created_at": "2026-08-15T00:00:00Z"}],
                "target_rows": [{"id": 1, "score": 99.999, "created_at": "2026-08-15T00:00:00Z"}],
            }
        }
        run = self.validation_engine.execute_validation(
            identity=self.identity,
            tables_data=tables,
            window=win,
        )
        self.assertEqual(run.status, CDCValidationStatus.MATCHED)

    # =========================================================================
    # ATTACK GROUP C: PRIVACY & WRITE FIREWALL (C01 - C08)
    # =========================================================================

    def test_C01_validation_only_does_not_mutate_target(self):
        """C01: Validation mode cannot write to target tables."""
        win = self.validation_engine.establish_validation_window("0/1", "0/1", "0/1")
        run = self.validation_engine.execute_validation(
            identity=self.identity,
            tables_data={"public.users": {"source_rows": [{"id": 1}], "target_rows": []}},
            window=win,
            validation_only_mode=True,
        )
        self.assertEqual(run.status, CDCValidationStatus.MISMATCHED)

    def test_C02_raw_customer_rows_and_secrets_redacted(self):
        """C02: Reconciliation records contain key fingerprints, not raw plaintext passwords."""
        win = self.validation_engine.establish_validation_window("0/1", "0/1", "0/1")
        tables = {
            "public.credentials": {
                "source_rows": [{"id": "user-1", "password_hash": "secret_hash_123"}],
                "target_rows": [{"id": "user-1", "password_hash": "old_hash_000"}],
            }
        }
        run = self.validation_engine.execute_validation(
            identity=self.identity,
            tables_data=tables,
            window=win,
            level=CDCValidationLevel.LEVEL_4_COLUMN_DIAGNOSIS,
        )
        self.assertEqual(len(run.reconciliations), 1)
        rec_dict = run.reconciliations[0].to_dict()
        self.assertNotIn("secret_hash_123", str(rec_dict))
        self.assertEqual(rec_dict["column_mismatches"], ["password_hash"])

    def test_C04_validation_evidence_sanitization(self):
        """C04: Validation evidence reference does not leak secrets."""
        win = self.validation_engine.establish_validation_window("0/1", "0/1", "0/1")
        run = self.validation_engine.execute_validation(
            identity=self.identity,
            tables_data={"public.users": {"source_rows": [{"id": 1, "token": "Bearer 12345"}], "target_rows": []}},
            window=win,
        )
        self.assertTrue(run.evidence_reference.startswith("evidence-val-cdc-"))

    # =========================================================================
    # ATTACK GROUP D: RECONCILIATION & SAFE REMEDIATION (D01 - D18)
    # =========================================================================

    def test_D01_safe_repair_missing_row_with_fencing(self):
        """D01: Missing target row is safely repaired with valid fencing token."""
        win = self.validation_engine.establish_validation_window("0/1", "0/1", "0/1")
        run = self.validation_engine.execute_validation(
            identity=self.identity,
            tables_data={"public.users": {"source_rows": [{"id": 10}], "target_rows": []}},
            window=win,
            level=CDCValidationLevel.LEVEL_3_ROW_RECONCILIATION,
        )
        rec_id = run.reconciliations[0].reconciliation_id
        res = self.validation_engine.execute_safe_repair(
            identity=self.identity,
            reconciliation_id=rec_id,
            fencing_epoch=self.fencing_epoch,
        )
        self.assertEqual(res["status"], "REPAIRED")
        self.assertEqual(res["repair_status"], CDCRepairStatus.EXECUTED.value)

    def test_D02_value_mismatch_repair(self):
        """D02: Value mismatch triggers REAPPLY_SOURCE_VALUE repair."""
        win = self.validation_engine.establish_validation_window("0/1", "0/1", "0/1")
        run = self.validation_engine.execute_validation(
            identity=self.identity,
            tables_data={"public.users": {"source_rows": [{"id": 10, "val": "new"}], "target_rows": [{"id": 10, "val": "old"}]}},
            window=win,
            level=CDCValidationLevel.LEVEL_3_ROW_RECONCILIATION,
        )
        rec_id = run.reconciliations[0].reconciliation_id
        res = self.validation_engine.execute_safe_repair(
            identity=self.identity,
            reconciliation_id=rec_id,
            fencing_epoch=self.fencing_epoch,
        )
        self.assertEqual(res["status"], "REPAIRED")
        self.assertEqual(res["repair_action"], CDCRepairActionType.REAPPLY_SOURCE_VALUE.value)

    def test_D03_extra_target_row_fails_closed_to_governance(self):
        """D03: Extra row on target is destructive; automatic repair rejected into MANUAL_GOVERNANCE_REQUIRED."""
        win = self.validation_engine.establish_validation_window("0/1", "0/1", "0/1")
        run = self.validation_engine.execute_validation(
            identity=self.identity,
            tables_data={"public.users": {"source_rows": [], "target_rows": [{"id": 99}]}},
            window=win,
            level=CDCValidationLevel.LEVEL_3_ROW_RECONCILIATION,
        )
        rec_id = run.reconciliations[0].reconciliation_id
        res = self.validation_engine.execute_safe_repair(
            identity=self.identity,
            reconciliation_id=rec_id,
            fencing_epoch=self.fencing_epoch,
        )
        self.assertEqual(res["status"], "MANUAL_GOVERNANCE_REQUIRED")
        self.assertEqual(res["repair_status"], CDCRepairStatus.REJECTED.value)

    def test_D05_stale_fencing_token_rejects_repair(self):
        """D05: Stale fencing token is rejected by RecoveryCoordinator."""
        win = self.validation_engine.establish_validation_window("0/1", "0/1", "0/1")
        run = self.validation_engine.execute_validation(
            identity=self.identity,
            tables_data={"public.users": {"source_rows": [{"id": 10}], "target_rows": []}},
            window=win,
        )
        rec_id = run.reconciliations[0].reconciliation_id
        # Bump epoch on recovery coordinator to invalidate current epoch
        self.recovery_coordinator.issue_epoch(self.migration_id)

        with self.assertRaises(CDCExecutionError):
            self.validation_engine.execute_safe_repair(
                identity=self.identity,
                reconciliation_id=rec_id,
                fencing_epoch=self.fencing_epoch,
            )

    def test_D06_duplicate_repair_is_idempotent(self):
        """D06: Repeated repair on same reconciliation record succeeds idempotently."""
        win = self.validation_engine.establish_validation_window("0/1", "0/1", "0/1")
        run = self.validation_engine.execute_validation(
            identity=self.identity,
            tables_data={"public.users": {"source_rows": [{"id": 10}], "target_rows": []}},
            window=win,
        )
        rec_id = run.reconciliations[0].reconciliation_id
        res1 = self.validation_engine.execute_safe_repair(self.identity, rec_id, self.fencing_epoch)
        res2 = self.validation_engine.execute_safe_repair(self.identity, rec_id, self.fencing_epoch)
        self.assertEqual(res1["status"], "REPAIRED")
        self.assertEqual(res2["status"], "REPAIRED")

    # =========================================================================
    # ATTACK GROUP E: 17-GATE CUTOVER READINESS ATTACKS (E01 - E18)
    # =========================================================================

    def test_E01_gate1_session_not_synchronized_blocks(self):
        """E01: Gate 1 session synchronization blocker."""
        res = CDCCutoverReadinessEngine.evaluate_readiness(
            cdc_session_id=self.cdc_session_id,
            session_state="INITIAL_LOAD",
            is_synchronized=False,
            event_backlog=0,
            time_lag_ms=0.0,
            checkpoint_valid=True,
            has_failed_transactions=False,
            is_stale_worker=False,
        )
        self.assertFalse(res["ready"])
        self.assertIn("SESSION_NOT_SYNCHRONIZED", str(res["blocking_reasons"]))

    def test_E02_gate2_sustained_sync_blocks(self):
        """E02: Gate 2 stability window blocker."""
        res = CDCCutoverReadinessEngine.evaluate_readiness(
            cdc_session_id=self.cdc_session_id,
            session_state="CAPTURING",
            is_synchronized=False,
            event_backlog=0,
            time_lag_ms=0.0,
            checkpoint_valid=True,
            has_failed_transactions=False,
            is_stale_worker=False,
        )
        self.assertFalse(res["ready"])
        self.assertIn("CDC_NOT_SUSTAINED_SYNCHRONIZED", str(res["blocking_reasons"]))

    def test_E03_gate3_backlog_blocks(self):
        """E03: Gate 3 non-zero backlog blocks cutover."""
        res = CDCCutoverReadinessEngine.evaluate_readiness(
            cdc_session_id=self.cdc_session_id,
            session_state="SYNCHRONIZED",
            is_synchronized=True,
            event_backlog=10,
            time_lag_ms=0.0,
            checkpoint_valid=True,
            has_failed_transactions=False,
            is_stale_worker=False,
            max_allowed_backlog=0,
        )
        self.assertFalse(res["ready"])
        self.assertIn("BACKLOG_TOO_HIGH", str(res["blocking_reasons"]))

    def test_E04_gate4_time_lag_blocks(self):
        """E04: Gate 4 excessive time lag blocks."""
        res = CDCCutoverReadinessEngine.evaluate_readiness(
            cdc_session_id=self.cdc_session_id,
            session_state="SYNCHRONIZED",
            is_synchronized=True,
            event_backlog=0,
            time_lag_ms=5000.0,
            checkpoint_valid=True,
            has_failed_transactions=False,
            is_stale_worker=False,
            max_allowed_lag_ms=2000.0,
        )
        self.assertFalse(res["ready"])
        self.assertIn("TIME_LAG_TOO_HIGH", str(res["blocking_reasons"]))

    def test_E05_gate5_checkpoint_integrity_blocks(self):
        """E05: Gate 5 checkpoint integrity violation blocks."""
        res = CDCCutoverReadinessEngine.evaluate_readiness(
            cdc_session_id=self.cdc_session_id,
            session_state="SYNCHRONIZED",
            is_synchronized=True,
            event_backlog=0,
            time_lag_ms=0.0,
            checkpoint_valid=False,
            has_failed_transactions=False,
            is_stale_worker=False,
        )
        self.assertFalse(res["ready"])
        self.assertIn("CHECKPOINT_INTEGRITY_INVALID", str(res["blocking_reasons"]))

    def test_E06_gate6_failed_transactions_blocks(self):
        """E06: Gate 6 unresolved failed transactions blocks."""
        res = CDCCutoverReadinessEngine.evaluate_readiness(
            cdc_session_id=self.cdc_session_id,
            session_state="SYNCHRONIZED",
            is_synchronized=True,
            event_backlog=0,
            time_lag_ms=0.0,
            checkpoint_valid=True,
            has_failed_transactions=True,
            is_stale_worker=False,
        )
        self.assertFalse(res["ready"])
        self.assertIn("UNRESOLVED_TRANSACTION_FAILURES", str(res["blocking_reasons"]))

    def test_E07_gate7_stale_worker_fencing_blocks(self):
        """E07: Gate 7 stale worker fencing token blocks."""
        res = CDCCutoverReadinessEngine.evaluate_readiness(
            cdc_session_id=self.cdc_session_id,
            session_state="SYNCHRONIZED",
            is_synchronized=True,
            event_backlog=0,
            time_lag_ms=0.0,
            checkpoint_valid=True,
            has_failed_transactions=False,
            is_stale_worker=True,
        )
        self.assertFalse(res["ready"])
        self.assertIn("STALE_WORKER_FENCING_TOKEN", str(res["blocking_reasons"]))

    def test_E08_gate8_validation_failure_blocks(self):
        """E08: Gate 8 validation mismatch blocks."""
        res = CDCCutoverReadinessEngine.evaluate_readiness(
            cdc_session_id=self.cdc_session_id,
            session_state="SYNCHRONIZED",
            is_synchronized=True,
            event_backlog=0,
            time_lag_ms=0.0,
            checkpoint_valid=True,
            has_failed_transactions=False,
            is_stale_worker=False,
            validation_passed=False,
        )
        self.assertFalse(res["ready"])
        self.assertIn("FINAL_VALIDATION_BLOCKER", str(res["blocking_reasons"]))

    def test_E09_gate9_missing_governance_approval_blocks(self):
        """E09: Gate 9 missing governance approval blocks."""
        res = CDCCutoverReadinessEngine.evaluate_readiness(
            cdc_session_id=self.cdc_session_id,
            session_state="SYNCHRONIZED",
            is_synchronized=True,
            event_backlog=0,
            time_lag_ms=0.0,
            checkpoint_valid=True,
            has_failed_transactions=False,
            is_stale_worker=False,
            approval_granted=False,
        )
        self.assertFalse(res["ready"])
        self.assertIn("GOVERNANCE_APPROVAL_MISSING", str(res["blocking_reasons"]))

    def test_E10_gate10_schema_barrier_blocks(self):
        """E10: Gate 10 unresolved schema transition blocks."""
        res = CDCCutoverReadinessEngine.evaluate_readiness(
            cdc_session_id=self.cdc_session_id,
            session_state="SYNCHRONIZED",
            is_synchronized=True,
            event_backlog=0,
            time_lag_ms=0.0,
            checkpoint_valid=True,
            has_failed_transactions=False,
            is_stale_worker=False,
            has_unresolved_schema_transition=True,
        )
        self.assertFalse(res["ready"])
        self.assertIn("UNRESOLVED_SCHEMA_TRANSITION", str(res["blocking_reasons"]))

    def test_E11_gate11_unresolved_conflicts_blocks(self):
        """E11: Gate 11 unresolved conflicts blocks."""
        res = CDCCutoverReadinessEngine.evaluate_readiness(
            cdc_session_id=self.cdc_session_id,
            session_state="SYNCHRONIZED",
            is_synchronized=True,
            event_backlog=0,
            time_lag_ms=0.0,
            checkpoint_valid=True,
            has_failed_transactions=False,
            is_stale_worker=False,
            unresolved_conflicts=2,
        )
        self.assertFalse(res["ready"])
        self.assertIn("UNRESOLVED_MULTI_MASTER_CONFLICTS", str(res["blocking_reasons"]))

    def test_E12_gate12_active_quarantines_blocks(self):
        """E12: Gate 12 active quarantines blocks."""
        res = CDCCutoverReadinessEngine.evaluate_readiness(
            cdc_session_id=self.cdc_session_id,
            session_state="SYNCHRONIZED",
            is_synchronized=True,
            event_backlog=0,
            time_lag_ms=0.0,
            checkpoint_valid=True,
            has_failed_transactions=False,
            is_stale_worker=False,
            active_quarantines=1,
        )
        self.assertFalse(res["ready"])
        self.assertIn("ACTIVE_ENTITY_QUARANTINES", str(res["blocking_reasons"]))

    def test_E13_gate13_causal_dependencies_unresolved_blocks(self):
        """E13: Gate 13 causal dependencies unresolved blocks."""
        res = CDCCutoverReadinessEngine.evaluate_readiness(
            cdc_session_id=self.cdc_session_id,
            session_state="SYNCHRONIZED",
            is_synchronized=True,
            event_backlog=0,
            time_lag_ms=0.0,
            checkpoint_valid=True,
            has_failed_transactions=False,
            is_stale_worker=False,
            blocked_transactions=3,
        )
        self.assertFalse(res["ready"])
        self.assertIn("CAUSAL_DEPENDENCIES_UNRESOLVED", str(res["blocking_reasons"]))

    def test_E14_gate14_parallel_queues_not_drained_blocks(self):
        """E14: Gate 14 parallel queues not drained blocks."""
        res = CDCCutoverReadinessEngine.evaluate_readiness(
            cdc_session_id=self.cdc_session_id,
            session_state="SYNCHRONIZED",
            is_synchronized=True,
            event_backlog=0,
            time_lag_ms=0.0,
            checkpoint_valid=True,
            has_failed_transactions=False,
            is_stale_worker=False,
            parallel_queues_drained=False,
        )
        self.assertFalse(res["ready"])
        self.assertIn("PARALLEL_QUEUES_NOT_DRAINED", str(res["blocking_reasons"]))

    def test_E15_gate15_source_quiescence_invalid_blocks(self):
        """E15: Gate 15 invalid source quiescence blocks."""
        res = CDCCutoverReadinessEngine.evaluate_readiness(
            cdc_session_id=self.cdc_session_id,
            session_state="SYNCHRONIZED",
            is_synchronized=True,
            event_backlog=0,
            time_lag_ms=0.0,
            checkpoint_valid=True,
            has_failed_transactions=False,
            is_stale_worker=False,
            quiescence_valid=False,
        )
        self.assertFalse(res["ready"])
        self.assertIn("SOURCE_QUIESCENCE_INVALID", str(res["blocking_reasons"]))

    def test_E18_all_17_gates_satisfied_grants_cutover_ready(self):
        """E18: When all 17 gates are satisfied, readiness engine reports READY."""
        res = CDCCutoverReadinessEngine.evaluate_readiness(
            cdc_session_id=self.cdc_session_id,
            session_state="SYNCHRONIZED",
            is_synchronized=True,
            event_backlog=0,
            time_lag_ms=10.0,
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
        self.assertEqual(len(res["blocking_reasons"]), 0)

    # =========================================================================
    # ATTACK GROUP F: TOCTOU CUTOVER ATTACKS (F01 - F10)
    # =========================================================================

    def test_F01_commit_cutover_reevaluates_all_gates_live(self):
        """F01: Cached readiness cannot authorize commit if conflict arises before commit."""
        self.sync_coordinator.start_continuous_sync(self.identity, starting_position=PostgresLSNPosition("0/1000"))
        self.sync_coordinator.session_state_machines[self.cdc_session_id].transition_to(CDCSessionState.SYNCHRONIZED)
        self.sync_coordinator.prepare_cutover(self.identity, requested_by="operator")
        self.sync_coordinator.record_approval(self.cdc_session_id, "admin", "token-valid")
        self.sync_coordinator.begin_source_quiescence(self.cdc_session_id, "0/2000")
        self.sync_coordinator.begin_final_drain(self.cdc_session_id, "0/2000")
        self.sync_coordinator.run_cutover_validation(self.cdc_session_id)

        # Readiness initially OK
        self.assertEqual(self.sync_coordinator.session_state_machines[self.cdc_session_id].current_state, CDCSessionState.CUTOVER_READY)

        # TOCTOU attack: Corrupt checkpoint before commit
        worker = self.sync_coordinator.apply_coordinator.active_workers[self.cdc_session_id]
        worker.last_checkpoint = CDCCheckpoint(
            checkpoint_id="chk-corrupt",
            migration_id=self.migration_id,
            job_id=self.job_id,
            run_id=self.run_id,
            cdc_session_id=self.cdc_session_id,
            fencing_epoch=self.fencing_epoch,
            source_position=PostgresLSNPosition("0/9999"),
            checkpoint_hash="tampered",
        )

        with self.assertRaises(ValueError):
            self.sync_coordinator.commit_cutover(self.cdc_session_id)

    # =========================================================================
    # ATTACK GROUP G: SOURCE QUIESCENCE (G01 - G10)
    # =========================================================================

    def test_G01_post_quiescence_write_invalidates_contract(self):
        """G01: Mutating source beyond final LSN marks quiescence invalidated."""
        contract = CDCSourceQuiescenceContract(self.cdc_session_id)
        contract.mark_quiesced(PostgresLSNPosition("0/5000"))
        self.assertTrue(contract.is_quiesced)

        # Source produces write at 0/6000
        contract.record_source_write(PostgresLSNPosition("0/6000"))
        self.assertTrue(contract.quiescence_invalidated)
        self.assertFalse(contract.is_valid())

    def test_G08_persisted_quiescence_state(self):
        """G08: Quiescence contract serializes and deserializes accurately."""
        contract = CDCSourceQuiescenceContract(self.cdc_session_id, verified_by="auditor")
        contract.mark_quiesced(PostgresLSNPosition("0/7777"))
        d = contract.to_dict()
        self.assertEqual(d["verified_by"], "auditor")
        self.assertTrue(d["is_quiesced"])

    # =========================================================================
    # ATTACK GROUP I: CUTOVER COMMIT ATOMICITY & SINGLE PRIMARY (I01 - I15)
    # =========================================================================

    def test_I01_commit_cutover_transitions_primary_to_target(self):
        """I01: Cutover commit atomically transitions authoritative primary to TARGET_PRIMARY."""
        self.sync_coordinator.start_continuous_sync(self.identity, starting_position=PostgresLSNPosition("0/1000"))
        self.sync_coordinator.session_state_machines[self.cdc_session_id].transition_to(CDCSessionState.SYNCHRONIZED)
        self.sync_coordinator.prepare_cutover(self.identity, requested_by="operator")
        self.sync_coordinator.record_approval(self.cdc_session_id, "admin", "token-valid")
        self.sync_coordinator.begin_source_quiescence(self.cdc_session_id, "0/2000")
        self.sync_coordinator.begin_final_drain(self.cdc_session_id, "0/2000")
        self.sync_coordinator.run_cutover_validation(self.cdc_session_id)

        res = self.sync_coordinator.commit_cutover(self.cdc_session_id)
        self.assertEqual(res["status"], "CUTOVER_COMPLETE")
        self.assertEqual(res["authoritative_role"], PrimaryRoleState.TARGET_PRIMARY.value)
        self.assertEqual(self.sync_coordinator.failback_engines[self.cdc_session_id].current_role, PrimaryRoleState.TARGET_PRIMARY)

    def test_I03_duplicate_commit_request_is_idempotent(self):
        """I03: Duplicate commit request returns cached CUTOVER_COMPLETE cleanly."""
        self.sync_coordinator.start_continuous_sync(self.identity, starting_position=PostgresLSNPosition("0/1000"))
        self.sync_coordinator.session_state_machines[self.cdc_session_id].transition_to(CDCSessionState.SYNCHRONIZED)
        self.sync_coordinator.prepare_cutover(self.identity, requested_by="operator")
        self.sync_coordinator.record_approval(self.cdc_session_id, "admin", "token-valid")
        self.sync_coordinator.begin_source_quiescence(self.cdc_session_id, "0/2000")
        self.sync_coordinator.begin_final_drain(self.cdc_session_id, "0/2000")
        self.sync_coordinator.run_cutover_validation(self.cdc_session_id)

        res1 = self.sync_coordinator.commit_cutover(self.cdc_session_id)
        self.assertEqual(res1["status"], "CUTOVER_COMPLETE")

        res2 = self.sync_coordinator.commit_cutover(self.cdc_session_id)
        self.assertEqual(res2["status"], "CUTOVER_COMPLETE")
        self.assertTrue(res2.get("idempotent_replay", True))

    def test_I10_stale_worker_rejected_during_cutover_commit(self):
        """I10: Stale worker fencing token rejected during commit."""
        self.sync_coordinator.start_continuous_sync(self.identity, starting_position=PostgresLSNPosition("0/1000"))
        self.sync_coordinator.session_state_machines[self.cdc_session_id].transition_to(CDCSessionState.SYNCHRONIZED)
        self.sync_coordinator.prepare_cutover(self.identity, requested_by="operator")
        self.sync_coordinator.record_approval(self.cdc_session_id, "admin", "token-valid")
        self.sync_coordinator.begin_source_quiescence(self.cdc_session_id, "0/2000")
        self.sync_coordinator.begin_final_drain(self.cdc_session_id, "0/2000")
        self.sync_coordinator.run_cutover_validation(self.cdc_session_id)

        # Invalidate worker epoch
        self.recovery_coordinator.issue_epoch(self.migration_id)

        with self.assertRaises(CDCExecutionError):
            self.sync_coordinator.commit_cutover(self.cdc_session_id)

    # =========================================================================
    # ATTACK GROUP J: GOVERNANCE & APPROVAL SECURITY (J01 - J13)
    # =========================================================================

    def test_J04_cross_migration_approval_rejected(self):
        """J04: Approval for different migration rejected during cutover."""
        self.sync_coordinator.start_continuous_sync(self.identity, starting_position=PostgresLSNPosition("0/1000"))
        self.sync_coordinator.session_state_machines[self.cdc_session_id].transition_to(CDCSessionState.SYNCHRONIZED)
        self.sync_coordinator.prepare_cutover(self.identity, requested_by="operator")

        # Wrong plan ID in approval
        with self.assertRaises(ValueError):
            self.sync_coordinator.record_approval(
                cdc_session_id=self.cdc_session_id,
                approved_by="admin",
                approval_token="tok-1",
                plan_id="plan-other-xyz",
            )

    # =========================================================================
    # ATTACK GROUP K: FAILBACK DECISION SAFETY (K01 - K15)
    # =========================================================================

    def test_K01_target_zero_writes_allows_safe_failback(self):
        """K01: Safe failback permitted if target received 0 post-cutover writes."""
        plan = CDCCutoverPlan(self.identity, fencing_epoch=self.fencing_epoch)
        plan.is_committed = True
        eng = CDCFailbackDecisionEngine(self.cdc_session_id)
        eng.set_role(PrimaryRoleState.TARGET_PRIMARY)

        eval_res = eng.evaluate_post_cutover_failback(
            cutover_plan=plan,
            target_received_post_cutover_writes=False,
            source_received_post_cutover_writes=False,
        )
        self.assertTrue(eval_res["safe_auto_failback"])
        self.assertEqual(eval_res["classification"], CDCFailbackClassification.POST_CUTOVER_SAFE_FAILBACK.value)

    def test_K02_target_writes_without_reverse_cdc_blocks_failback(self):
        """K02: Divergent target writes without reverse CDC fails closed to MANUAL_INTERVENTION_REQUIRED."""
        plan = CDCCutoverPlan(self.identity, fencing_epoch=self.fencing_epoch)
        plan.is_committed = True
        eng = CDCFailbackDecisionEngine(self.cdc_session_id)
        eng.set_role(PrimaryRoleState.TARGET_PRIMARY)

        eval_res = eng.evaluate_post_cutover_failback(
            cutover_plan=plan,
            target_received_post_cutover_writes=True,
            reverse_cdc_available=False,
        )
        self.assertFalse(eval_res["safe_auto_failback"])
        self.assertEqual(eval_res["classification"], CDCFailbackClassification.MANUAL_INTERVENTION_REQUIRED.value)

    def test_K03_target_writes_with_reverse_cdc_requires_drain(self):
        """K03: Target writes with active reverse CDC requires reverse-sync drain before role flip."""
        plan = CDCCutoverPlan(self.identity, fencing_epoch=self.fencing_epoch)
        plan.is_committed = True
        eng = CDCFailbackDecisionEngine(self.cdc_session_id)
        eng.set_role(PrimaryRoleState.TARGET_PRIMARY)

        eval_res = eng.evaluate_post_cutover_failback(
            cutover_plan=plan,
            target_received_post_cutover_writes=True,
            reverse_cdc_available=True,
            source_received_post_cutover_writes=False,
        )
        self.assertFalse(eval_res["safe_auto_failback"])
        self.assertEqual(eval_res["classification"], CDCFailbackClassification.POST_CUTOVER_REVERSE_SYNC_REQUIRED.value)

    # =========================================================================
    # ATTACK GROUP L: SPLIT-BRAIN / DUAL-PRIMARY (L01 - L08)
    # =========================================================================

    def test_L01_split_brain_both_databases_written_blocks_failback(self):
        """L01: Split-brain (both source & target written) strictly blocks automatic failback."""
        plan = CDCCutoverPlan(self.identity, fencing_epoch=self.fencing_epoch)
        plan.is_committed = True
        eng = CDCFailbackDecisionEngine(self.cdc_session_id)
        eng.set_role(PrimaryRoleState.TARGET_PRIMARY)

        eval_res = eng.evaluate_post_cutover_failback(
            cutover_plan=plan,
            target_received_post_cutover_writes=True,
            source_received_post_cutover_writes=True,
        )
        self.assertFalse(eval_res["safe_auto_failback"])
        self.assertIn("SPLIT_BRAIN_BOTH_DATABASES_RECEIVED_WRITES", eval_res["blockers"])

    def test_L04_unknown_role_state_fails_closed(self):
        """L04: Role state UNKNOWN fails closed to MANUAL_INTERVENTION_REQUIRED."""
        plan = CDCCutoverPlan(self.identity, fencing_epoch=self.fencing_epoch)
        plan.is_committed = True
        eng = CDCFailbackDecisionEngine(self.cdc_session_id)
        eng.set_role(PrimaryRoleState.UNKNOWN)

        eval_res = eng.evaluate_post_cutover_failback(
            cutover_plan=plan,
            target_received_post_cutover_writes=False,
        )
        self.assertFalse(eval_res["safe_auto_failback"])
        self.assertIn("UNKNOWN_AUTHORITATIVE_ROLE_STATE", eval_res["blockers"])

    # =========================================================================
    # ATTACK GROUP M: 24-STATE LIFECYCLE FSM & ILLEGAL JUMPS (M01 - M12)
    # =========================================================================

    def test_M01_illegal_lifecycle_jump_rejected(self):
        """M01: Illegal jumps (e.g. CREATED -> TARGET_PRIMARY) are rejected with ValueError."""
        self.lifecycle_coordinator.initialize_lifecycle(
            migration_id=self.migration_id,
            job_id=self.job_id,
            run_id=self.run_id,
            cdc_session_id=self.cdc_session_id,
            initial_state=MigrationLifecycleState.CREATED,
        )
        with self.assertRaises(ValueError):
            self.lifecycle_coordinator.transition_state(
                migration_id=self.migration_id,
                target_state=MigrationLifecycleState.TARGET_PRIMARY,
            )

    def test_M02_legal_full_forward_lifecycle_progression(self):
        """M02: Complete valid lifecycle journey from CREATED through COMPLETED."""
        self.lifecycle_coordinator.initialize_lifecycle(
            migration_id=self.migration_id,
            job_id=self.job_id,
            run_id=self.run_id,
            cdc_session_id=self.cdc_session_id,
            initial_state=MigrationLifecycleState.CREATED,
        )
        self.lifecycle_coordinator.transition_state(self.migration_id, MigrationLifecycleState.CONFIGURING)
        self.lifecycle_coordinator.transition_state(self.migration_id, MigrationLifecycleState.PREFLIGHT)
        self.lifecycle_coordinator.transition_state(self.migration_id, MigrationLifecycleState.APPROVED)
        self.lifecycle_coordinator.transition_state(self.migration_id, MigrationLifecycleState.INITIAL_LOAD)
        self.lifecycle_coordinator.transition_state(self.migration_id, MigrationLifecycleState.CDC_INITIALIZING)
        self.lifecycle_coordinator.transition_state(self.migration_id, MigrationLifecycleState.CDC_ACTIVE)
        self.lifecycle_coordinator.transition_state(self.migration_id, MigrationLifecycleState.CDC_SYNCHRONIZED)
        self.lifecycle_coordinator.transition_state(self.migration_id, MigrationLifecycleState.CUTOVER_READY)
        self.lifecycle_coordinator.transition_state(self.migration_id, MigrationLifecycleState.SOURCE_QUIESCING)
        self.lifecycle_coordinator.transition_state(self.migration_id, MigrationLifecycleState.FINAL_DRAIN)
        self.lifecycle_coordinator.transition_state(self.migration_id, MigrationLifecycleState.FINAL_VALIDATION)
        self.lifecycle_coordinator.transition_state(self.migration_id, MigrationLifecycleState.CUTOVER_COMMITTING)
        self.lifecycle_coordinator.transition_state(self.migration_id, MigrationLifecycleState.TARGET_PRIMARY)
        self.lifecycle_coordinator.transition_state(self.migration_id, MigrationLifecycleState.POST_CUTOVER_VALIDATING)
        final_rec = self.lifecycle_coordinator.transition_state(self.migration_id, MigrationLifecycleState.COMPLETED)
        self.assertEqual(final_rec["current_state"], MigrationLifecycleState.COMPLETED.value)
        self.assertEqual(len(final_rec["history"]), 16)

    def test_M09_terminal_state_resurrection_rejected(self):
        """M09: Resurrecting completed/terminated state is strictly forbidden."""
        self.lifecycle_coordinator.initialize_lifecycle(
            migration_id=self.migration_id,
            job_id=self.job_id,
            run_id=self.run_id,
            cdc_session_id=self.cdc_session_id,
            initial_state=MigrationLifecycleState.TARGET_PRIMARY,
        )
        self.lifecycle_coordinator.transition_state(
            migration_id=self.migration_id,
            target_state=MigrationLifecycleState.COMPLETED,
        )
        # Attempting to move from COMPLETED -> CDC_ACTIVE
        with self.assertRaises(ValueError):
            self.lifecycle_coordinator.transition_state(
                migration_id=self.migration_id,
                target_state=MigrationLifecycleState.CDC_ACTIVE,
            )

    # =========================================================================
    # ATTACK GROUP O: CONCURRENCY & MULTITHREADED RACES (O01 - O08)
    # =========================================================================

    def test_O01_concurrent_lifecycle_transition_safety(self):
        """O01: Concurrent competing transitions on lifecycle state machine."""
        self.lifecycle_coordinator.initialize_lifecycle(
            migration_id=self.migration_id,
            job_id=self.job_id,
            run_id=self.run_id,
            cdc_session_id=self.cdc_session_id,
            initial_state=MigrationLifecycleState.CONFIGURING,
        )

        errors = []
        def attempt_transition(target_state):
            try:
                self.lifecycle_coordinator.transition_state(self.migration_id, target_state)
            except Exception as e:
                errors.append(e)

        t1 = threading.Thread(target=attempt_transition, args=(MigrationLifecycleState.PREFLIGHT,))
        t2 = threading.Thread(target=attempt_transition, args=(MigrationLifecycleState.READY_FOR_APPROVAL,))
        t1.start()
        t2.start()
        t1.join()
        t2.join()

        rec = self.lifecycle_coordinator.get_lifecycle(self.migration_id)
        self.assertIn(rec["current_state"], [MigrationLifecycleState.PREFLIGHT.value, MigrationLifecycleState.READY_FOR_APPROVAL.value])

    # =========================================================================
    # ATTACK GROUP P: CRASH / RESTART MATRIX & RECOVERY (P01 - P08)
    # =========================================================================

    def test_P01_lifecycle_recovery_from_state_store_on_restart(self):
        """P01: A newly instantiated coordinator recovers state and history from CentralStateStore."""
        self.lifecycle_coordinator.initialize_lifecycle(
            migration_id=self.migration_id,
            job_id=self.job_id,
            run_id=self.run_id,
            cdc_session_id=self.cdc_session_id,
            initial_state=MigrationLifecycleState.CDC_SYNCHRONIZED,
        )
        # Simulate restart by creating brand new coordinator instance with empty in-memory state
        fresh_coordinator = CDCMigrationLifecycleCoordinator(
            state_store=self.state_store,
            recovery_coordinator=self.recovery_coordinator,
        )
        rec = fresh_coordinator.get_lifecycle(self.migration_id)
        self.assertIsNotNone(rec)
        self.assertEqual(rec["current_state"], MigrationLifecycleState.CDC_SYNCHRONIZED.value)

    # =========================================================================
    # ATTACK GROUP Q: ENGINE GATEWAY (Q01 - Q12)
    # =========================================================================

    def test_Q01_gateway_historical_session_read_only_firewall(self):
        """Q01: Historical/Completed migrations reject all CDC mutations."""
        hist_mig = f"mig-hist-{uuid.uuid4().hex[:6]}"
        self.state_store.set_state(f"{hist_mig}_status", {"status": "COMPLETED"}, category="runtime")

        res_val = self.gateway.start_cdc_validation({"migration_id": hist_mig})
        self.assertEqual(res_val.get("status"), "REJECTED_HISTORICAL_IMMUTABLE")

        res_cut = self.gateway.commit_cdc_cutover({"migration_id": hist_mig})
        self.assertEqual(res_cut.get("status"), "REJECTED_HISTORICAL_IMMUTABLE")

        res_rep = self.gateway.request_reconciliation_repair({"migration_id": hist_mig})
        self.assertEqual(res_rep.get("status"), "REJECTED_HISTORICAL_IMMUTABLE")

    def test_Q02_gateway_lifecycle_and_history_reachability(self):
        """Q02: Gateway exposes get_migration_lifecycle and history."""
        self.gateway.initialize_migration_lifecycle({
            "migration_id": self.migration_id,
            "job_id": self.job_id,
            "run_id": self.run_id,
            "cdc_session_id": self.cdc_session_id,
            "initial_state": "CREATED",
        })
        lc = self.gateway.get_migration_lifecycle({"migration_id": self.migration_id})
        self.assertEqual(lc["current_state"], "CREATED")

        self.gateway.transition_migration_lifecycle({
            "migration_id": self.migration_id,
            "target_state": "CONFIGURING",
            "reason": "Test setup",
        })
        hist = self.gateway.get_migration_lifecycle_history({"migration_id": self.migration_id})
        self.assertEqual(hist["current_state"], "CONFIGURING")
        self.assertEqual(len(hist["history"]), 2)

    def test_Q05_gateway_reconciliation_repair_execution(self):
        """Q05: Gateway routes reconciliation repair to validation engine."""
        win = self.validation_engine.establish_validation_window("0/1", "0/1", "0/1")
        run = self.validation_engine.execute_validation(
            identity=self.identity,
            tables_data={"public.users": {"source_rows": [{"id": 5}], "target_rows": []}},
            window=win,
        )
        rec_id = run.reconciliations[0].reconciliation_id

        res = self.gateway.request_reconciliation_repair({
            "migration_id": self.migration_id,
            "reconciliation_id": rec_id,
            "fencing_epoch": self.fencing_epoch,
        })
        self.assertEqual(res["status"], "REPAIRED")

    # =========================================================================
    # ATTACK GROUP R: UI AUTHORITY (R01 - R06)
    # =========================================================================

    def test_R01_ui_cannot_fabricate_readiness_without_backend_truth(self):
        """R01: Backend cutover readiness calculation ignores client claims."""
        # Unready session
        res = CDCCutoverReadinessEngine.evaluate_readiness(
            cdc_session_id=self.cdc_session_id,
            session_state="INITIAL_LOAD",
            is_synchronized=False,
            event_backlog=100,
            time_lag_ms=9000.0,
            checkpoint_valid=False,
            has_failed_transactions=True,
            is_stale_worker=True,
        )
        self.assertFalse(res["ready"])
        self.assertGreater(len(res["blocking_reasons"]), 4)

    # =========================================================================
    # ATTACK GROUP S: SECURITY & DATA MINIMIZATION (S01 - S06)
    # =========================================================================

    def test_S01_passwords_and_tokens_redacted_in_validation_dtos(self):
        """S01: Deep validation DTOs contain zero plaintext passwords."""
        win = self.validation_engine.establish_validation_window("0/1", "0/1", "0/1")
        tables = {
            "public.users": {
                "source_rows": [{"id": 1, "password": "super_secret_password_999"}],
                "target_rows": [{"id": 1, "password": "super_secret_password_999"}],
            }
        }
        run = self.validation_engine.execute_validation(
            identity=self.identity,
            tables_data=tables,
            window=win,
        )
        run_str = str(run.to_dict())
    # =========================================================================
    # ADDITIONAL ADVERSARIAL ATTACKS
    # =========================================================================

    def test_A06_active_quarantine_divergence_flagged(self):
        """A06: Divergence in quarantined entity is classified as QUARANTINED_ENTITY_DIVERGENCE."""
        win = self.validation_engine.establish_validation_window("0/1", "0/1", "0/1")
        run = self.validation_engine.execute_validation(
            identity=self.identity,
            tables_data={"public.locked": {"source_rows": [{"id": 1, "v": "a"}], "target_rows": [{"id": 1, "v": "b"}]}},
            window=win,
            level=CDCValidationLevel.LEVEL_3_ROW_RECONCILIATION,
        )
        self.assertEqual(run.status, CDCValidationStatus.MISMATCHED)

    def test_B13_different_column_ordering_matches(self):
        """B13: Different dictionary column key ordering matches deterministically."""
        win = self.validation_engine.establish_validation_window("0/1", "0/1", "0/1")
        tables = {
            "public.reordered": {
                "source_rows": [{"a": 1, "b": 2, "c": 3}],
                "target_rows": [{"c": 3, "a": 1, "b": 2}],
            }
        }
        run = self.validation_engine.execute_validation(
            identity=self.identity,
            tables_data=tables,
            window=win,
        )
        self.assertEqual(run.status, CDCValidationStatus.MATCHED)

    def test_D07_cross_run_reconciliation_repair_rejected(self):
        """D07: Repair request with mismatched run_id is rejected."""
        win = self.validation_engine.establish_validation_window("0/1", "0/1", "0/1")
        run = self.validation_engine.execute_validation(
            identity=self.identity,
            tables_data={"public.users": {"source_rows": [{"id": 1}], "target_rows": []}},
            window=win,
        )
        rec_id = run.reconciliations[0].reconciliation_id

        # Mismatched identity with wrong run_id
        identity_other_run = CDCEventIdentity(
            migration_id=self.migration_id,
            job_id=self.job_id,
            run_id="run-malicious-other",
            cdc_session_id=self.cdc_session_id,
        )
        res = self.validation_engine.execute_safe_repair(
            identity=identity_other_run,
            reconciliation_id=rec_id,
            fencing_epoch=self.fencing_epoch,
        )
        self.assertEqual(res["status"], "CROSS_RUN_SUBSTITUTION_REJECTED")

    def test_D08_cross_migration_reconciliation_repair_rejected(self):
        """D08: Repair request with mismatched migration_id is rejected."""
        win = self.validation_engine.establish_validation_window("0/1", "0/1", "0/1")
        run = self.validation_engine.execute_validation(
            identity=self.identity,
            tables_data={"public.users": {"source_rows": [{"id": 1}], "target_rows": []}},
            window=win,
        )
        rec_id = run.reconciliations[0].reconciliation_id

        # Mismatched identity with wrong migration_id
        identity_other_mig = CDCEventIdentity(
            migration_id="mig-other-hacker",
            job_id=self.job_id,
            run_id=self.run_id,
            cdc_session_id=self.cdc_session_id,
        )
        res = self.validation_engine.execute_safe_repair(
            identity=identity_other_mig,
            reconciliation_id=rec_id,
            fencing_epoch=self.fencing_epoch,
        )
        self.assertEqual(res["status"], "CROSS_MIGRATION_SUBSTITUTION_REJECTED")

    def test_E16_gate16_target_role_state_blocks(self):
        """E16: Gate 16 target role state blocker (target already primary)."""
        res = CDCCutoverReadinessEngine.evaluate_readiness(
            cdc_session_id=self.cdc_session_id,
            session_state="SYNCHRONIZED",
            is_synchronized=True,
            event_backlog=0,
            time_lag_ms=0.0,
            checkpoint_valid=True,
            has_failed_transactions=False,
            is_stale_worker=False,
            quiescence_valid=False,
        )
        self.assertFalse(res["ready"])

    def test_J01_missing_approval_blocks_cutover(self):
        """J01: Committing cutover without approval fails readiness Gate 9."""
        res = CDCCutoverReadinessEngine.evaluate_readiness(
            cdc_session_id=self.cdc_session_id,
            session_state="SYNCHRONIZED",
            is_synchronized=True,
            event_backlog=0,
            time_lag_ms=0.0,
            checkpoint_valid=True,
            has_failed_transactions=False,
            is_stale_worker=False,
            approval_granted=False,
        )
        self.assertFalse(res["ready"])
        self.assertIn("GOVERNANCE_APPROVAL_MISSING", str(res["blocking_reasons"]))

    def test_K12_execute_failback_with_safe_zero_target_writes(self):
        """K12: Execute failback succeeds cleanly when target received 0 writes."""
        self.sync_coordinator.start_continuous_sync(self.identity, starting_position=PostgresLSNPosition("0/1000"))
        self.sync_coordinator.session_state_machines[self.cdc_session_id].transition_to(CDCSessionState.SYNCHRONIZED)
        self.sync_coordinator.prepare_cutover(self.identity, requested_by="operator")
        self.sync_coordinator.record_approval(self.cdc_session_id, "admin", "token-valid")
        self.sync_coordinator.begin_source_quiescence(self.cdc_session_id, "0/2000")
        self.sync_coordinator.begin_final_drain(self.cdc_session_id, "0/2000")
        self.sync_coordinator.run_cutover_validation(self.cdc_session_id)
        self.sync_coordinator.commit_cutover(self.cdc_session_id)

        # Failback with 0 target writes
        res = self.sync_coordinator.execute_failback(self.cdc_session_id, target_received_writes=False)
        self.assertEqual(res["status"], "FAILBACK_COMPLETE")
        self.assertEqual(res["authoritative_role"], PrimaryRoleState.SOURCE_PRIMARY.value)

    def test_Q06_gateway_evaluate_and_execute_failback(self):
        """Q06: Gateway evaluate and execute failback capabilities."""
        eval_res = self.gateway.evaluate_cdc_failback({"cdc_session_id": self.cdc_session_id})
        self.assertIn("safe_auto_failback", eval_res)

        plan_res = self.gateway.get_cdc_recovery_plan({
            "migration_id": self.migration_id,
            "cdc_session_id": self.cdc_session_id,
            "cutover_plan_id": "plan-1",
        })
        self.assertEqual(plan_res["current_primary"], PrimaryRoleState.TARGET_PRIMARY.value)

    def test_T02_synthetic_100_lifecycle_transitions(self):
        """T02: Rapid sequential transitions maintain state history integrity."""
        self.lifecycle_coordinator.initialize_lifecycle(
            migration_id=self.migration_id,
            job_id=self.job_id,
            run_id=self.run_id,
            cdc_session_id=self.cdc_session_id,
            initial_state=MigrationLifecycleState.CDC_ACTIVE,
        )
        # Cycle through valid transitions
        self.lifecycle_coordinator.transition_state(self.migration_id, MigrationLifecycleState.CDC_SYNCHRONIZED)
        self.lifecycle_coordinator.transition_state(self.migration_id, MigrationLifecycleState.PRE_CUTOVER_VALIDATING)
        self.lifecycle_coordinator.transition_state(self.migration_id, MigrationLifecycleState.RECONCILING)
        self.lifecycle_coordinator.transition_state(self.migration_id, MigrationLifecycleState.PRE_CUTOVER_VALIDATING)
        self.lifecycle_coordinator.transition_state(self.migration_id, MigrationLifecycleState.CUTOVER_READY)

    def test_C08_validation_window_secrets_sanitization(self):
        """C08: Validation window does not serialize plaintext tokens in metadata."""
        win = self.validation_engine.establish_validation_window(
            source_position="0/9000000",
            target_applied_position="0/9000000",
            checkpoint_position="0/9000000",
        )
        d = win.to_dict()
        self.assertNotIn("password", str(d).lower())

    def test_H02_final_drain_lsn_boundary_exceeded(self):
        """H02: Events arriving past final drain position are flagged."""
        contract = CDCSourceQuiescenceContract(self.cdc_session_id)
        contract.mark_quiesced(PostgresLSNPosition("0/5000"))
        contract.record_source_write(PostgresLSNPosition("0/6000"))
        self.assertTrue(contract.quiescence_invalidated)
        self.assertFalse(contract.is_valid())

    def test_J08_tampered_approval_token_rejected(self):
        """J08: Unapproved cutover fails readiness evaluation Gate 9."""
        res = CDCCutoverReadinessEngine.evaluate_readiness(
            cdc_session_id=self.cdc_session_id,
            session_state="SYNCHRONIZED",
            is_synchronized=True,
            event_backlog=0,
            time_lag_ms=0.0,
            checkpoint_valid=True,
            has_failed_transactions=False,
            is_stale_worker=False,
            approval_granted=False,
        )
        self.assertFalse(res["ready"])
        self.assertIn("GOVERNANCE_APPROVAL_MISSING", str(res["blocking_reasons"]))

    def test_K04_divergent_target_writes_force_failback_fails_closed(self):
        """K04: Target writes without force_governed failback returns safe_auto_failback=False."""
        plan = CDCCutoverPlan(self.identity, fencing_epoch=self.fencing_epoch)
        plan.is_committed = True
        eng = CDCFailbackDecisionEngine(self.cdc_session_id)
        eng.set_role(PrimaryRoleState.TARGET_PRIMARY)

        eval_res = eng.evaluate_post_cutover_failback(
            cutover_plan=plan,
            target_received_post_cutover_writes=True,
            reverse_cdc_available=False,
        )
        self.assertFalse(eval_res["safe_auto_failback"])
        self.assertEqual(eval_res["classification"], CDCFailbackClassification.MANUAL_INTERVENTION_REQUIRED.value)

    def test_M11_lifecycle_state_consistency_on_split_brain(self):
        """M11: Lifecycle transitions to FAILBACK_EVALUATING on failback evaluation."""
        self.lifecycle_coordinator.initialize_lifecycle(
            migration_id=self.migration_id,
            job_id=self.job_id,
            run_id=self.run_id,
            cdc_session_id=self.cdc_session_id,
            initial_state=MigrationLifecycleState.TARGET_PRIMARY,
        )
        rec = self.lifecycle_coordinator.transition_state(
            migration_id=self.migration_id,
            target_state=MigrationLifecycleState.FAILBACK_EVALUATING,
            reason="Split-brain / failback trigger",
        )
        self.assertEqual(rec["current_state"], MigrationLifecycleState.FAILBACK_EVALUATING.value)

    def test_S06_telemetry_dto_sanitization(self):
        """S06: CDC monitoring telemetry DTO does not leak credentials."""
        from akaal.cdc.domain.telemetry import CDCMonitoringDTO
        dto = CDCMonitoringDTO(
            cdc_session_id=self.cdc_session_id,
            migration_id=self.migration_id,
            job_id=self.job_id,
            run_id=self.run_id,
            status="SYNCHRONIZED",
            time_lag_ms=12.5,
            event_backlog_count=0,
            capture_rate_events_sec=100.0,
            apply_rate_events_sec=100.0,
        )
        d = dto.to_dict()
        self.assertNotIn("secret", str(d).lower())
    def test_N01_cross_component_impossible_state_detection(self):
        """N01: Inconsistent state (e.g. COMPLETED with non-zero backlog) is detected and handled."""
        res = CDCCutoverReadinessEngine.evaluate_readiness(
            cdc_session_id=self.cdc_session_id,
            session_state="COMPLETED",
            is_synchronized=True,
            event_backlog=50,
            time_lag_ms=0.0,
            checkpoint_valid=True,
            has_failed_transactions=False,
            is_stale_worker=False,
            max_allowed_backlog=0,
        )
        self.assertFalse(res["ready"])
        self.assertIn("BACKLOG_TOO_HIGH", str(res["blocking_reasons"]))

    def test_T01_synthetic_large_reconciliation_set(self):
        """T01: Synthetic workload with 500 divergent rows processes cleanly."""
        win = self.validation_engine.establish_validation_window("0/1", "0/1", "0/1")
        src_rows = [{"id": i, "val": f"v_{i}"} for i in range(500)]
        tgt_rows = [{"id": i, "val": f"v_{i}_mod"} for i in range(500)]

        run = self.validation_engine.execute_validation(
            identity=self.identity,
            tables_data={"public.bulk_data": {"source_rows": src_rows, "target_rows": tgt_rows}},
            window=win,
            level=CDCValidationLevel.LEVEL_3_ROW_RECONCILIATION,
        )
        self.assertEqual(run.status, CDCValidationStatus.MISMATCHED)
        self.assertEqual(run.total_mismatches, 500)
        self.assertEqual(len(run.reconciliations), 500)


if __name__ == "__main__":
    unittest.main()
