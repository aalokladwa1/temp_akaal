"""
P1 Reality Rectification Hostile Acceptance Suite.
===================================================
Verifies Non-Negotiable Production Truth Law across P1:
- Zero fake rows written.
- Zero implicit simulation entries.
- Zero uncommitted checkpoint advancements.
- Zero mock leakage into production execution paths.
"""

import unittest
from unittest.mock import MagicMock

from akaal.engine.facade import AkaalSuperEngine, PhysicalExecutionContractError, ApprovalRequiredError
from akaal.workflow.steps.migration_steps import DataTransportStep
from akaal.workflow.models.context import WorkflowContext
from akaal.workflow.models.sub_contexts import ExecutionContext, RuntimeContext, UserContext
from akaal.replication.readers.oracle_reader import OraclePhysicalReader
from akaal.replication.readers.postgresql_reader import PostgreSQLPhysicalReader
from akaal.replication.readers.mysql_reader import MySQLPhysicalReader
from akaal.replication.readers.mssql_reader import MSSQLPhysicalReader
from akaal.replication.writers.oracle_writer import OraclePhysicalWriter
from akaal.replication.writers.postgresql_writer import PostgreSQLPhysicalWriter
from akaal.replication.writers.mysql_writer import MySQLPhysicalWriter
from akaal.replication.writers.mssql_writer import MSSQLPhysicalWriter
from akaal.engine.spec import BatchMetadata


class TestP1RealityRectificationHostileSuite(unittest.TestCase):

    def setUp(self):
        self.super_engine = AkaalSuperEngine()

    def test_01_missing_source_db_cannot_report_success(self):
        """Hostile Check 1 & 2: Missing physical connection params must fail closed."""
        spec = {"migration_id": "test-mig-01", "objects": [{"object_name": "users"}]}
        with self.assertRaises((PhysicalExecutionContractError, ApprovalRequiredError)):
            self.super_engine.execute_migration(
                workflow_id="test-mig-01",
                spec_dict=spec,
                source_params=None,
                target_params=None,
                is_synthetic_test=False,
            )

    def test_02_superengine_cannot_enter_implicit_simulation(self):
        """Hostile Check 11: Production runtime must not implicitly enter simulation mode."""
        spec = {"migration_id": "test-mig-02"}
        with self.assertRaises((PhysicalExecutionContractError, ApprovalRequiredError)):
            self.super_engine.execute_migration(
                workflow_id="test-mig-02",
                spec_dict=spec,
                source_params={},
                target_params={},
                is_synthetic_test=False,
            )

    def test_03_transport_cannot_fabricate_r_count_5(self):
        """Hostile Check 10: DataTransportStep must fail closed when real transport fails."""
        step = DataTransportStep()
        rt_ctx = {
            "selected_scope": {"objects": [{"object_name": "T1", "target_schema": "public"}]},
            "source_params": {"host": "invalid-host"},
            "target_params": {"host": "invalid-host"},
        }
        wf_ctx = WorkflowContext(
            execution_context=ExecutionContext(workflow_id="mig-hostile-03", run_id="run-hostile-03"),
            runtime_context=RuntimeContext(transient_parameters=rt_ctx),
            user_context=UserContext(user_id="op"),
        )
        res = step.execute(wf_ctx)
        self.assertFalse(res.success)
        self.assertEqual(res.context_updates.get("rows_migrated", 0), 0)

    def test_04_oracle_reader_fails_closed_unconditionally(self):
        """Hostile Check 15: OraclePhysicalReader fails closed when MagicMock passed."""
        reader = OraclePhysicalReader({"mock_mode": True})
        reader.conn = MagicMock()
        with self.assertRaises(RuntimeError) as ctx:
            reader.read_batch(100)
        self.assertIn("Mock fallback is disallowed in physical production readers", str(ctx.exception))

    def test_05_postgres_reader_fails_closed_unconditionally(self):
        """Hostile Check 15: PostgreSQLPhysicalReader fails closed when MagicMock passed."""
        reader = PostgreSQLPhysicalReader({"mock_mode": True})
        reader.conn = MagicMock()
        with self.assertRaises(RuntimeError) as ctx:
            reader.read_batch(100)
        self.assertIn("Mock fallback is disallowed in physical production readers", str(ctx.exception))

    def test_06_mysql_reader_fails_closed_unconditionally(self):
        """Hostile Check 15: MySQLPhysicalReader fails closed when MagicMock passed."""
        reader = MySQLPhysicalReader({"mock_mode": True})
        reader.conn = MagicMock()
        with self.assertRaises(RuntimeError) as ctx:
            reader.read_batch(100)
        self.assertIn("Mock fallback is disallowed in physical production readers", str(ctx.exception))

    def test_07_mssql_reader_fails_closed_unconditionally(self):
        """Hostile Check 15: MSSQLPhysicalReader fails closed when MagicMock passed."""
        reader = MSSQLPhysicalReader({"mock_mode": True})
        reader.conn = MagicMock()
        with self.assertRaises(RuntimeError) as ctx:
            reader.read_batch(100)
        self.assertIn("Mock fallback is disallowed in physical production readers", str(ctx.exception))

    def test_08_oracle_writer_fails_closed_unconditionally(self):
        """Hostile Check 6 & 15: OraclePhysicalWriter fails closed when MagicMock passed."""
        writer = OraclePhysicalWriter({"mock_mode": True})
        writer.conn = MagicMock()
        meta = BatchMetadata(batch_id="b1", partition_id="p1", table_name="T1", sequence=1, row_count=1)
        with self.assertRaises(RuntimeError) as ctx:
            writer.write_batch("T1", ["ID"], [(1,)], meta)
        self.assertIn("Mock fallback is disallowed in physical production writers", str(ctx.exception))

    def test_09_postgres_writer_fails_closed_unconditionally(self):
        """Hostile Check 6 & 15: PostgreSQLPhysicalWriter fails closed when MagicMock passed."""
        writer = PostgreSQLPhysicalWriter({"mock_mode": True})
        writer.conn = MagicMock()
        meta = BatchMetadata(batch_id="b1", partition_id="p1", table_name="T1", sequence=1, row_count=1)
        with self.assertRaises(RuntimeError) as ctx:
            writer.write_batch("T1", ["ID"], [(1,)], meta)
        self.assertIn("Mock fallback is disallowed in physical production writers", str(ctx.exception))

    def test_10_mysql_writer_fails_closed_unconditionally(self):
        """Hostile Check 6 & 15: MySQLPhysicalWriter fails closed when MagicMock passed."""
        writer = MySQLPhysicalWriter({"mock_mode": True})
        writer.conn = MagicMock()
        meta = BatchMetadata(batch_id="b1", partition_id="p1", table_name="T1", sequence=1, row_count=1)
        with self.assertRaises(RuntimeError) as ctx:
            writer.write_batch("T1", ["ID"], [(1,)], meta)
        self.assertIn("Mock fallback is disallowed in physical production writers", str(ctx.exception))

    def test_11_mssql_writer_fails_closed_unconditionally(self):
        """Hostile Check 6 & 15: MSSQLPhysicalWriter fails closed when MagicMock passed."""
        writer = MSSQLPhysicalWriter({"mock_mode": True})
        writer.conn = MagicMock()
        meta = BatchMetadata(batch_id="b1", partition_id="p1", table_name="T1", sequence=1, row_count=1)
        with self.assertRaises(RuntimeError) as ctx:
            writer.write_batch("T1", ["ID"], [(1,)], meta)
        self.assertIn("Mock fallback is disallowed in physical production writers", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
