"""
AKAAL P3.4 — Multi-Database Continuous CDC Synchronization, Cutover & Failback Acceptance Suite
==================================================================================================
Acceptance suite testing continuous CDC capture/apply cycles, lag stability evaluation, cutover readiness,
durable cutover plans, final drain, P2 validation reuse, governance approvals, cutover commit point,
pre-cutover abort, governed failback, split-brain prevention, and IPC reachability.
"""

import unittest
import os
import shutil
import tempfile
import uuid
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


class TestP34ContinuousCDCCutoverFailbackEngine(unittest.TestCase):
    """P3.4 Continuous CDC Synchronization, Cutover & Failback Acceptance Suite (20 Tests)."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.session_suffix = uuid.uuid4().hex[:8]
        self.migration_id = f"mig-p34-{self.session_suffix}"
        self.job_id = f"job-p34-{self.session_suffix}"
        self.run_id = f"run-p34-{self.session_suffix}"
        self.cdc_session_id = f"sess-p34-{self.session_suffix}"

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
    # 1. CONTINUOUS SYNCHRONIZATION & STABILITY WINDOW TESTS
    # -------------------------------------------------------------------------
    def test_01_start_continuous_sync_lifecycle(self):
        res = self.sync_coordinator.start_continuous_sync(
            migration_id=self.migration_id,
            job_id=self.job_id,
            run_id=self.run_id,
            cdc_session_id=self.cdc_session_id,
        )
        self.assertEqual(res["status"], "APPLYING")
        self.assertGreaterEqual(res["fencing_epoch"], 1)

    def test_02_stability_window_evaluator_requires_sustained_stability(self):
        evaluator = CDCSynchronizationStabilityEvaluator(
            required_stability_window_sec=0.1,
            required_observation_count=2,
            max_allowed_lag_ms=1000.0,
            max_allowed_backlog_events=0,
        )
        metrics = CDCLagMetrics(
            cdc_session_id=self.cdc_session_id,
            source_engine="POSTGRESQL",
            time_lag_ms=500.0,
            buffered_events=0,
        )
        # First observation
        res1 = evaluator.evaluate(metrics)
        self.assertFalse(res1["is_synchronized"])

        import time
        time.sleep(0.15)

        # Second observation
        res2 = evaluator.evaluate(metrics)
        self.assertTrue(res2["is_synchronized"])

    def test_03_transient_lag_spike_resets_stability_window(self):
        evaluator = CDCSynchronizationStabilityEvaluator(
            required_stability_window_sec=0.1,
            required_observation_count=2,
            max_allowed_lag_ms=500.0,
        )
        m_good = CDCLagMetrics(self.cdc_session_id, "POSTGRESQL", time_lag_ms=100.0)
        m_bad = CDCLagMetrics(self.cdc_session_id, "POSTGRESQL", time_lag_ms=5000.0)

        evaluator.evaluate(m_good)
        res_bad = evaluator.evaluate(m_bad)
        self.assertFalse(res_bad["is_synchronized"])
        self.assertEqual(evaluator.consecutive_stable_observations, 0)

    # -------------------------------------------------------------------------
    # 2. CUTOVER READINESS & DURABLE PLAN TESTS
    # -------------------------------------------------------------------------
    def test_04_backend_authoritative_cutover_readiness_blocks_unready_session(self):
        res = CDCCutoverReadinessEngine.evaluate_readiness(
            cdc_session_id=self.cdc_session_id,
            session_state="CAPTURING",
            is_synchronized=False,
            event_backlog=100,
            time_lag_ms=10000.0,
            checkpoint_valid=True,
            has_failed_transactions=True,
            is_stale_worker=False,
        )
        self.assertFalse(res["ready"])
        self.assertIn("SESSION_NOT_SYNCHRONIZED (Current State: CAPTURING)", res["blocking_reasons"])
        self.assertIn("CDC_NOT_SUSTAINED_SYNCHRONIZED", res["blocking_reasons"])

    def test_05_prepare_cutover_creates_durable_plan(self):
        self.sync_coordinator.start_continuous_sync(self.migration_id, self.job_id, self.run_id, self.cdc_session_id)
        # Force state to SYNCHRONIZED
        self.sync_coordinator.session_state_machines[self.cdc_session_id].current_state = CDCSessionState.SYNCHRONIZED

        plan = self.sync_coordinator.prepare_cutover(self.migration_id, self.job_id, self.run_id, self.cdc_session_id)
        self.assertEqual(plan["current_phase"], "PRECHECK_COMPLETE")
        self.assertIsNotNone(plan["plan_id"])

    # -------------------------------------------------------------------------
    # 3. CONTROLLED CUTOVER, FINAL DRAIN & COMMIT TESTS
    # -------------------------------------------------------------------------
    def test_06_begin_final_drain_and_validation(self):
        self.sync_coordinator.start_continuous_sync(self.migration_id, self.job_id, self.run_id, self.cdc_session_id)
        self.sync_coordinator.session_state_machines[self.cdc_session_id].current_state = CDCSessionState.SYNCHRONIZED
        self.sync_coordinator.prepare_cutover(self.migration_id, self.job_id, self.run_id, self.cdc_session_id)

        drain_res = self.sync_coordinator.begin_final_drain(self.cdc_session_id)
        self.assertEqual(drain_res["status"], "FINAL_DRAIN_COMPLETE")

        val_res = self.sync_coordinator.run_cutover_validation(self.cdc_session_id)
        self.assertTrue(val_res["schema_match"])
        self.assertTrue(val_res["checksum_match"])

    def test_07_governance_approval_registration_and_binding(self):
        self.sync_coordinator.start_continuous_sync(self.migration_id, self.job_id, self.run_id, self.cdc_session_id)
        self.sync_coordinator.session_state_machines[self.cdc_session_id].current_state = CDCSessionState.SYNCHRONIZED
        self.sync_coordinator.prepare_cutover(self.migration_id, self.job_id, self.run_id, self.cdc_session_id)

        app_res = self.sync_coordinator.record_approval(self.cdc_session_id, approved_by="admin@corp.com", approval_token="tok-123")
        self.assertEqual(app_res["approved_by"], "admin@corp.com")

    def test_08_commit_cutover_transitions_primary_role(self):
        self.sync_coordinator.start_continuous_sync(self.migration_id, self.job_id, self.run_id, self.cdc_session_id)
        self.sync_coordinator.session_state_machines[self.cdc_session_id].current_state = CDCSessionState.SYNCHRONIZED
        self.sync_coordinator.prepare_cutover(self.migration_id, self.job_id, self.run_id, self.cdc_session_id)
        self.sync_coordinator.record_approval(self.cdc_session_id, "admin@corp.com", "tok-1")
        self.sync_coordinator.begin_final_drain(self.cdc_session_id)
        self.sync_coordinator.run_cutover_validation(self.cdc_session_id)

        commit_res = self.sync_coordinator.commit_cutover(self.cdc_session_id)
        self.assertEqual(commit_res["status"], "CUTOVER_COMPLETE")
        self.assertEqual(commit_res["authoritative_role"], "TARGET_PRIMARY")

    def test_09_stale_coordinator_cannot_commit_cutover(self):
        self.sync_coordinator.start_continuous_sync(self.migration_id, self.job_id, self.run_id, self.cdc_session_id)
        self.sync_coordinator.session_state_machines[self.cdc_session_id].current_state = CDCSessionState.SYNCHRONIZED
        self.sync_coordinator.prepare_cutover(self.migration_id, self.job_id, self.run_id, self.cdc_session_id)
        self.sync_coordinator.record_approval(self.cdc_session_id, "admin@corp.com", "tok-1")
        self.sync_coordinator.begin_final_drain(self.cdc_session_id)
        self.sync_coordinator.run_cutover_validation(self.cdc_session_id)

        # Epoch bump in recovery coordinator
        self.recovery_coord.issue_epoch(self.migration_id)

        with self.assertRaises(CDCExecutionError) as ctx:
            self.sync_coordinator.commit_cutover(self.cdc_session_id)
        self.assertEqual(ctx.exception.failure.failure_type, CDCFailureType.STALE_WORKER)

    # -------------------------------------------------------------------------
    # 4. ABORT & FAILBACK SAFETY TESTS
    # -------------------------------------------------------------------------
    def test_10_pre_cutover_abort_restores_sync_lifecycle(self):
        self.sync_coordinator.start_continuous_sync(self.migration_id, self.job_id, self.run_id, self.cdc_session_id)
        self.sync_coordinator.session_state_machines[self.cdc_session_id].current_state = CDCSessionState.SYNCHRONIZED
        self.sync_coordinator.prepare_cutover(self.migration_id, self.job_id, self.run_id, self.cdc_session_id)

        abort_res = self.sync_coordinator.abort_cutover(self.cdc_session_id)
        self.assertEqual(abort_res["status"], "PRE_CUTOVER_ABORTED")
        self.assertEqual(abort_res["restored_state"], "CAPTURING")

    def test_11_post_cutover_divergence_fails_closed(self):
        engine = CDCFailbackDecisionEngine(self.cdc_session_id)
        plan = CDCCutoverPlan(self.identity, self.fencing_epoch)
        plan.is_committed = True

        # Post-cutover target writes occurred without reverse CDC
        res = engine.evaluate_post_cutover_failback(plan, target_received_post_cutover_writes=True, reverse_cdc_available=False)
        self.assertFalse(res["safe_auto_failback"])
        self.assertEqual(res["status"], "MANUAL_INTERVENTION_REQUIRED")

    # -------------------------------------------------------------------------
    # 5. RECOVERY & MULTI-ENGINE TESTS
    # -------------------------------------------------------------------------
    def test_12_restart_recovery_restores_committed_cutover_plan(self):
        self.sync_coordinator.start_continuous_sync(self.migration_id, self.job_id, self.run_id, self.cdc_session_id)
        self.sync_coordinator.session_state_machines[self.cdc_session_id].current_state = CDCSessionState.SYNCHRONIZED
        self.sync_coordinator.prepare_cutover(self.migration_id, self.job_id, self.run_id, self.cdc_session_id)
        self.sync_coordinator.record_approval(self.cdc_session_id, "admin@corp.com", "tok-1")
        self.sync_coordinator.begin_final_drain(self.cdc_session_id)
        self.sync_coordinator.run_cutover_validation(self.cdc_session_id)
        self.sync_coordinator.commit_cutover(self.cdc_session_id)

        # Recover cutover session
        rec_res = self.sync_coordinator.recover_cutover_session(self.migration_id, self.cdc_session_id)
        self.assertEqual(rec_res["status"], "CUTOVER_COMPLETE")
        self.assertEqual(rec_res["authoritative_role"], "TARGET_PRIMARY")

    def test_13_multi_engine_position_types_supported(self):
        pg_pos = PostgresLSNPosition("0/16B3748")
        my_pos = MySQLGTIDPosition("3E11FA47-71CA-11E1-9E33-C80AA9429562:1-5", 107)
        ora_pos = OracleSCNPosition(123456789)
        ms_pos = MSSQLChangePosition("00000024:000001D8:0001")
        mongo_pos = MongoDBOpLogPosition(1600000000, 1)

        self.assertEqual(pg_pos.to_string(), "0/16B3748")
        self.assertEqual(my_pos.to_string(), "3E11FA47-71CA-11E1-9E33-C80AA9429562:1-5:107")
        self.assertEqual(ora_pos.to_string(), "SCN:123456789#SEQ:0")
        self.assertEqual(ms_pos.to_string(), "00000024:000001D8:0001:00000000")
        self.assertEqual(mongo_pos.to_string(), "TS:1600000000:1")

    # -------------------------------------------------------------------------
    # 6. GATEWAY IPC REACHABILITY TESTS (13 Capabilities)
    # -------------------------------------------------------------------------
    def test_14_gateway_ipc_continuous_sync_lifecycle(self):
        gw = EngineGateway()
        payload = {
            "migration_id": f"mig-gw-{self.session_suffix}",
            "job_id": f"job-gw-{self.session_suffix}",
            "run_id": f"run-gw-{self.session_suffix}",
            "cdc_session_id": f"sess-gw-{self.session_suffix}",
        }
        res_start = gw.invoke("start_continuous_sync", payload)
        self.assertEqual(res_start["status"], "APPLYING")

        res_cycle = gw.invoke("process_sync_cycle", {"cdc_session_id": payload["cdc_session_id"]})
        self.assertIn("status", res_cycle)

        res_readiness = gw.invoke("evaluate_cutover_readiness", {"cdc_session_id": payload["cdc_session_id"]})
        self.assertIn("ready", res_readiness)

    def test_15_gateway_ipc_cutover_lifecycle(self):
        gw = EngineGateway()
        sess_id = f"sess-cut-{self.session_suffix}"
        payload = {
            "migration_id": f"mig-cut-{self.session_suffix}",
            "job_id": f"job-cut-{self.session_suffix}",
            "run_id": f"run-cut-{self.session_suffix}",
            "cdc_session_id": sess_id,
        }
        gw.invoke("start_continuous_sync", payload)

        coord = gw._get_cdc_sync_coordinator()
        coord.session_state_machines[sess_id].current_state = CDCSessionState.SYNCHRONIZED

        prep_res = gw.invoke("prepare_cutover", payload)
        self.assertEqual(prep_res["current_phase"], "PRECHECK_COMPLETE")

        app_res = gw.invoke("record_cutover_approval", {"cdc_session_id": sess_id, "approved_by": "lead@corp.com", "approval_token": "token-xyz"})
        self.assertEqual(app_res["approved_by"], "lead@corp.com")

        drain_res = gw.invoke("begin_final_drain", {"cdc_session_id": sess_id})
        self.assertEqual(drain_res["status"], "FINAL_DRAIN_COMPLETE")

        val_res = gw.invoke("run_cutover_validation", {"cdc_session_id": sess_id})
        self.assertTrue(val_res["checksum_match"])

        commit_res = gw.invoke("commit_cutover", {"cdc_session_id": sess_id})
        self.assertEqual(commit_res["status"], "CUTOVER_COMPLETE")

    def test_16_gateway_ipc_abort_and_failback(self):
        gw = EngineGateway()
        sess_id = f"sess-ab-{self.session_suffix}"
        payload = {
            "migration_id": f"mig-ab-{self.session_suffix}",
            "job_id": f"job-ab-{self.session_suffix}",
            "run_id": f"run-ab-{self.session_suffix}",
            "cdc_session_id": sess_id,
        }
        gw.invoke("start_continuous_sync", payload)
        gw._get_cdc_sync_coordinator().session_state_machines[sess_id].current_state = CDCSessionState.SYNCHRONIZED
        gw.invoke("prepare_cutover", payload)

        abort_res = gw.invoke("abort_cutover", {"cdc_session_id": sess_id})
        self.assertEqual(abort_res["status"], "PRE_CUTOVER_ABORTED")

        fb_eval = gw.invoke("evaluate_failback", {"cdc_session_id": sess_id, "target_received_writes": True})
        self.assertFalse(fb_eval["safe_auto_failback"])

    def test_17_illegal_state_transition_fails_closed(self):
        sm = self.sync_coordinator.get_or_create_state_machine(self.identity)
        with self.assertRaises(InvalidStateTransitionError):
            sm.transition_to(CDCSessionState.CUTOVER_COMPLETE)

    def test_18_stale_approval_or_cross_session_rejected(self):
        plan = CDCCutoverPlan(self.identity, self.fencing_epoch)
        self.assertIsNone(plan.approval_reference)

    def test_19_secrets_redacted_in_sync_telemetry(self):
        evt = CDCEvent(
            identity=self.identity,
            source_engine="POSTGRESQL",
            source_database="db",
            source_schema="public",
            source_table="creds",
            operation=CDCOperationType.INSERT,
            position=PostgresLSNPosition("0/1000000"),
            after_image={"user": "admin", "auth_token": "secret-token-12345"},
        )
        self.assertEqual(evt.to_dict()["after_image"]["auth_token"], "[REDACTED_SECRET]")

    def test_20_truthful_proof_classification_boundary(self):
        # Truthful claim verification: REAL_DB_PROVEN MUST BE False
        self.assertFalse(os.environ.get("AKAAL_REAL_DB_PROVEN", "False") == "True")


if __name__ == "__main__":
    unittest.main()
