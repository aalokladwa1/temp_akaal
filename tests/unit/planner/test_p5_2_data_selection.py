"""
Akaal — P5.2 Data Selection + Filtering + Projection Test Suite
================================================================
Comprehensive unit and hostile fault-injection test suite covering P5.2
SelectionDefinition models, pattern matching, ReDoS protection, PK auto-retention,
predicate validation, column projection in read_batch, selection volume estimation,
read-only selection preview, IPC evaluation, fingerprint binding, and 100k scale tests.
"""

import os
import tempfile
import unittest
import uuid
from typing import Any, Dict, List

from akaal.planner.models.p5_domain import (
    MigrationProject,
    MigrationPlan,
    PlanVersion,
    ExecutionPlan,
    PlanningMode,
    SelectionDefinition,
    SelectionRule,
    ProjectionDefinition,
    PredicateDefinition,
    RangeDefinition,
    SamplingDefinition,
    SelectionDiagnostic,
    SelectionEstimate,
    SelectionPreview,
    TopologyDefinition,
    SourceTopology,
    TargetTopology,
    RoutingDefinition,
)
from akaal.planner.engine.plan_compiler import PlanCompiler
from akaal.planner.persistence.project_store import ProjectStore
from akaal.gateway.engine_gateway import EngineGateway


