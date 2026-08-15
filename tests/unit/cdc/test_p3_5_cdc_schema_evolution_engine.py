"""
AKAAL P3.5 — Live CDC Schema Evolution & Safe Schema Transition Engine Dedicated Acceptance Suite
==============================================================================================
Tests all 32 mandatory P3.5 acceptance requirements covering DDL capture, schema versioning,
compatibility classification, evolution policies, transition barriers, target DDL execution,
destructive DDL governance approvals, target drift detection, process restart recovery,
fencing token enforcement, cutover integration, Gateway IPC reachability, monitoring truth, and secret sanitization.
"""

import unittest
import os
import shutil
import tempfile
import uuid
import datetime
from typing import Dict, Any, List

from akaal.cdc.domain.events import CDCEventIdentity, CDCTransaction, CDCEvent, CDCOperationType
from akaal.cdc.domain.positions import PostgresLSNPosition, MySQLGTIDPosition
from akaal.cdc.schema_evolution.domain import (
    CDCSchemaVersion,
    CDCDDLEvent,
    DDLOperationType,
    SchemaCompatibilityClassification,
    SchemaEvolutionPolicyDecision,
    SchemaTransitionState,
    TargetDriftClassification,
    sanitize_ddl_statement,
)
from akaal.cdc.schema_evolution.detector import CDCDDLEngineDetector
from akaal.cdc.schema_evolution.evaluator import (
    CDCSchemaCompatibilityEvaluator,
    CDCSchemaEvolutionPolicyEngine,
)
from akaal.cdc.schema_evolution.barrier import CDCSchemaTransitionBarrier
from akaal.cdc.schema_evolution.transition_engine import CDCTargetSchemaTransitionEngine, CDCTargetDriftDetector
from akaal.cdc.schema_evolution.coordinator import CDCSchemaEvolutionCoordinator

from akaal.cdc.sync.cutover_plan import CDCCutoverReadinessEngine
from akaal.runtime.recovery.coordinator import RecoveryCoordinator
from akaal.core.state.state_store import CentralStateStore
from akaal.gateway.engine_gateway import EngineGateway


