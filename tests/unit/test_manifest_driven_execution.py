import unittest
from akaal.gateway.engine_gateway import EngineGateway
from akaal.workflow.models.context import WorkflowContext
from akaal.workflow.models.sub_contexts import ExecutionContext
from akaal.workflow.steps.migration_steps import SchemaExecutionStep, DataTransportStep, ValidationStep

from tests.conftest import require_postgres

class TestManifestDrivenExecutionAndAntiSpecialCasing(unittest.TestCase):

    def setUp(self):
        require_postgres("localhost", 5432)
        self.gateway = EngineGateway()


    def _make_context(self, wfid: str, scope: dict) -> WorkflowContext:
        ctx = WorkflowContext(execution_context=ExecutionContext(workflow_id=wfid, run_id=f"run_{wfid}"))
        ctx.runtime_context.transient_parameters.update({
            "migration_id": f"mig_{wfid}",
            "selected_scope": scope
        })
        return ctx

    def test_single_table_scope_reconciliation(self):
        ctx = self._make_context("wf_single", {
            "objects": [
                {"object_name": "orders", "object_type": "Table", "target_schema": "public", "target_object_name": "orders"}
            ]
        })
        
        schema_step = SchemaExecutionStep()
        s_res = schema_step.execute(ctx)
        self.assertTrue(s_res.success)
        self.assertEqual(s_res.context_updates.get("tables_created"), 1)

        transport_step = DataTransportStep()
        t_res = transport_step.execute(ctx)
        self.assertTrue(t_res.success)
        self.assertEqual(t_res.context_updates.get("tables_migrated"), 1)

        valid_step = ValidationStep()
        v_res = valid_step.execute(ctx)
        self.assertTrue(v_res.success)
        matrix = v_res.context_updates.get("reconciliation_matrix", {})
        self.assertEqual(matrix.get("total_selected"), 1)
        self.assertEqual(matrix.get("migrated"), 1)
        self.assertTrue(matrix.get("invariant_satisfied"))

    def test_multi_table_custom_schema_scope(self):
        ctx = self._make_context("wf_multi", {
            "objects": [
                {"object_name": "products", "object_type": "Table", "target_schema": "inventory", "target_object_name": "products"},
                {"object_name": "suppliers", "object_type": "Table", "target_schema": "inventory", "target_object_name": "suppliers"},
                {"object_name": "shipments", "object_type": "Table", "target_schema": "logistics", "target_object_name": "shipments"}
            ]
        })
        
        s_res = SchemaExecutionStep().execute(ctx)
        self.assertTrue(s_res.success)
        self.assertGreaterEqual(s_res.context_updates.get("tables_created"), 3)

        t_res = DataTransportStep().execute(ctx)
        self.assertTrue(t_res.success)
        self.assertEqual(t_res.context_updates.get("tables_migrated"), 3)

        v_res = ValidationStep().execute(ctx)
        self.assertTrue(v_res.success)
        matrix = v_res.context_updates.get("reconciliation_matrix", {})
        self.assertEqual(matrix.get("total_selected"), 3)
        self.assertEqual(matrix.get("migrated"), 3)
        self.assertTrue(matrix.get("invariant_satisfied"))

    def test_mixed_object_types_scope(self):
        ctx = self._make_context("wf_mixed", {
            "objects": [
                {"object_name": "accounts", "object_type": "Table", "target_schema": "public", "target_object_name": "accounts"},
                {"object_name": "v_active_accounts", "object_type": "View", "target_schema": "public", "target_object_name": "v_active_accounts"},
                {"object_name": "seq_account_id", "object_type": "Sequence", "target_schema": "public", "target_object_name": "seq_account_id"},
                {"object_name": "sp_calc_interest", "object_type": "Procedure", "target_schema": "public", "target_object_name": "sp_calc_interest"}
            ]
        })
        
        s_res = SchemaExecutionStep().execute(ctx)
        self.assertTrue(s_res.success)

        t_res = DataTransportStep().execute(ctx)
        self.assertTrue(t_res.success)
        
        v_res = ValidationStep().execute(ctx)
        self.assertTrue(v_res.success)
        matrix = v_res.context_updates.get("reconciliation_matrix", {})
        self.assertEqual(matrix.get("total_selected"), 4)
        self.assertEqual(matrix.get("migrated"), 1) # 1 Table
        self.assertEqual(matrix.get("transformed"), 3) # 1 View + 1 Seq + 1 Proc
        self.assertTrue(matrix.get("invariant_satisfied"))

    def test_unsupported_object_type_accounting(self):
        ctx = self._make_context("wf_unsupported", {
            "objects": [
                {"object_name": "legacy_spatial_index", "object_type": "UNSUPPORTED", "target_schema": "public", "target_object_name": "legacy_spatial_index"}
            ]
        })
        
        t_res = DataTransportStep().execute(ctx)
        self.assertTrue(t_res.success)
        
        v_res = ValidationStep().execute(ctx)
        self.assertTrue(v_res.success)
        matrix = v_res.context_updates.get("reconciliation_matrix", {})
        self.assertEqual(matrix.get("total_selected"), 1)
        self.assertEqual(matrix.get("unsupported"), 1)
        self.assertTrue(matrix.get("invariant_satisfied"))

    def test_empty_scope_fallback(self):
        ctx = self._make_context("wf_empty", {"objects": []})
        
        s_res = SchemaExecutionStep().execute(ctx)
        self.assertTrue(s_res.success)

        t_res = DataTransportStep().execute(ctx)
        self.assertTrue(t_res.success)

        v_res = ValidationStep().execute(ctx)
        self.assertTrue(v_res.success)
        matrix = v_res.context_updates.get("reconciliation_matrix", {})
        self.assertEqual(matrix.get("total_selected"), 1)
        self.assertTrue(matrix.get("invariant_satisfied"))

    def test_arbitrary_custom_table_and_object_names(self):
        ctx = self._make_context("wf_custom_names", {
            "objects": [
                {"object_name": "tbl_custom_xyz_99", "object_type": "Table", "target_schema": "schema_alpha", "target_object_name": "tbl_custom_xyz_99"},
                {"object_name": "vw_custom_view_88", "object_type": "View", "target_schema": "schema_alpha", "target_object_name": "vw_custom_view_88"}
            ]
        })

        s_res = SchemaExecutionStep().execute(ctx)
        self.assertTrue(s_res.success)

        t_res = DataTransportStep().execute(ctx)
        self.assertTrue(t_res.success)

        v_res = ValidationStep().execute(ctx)
        self.assertTrue(v_res.success)
        matrix = v_res.context_updates.get("reconciliation_matrix", {})
        self.assertEqual(matrix.get("total_selected"), 2)
        self.assertEqual(matrix.get("migrated"), 1)
        self.assertEqual(matrix.get("transformed"), 1)
        self.assertTrue(matrix.get("invariant_satisfied"))

if __name__ == "__main__":
    unittest.main()
