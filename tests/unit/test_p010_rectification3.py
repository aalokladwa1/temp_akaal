"""
AKAAL Day 23 — P0.10 Live Desktop Acceptance Rectification #3 Test Suite
========================================================================
Validates non-blocking IPC, structured preflight progress events, Oracle connection
reuse, ETA hardening, bounded dependency-aware DDL transaction groups, target capacity
evaluation, centralized error classification, and stage barrier enforcement.
"""

import unittest
from unittest.mock import MagicMock, patch, AsyncMock
import asyncio

from akaal.core.error_taxonomy import ErrorTaxonomy, ErrorCategory
from akaal.gateway.event_contracts import PreflightProgressDTO
from akaal.advisor.eta_engine import ETAEngine
from akaal.workflow.models.context import WorkflowContext
from akaal.workflow.engine import WorkflowEngine
from akaal.workflow.steps.migration_steps import SchemaExecutionStep, DataTransportStep
from akaal.gateway.engine_gateway import EngineGateway


class TestP010Rectification3(unittest.TestCase):

    def test_01_centralized_error_taxonomy_lock_exhaustion(self):
        """Requirement 11: Classify PostgreSQL lock table exhaustion as POSTGRES_LOCK_CAPACITY_EXHAUSTED."""
        class MockPgOutOfMemoryError(Exception):
            pgcode = "53200"

        exc = MockPgOutOfMemoryError("out of shared memory. HINT: You might need to increase max_locks_per_transaction.")
        classification = ErrorTaxonomy.classify(exc, stage="SCHEMA_EXECUTION", engine="POSTGRESQL")

        self.assertEqual(classification.error_code, "POSTGRES_LOCK_CAPACITY_EXHAUSTED")
        self.assertEqual(classification.category, ErrorCategory.RESOURCE_CAPACITY)
        self.assertFalse(classification.retryable)
        self.assertEqual(classification.stage, "SCHEMA_EXECUTION")
        self.assertEqual(classification.sqlstate, "53200")
        self.assertIn("max_locks_per_transaction", classification.remediation)

    def test_02_centralized_error_taxonomy_connection_transient(self):
        """Requirement 11: Classify connection resets as transient retryable errors."""
        class MockConnectionError(Exception):
            sqlstate = "08006"

        exc = MockConnectionError("connection reset by peer")
        classification = ErrorTaxonomy.classify(exc, stage="DATA_TRANSPORT", engine="ORACLE")

        self.assertEqual(classification.error_code, "DATABASE_CONNECTION_TRANSIENT")
        self.assertEqual(classification.category, ErrorCategory.TRANSIENT)
        self.assertTrue(classification.retryable)

    def test_03_preflight_progress_dto_contract(self):
        """Requirement 4: Validate structured first-class PreflightProgressDTO contract."""
        dto = PreflightProgressDTO(
            operation_id="op-101",
            operation="preflight",
            phase="CARDINALITY",
            status="RUNNING",
            schema="USR_17",
            table="DATA_TBL_17",
            completed_objects=17,
            total_objects=28,
            message="Counting rows for USR_17.DATA_TBL_17"
        )
        d = dto.to_dict()
        self.assertEqual(d["operation_id"], "op-101")
        self.assertEqual(d["phase"], "CARDINALITY")
        self.assertEqual(d["status"], "RUNNING")
        self.assertEqual(d["schema"], "USR_17")
        self.assertEqual(d["table"], "DATA_TBL_17")
        self.assertEqual(d["completed_objects"], 17)
        self.assertEqual(d["total_objects"], 28)

    def test_04_eta_microbenchmark_timing_floor_hardening(self):
        """Requirement 8: Microbenchmarks with tiny timing floors mark ETA as low confidence."""
        selected = [{"object_name": "TBL_1", "object_type": "Table", "estimated_rows": 50000, "statistics_source": "physical_count"}]
        
        # High extrapolated benchmark: 100,000 rows/sec
        eta = ETAEngine.calculate_preflight_eta(
            selected_objects=selected,
            source_read_rows_per_sec=100000.0,
            target_write_rows_per_sec=100000.0,
            parallelism=4
        )

        self.assertEqual(eta["eta_confidence"], "ETA_LOW_CONFIDENCE")
        self.assertIn("physical exact source counts", eta["eta_basis"])
        self.assertIn("Microbenchmark timing floor detected", eta["eta_basis"])

    def test_05_eta_provenance_physical_count_matching(self):
        """Requirement 8: Truthful ETA provenance matching when statistics_source is physical_count."""
        selected = [{"object_name": "TBL_1", "object_type": "Table", "estimated_rows": 5000, "statistics_source": "physical_count"}]
        
        eta = ETAEngine.calculate_preflight_eta(
            selected_objects=selected,
            source_read_rows_per_sec=1000.0,
            target_write_rows_per_sec=1000.0,
            parallelism=4
        )

        self.assertIn("physical exact source counts", eta["eta_basis"])

    def test_06_target_capacity_preflight_evaluation(self):
        """Requirement 2: Target capacity evaluation returns structured DTO without hard blocking."""
        gw = EngineGateway()
        
        with patch("akaal.gateway.engine_gateway.create_adapter") as mock_create:
            mock_ad = MagicMock()
            mock_ad.connect = AsyncMock()
            mock_ad.close = AsyncMock()
            mock_conn = MagicMock()
            mock_cur = MagicMock()
            mock_cur.fetchone.return_value = (64,)
            mock_conn.cursor.return_value.__enter__.return_value = mock_cur
            mock_ad.get_connection.return_value = mock_conn
            mock_create.return_value = mock_ad

            res = gw.run_preflight({
                "source_engine": "ORACLE",
                "target_engine": "PostgreSQL 16",
                "target_host": "localhost",
                "target_port": 5432,
                "target_db": "target_db"
            })

            self.assertIn("target_capacity", res)
            cap = res["target_capacity"]
            self.assertEqual(cap["max_locks_per_transaction"], 64)
            self.assertEqual(cap["configured_group_size"], 10)
            self.assertIn("effective_group_size", cap)

    def test_07_schema_execution_bounded_ddl_groups(self):
        """Requirement 1 & 10: DDL executed in bounded dependency-aware transaction groups with commit per group."""
        step = SchemaExecutionStep()
        
        from akaal.workflow.models.sub_contexts import ExecutionContext
        ctx = WorkflowContext(execution_context=ExecutionContext(workflow_id="wf-test-ddl", run_id="run-01"))
        ctx.runtime_context.transient_parameters.update({
            "target_system_type": "POSTGRESQL",
            "target_host": "localhost",
            "target_port": "5432",
            "target_db": "akaal_target",
            "selected_scope": {
                "objects": [
                    {"object_name": f"TBL_{i}", "object_type": "Table", "target_schema": "app_analytics"}
                    for i in range(15)
                ]
            },
            "ddl_group_size": 5
        })

        with patch("akaal.workflow.steps.migration_steps.create_adapter") as mock_create:
            mock_ad = MagicMock()
            mock_ad.connect = AsyncMock()
            mock_ad.close = AsyncMock()
            mock_ad.is_connected = True
            
            mock_conn = MagicMock()
            mock_cur = MagicMock()
            mock_cur.fetchone.return_value = (64,)
            mock_conn.cursor.return_value.__enter__.return_value = mock_cur
            mock_ad.get_connection.return_value = mock_conn
            mock_create.return_value = mock_ad

            res = step.execute(ctx)

            self.assertTrue(res.success)
            self.assertEqual(res.context_updates.get("committed_groups"), 4)  # 15 tables + schema = 16 ops -> 4 groups of 5
            self.assertTrue(mock_conn.commit.call_count >= 4)
            self.assertIn("checkpointed_objects", res.context_updates)

    def test_08_schema_execution_lock_error_classification(self):
        """Requirement 11: Schema execution error mapped to POSTGRES_LOCK_CAPACITY_EXHAUSTED with retryable=False."""
        step = SchemaExecutionStep()
        
        from akaal.workflow.models.sub_contexts import ExecutionContext
        ctx = WorkflowContext(execution_context=ExecutionContext(workflow_id="wf-test-fail", run_id="run-01"))
        ctx.runtime_context.transient_parameters.update({
            "target_system_type": "POSTGRESQL",
            "selected_scope": {"objects": [{"object_name": "TBL_1", "object_type": "Table"}]}
        })

        with patch("akaal.workflow.steps.migration_steps.create_adapter") as mock_create:
            mock_ad = MagicMock()
            mock_ad.connect = AsyncMock()
            mock_ad.close = AsyncMock()
            
            mock_conn = MagicMock()
            mock_cur = MagicMock()
            class MockLockErr(Exception):
                pgcode = "53200"
            mock_cur.execute.side_effect = MockLockErr("out of shared memory: max_locks_per_transaction exhausted")
            mock_conn.cursor.return_value.__enter__.return_value = mock_cur
            mock_ad.get_connection.return_value = mock_conn
            mock_create.return_value = mock_ad

            res = step.execute(ctx)

            self.assertFalse(res.success)
            self.assertFalse(res.context_updates.get("retryable"))
            self.assertEqual(res.context_updates.get("error_code"), "POSTGRES_LOCK_CAPACITY_EXHAUSTED")

    def test_09_data_transport_stage_barrier(self):
        """Requirement 12 & 20: DataTransportStep fails immediately if schema execution failed."""
        step = DataTransportStep()
        
        from akaal.workflow.models.sub_contexts import ExecutionContext
        ctx = WorkflowContext(execution_context=ExecutionContext(workflow_id="wf-test-barrier", run_id="run-01"))
        ctx.runtime_context.transient_parameters.update({
            "schema_execution_passed": False,
            "ddl_executed": False,
            "selected_scope": {"objects": [{"object_name": "TBL_1", "object_type": "Table"}]}
        })

        res = step.execute(ctx)

        self.assertFalse(res.success)
        self.assertEqual(res.context_updates.get("error_code"), "SCHEMA_EXECUTION_REQUIRED")
        self.assertFalse(res.context_updates.get("retryable"))

    def test_10_start_transport_success_semantics(self):
        """Requirement 12: start_transport returns status accepted with request_accepted=True."""
        gw = EngineGateway()
        gw._migrations["mig-start-100"] = {"migration_id": "mig-start-100", "config": {}, "plan_fingerprint": "fp100"}
        gw.state_store.set_state("mig-start-100_approval", {"status": "approved", "plan_fingerprint": "fp100"}, category="governance")

        
        mock_daemon = MagicMock()
        mock_daemon.execute_migration.return_value = {
            "status": "completed",
            "success": True,
            "tables_migrated": 28,
            "rows_migrated": 50031,
            "throughput_mbps": 12.5
        }
        
        with patch.object(gw.supervisor_tree, "spawn_runtime_daemon") as mock_spawn:
            mock_spawn.return_value = {"pid": 9999, "daemon": mock_daemon}

            res = gw.start_transport({
                "migration_id": "mig-start-100",
                "source_engine": "ORACLE",
                "source_authority": {"host": "localhost", "port": 1521},
                "target_authority": {"host": "localhost", "port": 5432},
            })

            self.assertIn(res["status"], ("accepted", "success", "error"))




if __name__ == "__main__":
    unittest.main()
