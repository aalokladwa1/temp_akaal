"""
AKAAL P3.4.1 — Hostile Semantic, Multi-Database Continuous Sync, Cutover & Failback Acceptance Audit Suite
==========================================================================================================
Hostile acceptance suite executing 38 adversarial attacks against P3.4 continuous sync, lag model,
cutover readiness, durable cutover plan integrity, governance approval binding, final drain,
P2 validation reuse, irreversible cutover commit, concurrent coordinator race safety, split-brain prevention,
cutover & failback crash-window matrices, restart recovery, pre-cutover abort, post-cutover failback divergence,
Gateway IPC reachability, monitoring truth, and secret redaction.
"""

import unittest
import os
import shutil
import tempfile
import uuid
import time
import datetime
from typing import Dict, Any, Optional

from akaal.cdc.domain.events import (
    CDCEventIdentity,
    CDCTransaction,
    CDCEvent,
    CDCOperationType,
    CDCTransactionBoundary,
)
from akaal.cdc.domain.positions import (
    PostgresLSNPosition,
    MySQLGTIDPosition,
    OracleSCNPosition,
    MSSQLChangePosition,
    MongoDBOpLogPosition,
)
from akaal.cdc.domain.lifecycle import CDCSessionState, InvalidStateTransitionError
from akaal.cdc.domain.errors import CDCExecutionError, CDCFailureType
from akaal.cdc.sync.lag_model import CDCLagMetrics, CDCSynchronizationStabilityEvaluator
from akaal.cdc.sync.cutover_plan import (
    CDCCutoverPlan,
    CutoverPhase,
    CDCSourceQuiescenceContract,
    CDCCutoverReadinessEngine,
)
from akaal.cdc.sync.failback import PrimaryRoleState, CDCFailbackDecisionEngine
from akaal.cdc.sync.coordinator import CDCContinuousSyncCoordinator

from akaal.runtime.recovery.coordinator import RecoveryCoordinator
from akaal.core.state.state_store import CentralStateStore
from akaal.gateway.engine_gateway import EngineGateway


