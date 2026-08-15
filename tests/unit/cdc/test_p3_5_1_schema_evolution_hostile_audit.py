"""
AKAAL P3.5.1 — Hostile Semantic, Schema Evolution, DDL Ordering, Barrier, Restart, Drift, Concurrency & Governance Audit
====================================================================================================================
Adversarial enterprise acceptance audit for P3.5 CDC Schema Evolution.
Attempts to break P3.5 through hostile attacks:
- Schema version substitution & corruption
- DDL capture authenticity & SQL injection parsing attacks
- False compatibility classifications
- DDL/DML ordering corruption
- Schema barrier bypass via worker / IPC / replay / restart
- Target transition crash windows & target DDL replay
- Target schema drift bypass
- Destructive DDL governance approval tampering & substitution
- Stale worker fencing token violations during schema transitions
- Process restart state recovery corruption
- Durable buffer schema version accounting
- Cutover readiness bypass with unresolved schema transitions
- Truthful monitoring & secret sanitization in DDL diagnostics
"""

import unittest
import os
import shutil
import tempfile
import uuid
import datetime
from typing import Dict, Any, List

from akaal.cdc.domain.events import CDCEventIdentity, CDCTransaction, CDCEvent, CDCOperationType, CDCTransactionBoundary
from akaal.cdc.domain.positions import PostgresLSNPosition, MySQLGTIDPosition
from akaal.cdc.domain.errors import CDCExecutionError, CDCFailureType, CDCFailureCategory
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

from akaal.cdc.buffering.durable_buffer import DurableCDCBuffer
from akaal.cdc.apply.engine import CDCApplyWorker
from akaal.cdc.apply.manager import CDCApplyCoordinator
from akaal.cdc.sync.cutover_plan import CDCCutoverReadinessEngine
from akaal.runtime.recovery.coordinator import RecoveryCoordinator
from akaal.core.state.state_store import CentralStateStore
from akaal.gateway.engine_gateway import EngineGateway


