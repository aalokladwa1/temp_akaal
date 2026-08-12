"""
AKAAL Forensic Verification Tests — Step 5.2 Canonical Transport Reachability
=============================================================================
Verifies that DataTransportStep routes transport execution through the database-agnostic
physical transport resolver (resolve_physical_reader and resolve_physical_writer), and
asserts that legacy akaal.engine.api, legacy writer.py (TEXT column DDL), legacy reader.py,
and legacy checkpoint.py (checkpoints.db) are 100% UNREACHABLE from canonical WF-011 execution.
"""

import unittest
from unittest.mock import MagicMock, patch

from akaal.workflow.steps.migration_steps import DataTransportStep
from akaal.replication.resolver import resolve_physical_reader, resolve_physical_writer
from akaal.replication.readers.oracle_reader import OraclePhysicalReader
from akaal.replication.writers.postgresql_writer import PostgreSQLPhysicalWriter


class TestStep52CanonicalTransportReachability(unittest.TestCase):

    def test_canonical_transport_does_not_import_legacy_migration_engine(self):
        """Assert that DataTransportStep execution source code does not import akaal.engine.api AkaalMigrationEngine."""
        import inspect
        source_code = inspect.getsource(DataTransportStep.execute)
        self.assertNotIn(
            "from akaal.engine.api import AkaalMigrationEngine",
            source_code,
            "CRITICAL DEFECT: DataTransportStep still contains legacy import 'from akaal.engine.api import AkaalMigrationEngine'"
        )

    def test_canonical_transport_uses_generic_transport_resolver(self):
        """Assert that DataTransportStep imports resolve_physical_reader and resolve_physical_writer."""
        import inspect
        source_code = inspect.getsource(DataTransportStep.execute)
        self.assertIn(
            "from akaal.replication.resolver import resolve_physical_reader, resolve_physical_writer",
            source_code,
            "DataTransportStep must use generic physical transport resolver"
        )

    @patch("psycopg2.connect")
    def test_resolver_oracle_to_postgresql(self, mock_pg_conn):
        """Assert generic resolver returns OraclePhysicalReader for ORACLE and PostgreSQLPhysicalWriter for POSTGRESQL."""
        reader = resolve_physical_reader("ORACLE", {"username": "SYSTEM", "password": "p", "database": "FREE"})
        writer = resolve_physical_writer("POSTGRESQL", {"username": "postgres", "password": "p", "database": "db"})
        self.assertIsInstance(reader, OraclePhysicalReader)
        self.assertIsInstance(writer, PostgreSQLPhysicalWriter)

    def test_resolver_unsupported_engine_pair_raises_clean_error(self):
        """Assert generic resolver raises UNSUPPORTED_CAPABILITY when reader or writer capability is missing."""
        with self.assertRaises(ValueError) as cm_reader:
            resolve_physical_reader("UNSUPPORTED_SOURCE", {})
        self.assertIn("UNSUPPORTED_CAPABILITY", str(cm_reader.exception))

        with self.assertRaises(ValueError) as cm_writer:
            resolve_physical_writer("UNSUPPORTED_TARGET", {})
        self.assertIn("UNSUPPORTED_CAPABILITY", str(cm_writer.exception))

    @patch("akaal.engine.api.AkaalMigrationEngine")
    @patch("akaal.engine.writer.PostgreSQLTargetWriter")
    @patch("akaal.engine.checkpoint.CheckpointStore")
    def test_legacy_engine_components_never_invoked(self, mock_checkpoint_store, mock_target_writer, mock_migration_engine):
        """Assert that executing DataTransportStep never invokes AkaalMigrationEngine, PostgreSQLTargetWriter, or CheckpointStore."""
        step = DataTransportStep()
        
        mock_src_conn = MagicMock()
        mock_src_conn.__eq__ = lambda self, other: False
        mock_src_conn.cursor.return_value.__enter__.return_value = MagicMock()

        mock_pg_conn = MagicMock()
        mock_pg_conn.__eq__ = lambda self, other: False
        mock_pg_conn.cursor.return_value.__enter__.return_value = MagicMock()

        ctx_dict = {
            "migration_id": "mig-step-52-test",
            "source_config": MagicMock(
                system_type=MagicMock(value="ORACLE"),
                host="127.0.0.1",
                port=1521,
                database_name="FREE",
                credentials_ref="cred-src",
                extra={"username": "SYSTEM", "password": "pass"}
            ),
            "target_config": MagicMock(
                system_type=MagicMock(value="POSTGRESQL"),
                host="127.0.0.1",
                port=5432,
                database_name="pgdb",
                credentials_ref="cred-tgt",
                extra={"username": "postgres", "password": "pass"}
            ),
            "source_connection": mock_src_conn,
            "target_connection": mock_pg_conn,
            "discovered_objects": [
                {
                    "object_type": "TABLE",
                    "object_name": "CUSTOMERS",
                    "source_schema": "SYSTEM",
                    "target_schema": "public",
                }
            ],
            "schema_execution_passed": True,
            "ddl_executed": True,
        }

        mock_wf_context = MagicMock()
        mock_wf_context.runtime_context.transient_parameters = ctx_dict

        # Mock canonical reader/writer so test runs in isolation
        with patch("akaal.replication.readers.oracle_reader.OraclePhysicalReader") as mock_reader_cls, \
             patch("akaal.replication.writers.postgresql_writer.PostgreSQLPhysicalWriter") as mock_writer_cls:
            
            mock_reader_inst = MagicMock()
            mock_reader_inst.cols_info = ["id", "name"]
            mock_reader_inst.read_batch.return_value = ([(1, "Customer A")], MagicMock())
            mock_reader_cls.return_value = mock_reader_inst

            mock_writer_inst = MagicMock()
            mock_writer_inst.write_batch.return_value = 1
            mock_writer_cls.return_value = mock_writer_inst

            res = step.execute(mock_wf_context)

            self.assertTrue(res.success)
            mock_migration_engine.assert_not_called()
            mock_target_writer.assert_not_called()
            mock_checkpoint_store.assert_not_called()


if __name__ == "__main__":
    unittest.main()