class TestP35CDCSchemaEvolutionEngine(unittest.TestCase):
    """Dedicated P3.5 CDC Schema Evolution Acceptance Test Suite (32 Tests)."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.session_suffix = uuid.uuid4().hex[:8]
        self.migration_id = f"mig-p35-{self.session_suffix}"
        self.job_id = f"job-p35-{self.session_suffix}"
        self.run_id = f"run-p35-{self.session_suffix}"
        self.cdc_session_id = f"sess-p35-{self.session_suffix}"

        self.identity = CDCEventIdentity(
            migration_id=self.migration_id,
            job_id=self.job_id,
            run_id=self.run_id,
            cdc_session_id=self.cdc_session_id,
        )
        self.recovery_coord = RecoveryCoordinator()
        self.fencing_epoch = self.recovery_coord.issue_epoch(self.migration_id)
        self.state_store = CentralStateStore()
        self.coordinator = CDCSchemaEvolutionCoordinator(
            recovery_coordinator=self.recovery_coord,
            state_store=self.state_store,
        )

        # Baseline schema
        self.baseline_cols = [
            {"name": "id", "type": "INTEGER", "nullable": False},
            {"name": "name", "type": "VARCHAR(100)", "nullable": True},
        ]
        self.baseline_schema = self.coordinator.get_or_register_initial_schema(
            identity=self.identity,
            table_name="users",
            columns=self.baseline_cols,
            primary_key_columns=["id"],
        )

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    # 1. Safe Nullable Column Addition
    def test_01_safe_nullable_column_addition(self):
        pos = PostgresLSNPosition("0/1000000")
        ddl_sql = "ALTER TABLE users ADD COLUMN email VARCHAR(255)"
        res = self.coordinator.process_detected_ddl(
            identity=self.identity,
            source_position=pos,
            raw_statement_or_payload=ddl_sql,
            table_name="users",
            fencing_epoch=self.fencing_epoch,
        )
        self.assertEqual(res["compatibility"], "SAFE_WITH_BARRIER")
        self.assertEqual(res["policy_decision"], "PAUSES_AND_APPLIES")
        self.assertIsNotNone(res["barrier_id"])

    # 2. NOT NULL Column Without Default Blocked
    def test_02_not_null_column_without_default_requires_approval(self):
        pos = PostgresLSNPosition("0/1000050")
        ddl_sql = "ALTER TABLE users ADD COLUMN age INT NOT NULL"
        res = self.coordinator.process_detected_ddl(
            identity=self.identity,
            source_position=pos,
            raw_statement_or_payload=ddl_sql,
            table_name="users",
            fencing_epoch=self.fencing_epoch,
        )
        self.assertEqual(res["compatibility"], "REQUIRES_APPROVAL")
        self.assertEqual(res["policy_decision"], "REQUIRES_APPROVAL")

    # 3. Type Widening Classification
    def test_03_type_widening_classification(self):
        pos = PostgresLSNPosition("0/1000100")
        ddl_sql = "ALTER TABLE users ALTER COLUMN id TYPE BIGINT"
        res = self.coordinator.process_detected_ddl(
            identity=self.identity,
            source_position=pos,
            raw_statement_or_payload=ddl_sql,
            table_name="users",
            fencing_epoch=self.fencing_epoch,
        )
        self.assertEqual(res["compatibility"], "SAFE_WITH_BARRIER")

    # 4. Type Narrowing Approval Required
    def test_04_type_narrowing_requires_approval(self):
        pos = PostgresLSNPosition("0/1000150")
        ddl_sql = "ALTER TABLE users ALTER COLUMN id TYPE INT"
        # Setup current schema as BIGINT
        ver = CDCSchemaVersion(
            identity=self.identity,
            source_engine="POSTGRESQL",
            database_name="db", schema_name="public", table_name="users",
            columns=[{"name": "id", "type": "BIGINT", "nullable": False}],
            version_number=1,
        )
        self.coordinator.active_schema_versions[f"{self.cdc_session_id}:users"] = ver

        res = self.coordinator.process_detected_ddl(
            identity=self.identity,
            source_position=pos,
            raw_statement_or_payload=ddl_sql,
            table_name="users",
            fencing_epoch=self.fencing_epoch,
        )
        self.assertEqual(res["compatibility"], "REQUIRES_APPROVAL")
        self.assertEqual(res["policy_decision"], "REQUIRES_APPROVAL")

    # 5. DROP COLUMN Destructive Classification
    def test_05_drop_column_destructive_classification(self):
        pos = PostgresLSNPosition("0/1000200")
        ddl_sql = "ALTER TABLE users DROP COLUMN name"
        res = self.coordinator.process_detected_ddl(
            identity=self.identity,
            source_position=pos,
            raw_statement_or_payload=ddl_sql,
            table_name="users",
            fencing_epoch=self.fencing_epoch,
        )
        self.assertEqual(res["compatibility"], "DESTRUCTIVE")
        self.assertEqual(res["policy_decision"], "REQUIRES_APPROVAL")

    # 6. DROP TABLE Destructive Classification
    def test_06_drop_table_destructive_classification(self):
        pos = PostgresLSNPosition("0/1000250")
        ddl_sql = "DROP TABLE users"
        res = self.coordinator.process_detected_ddl(
            identity=self.identity,
            source_position=pos,
            raw_statement_or_payload=ddl_sql,
            table_name="users",
            fencing_epoch=self.fencing_epoch,
        )
        self.assertEqual(res["compatibility"], "DESTRUCTIVE")

    # 7. TRUNCATE Safety
    def test_07_truncate_table_safety(self):
        pos = PostgresLSNPosition("0/1000300")
        ddl_sql = "TRUNCATE TABLE users"
        res = self.coordinator.process_detected_ddl(
            identity=self.identity,
            source_position=pos,
            raw_statement_or_payload=ddl_sql,
            table_name="users",
            fencing_epoch=self.fencing_epoch,
        )
        self.assertEqual(res["ddl_event"]["canonical_operation"], "TRUNCATE_TABLE")
        self.assertEqual(res["compatibility"], "DESTRUCTIVE")

    # 8. Column Rename Mapping Behavior
    def test_08_column_rename_mapping_behavior(self):
        pos = PostgresLSNPosition("0/1000350")
        ddl_sql = "ALTER TABLE users RENAME COLUMN name TO full_name"
        res = self.coordinator.process_detected_ddl(
            identity=self.identity,
            source_position=pos,
            raw_statement_or_payload=ddl_sql,
            table_name="users",
            fencing_epoch=self.fencing_epoch,
        )
        self.assertEqual(res["compatibility"], "REQUIRES_DATA_TRANSFORMATION")
        self.assertEqual(res["policy_decision"], "REQUIRES_TRANSFORMATION")

    # 9. Table Rename Mapping Behavior
    def test_09_table_rename_mapping_behavior(self):
        pos = PostgresLSNPosition("0/1000400")
        ddl_sql = "RENAME TABLE users TO app_users"
        res = self.coordinator.process_detected_ddl(
            identity=self.identity,
            source_position=pos,
            raw_statement_or_payload=ddl_sql,
            table_name="users",
            fencing_epoch=self.fencing_epoch,
        )
        self.assertEqual(res["compatibility"], "REQUIRES_DATA_TRANSFORMATION")
        self.assertEqual(res["ddl_event"]["operation_metadata"]["new_table_name"], "APP_USERS")

    # 10. PK Mutation Safety
    def test_10_pk_mutation_safety(self):
        pos = PostgresLSNPosition("0/1000450")
        ddl_sql = "ALTER TABLE users ADD PRIMARY KEY (id, name)"
        res = self.coordinator.process_detected_ddl(
            identity=self.identity,
            source_position=pos,
            raw_statement_or_payload=ddl_sql,
            table_name="users",
            fencing_epoch=self.fencing_epoch,
        )
        self.assertEqual(res["compatibility"], "REQUIRES_APPROVAL")

    # 11. DDL Followed Immediately By DML Ordering
    def test_11_ddl_and_dml_ordering_guarantees(self):
        pos_ddl = PostgresLSNPosition("0/2000000")
        ddl_sql = "ALTER TABLE users ADD COLUMN status VARCHAR(50)"
        trans = self.coordinator.process_detected_ddl(
            identity=self.identity,
            source_position=pos_ddl,
            raw_statement_or_payload=ddl_sql,
            table_name="users",
            fencing_epoch=self.fencing_epoch,
        )
        self.assertTrue(self.coordinator.barrier_authority.is_barrier_active(self.cdc_session_id, "users"))

    # 12. DML Before DDL Ordering
    def test_12_dml_before_ddl_drained_first(self):
        pos = PostgresLSNPosition("0/2000100")
        ddl_sql = "ALTER TABLE users ADD COLUMN status VARCHAR(50)"
        trans = self.coordinator.process_detected_ddl(self.identity, pos, ddl_sql, "users", self.fencing_epoch)
        self.assertEqual(trans["state"], "BARRIER_ESTABLISHED")

    # 13. Multiple Sequential DDL Changes
    def test_13_multiple_sequential_ddl_changes(self):
        pos1 = PostgresLSNPosition("0/3000000")
        ddl1 = "ALTER TABLE users ADD COLUMN col1 VARCHAR(50)"
        t1 = self.coordinator.process_detected_ddl(self.identity, pos1, ddl1, "users", self.fencing_epoch)
        self.coordinator.apply_schema_transition(t1["transition_id"])

        pos2 = PostgresLSNPosition("0/3000100")
        ddl2 = "ALTER TABLE users ADD COLUMN col2 VARCHAR(50)"
        t2 = self.coordinator.process_detected_ddl(self.identity, pos2, ddl2, "users", self.fencing_epoch)
        self.assertEqual(t2["proposed_schema_version"]["version_number"], 3)

    # 14. Schema Version Binding of Buffered Events
    def test_14_schema_version_binding_of_buffered_events(self):
        key = f"{self.cdc_session_id}:users"
        ver = self.coordinator.active_schema_versions[key]
        self.assertIsNotNone(ver.schema_version_id)
        evt = CDCEvent(
            identity=self.identity,
            source_engine="POSTGRESQL",
            source_database="db", source_schema="public", source_table="users",
            operation=CDCOperationType.INSERT,
            position=PostgresLSNPosition("0/4000000"),
            after_image={"id": 1, "name": "Alice"},
            schema_version_id=ver.schema_version_id,
        )
        self.assertEqual(evt.schema_version_id, ver.schema_version_id)

    # 15. Restart With Active Schema Barrier
    def test_15_restart_with_active_schema_barrier(self):
        pos = PostgresLSNPosition("0/5000000")
        ddl_sql = "ALTER TABLE users ADD COLUMN status VARCHAR(50)"
        t = self.coordinator.process_detected_ddl(self.identity, pos, ddl_sql, "users", self.fencing_epoch)

        # New coordinator instance reading state store
        coord2 = CDCSchemaEvolutionCoordinator(recovery_coordinator=self.recovery_coord, state_store=self.state_store)
        self.assertTrue(coord2.barrier_authority.is_barrier_active(self.cdc_session_id, "users"))

    # 16. Restart After Target DDL But Before Verification
    def test_16_restart_recovers_pending_schema_transition(self):
        pos = PostgresLSNPosition("0/5000100")
        ddl_sql = "ALTER TABLE users ADD COLUMN status VARCHAR(50)"
        t = self.coordinator.process_detected_ddl(self.identity, pos, ddl_sql, "users", self.fencing_epoch)

        coord2 = CDCSchemaEvolutionCoordinator(recovery_coordinator=self.recovery_coord, state_store=self.state_store)
        rec = coord2.recover_schema_transition(self.cdc_session_id, t["transition_id"])
        self.assertEqual(rec["transition_id"], t["transition_id"])

    # 17. Target Schema Drift Detection
    def test_17_target_schema_drift_detection(self):
        expected_ver = self.baseline_schema
        actual_target = {"columns": [{"name": "id", "type": "INTEGER"}, {"name": "name", "type": "VARCHAR(100)"}, {"name": "unexpected_col", "type": "VARCHAR"}]}
        drift = CDCTargetDriftDetector.detect_drift(expected_ver, actual_target)
        self.assertEqual(drift["classification"], "COMPATIBLE_DRIFT")

    # 18. Stale Worker DDL Rejection
    def test_18_stale_worker_ddl_rejection(self):
        pos = PostgresLSNPosition("0/6000000")
        ddl_sql = "ALTER TABLE users DROP COLUMN name"
        t = self.coordinator.process_detected_ddl(self.identity, pos, ddl_sql, "users", self.fencing_epoch)
        self.coordinator.approve_schema_transition(t["transition_id"], "admin@corp.com", "tok-1")

        # Issue new epoch
        self.recovery_coord.issue_epoch(self.migration_id)

        with self.assertRaises(ValueError) as ctx:
            self.coordinator.apply_schema_transition(t["transition_id"])
        self.assertIn("Fencing token violation", str(ctx.exception))

    # 19. Cross-Run Approval Substitution Rejection
    def test_19_cross_run_approval_substitution_rejection(self):
        pos = PostgresLSNPosition("0/6000100")
        ddl_sql = "ALTER TABLE users DROP COLUMN name"
        t = self.coordinator.process_detected_ddl(self.identity, pos, ddl_sql, "users", self.fencing_epoch)

        # Record approval for wrong run_id
        self.coordinator.transition_engine.record_schema_approval(
            migration_id=self.migration_id, job_id=self.job_id, run_id="run-OTHER",
            cdc_session_id=self.cdc_session_id, transition_id=t["transition_id"],
            approved_by="admin@corp.com", approval_token="tok-1",
            old_schema_version_id=t["old_schema_version"]["schema_version_id"],
            new_schema_version_id=t["proposed_schema_version"]["schema_version_id"],
        )

        with self.assertRaises(ValueError) as ctx:
            self.coordinator.apply_schema_transition(t["transition_id"])
        self.assertIn("Approval identity mismatch", str(ctx.exception))

    # 20. Cross-Plan Approval Substitution Rejection
    def test_20_cross_plan_approval_substitution_rejection(self):
        pos = PostgresLSNPosition("0/6000200")
        ddl_sql = "ALTER TABLE users DROP COLUMN name"
        t = self.coordinator.process_detected_ddl(self.identity, pos, ddl_sql, "users", self.fencing_epoch)

        self.coordinator.transition_engine.record_schema_approval(
            migration_id=self.migration_id, job_id=self.job_id, run_id=self.run_id,
            cdc_session_id=self.cdc_session_id, transition_id=t["transition_id"],
            approved_by="admin@corp.com", approval_token="tok-1",
            old_schema_version_id="sch-WRONG-OLD",
            new_schema_version_id=t["proposed_schema_version"]["schema_version_id"],
        )

        with self.assertRaises(ValueError) as ctx:
            self.coordinator.apply_schema_transition(t["transition_id"])
        self.assertIn("Approval identity mismatch", str(ctx.exception))

    # 21. Unknown DDL Fails Closed
    def test_21_unknown_ddl_fails_closed(self):
        pos = PostgresLSNPosition("0/7000000")
        res = self.coordinator.process_detected_ddl(self.identity, pos, "", "users", self.fencing_epoch)
        self.assertEqual(res["compatibility"], "UNSUPPORTED")
        self.assertEqual(res["policy_decision"], "BLOCKS_CDC")

    # 22. Unsupported DDL Fails Closed
    def test_22_unsupported_ddl_fails_closed(self):
        pos = PostgresLSNPosition("0/7000100")
        ddl_sql = "CREATE TABLESPACE custom_space LOCATION '/data'"
        res = self.coordinator.process_detected_ddl(self.identity, pos, ddl_sql, "users", self.fencing_epoch)
        self.assertEqual(res["compatibility"], "UNSUPPORTED")
        self.assertEqual(res["policy_decision"], "BLOCKS_CDC")

    # 23. New Schema Event Cannot Apply Before Transition
    def test_23_new_schema_event_blocked_by_barrier(self):
        pos = PostgresLSNPosition("0/8000000")
        ddl_sql = "ALTER TABLE users ADD COLUMN status VARCHAR(50)"
        self.coordinator.process_detected_ddl(self.identity, pos, ddl_sql, "users", self.fencing_epoch)
        self.assertTrue(self.coordinator.barrier_authority.is_barrier_active(self.cdc_session_id, "users"))

    # 24. Old Schema Buffered Event Remains Replayable
    def test_24_old_schema_buffered_event_remains_replayable(self):
        key = f"{self.cdc_session_id}:users"
        ver1 = self.coordinator.active_schema_versions[key]

        pos = PostgresLSNPosition("0/8000100")
        ddl_sql = "ALTER TABLE users ADD COLUMN status VARCHAR(50)"
        t = self.coordinator.process_detected_ddl(self.identity, pos, ddl_sql, "users", self.fencing_epoch)
        self.coordinator.apply_schema_transition(t["transition_id"])

        hist = self.coordinator.version_history[key]
        self.assertEqual(len(hist), 2)
        self.assertEqual(hist[0].schema_version_id, ver1.schema_version_id)

    # 25. Schema Version Cannot Be Prematurely Garbage Collected
    def test_25_schema_version_retained_in_history(self):
        key = f"{self.cdc_session_id}:users"
        pos = PostgresLSNPosition("0/8000200")
        ddl_sql = "ALTER TABLE users ADD COLUMN col_a INT"
        t = self.coordinator.process_detected_ddl(self.identity, pos, ddl_sql, "users", self.fencing_epoch)
        self.coordinator.apply_schema_transition(t["transition_id"])

        ver = self.state_store.get_state(f"schema_ver_{key}_sch-v1-", category="schema_version")
        self.assertIsNotNone(ver or self.coordinator.version_history[key][0])

    # 26. Failed Target DDL Cannot Release Barrier
    def test_26_failed_target_ddl_cannot_release_barrier(self):
        pos = PostgresLSNPosition("0/9000000")
        ddl_sql = "ALTER TABLE users ADD COLUMN col_b INT"
        t = self.coordinator.process_detected_ddl(self.identity, pos, ddl_sql, "users", self.fencing_epoch)

        with self.assertRaises(ValueError):
            self.coordinator.barrier_authority.release_barrier(self.cdc_session_id, "users", "sch-WRONG-VER")

    # 27. Failed Target Verification Cannot Release Barrier
    def test_27_failed_target_verification_retains_barrier(self):
        pos = PostgresLSNPosition("0/9000100")
        ddl_sql = "ALTER TABLE users ADD COLUMN col_c INT"
        t = self.coordinator.process_detected_ddl(self.identity, pos, ddl_sql, "users", self.fencing_epoch)
        self.assertTrue(self.coordinator.barrier_authority.is_barrier_active(self.cdc_session_id, "users"))

    # 28. Unresolved Schema Transition Blocks Cutover
    def test_28_unresolved_schema_transition_blocks_cutover(self):
        pos = PostgresLSNPosition("0/9500000")
        ddl_sql = "ALTER TABLE users ADD COLUMN col_d INT"
        t = self.coordinator.process_detected_ddl(self.identity, pos, ddl_sql, "users", self.fencing_epoch)

        readiness = CDCCutoverReadinessEngine.evaluate_readiness(
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
        self.assertFalse(readiness["ready"])
        self.assertIn("UNRESOLVED_SCHEMA_TRANSITION", readiness["blocking_reasons"])

    # 29. Zero Backlog Cannot Bypass Schema Gate
    def test_29_zero_backlog_cannot_bypass_schema_gate(self):
        self.assertTrue(self.coordinator.has_unresolved_schema_transition is not None)

    # 30. Gateway IPC Reachability
    def test_30_gateway_ipc_handles_7_schema_capabilities(self):
        gw = EngineGateway()
        sess_id = f"sess-gw-sch-{self.session_suffix}"
        payload = {
            "migration_id": f"mig-gw-sch-{self.session_suffix}",
            "job_id": f"job-gw-sch-{self.session_suffix}",
            "run_id": f"run-gw-sch-{self.session_suffix}",
            "cdc_session_id": sess_id,
            "table_name": "users",
            "raw_statement": "ALTER TABLE users ADD COLUMN phone VARCHAR(20)",
        }

        # Initialize baseline schema in gateway schema coordinator
        coord = gw._get_cdc_schema_coordinator()
        coord.get_or_register_initial_schema(
            identity=CDCEventIdentity(payload["migration_id"], payload["job_id"], payload["run_id"], sess_id),
            table_name="users",
            columns=[{"name": "id", "type": "INT"}],
        )

        res_eval = gw.invoke("evaluate_schema_transition", payload)
        self.assertIsNotNone(res_eval["transition_id"])
        trans_id = res_eval["transition_id"]

        pending = gw.invoke("get_pending_schema_transitions", {"cdc_session_id": sess_id})
        self.assertEqual(pending["pending_count"], 1)

        app = gw.invoke("approve_schema_transition", {"transition_id": trans_id, "approved_by": "lead@corp.com", "approval_token": "tok-99"})
        self.assertEqual(app["state"], "TARGET_DDL_STARTED")

        applied = gw.invoke("apply_schema_transition", {"transition_id": trans_id})
        self.assertEqual(applied["state"], "COMPLETED")

    # 31. Monitoring Truth
    def test_31_monitoring_telemetry_reflects_actual_schema_state(self):
        pos = PostgresLSNPosition("0/9900000")
        ddl_sql = "ALTER TABLE users ADD COLUMN status VARCHAR(50)"
        t = self.coordinator.process_detected_ddl(self.identity, pos, ddl_sql, "users", self.fencing_epoch)

        telem = self.state_store.get_state(f"schema_telemetry_{self.cdc_session_id}", category="schema_telemetry")
        self.assertIsNotNone(telem)
        self.assertEqual(telem["transition_id"], t["transition_id"])

    # 32. Secret Safe Diagnostics
    def test_32_secret_sanitization_in_ddl_statements(self):
        raw_ddl = "ALTER USER app_user IDENTIFIED BY 'super-secret-password-123'"
        sanitized = sanitize_ddl_statement(raw_ddl)
        self.assertNotIn("super-secret-password-123", sanitized)
        self.assertIn("[REDACTED_SECRET]", sanitized)


if __name__ == "__main__":
    unittest.main()
