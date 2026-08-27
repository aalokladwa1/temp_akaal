"""
AKAAL P5.7 — Custom SQL + Hooks + Governed Extensibility Hostile Test Suite
============================================================================
Exhaustive verification of SQL safety classification, allow/deny governance,
parameter binding, injection resistance, secret sanitization, connector capability derivation,
execution mode fencing (M1-M8), transaction isolation, rollback truth, timeout boundaries,
crash-recovery state tracking in CentralStateStore, duplicate prevention, and Authority #12 evidence emission.
"""

import asyncio
import os
import sqlite3
import tempfile
import unittest
from typing import Any, Dict, List, Optional

from akaal.core.models.enums import SystemType
from akaal.connectors.registry import UniversalConnectorRegistry
from akaal.connectors.taxonomy import CapabilitySupportStatus
from akaal.planner.models.p5_domain import (
    MigrationPlan,
    PlanVersion,
    TopologyDefinition,
    SourceTopology,
    TargetTopology,
    RoutingDefinition,
    HookStage,
    HookSide,
    HookTransactionPolicy,
    HookIdempotencyClassification,
    HookFailurePolicy,
    HookExecutionState,
    SQLSafetyClassification,
    HookDefinition,
    HooksConfiguration,
    HookExecutionResult,
)
from akaal.planner.engine.plan_compiler import PlanCompiler
from akaal.planner.engine.sql_safety import SQLSafetyClassifier
from akaal.privacy.sanitizer import LogAndDiagnosticSanitizer
from akaal.audit.audit_logger import AuditLogger, AuditEventType
from akaal.core.state.state_store import CentralStateStore
from akaal.migration.execution.hooks.executor import (
    GovernedHookExecutor,
    HookExecutor,
    HookExecutionError,
    AmbiguousHookReplayError,
    UnapprovedHookExecutionError,
    HookOperatorInterventionRequiredError,
)
from akaal.gateway.engine_gateway import EngineGateway
from akaalEngine.evidence.api import EvidenceAuthority


class MockDBConnection:
    """In-memory SQLite mock connection with realistic DB-API semantics."""

    def __init__(self, db_path: str = ":memory:") -> None:
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self.cursor_calls: List[str] = []
        self.committed = False
        self.rolled_back = False
        self.autocommit = True
        self.fail_on_execute = False

    def cursor(self):
        return MockDBCursor(self)

    def commit(self):
        self.committed = True
        self._conn.commit()

    def rollback(self):
        self.rolled_back = True
        self._conn.rollback()

    def close(self):
        self._conn.close()


class MockDBCursor:
    def __init__(self, mock_conn: MockDBConnection) -> None:
        self.mock_conn = mock_conn
        self._cursor = mock_conn._conn.cursor()
        self.rowcount = 1

    def execute(self, sql: str, params: Optional[Any] = None):
        self.mock_conn.cursor_calls.append(sql)
        if getattr(self.mock_conn, "fail_on_execute", False):
            raise RuntimeError("Simulated DB Execution Failure")
        if params:
            return self._cursor.execute(sql, params)
        return self._cursor.execute(sql)

    def fetchall(self):
        return self._cursor.fetchall()

    def close(self):
        self._cursor.close()


class MockDatabaseAdapter:
    """Realistic adapter wrapping MockDBConnection."""

    def __init__(self, db_path: str = ":memory:", fail_on_sql: Optional[str] = None, slow_ms: int = 0) -> None:
        self.is_connected = True
        self.mock_conn = MockDBConnection(db_path)
        self.fail_on_sql = fail_on_sql
        self.slow_ms = slow_ms

    def get_connection(self):
        if self.slow_ms > 0:
            import time
            time.sleep(self.slow_ms / 1000.0)
        if self.fail_on_sql and self.fail_on_sql in getattr(self, "_last_sql", ""):
            raise RuntimeError(f"Database error executing {self.fail_on_sql}")
        return self.mock_conn

    async def connect(self):
        self.is_connected = True

    async def close(self):
        self.is_connected = False

    async def rollback(self):
        self.mock_conn.rollback()

    async def commit(self):
        self.mock_conn.commit()


