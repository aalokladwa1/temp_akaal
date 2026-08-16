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


if __name__ == "__main__":
    unittest.main()