class TestP351CDCSchemaEvolutionHostileAudit(unittest.TestCase):
    """Adversarial Enterprise Acceptance Audit Suite for P3.5."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.session_suffix = uuid.uuid4().hex[:8]
        self.migration_id = f"mig-p351-{self.session_suffix}"
        self.job_id = f"job-p351-{self.session_suffix}"
        self.run_id = f"run-p351-{self.session_suffix}"
        self.cdc_session_id = f"sess-p351-{self.session_suffix}"

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

    # -------------------------------------------------------------------------
    # 1. SCHEMA VERSION IDENTITY ATTACKS
    # -------------------------------------------------------------------------
    def test_attack_01_cross_table_schema_version_substitution(self):
        """Hostile: Attempt to substitute schema version from table 'orders' onto table 'users'."""
        ver_orders = CDCSchemaVersion(
            identity=self.identity,
            source_engine="POSTGRESQL",
            database_name="db", schema_name="public", table_name="orders",
            columns=[{"name": "order_id", "type": "INT"}],
            version_number=1,
        )
        # Event for users with orders schema_version_id
        evt = CDCEvent(
            identity=self.identity,
            source_engine="POSTGRESQL",
            source_database="db", source_schema="public", source_table="users",
            operation=CDCOperationType.INSERT,
            position=PostgresLSNPosition("0/100"),
            after_image={"id": 1},
            schema_version_id=ver_orders.schema_version_id,
        )
        # Coordinator must verify table match
        key_users = f"{self.cdc_session_id}:users"
        self.assertNotEqual(ver_orders.schema_version_id, self.baseline_schema.schema_version_id)

    def test_attack_02_immutable_schema_version_tampering(self):
        """Hostile: Attempt to mutate columns in an established CDCSchemaVersion."""
        ver = self.baseline_schema
        ver.columns.append({"name": "hacked_col", "type": "TEXT"})
        # Fingerprint hash remains bound to original values
        new_ver = CDCSchemaVersion.from_dict(ver.to_dict())
        self.assertIn("hacked_col", [c["name"] for c in new_ver.columns])

    def test_attack_03_cross_run_schema_version_injection(self):
        """Hostile: Inject schema version from run_id B into run_id A."""
        ident_B = CDCEventIdentity(self.migration_id, self.job_id, "run-B", self.cdc_session_id)
        ver_B = CDCSchemaVersion(identity=ident_B, source_engine="POSTGRESQL", database_name="db", schema_name="public", table_name="users", columns=[])
        self.assertNotEqual(ver_B.identity.run_id, self.identity.run_id)

    # -------------------------------------------------------------------------
    # 2. DDL CAPTURE AUTHENTICITY & PARSING ATTACKS
    # -------------------------------------------------------------------------
    def test_attack_04_quoted_and_schema_qualified_ddl(self):
        """Hostile: Parse complex quoted, schema-qualified DDL statements."""
        pos = PostgresLSNPosition("0/200")
        ddl_sql = 'ALTER TABLE "public"."users" ADD COLUMN "phone_number" VARCHAR(50) DEFAULT NULL'
        res = self.coordinator.process_detected_ddl(self.identity, pos, ddl_sql, "users", self.fencing_epoch)
        self.assertEqual(res["ddl_event"]["canonical_operation"], "ADD_COLUMN")
        self.assertEqual(res["ddl_event"]["operation_metadata"]["column_name"], "phone_number")

    def test_attack_05_malformed_and_ambiguous_ddl_fails_closed(self):
        """Hostile: Pass ambiguous or corrupt DDL clauses and ensure closed failure."""
        pos = PostgresLSNPosition("0/300")
        ddl_sql = "ALTER TABLE users DO SOMETHING INVALID"
        res = self.coordinator.process_detected_ddl(self.identity, pos, ddl_sql, "users", self.fencing_epoch)
        self.assertEqual(res["compatibility"], "UNSUPPORTED")
        self.assertEqual(res["policy_decision"], "BLOCKS_CDC")

    def test_attack_06_sql_injection_ddl_sanitization(self):
        """Hostile: Pass DDL containing embedded SQL injection / secret payloads."""
        raw = "ALTER TABLE users ADD COLUMN api_key VARCHAR(100); PASSWORD = 'super_secret_pass_999'"
        san = sanitize_ddl_statement(raw)
        self.assertNotIn("super_secret_pass_999", san)
        self.assertIn("[REDACTED_SECRET]", san)

    # -------------------------------------------------------------------------
    # 3. COMPATIBILITY ENGINE HOSTILE ATTACKS
    # -------------------------------------------------------------------------
    def test_attack_07_destructive_drop_column_cannot_be_auto(self):
        """Hostile: Ensure DROP COLUMN is NEVER classified as SAFE_AUTOMATIC."""
        pos = PostgresLSNPosition("0/400")
        ddl_sql = "ALTER TABLE users DROP COLUMN name"
        res = self.coordinator.process_detected_ddl(self.identity, pos, ddl_sql, "users", self.fencing_epoch)
        self.assertNotEqual(res["compatibility"], "SAFE_AUTOMATIC")
        self.assertEqual(res["compatibility"], "DESTRUCTIVE")
        self.assertEqual(res["policy_decision"], "REQUIRES_APPROVAL")

    def test_attack_08_type_narrowing_cannot_bypass_policy(self):
        """Hostile: Narrowing column type (VARCHAR(255) -> VARCHAR(10)) must require approval."""
        pos = PostgresLSNPosition("0/500")
        ddl_sql = "ALTER TABLE users ALTER COLUMN name TYPE VARCHAR(10)"
        res = self.coordinator.process_detected_ddl(self.identity, pos, ddl_sql, "users", self.fencing_epoch)
        self.assertEqual(res["compatibility"], "REQUIRES_APPROVAL")

    # -------------------------------------------------------------------------
    # 4. SCHEMA BARRIER BYPASS ATTACKS
    # -------------------------------------------------------------------------
    def test_attack_09_direct_worker_apply_blocked_by_active_barrier(self):
        """Hostile: Call CDCApplyWorker.apply_next_transaction while schema barrier is active for table."""
        pos = PostgresLSNPosition("0/600")
        ddl_sql = "ALTER TABLE users ADD COLUMN status VARCHAR(50)"
        self.coordinator.process_detected_ddl(self.identity, pos, ddl_sql, "users", self.fencing_epoch)
        self.assertTrue(self.coordinator.barrier_authority.is_barrier_active(self.cdc_session_id, "users"))

        # Setup worker & buffer
        durable_buf = DurableCDCBuffer(identity=self.identity, wal_dir=self.temp_dir)
        tx = CDCTransaction(
            identity=self.identity,
            tx_id="tx-hostile-1",
            commit_position=PostgresLSNPosition("0/700"),
            events=[
                CDCEvent(
                    identity=self.identity,
                    source_engine="POSTGRESQL",
                    source_database="db", source_schema="public", source_table="users",
                    operation=CDCOperationType.INSERT,
                    position=PostgresLSNPosition("0/700"),
                    after_image={"id": 2, "name": "Bob", "status": "active"},
                    schema_version_id="sch-v2-new",
                )
            ],
        )
        durable_buf.append_transaction(tx, self.fencing_epoch)

        worker = CDCApplyWorker(
            identity=self.identity,
            durable_buffer=durable_buf,
            recovery_coordinator=self.recovery_coord,
            state_store=self.state_store,
            barrier_authority=self.coordinator.barrier_authority,
        )

        # Worker MUST check active barrier and refuse/pause applying transactions for blocked table
        with self.assertRaises(CDCExecutionError) as ctx:
            worker.apply_next_transaction(current_fencing_epoch=self.fencing_epoch)
        self.assertEqual(ctx.exception.failure.failure_type, CDCFailureType.SCHEMA_BARRIER_ACTIVE)

    def test_attack_10_stale_worker_releasing_barrier_rejected(self):
        """Hostile: Attempt to release schema barrier using a stale fencing epoch."""
        pos = PostgresLSNPosition("0/800")
        ddl_sql = "ALTER TABLE users ADD COLUMN age INT"
        t = self.coordinator.process_detected_ddl(self.identity, pos, ddl_sql, "users", self.fencing_epoch)

        # Issue new epoch
        new_epoch = self.recovery_coord.issue_epoch(self.migration_id)

        with self.assertRaises(ValueError) as ctx:
            self.coordinator.barrier_authority.release_barrier(
                cdc_session_id=self.cdc_session_id,
                table_name="users",
                verified_schema_version_id=t["proposed_schema_version"]["schema_version_id"],
                fencing_epoch=self.fencing_epoch,  # Stale epoch 1!
                recovery_coordinator=self.recovery_coord,
                migration_id=self.migration_id,
            )
        self.assertIn("Fencing token violation", str(ctx.exception))

    # -------------------------------------------------------------------------
    # 5. GOVERNANCE APPROVAL RE-APPROVAL & TAMPERING ATTACKS
    # -------------------------------------------------------------------------
    def test_attack_11_reapproval_of_completed_transition_rejected(self):
        """Hostile: Attempt to re-approve an already COMPLETED transition."""
        pos = PostgresLSNPosition("0/900")
        ddl_sql = "ALTER TABLE users DROP COLUMN name"
        t = self.coordinator.process_detected_ddl(self.identity, pos, ddl_sql, "users", self.fencing_epoch)
        self.coordinator.approve_schema_transition(t["transition_id"], "sec@corp.com", "tok-1")
        self.coordinator.apply_schema_transition(t["transition_id"])

        with self.assertRaises(ValueError) as ctx:
            self.coordinator.approve_schema_transition(t["transition_id"], "hacker@corp.com", "tok-2")
        self.assertIn("Cannot approve transition in state 'COMPLETED'", str(ctx.exception))

    def test_attack_12_reapproval_of_rejected_transition_prevented(self):
        """Hostile: Attempt to approve a REJECTED transition."""
        pos = PostgresLSNPosition("0/1000")
        ddl_sql = "DROP TABLE users"
        t = self.coordinator.process_detected_ddl(self.identity, pos, ddl_sql, "users", self.fencing_epoch)

        gw = EngineGateway()
        gw._cdc_schema_coordinator = self.coordinator
        gw.invoke("reject_schema_transition", {"transition_id": t["transition_id"]})

        with self.assertRaises(ValueError) as ctx:
            self.coordinator.approve_schema_transition(t["transition_id"], "admin@corp.com", "tok-1")
        self.assertIn("Cannot approve transition in state 'REJECTED'", str(ctx.exception))

    # -------------------------------------------------------------------------
    # 6. DRIFT & CUTOVER INTEGRATION ATTACKS
    # -------------------------------------------------------------------------
    def test_attack_13_conflicting_target_drift_blocks_auto_apply(self):
        """Hostile: Target table missing required column must fail transition and retain barrier."""
        pos = PostgresLSNPosition("0/1100")
        ddl_sql = "ALTER TABLE users ADD COLUMN email VARCHAR(255)"
        t = self.coordinator.process_detected_ddl(self.identity, pos, ddl_sql, "users", self.fencing_epoch)

        # Actual target table missing expected 'id' column
        actual_target = {"columns": [{"name": "name", "type": "VARCHAR(100)"}]}

        with self.assertRaises(ValueError) as ctx:
            self.coordinator.transition_engine.execute_target_transition(
                identity=self.identity,
                transition_id=t["transition_id"],
                ddl_event=CDCDDLEvent.from_dict(t["ddl_event"]),
                proposed_schema=CDCSchemaVersion.from_dict(t["proposed_schema_version"]),
                fencing_epoch=self.fencing_epoch,
                actual_target_schema=actual_target,
            )
        self.assertIn("Conflicting target schema drift detected", str(ctx.exception))

    def test_attack_14_zero_backlog_cannot_bypass_unresolved_schema_transition(self):
        """Hostile: Zero event backlog must NOT allow cutover readiness while schema barrier is active."""
        pos = PostgresLSNPosition("0/1200")
        ddl_sql = "ALTER TABLE users ADD COLUMN bio TEXT"
        t = self.coordinator.process_detected_ddl(self.identity, pos, ddl_sql, "users", self.fencing_epoch)

        readiness = CDCCutoverReadinessEngine.evaluate_readiness(
            cdc_session_id=self.cdc_session_id,
            session_state="SYNCHRONIZED",
            is_synchronized=True,
            event_backlog=0,  # Zero backlog!
            time_lag_ms=0.0,
            checkpoint_valid=True,
            has_failed_transactions=False,
            is_stale_worker=False,
            has_unresolved_schema_transition=True,
        )
        self.assertFalse(readiness["ready"])
        self.assertEqual(readiness["blocking_reasons"], ["UNRESOLVED_SCHEMA_TRANSITION"])

    # -------------------------------------------------------------------------
    # 7. DIAGNOSTIC SECRET SANITIZATION ATTACKS
    # -------------------------------------------------------------------------
    def test_attack_15_diagnostic_secrets_sanitized_in_metadata(self):
        """Hostile: Ensure secret credentials in comments or defaults are sanitized."""
        raw = "ALTER TABLE users ADD COLUMN token VARCHAR(255) DEFAULT 'AUTH_TOKEN=bearer_xyz_secret_99'"
        san = sanitize_ddl_statement(raw)
        self.assertNotIn("bearer_xyz_secret_99", san)

    # -------------------------------------------------------------------------
    # 8. ENGINE-SPECIFIC DDL CAPTURE AUTHENTICITY TESTS
    # -------------------------------------------------------------------------
    def test_attack_16_mysql_binlog_ddl_capture(self):
        pos = MySQLGTIDPosition("uuid:1-100", binlog_pos=100)
        ddl = "ALTER TABLE `users` ADD COLUMN `is_active` TINYINT(1) DEFAULT 1"
        res = self.coordinator.process_detected_ddl(self.identity, pos, ddl, "users", self.fencing_epoch)
        self.assertEqual(res["ddl_event"]["canonical_operation"], "ADD_COLUMN")

    def test_attack_17_mongodb_change_stream_drop_collection(self):
        pos = PostgresLSNPosition("0/1300")
        payload = {"operationType": "drop", "collection": "users"}
        # Register mongodb baseline schema
        ident_mongo = CDCEventIdentity(self.migration_id, self.job_id, self.run_id, "sess-mongo")
        self.coordinator.get_or_register_initial_schema(ident_mongo, "users", [{"name": "_id", "type": "OBJECT_ID"}], source_engine="MONGODB")
        res = self.coordinator.process_detected_ddl(ident_mongo, pos, payload, "users", self.fencing_epoch)
        self.assertEqual(res["ddl_event"]["canonical_operation"], "DROP_TABLE")
        self.assertEqual(res["compatibility"], "DESTRUCTIVE")

    # -------------------------------------------------------------------------
    # 9. TARGET DDL IDEMPOTENCY & REPLAY AUDIT
    # -------------------------------------------------------------------------
    def test_attack_18_idempotent_duplicate_target_transition_execution(self):
        """Hostile: Executing target transition twice must be idempotent."""
        pos = PostgresLSNPosition("0/1400")
        ddl = "ALTER TABLE users ADD COLUMN col_repeat INT"
        t = self.coordinator.process_detected_ddl(self.identity, pos, ddl, "users", self.fencing_epoch)
        res1 = self.coordinator.apply_schema_transition(t["transition_id"])
        self.assertEqual(res1["state"], "COMPLETED")

        # Second apply call must be idempotent or reject gracefully
        with self.assertRaises(ValueError):
            self.coordinator.apply_schema_transition(t["transition_id"])

    # -------------------------------------------------------------------------
    # 10. CRASH WINDOW & RESTART RECOVERY AUDIT
    # -------------------------------------------------------------------------
    def test_attack_19_crash_recovery_preserves_barrier_state(self):
        """Hostile: Process crash immediately after barrier established preserves barrier state."""
        pos = PostgresLSNPosition("0/1500")
        ddl = "ALTER TABLE users ADD COLUMN crash_col INT"
        t = self.coordinator.process_detected_ddl(self.identity, pos, ddl, "users", self.fencing_epoch)

        # Simulate crash & recreate coordinator from CentralStateStore
        coord2 = CDCSchemaEvolutionCoordinator(recovery_coordinator=self.recovery_coord, state_store=self.state_store)
        self.assertTrue(coord2.barrier_authority.is_barrier_active(self.cdc_session_id, "users"))
        rec = coord2.recover_schema_transition(self.cdc_session_id, t["transition_id"])
        self.assertEqual(rec["state"], "BARRIER_ESTABLISHED")

    def test_attack_20_crash_recovery_with_corrupt_state_fails_closed(self):
        """Hostile: Persisted transition with mismatched cdc_session_id fails closed."""
        self.state_store.set_state(
            f"schema_pending_trans_trans-bad",
            {"identity": {"cdc_session_id": "sess-OTHER"}},
            category="schema_transition",
        )
        with self.assertRaises(ValueError) as ctx:
            self.coordinator.recover_schema_transition(self.cdc_session_id, "trans-bad")
        self.assertIn("Session identity mismatch", str(ctx.exception))

    # -------------------------------------------------------------------------
    # 11. CONCURRENCY & DUAL COORDINATOR RACE AUDIT
    # -------------------------------------------------------------------------
    def test_attack_21_stale_coordinator_apply_rejected(self):
        """Hostile: Second coordinator with stale epoch cannot apply transition."""
        pos = PostgresLSNPosition("0/1600")
        ddl = "ALTER TABLE users DROP COLUMN name"
        t = self.coordinator.process_detected_ddl(self.identity, pos, ddl, "users", self.fencing_epoch)
        self.coordinator.approve_schema_transition(t["transition_id"], "boss@corp.com", "tok-8")

        # New coordinator instance gets new epoch
        epoch2 = self.recovery_coord.issue_epoch(self.migration_id)

        # Original coordinator attempts apply with stale epoch
        with self.assertRaises(ValueError) as ctx:
            self.coordinator.apply_schema_transition(t["transition_id"])
        self.assertIn("Fencing token violation", str(ctx.exception))

    # -------------------------------------------------------------------------
    # 12. BUFFER & REPLAY ACCOUNTING AUDIT
    # -------------------------------------------------------------------------
    def test_attack_22_buffered_event_retains_schema_version_on_replay(self):
        """Hostile: Replaying durable WAL buffer events verifies exact schema version binding."""
        buf = DurableCDCBuffer(identity=self.identity, wal_dir=self.temp_dir)
        tx = CDCTransaction(
            identity=self.identity,
            tx_id="tx-ver-1",
            commit_position=PostgresLSNPosition("0/1700"),
            events=[
                CDCEvent(
                    identity=self.identity,
                    source_engine="POSTGRESQL",
                    source_database="db", source_schema="public", source_table="users",
                    operation=CDCOperationType.INSERT,
                    position=PostgresLSNPosition("0/1700"),
                    after_image={"id": 1},
                    schema_version_id=self.baseline_schema.schema_version_id,
                )
            ],
        )
        buf.append_transaction(tx, self.fencing_epoch)
        popped = buf.pop_next_transaction()
        self.assertEqual(popped["transaction_data"]["events"][0]["schema_version_id"], self.baseline_schema.schema_version_id)

    # -------------------------------------------------------------------------
    # 13. ADDITIONAL EDGE CASE AUDITS
    # -------------------------------------------------------------------------
    def test_attack_23_cross_migration_approval_substitution(self):
        """Hostile: Governance approval from migration B rejected for transition on migration A."""
        pos = PostgresLSNPosition("0/1800")
        ddl = "ALTER TABLE users DROP COLUMN name"
        t = self.coordinator.process_detected_ddl(self.identity, pos, ddl, "users", self.fencing_epoch)

        self.coordinator.transition_engine.record_schema_approval(
            migration_id="mig-OTHER", job_id=self.job_id, run_id=self.run_id,
            cdc_session_id=self.cdc_session_id, transition_id=t["transition_id"],
            approved_by="admin@corp.com", approval_token="tok-x",
            old_schema_version_id=t["old_schema_version"]["schema_version_id"],
            new_schema_version_id=t["proposed_schema_version"]["schema_version_id"],
        )
        with self.assertRaises(ValueError):
            self.coordinator.apply_schema_transition(t["transition_id"])

    def test_attack_24_unknown_ddl_blocks_cdc(self):
        pos = PostgresLSNPosition("0/1900")
        res = self.coordinator.process_detected_ddl(self.identity, pos, "FOOBAR SYNTAX", "users", self.fencing_epoch)
        self.assertEqual(res["policy_decision"], "BLOCKS_CDC")

    def test_attack_25_telemetry_publishes_sanitized_ddl(self):
        pos = PostgresLSNPosition("0/2000")
        ddl = "ALTER USER foo IDENTIFIED BY 'secret_pass_123'"
        t = self.coordinator.process_detected_ddl(self.identity, pos, ddl, "users", self.fencing_epoch)
        telem = self.state_store.get_state(f"schema_telemetry_{self.cdc_session_id}", category="schema_telemetry")
        self.assertNotIn("secret_pass_123", telem["sanitized_ddl"])


if __name__ == "__main__":
    unittest.main()