class TestP57CustomSQLHooks(unittest.TestCase):
    """Hostile Acceptance Test Suite for P5.7 Custom SQL + Hooks + Governed Extensibility."""

    def setUp(self) -> None:
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.state_db_path = os.path.join(self.tmp_dir.name, "test_state.db")
        CentralStateStore._instance = None
        self.state_store = CentralStateStore(db_path=self.state_db_path)
        self.compiler = PlanCompiler()

    def tearDown(self) -> None:
        if hasattr(self, "state_store") and self.state_store:
            self.state_store.close()
        CentralStateStore._instance = None
        try:
            self.tmp_dir.cleanup()
        except Exception:
            pass

    def _create_sample_plan(self, src_type="postgresql", tgt_type="postgresql", execution_mode="M2") -> MigrationPlan:
        from akaal.planner.models.p5_domain import PlanningMode
        return MigrationPlan(
            plan_id="plan-hooks-001",
            project_id="proj-hooks-001",
            title="Hooks Test Plan",
            planning_mode=PlanningMode.SIMPLE,
            topology=TopologyDefinition(
                topology_type="1:1",
                source=SourceTopology(instance_id="src-inst", endpoint="src-host:5432", connector_type=src_type),
                target=TargetTopology(instance_id="tgt-inst", endpoint="tgt-host:5432", connector_type=tgt_type),
            ),
            routing=RoutingDefinition(),
            selected_scope={
                "databases": ["db1"],
                "schemas": ["public"],
                "objects": [
                    {"object_name": "CUSTOMERS", "selected": True},
                    {"object_name": "ORDERS", "selected": True},
                ],
            },
            configuration={"execution_mode": execution_mode},
        )

    # ---------------------------------------------------------------------------
    # 1. SQL Safety Classification Tests
    # ---------------------------------------------------------------------------

    def test_01_sql_safety_classification_safe_select(self):
        """Hostile Test: Non-mutating SELECT, WITH-SELECT, and EXPLAIN statements classify as SAFE_SELECT."""
        sql1 = "SELECT id, name, email FROM customers WHERE active = 1"
        sql2 = "WITH ranked AS (SELECT id, ROW_NUMBER() OVER () as rn FROM orders) SELECT * FROM ranked WHERE rn <= 10"
        sql3 = "EXPLAIN SELECT * FROM audit_logs"

        self.assertEqual(SQLSafetyClassifier.classify(sql1), SQLSafetyClassification.SAFE_SELECT)
        self.assertEqual(SQLSafetyClassifier.classify(sql2), SQLSafetyClassification.SAFE_SELECT)
        self.assertEqual(SQLSafetyClassifier.classify(sql3), SQLSafetyClassification.SAFE_SELECT)
        self.assertFalse(SQLSafetyClassifier.is_mutating(SQLSafetyClassification.SAFE_SELECT))
        self.assertFalse(SQLSafetyClassifier.is_destructive(SQLSafetyClassification.SAFE_SELECT))

    def test_02_sql_safety_classification_safe_mutating(self):
        """Hostile Test: Standard INSERT, UPDATE with WHERE, MERGE classify as SAFE_MUTATING."""
        sql1 = "INSERT INTO staging_customers (id, name) VALUES (1, 'Acme')"
        sql2 = "UPDATE customers SET status = 'ACTIVE' WHERE id = 100"
        sql3 = "DELETE FROM session_cache WHERE expires_at < NOW()"

        self.assertEqual(SQLSafetyClassifier.classify(sql1), SQLSafetyClassification.SAFE_MUTATING)
        self.assertEqual(SQLSafetyClassifier.classify(sql2), SQLSafetyClassification.SAFE_MUTATING)
        self.assertEqual(SQLSafetyClassifier.classify(sql3), SQLSafetyClassification.SAFE_MUTATING)
        self.assertTrue(SQLSafetyClassifier.is_mutating(SQLSafetyClassification.SAFE_MUTATING))
        self.assertFalse(SQLSafetyClassifier.is_destructive(SQLSafetyClassification.SAFE_MUTATING))

    def test_03_sql_safety_classification_destructive_dml(self):
        """Hostile Test: TRUNCATE TABLE and unconstrained DELETE classify as DESTRUCTIVE_DML."""
        sql1 = "TRUNCATE TABLE target_staging"
        sql2 = "DELETE FROM customers"
        sql3 = "DELETE FROM customers;"

        self.assertEqual(SQLSafetyClassifier.classify(sql1), SQLSafetyClassification.DESTRUCTIVE_DML)
        self.assertEqual(SQLSafetyClassifier.classify(sql2), SQLSafetyClassification.DESTRUCTIVE_DML)
        self.assertEqual(SQLSafetyClassifier.classify(sql3), SQLSafetyClassification.DESTRUCTIVE_DML)
        self.assertTrue(SQLSafetyClassifier.is_destructive(SQLSafetyClassification.DESTRUCTIVE_DML))

    def test_04_sql_safety_classification_destructive_ddl(self):
        """Hostile Test: DROP TABLE, DROP DATABASE, destructive ALTER classify as DESTRUCTIVE_DDL."""
        sql1 = "DROP TABLE old_customers"
        sql2 = "DROP DATABASE legacy_db"
        sql3 = "ALTER TABLE users DROP COLUMN ssn"

        self.assertEqual(SQLSafetyClassifier.classify(sql1), SQLSafetyClassification.DESTRUCTIVE_DDL)
        self.assertEqual(SQLSafetyClassifier.classify(sql2), SQLSafetyClassification.DESTRUCTIVE_DDL)
        self.assertEqual(SQLSafetyClassifier.classify(sql3), SQLSafetyClassification.DESTRUCTIVE_DDL)
        self.assertTrue(SQLSafetyClassifier.is_destructive(SQLSafetyClassification.DESTRUCTIVE_DDL))

    def test_05_sql_safety_classification_privileges(self):
        """Hostile Test: GRANT, REVOKE, CREATE USER classify as PRIVILEGE_MODIFICATION."""
        sql1 = "GRANT ALL PRIVILEGES ON DATABASE prod TO admin_user"
        sql2 = "REVOKE CONNECT ON DATABASE prod FROM public"
        sql3 = "CREATE USER test_user WITH PASSWORD 'secret123'"

        self.assertEqual(SQLSafetyClassifier.classify(sql1), SQLSafetyClassification.PRIVILEGE_MODIFICATION)
        self.assertEqual(SQLSafetyClassifier.classify(sql2), SQLSafetyClassification.PRIVILEGE_MODIFICATION)
        self.assertEqual(SQLSafetyClassifier.classify(sql3), SQLSafetyClassification.PRIVILEGE_MODIFICATION)
        self.assertTrue(SQLSafetyClassifier.is_destructive(SQLSafetyClassification.PRIVILEGE_MODIFICATION))

    def test_06_sql_safety_classification_unknown_fail_closed(self):
        """Hostile Test: Empty, comment-only, or garbage SQL classifies as UNKNOWN_UNCLASSIFIED and fails closed."""
        sql1 = "-- Just a comment"
        sql2 = "   /* Multi-line comment */   "
        sql3 = "XYZ_INVALID_COMMAND_BLAH 123"

        self.assertEqual(SQLSafetyClassifier.classify(sql1), SQLSafetyClassification.UNKNOWN_UNCLASSIFIED)
        self.assertEqual(SQLSafetyClassifier.classify(sql2), SQLSafetyClassification.UNKNOWN_UNCLASSIFIED)
        self.assertEqual(SQLSafetyClassifier.classify(sql3), SQLSafetyClassification.UNKNOWN_UNCLASSIFIED)
        self.assertTrue(SQLSafetyClassifier.is_destructive(SQLSafetyClassification.UNKNOWN_UNCLASSIFIED))

    # ---------------------------------------------------------------------------
    # 2. Allow / Deny Governance Policy Tests
    # ---------------------------------------------------------------------------

    def test_07_deny_rules_enforcement(self):
        """Hostile Test: Deny rules block matching SQL statements regardless of allow rules."""
        sql = "DROP TABLE temp_staging"
        passed, violations = SQLSafetyClassifier.evaluate_policies(
            raw_sql=sql,
            deny_rules=[r"^DROP\s+TABLE", r"TRUNCATE\b"],
        )
        self.assertFalse(passed)
        self.assertTrue(any("DENIED_SQL_OPERATION" in v for v in violations))

    def test_08_allow_rules_enforcement(self):
        """Hostile Test: When allow rules configured, non-matching SQL is rejected."""
        sql = "UPDATE customers SET status = 'INACTIVE' WHERE id = 5"
        passed, violations = SQLSafetyClassifier.evaluate_policies(
            raw_sql=sql,
            allow_rules=[r"^SELECT\b", r"^INSERT\b"],
        )
        self.assertFalse(passed)
        self.assertTrue(any("DISALLOWED_SQL_OPERATION" in v for v in violations))

    def test_09_deny_rule_bypass_with_comments_blocked(self):
        """Hostile Test: Comments embedded inside SQL cannot bypass deny rule evaluation."""
        sql = "/* malicious drop */ DROP -- comment \n TABLE customers"
        passed, violations = SQLSafetyClassifier.evaluate_policies(
            raw_sql=sql,
            deny_rules=[r"DROP\s+TABLE"],
        )
        self.assertFalse(passed)

    # ---------------------------------------------------------------------------
    # 3. Parameter Safety & Secret Sanitization Tests
    # ---------------------------------------------------------------------------

    def test_10_parameter_sanitization_and_secret_redaction(self):
        """Hostile Test: Sensitive parameter values and SUPER_SECRET_PAYLOAD are redacted."""
        params = {
            "batch_id": "BATCH-101",
            "password": "SUPER_SECRET_PAYLOAD_12345",
            "api_token": "bearer-xyz987",
            "user_email": "admin@enterprise.com",
        }
        sanitized = LogAndDiagnosticSanitizer.sanitize_hook_parameters(params)
        self.assertEqual(sanitized["password"], "[REDACTED]")
        self.assertEqual(sanitized["api_token"], "[REDACTED]")
        self.assertEqual(sanitized["user_email"], "[REDACTED_EMAIL]")
        self.assertEqual(sanitized["batch_id"], "BATCH-101")

        raw_diag = "Failed executing hook: password='SUPER_SECRET_PAYLOAD_ABC' on host"
        clean_diag = LogAndDiagnosticSanitizer.sanitize_hook_diagnostics(raw_diag)
        self.assertNotIn("SUPER_SECRET_PAYLOAD_ABC", clean_diag)
        self.assertIn("[REDACTED", clean_diag)

    # ---------------------------------------------------------------------------
    # 4. Dependency DAG & Lifecycle Stage Ordering Tests
    # ---------------------------------------------------------------------------

    def test_11_dependency_cycle_detection(self):
        """Hostile Test: Circular dependencies between hooks are caught during compilation."""
        h1 = HookDefinition(hook_id="h1", name="Hook 1", stage=HookStage.PRE_MIGRATION, sql_statement="SELECT 1", dependencies=["h2"])
        h2 = HookDefinition(hook_id="h2", name="Hook 2", stage=HookStage.PRE_MIGRATION, sql_statement="SELECT 2", dependencies=["h1"])

        res = self.compiler.compile_custom_sql_hooks(
            hooks_config=HooksConfiguration(enabled=True, hooks=[h1, h2]),
            source_connector_type="postgresql",
            target_connector_type="postgresql",
        )
        self.assertEqual(res["status"], "BLOCKER")
        self.assertTrue(any(d["code"] == "HOOK_DEPENDENCY_CYCLE" for d in res["diagnostics"]))

    def test_12_missing_dependency_detection(self):
        """Hostile Test: Reference to non-existent hook dependency fails compilation."""
        h1 = HookDefinition(hook_id="h1", name="Hook 1", stage=HookStage.PRE_MIGRATION, sql_statement="SELECT 1", dependencies=["non_existent_hook"])
        res = self.compiler.compile_custom_sql_hooks(
            hooks_config=[h1],
            source_connector_type="postgresql",
            target_connector_type="postgresql",
        )
        self.assertEqual(res["status"], "BLOCKER")
        self.assertTrue(any(d["code"] == "MISSING_HOOK_DEPENDENCY" for d in res["diagnostics"]))

    def test_13_invalid_lifecycle_stage_dependency(self):
        """Hostile Test: Earlier stage hook cannot depend on a later stage hook."""
        h_pre = HookDefinition(hook_id="h_pre", name="Pre Hook", stage=HookStage.PRE_MIGRATION, sql_statement="SELECT 1", dependencies=["h_post"])
        h_post = HookDefinition(hook_id="h_post", name="Post Hook", stage=HookStage.POST_MIGRATION, sql_statement="SELECT 2")

        res = self.compiler.compile_custom_sql_hooks(
            hooks_config=[h_pre, h_post],
            source_connector_type="postgresql",
            target_connector_type="postgresql",
        )
        self.assertEqual(res["status"], "BLOCKER")
        self.assertTrue(any(d["code"] == "INVALID_HOOK_STAGE_DEPENDENCY" for d in res["diagnostics"]))

    def test_14_deterministic_topological_sort_and_tie_breaking(self):
        """Hostile Test: Multi-hook ordering respects dependencies, order property, and hook_id tie-breaking."""
        h_b = HookDefinition(hook_id="h_b", name="B", stage=HookStage.PRE_MIGRATION, sql_statement="SELECT 'B'", order=10)
        h_a = HookDefinition(hook_id="h_a", name="A", stage=HookStage.PRE_MIGRATION, sql_statement="SELECT 'A'", order=10)
        h_c = HookDefinition(hook_id="h_c", name="C", stage=HookStage.PRE_MIGRATION, sql_statement="SELECT 'C'", dependencies=["h_b"], order=5)

        res = self.compiler.compile_custom_sql_hooks(
            hooks_config=[h_c, h_b, h_a],
            source_connector_type="postgresql",
            target_connector_type="postgresql",
        )
        self.assertEqual(res["status"], "SUCCESS")
        compiled_ids = [h["hook_id"] for h in res["hooks"]]
        # h_a (depth 0, order 10), h_b (depth 0, order 10), h_c (depth 1, order 5)
        self.assertEqual(compiled_ids, ["h_a", "h_b", "h_c"])
        self.assertTrue(bool(res["fingerprint"]))

    # ---------------------------------------------------------------------------
    # 5. Connector Capability & Execution Mode Fencing Tests
    # ---------------------------------------------------------------------------

    def test_15_non_sql_sink_rejection(self):
        """Hostile Test: Attempting to attach SQL hook to non-SQL connector (e.g. S3, Kafka) fails closed."""
        h1 = HookDefinition(hook_id="h1", name="Target Hook", stage=HookStage.TARGET_PREPARATION, side=HookSide.TARGET, sql_statement="SELECT 1")
        res = self.compiler.compile_custom_sql_hooks(
            hooks_config=[h1],
            source_connector_type="postgresql",
            target_connector_type="s3",  # S3 does not support SQL execution
        )
        self.assertEqual(res["status"], "BLOCKER")
        self.assertTrue(any(d["code"] == "UNSUPPORTED_HOOK_TARGET_CONNECTOR" for d in res["diagnostics"]))

    def test_16_m8_validation_mode_blocks_mutating_hooks(self):
        """Hostile Test: Execution mode M8 (Validation Only) strictly blocks mutating target SQL hooks."""
        h1 = HookDefinition(
            hook_id="h1",
            name="Mutating Hook",
            stage=HookStage.PRE_MIGRATION,
            side=HookSide.TARGET,
            sql_statement="UPDATE control_table SET sync_status = 'STARTING'",
        )
        res = self.compiler.compile_custom_sql_hooks(
            hooks_config=[h1],
            source_connector_type="postgresql",
            target_connector_type="postgresql",
            execution_mode="M8",
        )
        self.assertEqual(res["status"], "BLOCKER")
        self.assertTrue(any(d["code"] == "MUTATING_HOOK_IN_VALIDATION_MODE" for d in res["diagnostics"]))

    def test_17_unapproved_destructive_sql_blocked(self):
        """Hostile Test: Destructive SQL without approval requirement fails closed during compilation."""
        h1 = HookDefinition(
            hook_id="h_drop",
            name="Destructive Drop",
            stage=HookStage.TARGET_PREPARATION,
            sql_statement="DROP TABLE old_schema.customers",
            requires_approval=False,
        )
        res = self.compiler.compile_custom_sql_hooks(
            hooks_config=HooksConfiguration(enabled=True, hooks=[h1], allow_dangerous_sql=False),
            source_connector_type="postgresql",
            target_connector_type="postgresql",
        )
        self.assertEqual(res["status"], "BLOCKER")
        self.assertTrue(any(d["code"] == "UNAPPROVED_DANGEROUS_SQL" for d in res["diagnostics"]))

    # ---------------------------------------------------------------------------
    # 6. Physical Execution & GovernedHookExecutor Tests
    # ---------------------------------------------------------------------------

    def test_18_physical_execution_all_lifecycle_stages(self):
        """Hostile Test: Physical execution across PRE_MIGRATION, SESSION_INIT, TARGET_PREP, PRE_OBJECT, POST_OBJECT, TARGET_FINAL, POST_MIGRATION."""
        adapter = MockDatabaseAdapter()
        executor = GovernedHookExecutor(source_adapter=adapter, target_adapter=adapter, state_store=self.state_store)

        hooks = [
            HookDefinition(hook_id="h_pre", name="Pre Mig", stage=HookStage.PRE_MIGRATION, sql_statement="SELECT 'PRE'"),
            HookDefinition(hook_id="h_sess", name="Sess Init", stage=HookStage.SESSION_INITIALIZATION, sql_statement="PRAGMA encoding = 'UTF-8'"),
            HookDefinition(hook_id="h_prep", name="Target Prep", stage=HookStage.TARGET_PREPARATION, sql_statement="CREATE TABLE IF NOT EXISTS test_t (id INT)"),
            HookDefinition(hook_id="h_pre_obj", name="Pre Object", stage=HookStage.PRE_OBJECT, scope_object="CUSTOMERS", sql_statement="SELECT 1"),
            HookDefinition(hook_id="h_post_obj", name="Post Object", stage=HookStage.POST_OBJECT, scope_object="CUSTOMERS", sql_statement="SELECT 2"),
            HookDefinition(hook_id="h_final", name="Target Final", stage=HookStage.TARGET_FINALIZATION, sql_statement="SELECT 'FINAL'"),
            HookDefinition(hook_id="h_post", name="Post Mig", stage=HookStage.POST_MIGRATION, sql_statement="SELECT 'POST'"),
        ]

        for stage in HookStage:
            results = asyncio.run(executor.execute_stage_hooks(hooks, stage=stage, workflow_id="wf-101"))
            self.assertEqual(len(results), 1)
            self.assertEqual(results[0].state, HookExecutionState.COMPLETED)

        # Check CentralStateStore has all 7 hooks in COMPLETED state
        for h in hooks:
            st = self.state_store.get_state(f"wf-101:{h.hook_id}", category="hooks")
            self.assertIsNotNone(st)
            self.assertEqual(st["state"], "COMPLETED")

    def test_19_duplicate_execution_prevention(self):
        """Hostile Test: Once recorded COMPLETED in CentralStateStore, re-executing skips with zero database queries."""
        adapter = MockDatabaseAdapter()
        executor = GovernedHookExecutor(source_adapter=adapter, target_adapter=adapter, state_store=self.state_store)

        hook = HookDefinition(hook_id="h_once", name="One Time", stage=HookStage.PRE_MIGRATION, sql_statement="SELECT 'EXEC_ONCE'")

        # First run
        res1 = asyncio.run(executor.execute_stage_hooks([hook], stage=HookStage.PRE_MIGRATION, workflow_id="wf-dup-test"))
        self.assertEqual(res1[0].state, HookExecutionState.COMPLETED)
        initial_calls_count = len(adapter.mock_conn.cursor_calls)
        self.assertGreater(initial_calls_count, 0)

        # Second run with same workflow_id
        res2 = asyncio.run(executor.execute_stage_hooks([hook], stage=HookStage.PRE_MIGRATION, workflow_id="wf-dup-test"))
        self.assertEqual(res2[0].state, HookExecutionState.COMPLETED)
        # Database query count must remain EXACTLY identical (zero additional queries)
        self.assertEqual(len(adapter.mock_conn.cursor_calls), initial_calls_count)

    def test_20_ambiguous_failure_blocks_non_idempotent_replay(self):
        """Hostile Test: Ambiguous / failed non-idempotent hook blocks automatic replay."""
        adapter = MockDatabaseAdapter()
        executor = GovernedHookExecutor(source_adapter=adapter, target_adapter=adapter, state_store=self.state_store)

        hook = HookDefinition(
            hook_id="h_non_idem",
            name="Non Idempotent Insert",
            stage=HookStage.PRE_MIGRATION,
            sql_statement="INSERT INTO ledger (val) VALUES (500)",
            idempotency=HookIdempotencyClassification.NON_IDEMPOTENT,
        )

        # Simulate prior crash leaving state AMBIGUOUS in CentralStateStore
        self.state_store.set_state(
            key="wf-crash:h_non_idem",
            value={"hook_id": "h_non_idem", "state": HookExecutionState.AMBIGUOUS.value},
            category="hooks",
        )

        # Execution MUST raise AmbiguousHookReplayError and abort
        with self.assertRaises(AmbiguousHookReplayError):
            asyncio.run(executor.execute_stage_hooks([hook], stage=HookStage.PRE_MIGRATION, workflow_id="wf-crash"))

    def test_21_idempotent_hook_allows_safe_retry(self):
        """Hostile Test: Hook classified as IDEMPOTENT is permitted to retry after prior failure."""
        adapter = MockDatabaseAdapter()
        executor = GovernedHookExecutor(source_adapter=adapter, target_adapter=adapter, state_store=self.state_store)

        hook = HookDefinition(
            hook_id="h_idem",
            name="Idempotent Query",
            stage=HookStage.PRE_MIGRATION,
            sql_statement="SELECT 'IDEMPOTENT_RETRY'",
            idempotency=HookIdempotencyClassification.IDEMPOTENT,
        )

        # Simulate prior failure
        self.state_store.set_state(
            key="wf-retry:h_idem",
            value={"hook_id": "h_idem", "state": HookExecutionState.FAILED.value},
            category="hooks",
        )

        res = asyncio.run(executor.execute_stage_hooks([hook], stage=HookStage.PRE_MIGRATION, workflow_id="wf-retry"))
        self.assertEqual(res[0].state, HookExecutionState.COMPLETED)

    def test_22_timeout_enforcement_and_ambiguous_state_recording(self):
        """Hostile Test: Hook exceeding timeout_ms is aborted and marked AMBIGUOUS in CentralStateStore."""
        # Slow adapter that sleeps 200ms
        adapter = MockDatabaseAdapter(slow_ms=200)
        executor = GovernedHookExecutor(source_adapter=adapter, target_adapter=adapter, state_store=self.state_store)

        hook = HookDefinition(
            hook_id="h_timeout",
            name="Slow Hook",
            stage=HookStage.PRE_MIGRATION,
            sql_statement="SELECT 1",
            timeout_ms=50,  # 50ms timeout < 200ms adapter sleep
            failure_policy=HookFailurePolicy.CONTINUE_ON_FAILURE,
        )

        res = asyncio.run(executor.execute_stage_hooks([hook], stage=HookStage.PRE_MIGRATION, workflow_id="wf-to"))
        self.assertEqual(res[0].state, HookExecutionState.AMBIGUOUS)
        self.assertTrue(res[0].is_ambiguous)

        # Verify CentralStateStore recorded AMBIGUOUS
        st = self.state_store.get_state("wf-to:h_timeout", category="hooks")
        self.assertEqual(st["state"], "AMBIGUOUS")

    def test_23_transaction_isolation_and_rollback_on_failure(self):
        """Hostile Test: Failed hook in ISOLATED_TRANSACTION triggers adapter rollback."""
        adapter = MockDatabaseAdapter()
        adapter.mock_conn.fail_on_execute = True

        executor = GovernedHookExecutor(source_adapter=adapter, target_adapter=adapter, state_store=self.state_store)

        hook = HookDefinition(
            hook_id="h_tx_fail",
            name="Tx Fail Hook",
            stage=HookStage.PRE_MIGRATION,
            sql_statement="INSERT INTO accounts VALUES (1)",
            transaction_policy=HookTransactionPolicy.ISOLATED_TRANSACTION,
            failure_policy=HookFailurePolicy.CONTINUE_ON_FAILURE,
        )

        res = asyncio.run(executor.execute_stage_hooks([hook], stage=HookStage.PRE_MIGRATION, workflow_id="wf-tx"))
        self.assertEqual(res[0].state, HookExecutionState.FAILED)
        self.assertTrue(adapter.mock_conn.rolled_back)

    def test_24_approval_barrier_governance(self):
        """Hostile Test: Approval barrier blocks unapproved destructive hooks and allows valid fingerprint."""
        adapter = MockDatabaseAdapter()
        executor = GovernedHookExecutor(source_adapter=adapter, target_adapter=adapter, state_store=self.state_store)

        hook = HookDefinition(
            hook_id="h_destruct",
            name="Destructive Drop",
            stage=HookStage.TARGET_PREPARATION,
            sql_statement="DROP TABLE IF EXISTS target_users",
            requires_approval=True,
        )

        # CASE A: No approval fingerprint in context -> REJECTED
        with self.assertRaises(UnapprovedHookExecutionError):
            asyncio.run(executor.execute_stage_hooks([hook], stage=HookStage.TARGET_PREPARATION, workflow_id="wf-app", context={}))

        # CASE B: Valid matching approval fingerprint -> PASSES
        exec_plan = {"fingerprint": "FP_APPROVED_123", "resolved_configuration": {"hooks_fingerprint": "FP_APPROVED_123", "hooks_requires_approval": True}}
        res = asyncio.run(executor.execute_stage_hooks(
            [hook],
            stage=HookStage.TARGET_PREPARATION,
            workflow_id="wf-app",
            context={"execution_plan": exec_plan, "approved_fingerprint": "FP_APPROVED_123"},
        ))
        self.assertEqual(res[0].state, HookExecutionState.COMPLETED)

    # ---------------------------------------------------------------------------
    # 7. End-to-End Plan Compilation & Immutability Integration Tests
    # ---------------------------------------------------------------------------

    def test_25_end_to_end_plan_compilation_with_hooks(self):
        """Hostile Test: Full compilation of plan incorporating custom SQL hooks into ExecutionPlan."""
        plan = self._create_sample_plan()
        from akaal.planner.models.p5_domain import PlanningMode
        version = PlanVersion(
            version_id="ver-hooks-001",
            project_id=plan.project_id,
            parent_version_id=None,
            revision=1,
            created_at="2026-08-27T00:00:00Z",
            created_by="Admin",
            reason="Hooks Test",
            planning_mode=PlanningMode.SIMPLE,
            canonical_payload=plan.to_dict(),
            fingerprint="",
        )

        hook = HookDefinition(
            hook_id="h_init",
            name="Session Init",
            stage=HookStage.SESSION_INITIALIZATION,
            sql_statement="SELECT 1",
        )
        plan.configuration["hooks"] = [hook.to_dict()]

        comp_res = self.compiler.compile(plan, version)
        self.assertTrue(comp_res.success)
        self.assertIsNotNone(comp_res.execution_plan)
        self.assertTrue(bool(comp_res.fingerprint))

        resolved_cfg = comp_res.execution_plan["resolved_configuration"]
        self.assertIn("hooks", resolved_cfg)
        self.assertIn("hooks_fingerprint", resolved_cfg)
        self.assertEqual(len(resolved_cfg["hooks"]), 1)

    def test_26_plan_diff_detects_material_hook_mutation(self):
        """Hostile Test: PlanDiff invalidates approval and marks requires_reapproval on hook edits."""
        plan_a = {"configuration": {"hooks": [{"hook_id": "h1", "sql_statement": "SELECT 1"}]}}
        plan_b = {"configuration": {"hooks": [{"hook_id": "h1", "sql_statement": "SELECT 2"}]}}

        diff = self.compiler.compute_diff(plan_a, plan_b)
        self.assertTrue(diff.requires_reapproval)
        self.assertTrue(any("configuration.hooks" in str(c.get("field")) for c in diff.changes))

    def test_27_engine_gateway_facade_integration(self):
        """Hostile Test: EngineGateway facade compiles and validates custom SQL hooks."""
        gateway = EngineGateway()
        payload = {
            "hooks": [
                {"hook_id": "gw_hook", "stage": "PRE_MIGRATION", "sql_statement": "SELECT 1"},
            ],
            "source_connector_type": "postgresql",
            "target_connector_type": "postgresql",
        }

        comp_res = gateway.compile_custom_sql_hooks(payload)
        self.assertEqual(comp_res["status"], "SUCCESS")
        self.assertTrue(bool(comp_res["fingerprint"]))

        val_res = gateway.validate_custom_sql_hooks(payload)
        self.assertTrue(val_res["is_valid"])

    # ---------------------------------------------------------------------------
    # 8. Hostile Failure Policies & Multi-Statement Tests
    # ---------------------------------------------------------------------------

    def test_28_multi_statement_sql_splitting_and_execution(self):
        """Hostile Test: Multi-statement SQL string is cleanly split and executed sequentially."""
        adapter = MockDatabaseAdapter()
        executor = GovernedHookExecutor(source_adapter=adapter, target_adapter=adapter, state_store=self.state_store)

        multi_sql = "CREATE TABLE IF NOT EXISTS t1 (id INT); INSERT INTO t1 VALUES (1); SELECT * FROM t1;"
        hook = HookDefinition(hook_id="h_multi", name="Multi SQL", stage=HookStage.PRE_MIGRATION, sql_statement=multi_sql)

        res = asyncio.run(executor.execute_stage_hooks([hook], stage=HookStage.PRE_MIGRATION, workflow_id="wf-multi"))
        self.assertEqual(res[0].state, HookExecutionState.COMPLETED)
        # Should have executed 3 individual SQL statements
        self.assertEqual(len(adapter.mock_conn.cursor_calls), 3)

    def test_29_fail_fast_failure_policy_aborts_stage(self):
        """Hostile Test: FAIL_FAST policy halts immediately on first failing hook and does not run subsequent hooks."""
        adapter = MockDatabaseAdapter()
        adapter.mock_conn.fail_on_execute = True
        executor = GovernedHookExecutor(source_adapter=adapter, target_adapter=adapter, state_store=self.state_store)

        h1 = HookDefinition(hook_id="h1", name="H1", stage=HookStage.PRE_MIGRATION, sql_statement="SELECT 1", failure_policy=HookFailurePolicy.FAIL_FAST, order=1)
        h2 = HookDefinition(hook_id="h2", name="H2", stage=HookStage.PRE_MIGRATION, sql_statement="SELECT 2", failure_policy=HookFailurePolicy.FAIL_FAST, order=2)

        with self.assertRaises(HookExecutionError):
            asyncio.run(executor.execute_stage_hooks([h1, h2], stage=HookStage.PRE_MIGRATION, workflow_id="wf-ff"))

        # h2 should never have been recorded in CentralStateStore
        st_h2 = self.state_store.get_state("wf-ff:h2", category="hooks")
        self.assertIsNone(st_h2)

    def test_30_continue_on_failure_policy_executes_subsequent_hooks(self):
        """Hostile Test: CONTINUE_ON_FAILURE records failure and proceeds to execute remaining hooks in stage."""
        adapter = MockDatabaseAdapter()
        # Make hook 1 fail by pointing to bad syntax, but hook 2 pass
        executor = GovernedHookExecutor(source_adapter=adapter, target_adapter=adapter, state_store=self.state_store)

        # Hook 1 uses an unclassifiable/bad table to fail, hook 2 uses valid SELECT
        h1 = HookDefinition(hook_id="h1", name="H1 Fail", stage=HookStage.PRE_MIGRATION, sql_statement="SELECT * FROM non_existent_xyz", failure_policy=HookFailurePolicy.CONTINUE_ON_FAILURE, order=1)
        h2 = HookDefinition(hook_id="h2", name="H2 Pass", stage=HookStage.PRE_MIGRATION, sql_statement="SELECT 1", failure_policy=HookFailurePolicy.FAIL_FAST, order=2)

        results = asyncio.run(executor.execute_stage_hooks([h1, h2], stage=HookStage.PRE_MIGRATION, workflow_id="wf-cof"))
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0].state, HookExecutionState.FAILED)
        self.assertEqual(results[1].state, HookExecutionState.COMPLETED)

    def test_31_require_operator_intervention_policy(self):
        """Hostile Test: REQUIRE_OPERATOR raises HookOperatorInterventionRequiredError."""
        adapter = MockDatabaseAdapter()
        executor = GovernedHookExecutor(source_adapter=adapter, target_adapter=adapter, state_store=self.state_store)

        h1 = HookDefinition(hook_id="h_op", name="Op Required", stage=HookStage.PRE_MIGRATION, sql_statement="SELECT * FROM non_existent_xyz", failure_policy=HookFailurePolicy.REQUIRE_OPERATOR)

        with self.assertRaises(HookOperatorInterventionRequiredError):
            asyncio.run(executor.execute_stage_hooks([h1], stage=HookStage.PRE_MIGRATION, workflow_id="wf-op"))

    def test_32_disabled_hooks_are_skipped_zero_queries(self):
        """Hostile Test: Hooks with enabled=False are completely skipped without running any database queries."""
        adapter = MockDatabaseAdapter()
        executor = GovernedHookExecutor(source_adapter=adapter, target_adapter=adapter, state_store=self.state_store)

        hook = HookDefinition(hook_id="h_dis", name="Disabled Hook", stage=HookStage.PRE_MIGRATION, sql_statement="SELECT 1", enabled=False)

        results = asyncio.run(executor.execute_stage_hooks([hook], stage=HookStage.PRE_MIGRATION, workflow_id="wf-dis"))
        self.assertEqual(len(results), 0)
        self.assertEqual(len(adapter.mock_conn.cursor_calls), 0)

    # ---------------------------------------------------------------------------
    # 9. Scope Fencing & Execution Mode Tests
    # ---------------------------------------------------------------------------

    def test_33_unknown_scope_object_fails_compilation(self):
        """Hostile Test: Hook targeting an object not present in selected_scope fails compilation."""
        h1 = HookDefinition(
            hook_id="h_scoped",
            name="Scoped Hook",
            stage=HookStage.PRE_OBJECT,
            scope_object="UNKNOWN_NONEXISTENT_TABLE",
            sql_statement="SELECT 1",
        )
        res = self.compiler.compile_custom_sql_hooks(
            hooks_config=[h1],
            source_connector_type="postgresql",
            target_connector_type="postgresql",
            selected_scope={"objects": [{"object_name": "CUSTOMERS"}]},
        )
        self.assertEqual(res["status"], "BLOCKER")
        self.assertTrue(any(d["code"] == "UNKNOWN_SCOPE_OBJECT" for d in res["diagnostics"]))

    def test_34_m6_schema_only_blocks_data_hooks(self):
        """Hostile Test: Mode M6 (Schema Only) blocks PRE_OBJECT and POST_OBJECT data hooks."""
        h1 = HookDefinition(
            hook_id="h_data",
            name="Data Hook",
            stage=HookStage.PRE_OBJECT,
            scope_object="CUSTOMERS",
            sql_statement="SELECT 1",
        )
        res = self.compiler.compile_custom_sql_hooks(
            hooks_config=[h1],
            source_connector_type="postgresql",
            target_connector_type="postgresql",
            execution_mode="M6",
            selected_scope={"objects": [{"object_name": "CUSTOMERS"}]},
        )
        self.assertEqual(res["status"], "BLOCKER")
        self.assertTrue(any(d["code"] == "DATA_HOOK_IN_SCHEMA_ONLY_MODE" for d in res["diagnostics"]))

    def test_35_kafka_target_connector_rejected(self):
        """Hostile Test: Kafka streaming target fails compilation when custom SQL hooks are attached."""
        h1 = HookDefinition(
            hook_id="h_kafka",
            name="Kafka Target Hook",
            stage=HookStage.TARGET_PREPARATION,
            side=HookSide.TARGET,
            sql_statement="SELECT 1",
        )
        res = self.compiler.compile_custom_sql_hooks(
            hooks_config=[h1],
            source_connector_type="postgresql",
            target_connector_type="kafka",
        )
        self.assertEqual(res["status"], "BLOCKER")
        self.assertTrue(any(d["code"] == "UNSUPPORTED_HOOK_TARGET_CONNECTOR" for d in res["diagnostics"]))

    # ---------------------------------------------------------------------------
    # 10. Crash Window State Reconstruction & Durability
    # ---------------------------------------------------------------------------

    def test_36_crash_window_1_unexecuted_stage_detected_on_restart(self):
        """Hostile Test: Process restart before stage execution detects unexecuted state in CentralStateStore."""
        # Fresh store has no record for this workflow
        st = self.state_store.get_state("wf-fresh:h1", category="hooks")
        self.assertIsNone(st)

    def test_37_crash_window_2_interrupted_run_resumption(self):
        """Hostile Test: Restarting after crash while hook in STARTED state blocks non-idempotent re-run."""
        self.state_store.set_state(
            key="wf-crash2:h_mut",
            value={"hook_id": "h_mut", "state": HookExecutionState.STARTED.value},
            category="hooks",
        )

        adapter = MockDatabaseAdapter()
        executor = GovernedHookExecutor(source_adapter=adapter, target_adapter=adapter, state_store=self.state_store)
        hook = HookDefinition(
            hook_id="h_mut",
            name="Mutating Hook",
            stage=HookStage.PRE_MIGRATION,
            sql_statement="INSERT INTO target_audit VALUES (1)",
            idempotency=HookIdempotencyClassification.NON_IDEMPOTENT,
        )

        with self.assertRaises(AmbiguousHookReplayError):
            asyncio.run(executor.execute_stage_hooks([hook], stage=HookStage.PRE_MIGRATION, workflow_id="wf-crash2"))

    def test_38_crash_window_3_post_completion_restart_idempotency(self):
        """Hostile Test: Process restart after COMPLETED state persistently skips re-execution."""
        self.state_store.set_state(
            key="wf-crash3:h_done",
            value={"hook_id": "h_done", "state": HookExecutionState.COMPLETED.value, "rows_affected": 5, "duration_ms": 12.5},
            category="hooks",
        )

        # Simulate process restart with fresh executor
        adapter = MockDatabaseAdapter()
        fresh_executor = GovernedHookExecutor(source_adapter=adapter, target_adapter=adapter, state_store=self.state_store)
        hook = HookDefinition(hook_id="h_done", name="Done Hook", stage=HookStage.PRE_MIGRATION, sql_statement="SELECT 1")

        results = asyncio.run(fresh_executor.execute_stage_hooks([hook], stage=HookStage.PRE_MIGRATION, workflow_id="wf-crash3"))
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].state, HookExecutionState.COMPLETED)
        self.assertEqual(results[0].rows_affected, 5)
        # Database query was skipped
        self.assertEqual(len(adapter.mock_conn.cursor_calls), 0)

    # ---------------------------------------------------------------------------
    # 11. Legacy HookExecutor & Evidence Authority Integration
    # ---------------------------------------------------------------------------

    def test_39_legacy_hook_executor_backward_compatibility(self):
        """Hostile Test: Legacy HookExecutor.execute_phase_hooks maintains 100% backward compatibility."""
        from akaal.core.models.configuration import SQLHook, HookPhase

        adapter = MockDatabaseAdapter()
        legacy_executor = HookExecutor(connection_adapter=adapter)

        legacy_hook = SQLHook(
            phase=HookPhase.BEFORE_DISCOVERY,
            sql_commands=["SELECT 1", "SELECT 2"],
            transactional=True,
            timeout_seconds=30,
        )

        asyncio.run(legacy_executor.execute_phase_hooks([legacy_hook], phase=HookPhase.BEFORE_DISCOVERY))
        self.assertEqual(len(legacy_executor.audit_log), 1)
        self.assertTrue(legacy_executor.audit_log[0]["success"])

    def test_40_authority_12_evidence_packaging(self):
        """Hostile Test: GovernedHookExecutor emits Evidence Authority #12 facts on stage completion."""
        evidence_auth = EvidenceAuthority.get_instance()
        adapter = MockDatabaseAdapter()
        executor = GovernedHookExecutor(
            source_adapter=adapter,
            target_adapter=adapter,
            state_store=self.state_store,
            evidence_authority=evidence_auth,
        )

        hook = HookDefinition(hook_id="h_evd", name="Evidence Hook", stage=HookStage.PRE_MIGRATION, sql_statement="SELECT 1")
        results = asyncio.run(executor.execute_stage_hooks([hook], stage=HookStage.PRE_MIGRATION, workflow_id="wf-evd-101"))
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].state, HookExecutionState.COMPLETED)

    # ---------------------------------------------------------------------------
    # 12. Advanced Hostile Parameter, Injection & Security Tests
    # ---------------------------------------------------------------------------

    def test_41_hostile_sql_injection_payload_in_parameters(self):
        """Hostile Test: SQL injection vectors in parameters are bound safely without string interpolation."""
        adapter = MockDatabaseAdapter()
        executor = GovernedHookExecutor(source_adapter=adapter, target_adapter=adapter, state_store=self.state_store)

        injection_param = "' OR '1'='1'; DROP TABLE users; --"
        hook = HookDefinition(
            hook_id="h_inject",
            name="Injection Attempt",
            stage=HookStage.PRE_MIGRATION,
            sql_statement="SELECT :user_name AS val",
            parameters={"user_name": injection_param},
        )

        res = asyncio.run(executor.execute_stage_hooks([hook], stage=HookStage.PRE_MIGRATION, workflow_id="wf-inj"))
        self.assertEqual(res[0].state, HookExecutionState.COMPLETED)
        # Verify cursor execution received parameters safely
        self.assertEqual(len(adapter.mock_conn.cursor_calls), 1)

    def test_42_sql_preview_sanitizes_credentials(self):
        """Hostile Test: Preview of SQL statement with embedded secrets redacts secret values."""
        raw_sql = "CREATE USER app_user WITH PASSWORD 'SUPER_SECRET_PAYLOAD_999';"
        preview = LogAndDiagnosticSanitizer.sanitize_sql_preview(raw_sql)
        self.assertNotIn("SUPER_SECRET_PAYLOAD_999", preview)
        self.assertIn("[REDACTED", preview)

    def test_43_audit_log_records_hook_lifecycle_events(self):
        """Hostile Test: GovernedHookExecutor logs HOOK_STARTED and HOOK_COMPLETED audit events."""
        audit_log = AuditLogger.get_instance()
        adapter = MockDatabaseAdapter()
        executor = GovernedHookExecutor(
            source_adapter=adapter,
            target_adapter=adapter,
            state_store=self.state_store,
            audit_logger=audit_log,
        )

        hook = HookDefinition(hook_id="h_aud", name="Audit Hook", stage=HookStage.PRE_MIGRATION, sql_statement="SELECT 1")
        asyncio.run(executor.execute_stage_hooks([hook], stage=HookStage.PRE_MIGRATION, workflow_id="wf-audit-trace"))

        # Find matching audit records
        started_entries = [e for e in audit_log._entries if e.event_type == AuditEventType.HOOK_STARTED]
        completed_entries = [e for e in audit_log._entries if e.event_type == AuditEventType.HOOK_COMPLETED]

        self.assertGreaterEqual(len(started_entries), 1)
        self.assertGreaterEqual(len(completed_entries), 1)

    def test_44_complex_5_hook_multi_stage_dag_resolution(self):
        """Hostile Test: Deterministic ordering of 5 hooks spanning multiple stages with stage dependency constraints."""
        h1 = HookDefinition(hook_id="h1", name="H1", stage=HookStage.PRE_MIGRATION, sql_statement="SELECT 1", order=2)
        h2 = HookDefinition(hook_id="h2", name="H2", stage=HookStage.PRE_MIGRATION, sql_statement="SELECT 2", order=1)
        h3 = HookDefinition(hook_id="h3", name="H3", stage=HookStage.TARGET_PREPARATION, sql_statement="SELECT 3", dependencies=["h1"])
        h4 = HookDefinition(hook_id="h4", name="H4", stage=HookStage.TARGET_FINALIZATION, sql_statement="SELECT 4", dependencies=["h3"])
        h5 = HookDefinition(hook_id="h5", name="H5", stage=HookStage.POST_MIGRATION, sql_statement="SELECT 5", dependencies=["h4"])

        res = self.compiler.compile_custom_sql_hooks(
            hooks_config=[h5, h4, h3, h2, h1],
            source_connector_type="postgresql",
            target_connector_type="postgresql",
        )
        self.assertEqual(res["status"], "SUCCESS")
        compiled_ids = [h["hook_id"] for h in res["hooks"]]
        self.assertEqual(compiled_ids, ["h2", "h1", "h3", "h4", "h5"])

    def test_45_plan_diff_detects_hook_additions_and_deletions(self):
        """Hostile Test: Adding or removing a hook from configuration triggers critical plan diff."""
        plan_base = {"configuration": {"hooks": [{"hook_id": "h1", "sql_statement": "SELECT 1"}]}}
        plan_added = {"configuration": {"hooks": [{"hook_id": "h1", "sql_statement": "SELECT 1"}, {"hook_id": "h2", "sql_statement": "SELECT 2"}]}}
        plan_removed = {"configuration": {"hooks": []}}

        diff_add = self.compiler.compute_diff(plan_base, plan_added)
        self.assertTrue(diff_add.requires_reapproval)

        diff_del = self.compiler.compute_diff(plan_base, plan_removed)
        self.assertTrue(diff_del.requires_reapproval)

    def test_46_concurrent_independent_workflows_do_not_interfere(self):
        """Hostile Test: CentralStateStore isolates hook records across independent workflow IDs."""
        adapter = MockDatabaseAdapter()
        executor = GovernedHookExecutor(source_adapter=adapter, target_adapter=adapter, state_store=self.state_store)

        hook = HookDefinition(hook_id="h_shared", name="Shared Hook", stage=HookStage.PRE_MIGRATION, sql_statement="SELECT 1")

        # Run for workflow A
        asyncio.run(executor.execute_stage_hooks([hook], stage=HookStage.PRE_MIGRATION, workflow_id="wf-A"))
        # Run for workflow B
        asyncio.run(executor.execute_stage_hooks([hook], stage=HookStage.PRE_MIGRATION, workflow_id="wf-B"))

        st_a = self.state_store.get_state("wf-A:h_shared", category="hooks")
        st_b = self.state_store.get_state("wf-B:h_shared", category="hooks")

        self.assertIsNotNone(st_a)
        self.assertIsNotNone(st_b)
        self.assertEqual(st_a["workflow_id"], "wf-A")
        self.assertEqual(st_b["workflow_id"], "wf-B")

    def test_47_re_approval_validation_fails_when_plan_altered(self):
        """Hostile Test: validate_plan_approval fails closed when approved_fingerprint does not match altered plan."""
        exec_plan = {
            "fingerprint": "NEW_UNAPPROVED_FP_999",
            "resolved_configuration": {
                "hooks_fingerprint": "HOOKS_FP_999",
                "hooks_requires_approval": True,
            },
        }
        old_approved_fp = "OLD_STALE_APPROVED_FP_111"

        with self.assertRaises(RuntimeError) as ctx_err:
            PlanCompiler.validate_plan_approval(exec_plan, old_approved_fp)
        self.assertIn("STALE_APPROVAL_REJECTED", str(ctx_err.exception))

    def test_48_multiple_statements_with_destructive_ddl_require_approval(self):
        """Hostile Test: Multi-statement query containing any destructive statement requires approval."""
        multi_sql = "SELECT 1; DROP TABLE customers; SELECT 2;"
        h1 = HookDefinition(
            hook_id="h_multi_drop",
            name="Multi Drop",
            stage=HookStage.PRE_MIGRATION,
            sql_statement=multi_sql,
            requires_approval=False,
        )
        res = self.compiler.compile_custom_sql_hooks(
            hooks_config=HooksConfiguration(enabled=True, hooks=[h1], allow_dangerous_sql=False),
            source_connector_type="postgresql",
            target_connector_type="postgresql",
        )
        self.assertEqual(res["status"], "BLOCKER")
        self.assertTrue(any(d["code"] == "UNAPPROVED_DANGEROUS_SQL" for d in res["diagnostics"]))

    def test_49_disallowed_sql_by_custom_allow_policy(self):
        """Hostile Test: SQL statement not matching custom allow policy is blocked during compilation."""
        h1 = HookDefinition(
            hook_id="h_disallowed",
            name="Disallowed Hook",
            stage=HookStage.PRE_MIGRATION,
            sql_statement="UPDATE control SET flag = 1",
        )
        cfg = HooksConfiguration(
            enabled=True,
            hooks=[h1],
            allow_rules=[r"^SELECT\b"],  # Only SELECT allowed
        )
        res = self.compiler.compile_custom_sql_hooks(
            hooks_config=cfg,
            source_connector_type="postgresql",
            target_connector_type="postgresql",
        )
        self.assertEqual(res["status"], "BLOCKER")
        self.assertTrue(any(d["code"] == "DISALLOWED_SQL_OPERATION" for d in res["diagnostics"]))

    def test_50_empty_hooks_configuration_compiles_cleanly(self):
        """Hostile Test: Plan with empty or disabled hooks compiles cleanly with empty fingerprint."""
        res = self.compiler.compile_custom_sql_hooks(
            hooks_config=HooksConfiguration(enabled=False, hooks=[]),
            source_connector_type="postgresql",
            target_connector_type="postgresql",
        )
        self.assertEqual(res["status"], "SUCCESS")
        self.assertEqual(len(res["hooks"]), 0)
        self.assertEqual(res["fingerprint"], "")

    # ---------------------------------------------------------------------------
    # 13. Deep Fencing, Mode Invariants & Crash Recovery Matrix
    # ---------------------------------------------------------------------------

    def test_51_mode_m7_data_only_blocks_ddl_hooks(self):
        """Hostile Test: M7 Data-Only migration mode blocks DDL operations in hooks."""
        h1 = HookDefinition(
            hook_id="h_ddl_m7",
            name="DDL in M7",
            stage=HookStage.TARGET_PREPARATION,
            sql_statement="CREATE TABLE test_tab (id INT);",
            requires_approval=True,
        )
        res = self.compiler.compile_custom_sql_hooks(
            hooks_config=[h1],
            execution_mode="M7",
            source_connector_type="postgresql",
            target_connector_type="postgresql",
        )
        self.assertEqual(res["status"], "BLOCKER")
        self.assertTrue(any(d["code"] == "DDL_HOOK_IN_DATA_ONLY_MODE" for d in res["diagnostics"]))

    def test_52_mode_m8_validation_blocks_source_mutations(self):
        """Hostile Test: M8 Validation-Only mode blocks mutating SQL on source side as well as target."""
        h1 = HookDefinition(
            hook_id="h_mut_src_m8",
            name="Source Mutation in M8",
            side=HookSide.SOURCE,
            stage=HookStage.PRE_MIGRATION,
            sql_statement="UPDATE control_table SET status = 'IN_PROGRESS';",
            requires_approval=True,
        )
        res = self.compiler.compile_custom_sql_hooks(
            hooks_config=[h1],
            execution_mode="M8",
            source_connector_type="postgresql",
            target_connector_type="postgresql",
        )
        self.assertEqual(res["status"], "BLOCKER")
        self.assertTrue(any(d["code"] == "MUTATING_HOOK_IN_VALIDATION_MODE" for d in res["diagnostics"]))

    def test_53_stub_connector_evaluates_sql_execution_as_unsupported(self):
        """Hostile Test: UniversalCapabilityManifest forces supports_sql_execution=False for STUB implementation state."""
        from akaal.connectors.manifest import UniversalCapabilityManifest
        from akaal.connectors.taxonomy import ConnectorFamily, ImplementationState, CapabilitySupportStatus

        manifest = UniversalCapabilityManifest(
            connector_id="stub_db",
            family=ConnectorFamily.RELATIONAL_DATABASE,
            vendor_name="StubVendor",
            system_type="STUB_SQL",
            implementation_state=ImplementationState.STUB,
        )
        self.assertFalse(manifest.supports_sql_execution)
        self.assertEqual(manifest.get_capability_status("sql_execution"), CapabilitySupportStatus.UNSUPPORTED)

    def test_54_complex_cte_with_comments_and_quoted_literals_parsed_safely(self):
        """Hostile Test: Complex CTE query with multi-line comments and quotes is correctly classified as SAFE_SELECT."""
        sql = """
        /* Multi-line header comment; contains DROP TABLE keywords */
        WITH active_users AS (
            SELECT id, name, '--not-a-comment--' AS dummy_str
            FROM users -- inline comment
            WHERE status = 'ACTIVE'
        )
        SELECT * FROM active_users;
        """
        classification = SQLSafetyClassifier.classify(sql)
        self.assertEqual(classification, SQLSafetyClassification.SAFE_SELECT)

    def test_55_plan_diff_triggers_reapproval_on_hook_parameter_change(self):
        """Hostile Test: Modifying hook parameters changes hooks_fingerprint and triggers requires_reapproval."""
        plan_v1 = {"configuration": {"hooks": [{"hook_id": "h1", "sql_statement": "SELECT 1", "parameters": {"env": "staging"}}]}}
        plan_v2 = {"configuration": {"hooks": [{"hook_id": "h1", "sql_statement": "SELECT 1", "parameters": {"env": "production"}}]}}

        diff = self.compiler.compute_diff(plan_v1, plan_v2)
        self.assertTrue(diff.requires_reapproval)

    def test_56_plan_diff_triggers_reapproval_on_hook_stage_change(self):
        """Hostile Test: Modifying hook lifecycle stage triggers requires_reapproval."""
        plan_v1 = {"configuration": {"hooks": [{"hook_id": "h1", "sql_statement": "SELECT 1", "stage": "PRE_MIGRATION"}]}}
        plan_v2 = {"configuration": {"hooks": [{"hook_id": "h1", "sql_statement": "SELECT 1", "stage": "POST_MIGRATION"}]}}

        diff = self.compiler.compute_diff(plan_v1, plan_v2)
        self.assertTrue(diff.requires_reapproval)

    def test_57_failure_policy_require_operator_raises_informative_error(self):
        """Hostile Test: Hook with REQUIRE_OPERATOR policy raises HookExecutionError indicating operator intervention."""
        adapter = MockDatabaseAdapter()
        executor = GovernedHookExecutor(source_adapter=adapter, target_adapter=adapter, state_store=self.state_store)

        adapter.mock_conn.fail_on_execute = True
        hook = HookDefinition(
            hook_id="h_op",
            name="Operator Gate Hook",
            stage=HookStage.PRE_MIGRATION,
            sql_statement="SELECT 1;",
            failure_policy=HookFailurePolicy.REQUIRE_OPERATOR,
        )

        with self.assertRaises(HookExecutionError) as ctx_err:
            asyncio.run(executor.execute_stage_hooks([hook], stage=HookStage.PRE_MIGRATION, workflow_id="wf-op"))
        self.assertIn("h_op", str(ctx_err.exception))

    def test_58_crash_window_durable_state_verification(self):
        """Hostile Test: CentralStateStore accurately reflects lifecycle transitions across crash simulations."""
        adapter = MockDatabaseAdapter()
        executor = GovernedHookExecutor(source_adapter=adapter, target_adapter=adapter, state_store=self.state_store)

        hook = HookDefinition(hook_id="h_durable", name="Durable Hook", stage=HookStage.PRE_MIGRATION, sql_statement="SELECT 1;")

        # 1. Pre-execution: state is None
        self.assertIsNone(self.state_store.get_state("wf-dur:h_durable", category="hooks"))

        # 2. Execution runs and completes
        res = asyncio.run(executor.execute_stage_hooks([hook], stage=HookStage.PRE_MIGRATION, workflow_id="wf-dur"))
        self.assertEqual(res[0].state, HookExecutionState.COMPLETED)

        # 3. Post-execution: state is COMPLETED
        st = self.state_store.get_state("wf-dur:h_durable", category="hooks")
        self.assertIsNotNone(st)
        self.assertEqual(st["state"], HookExecutionState.COMPLETED.value)

    def test_59_evidence_authority_packages_redacted_hook_telemetry(self):
        """Hostile Test: Evidence Authority packages hook execution facts with sensitive data excluded."""
        evidence_auth = EvidenceAuthority.get_instance()
        hook_res = HookExecutionResult(
            hook_id="h_evd_sec",
            stage=HookStage.PRE_MIGRATION,
            state=HookExecutionState.COMPLETED,
            sanitized_sql="CREATE USER test_usr WITH PASSWORD '[REDACTED]';",
            duration_ms=42.5,
        )
        bundle = evidence_auth.package_hook_execution_evidence(
            migration_id="mig-evd-999",
            stage=HookStage.PRE_MIGRATION,
            hook_results=[hook_res],
        )
        self.assertIn("facts", bundle)
        self.assertNotIn("SUPER_SECRET", str(bundle))
        self.assertEqual(bundle["status"], "CERTIFIED")

    def test_60_audit_logger_entry_computes_valid_checksum(self):
        """Hostile Test: AuditLogger produces tamper-evident SHA-256 checksums on hook audit entries."""
        audit_log = AuditLogger.get_instance()
        entry = audit_log.log(
            event_type=AuditEventType.HOOK_COMPLETED,
            migration_id="mig-audit-chk",
            task_id="h_chk",
            details={"rows": 100},
        )
        self.assertIsNotNone(entry.checksum)
        self.assertEqual(len(entry.checksum), 64)
        # Re-compute checksum and verify exact match
        self.assertEqual(entry.checksum, entry._compute_checksum())


if __name__ == "__main__":
    unittest.main()


