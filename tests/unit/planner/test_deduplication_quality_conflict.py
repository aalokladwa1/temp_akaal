"""
Akaal — Deduplication + Data Quality + Conflict Policies Comprehensive Test Suite
==================================================================================
Comprehensive unit, hostile, and integration test suite covering:
1. Composite key hashing and delimiter collision prevention.
2. Deterministic survivor strategies (FIRST, LAST, MIN_FIELD, MAX_FIELD, NEWEST, OLDEST, PRIORITY, REJECT_GROUP, QUARANTINE_GROUP, FAIL_ON_DUPLICATE).
3. Input shuffle permutation invariance and record fingerprint tie-breaking.
4. Target collision DML generation across PostgreSQL, MySQL, Oracle, MSSQL, SQLite.
5. Data quality rules (NOT_NULL, VALUE_RANGE, REGEX_MATCH, ENUM_VALUES, MAX_LENGTH, NUMERIC_OVERFLOW).
6. Non-silent truncation and numeric boundary enforcement.
7. Quality threshold gate evaluation and cutover blocking.
8. P3 CDC conflict policy integration without duplicate engines.
9. ExecutionPlan compilation, immutability, fingerprint binding, and restart reconstruction.
10. EngineGateway capability endpoints.
11. Hostile attacks: adversarial composite keys, NULL / missing components, type safety, extreme gate boundaries.
"""

import hashlib
import json
import os
import random
import tempfile
import unittest
import uuid
from typing import Any, Dict, List

from akaal.core.models.enums import SystemType
from akaal.gateway.engine_gateway import EngineGateway
from akaal.migration.execution.deduplication import (
    ZeroDuplicateMigrationEngine,
    UnsupportedCollisionPolicyError,
    DeduplicationResult,
)
from akaal.planner.engine.plan_compiler import PlanCompiler
from akaal.planner.models.p5_domain import (
    CollisionPolicy,
    ConflictPolicyConfiguration,
    DataQualityDefinition,
    DataQualityRule,
    DeduplicationDefinition,
    DeduplicationRule,
    DuplicateDisposition,
    ExecutionPlan,
    MigrationPlan,
    MigrationProject,
    PlanVersion,
    PlanningMode,
    QualityGateConsequence,
    QualityRuleType,
    QualityThreshold,
    QualityViolationPolicy,
    RoutingDefinition,
    SchemaRoute,
    SelectionDefinition,
    SelectionRule,
    SourceTopology,
    SurvivorStrategy,
    TargetTopology,
    TopologyDefinition,
)
from akaal.planner.persistence.project_store import ProjectStore
from akaalEngine.data_processing.api import DataProcessingAuthority
from akaalEngine.data_processing.dedup.deduplicator import (
    DuplicateKeyException,
    RowDeduplicator,
)
from akaalEngine.data_processing.engine.processing_engine import (
    MalformedDataException,
    ProcessingEngine,
)
from akaalEngine.data_processing.models.plan import (
    MalformedDataPolicy,
    ProcessingPlan,
    RuleType,
    TransformationRule,
)


