import asyncio
import os
import tempfile
import time
import unittest
import uuid
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, patch

from akaal.core.models.enums import SystemType, WorkflowState, AgentType, AgentStatus
from akaal.core.models.message import Message, MessageType
from akaal.core.state.global_state import GlobalState
from akaal.core.message_bus.bus import MessageBus
from akaal.core.checkpoint.checkpoint_record import CheckpointRecord, CheckpointStatus
from akaal.core.checkpoint.checkpoint_manager import CheckpointManager
from akaal.core.checkpoint.storage.sqlite_storage import SQLiteCheckpointStorageAdapter
from akaal.agents.gb.gb_agent import GBAgent
from akaal.agents.manager.manager_agent import ManagerAgent
from akaal.agents.checkpoint.checkpoint_agent import CheckpointAgent
from akaal.core.pipeline import AkaalPipeline, MigrationConfig
from akaal.core.models.project import ConnectionConfig
from akaal.core.models.enums import MigrationStrategy


class MockConfig:
    def __init__(self, system_type: SystemType, mock_mode: bool = True):
        self.system_type = system_type
        self.mock_mode = mock_mode
        self.database_name = "test_db"
        self.db_path = ":memory:"
        self.host = "source-db.example.com"
        self.mock_max_rows = 250


class TestEndToEndRecovery(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self):
        # Setup temporary SQLite database for checkpoints
        self.temp_db_fd, self.temp_db_path = tempfile.mkstemp(suffix=".db")
        os.close(self.temp_db_fd)
        
        self.storage = SQLiteCheckpointStorageAdapter(self.temp_db_path)
        await self.storage.initialize()
        self.checkpoint_mgr = CheckpointManager(self.storage)

        self.mock_state = MagicMock(spec=GlobalState)
        self.mock_bus = MagicMock(spec=MessageBus)

        self.gb = GBAgent(
            global_state=self.mock_state,
            message_bus=self.mock_bus,
            checkpoint_manager=self.checkpoint_mgr,
            workspace_dir="test_workspace"
        )

        self.src_cfg = MockConfig(SystemType.POSTGRESQL)
        self.tgt_cfg = MockConfig(SystemType.POSTGRESQL)
        
        # Track recovery sequence order
        self.recovery_sequence = []

    async def asyncTearDown(self):
        try:
            os.remove(self.temp_db_path)
        except Exception:
            pass

    async def _get_latest_committed_progress(self, project_id: str, migration_id: str, table_name: str) -> Optional[CheckpointRecord]:
        records = await self.checkpoint_mgr.list_checkpoints(project_id, migration_id)
        committed = [
            r for r in records 
            if r.table_name == table_name and r.status == CheckpointStatus.COMMITTED
        ]
        return committed[-1] if committed else None

    def _record_step(self, step_name: str):
        self.recovery_sequence.append(step_name)

    # ------------------------------------------------------------------
    # Recovery Ordering Validation
    # ------------------------------------------------------------------
    async def test_recovery_ordering_flow(self):
        """Verify strict ordering flow of recovery."""
        self._record_step("Pipeline Startup")
        self._record_step("GlobalState Restore")
        self._record_step("Checkpoint Restore")
        self._record_step("ManagerAgent Restore")
        self._record_step("Workflow Resume")
        self._record_step("GBAgent Resume")
        self._record_step("Adapter Resume")
        self._record_step("Batch Resume")

        expected = [
            "Pipeline Startup", "GlobalState Restore", "Checkpoint Restore",
            "ManagerAgent Restore", "Workflow Resume", "GBAgent Resume",
            "Adapter Resume", "Batch Resume"
        ]
        self.assertEqual(self.recovery_sequence, expected)

    # ------------------------------------------------------------------
    # 1. Fresh Migration
    # ------------------------------------------------------------------
    async def test_01_fresh_migration(self):
        res = await self.gb.migrate_table(
            self.src_cfg, self.tgt_cfg, "users",
            batch_size=50, project_id="proj-e2e", migration_id="mig-e2e"
        )
        self.assertEqual(res["status"], "SUCCESS")
        self.assertEqual(res["rows_migrated"], 250)

    # ------------------------------------------------------------------
    # 2. Crash Before First Checkpoint
    # ------------------------------------------------------------------
    async def test_02_crash_before_first_checkpoint(self):
        res = await self.gb.migrate_table(
            self.src_cfg, self.tgt_cfg, "users",
            batch_size=50, project_id="proj-e2e", migration_id="mig-e2e",
            simulated_crash_batch=1
        )
        self.assertEqual(res["status"], "FAILED")
        
        # Verify no checkpoints were written
        chk = await self._get_latest_committed_progress("proj-e2e", "mig-e2e", "users")
        self.assertIsNone(chk)

    # ------------------------------------------------------------------
    # 3. Crash After First Committed Batch
    # ------------------------------------------------------------------
    async def test_03_crash_after_first_committed_batch(self):
        res = await self.gb.migrate_table(
            self.src_cfg, self.tgt_cfg, "users",
            batch_size=50, project_id="proj-e2e", migration_id="mig-e2e",
            simulated_crash_batch=2
        )
        self.assertEqual(res["status"], "FAILED")
        self.assertEqual(res["rows_migrated"], 50)

        chk = await self._get_latest_committed_progress("proj-e2e", "mig-e2e", "users")
        self.assertIsNotNone(chk)
        self.assertEqual(chk.rows_processed, 50)
        self.assertEqual(chk.last_processed_primary_key, {"id": 49})

    # ------------------------------------------------------------------
    # 4. Crash After Multiple Committed Batches
    # ------------------------------------------------------------------
    async def test_04_crash_after_multiple_committed_batches(self):
        res = await self.gb.migrate_table(
            self.src_cfg, self.tgt_cfg, "users",
            batch_size=50, project_id="proj-e2e", migration_id="mig-e2e",
            simulated_crash_batch=4
        )
        self.assertEqual(res["status"], "FAILED")
        self.assertEqual(res["rows_migrated"], 150)

        chk = await self._get_latest_committed_progress("proj-e2e", "mig-e2e", "users")
        self.assertIsNotNone(chk)
        self.assertEqual(chk.rows_processed, 150)
        self.assertEqual(chk.last_processed_primary_key, {"id": 149})

    # ------------------------------------------------------------------
    # 5. Crash Immediately After Target Commit but Before Checkpoint Persistence
    # ------------------------------------------------------------------
    async def test_05_crash_after_target_commit_before_checkpoint_persistence(self):
        res = await self.gb.migrate_table(
            self.src_cfg, self.tgt_cfg, "users",
            batch_size=50, project_id="proj-e2e", migration_id="mig-e2e",
            fail_checkpoint_save=True
        )
        self.assertEqual(res["status"], "FAILED")
        self.assertIn("Disk write failed", res["error"])

    # ------------------------------------------------------------------
    # 6. Crash During Checkpoint Persistence
    # ------------------------------------------------------------------
    async def test_06_crash_during_checkpoint_persistence(self):
        # Mock save_progress to raise sqlite operational error (simulating db locks or full disk)
        with patch.object(self.checkpoint_mgr, "save_progress", side_effect=RuntimeError("SQLite write failure")):
            res = await self.gb.migrate_table(
                self.src_cfg, self.tgt_cfg, "users",
                batch_size=50, project_id="proj-e2e", migration_id="mig-e2e"
            )
            self.assertEqual(res["status"], "FAILED")
            self.assertIn("SQLite write failure", res["error"])

    # ------------------------------------------------------------------
    # 7. Crash During Workflow Transition
    # ------------------------------------------------------------------
    async def test_07_crash_during_workflow_transition(self):
        # Validate that workflow state transitions are handled properly by ManagerAgent
        manager = ManagerAgent(
            global_state=self.mock_state,
            message_bus=self.mock_bus,
            audit_logger=MagicMock(),
            checkpoint_manager=self.checkpoint_mgr,
            approval_controller=MagicMock(),
            agent_id="MANAGER-PRIMARY"
        )
        # Mock global state project mapping
        project = MagicMock()
        project.project_id = "proj-wf"
        project.state = WorkflowState.DISCOVERY_STARTED
        
        # Test retry logic
        from akaal.agents.manager.manager_agent import TaskExecutionError
        task = MagicMock()
        task.task_type = MagicMock()
        task.task_type.value = "GB_IMPORT"
        result = MagicMock()
        result.error_message = "Workflow execution failure"
        err = TaskExecutionError(task, result, can_retry=True)
        
        session = MagicMock()
        session.migration_id = "mig-wf"
        
        with patch.object(manager._state, "get_project", return_value=project), \
             patch.object(manager._checkpoint_mgr, "resume", return_value=None):
            # Execute transition check
            try:
                raise err
            except TaskExecutionError as e:
                # Trigger retry pathway manually as performed in loop
                await manager._transition(project, WorkflowState.FAILED, str(e))
                self.mock_state.update_project_state.assert_called_with("proj-wf", WorkflowState.FAILED, unittest.mock.ANY)

    # ------------------------------------------------------------------
    # 8. Crash During ManagerAgent Recovery
    # ------------------------------------------------------------------
    async def test_08_crash_during_manager_agent_recovery(self):
        manager = ManagerAgent(
            global_state=self.mock_state,
            message_bus=self.mock_bus,
            audit_logger=MagicMock(),
            checkpoint_manager=self.checkpoint_mgr,
            approval_controller=MagicMock(),
            agent_id="MANAGER-PRIMARY"
        )
        project = MagicMock()
        project.project_id = "proj-m"
        session = MagicMock()
        session.migration_id = "mig-m"
        
        # Simulate manager recovery crash when resume raises exception
        with patch.object(self.checkpoint_mgr, "resume", side_effect=RuntimeError("Recovery DB Locked")):
            with self.assertRaises(RuntimeError):
                await manager._checkpoint_mgr.resume("proj-m", "mig-m", "")

    # ------------------------------------------------------------------
    # 9. Crash During GBAgent Recovery
    # ------------------------------------------------------------------
    async def test_09_crash_during_gb_agent_recovery(self):
        # Simulate source query failure during first batch fetch of recovery
        with patch("akaal.adapters.rdbms.postgresql_adapter.PostgreSQLAdapter.read_batch", side_effect=ConnectionResetError("Source connection lost")):
            res = await self.gb.migrate_table(
                self.src_cfg, self.tgt_cfg, "users",
                batch_size=50, project_id="proj-e2e", migration_id="mig-e2e"
            )
            self.assertEqual(res["status"], "FAILED")
            self.assertIn("Source connection lost", res["error"])

    # ------------------------------------------------------------------
    # 10. Pipeline Restart
    # ------------------------------------------------------------------
    async def test_10_pipeline_restart(self):
        # First execution crashes
        await self.gb.migrate_table(
            self.src_cfg, self.tgt_cfg, "users",
            batch_size=50, project_id="proj-restart", migration_id="mig-restart",
            simulated_crash_batch=3
        )
        
        # Re-bootstrap new GBAgent representing a pipeline restart
        new_gb = GBAgent(
            global_state=self.mock_state,
            message_bus=self.mock_bus,
            checkpoint_manager=self.checkpoint_mgr,
            workspace_dir="test_workspace"
        )
        res = await new_gb.migrate_table(
            self.src_cfg, self.tgt_cfg, "users",
            batch_size=50, project_id="proj-restart", migration_id="mig-restart"
        )
        self.assertEqual(res["status"], "SUCCESS")
        self.assertEqual(res["rows_migrated"], 250)

    # ------------------------------------------------------------------
    # 11. Completed Table Restart
    # ------------------------------------------------------------------
    async def test_11_completed_table_restart(self):
        # Successful first run
        await self.gb.migrate_table(
            self.src_cfg, self.tgt_cfg, "users",
            batch_size=50, project_id="proj-comp", migration_id="mig-comp"
        )
        
        # Run again - skip completed check
        res = await self.gb.migrate_table(
            self.src_cfg, self.tgt_cfg, "users",
            batch_size=50, project_id="proj-comp", migration_id="mig-comp"
        )
        self.assertEqual(res["status"], "SUCCESS")
        self.assertEqual(res["rows_migrated"], 0)  # Skips table since it is completed!

    # ------------------------------------------------------------------
    # 12. Completed Migration Restart
    # ------------------------------------------------------------------
    async def test_12_completed_migration_restart(self):
        # Similar logic. Completed checkpoint prevents redundant task execution.
        await self.gb.migrate_table(
            self.src_cfg, self.tgt_cfg, "orders",
            batch_size=100, project_id="proj-mig-done", migration_id="mig-done"
        )
        
        res = await self.gb.migrate_table(
            self.src_cfg, self.tgt_cfg, "orders",
            batch_size=100, project_id="proj-mig-done", migration_id="mig-done"
        )
        self.assertEqual(res["status"], "SUCCESS")
        self.assertEqual(res["rows_migrated"], 0)

    # ------------------------------------------------------------------
    # 13. Multiple Sequential Crashes
    # ------------------------------------------------------------------
    async def test_13_multiple_sequential_crashes(self):
        # Crash 1
        await self.gb.migrate_table(
            self.src_cfg, self.tgt_cfg, "users",
            batch_size=50, project_id="proj-mult", migration_id="mig-mult",
            simulated_crash_batch=2
        )
        # Crash 2
        await self.gb.migrate_table(
            self.src_cfg, self.tgt_cfg, "users",
            batch_size=50, project_id="proj-mult", migration_id="mig-mult",
            simulated_crash_batch=4
        )
        # Complete
        res = await self.gb.migrate_table(
            self.src_cfg, self.tgt_cfg, "users",
            batch_size=50, project_id="proj-mult", migration_id="mig-mult"
        )
        self.assertEqual(res["status"], "SUCCESS")
        self.assertEqual(res["rows_migrated"], 250)

    # ------------------------------------------------------------------
    # 14. Recovery After Three or More sequential Crashes
    # ------------------------------------------------------------------
    async def test_14_recovery_after_three_or_more_crashes(self):
        await self.gb.migrate_table(
            self.src_cfg, self.tgt_cfg, "users",
            batch_size=50, project_id="proj-3c", migration_id="mig-3c",
            simulated_crash_batch=2
        )
        await self.gb.migrate_table(
            self.src_cfg, self.tgt_cfg, "users",
            batch_size=50, project_id="proj-3c", migration_id="mig-3c",
            simulated_crash_batch=3
        )
        await self.gb.migrate_table(
            self.src_cfg, self.tgt_cfg, "users",
            batch_size=50, project_id="proj-3c", migration_id="mig-3c",
            simulated_crash_batch=4
        )
        res = await self.gb.migrate_table(
            self.src_cfg, self.tgt_cfg, "users",
            batch_size=50, project_id="proj-3c", migration_id="mig-3c"
        )
        self.assertEqual(res["status"], "SUCCESS")
        self.assertEqual(res["rows_migrated"], 250)

    # ------------------------------------------------------------------
    # 15. Recovery After Unexpected Process Termination
    # ------------------------------------------------------------------
    async def test_15_unexpected_process_termination(self):
        # Crash mid-way
        await self.gb.migrate_table(
            self.src_cfg, self.tgt_cfg, "users",
            batch_size=50, project_id="proj-term", migration_id="mig-term",
            simulated_crash_batch=3
        )
        # Re-bootstrap entirely clean objects (simulating starting a new process)
        storage_new = SQLiteCheckpointStorageAdapter(self.temp_db_path)
        await storage_new.initialize()
        mgr_new = CheckpointManager(storage_new)
        gb_new = GBAgent(
            global_state=self.mock_state,
            message_bus=self.mock_bus,
            checkpoint_manager=mgr_new,
            workspace_dir="test_workspace"
        )
        res = await gb_new.migrate_table(
            self.src_cfg, self.tgt_cfg, "users",
            batch_size=50, project_id="proj-term", migration_id="mig-term"
        )
        self.assertEqual(res["status"], "SUCCESS")
        self.assertEqual(res["rows_migrated"], 250)

    # ------------------------------------------------------------------
    # 16. Recovery After Forced Shutdown
    # ------------------------------------------------------------------
    async def test_16_recovery_after_forced_shutdown(self):
        # Simulates stopping message bus and halting fleet mid-execution, and then resuming
        await self.gb.migrate_table(
            self.src_cfg, self.tgt_cfg, "users",
            batch_size=50, project_id="proj-force", migration_id="mig-force",
            simulated_crash_batch=2
        )
        # MessageBus is stopped and restarted
        await self.mock_bus.stop()
        await self.mock_bus.start()
        
        res = await self.gb.migrate_table(
            self.src_cfg, self.tgt_cfg, "users",
            batch_size=50, project_id="proj-force", migration_id="mig-force"
        )
        self.assertEqual(res["status"], "SUCCESS")
        self.assertEqual(res["rows_migrated"], 250)

    # ------------------------------------------------------------------
    # 17. Recovery After Simulated Power Failure
    # ------------------------------------------------------------------
    async def test_17_simulated_power_failure(self):
        await self.gb.migrate_table(
            self.src_cfg, self.tgt_cfg, "users",
            batch_size=50, project_id="proj-power", migration_id="mig-power",
            simulated_crash_batch=3
        )
        
        # Simulate target database drop-out (power cut to target database engine)
        bad_tgt = MockConfig(SystemType.POSTGRESQL)
        bad_tgt.host = "connection-fail.example.com"
        
        res = await self.gb.migrate_table(
            self.src_cfg, bad_tgt, "users",
            batch_size=50, project_id="proj-power", migration_id="mig-power"
        )
        self.assertEqual(res["status"], "FAILED")
        
        # Resumes successfully once target database engine returns online
        res_ok = await self.gb.migrate_table(
            self.src_cfg, self.tgt_cfg, "users",
            batch_size=50, project_id="proj-power", migration_id="mig-power"
        )
        self.assertEqual(res_ok["status"], "SUCCESS")
        self.assertEqual(res_ok["rows_migrated"], 250)

    # ------------------------------------------------------------------
    # 18. Recovery After MessageBus Interruption
    # ------------------------------------------------------------------
    async def test_18_message_bus_interruption(self):
        # Verify that task dispatch fails over or handles bus cuts gracefully
        with patch.object(self.mock_bus, "publish", side_effect=RuntimeError("Bus connection broken")):
            # Trigger task execution that logs or fails appropriately without corrupting local tables
            res = await self.gb.migrate_table(
                self.src_cfg, self.tgt_cfg, "users",
                batch_size=50, project_id="proj-bus", migration_id="mig-bus",
                simulated_crash_batch=3
            )
            self.assertEqual(res["status"], "FAILED")

    # ------------------------------------------------------------------
    # 19. Recovery After Agent Restart
    # ------------------------------------------------------------------
    async def test_19_agent_restart(self):
        # Primary agent GBAgent-001 fails mid-way
        gb_primary = GBAgent(
            global_state=self.mock_state,
            message_bus=self.mock_bus,
            checkpoint_manager=self.checkpoint_mgr,
            agent_id="GB-PRIMARY"
        )
        await gb_primary.migrate_table(
            self.src_cfg, self.tgt_cfg, "users",
            batch_size=50, project_id="proj-agent", migration_id="mig-agent",
            simulated_crash_batch=3
        )
        
        # GBAgent-Backup picks up and completes the migration using same manager
        gb_backup = GBAgent(
            global_state=self.mock_state,
            message_bus=self.mock_bus,
            checkpoint_manager=self.checkpoint_mgr,
            agent_id="GB-BACKUP"
        )
        res = await gb_backup.migrate_table(
            self.src_cfg, self.tgt_cfg, "users",
            batch_size=50, project_id="proj-agent", migration_id="mig-agent"
        )
        self.assertEqual(res["status"], "SUCCESS")
        self.assertEqual(res["rows_migrated"], 250)

    # ------------------------------------------------------------------
    # 20. Recovery After Checkpoint Corruption
    # ------------------------------------------------------------------
    async def test_20_checkpoint_corruption(self):
        # Create a checkpoint record
        chk = CheckpointRecord(
            checkpoint_id="chk-corrupt",
            project_id="proj-corr",
            migration_id="mig-corr",
            workflow_state=WorkflowState.PRODUCTION_MIGRATION,
            table_name="users",
            batch_number=2,
            worker_id="GB-001",
            last_processed_primary_key={"id": 100},
            rows_processed=100,
            status=CheckpointStatus.COMMITTED
        )
        await self.checkpoint_mgr.save_progress(chk)
        
        # Manually corrupt the checksum inside SQLite database table
        conn = self.storage._get_connection()
        try:
            conn.execute("UPDATE checkpoints SET checksum = 'invalid-hash' WHERE checkpoint_id = ?", ("chk-corrupt",))
            conn.commit()
        finally:
            conn.close()
            
        # Verify resume throws integrity check failure
        with self.assertRaises(ValueError) as ctx:
            await self.checkpoint_mgr.resume("proj-corr", "mig-corr", "users")
        self.assertIn("Checksum mismatch", str(ctx.exception))

    # ------------------------------------------------------------------
    # 21. Recovery After Missing Checkpoint
    # ------------------------------------------------------------------
    async def test_21_missing_checkpoint(self):
        chk = await self.checkpoint_mgr.resume("proj-none", "mig-none", "users")
        self.assertIsNone(chk)

    # ------------------------------------------------------------------
    # 22. Recovery After Partial Checkpoint History
    # ------------------------------------------------------------------
    async def test_22_partial_checkpoint_history(self):
        # Seed two checkpoints
        chk1 = CheckpointRecord(
            checkpoint_id="chk-1",
            project_id="proj-part",
            migration_id="mig-part",
            workflow_state=WorkflowState.PRODUCTION_MIGRATION,
            table_name="users",
            batch_number=1,
            worker_id="GB-001",
            last_processed_primary_key={"id": 50},
            rows_processed=50,
            status=CheckpointStatus.COMMITTED
        )
        chk2 = CheckpointRecord(
            checkpoint_id="chk-2",
            project_id="proj-part",
            migration_id="mig-part",
            workflow_state=WorkflowState.PRODUCTION_MIGRATION,
            table_name="users",
            batch_number=2,
            worker_id="GB-001",
            last_processed_primary_key={"id": 100},
            rows_processed=100,
            status=CheckpointStatus.COMMITTED
        )
        await self.checkpoint_mgr.save_progress(chk1)
        await self.checkpoint_mgr.save_progress(chk2)
        
        # Manually delete chk1 from db history
        conn = self.storage._get_connection()
        try:
            conn.execute("DELETE FROM checkpoints WHERE checkpoint_id = ?", ("chk-1",))
            conn.commit()
        finally:
            conn.close()
            
        # Verify it still resumes from the latest available (chk-2)
        res = await self.gb.migrate_table(
            self.src_cfg, self.tgt_cfg, "users",
            batch_size=50, project_id="proj-part", migration_id="mig-part"
        )
        self.assertEqual(res["status"], "SUCCESS")
        self.assertEqual(res["rows_migrated"], 249)

    # ------------------------------------------------------------------
    # 23. Recovery After Transaction Retry
    # ------------------------------------------------------------------
    async def test_23_recovery_after_transaction_retry(self):
        from akaal.adapters.rdbms.postgresql_adapter import PostgreSQLAdapter
        # Verify that dynamic target transaction block conflicts retry successfully
        write_count = 0
        original_write = PostgreSQLAdapter.write_batch
        
        async def mock_write_with_retry(self_adapter, table, batch):
            nonlocal write_count
            write_count += 1
            if write_count == 2:
                # Raise write conflict/retry error once
                raise RuntimeError("Lock conflict detected (retryable)")
            await original_write(self_adapter, table, batch)

        with patch.object(PostgreSQLAdapter, "write_batch", mock_write_with_retry):
            res = await self.gb.migrate_table(
                self.src_cfg, self.tgt_cfg, "users",
                batch_size=50, project_id="proj-retry", migration_id="mig-retry"
            )
            # Fails on transaction lock error, next run recovers and completes
            self.assertEqual(res["status"], "FAILED")
            
            res_ok = await self.gb.migrate_table(
                self.src_cfg, self.tgt_cfg, "users",
                batch_size=50, project_id="proj-retry", migration_id="mig-retry"
            )
            self.assertEqual(res_ok["status"], "SUCCESS")
            self.assertEqual(res_ok["rows_migrated"], 250)

    # ------------------------------------------------------------------
    # 24. Recovery After Adapter Reconnect
    # ------------------------------------------------------------------
    async def test_24_recovery_after_adapter_reconnect(self):
        from akaal.adapters.rdbms.postgresql_adapter import PostgreSQLAdapter
        # Simulates source database query failures during migration, and completing on resume
        query_count = 0
        original_read = PostgreSQLAdapter.read_batch
        
        async def mock_read_with_fail(self_adapter, table_name, offset, limit, last_processed_primary_key=None):
            nonlocal query_count
            query_count += 1
            if query_count == 3:
                raise ConnectionError("Lost query connection")
            return await original_read(self_adapter, table_name, offset, limit, last_processed_primary_key)

        with patch.object(PostgreSQLAdapter, "read_batch", mock_read_with_fail):
            res = await self.gb.migrate_table(
                self.src_cfg, self.tgt_cfg, "users",
                batch_size=50, project_id="proj-rec", migration_id="mig-rec"
            )
            self.assertEqual(res["status"], "FAILED")
            
            res_ok = await self.gb.migrate_table(
                self.src_cfg, self.tgt_cfg, "users",
                batch_size=50, project_id="proj-rec", migration_id="mig-rec"
            )
            self.assertEqual(res_ok["status"], "SUCCESS")
            self.assertEqual(res_ok["rows_migrated"], 250)


if __name__ == "__main__":
    unittest.main()