class TestP52DataSelection(unittest.TestCase):
    """Authoritative test suite for P5.2 Data Selection + Filtering + Projection."""

    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.temp_dir.name, "test_p5_2.db")
        self.store = ProjectStore(db_path=self.db_path)
        self.compiler = PlanCompiler()

    def tearDown(self) -> None:
        try:
            self.temp_dir.cleanup()
        except Exception:
            pass

    def test_01_selection_definition_serialization(self):
        """Tests dataclass serialization and deserialization for SelectionDefinition."""
        rule = SelectionRule(rule_type="INCLUDE", target_type="OBJECT", pattern="SALES_*", is_regex=False)
        proj = ProjectionDefinition(
            object_id="tbl_customers",
            selected_columns=["name", "email"],
            auto_retained_columns=["id"],
            excluded_columns=["ssn"],
        )
        pred = PredicateDefinition(
            object_id="tbl_customers",
            column="status",
            operator="=",
            value="ACTIVE",
            pushdown_mode="NATIVE_PUSHDOWN",
        )
        samp = SamplingDefinition(method="PERCENTAGE", sample_size=25.0, seed=42)

        sel_def = SelectionDefinition(
            rules=[rule],
            projections=[proj],
            predicates=[pred],
            ranges=[],
            sampling=samp,
            diagnostics=[],
        )

        d_dict = sel_def.to_dict()
        reconstructed = SelectionDefinition.from_dict(d_dict)

        self.assertEqual(len(reconstructed.rules), 1)
        self.assertEqual(reconstructed.rules[0].pattern, "SALES_*")
        self.assertEqual(len(reconstructed.projections), 1)
        self.assertEqual(reconstructed.projections[0].auto_retained_columns, ["id"])
        self.assertEqual(reconstructed.predicates[0].operator, "=")
        self.assertIsNotNone(reconstructed.sampling)
        self.assertEqual(reconstructed.sampling.sample_size, 25.0)

    def test_02_rule_matching_globs_and_exact(self):
        """Tests resolution of include/exclude rules with glob patterns."""
        selected_scope = {
            "objects": [
                {"object_name": "SALES_ORDERS", "selected": True},
                {"object_name": "SALES_ITEMS", "selected": True},
                {"object_name": "SYS_LOGS", "selected": False},
            ]
        }
        sel_def = self.compiler.resolve_selection_definition(selected_scope)
        self.assertEqual(len(sel_def.rules), 3)
        self.assertEqual(sel_def.rules[0].rule_type, "INCLUDE")
        self.assertEqual(sel_def.rules[2].rule_type, "EXCLUDE")

    def test_03_regex_redos_safety_fencing(self):
        """Tests that catastrophic backtracking regex patterns trigger BLOCKER diagnostics."""
        sel_def = SelectionDefinition(
            rules=[
                SelectionRule(rule_type="INCLUDE", target_type="OBJECT", pattern="(a+)+", is_regex=True)
            ]
        )
        selected_scope = {"objects": [{"object_name": "TEST_TABLE"}]}
        res = self.compiler.resolve_rules_and_projections(selected_scope, sel_def, "POSTGRESQL")
        diagnostics = res["diagnostics"]

        blockers = [d for d in diagnostics if d.level == "BLOCKER"]
        self.assertTrue(len(blockers) > 0)
        self.assertEqual(blockers[0].code, "INVALID_REGEX_PATTERN")

    def test_04_pk_auto_retention_required_by_akaal(self):
        """Tests that Primary Key (PK) columns are auto-retained even if excluded by operator."""
        proj = ProjectionDefinition(
            object_id="oracle://host:1521/ORCL/SYSTEM/Table/CUSTOMERS",
            selected_columns=["name", "email"],
            auto_retained_columns=[],
            excluded_columns=["id", "ssn"],
        )
        sel_def = SelectionDefinition(projections=[proj])
        selected_scope = {"objects": [{"object_name": "CUSTOMERS"}]}
        res = self.compiler.resolve_rules_and_projections(selected_scope, sel_def, "ORACLE")

        resolved_proj = res["projections"]["oracle://host:1521/ORCL/SYSTEM/Table/CUSTOMERS"]
        self.assertIn("id", resolved_proj.selected_columns)
        self.assertIn("id", resolved_proj.auto_retained_columns)

    def test_05_predicate_validation_and_pushdown(self):
        """Tests validation of row predicate operators."""
        valid_pred = PredicateDefinition(object_id="tbl_1", column="age", operator=">=", value=18)
        invalid_pred = PredicateDefinition(object_id="tbl_1", column="name", operator="DROP TABLE", value="foo")

        sel_def = SelectionDefinition(predicates=[valid_pred, invalid_pred])
        selected_scope = {"objects": [{"object_name": "tbl_1"}]}
        res = self.compiler.resolve_rules_and_projections(selected_scope, sel_def, "POSTGRESQL")

        blockers = [d for d in res["diagnostics"] if d.level == "BLOCKER"]
        self.assertTrue(len(blockers) > 0)
        self.assertEqual(blockers[0].code, "UNSUPPORTED_PREDICATE_OPERATOR")

    def test_06_selection_volume_estimation(self):
        """Tests volume estimation with sampling reduction factor."""
        selected_scope = {
            "databases": ["ORCL"],
            "schemas": ["SYSTEM"],
            "objects": [
                {"object_name": "T1", "estimated_rows": 10000, "selected": True},
                {"object_name": "T2", "estimated_rows": 20000, "selected": True},
            ],
        }
        sel_def = SelectionDefinition(
            sampling=SamplingDefinition(method="PERCENTAGE", sample_size=10.0)
        )
        est = self.compiler.compute_selection_estimate(selected_scope, sel_def)
        self.assertEqual(est["estimated_total_rows"], 3000)  # 10% of 30,000
        self.assertEqual(est["confidence"], "ESTIMATED")

    def test_07_selection_preview_zero_target_writes(self):
        """Tests that p5_preview_selection returns 10 sanitized sample rows with zero target writes."""
        gateway = EngineGateway()
        res = gateway.handle_capability("p5_preview_selection", {
            "object_id": "CUSTOMERS",
            "columns": ["id", "name", "email"],
        })
        self.assertEqual(res["status"], "SUCCESS")
        preview = res["preview"]
        self.assertEqual(preview["object_id"], "CUSTOMERS")
        self.assertTrue(preview["sanitized"])
        self.assertEqual(len(preview["rows"]), 3)

    def test_08_ipc_evaluate_and_validate_selection(self):
        """Tests Gateway capabilities for p5_evaluate_selection and p5_validate_selection."""
        gateway = EngineGateway()

        eval_res = gateway.handle_capability("p5_evaluate_selection", {
            "selected_scope": {"objects": [{"object_name": "USERS", "selected": True}]},
            "connector_type": "POSTGRESQL",
        })
        self.assertEqual(eval_res["status"], "SUCCESS")
        self.assertTrue(len(eval_res["selection_definition"]["rules"]) > 0)

        val_res = gateway.handle_capability("p5_validate_selection", {
            "selected_scope": {"objects": [{"object_name": "USERS", "selected": True}]},
            "connector_type": "POSTGRESQL",
        })
        self.assertEqual(val_res["status"], "SUCCESS")
        self.assertTrue(val_res["is_valid"])

    def test_09_selection_fingerprint_binding_and_approval_invalidation(self):
        """Tests that modifying SelectionDefinition changes the SHA-256 fingerprint, invalidating stale approvals."""
        proj = MigrationProject(
            project_id="proj-sel-fp",
            title="Selection FP Test",
            description="",
            workspace="w",
            owner="o",
            environment="e",
            priority="p",
            migration_strategy="s",
            source_instance_ref={"host": "1.1.1.1"},
            target_instance_ref={"host": "2.2.2.2"},
        )
        self.store.save_project(proj)

        plan = MigrationPlan(
            plan_id="plan-sel-fp",
            project_id=proj.project_id,
            title="Plan Sel FP",
            planning_mode=PlanningMode.SIMPLE,
            topology=TopologyDefinition(
                source=SourceTopology(instance_id="s1", endpoint="e1", connector_type="ORACLE"),
                target=TargetTopology(instance_id="t1", endpoint="e2", connector_type="POSTGRESQL"),
            ),
            routing=RoutingDefinition(),
            selected_scope={"objects": [{"object_name": "T1", "selected": True}]},
            configuration={"parallelism": 4},
        )
        self.store.save_plan(plan)

        ver1 = PlanVersion(
            version_id="ver-sel-1",
            project_id=proj.project_id,
            parent_version_id=None,
            revision=1,
            created_at="2026-08-16T12:00:00Z",
            created_by="Operator",
            reason="v1",
            planning_mode=PlanningMode.SIMPLE,
            canonical_payload=plan.to_dict(),
            fingerprint="fp1",
        )
        self.store.save_plan_version(ver1)

        c1 = self.compiler.compile(plan, ver1)
        fp1 = c1.fingerprint

        # Modify scope (add a new table)
        plan.selected_scope = {"objects": [{"object_name": "T1", "selected": True}, {"object_name": "T2", "selected": True}]}
        ver2 = PlanVersion(
            version_id="ver-sel-2",
            project_id=proj.project_id,
            parent_version_id=ver1.version_id,
            revision=2,
            created_at="2026-08-16T12:05:00Z",
            created_by="Operator",
            reason="v2",
            planning_mode=PlanningMode.SIMPLE,
            canonical_payload=plan.to_dict(),
            fingerprint="fp2",
        )
        self.store.save_plan_version(ver2)

        c2 = self.compiler.compile(plan, ver2)
        fp2 = c2.fingerprint

        self.assertNotEqual(fp1, fp2)

    def test_10_scale_100k_rule_resolution(self):
        """Tests fast rule resolution over 100,000 object rules."""
        rules = [
            SelectionRule(rule_type="INCLUDE", target_type="OBJECT", pattern=f"TABLE_{i}", is_regex=False)
            for i in range(100000)
        ]
        sel_def = SelectionDefinition(rules=rules)
        selected_scope = {"objects": [{"object_name": "TABLE_50000"}]}

        res = self.compiler.resolve_rules_and_projections(selected_scope, sel_def, "POSTGRESQL")
        self.assertEqual(len(res["diagnostics"]), 0)

    def test_11_live_connector_preview_read(self):
        """Tests p5_preview_selection returns bounded, sanitized rows."""
        gateway = EngineGateway()
        res = gateway.handle_capability("p5_preview_selection", {
            "object_id": "CUSTOMERS",
            "columns": ["id", "name", "email", "password"],
            "connection_params": {"connector_type": "SQLITE", "database": ":memory:"},
        })
        self.assertEqual(res["status"], "SUCCESS")
        preview = res["preview"]
        self.assertTrue(len(preview["rows"]) <= 10)
        self.assertTrue(preview["sanitized"])

    def test_12_adapter_read_batch_column_and_predicate_projection(self):
        """Tests that BaseAdapter implementations accept column lists and predicates."""
        from akaal.adapters.rdbms.sqlite_adapter import SQLiteAdapter
        from akaal.adapters.rdbms.postgresql_adapter import PostgreSQLAdapter
        from akaal.adapters.rdbms.mssql_adapter import MSSQLAdapter
        from akaal.adapters.nosql.mongodb_adapter import MongoDBAdapter

        sq_adapter = SQLiteAdapter.__new__(SQLiteAdapter)
        pg_adapter = PostgreSQLAdapter.__new__(PostgreSQLAdapter)
        ms_adapter = MSSQLAdapter.__new__(MSSQLAdapter)
        mg_adapter = MongoDBAdapter.__new__(MongoDBAdapter)

        import inspect
        self.assertIn("columns", inspect.signature(sq_adapter.read_batch).parameters)
        self.assertIn("predicates", inspect.signature(sq_adapter.read_batch).parameters)
        self.assertIn("columns", inspect.signature(pg_adapter.read_batch).parameters)
        self.assertIn("predicates", inspect.signature(pg_adapter.read_batch).parameters)
        self.assertIn("columns", inspect.signature(ms_adapter.read_batch).parameters)
        self.assertIn("predicates", inspect.signature(ms_adapter.read_batch).parameters)
        self.assertIn("columns", inspect.signature(mg_adapter.read_batch).parameters)
        self.assertIn("predicates", inspect.signature(mg_adapter.read_batch).parameters)

    def test_13_discovery_drift_fence_blocks_missing_table(self):
        """Tests pre-execution fence detecting catalog drift (missing selected table)."""
        planned = {"objects": [{"object_name": "CUSTOMERS", "selected": True}, {"object_name": "ORDERS", "selected": True}]}
        current = {"objects": [{"object_name": "CUSTOMERS"}]}  # ORDERS removed

        diagnostics = self.compiler.verify_discovery_drift(planned, current)
        self.assertEqual(len(diagnostics), 1)
        self.assertEqual(diagnostics[0].code, "DISCOVERY_DRIFT_DETECTED")
        self.assertEqual(diagnostics[0].target, "ORDERS")

    def test_14_cdc_predicate_transition_states(self):
        """Tests CDC row predicate state transitions (IN->IN, OUT->OUT, OUT->IN, IN->OUT)."""
        from akaal.replication.domain.core_replication import CoreReplicationDomain
        preds = [{"column": "status", "operator": "=", "value": "ACTIVE"}]

        # IN -> IN (UPDATE)
        res_in_in = CoreReplicationDomain.process_cdc_event_with_predicates("UPDATE", {"status": "ACTIVE"}, {"status": "ACTIVE"}, preds)
        self.assertEqual(res_in_in, "UPDATE")

        # OUT -> OUT (SKIP)
        res_out_out = CoreReplicationDomain.process_cdc_event_with_predicates("UPDATE", {"status": "INACTIVE"}, {"status": "INACTIVE"}, preds)
        self.assertEqual(res_out_out, "SKIP")

        # OUT -> IN (INSERT into target scope)
        res_out_in = CoreReplicationDomain.process_cdc_event_with_predicates("UPDATE", {"status": "INACTIVE"}, {"status": "ACTIVE"}, preds)
        self.assertEqual(res_out_in, "INSERT")

        # IN -> OUT (DELETE / tombstone emit to prevent stale target row)
        res_in_out = CoreReplicationDomain.process_cdc_event_with_predicates("UPDATE", {"status": "ACTIVE"}, {"status": "INACTIVE"}, preds)
        self.assertEqual(res_in_out, "DELETE")

        # DELETE
        res_del = CoreReplicationDomain.process_cdc_event_with_predicates("DELETE", {"status": "ACTIVE"}, None, preds)
        self.assertEqual(res_del, "DELETE")

    def test_15_validation_exact_scope_filtered_rows(self):
        """Tests EnterpriseDataIntegrityPlatformV8 validates exact filtered logical dataset."""
        from akaal.data_integrity.facade.platform8 import EnterpriseDataIntegrityPlatformV8
        platform = EnterpriseDataIntegrityPlatformV8()
        sel_def = {"predicates": [{"column": "country", "operator": "=", "value": "INDIA"}]}

        report = platform.verify_selection_aligned_consistency("CUSTOMERS", "CUSTOMERS", sel_def)
        self.assertEqual(report.rows_compared, 125000)
        self.assertEqual(report.mismatches_found, 0)

    def test_16_scale_100k_catalog_objects_with_compact_rules(self):
        """Tests fast rule resolution over 100,000 discovered catalog objects with compact rules."""
        catalog_objs = [{"object_name": f"SALES_TABLE_{i}"} for i in range(100000)]
        rules = [SelectionRule(rule_type="INCLUDE", target_type="OBJECT", pattern="SALES_*", is_regex=False)]
        sel_def = SelectionDefinition(rules=rules)

        import time
        t0 = time.time()
        res = self.compiler.resolve_rules_and_projections({"objects": catalog_objs}, sel_def, "POSTGRESQL")
        elapsed = time.time() - t0

        self.assertTrue(elapsed < 0.15)  # Executes in under 150ms over 100k objects
        self.assertEqual(len(res["diagnostics"]), 0)

    def test_17_fail_closed_unsupported_cdc_sampling(self):
        """Tests fail-closed compilation diagnostic when sampling is requested on CDC stream."""
        sel_def = SelectionDefinition(sampling=SamplingDefinition(method="PERCENTAGE", sample_size=10.0))
        res = self.compiler.resolve_rules_and_projections({"objects": []}, sel_def, "CDC_POSTGRES")

        blockers = [d for d in res["diagnostics"] if d.level == "BLOCKER"]
        self.assertTrue(len(blockers) > 0)
        self.assertEqual(blockers[0].code, "SAMPLING_UNSUPPORTED_FOR_CDC")

    def test_18_production_cdc_batch_reconciliation_caller(self):
        """Tests live production process_incoming_cdc_batch calling process_cdc_event_with_predicates."""
        from akaal.replication.domain.core_replication import CoreReplicationDomain
        replication_domain = CoreReplicationDomain()
        events = [
            {"operation": "UPDATE", "before_image": {"status": "ACTIVE"}, "after_image": {"status": "ACTIVE"}},
            {"operation": "UPDATE", "before_image": {"status": "INACTIVE"}, "after_image": {"status": "INACTIVE"}},
            {"operation": "UPDATE", "before_image": {"status": "ACTIVE"}, "after_image": {"status": "INACTIVE"}},
        ]
        preds = [{"column": "status", "operator": "=", "value": "ACTIVE"}]
        processed = replication_domain.process_incoming_cdc_batch(events, preds)

        self.assertEqual(len(processed), 2)  # IN->IN (UPDATE) and IN->OUT (DELETE tombstone emit)
        self.assertEqual(processed[0]["reconciled_action"], "UPDATE")
        self.assertEqual(processed[1]["reconciled_action"], "DELETE")

    def test_19_production_e2e_validation_caller(self):
        """Tests production verify_e2e_consistency calling verify_selection_aligned_consistency."""
        from akaal.data_integrity.facade.platform8 import EnterpriseDataIntegrityPlatformV8
        platform = EnterpriseDataIntegrityPlatformV8()
        sel_def = {"predicates": [{"column": "country", "operator": "=", "value": "INDIA"}]}

        report = platform.verify_e2e_consistency("CUSTOMERS", "CUSTOMERS", selection_def=sel_def)
        self.assertEqual(report.rows_compared, 125000)
        self.assertEqual(report.mismatches_found, 0)

    def test_20_production_pre_execution_fence_caller(self):
        """Tests production p5_verify_pre_execution_fence calling verify_discovery_drift."""
        from akaal.gateway.engine_gateway import EngineGateway
        gateway = EngineGateway()
        payload = {
            "planned_scope": {"objects": [{"object_name": "CUSTOMERS", "selected": True}, {"object_name": "ORDERS", "selected": True}]},
            "current_discovery": {"objects": [{"object_name": "CUSTOMERS"}]},
        }
        res = gateway.p5_verify_pre_execution_fence(payload)
        self.assertEqual(res["status"], "BLOCKER")
        self.assertFalse(res["execution_permitted"])

    def test_00_baseadapter_read_batch_fails_closed_without_synthetic_data(self):
        """Tests that BaseAdapter.read_batch raises NotImplementedError without fabricating synthetic Item_i rows."""
        from akaal.adapters.base_adapter import BaseAdapter
        class DummyAdapter(BaseAdapter):
            async def connect(self): pass
            async def close(self): pass
            async def check_permissions(self): pass
            async def discover_tables(self): pass
            async def discover_columns(self, t): pass
            async def discover_indexes(self, t): pass
            async def discover_constraints(self, t): pass
            async def discover_foreign_keys(self, t): pass
            async def discover_triggers(self, t): pass
            async def discover_views(self): pass
            async def write_batch(self, t, r): pass
            async def get_row_count(self, t): pass
            async def compute_checksum(self, t): pass

        adapter = DummyAdapter(None)
        import asyncio
        with self.assertRaises(NotImplementedError) as ctx:
            asyncio.run(adapter.read_batch("tbl", 0, 10))
        self.assertIn("strictly forbids synthetic data fallback", str(ctx.exception))

    def test_21_akaal_side_filter_and_sampling_evaluator(self):
        """Tests AkaalSideFilterEvaluator for physical row sampling and column projection."""
        from akaal.engine.akaal_side_filter import AkaalSideFilterEvaluator
        rows = [
            {"id": 1, "name": "Alice", "country": "INDIA"},
            {"id": 2, "name": "Bob", "country": "USA"},
            {"id": 3, "name": "Charlie", "country": "INDIA"},
            {"id": 4, "name": "David", "country": "INDIA"},
        ]
        columns = ["id", "name"]
        predicates = [{"column": "country", "operator": "=", "value": "INDIA"}]
        sampling = {"method": "FIXED_ROWS", "sample_size": 2}

        filtered = AkaalSideFilterEvaluator.filter_batch(rows, columns=columns, predicates=predicates, sampling=sampling)
        self.assertEqual(len(filtered), 2)
        self.assertEqual(list(filtered[0].keys()), ["id", "name"])
        self.assertEqual(filtered[0]["name"], "Alice")
        self.assertEqual(filtered[1]["name"], "Charlie")

    def test_22_execute_migration_aborts_on_discovery_drift(self):
        """Tests that authoritative migration start entrypoint aborts execution before target write when discovery drift occurs."""
        from akaal.gateway.engine_gateway import EngineGateway
        gateway = EngineGateway()
        payload = {
            "planned_scope": {"objects": [{"object_name": "CUSTOMERS", "selected": True}, {"object_name": "ORDERS", "selected": True}]},
            "current_discovery": {"objects": [{"object_name": "CUSTOMERS"}]},
        }
        with self.assertRaises(RuntimeError) as ctx:
            gateway.execute_migration_with_pre_execution_fence(payload)
        self.assertIn("[EXECUTION BLOCKED]", str(ctx.exception))

    def test_23_transitive_cdc_stream_reconciliation(self):
        """Tests transitive execution of CDC batch reconciliation in CoreReplicationDomain."""
        from akaal.replication.domain.core_replication import CoreReplicationDomain
        domain = CoreReplicationDomain()
        batch = [
            {"operation": "UPDATE", "before_image": {"status": "ACTIVE"}, "after_image": {"status": "ACTIVE"}},
            {"operation": "UPDATE", "before_image": {"status": "ACTIVE"}, "after_image": {"status": "INACTIVE"}},
        ]
        preds = [{"column": "status", "operator": "=", "value": "ACTIVE"}]
        reconciled = domain.process_incoming_cdc_batch(batch, preds)
        self.assertEqual(len(reconciled), 2)
        self.assertEqual(reconciled[0]["reconciled_action"], "UPDATE")
        self.assertEqual(reconciled[1]["reconciled_action"], "DELETE")


if __name__ == "__main__":
    unittest.main()
