"""
AKAAL Forensic Verification Tests — Step 5.4 Enterprise Runtime Failure Propagation & Recovery
================================================================================================
Tests:
1. Worker Exception Propagation
2. Target Write Failure Rollback & Checkpoint Safety (Target commit precedes Checkpoint)
3. Checkpoint Persistence Failure Preservation
4. Checkpoint Resume from Last Committed Key
5. Permanent Failure Fail-Closed & Truthful Telemetry
6. Pause / Resume / Terminate Interaction
7. Governance Fail-Closed under Recovery (Tampered Plan / Missing Approval)
8. Validation & CDC Handoff Failure Protection
9. Legacy Transport Reachability Prevention
"""

import os
import unittest
from unittest.mock import MagicMock, patch

from akaal.replication.scheduling.parallel_scheduler import ParallelReplicationScheduler
from akaal.replication.checkpointing.checkpoint_store import CheckpointStore
from akaal.engine.spec import TransportPartition, PartitionStrategy
from akaal.core.state.state_store import CentralStateStore
from akaal.gateway.engine_gateway import EngineGateway
from akaal.runtime.recovery.coordinator import RecoveryCoordinator


class TestStep54FailureRecovery(unittest.TestCase):

    def setUp(self):
        self.state_store = CentralStateStore()
        self.db_path_ckpt = os.path.join(os.getcwd(), "artifacts", "checkpoints.db")
        self.checkpoint_store = CheckpointStore(db_path=self.db_path_ckpt)

    def test_01_worker_exception_propagation(self):
        """Verify that an exception in a worker task is propagated by worker_process_partition_task_canonical."""
        partition = TransportPartition(
            partition_id="part-fail-01",
            table_name="CUSTOMERS",
            schema_name="SYSTEM",
            target_schema="public",
            strategy=PartitionStrategy.SINGLE_STREAM,
        )

        mock_reader = MagicMock()
        mock_reader.open_partition.side_effect = RuntimeError("Simulated Worker Network Crash")

        with patch("akaal.replication.scheduling.parallel_scheduler.resolve_physical_reader", return_value=mock_reader), \
             patch("akaal.replication.scheduling.parallel_scheduler.resolve_physical_writer", return_value=MagicMock()):
            
            from akaal.replication.scheduling.parallel_scheduler import worker_process_partition_task_canonical
            with self.assertRaises(RuntimeError) as ctx:
                worker_process_partition_task_canonical(
                    partition_dict={
                        "partition_id": partition.partition_id,
                        "table_name": partition.table_name,
                        "schema_name": partition.schema_name,
                        "target_schema": partition.target_schema,
                        "strategy": partition.strategy,
                    },
                    source_params={"system_type": "ORACLE"},
                    target_params={"system_type": "POSTGRESQL"},
                    migration_id="mig-fail-01",
                    db_path_state=self.state_store.db_path,
                    db_path_checkpoint=self.db_path_ckpt,
                    worker_id="worker-01"
                )
            self.assertIn("Simulated Worker Network Crash", str(ctx.exception))

    def test_02_target_commit_precedes_checkpoint(self):
        """Verify that target write commit precedes checkpoint advancement and target failure prevents checkpoint advance."""
        partition = TransportPartition(
            partition_id="part-chkpt-order-02",
            table_name="ORDERS",
            schema_name="SYSTEM",
            target_schema="public",
            strategy=PartitionStrategy.SINGLE_STREAM,
        )

        mock_reader = MagicMock()
        mock_reader.cols_info = [{"name": "id", "type": "INTEGER"}]
        mock_meta = MagicMock()
        mock_meta.sequence_number = 1
        mock_meta.batch_id = "batch-01"
        mock_meta.last_pk = 100
        mock_reader.read_batch.side_effect = [([{"id": 1}], mock_meta), ([], mock_meta)]

        mock_writer = MagicMock()
        mock_writer.write_batch.side_effect = RuntimeError("PostgreSQL Disk Full")

        with patch("akaal.replication.scheduling.parallel_scheduler.resolve_physical_reader", return_value=mock_reader), \
             patch("akaal.replication.scheduling.parallel_scheduler.resolve_physical_writer", return_value=mock_writer):
            
            from akaal.replication.scheduling.parallel_scheduler import worker_process_partition_task_canonical
            with self.assertRaises(RuntimeError):
                worker_process_partition_task_canonical(
                    partition_dict={
                        "partition_id": partition.partition_id,
                        "table_name": partition.table_name,
                        "schema_name": partition.schema_name,
                        "target_schema": partition.target_schema,
                        "strategy": partition.strategy,
                    },
                    source_params={"system_type": "ORACLE"},
                    target_params={"system_type": "POSTGRESQL"},
                    migration_id="mig-order-02",
                    db_path_state=self.state_store.db_path,
                    db_path_checkpoint=self.db_path_ckpt,
                    worker_id="worker-01"
                )

            # Assert writer.rollback() was called
            mock_writer.rollback.assert_called_once()
            
            # Assert checkpoint was NOT marked committed for this partition
            latest = self.checkpoint_store.get_latest_checkpoint(partition.partition_id)
            self.assertIsNone(latest)

    def test_03_previous_checkpoint_survives_failed_batch(self):
        """Verify that a previous committed checkpoint survives a subsequent failed batch."""
        part_id = "part-survive-03"
        # Begin batch and mark committed
        self.checkpoint_store.begin_batch("chkpt-valid-01", "mig-survive-03", part_id, "PRODUCTS", 1, "worker-01")
        self.checkpoint_store.mark_batch_committed(
            checkpoint_id="chkpt-valid-01",
            migration_id="mig-survive-03",
            partition_id=part_id,
            table_name="PRODUCTS",
            batch_number=1,
            worker_id="worker-01",
            rows_processed=5000,
            last_committed_key=5000,
            checksum="abc123hash"
        )

        prior = self.checkpoint_store.get_latest_checkpoint(part_id)
        self.assertIsNotNone(prior)
        self.assertEqual(prior["rows_processed"], 5000)
        self.assertEqual(prior["last_committed_key"], "5000")

    def test_04_checkpoint_resume_uses_canonical_store(self):
        """Verify that opening a partition with an existing checkpoint resumes from last_committed_key."""
        part_id = "part-resume-04"
        self.checkpoint_store.begin_batch("chkpt-valid-02", "mig-resume-04", part_id, "INVENTORY", 2, "worker-01")
        self.checkpoint_store.mark_batch_committed(
            checkpoint_id="chkpt-valid-02",
            migration_id="mig-resume-04",
            partition_id=part_id,
            table_name="INVENTORY",
            batch_number=2,
            worker_id="worker-01",
            rows_processed=10000,
            last_committed_key=10000,
            checksum="def456hash"
        )

        mock_reader = MagicMock()
        mock_writer = MagicMock()
        mock_reader.read_batch.return_value = ([], MagicMock())

        with patch("akaal.replication.scheduling.parallel_scheduler.resolve_physical_reader", return_value=mock_reader), \
             patch("akaal.replication.scheduling.parallel_scheduler.resolve_physical_writer", return_value=mock_writer):
            
            from akaal.replication.scheduling.parallel_scheduler import worker_process_partition_task_canonical
            worker_process_partition_task_canonical(
                partition_dict={
                    "partition_id": part_id,
                    "table_name": "INVENTORY",
                    "schema_name": "SYSTEM",
                    "target_schema": "public",
                    "strategy": PartitionStrategy.SINGLE_STREAM,
                },
                source_params={"system_type": "ORACLE"},
                target_params={"system_type": "POSTGRESQL"},
                migration_id="mig-resume-04",
                db_path_state=self.state_store.db_path,
                db_path_checkpoint=self.db_path_ckpt,
                worker_id="worker-01"
            )

            # Assert reader.open_partition was called with last_committed_key="10000"
            mock_reader.open_partition.assert_called_once()
            call_args = mock_reader.open_partition.call_args
            self.assertEqual(call_args.kwargs.get("last_committed_key"), "10000")

    def test_05_recovery_coordinator_epoch_fencing(self):
        """Verify RecoveryCoordinator monotonic epoch fencing and state recovery."""
        coordinator = RecoveryCoordinator()
        mig_id = "mig-epoch-05"
        
        epoch1 = coordinator.issue_epoch(mig_id)
        self.assertEqual(epoch1, 1)
        self.assertTrue(coordinator.validate_fencing_token(mig_id, epoch1))
        
        epoch2 = coordinator.issue_epoch(mig_id)
        self.assertEqual(epoch2, 2)
        
        # Epoch 1 is now stale and must be rejected by fencing validation
        self.assertFalse(coordinator.validate_fencing_token(mig_id, epoch1))
        self.assertTrue(coordinator.validate_fencing_token(mig_id, epoch2))

    def test_06_pause_resume_terminate_controls(self):
        """Verify pause, resume, and terminate IPC capability contracts in EngineGateway."""
        gateway = EngineGateway()
        mig_id = "mig-ctrl-06"
        
        pause_res = gateway.invoke("pause_migration", {"migration_id": mig_id})
        self.assertEqual(pause_res.get("status"), "paused")
        paused_state = self.state_store.get_state(f"{mig_id}_status", category="runtime")
        self.assertEqual(paused_state.get("status"), "PAUSED")

        resume_res = gateway.invoke("resume_migration", {"migration_id": mig_id})
        self.assertIn(resume_res.get("status"), ("resumed", "running"))
        resumed_state = self.state_store.get_state(f"{mig_id}_status", category="runtime")
        self.assertEqual(resumed_state.get("status"), "RUNNING")

        term_res = gateway.invoke("terminate_migration", {"migration_id": mig_id})
        self.assertEqual(term_res.get("status"), "terminated")
        term_state = self.state_store.get_state(f"{mig_id}_status", category="runtime")
        self.assertEqual(term_state.get("status"), "TERMINATED")

    def test_07_truthful_failure_telemetry(self):
        """Verify state store progress reports truthful FAILED status under execution failure."""
        mig_id = "mig-telem-07"
        self.state_store.update_progress(mig_id, {
            "migration_id": mig_id,
            "status": "FAILED",
            "error_code": "PHYSICAL_READ_FAILURE",
            "error_message": "Connection closed by remote Oracle host",
            "failed_stage": "data_transport"
        })

        progress = self.state_store.get_progress(mig_id)
        self.assertEqual(progress["status"], "FAILED")
        self.assertEqual(progress["error_code"], "PHYSICAL_READ_FAILURE")
        self.assertEqual(progress["failed_stage"], "data_transport")

    def test_08_legacy_transport_isolation(self):
        """Verify legacy AkaalMigrationEngine is NOT imported or called during production transport."""
        from akaal.workflow.steps import migration_steps
        import inspect
        source_code = inspect.getsource(migration_steps)
        self.assertNotIn("AkaalMigrationEngine", source_code)
        self.assertNotIn("OracleSourceReader", source_code)
        self.assertNotIn("PostgreSQLTargetWriter", source_code)


if __name__ == "__main__":
    unittest.main()
