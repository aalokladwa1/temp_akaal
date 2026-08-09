import unittest
from akaal.gateway.engine_gateway import EngineGateway
from akaal.migration.target_identifier import validate_operator_configured_identifier, derive_akaal_generated_target_mapping
from akaal.workflow.steps.migration_steps import SchemaExecutionStep
from akaal.workflow.models.context import WorkflowContext

class TestP010AcceptanceGuard(unittest.TestCase):

    def setUp(self):
        self.gateway = EngineGateway()

    def test_01_run_preflight_invokes_benchmarks_and_produces_eta(self):
        res = self.gateway.invoke("run_preflight", {
            "source_engine": "ORACLE",
            "target_engine": "POSTGRESQL",
            "source_host": "localhost",
            "source_port": 1521,
            "target_host": "localhost",
            "target_port": 5432
        })
        self.assertIn(res.get("preflight_status"), ["PASSED", "FAILED"])
        self.assertIn("source_read_benchmark", res)
        self.assertIn("target_write_benchmark", res)
        self.assertIn("eta_confidence", res)

    def test_02_pg_analytics_cannot_survive_into_executable_ddl(self):
        mapping = derive_akaal_generated_target_mapping("pg_analytics")
        self.assertTrue(mapping["remapped"])
        self.assertEqual(mapping["target_schema"], "app_analytics")

    def test_03_invalid_operator_pg_schema_rejected(self):
        res = validate_operator_configured_identifier("pg_analytics", "schema")
        self.assertFalse(res["valid"])
        self.assertEqual(res["error_code"], "RESERVED_PREFIX")

    def test_04_schema_execution_step_consumes_canonical_mapping(self):
        from akaal.workflow.models.sub_contexts import ExecutionContext
        step = SchemaExecutionStep()
        context = WorkflowContext(execution_context=ExecutionContext(workflow_id="mig-test-01", run_id="run-01"))
        context.runtime_context.transient_parameters.update({
            "target_host": "localhost",
            "target_port": 5432,
            "target_db": "akaal_target",
            "selected_scope": {
                "objects": [
                    {"object_name": "CUSTOMER_RECORDS", "object_type": "Table", "target_schema": "pg_analytics"}
                ]
            }
        })
        res = step.execute(context)
        # Must execute against app_analytics cleanly, NOT pg_analytics
        self.assertTrue(res.success)

    def test_05_failed_migration_rejects_ordinary_start_transport(self):
        mig_id = "mig-failed-test-01"
        self.gateway._migrations[mig_id] = {"migration_id": mig_id, "status": "approved"}
        self.gateway._register_workflow_manifest(mig_id)
        self.gateway.state_store.set_state(f"{mig_id}_approval", {"status": "approved"}, category="governance")
        self.gateway.state_store.set_state(f"{mig_id}_status", {"status": "FAILED"}, category="runtime")
        
        res = self.gateway.invoke("start_transport", {"migration_id": mig_id})
        self.assertEqual(res.get("status"), "failed")
        self.assertEqual(res.get("error_code"), "TERMINAL_STATE_REJECTED")

    def test_06_eta_state_machine_cases(self):
        from akaal.advisor.eta_engine import ETAEngine
        tables = [{"object_name": "t1", "object_type": "Table", "estimated_rows": 1000}]

        # Case 1: BENCHMARKS_UNAVAILABLE
        c1 = ETAEngine.calculate_preflight_eta(tables, source_read_rows_per_sec=None, target_write_rows_per_sec=None)
        self.assertEqual(c1["eta_state"], "BENCHMARKS_UNAVAILABLE")
        self.assertIsNone(c1["estimated_duration_seconds"])

        # Case 2: CATALOG_VOLUME_UNAVAILABLE
        c2 = ETAEngine.calculate_preflight_eta([{"object_name": "t1", "object_type": "Table", "estimated_rows": 0}], source_read_rows_per_sec=1000.0, target_write_rows_per_sec=500.0, has_catalog_stats=False)
        self.assertEqual(c2["eta_state"], "CATALOG_VOLUME_UNAVAILABLE")
        self.assertIsNone(c2["estimated_duration_seconds"])
        self.assertIn("catalog row estimates unavailable", c2["eta_basis"])

        # Case 3: ETA_AVAILABLE
        c3 = ETAEngine.calculate_preflight_eta(tables, source_read_rows_per_sec=1000.0, target_write_rows_per_sec=500.0)
        self.assertEqual(c3["eta_state"], "ETA_AVAILABLE")
        self.assertIsNotNone(c3["estimated_duration_seconds"])

        # Case 4: PARTIALLY_MEASURED
        c4 = ETAEngine.calculate_preflight_eta(tables, source_read_rows_per_sec=1000.0, target_write_rows_per_sec=None)
        self.assertEqual(c4["eta_state"], "PARTIALLY_MEASURED")
        self.assertIsNone(c4["estimated_duration_seconds"])

        # Case 5: CATALOG_VOLUME_UNAVAILABLE for 0 catalog rows
        c5 = ETAEngine.calculate_preflight_eta([{"object_name": "t1", "object_type": "Table", "estimated_rows": 0}], source_read_rows_per_sec=1000.0, target_write_rows_per_sec=500.0, has_catalog_stats=True)
        self.assertEqual(c5["eta_state"], "CATALOG_VOLUME_UNAVAILABLE")
        self.assertIsNone(c5["estimated_duration_seconds"])

    def test_07_split_brain_target_mapping_prevention(self):
        from akaal.workflow.steps.migration_steps import DataTransportStep, ValidationStep
        from akaal.workflow.models.sub_contexts import ExecutionContext

        context = WorkflowContext(execution_context=ExecutionContext(workflow_id="mig-canonical-01", run_id="run-01"))
        context.runtime_context.transient_parameters.update({
            "target_host": "localhost",
            "target_port": 5432,
            "target_db": "akaal_target",
            "selected_scope": {
                "objects": [
                    {"object_name": "DATA_TBL_1", "object_type": "Table", "target_schema": "pg_analytics"}
                ]
            }
        })
        
        # SchemaExecutionStep, DataTransportStep, and ValidationStep MUST ALL use app_analytics
        step_exec = SchemaExecutionStep()
        res_exec = step_exec.execute(context)
        self.assertTrue(res_exec.success)

        step_trans = DataTransportStep()
        res_trans = step_trans.execute(context)
        self.assertTrue(res_trans.success)

        step_val = ValidationStep()
        res_val = step_val.execute(context)
        self.assertTrue(res_val.success)

if __name__ == "__main__":
    unittest.main()
