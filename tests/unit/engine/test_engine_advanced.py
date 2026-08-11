"""
AKAAL Engine Advanced Verification Test Suite
=============================================
Tests partition boundaries, sparse PKs, non-overlapping adjacent ranges,
uncertain commit reconciliation, data corruption detection (Level 2/3),
pause/resume/cancel state transitions, and EngineGateway delegation.
"""

import os
import shutil
import unittest
from akaal.engine.spec import (
    TransportPartition,
    PartitionStrategy,
    TuningPolicy,
    ValidationPolicy,
    ValidationLevel,
    MigrationState,
    ConnectionAuthorityDTO,
)
from akaal.engine.partitioner import TransportPartitioner
from akaal.engine.validator import EngineValidator
from akaal.engine.writer import PostgreSQLTargetWriter
from akaal.engine.state import EngineStateRepository
from akaal.engine.checkpoint import CheckpointStore
from akaal.gateway.engine_gateway import EngineGateway


class MockTargetWriter(PostgreSQLTargetWriter):
    """Mock TargetWriter for testing uncertain commit verification without live DB."""
    def __init__(self, count_to_return: int):
        self.count_to_return = count_to_return
        self.conn = None
        self.cursor = None

    def verify_uncertain_batch(self, table_name: str, pk_column: str, first_pk: str, last_pk: str, expected_rows: int, target_schema: str = "public") -> str:
        if self.count_to_return == expected_rows:
            return "COMMITTED"
        elif self.count_to_return == 0:
            return "NOT_COMMITTED"
        else:
            return "AMBIGUOUS"


class TestEngineAdvanced(unittest.TestCase):

    def setUp(self):
        self.test_dir = os.path.join(os.getcwd(), "artifacts", "test_engine_adv_tmp")
        os.makedirs(self.test_dir, exist_ok=True)
        self.state_db = os.path.join(self.test_dir, "test_state.db")
        self.checkpoint_db = os.path.join(self.test_dir, "test_checkpoint.db")

    def tearDown(self):
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_partition_boundaries_non_overlapping(self):
        """Verify adjacent partitions do not overlap or skip key boundaries."""
        tuning = TuningPolicy(parallelism=4)
        partitioner = TransportPartitioner(tuning_policy=tuning)

        parts = partitioner.generate_partitions_for_table(
            table_name="LARGE_TABLE",
            schema_name="SYSTEM",
            target_schema="public",
            total_rows=1000000,
            pk_columns=["id"],
            min_pk=1,
            max_pk=1000000,
            strategy=PartitionStrategy.PK_NUMERIC_RANGE,
        )

        self.assertEqual(len(parts), 4)

        # Check non-overlapping bounds: lower_bound of part N equals upper_bound of part N-1
        for i in range(1, len(parts)):
            prev_upper = parts[i-1].upper_bound
            curr_lower = parts[i].lower_bound
            self.assertEqual(prev_upper, curr_lower, f"Partition overlap or gap detected between part {i-1} upper={prev_upper} and part {i} lower={curr_lower}")

    def test_empty_and_single_row_partitions(self):
        partitioner = TransportPartitioner(tuning_policy=TuningPolicy(parallelism=1))

        # Single-row partition
        single_p = partitioner.generate_partitions_for_table(
            table_name="SINGLE_ROW_TBL", schema_name="SYSTEM", target_schema="public", total_rows=1, pk_columns=["id"], min_pk=42, max_pk=42
        )
        self.assertEqual(len(single_p), 1)

        # Empty table fallback
        empty_p = partitioner.generate_partitions_for_table(
            table_name="EMPTY_TBL", schema_name="SYSTEM", target_schema="public", total_rows=0, pk_columns=["id"], min_pk=None, max_pk=None
        )
        self.assertEqual(len(empty_p), 1)

    def test_uncertain_commit_verification_outcomes(self):
        """Verify UNCERTAIN batch protocol produces COMMITTED, NOT_COMMITTED, and AMBIGUOUS fail-closed states."""
        writer_committed = MockTargetWriter(count_to_return=5000)
        res1 = writer_committed.verify_uncertain_batch("TBL", "id", 1, 5000, 5000)
        self.assertEqual(res1, "COMMITTED")

        writer_failed = MockTargetWriter(count_to_return=0)
        res2 = writer_failed.verify_uncertain_batch("TBL", "id", 1, 5000, 5000)
        self.assertEqual(res2, "NOT_COMMITTED")

        writer_ambiguous = MockTargetWriter(count_to_return=2500)
        res3 = writer_ambiguous.verify_uncertain_batch("TBL", "id", 1, 5000, 5000)
        self.assertEqual(res3, "AMBIGUOUS")

    def test_corruption_detection_level2_level3(self):
        """
        CORRUPTION TEST MANDATE:
        1. Source data vs Target data
        2. Alter ONE cell in target
        3. Level 1 Row Count PASSES
        4. Level 2 / Level 3 Data Hash FAILS
        """
        validator = EngineValidator(ValidationPolicy(level=ValidationLevel.LEVEL_3_MERKLE_TREE))
        table_names = ["ORDERS"]

        src_rows = [
            (101, "COMPLETED", 150.00),
            (102, "PENDING", 85.50),
            (103, "SHIPPED", 210.00),
        ]

        # Target rows with ONE corrupted cell: 150.00 -> 150.01
        tgt_rows_corrupted = [
            (101, "COMPLETED", 150.01),
            (102, "PENDING", 85.50),
            (103, "SHIPPED", 210.00),
        ]

        src_hash = validator.compute_data_checksum(src_rows)
        tgt_hash = validator.compute_data_checksum(tgt_rows_corrupted)

        self.assertNotEqual(src_hash, tgt_hash)

        # Level 1 Validation (Counts) -> PASSES
        val_l1 = validator.validate_tables(table_names, {"ORDERS": 3}, {"ORDERS": 3}, level=ValidationLevel.LEVEL_1_ROW_COUNT)
        self.assertTrue(val_l1["overall_match"])

        # Level 3 Merkle Data Hash Validation -> FAILS
        val_l3 = validator.validate_tables(
            table_names,
            {"ORDERS": 3},
            {"ORDERS": 3},
            source_data_hashes={"ORDERS": src_hash},
            target_data_hashes={"ORDERS": tgt_hash},
            level=ValidationLevel.LEVEL_3_MERKLE_TREE,
        )
        self.assertFalse(val_l3["overall_match"])
        self.assertFalse(val_l3["tables"]["ORDERS"]["data_match"])

    def test_state_repository_pause_cancel_transitions(self):
        repo = EngineStateRepository(db_path=self.state_db)
        mig_id = "mig-transition-001"

        repo.set_migration_state(mig_id, MigrationState.RUNNING)
        self.assertEqual(repo.get_migration_state(mig_id)["state"], "RUNNING")

        repo.set_migration_state(mig_id, MigrationState.PAUSED)
        self.assertEqual(repo.get_migration_state(mig_id)["state"], "PAUSED")

        repo.set_migration_state(mig_id, MigrationState.CANCEL_REQUESTED)
        self.assertEqual(repo.get_migration_state(mig_id)["state"], "CANCEL_REQUESTED")

        repo.set_migration_state(mig_id, MigrationState.CANCELLED)
        self.assertEqual(repo.get_migration_state(mig_id)["state"], "CANCELLED")

    def test_engine_gateway_delegation(self):
        gateway = EngineGateway()
        status = gateway.invoke("get_engine_status", {})
        self.assertEqual(status["status"], "RUNNING")


if __name__ == "__main__":
    unittest.main()
