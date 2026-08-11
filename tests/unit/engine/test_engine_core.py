"""
AKAAL Engine Core — Unit & Integration Test Suite
==================================================
Tests ConnectionAuthorityDTO fingerprint calculation, SQLite WAL state repository,
SQLite WAL CheckpointStore, TransportPartitioner, EngineValidator, and AkaalMigrationEngine native API.
"""

import os
import shutil
import unittest
from akaal.engine.spec import (
    ConnectionAuthorityDTO,
    TransportPartition,
    PartitionStrategy,
    TuningPolicy,
    ValidationPolicy,
    ValidationLevel,
)
from akaal.engine.state import EngineStateRepository, MigrationState, PartitionState
from akaal.engine.checkpoint import CheckpointStore
from akaal.engine.partitioner import TransportPartitioner
from akaal.engine.validator import EngineValidator


class TestEngineCore(unittest.TestCase):

    def setUp(self):
        self.test_dir = os.path.join(os.getcwd(), "artifacts", "test_engine_tmp")
        os.makedirs(self.test_dir, exist_ok=True)
        self.state_db = os.path.join(self.test_dir, "test_state.db")
        self.checkpoint_db = os.path.join(self.test_dir, "test_checkpoint.db")

    def tearDown(self):
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_connection_authority_fingerprint(self):
        auth1 = ConnectionAuthorityDTO.create("SOURCE", "ORACLE", "localhost", 1521, "instance2_pdb", "SYSTEM", "cred-1")
        auth2 = ConnectionAuthorityDTO.create("SOURCE", "ORACLE", "localhost", 1521, "instance2_pdb", "SYSTEM", "cred-1")
        auth3 = ConnectionAuthorityDTO.create("SOURCE", "ORACLE", "localhost", 1521, "OTHER_DB", "SYSTEM", "cred-1")

        self.assertEqual(auth1.authority_fingerprint, auth2.authority_fingerprint)
        self.assertNotEqual(auth1.authority_fingerprint, auth3.authority_fingerprint)

    def test_missing_authority_fails_closed(self):
        with self.assertRaises(ValueError):
            ConnectionAuthorityDTO.create("SOURCE", "ORACLE", "", 1521, "instance2_pdb", "SYSTEM", "cred-1")

    def test_state_repository_wal(self):
        repo = EngineStateRepository(db_path=self.state_db)
        repo.set_migration_state("mig-test-001", MigrationState.CREATED)

        res = repo.get_migration_state("mig-test-001")
        self.assertIsNotNone(res)
        self.assertEqual(res["state"], "CREATED")

        repo.set_migration_state("mig-test-001", MigrationState.RUNNING)
        res2 = repo.get_migration_state("mig-test-001")
        self.assertEqual(res2["state"], "RUNNING")

    def test_checkpoint_store_wal(self):
        ckpt_store = CheckpointStore(db_path=self.checkpoint_db)
        ckpt_store.begin_batch("ckpt-01", "mig-01", "part-01", "TABLE_A", 1, "worker-1")
        ckpt_store.mark_batch_committed("ckpt-01", "mig-01", "part-01", "TABLE_A", 1, "worker-1", 5000, "5000", "hash123")

        latest = ckpt_store.get_latest_checkpoint("part-01")
        self.assertIsNotNone(latest)
        self.assertEqual(latest["rows_processed"], 5000)
        self.assertEqual(latest["last_committed_key"], "5000")

    def test_transport_partitioner(self):
        tuning = TuningPolicy(parallelism=4)
        partitioner = TransportPartitioner(tuning_policy=tuning)

        partitions = partitioner.generate_partitions_for_table(
            table_name="BIG_TABLE_1",
            schema_name="SYSTEM",
            target_schema="public",
            total_rows=1000000,
            pk_columns=["id"],
            min_pk=1,
            max_pk=1000000,
            strategy=PartitionStrategy.PK_NUMERIC_RANGE,
        )

        self.assertEqual(len(partitions), 4)
        self.assertEqual(partitions[0].lower_bound, 1)
        self.assertEqual(partitions[3].upper_bound, 1000001)

    def test_engine_validator(self):
        validator = EngineValidator(ValidationPolicy(level=ValidationLevel.LEVEL_3_MERKLE_TREE))
        src_counts = {"TBL_A": 5000, "TBL_B": 10000}
        tgt_counts = {"TBL_A": 5000, "TBL_B": 10000}

        res = validator.validate_tables(["TBL_A", "TBL_B"], src_counts, tgt_counts)
        self.assertTrue(res["overall_match"])
        self.assertIn("merkle_root_hash", res)
        self.assertEqual(res["total_source_rows"], 15000)


if __name__ == "__main__":
    unittest.main()