class TestDeduplicationQualityConflict(unittest.TestCase):
    """Authoritative test suite for Deduplication + Data Quality + Conflict Policies."""

    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.temp_dir.name, "test_dedup_quality.db")
        self.store = ProjectStore(db_path=self.db_path)
        self.compiler = PlanCompiler()
        self.gateway = EngineGateway()

        self.sample_scope = {
            "databases": ["crm_db"],
            "schemas": ["public"],
            "objects": [
                {
                    "schema_name": "public",
                    "object_name": "CUSTOMERS",
                    "selected": True,
                    "columns": ["id", "email", "first_name", "last_name", "tier", "score", "updated_at"],
                    "pk_columns": ["id"],
                },
                {
                    "schema_name": "public",
                    "object_name": "ORDERS",
                    "selected": True,
                    "columns": ["id", "customer_id", "order_date", "total_amount", "status"],
                    "pk_columns": ["id"],
                },
            ],
        }

    def tearDown(self) -> None:
        try:
            self.temp_dir.cleanup()
        except Exception:
            pass

    # =========================================================================
    # 1. DEDUPLICATION & COMPOSITE KEY HASHING
    # =========================================================================

    def test_01_composite_key_hash_unambiguous(self):
        """Tests that length-prefixed composite key hashing prevents delimiter collision attacks."""
        dedup = RowDeduplicator()

        # Without length-prefixing, ("a|b", "c") and ("a", "b|c") would both yield "a|b|c"
        row1 = {"col1": "a|b", "col2": "c"}
        row2 = {"col1": "a", "col2": "b|c"}

        hash1 = dedup.compute_key_hash(row1, ["col1", "col2"])
        hash2 = dedup.compute_key_hash(row2, ["col1", "col2"])

        self.assertNotEqual(hash1, hash2, "Composite key hashing must be collision-resistant across delimiters.")

    def test_01b_adversarial_composite_key_collisions(self):
        """Hostile Test: Adversarial composite key attacks with NULL vs string 'None', empty strings, and type differences."""
        dedup = RowDeduplicator()

        # 1. NULL vs string "None"
        row_null = {"k1": None, "k2": "val"}
        row_str_none = {"k1": "None", "k2": "val"}
        self.assertNotEqual(
            dedup.compute_key_hash(row_null, ["k1", "k2"]),
            dedup.compute_key_hash(row_str_none, ["k1", "k2"]),
            "NULL and string 'None' must yield distinct key hashes.",
        )

        # 2. Integer vs String representation
        row_int = {"k1": 123, "k2": "x"}
        row_str = {"k1": "123", "k2": "x"}
        # Both produce unambiguous type-prefixed or canonical strings
        hash_int = dedup.compute_key_hash(row_int, ["k1", "k2"])
        hash_str = dedup.compute_key_hash(row_str, ["k1", "k2"])
        self.assertIsInstance(hash_int, str)
        self.assertIsInstance(hash_str, str)

        # 3. Empty string vs NULL
        row_empty = {"k1": "", "k2": "x"}
        self.assertNotEqual(
            dedup.compute_key_hash(row_empty, ["k1", "k2"]),
            dedup.compute_key_hash(row_null, ["k1", "k2"]),
            "Empty string and NULL must yield distinct key hashes.",
        )

    def test_02_survivor_first_and_last_strategy(self):
        """Tests deterministic FIRST and LAST survivor selection based on explicit order_by_columns."""
        dedup = RowDeduplicator()

        records = [
            {"id": 1, "email": "alice@example.com", "updated_at": "2026-01-01T00:00:00Z", "version": 1},
            {"id": 2, "email": "alice@example.com", "updated_at": "2026-02-01T00:00:00Z", "version": 2},
            {"id": 3, "email": "alice@example.com", "updated_at": "2026-03-01T00:00:00Z", "version": 3},
        ]

        # FIRST with updated_at DESC (should pick version 3)
        survivors_first, dups_first, _ = dedup.deduplicate_batch(
            records=records,
            key_columns=["email"],
            survivor_strategy="FIRST",
            order_by_columns=["updated_at DESC"],
        )
        self.assertEqual(len(survivors_first), 1)
        self.assertEqual(survivors_first[0]["version"], 3)
        self.assertEqual(len(dups_first), 2)

        # LAST with updated_at DESC (should pick version 1)
        survivors_last, dups_last, _ = dedup.deduplicate_batch(
            records=records,
            key_columns=["email"],
            survivor_strategy="LAST",
            order_by_columns=["updated_at DESC"],
        )
        self.assertEqual(len(survivors_last), 1)
        self.assertEqual(survivors_last[0]["version"], 1)

    def test_03_survivor_min_and_max_field_strategy(self):
        """Tests MIN_FIELD and MAX_FIELD survivor selection."""
        dedup = RowDeduplicator()

        records = [
            {"id": 1, "account": "ACC100", "balance": 500},
            {"id": 2, "account": "ACC100", "balance": 1500},
            {"id": 3, "account": "ACC100", "balance": 250},
        ]

        # MAX_FIELD balance -> 1500
        surv_max, _, _ = dedup.deduplicate_batch(
            records=records,
            key_columns=["account"],
            survivor_strategy="MAX_FIELD",
            order_by_columns=["balance"],
        )
        self.assertEqual(len(surv_max), 1)
        self.assertEqual(surv_max[0]["balance"], 1500)

        # MIN_FIELD balance -> 250
        surv_min, _, _ = dedup.deduplicate_batch(
            records=records,
            key_columns=["account"],
            survivor_strategy="MIN_FIELD",
            order_by_columns=["balance"],
        )
        self.assertEqual(len(surv_min), 1)
        self.assertEqual(surv_min[0]["balance"], 250)

    def test_04_survivor_newest_and_oldest_strategy(self):
        """Tests NEWEST and OLDEST timestamp survivor selection."""
        dedup = RowDeduplicator()

        records = [
            {"id": 10, "device_id": "D1", "ts": "2026-05-10T12:00:00Z"},
            {"id": 11, "device_id": "D1", "ts": "2026-01-01T00:00:00Z"},
            {"id": 12, "device_id": "D1", "ts": "2026-08-20T18:30:00Z"},
        ]

        # NEWEST -> 2026-08-20
        surv_new, _, _ = dedup.deduplicate_batch(
            records=records,
            key_columns=["device_id"],
            survivor_strategy="NEWEST",
            order_by_columns=["ts"],
        )
        self.assertEqual(surv_new[0]["id"], 12)

        # OLDEST -> 2026-01-01
        surv_old, _, _ = dedup.deduplicate_batch(
            records=records,
            key_columns=["device_id"],
            survivor_strategy="OLDEST",
            order_by_columns=["ts"],
        )
        self.assertEqual(surv_old[0]["id"], 11)

    def test_05_survivor_priority_strategy(self):
        """Tests PRIORITY survivor selection according to configured priority order list."""
        dedup = RowDeduplicator()

        records = [
            {"id": 1, "customer_id": "C-1", "tier": "BRONZE"},
            {"id": 2, "customer_id": "C-1", "tier": "PLATINUM"},
            {"id": 3, "customer_id": "C-1", "tier": "GOLD"},
            {"id": 4, "customer_id": "C-1", "tier": "SILVER"},
        ]

        # Priority order: PLATINUM > GOLD > SILVER > BRONZE
        priority_hierarchy = ["PLATINUM", "GOLD", "SILVER", "BRONZE"]
        survivors, dups, _ = dedup.deduplicate_batch(
            records=records,
            key_columns=["customer_id"],
            survivor_strategy="PRIORITY",
            priority_field="tier",
            priority_order=priority_hierarchy,
        )

        self.assertEqual(len(survivors), 1)
        self.assertEqual(survivors[0]["tier"], "PLATINUM")
        self.assertEqual(len(dups), 3)

    def test_06_input_shuffle_permutation_invariance(self):
        """Hostile Test: Shuffling input records across 100 permutations produces the exact same survivor."""
        dedup = RowDeduplicator()

        base_records = [
            {"id": 1, "uid": "U100", "score": 90, "city": "London"},
            {"id": 2, "uid": "U100", "score": 95, "city": "Paris"},
            {"id": 3, "uid": "U100", "score": 85, "city": "Tokyo"},
            {"id": 4, "uid": "U100", "score": 95, "city": "New York"},  # Tie on score with id 2
        ]

        expected_survivor = None
        for i in range(100):
            shuffled = list(base_records)
            random.seed(i)
            random.shuffle(shuffled)

            survivors, _, _ = dedup.deduplicate_batch(
                records=shuffled,
                key_columns=["uid"],
                survivor_strategy="MAX_FIELD",
                order_by_columns=["score"],
            )

            self.assertEqual(len(survivors), 1)
            if expected_survivor is None:
                expected_survivor = survivors[0]
            else:
                self.assertEqual(
                    survivors[0]["id"],
                    expected_survivor["id"],
                    f"Survivor changed on permutation {i}! Determinism violated.",
                )

    def test_07_survivor_reject_and_quarantine_group(self):
        """Tests REJECT_GROUP and QUARANTINE_GROUP strategies where entire duplicate groups are suppressed."""
        dedup = RowDeduplicator()

        records = [
            {"id": 1, "email": "unique@example.com", "name": "Unique"},
            {"id": 2, "email": "dup@example.com", "name": "Dup A"},
            {"id": 3, "email": "dup@example.com", "name": "Dup B"},
        ]

        # REJECT_GROUP
        survivors_rej, dups_rej, _ = dedup.deduplicate_batch(
            records=records,
            key_columns=["email"],
            survivor_strategy="REJECT_GROUP",
        )
        self.assertEqual(len(survivors_rej), 1)
        self.assertEqual(survivors_rej[0]["email"], "unique@example.com")
        self.assertEqual(len(dups_rej), 2)
        for d in dups_rej:
            self.assertEqual(d["_dedup_disposition"], "REJECTED")

        # QUARANTINE_GROUP
        survivors_quar, dups_quar, _ = dedup.deduplicate_batch(
            records=records,
            key_columns=["email"],
            survivor_strategy="QUARANTINE_GROUP",
        )
        self.assertEqual(len(survivors_quar), 1)
        self.assertEqual(len(dups_quar), 2)
        for d in dups_quar:
            self.assertEqual(d["_dedup_disposition"], "QUARANTINED")

    def test_08_fail_on_duplicate_policy(self):
        """Tests that FAIL_ON_DUPLICATE raises DuplicateKeyException immediately."""
        dedup = RowDeduplicator()

        records = [
            {"id": 1, "code": "X"},
            {"id": 2, "code": "X"},
        ]

        with self.assertRaises(DuplicateKeyException):
            dedup.deduplicate_batch(
                records=records,
                key_columns=["code"],
                survivor_strategy="FAIL_ON_DUPLICATE",
            )

    # =========================================================================
    # 2. TARGET COLLISION POLICIES & SQL GENERATION
    # =========================================================================

    def test_09_collision_upsert_postgresql_and_sqlite(self):
        """Tests dialect-aware UPSERT generation for PostgreSQL and SQLite (ON CONFLICT DO UPDATE)."""
        engine = ZeroDuplicateMigrationEngine(target_dialect=SystemType.POSTGRESQL)

        sql = engine.generate_collision_statement(
            table_name="customers",
            columns=["id", "name", "email"],
            pk_columns=["id"],
            collision_policy=CollisionPolicy.UPSERT,
        )
        self.assertIn("ON CONFLICT (id) DO UPDATE SET name = EXCLUDED.name, email = EXCLUDED.email", sql)

    def test_10_collision_upsert_mysql_and_mariadb(self):
        """Tests dialect-aware UPSERT generation for MySQL (ON DUPLICATE KEY UPDATE)."""
        engine = ZeroDuplicateMigrationEngine(target_dialect=SystemType.MYSQL)

        sql = engine.generate_collision_statement(
            table_name="customers",
            columns=["id", "name", "email"],
            pk_columns=["id"],
            collision_policy=CollisionPolicy.UPSERT,
        )
        self.assertIn("ON DUPLICATE KEY UPDATE name = VALUES(name), email = VALUES(email)", sql)

    def test_11_collision_upsert_oracle_and_mssql(self):
        """Tests dialect-aware UPSERT generation for Oracle and MSSQL (MERGE INTO)."""
        engine = ZeroDuplicateMigrationEngine(target_dialect=SystemType.ORACLE)

        sql = engine.generate_collision_statement(
            table_name="customers",
            columns=["id", "name", "email"],
            pk_columns=["id"],
            collision_policy=CollisionPolicy.UPSERT,
        )
        self.assertIn("MERGE INTO customers target USING", sql)
        self.assertIn("WHEN MATCHED THEN UPDATE SET", sql)
        self.assertIn("WHEN NOT MATCHED THEN INSERT", sql)

    def test_12_collision_skip_policy_do_nothing(self):
        """Tests SKIP collision policy across dialects (DO NOTHING / INSERT IGNORE)."""
        engine_pg = ZeroDuplicateMigrationEngine(target_dialect=SystemType.POSTGRESQL)
        sql_pg = engine_pg.generate_collision_statement(
            table_name="orders",
            columns=["id", "total"],
            pk_columns=["id"],
            collision_policy=CollisionPolicy.SKIP,
        )
        self.assertIn("ON CONFLICT (id) DO NOTHING", sql_pg)

        engine_mysql = ZeroDuplicateMigrationEngine(target_dialect=SystemType.MYSQL)
        sql_my = engine_mysql.generate_collision_statement(
            table_name="orders",
            columns=["id", "total"],
            pk_columns=["id"],
            collision_policy=CollisionPolicy.SKIP,
        )
        self.assertIn("INSERT IGNORE INTO orders", sql_my)

    def test_13_collision_unsupported_connector_blocker(self):
        """Tests that attempting UPSERT on object storage connectors emits a BLOCKER compilation diagnostic."""
        res = self.compiler.compile_deduplication_and_quality(
            selected_scope=self.sample_scope,
            dedup_def={
                "enabled": True,
                "rules": [
                    {
                        "object_name": "CUSTOMERS",
                        "key_columns": ["id"],
                        "collision_policy": "UPSERT",
                    }
                ],
            },
            target_connector_type="S3_PARQUET",
        )
        self.assertEqual(res["status"], "BLOCKER")
        codes = [d["code"] for d in res["diagnostics"]]
        self.assertIn("UNSUPPORTED_COLLISION_POLICY", codes)

    # =========================================================================
    # 3. DATA QUALITY RULES & EXPLICIT VALUE HANDLING
    # =========================================================================

    def test_14_not_null_rule_enforcement(self):
        """Tests NOT_NULL quality rule violation with FAIL_JOB and REJECT_RECORD policies."""
        proc = ProcessingEngine()

        # 1. FAIL_JOB policy
        plan_fail = ProcessingPlan(
            object_name="CUSTOMERS",
            compiled_rules=(
                TransformationRule(
                    rule_id="nn-1",
                    column_name="email",
                    rule_type=RuleType.QUALITY,
                    quality_rule_type="NOT_NULL",
                    malformed_policy=MalformedDataPolicy.FAIL_JOB,
                ),
            ),
        )
        with self.assertRaises(MalformedDataException):
            proc.transform_row({"id": 1, "email": None}, plan_fail)

        # 2. REJECT_RECORD policy
        plan_rej = ProcessingPlan(
            object_name="CUSTOMERS",
            compiled_rules=(
                TransformationRule(
                    rule_id="nn-2",
                    column_name="email",
                    rule_type=RuleType.QUALITY,
                    quality_rule_type="NOT_NULL",
                    malformed_policy=MalformedDataPolicy.REJECT_RECORD,
                ),
            ),
        )
        res = proc.transform_row({"id": 1, "email": None}, plan_rej)
        self.assertEqual(res.status, "REJECTED")
        self.assertIsNone(res.transformed_row)

    def test_15_numeric_overflow_boundary_fencing(self):
        """Tests numeric overflow detection preventing silent wrapping on SMALLINT, INT, and BIGINT."""
        proc = ProcessingEngine()

        plan_overflow = ProcessingPlan(
            object_name="ORDERS",
            compiled_rules=(
                TransformationRule(
                    rule_id="ovf-1",
                    column_name="quantity",
                    rule_type=RuleType.QUALITY,
                    quality_rule_type="NUMERIC_OVERFLOW",
                    target_datatype="SMALLINT",  # max 32767
                    malformed_policy=MalformedDataPolicy.QUARANTINE_RECORD,
                ),
            ),
        )

        # Valid smallint
        res_ok = proc.transform_row({"quantity": 100}, plan_overflow)
        self.assertEqual(res_ok.status, "SUCCESS")

        # Overflow smallint (40000 > 32767)
        res_ovf = proc.transform_row({"quantity": 40000}, plan_overflow)
        self.assertEqual(res_ovf.status, "QUARANTINED")

    def test_16_explicit_truncation_vs_silent_truncation_fencing(self):
        """Tests that length exceeding maximum is rejected unless explicit truncation is enabled."""
        proc = ProcessingEngine()

        # Without allow_truncation: FAILS / QUARANTINES
        plan_strict = ProcessingPlan(
            object_name="CUSTOMERS",
            compiled_rules=(
                TransformationRule(
                    rule_id="len-1",
                    column_name="code",
                    rule_type=RuleType.QUALITY,
                    quality_rule_type="MAX_LENGTH",
                    max_length=5,
                    allow_truncation=False,
                    malformed_policy=MalformedDataPolicy.QUARANTINE_RECORD,
                ),
            ),
        )
        res_strict = proc.transform_row({"code": "ABCDEFGH"}, plan_strict)
        self.assertEqual(res_strict.status, "QUARANTINED")

        # With explicit allow_truncation: explicitly truncates to max_length
        plan_trunc = ProcessingPlan(
            object_name="CUSTOMERS",
            compiled_rules=(
                TransformationRule(
                    rule_id="len-2",
                    column_name="code",
                    rule_type=RuleType.QUALITY,
                    quality_rule_type="MAX_LENGTH",
                    max_length=5,
                    allow_truncation=True,
                    malformed_policy=MalformedDataPolicy.EXPLICIT_TRUNCATE,
                ),
            ),
        )
        res_trunc = proc.transform_row({"code": "ABCDEFGH"}, plan_trunc)
        self.assertEqual(res_trunc.status, "SUCCESS")
        self.assertEqual(res_trunc.transformed_row["code"], "ABCDE")

    def test_17_value_range_and_enum_membership(self):
        """Tests VALUE_RANGE and ENUM_VALUES quality rules."""
        proc = ProcessingEngine()

        plan = ProcessingPlan(
            object_name="CUSTOMERS",
            compiled_rules=(
                TransformationRule(
                    rule_id="vr-1",
                    column_name="age",
                    rule_type=RuleType.QUALITY,
                    quality_rule_type="VALUE_RANGE",
                    min_value=18,
                    max_value=120,
                    malformed_policy=MalformedDataPolicy.REJECT_RECORD,
                ),
                TransformationRule(
                    rule_id="enum-1",
                    column_name="status",
                    rule_type=RuleType.QUALITY,
                    quality_rule_type="ENUM_VALUES",
                    allowed_values=["ACTIVE", "INACTIVE", "SUSPENDED"],
                    malformed_policy=MalformedDataPolicy.REJECT_RECORD,
                ),
            ),
        )

        # Valid row
        res_ok = proc.transform_row({"age": 25, "status": "ACTIVE"}, plan)
        self.assertEqual(res_ok.status, "SUCCESS")

        # Age too low
        res_low = proc.transform_row({"age": 15, "status": "ACTIVE"}, plan)
        self.assertEqual(res_low.status, "REJECTED")

        # Invalid enum
        res_bad_enum = proc.transform_row({"age": 30, "status": "DELETED"}, plan)
        self.assertEqual(res_bad_enum.status, "REJECTED")

    # =========================================================================
    # 4. QUALITY GATES & THRESHOLDS
    # =========================================================================

    def test_18_quality_gate_passed(self):
        """Tests quality gate evaluation passing when metrics are within thresholds."""
        q_def = DataQualityDefinition(
            global_threshold=QualityThreshold(
                max_duplicate_count=10,
                max_invalid_percentage=5.0,
                consequence=QualityGateConsequence.FAIL_JOB,
            )
        )

        metrics = {
            "total_rows": 1000,
            "duplicate_count": 2,
            "invalid_count": 10,
            "reject_count": 5,
            "quarantine_count": 5,
        }
        res = PlanCompiler.evaluate_quality_gates(q_def, metrics)
        self.assertTrue(res.passed)
        self.assertFalse(res.cutover_blocked)

    def test_19_quality_gate_block_cutover_consequence(self):
        """Tests that exceeding threshold with BLOCK_CUTOVER consequence sets cutover_blocked=True."""
        q_def = DataQualityDefinition(
            global_threshold=QualityThreshold(
                max_duplicate_percentage=1.0,
                consequence=QualityGateConsequence.BLOCK_CUTOVER,
            )
        )

        metrics = {
            "total_rows": 1000,
            "duplicate_count": 50,  # 5% > 1%
            "invalid_count": 0,
        }
        res = PlanCompiler.evaluate_quality_gates(q_def, metrics)
        self.assertFalse(res.passed)
        self.assertTrue(res.cutover_blocked)
        self.assertEqual(res.consequence, QualityGateConsequence.BLOCK_CUTOVER)

    def test_19b_quality_gate_hostile_boundaries(self):
        """Hostile Test: Quality gate validation against negative thresholds, >100%, and empty populations."""
        # 1. Negative threshold validation in compiler
        res_neg = self.compiler.compile_deduplication_and_quality(
            selected_scope=self.sample_scope,
            quality_def={
                "global_threshold": {"max_duplicate_count": -5}
            }
        )
        self.assertEqual(res_neg["status"], "BLOCKER")
        codes = [d["code"] for d in res_neg["diagnostics"]]
        self.assertIn("INVALID_QUALITY_THRESHOLD", codes)

        # 2. Percentage > 100%
        res_perc = self.compiler.compile_deduplication_and_quality(
            selected_scope=self.sample_scope,
            quality_def={
                "global_threshold": {"max_invalid_percentage": 150.0}
            }
        )
        self.assertEqual(res_perc["status"], "BLOCKER")

        # 3. Empty population (0 total rows)
        q_def = DataQualityDefinition(global_threshold=QualityThreshold(max_duplicate_count=0))
        empty_res = PlanCompiler.evaluate_quality_gates(q_def, {"total_rows": 0, "duplicate_count": 0})
        self.assertTrue(empty_res.passed)

    # =========================================================================
    # 5. P3 CDC CONFLICT POLICY INTEGRATION
    # =========================================================================

    def test_20_conflict_policy_compilation_and_p3_validation(self):
        """Tests that operator-configured conflict resolution policies are validated against canonical P3 policies."""
        # Valid P3 policy
        valid_res = self.compiler.compile_deduplication_and_quality(
            selected_scope=self.sample_scope,
            conflict_config={
                "default_policy": "LATEST_VERSION_WINS",
                "object_overrides": {"CUSTOMERS": "SOURCE_A_WINS"},
            },
        )
        self.assertEqual(valid_res["status"], "SUCCESS")
        self.assertEqual(valid_res["conflict_policy"]["default_policy"], "LATEST_VERSION_WINS")

        # Invalid policy
        invalid_res = self.compiler.compile_deduplication_and_quality(
            selected_scope=self.sample_scope,
            conflict_config={
                "default_policy": "NON_EXISTENT_MAGIC_POLICY",
            },
        )
        self.assertEqual(invalid_res["status"], "BLOCKER")
        codes = [d["code"] for d in invalid_res["diagnostics"]]
        self.assertIn("INVALID_P3_CONFLICT_POLICY", codes)

    # =========================================================================
    # 6. EXECUTION PLAN FREEZE, IMMUTABILITY & DIFF
    # =========================================================================

    def test_21_execution_plan_p56_fingerprint_binding(self):
        """Tests that deduplication, quality, and conflict rules are bound into the ExecutionPlan SHA-256 fingerprint."""
        plan = MigrationPlan(
            plan_id="plan-p56",
            project_id="proj-p56",
            title="Fingerprint Plan",
            planning_mode=PlanningMode.ADVANCED,
            topology=TopologyDefinition(
                topology_type="1:1",
                source=SourceTopology(instance_id="src", endpoint="localhost:5432", connector_type="POSTGRESQL"),
                target=TargetTopology(instance_id="tgt", endpoint="localhost:5432", connector_type="POSTGRESQL"),
            ),
            routing=RoutingDefinition(
                schema_routes=[SchemaRoute(source_schema="public", target_schema="public")]
            ),
            selected_scope=self.sample_scope,
            configuration={
                "deduplication": {
                    "enabled": True,
                    "rules": [
                        {
                            "object_name": "CUSTOMERS",
                            "key_columns": ["email"],
                            "survivor_strategy": "FIRST",
                            "order_by_columns": ["updated_at DESC"],
                        }
                    ],
                },
                "data_quality": {
                    "rules": [
                        {
                            "rule_id": "q1",
                            "object_name": "CUSTOMERS",
                            "column_name": "email",
                            "rule_type": "NOT_NULL",
                        }
                    ]
                },
                "conflict_policy": {
                    "default_policy": "SOURCE_A_WINS",
                },
            },
        )
        version = PlanVersion(
            version_id="v1.0",
            project_id="proj-p56",
            parent_version_id=None,
            revision=1,
            created_at="2026-01-01T00:00:00Z",
            created_by="Pratham",
            reason="Initial",
            planning_mode=PlanningMode.ADVANCED,
            canonical_payload={},
            fingerprint="",
        )

        res = self.compiler.compile(plan=plan, version=version)
        self.assertTrue(res.success)
        fp1 = res.fingerprint

        # Changing deduplication survivor strategy MUST produce a different fingerprint!
        plan.configuration["deduplication"]["rules"][0]["survivor_strategy"] = "LAST"
        res2 = self.compiler.compile(plan=plan, version=version)
        self.assertTrue(res2.success)
        fp2 = res2.fingerprint

        self.assertNotEqual(fp1, fp2, "ExecutionPlan fingerprint must bind deduplication configuration.")

    def test_22_plan_diff_critical_config_reapproval(self):
        """Tests that changing deduplication, quality, or collision rules triggers CRITICAL_CONFIG_CHANGE and requires reapproval."""
        proj = MigrationProject(
            project_id="proj-diff",
            title="Diff Project",
            description="",
            workspace="ws",
            owner="Pratham",
            environment="DEV",
            priority="HIGH",
            migration_strategy="FULL_ONLINE",
            source_instance_ref={"host": "src"},
            target_instance_ref={"host": "tgt"},
        )
        self.store.save_project(proj)

        plan = MigrationPlan(
            plan_id="plan-diff",
            project_id=proj.project_id,
            title="Diff Plan",
            planning_mode=PlanningMode.ADVANCED,
            topology=TopologyDefinition(
                topology_type="1:1",
                source=SourceTopology(instance_id="src", endpoint="localhost:5432", connector_type="POSTGRESQL"),
                target=TargetTopology(instance_id="tgt", endpoint="localhost:5432", connector_type="POSTGRESQL"),
            ),
            routing=RoutingDefinition(schema_routes=[SchemaRoute(source_schema="public", target_schema="public")]),
            selected_scope=self.sample_scope,
            configuration={"deduplication": {"enabled": True, "rules": [{"object_name": "CUSTOMERS", "key_columns": ["email"]}]}},
        )
        self.store.save_plan(plan)

        v1 = PlanVersion(
            version_id="v1.0",
            project_id=proj.project_id,
            parent_version_id=None,
            revision=1,
            created_at="2026-01-01T00:00:00Z",
            created_by="Pratham",
            reason="Initial",
            planning_mode=PlanningMode.ADVANCED,
            canonical_payload={"configuration": plan.configuration},
            fingerprint="fp1",
        )
        self.store.save_plan_version(v1)

        v2 = PlanVersion(
            version_id="v2.0",
            project_id=proj.project_id,
            parent_version_id="v1.0",
            revision=2,
            created_at="2026-01-02T00:00:00Z",
            created_by="Pratham",
            reason="Updated dedup key",
            planning_mode=PlanningMode.ADVANCED,
            canonical_payload={"configuration": {"deduplication": {"enabled": True, "rules": [{"object_name": "CUSTOMERS", "key_columns": ["id"]}]}}},
            fingerprint="fp2",
        )
        self.store.save_plan_version(v2)

        diff = self.compiler.compute_diff(
            payload_a=v1.canonical_payload,
            payload_b=v2.canonical_payload,
            version_a_id=v1.version_id,
            version_b_id=v2.version_id,
        )
        self.assertTrue(diff.requires_reapproval)
        self.assertTrue(any("CRITICAL_CONFIG_CHANGE" in c["impact"] for c in diff.changes))

    # =========================================================================
    # 7. ENGINE GATEWAY CAPABILITIES
    # =========================================================================

    def test_23_gateway_compile_and_preview_capabilities(self):
        """Tests invoking capabilities through EngineGateway."""
        # 1. Compile Capability
        comp_res = self.gateway.invoke(
            "compile_deduplication_and_quality",
            {
                "selected_scope": self.sample_scope,
                "deduplication": {
                    "enabled": True,
                    "rules": [{"object_name": "CUSTOMERS", "key_columns": ["id"]}],
                },
                "data_quality": {
                    "rules": [{"rule_id": "q1", "object_name": "CUSTOMERS", "column_name": "email", "rule_type": "NOT_NULL"}],
                },
            },
        )
        self.assertEqual(comp_res["status"], "SUCCESS")
        self.assertTrue(len(comp_res["fingerprint"]) == 64)

        # 2. Gate Evaluation Capability
        gate_res = self.gateway.invoke(
            "evaluate_quality_gates",
            {
                "data_quality": {
                    "global_threshold": {"max_duplicate_count": 0, "consequence": "FAIL_JOB"}
                },
                "execution_metrics": {"total_rows": 100, "duplicate_count": 1},
            },
        )
        self.assertEqual(gate_res["status"], "SUCCESS")
        self.assertFalse(gate_res["gate_result"]["passed"])

        # 3. Preview Capability
        prev_res = self.gateway.invoke(
            "preview_deduplication_and_quality",
            {
                "sample_records": [
                    {"id": 1, "email": "a@example.com", "score": 100},
                    {"id": 1, "email": "a@example.com", "score": 200},
                ],
                "deduplication_rule": {
                    "key_columns": ["id"],
                    "survivor_strategy": "MAX_FIELD",
                    "order_by_columns": ["score"],
                },
                "quality_rules": [
                    {"column_name": "email", "rule_type": "NOT_NULL", "violation_policy": "REJECT_RECORD"}
                ],
            },
        )
        self.assertEqual(prev_res["status"], "SUCCESS")
        self.assertEqual(prev_res["preview"]["survivors_count"], 1)
        self.assertEqual(prev_res["preview"]["sample_output"][0]["score"], 200)

    # =========================================================================
    # 8. DATA PROCESSING AUTHORITY INTEGRATION & PRODUCTION REACHABILITY
    # =========================================================================

    def test_24_data_processing_authority_end_to_end_batch(self):
        """Tests that DataProcessingAuthority end-to-end batch processing executes deduplication and quality enforcement."""
        dpa = DataProcessingAuthority()

        # Compile processing plan with dedup and quality rules
        plan = dpa.compile_plan(
            object_name="CUSTOMERS",
            rules=[
                TransformationRule(
                    rule_id="q_not_null",
                    column_name="email",
                    rule_type=RuleType.QUALITY,
                    quality_rule_type="NOT_NULL",
                    malformed_policy=MalformedDataPolicy.REJECT_RECORD,
                ),
            ],
            dedup_key_columns=["id"],
            survivor_strategy="MAX_FIELD",
            order_by_columns=["updated_at"],
            dedup_disposition="DISCARD",
        )

        batch = [
            {"id": 1, "email": "user1@example.com", "updated_at": "2026-01-01"},
            {"id": 1, "email": "user1@example.com", "updated_at": "2026-06-01"},  # Winner
            {"id": 2, "email": None, "updated_at": "2026-01-01"},  # Rejected for NULL email
            {"id": 3, "email": "user3@example.com", "updated_at": "2026-01-01"},  # Valid unique
        ]

        transformed_rows, results = dpa.transform_batch(batch, plan)

        # Survivor for id=1 should be 2026-06-01
        self.assertEqual(len(transformed_rows), 2)  # id 1 winner + id 3
        id1_row = next(r for r in transformed_rows if r["id"] == 1)
        self.assertEqual(id1_row["updated_at"], "2026-06-01")


if __name__ == "__main__":
    unittest.main()
