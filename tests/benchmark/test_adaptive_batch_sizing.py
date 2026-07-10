import asyncio
import os
import tempfile
import unittest
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, patch

from akaal.core.models.enums import SystemType, WorkflowState
from akaal.core.state.global_state import GlobalState
from akaal.core.message_bus.bus import MessageBus
from akaal.core.checkpoint.checkpoint_record import CheckpointRecord, CheckpointStatus
from akaal.core.checkpoint.checkpoint_manager import CheckpointManager
from akaal.core.checkpoint.storage.sqlite_storage import SQLiteCheckpointStorageAdapter
from akaal.agents.gb.gb_agent import GBAgent, AdaptiveBatchGovernor


class MockConfig:
    def __init__(self, system_type: SystemType, mock_max_rows: int = 150):
        self.system_type = system_type
        self.mock_mode = True
        self.database_name = "test_db"
        self.db_path = ":memory:"
        self.host = "source-db.example.com"
        self.mock_max_rows = mock_max_rows


class TestAdaptiveBatchSizing(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self):
        self.temp_db_fd, self.temp_db_path = tempfile.mkstemp(suffix=".db")
        os.close(self.temp_db_fd)
        
        self.storage = SQLiteCheckpointStorageAdapter(self.temp_db_path)
        await self.storage.initialize()
        self.checkpoint_mgr = CheckpointManager(self.storage)

        self.mock_state = MagicMock(spec=GlobalState)
        self.mock_state._mock_return_value = None
        self.mock_state.get_project = MagicMock(return_value=None)
        
        self.mock_bus = MagicMock(spec=MessageBus)

        self.gb = GBAgent(
            global_state=self.mock_state,
            message_bus=self.mock_bus,
            checkpoint_manager=self.checkpoint_mgr,
            workspace_dir="test_workspace"
        )

        self.src_cfg = MockConfig(SystemType.POSTGRESQL, mock_max_rows=150)
        self.tgt_cfg = MockConfig(SystemType.POSTGRESQL, mock_max_rows=150)

    async def asyncTearDown(self):
        await self.storage.clear_migration("proj-1", "mig-1")
        try:
            os.remove(self.temp_db_path)
        except Exception:
            pass

    # Helper to generate mock time sequence
    def make_time_generator(self, durations, default_duration=1.0):
        current_time = 0.0
        yield current_time
        for dur in durations:
            yield current_time
            current_time += dur / 2.0
            yield current_time
            yield current_time
            current_time += dur / 2.0
            yield current_time
            yield current_time
        # Fallback to prevent StopIteration
        while True:
            yield current_time
            current_time += default_duration / 2.0
            yield current_time
            yield current_time
            current_time += default_duration / 2.0
            yield current_time
            yield current_time

    # 1. Fixed batch startup
    async def test_fixed_batch_startup(self):
        # With growth_factor=1.0, batch size is locked at 100.
        # Max rows = 150, so we expect exactly 2 batches.
        res = await self.gb.migrate_table(
            self.src_cfg, self.tgt_cfg, "users",
            batch_size=50, project_id="proj-1", migration_id="mig-1",
            use_adaptive_batch=True,
            initial_batch_size=100,
            growth_factor=1.0
        )
        self.assertEqual(res["status"], "SUCCESS")
        self.assertEqual(res["batches_processed"], 2)
        self.assertEqual(res["rows_migrated"], 150)

    # 2. Adaptive growth
    @patch.object(GBAgent, "_get_time")
    async def test_adaptive_growth(self, mock_time):
        # We specify durations that are way below target (1000ms), e.g. 50ms (0.05s)
        # So duration < 0.7 * target_seconds
        durations = [0.05, 0.05, 0.05, 0.05, 0.05]
        mock_time.side_effect = self.make_time_generator(durations)

        res = await self.gb.migrate_table(
            self.src_cfg, self.tgt_cfg, "users",
            batch_size=50, project_id="proj-1", migration_id="mig-1",
            use_adaptive_batch=True,
            initial_batch_size=30,
            growth_factor=2.0,
            target_batch_duration_ms=1000.0,
            adjustment_window=1  # adjust on every batch for testing
        )
        self.assertEqual(res["status"], "SUCCESS")
        # Starts at 30. Grew to 60. Grew to 120.
        self.assertEqual(res["rows_migrated"], 150)
        self.assertGreater(res["avg_batch_size"], 30)

    # 3. Adaptive shrink
    @patch.object(GBAgent, "_get_time")
    async def test_adaptive_shrink(self, mock_time):
        # We specify durations that exceed the target (1000ms), e.g. 1500ms (1.5s)
        durations = [1.5, 1.5, 1.5, 1.5, 1.5, 1.5, 1.5, 1.5, 1.5, 1.5]
        mock_time.side_effect = self.make_time_generator(durations, default_duration=1.5)

        res = await self.gb.migrate_table(
            self.src_cfg, self.tgt_cfg, "users",
            batch_size=50, project_id="proj-1", migration_id="mig-1",
            use_adaptive_batch=True,
            initial_batch_size=100,
            shrink_factor=0.5,
            target_batch_duration_ms=1000.0,
            adjustment_window=1
        )
        self.assertEqual(res["status"], "SUCCESS")
        self.assertEqual(res["rows_migrated"], 150)
        self.assertLess(res["avg_batch_size"], 100)

    # 4. Minimum limit enforcement
    @patch.object(GBAgent, "_get_time")
    async def test_minimum_limit_enforcement(self, mock_time):
        durations = [2.0] * 10
        mock_time.side_effect = self.make_time_generator(durations, default_duration=2.0)

        res = await self.gb.migrate_table(
            self.src_cfg, self.tgt_cfg, "users",
            batch_size=50, project_id="proj-1", migration_id="mig-1",
            use_adaptive_batch=True,
            initial_batch_size=20,
            minimum_batch_size=15,
            shrink_factor=0.5,
            target_batch_duration_ms=1000.0,
            adjustment_window=1
        )
        self.assertEqual(res["status"], "SUCCESS")
        # Shrinks from 20 to 15 (cannot go lower than 15)
        self.assertEqual(res["avg_batch_size"], 15.0)

    # 5. Maximum limit enforcement
    @patch.object(GBAgent, "_get_time")
    async def test_maximum_limit_enforcement(self, mock_time):
        durations = [0.01] * 10
        mock_time.side_effect = self.make_time_generator(durations, default_duration=0.01)

        res = await self.gb.migrate_table(
            self.src_cfg, self.tgt_cfg, "users",
            batch_size=50, project_id="proj-1", migration_id="mig-1",
            use_adaptive_batch=True,
            initial_batch_size=50,
            maximum_batch_size=80,
            growth_factor=2.0,
            target_batch_duration_ms=1000.0,
            adjustment_window=1
        )
        self.assertEqual(res["status"], "SUCCESS")
        # Grows from 50 -> 80 (maxed out)
        self.assertEqual(res["avg_batch_size"], 80.0)

    # 6. Retry-triggered reduction & 16. Recovery after checkpoint resume
    async def test_retry_triggered_reduction(self):
        # We seed a checkpoint with retry_count = 1
        record = CheckpointRecord(
            checkpoint_id="chk-retry-1",
            project_id="proj-1",
            migration_id="mig-1",
            workflow_state=WorkflowState.PRODUCTION_MIGRATION,
            table_name="users",
            batch_number=1,
            worker_id="GB-001",
            last_processed_primary_key={"id": 50},
            rows_processed=50,
            rows_failed=0,
            rows_skipped=0,
            retry_count=1,
            adapter_state={"offset": 50},
            metrics={"batch_size": 100},
            status=CheckpointStatus.COMMITTED
        )
        await self.checkpoint_mgr.save_progress(record)

        # On resume, GBAgent sees retry_count = record.retry_count + 1 = 2
        # Since retry_count > 1, it should shrink initial batch size (from 100 to 100 * shrink_factor = 50)
        # Lock growth using growth_factor=1.0
        res = await self.gb.migrate_table(
            self.src_cfg, self.tgt_cfg, "users",
            batch_size=50, project_id="proj-1", migration_id="mig-1",
            use_adaptive_batch=True,
            initial_batch_size=100,
            shrink_factor=0.5,
            growth_factor=1.0
        )
        self.assertEqual(res["status"], "SUCCESS")
        self.assertEqual(res["avg_batch_size"], 50.0)

    # 7. Checkpoint compatibility & 15. Recovery after restart
    async def test_checkpoint_compatibility(self):
        # Run a partial migration by crash testing. Lock growth using growth_factor=1.0.
        try:
            await self.gb.migrate_table(
                self.src_cfg, self.tgt_cfg, "users",
                batch_size=50, project_id="proj-1", migration_id="mig-1",
                use_adaptive_batch=True,
                initial_batch_size=40,
                growth_factor=1.0,
                simulated_crash_batch=3
            )
        except ConnectionResetError:
            pass

        # Verify that checkpoint is saved with adaptive governor metrics and state
        records = await self.checkpoint_mgr.list_checkpoints("proj-1", "mig-1")
        pending_or_committed = [r for r in records if r.table_name == "users"]
        self.assertTrue(len(pending_or_committed) > 0)
        latest_checkpoint = pending_or_committed[-1]
        
        self.assertIn("batch_size", latest_checkpoint.metrics)
        self.assertIn("adaptive_governor_state", latest_checkpoint.metrics)
        gov_state = latest_checkpoint.metrics["adaptive_governor_state"]
        self.assertEqual(gov_state["current_batch_size"], 40)

        # Now resume, and verify that the governor state is successfully restored
        res = await self.gb.migrate_table(
            self.src_cfg, self.tgt_cfg, "users",
            batch_size=50, project_id="proj-1", migration_id="mig-1",
            use_adaptive_batch=True,
            initial_batch_size=40,
            growth_factor=1.0
        )
        self.assertEqual(res["status"], "SUCCESS")
        self.assertEqual(res["rows_migrated"], 150)

    # 8. Cursor compatibility & 9. Transaction correctness
    async def test_cursor_and_transaction_correctness(self):
        res = await self.gb.migrate_table(
            self.src_cfg, self.tgt_cfg, "users",
            batch_size=50, project_id="proj-1", migration_id="mig-1",
            use_adaptive_batch=True,
            initial_batch_size=33
        )
        self.assertEqual(res["status"], "SUCCESS")
        self.assertEqual(res["rows_migrated"], 150)

        checkpoints = await self.checkpoint_mgr.list_checkpoints("proj-1", "mig-1")
        users_chk = [c for c in checkpoints if c.table_name == "users" and c.batch_number > 0]
        
        processed = [c.rows_processed for c in users_chk]
        self.assertEqual(processed, sorted(processed))

    # 10. Zero duplicate rows & 11. Zero skipped rows
    async def test_zero_duplicate_and_skipped_rows(self):
        res = await self.gb.migrate_table(
            self.src_cfg, self.tgt_cfg, "users",
            batch_size=50, project_id="proj-1", migration_id="mig-1",
            use_adaptive_batch=True,
            initial_batch_size=15,
            growth_factor=1.5,
            shrink_factor=0.8,
            target_batch_duration_ms=10.0,
            adjustment_window=1
        )
        self.assertEqual(res["status"], "SUCCESS")
        self.assertEqual(res["rows_migrated"], 150)

    # 12. Deterministic behavior
    async def test_deterministic_behavior(self):
        res_1 = await self.gb.migrate_table(
            self.src_cfg, self.tgt_cfg, "users",
            batch_size=50, project_id="proj-1", migration_id="mig-1",
            use_adaptive_batch=True,
            initial_batch_size=20,
            growth_factor=2.0,
            target_batch_duration_ms=2000.0,
            adjustment_window=1
        )
        await self.storage.clear_migration("proj-1", "mig-1")
        
        res_2 = await self.gb.migrate_table(
            self.src_cfg, self.tgt_cfg, "users",
            batch_size=50, project_id="proj-1", migration_id="mig-1",
            use_adaptive_batch=True,
            initial_batch_size=20,
            growth_factor=2.0,
            target_batch_duration_ms=2000.0,
            adjustment_window=1
        )
        self.assertEqual(res_1["adjustment_frequency"], res_2["adjustment_frequency"])
        self.assertEqual(res_1["avg_batch_size"], res_2["avg_batch_size"])

    # 13. Long-running migration
    async def test_long_running_migration(self):
        big_src = MockConfig(SystemType.POSTGRESQL, mock_max_rows=1000)
        big_tgt = MockConfig(SystemType.POSTGRESQL, mock_max_rows=1000)
        res = await self.gb.migrate_table(
            big_src, big_tgt, "big_table",
            batch_size=50, project_id="proj-1", migration_id="mig-1",
            use_adaptive_batch=True,
            initial_batch_size=100
        )
        self.assertEqual(res["status"], "SUCCESS")
        self.assertEqual(res["rows_migrated"], 1000)

    # 14. Parallel migration compatibility
    async def test_parallel_migration_compatibility(self):
        t1 = self.gb.migrate_table(
            self.src_cfg, self.tgt_cfg, "table_one",
            batch_size=50, project_id="proj-1", migration_id="mig-1",
            use_adaptive_batch=True,
            initial_batch_size=50
        )
        t2 = self.gb.migrate_table(
            self.src_cfg, self.tgt_cfg, "table_two",
            batch_size=50, project_id="proj-1", migration_id="mig-1",
            use_adaptive_batch=True,
            initial_batch_size=50
        )
        results = await asyncio.gather(t1, t2)
        self.assertEqual(results[0]["status"], "SUCCESS")
        self.assertEqual(results[1]["status"], "SUCCESS")

    # 17. Stable oscillation prevention
    @patch.object(GBAgent, "_get_time")
    async def test_stable_oscillation_prevention(self, mock_time):
        # Bounce durations inside the hysteresis deadband [700ms, 1100ms]
        durations = [0.8, 1.05, 0.8, 1.05, 0.8, 1.05]
        mock_time.side_effect = self.make_time_generator(durations, default_duration=1.0)

        res = await self.gb.migrate_table(
            self.src_cfg, self.tgt_cfg, "users",
            batch_size=50, project_id="proj-1", migration_id="mig-1",
            use_adaptive_batch=True,
            initial_batch_size=50,
            growth_factor=2.0,
            shrink_factor=0.5,
            target_batch_duration_ms=1000.0,
            adjustment_window=1
        )
        self.assertEqual(res["status"], "SUCCESS")
        self.assertEqual(res["adjustment_frequency"], 0)
        self.assertEqual(res["avg_batch_size"], 50.0)

    # 18. Performance comparison against fixed batch sizing
    async def test_performance_comparison(self):
        res_fixed = await self.gb.migrate_table(
            self.src_cfg, self.tgt_cfg, "users",
            batch_size=20, project_id="proj-fixed", migration_id="mig-fixed",
            use_adaptive_batch=False
        )
        res_adaptive = await self.gb.migrate_table(
            self.src_cfg, self.tgt_cfg, "users",
            batch_size=20, project_id="proj-adaptive", migration_id="mig-adaptive",
            use_adaptive_batch=True,
            initial_batch_size=20,
            maximum_batch_size=200,
            target_batch_duration_ms=2000.0,
            adjustment_window=1
        )
        self.assertLess(res_adaptive["batches_processed"], res_fixed["batches_processed"])
        self.assertEqual(res_adaptive["rows_migrated"], 150)
        self.assertEqual(res_fixed["rows_migrated"], 150)


if __name__ == "__main__":
    unittest.main()