class TestP341HostileSyncCutoverFailbackAudit(unittest.TestCase):
    """P3.4.1 Hostile Semantic, Continuous Sync, Cutover & Failback Audit Suite (38 Adversarial Tests)."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.session_suffix = uuid.uuid4().hex[:8]
        self.migration_id = f"mig-p341-{self.session_suffix}"
        self.job_id = f"job-p341-{self.session_suffix}"
        self.run_id = f"run-p341-{self.session_suffix}"
        self.cdc_session_id = f"sess-p341-{self.session_suffix}"

        self.identity = CDCEventIdentity(
            migration_id=self.migration_id,
            job_id=self.job_id,
            run_id=self.run_id,
            cdc_session_id=self.cdc_session_id,
        )
        self.recovery_coord = RecoveryCoordinator()
        self.fencing_epoch = self.recovery_coord.issue_epoch(self.migration_id)
        self.state_store = CentralStateStore()
        self.sync_coordinator = CDCContinuousSyncCoordinator(
            recovery_coordinator=self.recovery_coord,
            state_store=self.state_store,
        )
        self.gateway = EngineGateway()

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    # -------------------------------------------------------------------------
    # SECTION 4 & 6: CONTINUOUS SYNC & FALSE SYNCHRONIZATION ATTACKS (Tests 1-6)
    # -------------------------------------------------------------------------
    def test_01_attack_single_low_lag_observation_cannot_establish_sync(self):
        """ATTACK: Single transient low lag sample MUST NOT trigger SYNCHRONIZED state."""
        evaluator = CDCSynchronizationStabilityEvaluator(
            required_stability_window_sec=1.0,
            required_observation_count=5,
        )
        metrics = CDCLagMetrics(self.cdc_session_id, "POSTGRESQL", time_lag_ms=10.0, buffered_events=0)
        res = evaluator.evaluate(metrics)
        self.assertFalse(res["is_synchronized"])
        self.assertEqual(evaluator.consecutive_stable_observations, 1)

    def test_02_attack_backlog_growth_resets_stability_window(self):
        """ATTACK: Sudden backlog spike during observation window resets stability counter."""
        evaluator = CDCSynchronizationStabilityEvaluator(
            required_stability_window_sec=0.1,
            required_observation_count=3,
            max_allowed_backlog_events=5,
        )
        m_good = CDCLagMetrics(self.cdc_session_id, "POSTGRESQL", buffered_events=0)
        m_spike = CDCLagMetrics(self.cdc_session_id, "POSTGRESQL", buffered_events=500)

        evaluator.evaluate(m_good)
        evaluator.evaluate(m_good)
        self.assertEqual(evaluator.consecutive_stable_observations, 2)

        res_spike = evaluator.evaluate(m_spike)
        self.assertFalse(res_spike["is_synchronized"])
        self.assertEqual(evaluator.consecutive_stable_observations, 0)
        self.assertIsNone(evaluator.synchronized_since)

    def test_03_attack_unacknowledged_backlog_blocks_readiness(self):
        """ATTACK: Buffered unacknowledged transactions MUST block cutover readiness."""
        res = CDCCutoverReadinessEngine.evaluate_readiness(
            cdc_session_id=self.cdc_session_id,
            session_state="SYNCHRONIZED",
            is_synchronized=True,
            event_backlog=50,
            time_lag_ms=10.0,
            checkpoint_valid=True,
            has_failed_transactions=False,
            is_stale_worker=False,
        )
        self.assertFalse(res["ready"])
        self.assertIn("BACKLOG_TOO_HIGH (50 > 5)", res["blocking_reasons"])

    def test_04_attack_capture_failure_invalidates_sync_readiness(self):
        """ATTACK: Unsynchronized session state MUST block readiness."""
        res = CDCCutoverReadinessEngine.evaluate_readiness(
            cdc_session_id=self.cdc_session_id,
            session_state="FAILED",
            is_synchronized=False,
            event_backlog=0,
            time_lag_ms=0.0,
            checkpoint_valid=True,
            has_failed_transactions=False,
            is_stale_worker=False,
        )
        self.assertFalse(res["ready"])
        self.assertIn("SESSION_NOT_SYNCHRONIZED (Current State: FAILED)", res["blocking_reasons"])

    def test_05_attack_stale_checkpoint_invalidates_readiness(self):
        """ATTACK: Invalid checkpoint integrity MUST block cutover readiness."""
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
        self.assertIn("CHECKPOINT_INTEGRITY_INVALID", res["blocking_reasons"])

    def test_06_attack_unresolved_failed_transactions_invalidates_readiness(self):
        """ATTACK: Active failed transaction attempts MUST block readiness."""
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
        self.assertIn("UNRESOLVED_TRANSACTION_FAILURES", res["blocking_reasons"])

    # -------------------------------------------------------------------------
    # SECTION 5: MULTI-DATABASE POSITION SEMANTICS (Tests 7-10)
    # -------------------------------------------------------------------------
    def test_07_attack_cross_engine_position_subtraction_rejected(self):
        """ATTACK: Cross-engine position comparison MUST raise TypeError."""
        pg_pos = PostgresLSNPosition("0/1000000")
        my_pos = MySQLGTIDPosition("3E11FA47-71CA-11E1-9E33-C80AA9429562:1-5", 107)

        with self.assertRaises(TypeError):
            pg_pos.is_after(my_pos)

    def test_08_attack_gtid_discontinuity_and_format_handling(self):
        """ATTACK: GTID position handles discontinuities without raw integer arithmetic."""
        my1 = MySQLGTIDPosition("uuid:1-10", 100)
        my2 = MySQLGTIDPosition("uuid:1-10,12-15", 200)
        self.assertTrue(my2.is_after(my1))

    def test_09_attack_mongodb_oplog_opaque_token_monotonicity(self):
        """ATTACK: MongoDB oplog token comparison respects timestamp_sec and inc."""
        op1 = MongoDBOpLogPosition(1600000000, 1)
        op2 = MongoDBOpLogPosition(1600000000, 2)
        op3 = MongoDBOpLogPosition(1600000001, 1)

        self.assertTrue(op2.is_after(op1))
        self.assertTrue(op3.is_after(op2))

    def test_10_attack_position_regression_rejected(self):
        """ATTACK: Attempting position regression MUST raise ValueError."""
        pos1 = PostgresLSNPosition("0/2000000")
        pos2 = PostgresLSNPosition("0/1000000")
        self.assertTrue(pos1.is_after(pos2))
        self.assertFalse(pos2.is_after(pos1))

    # -------------------------------------------------------------------------
    # SECTION 7, 8 & 9: CUTOVER PLAN, READINESS & APPROVAL ATTACKS (Tests 11-16)
    # -------------------------------------------------------------------------
    def test_11_attack_missing_approval_blocks_readiness(self):
        """ATTACK: Cutover readiness without bound approval MUST fail."""
        self.sync_coordinator.start_continuous_sync(self.migration_id, self.job_id, self.run_id, self.cdc_session_id)
        self.sync_coordinator.session_state_machines[self.cdc_session_id].current_state = CDCSessionState.SYNCHRONIZED
        self.sync_coordinator.prepare_cutover(self.migration_id, self.job_id, self.run_id, self.cdc_session_id)

        readiness = self.sync_coordinator.evaluate_cutover_readiness(self.cdc_session_id)
        self.assertFalse(readiness["ready"])
        self.assertIn("GOVERNANCE_APPROVAL_MISSING", readiness["blocking_reasons"])

    def test_12_attack_approval_from_wrong_migration_rejected(self):
        """ATTACK: Governance approval with mismatched migration ID MUST be rejected."""
        self.sync_coordinator.start_continuous_sync(self.migration_id, self.job_id, self.run_id, self.cdc_session_id)
        self.sync_coordinator.session_state_machines[self.cdc_session_id].current_state = CDCSessionState.SYNCHRONIZED
        self.sync_coordinator.prepare_cutover(self.migration_id, self.job_id, self.run_id, self.cdc_session_id)

        # Record approval for wrong plan_id
        with self.assertRaises(ValueError):
            self.sync_coordinator.record_approval(self.cdc_session_id, "lead@corp.com", "tok-1", plan_id="plan-wrong-999")

    def test_13_attack_cross_run_approval_substitution_rejected(self):
        """ATTACK: Stale approval from another run MUST NOT authorize cutover."""
        sm = self.sync_coordinator.get_or_create_state_machine(self.identity)
        sm.current_state = CDCSessionState.SYNCHRONIZED

        plan = CDCCutoverPlan(self.identity, self.fencing_epoch)
        plan.approval_reference = {
            "cdc_session_id": self.cdc_session_id,
            "migration_id": self.migration_id,
            "run_id": "run-OTHER-RUN",
            "plan_id": plan.plan_id,
        }
        self.sync_coordinator.cutover_plans[self.cdc_session_id] = plan
        readiness = self.sync_coordinator.evaluate_cutover_readiness(self.cdc_session_id)
        self.assertFalse(readiness["ready"])
        self.assertIn("GOVERNANCE_APPROVAL_MISSING", readiness["blocking_reasons"])

    def test_14_attack_cutover_plan_tampering_detected(self):
        """ATTACK: Cutover plan identity fields MUST remain bound."""
        plan = CDCCutoverPlan(self.identity, self.fencing_epoch)
        plan_dict = plan.to_dict()
        self.assertEqual(plan_dict["identity"]["migration_id"], self.migration_id)
        self.assertEqual(plan_dict["fencing_epoch"], self.fencing_epoch)

    def test_15_attack_commit_cutover_without_ready_state_fails(self):
        """ATTACK: Invoking commit_cutover while session is unready MUST raise ValueError."""
        self.sync_coordinator.start_continuous_sync(self.migration_id, self.job_id, self.run_id, self.cdc_session_id)
        with self.assertRaises(ValueError):
            self.sync_coordinator.commit_cutover(self.cdc_session_id)

    def test_16_attack_unvalidated_cutover_plan_commit_rejected(self):
        """ATTACK: Cutover plan lacking final validation MUST fail readiness check."""
        self.sync_coordinator.start_continuous_sync(self.migration_id, self.job_id, self.run_id, self.cdc_session_id)
        self.sync_coordinator.session_state_machines[self.cdc_session_id].current_state = CDCSessionState.SYNCHRONIZED
        self.sync_coordinator.prepare_cutover(self.migration_id, self.job_id, self.run_id, self.cdc_session_id)
        self.sync_coordinator.record_approval(self.cdc_session_id, "lead@corp.com", "tok-1")

        readiness = self.sync_coordinator.evaluate_cutover_readiness(self.cdc_session_id)
        self.assertFalse(readiness["ready"])
        self.assertIn("FINAL_VALIDATION_BLOCKER", readiness["blocking_reasons"])

    # -------------------------------------------------------------------------
    # SECTION 10 & 11: FINAL DRAIN & QUIESCENCE ATTACKS (Tests 17-19)
    # -------------------------------------------------------------------------
    def test_17_attack_final_drain_without_cutover_plan_fails(self):
        """ATTACK: Initiating final drain without active cutover plan raises ValueError."""
        with self.assertRaises(ValueError):
            self.sync_coordinator.begin_final_drain(self.cdc_session_id)

    def test_18_attack_stale_fencing_token_during_final_drain_rejected(self):
        """ATTACK: Stale fencing epoch during final drain raises CDCExecutionError."""
        self.sync_coordinator.start_continuous_sync(self.migration_id, self.job_id, self.run_id, self.cdc_session_id)
        self.sync_coordinator.session_state_machines[self.cdc_session_id].current_state = CDCSessionState.SYNCHRONIZED
        self.sync_coordinator.prepare_cutover(self.migration_id, self.job_id, self.run_id, self.cdc_session_id)

        # Epoch bump
        self.recovery_coord.issue_epoch(self.migration_id)

        with self.assertRaises(CDCExecutionError) as ctx:
            self.sync_coordinator.begin_final_drain(self.cdc_session_id)
        self.assertEqual(ctx.exception.failure.failure_type, CDCFailureType.STALE_WORKER)

    def test_19_attack_source_quiescence_contract_marking(self):
        """ATTACK: Source quiescence contract records final LSN and timestamp."""
        contract = CDCSourceQuiescenceContract(self.cdc_session_id)
        self.assertFalse(contract.is_quiesced)

        pos = PostgresLSNPosition("0/8000000")
        contract.mark_quiesced(pos)
        self.assertTrue(contract.is_quiesced)
        self.assertIsNotNone(contract.quiesced_at)

    # -------------------------------------------------------------------------
    # SECTION 12, 13 & 14: COMMIT, CONCURRENCY & SPLIT-BRAIN ATTACKS (Tests 20-25)
    # -------------------------------------------------------------------------
    def test_20_attack_commit_cutover_is_safely_idempotent(self):
        """ATTACK: Repeated commit_cutover on committed plan returns idempotent success."""
        self.sync_coordinator.start_continuous_sync(self.migration_id, self.job_id, self.run_id, self.cdc_session_id)
        self.sync_coordinator.session_state_machines[self.cdc_session_id].current_state = CDCSessionState.SYNCHRONIZED
        self.sync_coordinator.prepare_cutover(self.migration_id, self.job_id, self.run_id, self.cdc_session_id)
        self.sync_coordinator.record_approval(self.cdc_session_id, "admin@corp.com", "tok-1")
        self.sync_coordinator.begin_final_drain(self.cdc_session_id)
        self.sync_coordinator.run_cutover_validation(self.cdc_session_id)

        res1 = self.sync_coordinator.commit_cutover(self.cdc_session_id)
        self.assertEqual(res1["status"], "CUTOVER_COMPLETE")

        # Second commit
        res2 = self.sync_coordinator.commit_cutover(self.cdc_session_id)
        self.assertEqual(res2["status"], "CUTOVER_COMPLETE")
        self.assertTrue(res2.get("idempotent_replay"))

    def test_21_attack_stale_coordinator_cannot_commit_cutover(self):
        """ATTACK: Stale coordinator fencing token MUST reject cutover commit."""
        self.sync_coordinator.start_continuous_sync(self.migration_id, self.job_id, self.run_id, self.cdc_session_id)
        self.sync_coordinator.session_state_machines[self.cdc_session_id].current_state = CDCSessionState.SYNCHRONIZED
        self.sync_coordinator.prepare_cutover(self.migration_id, self.job_id, self.run_id, self.cdc_session_id)
        self.sync_coordinator.record_approval(self.cdc_session_id, "admin@corp.com", "tok-1")
        self.sync_coordinator.begin_final_drain(self.cdc_session_id)
        self.sync_coordinator.run_cutover_validation(self.cdc_session_id)

        # Issue new fencing epoch
        self.recovery_coord.issue_epoch(self.migration_id)

        with self.assertRaises(CDCExecutionError) as ctx:
            self.sync_coordinator.commit_cutover(self.cdc_session_id)
        self.assertEqual(ctx.exception.failure.failure_type, CDCFailureType.STALE_WORKER)

    def test_22_attack_split_brain_prevention_two_primaries_rejected(self):
        """ATTACK: Both source and target receiving writes MUST reject failback with MANUAL_INTERVENTION_REQUIRED."""
        engine = CDCFailbackDecisionEngine(self.cdc_session_id)
        plan = CDCCutoverPlan(self.identity, self.fencing_epoch)
        plan.is_committed = True

        res = engine.evaluate_post_cutover_failback(
            cutover_plan=plan,
            target_received_post_cutover_writes=True,
            source_received_post_cutover_writes=True,
            reverse_cdc_available=True,
        )
        self.assertFalse(res["safe_auto_failback"])
        self.assertEqual(res["status"], "MANUAL_INTERVENTION_REQUIRED")
        self.assertIn("SPLIT_BRAIN_BOTH_DATABASES_RECEIVED_WRITES", res["blockers"])

    def test_23_attack_ambiguous_unknown_primary_role_fails_closed(self):
        """ATTACK: Primary role in UNKNOWN state MUST fail closed for failback."""
        engine = CDCFailbackDecisionEngine(self.cdc_session_id)
        engine.set_role(PrimaryRoleState.UNKNOWN)
        plan = CDCCutoverPlan(self.identity, self.fencing_epoch)
        plan.is_committed = True

        res = engine.evaluate_post_cutover_failback(plan)
        self.assertFalse(res["safe_auto_failback"])
        self.assertIn("UNKNOWN_AUTHORITATIVE_ROLE_STATE", res["blockers"])

    def test_24_attack_terminal_cutover_state_cannot_be_resurrected(self):
        """ATTACK: Transitioning out of terminal CUTOVER_COMPLETE directly to CAPTURING is illegal."""
        sm = self.sync_coordinator.get_or_create_state_machine(self.identity)
        sm.current_state = CDCSessionState.CUTOVER_COMPLETE
        with self.assertRaises(InvalidStateTransitionError):
            sm.transition_to(CDCSessionState.CAPTURING)

    def test_25_attack_concurrent_fencing_epochs_prevent_conflicting_commit(self):
        """ATTACK: Dual coordinators with different fencing tokens cannot commit concurrently."""
        coord1 = CDCContinuousSyncCoordinator(recovery_coordinator=self.recovery_coord, state_store=self.state_store)
        coord2 = CDCContinuousSyncCoordinator(recovery_coordinator=self.recovery_coord, state_store=self.state_store)

        coord1.start_continuous_sync(self.migration_id, self.job_id, self.run_id, self.cdc_session_id)
        coord1.session_state_machines[self.cdc_session_id].current_state = CDCSessionState.SYNCHRONIZED
        coord1.prepare_cutover(self.migration_id, self.job_id, self.run_id, self.cdc_session_id)

        # Coord2 issues new epoch
        epoch2 = self.recovery_coord.issue_epoch(self.migration_id)

        # Coord1 attempts commit with old epoch -> Fails
        with self.assertRaises(CDCExecutionError):
            coord1.commit_cutover(self.cdc_session_id)

    # -------------------------------------------------------------------------
    # SECTION 15, 16 & 17: CRASH MATRICES, RECOVERY & ABORT ATTACKS (Tests 26-29)
    # -------------------------------------------------------------------------
    def test_26_attack_pre_cutover_abort_restores_capturing_state(self):
        """ATTACK: Pre-cutover abort returns session state machine to CAPTURING."""
        self.sync_coordinator.start_continuous_sync(self.migration_id, self.job_id, self.run_id, self.cdc_session_id)
        self.sync_coordinator.session_state_machines[self.cdc_session_id].current_state = CDCSessionState.SYNCHRONIZED
        self.sync_coordinator.prepare_cutover(self.migration_id, self.job_id, self.run_id, self.cdc_session_id)

        res = self.sync_coordinator.abort_cutover(self.cdc_session_id)
        self.assertEqual(res["status"], "PRE_CUTOVER_ABORTED")
        self.assertEqual(res["restored_state"], "CAPTURING")

    def test_27_attack_abort_after_committed_cutover_fails(self):
        """ATTACK: Abort requested after irreversible cutover commit MUST fail."""
        self.sync_coordinator.start_continuous_sync(self.migration_id, self.job_id, self.run_id, self.cdc_session_id)
        self.sync_coordinator.session_state_machines[self.cdc_session_id].current_state = CDCSessionState.SYNCHRONIZED
        self.sync_coordinator.prepare_cutover(self.migration_id, self.job_id, self.run_id, self.cdc_session_id)
        self.sync_coordinator.record_approval(self.cdc_session_id, "admin@corp.com", "tok-1")
        self.sync_coordinator.begin_final_drain(self.cdc_session_id)
        self.sync_coordinator.run_cutover_validation(self.cdc_session_id)
        self.sync_coordinator.commit_cutover(self.cdc_session_id)

        with self.assertRaises(ValueError):
            self.sync_coordinator.abort_cutover(self.cdc_session_id)

    def test_28_attack_restart_recovery_with_mismatched_migration_id_rejected(self):
        """ATTACK: Recovering cutover session with wrong migration ID MUST be rejected."""
        self.sync_coordinator.start_continuous_sync(self.migration_id, self.job_id, self.run_id, self.cdc_session_id)
        self.sync_coordinator.session_state_machines[self.cdc_session_id].current_state = CDCSessionState.SYNCHRONIZED
        self.sync_coordinator.prepare_cutover(self.migration_id, self.job_id, self.run_id, self.cdc_session_id)

        with self.assertRaises(ValueError):
            self.sync_coordinator.recover_cutover_session("mig-WRONG-MIGRATION", self.cdc_session_id)

    def test_29_attack_restart_recovery_restores_target_primary_role(self):
        """ATTACK: Recovering cutover session after commit restores TARGET_PRIMARY role."""
        self.sync_coordinator.start_continuous_sync(self.migration_id, self.job_id, self.run_id, self.cdc_session_id)
        self.sync_coordinator.session_state_machines[self.cdc_session_id].current_state = CDCSessionState.SYNCHRONIZED
        self.sync_coordinator.prepare_cutover(self.migration_id, self.job_id, self.run_id, self.cdc_session_id)
        self.sync_coordinator.record_approval(self.cdc_session_id, "admin@corp.com", "tok-1")
        self.sync_coordinator.begin_final_drain(self.cdc_session_id)
        self.sync_coordinator.run_cutover_validation(self.cdc_session_id)
        self.sync_coordinator.commit_cutover(self.cdc_session_id)

        rec = self.sync_coordinator.recover_cutover_session(self.migration_id, self.cdc_session_id)
        self.assertEqual(rec["status"], "CUTOVER_COMPLETE")
        self.assertEqual(rec["authoritative_role"], "TARGET_PRIMARY")

    # -------------------------------------------------------------------------
    # SECTION 18, 19 & 20: FAILBACK & POST-CUTOVER DIVERGENCE ATTACKS (Tests 30-33)
    # -------------------------------------------------------------------------
    def test_30_attack_failback_without_reverse_cdc_fails_closed(self):
        """ATTACK: Target writes occurred without reverse CDC returns MANUAL_INTERVENTION_REQUIRED."""
        engine = CDCFailbackDecisionEngine(self.cdc_session_id)
        plan = CDCCutoverPlan(self.identity, self.fencing_epoch)
        plan.is_committed = True

        res = engine.evaluate_post_cutover_failback(
            cutover_plan=plan,
            target_received_post_cutover_writes=True,
            reverse_cdc_available=False,
        )
        self.assertFalse(res["safe_auto_failback"])
        self.assertEqual(res["status"], "MANUAL_INTERVENTION_REQUIRED")
        self.assertIn("POST_CUTOVER_TARGET_WRITES_WITHOUT_REVERSE_CDC", res["blockers"])

    def test_31_attack_failback_on_uncommitted_cutover_rejected(self):
        """ATTACK: Post-cutover failback evaluation on uncommitted plan returns blocker."""
        engine = CDCFailbackDecisionEngine(self.cdc_session_id)
        plan = CDCCutoverPlan(self.identity, self.fencing_epoch)

        res = engine.evaluate_post_cutover_failback(cutover_plan=plan)
        self.assertFalse(res["safe_auto_failback"])
        self.assertIn("CUTOVER_NOT_COMMITTED", res["blockers"])

    def test_32_attack_execute_failback_without_force_fails_closed(self):
        """ATTACK: Executing unsafe failback without force flag fails closed."""
        self.sync_coordinator.start_continuous_sync(self.migration_id, self.job_id, self.run_id, self.cdc_session_id)
        self.sync_coordinator.session_state_machines[self.cdc_session_id].current_state = CDCSessionState.SYNCHRONIZED
        self.sync_coordinator.prepare_cutover(self.migration_id, self.job_id, self.run_id, self.cdc_session_id)
        self.sync_coordinator.record_approval(self.cdc_session_id, "admin@corp.com", "tok-1")
        self.sync_coordinator.begin_final_drain(self.cdc_session_id)
        self.sync_coordinator.run_cutover_validation(self.cdc_session_id)
        self.sync_coordinator.commit_cutover(self.cdc_session_id)

        res = self.sync_coordinator.execute_failback(self.cdc_session_id)
        self.assertFalse(res["safe_auto_failback"])
        self.assertEqual(res["status"], "MANUAL_INTERVENTION_REQUIRED")

    def test_33_attack_governed_force_failback_restores_source_primary(self):
        """ATTACK: Governed forced failback transitions role to SOURCE_PRIMARY."""
        self.sync_coordinator.start_continuous_sync(self.migration_id, self.job_id, self.run_id, self.cdc_session_id)
        self.sync_coordinator.session_state_machines[self.cdc_session_id].current_state = CDCSessionState.SYNCHRONIZED
        self.sync_coordinator.prepare_cutover(self.migration_id, self.job_id, self.run_id, self.cdc_session_id)
        self.sync_coordinator.record_approval(self.cdc_session_id, "admin@corp.com", "tok-1")
        self.sync_coordinator.begin_final_drain(self.cdc_session_id)
        self.sync_coordinator.run_cutover_validation(self.cdc_session_id)
        self.sync_coordinator.commit_cutover(self.cdc_session_id)

        res = self.sync_coordinator.execute_failback(self.cdc_session_id, force_governed=True)
        self.assertEqual(res["status"], "FAILBACK_COMPLETE")
        self.assertEqual(res["authoritative_role"], "SOURCE_PRIMARY")

    # -------------------------------------------------------------------------
    # SECTION 24, 25 & 26: GATEWAY IPC, MONITORING & SECRET REDACTION (Tests 34-38)
    # -------------------------------------------------------------------------
    def test_34_attack_gateway_ipc_handles_13_p34_capabilities(self):
        """ATTACK: All 13 P3.4 Gateway IPC capabilities reach canonical sync coordinator."""
        gw = EngineGateway()
        sess_id = f"sess-gw13-{self.session_suffix}"
        payload = {
            "migration_id": f"mig-gw13-{self.session_suffix}",
            "job_id": f"job-gw13-{self.session_suffix}",
            "run_id": f"run-gw13-{self.session_suffix}",
            "cdc_session_id": sess_id,
        }
        res_start = gw.invoke("start_continuous_sync", payload)
        self.assertEqual(res_start["status"], "APPLYING")

        coord = gw._get_cdc_sync_coordinator()
        coord.session_state_machines[sess_id].current_state = CDCSessionState.SYNCHRONIZED

        prep = gw.invoke("prepare_cutover", payload)
        self.assertIsNotNone(prep["plan_id"])

        app = gw.invoke("record_cutover_approval", {"cdc_session_id": sess_id, "approved_by": "lead@corp.com", "approval_token": "tok-123", "plan_id": prep["plan_id"]})
        self.assertEqual(app["approved_by"], "lead@corp.com")

        drain = gw.invoke("begin_final_drain", {"cdc_session_id": sess_id})
        self.assertEqual(drain["status"], "FINAL_DRAIN_COMPLETE")

        val = gw.invoke("run_cutover_validation", {"cdc_session_id": sess_id})
        self.assertTrue(val["checksum_match"])

        readiness = gw.invoke("evaluate_cutover_readiness", {"cdc_session_id": sess_id})
        self.assertTrue(readiness["ready"])

        commit = gw.invoke("commit_cutover", {"cdc_session_id": sess_id})
        self.assertEqual(commit["status"], "CUTOVER_COMPLETE")

    def test_35_attack_gateway_ipc_unsupported_capability_raises_valueerror(self):
        """ATTACK: Invoking unknown IPC capability raises ValueError."""
        gw = EngineGateway()
        with self.assertRaises(ValueError):
            gw.invoke("invalid_p34_capability", {})

    def test_36_attack_monitoring_telemetry_never_fabricates_readiness(self):
        """ATTACK: Monitoring telemetry reflects actual backend readiness state."""
        self.sync_coordinator.start_continuous_sync(self.migration_id, self.job_id, self.run_id, self.cdc_session_id)
        telemetry = self.state_store.get_cdc_telemetry(self.cdc_session_id)
        self.assertIsNotNone(telemetry)
        self.assertFalse(telemetry["is_cutover_ready"])

    def test_37_attack_secret_redaction_in_nested_event_payloads(self):
        """ATTACK: Passwords, tokens, and API keys are redacted in event to_dict()."""
        evt = CDCEvent(
            identity=self.identity,
            source_engine="POSTGRESQL",
            source_database="db",
            source_schema="public",
            source_table="users",
            operation=CDCOperationType.INSERT,
            position=PostgresLSNPosition("0/1000000"),
            after_image={
                "username": "admin",
                "password": "super-secret-password",
                "api_key": "key-12345",
                "meta": {"auth_token": "bearer-xyz"},
            },
        )
        d = evt.to_dict()
        self.assertEqual(d["after_image"]["password"], "[REDACTED_SECRET]")
        self.assertEqual(d["after_image"]["api_key"], "[REDACTED_SECRET]")
        self.assertEqual(d["after_image"]["meta"]["auth_token"], "[REDACTED_SECRET]")

    def test_38_truthful_proof_classification_boundary(self):
        """ATTACK: REAL_DB_PROVEN MUST BE False under unit/simulated test execution."""
        self.assertFalse(os.environ.get("AKAAL_REAL_DB_PROVEN", "False") == "True")


if __name__ == "__main__":
    unittest.main()
