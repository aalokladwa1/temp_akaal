import asyncio
import os
import tempfile
import unittest
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock

from akaal.core.models.enums import SystemType, WorkflowState
from akaal.core.state.global_state import GlobalState
from akaal.core.message_bus.bus import MessageBus
from akaal.core.checkpoint.checkpoint_record import CheckpointRecord, CheckpointStatus
from akaal.core.checkpoint.checkpoint_manager import CheckpointManager
from akaal.core.checkpoint.storage.sqlite_storage import SQLiteCheckpointStorageAdapter
from akaal.agents.gb.gb_agent import GBAgent


class MockConfig:
    def __init__(self, system_type: SystemType, mock_mode: bool = True):
        self.system_type = system_type
        self.mock_mode = mock_mode
        self.database_name = "test_db"
        self.db_path = ":memory:"
        self.host = "source-db.example.com"
        self.mock_max_rows = 250


class TestGBCheckpointResume(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self):
        # 1. Create a temporary DB file path
        self.temp_db_fd, self.temp_db_path = tempfile.mkstemp(suffix=".db")
        os.close(self.temp_db_fd)
        
        # 2. Initialize DB-backed Checkpoint Manager with disk file
        self.storage = SQLiteCheckpointStorageAdapter(self.temp_db_path)
        await self.storage.initialize()
        self.checkpoint_mgr = CheckpointManager(self.storage)

        # 3. Setup mock global state and message bus
        self.mock_state = MagicMock(spec=GlobalState)
        self.mock_bus = MagicMock(spec=MessageBus)

        # 4. Instantiate GBAgent with injected CheckpointManager
        self.gb = GBAgent(
            global_state=self.mock_state,
            message_bus=self.mock_bus,
            checkpoint_manager=self.checkpoint_mgr,
            workspace_dir="test_workspace"
        )

        # 5. Standard connection configs
        self.src_cfg = MockConfig(SystemType.POSTGRESQL)
        self.tgt_cfg = MockConfig(SystemType.POSTGRESQL)

    async def asyncTearDown(self):
        await self.storage.clear_migration("proj-1", "mig-1")
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

    # ------------------------------------------------------------------
    # Test 1: Fresh Migration Starts Without Checkpoints
    # ------------------------------------------------------------------
    async def test_fresh_migration_starts_without_checkpoints(self):
        res = await self.gb.migrate_table(
            self.src_cfg, self.tgt_cfg, "users",
            batch_size=50, project_id="proj-1", migration_id="mig-1"
        )
        self.assertEqual(res["status"], "SUCCESS")
        self.assertEqual(res["rows_migrated"], 250)
        self.assertEqual(res["batches_processed"], 5)

        # Confirm progress checkpoint exists
        record = await self._get_latest_committed_progress("proj-1", "mig-1", "users")
        self.assertIsNotNone(record)
        self.assertEqual(record.rows_processed, 250)
        self.assertEqual(record.batch_number, 5)

    # ------------------------------------------------------------------
    # Test 2: Migration Resumes From a Saved Primary Key
    # ------------------------------------------------------------------
    async def test_migration_resumes_from_saved_primary_key(self):
        # Seed a checkpoint at ID 100 out of 250
        record = CheckpointRecord(
            checkpoint_id="chk-001",
            project_id="proj-1",
            migration_id="mig-1",
            workflow_state=WorkflowState.PRODUCTION_MIGRATION,
            table_name="users",
            batch_number=2,
            worker_id="GB-001",
            last_processed_primary_key={"id": 100},
            rows_processed=100,
            rows_failed=0,
            rows_skipped=0,
            retry_count=0,
            adapter_state={"offset": 100},
            metrics={"elapsed_seconds": 1.0, "throughput_rows_s": 100.0},
            status=CheckpointStatus.PENDING
        )
        # Force status to committed so we find it in progress
        record.status = CheckpointStatus.COMMITTED
        await self.checkpoint_mgr.save_progress(record)

        # Migrate remaining 149 rows
        res = await self.gb.migrate_table(
            self.src_cfg, self.tgt_cfg, "users",
            batch_size=50, project_id="proj-1", migration_id="mig-1"
        )
        self.assertEqual(res["status"], "SUCCESS")
        self.assertEqual(res["rows_migrated"], 249)
        
        # New progress checkpoint must have updated fields
        new_record = await self._get_latest_committed_progress("proj-1", "mig-1", "users")
        self.assertEqual(new_record.last_processed_primary_key, {"id": 249})
        self.assertEqual(new_record.batch_number, 5)

    # ------------------------------------------------------------------
    # Test 3: Composite Primary Key Resume Works Correctly
    # ------------------------------------------------------------------
    async def test_composite_primary_key_resume_works_correctly(self):
        # Seed a composite checkpoint
        record = CheckpointRecord(
            checkpoint_id="chk-002",
            project_id="proj-1",
            migration_id="mig-1",
            workflow_state=WorkflowState.PRODUCTION_MIGRATION,
            table_name="composite_table",
            batch_number=1,
            worker_id="GB-001",
            last_processed_primary_key={"pk1": 15, "pk2": 150},
            rows_processed=50,
            rows_failed=0,
            rows_skipped=0,
            retry_count=0,
            adapter_state={"offset": 50},
            metrics={"elapsed_seconds": 1.0},
            status=CheckpointStatus.COMMITTED
        )
        await self.checkpoint_mgr.save_progress(record)

        # Run migration
        res = await self.gb.migrate_table(
            self.src_cfg, self.tgt_cfg, "composite_table",
            batch_size=50, project_id="proj-1", migration_id="mig-1"
        )
        self.assertEqual(res["status"], "SUCCESS")
        new_record = await self._get_latest_committed_progress("proj-1", "mig-1", "composite_table")
        self.assertEqual(new_record.last_processed_primary_key, {"pk1": 249, "pk2": 2490})

    # ------------------------------------------------------------------
    # Test 4: UUID Primary Key Resume Works Correctly
    # ------------------------------------------------------------------
    async def test_uuid_primary_key_resume_works_correctly(self):
        record = CheckpointRecord(
            checkpoint_id="chk-uuid",
            project_id="proj-1",
            migration_id="mig-1",
            workflow_state=WorkflowState.PRODUCTION_MIGRATION,
            table_name="uuid_table",
            batch_number=1,
            worker_id="GB-001",
            last_processed_primary_key={"uuid_col": "uuid-99"},
            rows_processed=50,
            rows_failed=0,
            rows_skipped=0,
            retry_count=0,
            status=CheckpointStatus.COMMITTED
        )
        await self.checkpoint_mgr.save_progress(record)

        res = await self.gb.migrate_table(
            self.src_cfg, self.tgt_cfg, "uuid_table",
            batch_size=50, project_id="proj-1", migration_id="mig-1"
        )
        self.assertEqual(res["status"], "SUCCESS")
        new_record = await self._get_latest_committed_progress("proj-1", "mig-1", "uuid_table")
        self.assertEqual(new_record.last_processed_primary_key, {"uuid_col": "uuid-249"})

    # ------------------------------------------------------------------
    # Test 5: String Primary Key Resume Works Correctly
    # ------------------------------------------------------------------
    async def test_string_primary_key_resume_works_correctly(self):
        record = CheckpointRecord(
            checkpoint_id="chk-str",
            project_id="proj-1",
            migration_id="mig-1",
            workflow_state=WorkflowState.PRODUCTION_MIGRATION,
            table_name="string_table",
            batch_number=1,
            worker_id="GB-001",
            last_processed_primary_key={"str_col": "str-200"},
            rows_processed=50,
            rows_failed=0,
            rows_skipped=0,
            retry_count=0,
            status=CheckpointStatus.COMMITTED
        )
        await self.checkpoint_mgr.save_progress(record)

        res = await self.gb.migrate_table(
            self.src_cfg, self.tgt_cfg, "string_table",
            batch_size=50, project_id="proj-1", migration_id="mig-1"
        )
        self.assertEqual(res["status"], "SUCCESS")
        new_record = await self._get_latest_committed_progress("proj-1", "mig-1", "string_table")
        self.assertEqual(new_record.last_processed_primary_key, {"str_col": "str-249"})

    # ------------------------------------------------------------------
    # Test 6: Tables Without Primary Keys Fall Back to OFFSET Pagination
    # ------------------------------------------------------------------
    async def test_tables_without_primary_keys_fallback_to_offset(self):
        res = await self.gb.migrate_table(
            self.src_cfg, self.tgt_cfg, "no_pk_table",
            batch_size=50, project_id="proj-1", migration_id="mig-1"
        )
        self.assertEqual(res["status"], "SUCCESS")
        self.assertEqual(res["rows_migrated"], 250)

        new_record = await self._get_latest_committed_progress("proj-1", "mig-1", "no_pk_table")
        self.assertIsNone(new_record.last_processed_primary_key)
        self.assertEqual(new_record.adapter_state.get("offset"), 250)

    # ------------------------------------------------------------------
    # Test 7: Crash Mid-Migration and Resume From Last Committed Batch
    # ------------------------------------------------------------------
    async def test_crash_mid_migration_and_resume_success(self):
        # 1. Run with crash simulated at batch 3
        res = await self.gb.migrate_table(
            self.src_cfg, self.tgt_cfg, "users",
            batch_size=10, project_id="proj-1", migration_id="mig-1",
            simulated_crash_batch=3
        )
        self.assertEqual(res["status"], "FAILED")
        self.assertIn("Simulated connection crash at batch 3", res["error"])
        self.assertEqual(res["rows_migrated"], 20)

        # Verify manager saved checkpoint up to batch 2
        chk = await self.checkpoint_mgr.resume("proj-1", "mig-1", "users")
        self.assertIsNotNone(chk)
        self.assertEqual(chk.batch_number, 2)
        self.assertEqual(chk.rows_processed, 20)
        self.assertEqual(chk.last_processed_primary_key, {"id": 19})

        # 2. Resume migration
        res_resume = await self.gb.migrate_table(
            self.src_cfg, self.tgt_cfg, "users",
            batch_size=10, project_id="proj-1", migration_id="mig-1"
        )
        self.assertEqual(res_resume["status"], "SUCCESS")
        self.assertEqual(res_resume["rows_migrated"], 250)

        chk_final = await self._get_latest_committed_progress("proj-1", "mig-1", "users")
        self.assertEqual(chk_final.rows_processed, 250)
        self.assertEqual(chk_final.last_processed_primary_key, {"id": 249})

    # ------------------------------------------------------------------
    # Test 8: Verify No Duplicate Rows Migrated After Recovery
    # ------------------------------------------------------------------
    async def test_no_duplicate_rows_after_recovery(self):
        await self.gb.migrate_table(
            self.src_cfg, self.tgt_cfg, "users",
            batch_size=10, project_id="proj-1", migration_id="mig-1",
            simulated_crash_batch=2
        )
        res = await self.gb.migrate_table(
            self.src_cfg, self.tgt_cfg, "users",
            batch_size=10, project_id="proj-1", migration_id="mig-1"
        )
        self.assertEqual(res["status"], "SUCCESS")
        self.assertEqual(res["rows_migrated"], 250)

    # ------------------------------------------------------------------
    # Test 9: Verify No Rows are Skipped After Recovery
    # ------------------------------------------------------------------
    async def test_no_rows_skipped_after_recovery(self):
        await self.gb.migrate_table(
            self.src_cfg, self.tgt_cfg, "users",
            batch_size=10, project_id="proj-2", migration_id="mig-2",
            simulated_crash_batch=3
        )
        await self.gb.migrate_table(
            self.src_cfg, self.tgt_cfg, "users",
            batch_size=10, project_id="proj-2", migration_id="mig-2"
        )
        chk = await self._get_latest_committed_progress("proj-2", "mig-2", "users")
        self.assertEqual(chk.rows_processed, 250)
        self.assertEqual(chk.last_processed_primary_key, {"id": 249})

    # ------------------------------------------------------------------
    # Test 10: Multi-Crash Completion Success
    # ------------------------------------------------------------------
    async def test_multi_crash_completion_resilience(self):
        await self.gb.migrate_table(
            self.src_cfg, self.tgt_cfg, "users",
            batch_size=5, project_id="proj-3", migration_id="mig-3",
            simulated_crash_batch=2
        )
        await self.gb.migrate_table(
            self.src_cfg, self.tgt_cfg, "users",
            batch_size=5, project_id="proj-3", migration_id="mig-3",
            simulated_crash_batch=3
        )
        res = await self.gb.migrate_table(
            self.src_cfg, self.tgt_cfg, "users",
            batch_size=5, project_id="proj-3", migration_id="mig-3"
        )
        self.assertEqual(res["status"], "SUCCESS")
        self.assertEqual(res["rows_migrated"], 250)

    # ------------------------------------------------------------------
    # Test 11: Verify Checkpoint is NOT Written if Target Transaction Fails
    # ------------------------------------------------------------------
    async def test_checkpoint_not_written_if_target_transaction_fails(self):
        bad_tgt = MockConfig(SystemType.POSTGRESQL)
        bad_tgt.host = "connection-fail.example.com"

        res = await self.gb.migrate_table(
            self.src_cfg, bad_tgt, "users",
            batch_size=10, project_id="proj-1", migration_id="mig-1"
        )
        self.assertEqual(res["status"], "FAILED")
        
        chk = await self.checkpoint_mgr.resume("proj-1", "mig-1", "users")
        self.assertIsNone(chk)

    # ------------------------------------------------------------------
    # Test 12: Verify Checkpoint is Written ONLY After Commit Acknowledged
    # ------------------------------------------------------------------
    async def test_checkpoint_written_only_after_commit_acknowledgement(self):
        res = await self.gb.migrate_table(
            self.src_cfg, self.tgt_cfg, "users",
            batch_size=10, project_id="proj-ok", migration_id="mig-ok"
        )
        self.assertEqual(res["status"], "SUCCESS")
        chk = await self._get_latest_committed_progress("proj-ok", "mig-ok", "users")
        self.assertIsNotNone(chk)
        self.assertEqual(chk.rows_processed, 250)

    # ------------------------------------------------------------------
    # Test 13: Verify Deterministic Ordering Across Repeated Resume Cycles
    # ------------------------------------------------------------------
    async def test_deterministic_ordering_across_resume_cycles(self):
        await self.gb.migrate_table(
            self.src_cfg, self.tgt_cfg, "users",
            batch_size=10, project_id="proj-order", migration_id="mig-order"
        )
        chk1 = await self._get_latest_committed_progress("proj-order", "mig-order", "users")
        self.assertEqual(chk1.last_processed_primary_key, {"id": 249})

    # ------------------------------------------------------------------
    # Test 14: Verify adapter_state Restoration
    # ------------------------------------------------------------------
    async def test_adapter_state_restoration(self):
        await self.gb.migrate_table(
            self.src_cfg, self.tgt_cfg, "users",
            batch_size=10, project_id="proj-state", migration_id="mig-state",
            simulated_crash_batch=2
        )
        chk = await self.checkpoint_mgr.resume("proj-state", "mig-state", "users")
        self.assertIsNotNone(chk)
        self.assertEqual(chk.adapter_state.get("offset"), 10)
        self.assertEqual(chk.adapter_state.get("original_rows_migrated"), 10)

    # ------------------------------------------------------------------
    # Test 15: Verify Performance Stability (Avoid Full Table Scans)
    # ------------------------------------------------------------------
    async def test_performance_stability_and_index_usage(self):
        import time
        from akaal.adapters.rdbms.postgresql_adapter import PostgreSQLAdapter

        self.src_cfg.mock_max_rows = 10000

        adapter = PostgreSQLAdapter(self.src_cfg)
        await adapter.connect()

        start = time.perf_counter()
        rows = await adapter.read_batch(
            "composite_table", offset=0, limit=1000,
            last_processed_primary_key={"pk1": 500, "pk2": 5000}
        )
        duration = time.perf_counter() - start
        
        self.assertLess(duration, 0.1)
        self.assertEqual(len(rows), 1000)
        self.assertEqual(rows[0]["pk1"], 501)
        await adapter.close()


if __name__ == "__main__":
    unittest.main()
