"""
AKAAL Unit Tests — Canonical Physical Replication Infrastructure (Step 1 Verification)
======================================================================================
Tests OraclePhysicalReader, PostgreSQLPhysicalWriter, RangePartitioner, CheckpointStore,
and ParallelReplicationScheduler.
"""

import os
import unittest
from unittest.mock import MagicMock, patch

from akaal.engine.spec import TransportPartition, PartitionStrategy, TuningPolicy, BatchMetadata
from akaal.replication.readers.oracle_reader import OraclePhysicalReader
from akaal.replication.writers.postgresql_writer import PostgreSQLPhysicalWriter
from akaal.replication.partitioning.range_partitioner import RangePartitioner
from akaal.replication.checkpointing.checkpoint_store import CheckpointStore
from akaal.replication.scheduling.parallel_scheduler import ParallelReplicationScheduler
from akaal.replication.domain.core_replication import CoreReplicationDomain
from akaal.replication.core.context import ReplicationContext


class TestCanonicalPhysicalReplication(unittest.IsolatedAsyncioTestCase):

    def setUp(self):
        self.db_path = "artifacts/test_checkpoints.db"
        if os.path.exists(self.db_path):
            try:
                os.remove(self.db_path)
            except OSError:
                pass

    def tearDown(self):
        if os.path.exists(self.db_path):
            try:
                os.remove(self.db_path)
            except OSError:
                pass

    def test_range_partitioner_intra_table_generation(self):
        policy = TuningPolicy(parallelism=4, batch_size=5000)
        partitioner = RangePartitioner(tuning_policy=policy)

        parts = partitioner.generate_partitions_for_table(
            table_name="LARGE_TABLE",
            schema_name="SYSTEM",
            target_schema="public",
            total_rows=1000000,
            pk_columns=["ID"],
            min_pk=1,
            max_pk=1000000,
            strategy=PartitionStrategy.PK_NUMERIC_RANGE,
        )

        self.assertEqual(len(parts), 4)
        self.assertEqual(parts[0].table_name, "LARGE_TABLE")
        self.assertEqual(parts[0].lower_bound, 1)
        self.assertGreater(parts[0].upper_bound, 1)

    def test_range_partitioner_single_partition_fallback(self):
        policy = TuningPolicy(parallelism=4, batch_size=5000)
        partitioner = RangePartitioner(tuning_policy=policy)

        parts = partitioner.generate_partitions_for_table(
            table_name="SMALL_TABLE",
            schema_name="SYSTEM",
            target_schema="public",
            total_rows=500,
            pk_columns=["ID"],
        )

        self.assertEqual(len(parts), 1)
        self.assertEqual(parts[0].partition_id, "part-SMALL_TABLE-001")

    def test_checkpoint_store_lifecycle(self):
        ckpt_store = CheckpointStore(db_path=self.db_path)
        ckpt_id = "chkpt-part-001-000001"

        ckpt_store.begin_batch(
            checkpoint_id=ckpt_id,
            migration_id="mig-test-01",
            partition_id="part-001",
            table_name="USERS",
            batch_number=1,
            worker_id="worker-01",
        )

        latest = ckpt_store.get_latest_checkpoint("part-001")
        self.assertIsNone(latest)

        ckpt_store.mark_batch_committed(
            checkpoint_id=ckpt_id,
            migration_id="mig-test-01",
            partition_id="part-001",
            table_name="USERS",
            batch_number=1,
            worker_id="worker-01",
            rows_processed=500,
            last_committed_key=500,
            checksum="hash123",
        )

        latest = ckpt_store.get_latest_checkpoint("part-001")
        self.assertIsNotNone(latest)
        self.assertEqual(latest["rows_processed"], 500)
        self.assertEqual(latest["last_committed_key"], "500")

    @patch("oracledb.connect")
    def test_oracle_physical_reader_mock(self, mock_connect):
        from tests.conftest import require_oracle
        require_oracle("localhost", 1521)
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_connect.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor

        mock_cursor.fetchmany.return_value = [(1, "Alice"), (2, "Bob")]
        mock_cursor.description = [("ID", None), ("NAME", None)]

        reader = OraclePhysicalReader({
            "username": "system",
            "password": "pwd",
            "host": "localhost",
            "port": 1521,
            "database": "FREE",
        })

        part = TransportPartition(
            partition_id="part-001",
            table_name="USERS",
            schema_name="SYSTEM",
            target_schema="public",
            strategy=PartitionStrategy.SINGLE_STREAM,
            pk_columns=["ID"],
        )

        reader.open_partition(part)
        rows, meta = reader.read_batch(10)

        self.assertEqual(len(rows), 2)
        self.assertEqual(meta.row_count, 2)
        self.assertEqual(meta.first_pk, 1)
        self.assertEqual(meta.last_pk, 2)
        reader.close()

    @patch("psycopg2.connect")
    def test_postgresql_physical_writer_mock(self, mock_connect):
        from tests.conftest import require_postgres
        require_postgres("localhost", 5432)
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_connect.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor

        writer = PostgreSQLPhysicalWriter({
            "username": "postgres",
            "password": "pwd",
            "host": "localhost",
            "port": 5432,
            "database": "pg_analytics",
        })


        meta = BatchMetadata(
            batch_id="batch-001",
            partition_id="part-001",
            table_name="users",
            sequence=1,
            row_count=2,
        )

        written = writer.write_batch(
            table_name="users",
            columns=["id", "name"],
            data=[(1, "Alice"), (2, "Bob")],
            batch_meta=meta,
            pk_columns=["id"],
        )

        self.assertEqual(written, 2)
        writer.commit()
        mock_conn.commit.assert_called_once()
        writer.close()

    async def test_core_replication_domain_physical_dispatch(self):
        domain = CoreReplicationDomain()
        ctx = ReplicationContext(
            runtime_metadata={
                "migration_id": "mig-test-123",
                "physical_spec": {
                    "selected_scope": {
                        "objects": [
                            {"object_name": "USERS", "schema_name": "SYSTEM", "target_schema": "public", "estimated_rows": 50}
                        ]
                    },
                    "tuning": {"parallelism": 1, "batch_size": 100}
                },
                "source_params": {"username": "system", "password": "pwd", "host": "localhost", "port": 1521, "database": "FREE"},
                "target_params": {"username": "postgres", "password": "pwd", "host": "localhost", "port": 5432, "database": "pg_analytics"},
            }
        )

        with patch("akaal.replication.scheduling.parallel_scheduler.ParallelReplicationScheduler.execute_partitions") as mock_sched:
            mock_sched.return_value = {
                "status": "COMPLETED",
                "total_rows": 50,
                "execution_time_sec": 0.1,
            }
            res = await domain.replicate_domain(ctx)
            self.assertEqual(res.status.value, "COMPLETED")
            mock_sched.assert_called_once()


if __name__ == "__main__":
    unittest.main()
