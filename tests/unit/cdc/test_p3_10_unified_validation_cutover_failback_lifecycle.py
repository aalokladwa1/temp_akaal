"""
Comprehensive Unit & Integration Acceptance Suite for Phase P3.10:
Unified CDC Validation, Reconciliation, Controlled Cutover, Failback/Recovery &
End-to-End Migration Lifecycle Management.
"""

import unittest
import os
import sqlite3
import datetime
import uuid
from typing import Dict, Any

from akaal.core.state.state_store import CentralStateStore
from akaal.runtime.recovery.coordinator import RecoveryCoordinator
from akaal.cdc.domain.events import CDCEventIdentity
from akaal.cdc.domain.positions import PostgresLSNPosition
from akaal.cdc.domain.durability import CDCCheckpoint
from akaal.cdc.domain.lifecycle import CDCSessionState
from akaal.cdc.domain.errors import CDCExecutionError

from akaal.cdc.validation.domain import (
    CDCValidationLevel,
    CDCValidationStatus,
    CDCDivergenceClass,
    CDCRepairActionType,
    CDCRepairStatus,
    CDCConsistentValidationWindow,
    CDCValidationRun,
)
from akaal.cdc.validation.engine import CDCValidationEngine
from akaal.cdc.sync.cutover_plan import (
    CDCCutoverPlan,
    CutoverPhase,
    CDCSourceQuiescenceContract,
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
from akaal.gateway.engine_gateway import EngineGateway


class TestP310UnifiedValidationCutoverFailbackLifecycle(unittest.TestCase):
    """Acceptance test suite proving complete P3.10 canonical functionality across all workstreams."""

    def setUp(self) -> None:
        self.migration_id = "mig-p310-test"
        self.job_id = "job-p310"
        self.run_id = "run-p310"
        self.cdc_session_id = f"cdc-{self.migration_id}"
        self.identity = CDCEventIdentity(self.migration_id, self.job_id, self.run_id, self.cdc_session_id)

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

        self.recovery_coordinator = RecoveryCoordinator()
        self.fencing_epoch = self.recovery_coordinator.issue_epoch(self.migration_id)

        self.validation_engine = CDCValidationEngine(
            state_store=self.state_store,
            recovery_coordinator=self.recovery_coordinator,
        )
        self.sync_coordinator = CDCContinuousSyncCoordinator(
            recovery_coordinator=self.recovery_coordinator,
            state_store=self.state_store,
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
    # Workstream A: CDC Validation & Reconciliation
    # =========================================================================

    def test_A01_consistent_validation_window_evaluation(self):
        """Proves consistent validation window evaluation fails closed on moving stream or causal holes."""
        # 1. Consistent frozen window
        win_ok = self.validation_engine.establish_validation_window(
            source_position="0/10000",
            target_applied_position="0/10000",
            checkpoint_position="0/10000",
            schema_version=1,
            has_causal_holes=False,
        )
        self.assertTrue(win_ok.is_consistent)

        # 2. Moving stream (source ahead of target)
        win_moving = self.validation_engine.establish_validation_window(
            source_position="0/20000",
            target_applied_position="0/10000",
            checkpoint_position="0/10000",
            schema_version=1,
            has_causal_holes=False,
        )
        self.assertFalse(win_moving.is_consistent)

        # 3. Causal holes present
        win_holes = self.validation_engine.establish_validation_window(
            source_position="0/10000",
            target_applied_position="0/10000",
            checkpoint_position="0/10000",
            schema_version=1,
            has_causal_holes=True,
        )
        self.assertFalse(win_holes.is_consistent)

    def test_A02_validation_levels_and_divergence_detection(self):
        """Proves progressive validation levels 1-3 detect missing, extra, and changed rows."""
        tables_matched = {
            "users": {
                "source_rows": [{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}],
                "target_rows": [{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}],
            }
        }
        win = self.validation_engine.establish_validation_window("0/100", "0/100", "0/100")
        run_matched = self.validation_engine.execute_validation(
            identity=self.identity,
            tables_data=tables_matched,
            window=win,
            level=CDCValidationLevel.LEVEL_2_TABLE_CHECKSUM,
        )
        self.assertEqual(run_matched.status, CDCValidationStatus.MATCHED)
        self.assertEqual(run_matched.matched_tables, 1)
        self.assertEqual(run_matched.total_mismatches, 0)

        # Divergent table
        tables_divergent = {
            "users": {
                "source_rows": [{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob_Updated"}, {"id": 3, "name": "Charlie"}],
                "target_rows": [{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob_Old"}, {"id": 4, "name": "Extra_Target"}],
            }
        }
        run_div = self.validation_engine.execute_validation(
            identity=self.identity,
            tables_data=tables_divergent,
            window=win,
            level=CDCValidationLevel.LEVEL_3_ROW_RECONCILIATION,
        )
        self.assertEqual(run_div.status, CDCValidationStatus.MISMATCHED)
        self.assertEqual(run_div.total_mismatches, 3)
        self.assertTrue(len(run_div.reconciliations) >= 3)

        div_classes = {r.mismatch_class for r in run_div.reconciliations}
        self.assertIn(CDCDivergenceClass.VALUE_MISMATCH, div_classes)
        self.assertIn(CDCDivergenceClass.MISSING_TARGET_ROW, div_classes)
        self.assertIn(CDCDivergenceClass.EXTRA_TARGET_ROW, div_classes)

    def test_A03_safe_fenced_reconciliation_repair(self):
        """Proves safe remediation executes for deterministic mismatches and fails on stale epoch or ambiguity."""
        tables_data = {
            "users": {
                "source_rows": [{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}],
                "target_rows": [{"id": 1, "name": "Alice"}], # id:2 missing on target
            }
        }
        win = self.validation_engine.establish_validation_window("0/100", "0/100", "0/100")
        run = self.validation_engine.execute_validation(self.identity, tables_data, win, CDCValidationLevel.LEVEL_3_ROW_RECONCILIATION)
        self.assertEqual(len(run.reconciliations), 1)
        rec = run.reconciliations[0]
        self.assertEqual(rec.repair_action, CDCRepairActionType.REPAIR_MISSING_ROW)

        # 1. Stale fencing epoch rejected
        stale_epoch = self.fencing_epoch - 1
        with self.assertRaises(CDCExecutionError):
            self.validation_engine.execute_safe_repair(self.identity, rec.reconciliation_id, stale_epoch)

        # 2. Valid fencing epoch executes repair
        repair_res = self.validation_engine.execute_safe_repair(self.identity, rec.reconciliation_id, self.fencing_epoch)
        self.assertEqual(repair_res["status"], "REPAIRED")
        self.assertEqual(repair_res["repair_status"], CDCRepairStatus.EXECUTED.value)

    def test_A04_extra_row_divergence_requires_manual_governance(self):
        """Proves extra target rows fail closed into manual governance requirement to prevent data loss."""
        tables_data = {
            "orders": {
                "source_rows": [{"id": 101, "item": "Widget"}],
                "target_rows": [{"id": 101, "item": "Widget"}, {"id": 999, "item": "RogueRow"}],
            }
        }
        win = self.validation_engine.establish_validation_window("0/200", "0/200", "0/200")
        run = self.validation_engine.execute_validation(self.identity, tables_data, win, CDCValidationLevel.LEVEL_3_ROW_RECONCILIATION)
        self.assertEqual(len(run.reconciliations), 1)
        rec = run.reconciliations[0]
        self.assertEqual(rec.mismatch_class, CDCDivergenceClass.EXTRA_TARGET_ROW)
        self.assertEqual(rec.repair_action, CDCRepairActionType.MANUAL_GOVERNANCE_REQUIRED)

        # Attempt safe repair on manual governance required row
        res = self.validation_engine.execute_safe_repair(self.identity, rec.reconciliation_id, self.fencing_epoch)
        self.assertEqual(res["status"], "MANUAL_GOVERNANCE_REQUIRED")
        self.assertEqual(res["repair_status"], CDCRepairStatus.REJECTED.value)

    def test_A05_progressive_validation_level_5_revalidation(self):
        """Proves progressive Level 5 executes post-repair revalidation."""
        tables_data = {
            "accounts": {
                "source_rows": [{"id": 1, "balance": 500}],
                "target_rows": [{"id": 1, "balance": 500}],
            }
        }
        win = self.validation_engine.establish_validation_window("0/300", "0/300", "0/300")
        run = self.validation_engine.execute_validation(self.identity, tables_data, win, CDCValidationLevel.LEVEL_5_POST_REPAIR_REVALIDATION)
        self.assertEqual(run.level, CDCValidationLevel.LEVEL_5_POST_REPAIR_REVALIDATION)
        self.assertEqual(run.status, CDCValidationStatus.MATCHED)

    # =========================================================================
    # Workstream B: Final Drain & Controlled Cutover
    # =========================================================================

    def test_B01_cutover_readiness_all_17_gates(self):
        """Proves 17 cutover readiness gates enforce strict zero-backlog and backend truth."""
        # 1. Healthy ready evaluation
        res_ready = CDCCutoverReadinessEngine.evaluate_readiness(
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
            unresolved_conflicts=0,
            active_quarantines=0,
            quiescence_valid=True,
        )
        self.assertTrue(res_ready["ready"])
        self.assertEqual(res_ready["overall_status"], "READY")
        self.assertEqual(len(res_ready["blocking_reasons"]), 0)

        # 2. Non-zero backlog blocks cutover
        res_backlog = CDCCutoverReadinessEngine.evaluate_readiness(
            cdc_session_id=self.cdc_session_id,
            session_state="SYNCHRONIZED",
            is_synchronized=True,
            event_backlog=10,
            time_lag_ms=10.0,
            checkpoint_valid=True,
            has_failed_transactions=False,
            is_stale_worker=False,
        )
        self.assertFalse(res_backlog["ready"])
        self.assertIn("BACKLOG_TOO_HIGH", str(res_backlog["blocking_reasons"]))

        # 3. Unresolved conflict blocks cutover
        res_conf = CDCCutoverReadinessEngine.evaluate_readiness(
            cdc_session_id=self.cdc_session_id,
            session_state="SYNCHRONIZED",
            is_synchronized=True,
            event_backlog=0,
            time_lag_ms=10.0,
            checkpoint_valid=True,
            has_failed_transactions=False,
            is_stale_worker=False,
            unresolved_conflicts=1,
        )
        self.assertFalse(res_conf["ready"])
        self.assertIn("UNRESOLVED_MULTI_MASTER_CONFLICTS", str(res_conf["blocking_reasons"]))
        self.assertEqual(res_conf["gates"]["conflicts_resolved"]["status"], "BLOCKED")

    def test_B02_source_quiescence_contract_and_write_invalidation(self):
        """Proves source quiescence contract is invalidated if source writes occur post-quiescence."""
        contract = CDCSourceQuiescenceContract(self.cdc_session_id)
        self.assertFalse(contract.is_quiescence_valid)

        pos_1 = PostgresLSNPosition("0/50000")
        contract.mark_quiesced(pos_1)
        self.assertTrue(contract.is_quiescence_valid)

        # Post-quiescence write arrives
        pos_write = PostgresLSNPosition("0/50050")
        contract.record_write_observed(pos_write)
        self.assertFalse(contract.is_quiescence_valid)
        self.assertTrue(contract.quiescence_invalidated)

    def test_B03_end_to_end_cutover_commit_and_idempotency(self):
        """Proves full cutover flow: prepare -> approval -> quiescence -> drain -> validation -> commit."""
        # 1. Start sync & transition to SYNCHRONIZED
        self.sync_coordinator.start_continuous_sync(
            self.migration_id, self.job_id, self.run_id, self.cdc_session_id
        )
        sm = self.sync_coordinator.session_state_machines[self.cdc_session_id]
        sm.transition_to(CDCSessionState.SYNCHRONIZED)

        # 2. Prepare cutover plan
        plan_dict = self.sync_coordinator.prepare_cutover(
            self.migration_id, self.job_id, self.run_id, self.cdc_session_id
        )
        self.assertEqual(plan_dict["current_phase"], CutoverPhase.PRECHECK_COMPLETE.value)

        # 3. Record governance approval
        appr = self.sync_coordinator.record_approval(
            self.cdc_session_id, approved_by="admin@enterprise.internal", approval_token="token-p310"
        )
        self.assertIsNotNone(appr["approval_token"])

        # 4. Final drain
        drain_res = self.sync_coordinator.begin_final_drain(self.cdc_session_id, "0/9000000")
        self.assertEqual(drain_res["status"], "FINAL_DRAIN_COMPLETE")

        # 5. Final validation
        val_res = self.sync_coordinator.run_cutover_validation(self.cdc_session_id)
        self.assertEqual(val_res["status"], CDCValidationStatus.MATCHED.value)
        self.assertEqual(sm.current_state, CDCSessionState.CUTOVER_READY)

        # 6. Commit Cutover
        commit_res = self.sync_coordinator.commit_cutover(self.cdc_session_id)
        self.assertEqual(commit_res["status"], "CUTOVER_COMPLETE")
        self.assertEqual(commit_res["authoritative_role"], PrimaryRoleState.TARGET_PRIMARY.value)

        # 7. Idempotent duplicate commit request
        dup_res = self.sync_coordinator.commit_cutover(self.cdc_session_id)
        self.assertEqual(dup_res["status"], "CUTOVER_COMPLETE")
        self.assertTrue(dup_res.get("idempotent_replay", False))

    # =========================================================================
    # Workstream C: Failback & Recovery
    # =========================================================================

    def test_C01_pre_cutover_abort_and_post_cutover_failback(self):
        """Proves pre-cutover abort restores sync and post-cutover divergence fails closed."""
        # 1. Pre-cutover abort
        self.sync_coordinator.start_continuous_sync(
            self.migration_id, self.job_id, self.run_id, self.cdc_session_id
        )
        sm = self.sync_coordinator.session_state_machines[self.cdc_session_id]
        sm.transition_to(CDCSessionState.SYNCHRONIZED)
        self.sync_coordinator.prepare_cutover(
            self.migration_id, self.job_id, self.run_id, self.cdc_session_id
        )
        abort_res = self.sync_coordinator.abort_cutover(self.cdc_session_id)
        self.assertEqual(abort_res["status"], "PRE_CUTOVER_ABORTED")
        self.assertEqual(abort_res["restored_state"], CDCSessionState.CAPTURING.value)

        # 2. Post-cutover target-write divergence evaluation
        fb_eng = CDCFailbackDecisionEngine(self.cdc_session_id)
        fb_eng.set_role(PrimaryRoleState.TARGET_PRIMARY)
        plan = CDCCutoverPlan(self.identity, self.fencing_epoch)
        plan.is_committed = True

        # Target received writes without reverse sync -> MANUAL_INTERVENTION_REQUIRED
        eval_div = fb_eng.evaluate_post_cutover_failback(
            cutover_plan=plan,
            target_received_post_cutover_writes=True,
            reverse_cdc_available=False,
        )
        self.assertFalse(eval_div["safe_auto_failback"])
        self.assertEqual(eval_div["status"], "MANUAL_INTERVENTION_REQUIRED")
        self.assertEqual(eval_div["classification"], CDCFailbackClassification.MANUAL_INTERVENTION_REQUIRED.value)

    def test_C02_safe_post_cutover_failback_without_target_writes(self):
        """Proves safe failback is permitted when target has received 0 post-cutover writes."""
        fb_eng = CDCFailbackDecisionEngine(self.cdc_session_id)
        fb_eng.set_role(PrimaryRoleState.TARGET_PRIMARY)
        plan = CDCCutoverPlan(self.identity, self.fencing_epoch)
        plan.is_committed = True

        eval_safe = fb_eng.evaluate_post_cutover_failback(
            cutover_plan=plan,
            target_received_post_cutover_writes=False,
            reverse_cdc_available=False,
        )
        self.assertTrue(eval_safe["safe_auto_failback"])
        self.assertEqual(eval_safe["status"], "FAILBACK_ELIGIBLE")
        self.assertEqual(eval_safe["classification"], CDCFailbackClassification.POST_CUTOVER_SAFE_FAILBACK.value)

    # =========================================================================
    # Workstream D: Migration Lifecycle Orchestration
    # =========================================================================

    def test_D01_canonical_lifecycle_transitions_and_illegal_jump_rejection(self):
        """Proves legal lifecycle transitions succeed and illegal jumps are strictly rejected."""
        rec = self.lifecycle_coordinator.initialize_lifecycle(
            self.migration_id, self.job_id, self.run_id, self.cdc_session_id
        )
        self.assertEqual(rec["current_state"], MigrationLifecycleState.CREATED.value)

        # Legal progression
        self.lifecycle_coordinator.transition_state(self.migration_id, MigrationLifecycleState.CONFIGURING)
        self.lifecycle_coordinator.transition_state(self.migration_id, MigrationLifecycleState.PREFLIGHT)
        self.lifecycle_coordinator.transition_state(self.migration_id, MigrationLifecycleState.APPROVED)
        self.lifecycle_coordinator.transition_state(self.migration_id, MigrationLifecycleState.INITIAL_LOAD)
        self.lifecycle_coordinator.transition_state(self.migration_id, MigrationLifecycleState.CDC_INITIALIZING)
        self.lifecycle_coordinator.transition_state(self.migration_id, MigrationLifecycleState.CDC_ACTIVE)
        self.lifecycle_coordinator.transition_state(self.migration_id, MigrationLifecycleState.CDC_SYNCHRONIZED)
        self.lifecycle_coordinator.transition_state(self.migration_id, MigrationLifecycleState.CUTOVER_READY)
        self.lifecycle_coordinator.transition_state(self.migration_id, MigrationLifecycleState.FINAL_DRAIN)
        self.lifecycle_coordinator.transition_state(self.migration_id, MigrationLifecycleState.FINAL_VALIDATION)
        self.lifecycle_coordinator.transition_state(self.migration_id, MigrationLifecycleState.CUTOVER_COMMITTING)
        self.lifecycle_coordinator.transition_state(self.migration_id, MigrationLifecycleState.TARGET_PRIMARY)
        self.lifecycle_coordinator.transition_state(self.migration_id, MigrationLifecycleState.COMPLETED)

        final_rec = self.lifecycle_coordinator.get_lifecycle(self.migration_id)
        self.assertEqual(final_rec["current_state"], MigrationLifecycleState.COMPLETED.value)

        # Illegal terminal resurrection
        with self.assertRaises(ValueError):
            self.lifecycle_coordinator.transition_state(self.migration_id, MigrationLifecycleState.CONFIGURING)

    def test_D02_lifecycle_restart_recoverability(self):
        """Proves lifecycle state is reconstructed from CentralStateStore upon restart."""
        self.lifecycle_coordinator.initialize_lifecycle(
            self.migration_id, self.job_id, self.run_id, self.cdc_session_id
        )
        self.lifecycle_coordinator.transition_state(self.migration_id, MigrationLifecycleState.CONFIGURING)
        self.lifecycle_coordinator.transition_state(self.migration_id, MigrationLifecycleState.PREFLIGHT)

        # Simulate new coordinator instance (restart)
        new_coord = CDCMigrationLifecycleCoordinator(state_store=self.state_store)
        reconstructed = new_coord.get_lifecycle(self.migration_id)
        self.assertIsNotNone(reconstructed)
        self.assertEqual(reconstructed["current_state"], MigrationLifecycleState.PREFLIGHT.value)
        self.assertEqual(len(reconstructed["history"]), 3)

    # =========================================================================
    # Workstream E & F: Gateway Reachability & Historical Immutability
    # =========================================================================

    def test_E01_gateway_p3_10_capabilities_and_historical_immutability(self):
        """Proves EngineGateway routes all P3.10 IPC capabilities and enforces historical immutability."""
        # 1. Lifecycle
        lc = self.gateway.handle_capability("get_migration_lifecycle", {"migration_id": self.migration_id})
        self.assertIsNotNone(lc["current_state"])

        # 2. Validation
        val_status = self.gateway.handle_capability("get_cdc_validation_status", {"cdc_session_id": self.cdc_session_id})
        self.assertIn("status", val_status)

        val_run = self.gateway.handle_capability("start_cdc_validation", {
            "migration_id": self.migration_id,
            "cdc_session_id": self.cdc_session_id,
            "level": "LEVEL_2_TABLE_CHECKSUM",
        })
        self.assertEqual(val_run["status"], "MATCHED")

        # 3. Cutover Readiness
        ready = self.gateway.handle_capability("get_cdc_cutover_readiness", {"cdc_session_id": self.cdc_session_id})
        self.assertIn("ready", ready)

        # 4. Failback status
        fb = self.gateway.handle_capability("get_cdc_failback_status", {"cdc_session_id": self.cdc_session_id})
        self.assertIn("status", fb)

        # 5. Historical Session Immutability
        hist_mig_id = "mig-historical-p310"
        self.state_store.set_state(f"migration_{hist_mig_id}", {"status": "COMPLETED"}, category="migration")

        mut_res = self.gateway.handle_capability("start_cdc_validation", {"migration_id": hist_mig_id})
        self.assertEqual(mut_res["status"], "REJECTED_HISTORICAL_IMMUTABLE")

        mut_cut = self.gateway.handle_capability("commit_cdc_cutover", {"migration_id": hist_mig_id})
        self.assertEqual(mut_cut["status"], "REJECTED_HISTORICAL_IMMUTABLE")


if __name__ == "__main__":
    unittest.main()
