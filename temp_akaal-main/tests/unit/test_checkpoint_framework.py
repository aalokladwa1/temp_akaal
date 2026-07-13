"""
Akaal — Checkpoint Framework Test Suite
========================================
Validates all features of the upgraded production checkpoint subsystem, 
including enums, storage engines, factories, concurrent writes, and stress testing.
"""

import asyncio
import json
import logging
import os
import shutil
import tempfile
import unittest
from datetime import datetime, timezone
import uuid

from akaal.core.checkpoint.checkpoint_record import CheckpointRecord, CheckpointStatus
from akaal.core.checkpoint.checkpoint_manager import CheckpointManager
from akaal.core.checkpoint.storage.factory import CheckpointStorageFactory
from akaal.core.checkpoint.storage.sqlite_storage import SQLiteCheckpointStorageAdapter
from akaal.core.checkpoint.storage.file_storage import FileCheckpointStorageAdapter
from akaal.core.models.enums import WorkflowState

# Configure logging for tests
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("tests.checkpoint")


class TestCheckpointFramework(unittest.IsolatedAsyncioTestCase):
    """Stress and verification tests for the Checkpoint subsystem."""

    async def asyncSetUp(self) -> None:
        # Create a temporary directory for tests
        self.test_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.test_dir, "test_checkpoints.db")
        
        # Initialize storage adapters
        self.sqlite_adapter = SQLiteCheckpointStorageAdapter(self.db_path)
        await self.sqlite_adapter.initialize()
        
        self.file_adapter = FileCheckpointStorageAdapter(self.test_dir)
        await self.file_adapter.initialize()
        
        # Instantiate managers
        self.sqlite_mgr = CheckpointManager(self.sqlite_adapter)
        self.file_mgr = CheckpointManager(self.file_adapter)
        
        # Sample base record
        self.sample_record = CheckpointRecord(
            checkpoint_id="chk-sample-001",
            project_id="proj-test-1",
            migration_id="mig-session-A",
            workflow_state=WorkflowState.PRODUCTION_MIGRATION,
            table_name="inventory",
            batch_number=10,
            worker_id="worker-node-1",
            last_processed_primary_key={"id": 500, "sku": "ABC-123"},
            rows_processed=10000,
            rows_failed=5,
            rows_skipped=12,
            retry_count=2,
            adapter_state={"current_offset": 54321},
            metrics={"speed_mb_s": 42.1}
        )

    async def asyncTearDown(self) -> None:
        # Clean up temp files
        try:
            shutil.rmtree(self.test_dir)
        except Exception:
            pass

    def test_checksum_validation(self) -> None:
        """Verify that checksum calculation is correct and immutable fields affect it, while mutables do not."""
        record = self.sample_record
        initial_checksum = record.calculate_checksum()
        record.checksum = initial_checksum
        
        self.assertTrue(record.verify_integrity())
        
        # Mutating status, metrics, or updated_at MUST NOT affect checksum calculation
        record.status = CheckpointStatus.FAILED
        record.metrics["latency_ms"] = 99.9
        record.updated_at = datetime.now(timezone.utc).isoformat()
        
        self.assertEqual(record.calculate_checksum(), initial_checksum)
        self.assertTrue(record.verify_integrity())
        
        # Mutating an immutable progress field MUST change checksum calculation
        record.rows_processed = 10001
        self.assertNotEqual(record.calculate_checksum(), initial_checksum)
        self.assertFalse(record.verify_integrity())

    async def test_corruption_detection(self) -> None:
        """Verify that load_progress raises ValueError when a checkpoint has been corrupted."""
        # Save record to both adapters
        record = self.sample_record
        record.checksum = record.calculate_checksum()
        
        await self.sqlite_mgr.save_progress(record)
        await self.file_mgr.save_progress(record)
        
        # Corrupt DB record directly via SQLite cursor bypassing manager
        conn = self.sqlite_adapter._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("UPDATE checkpoints SET rows_processed = 999999 WHERE checkpoint_id = ?", (record.checkpoint_id,))
            conn.commit()
        finally:
            conn.close()
            
        with self.assertRaises(ValueError) as ctx:
            await self.sqlite_mgr.load_progress(record.checkpoint_id)
        self.assertIn("CHECKPOINT CORRUPTION", str(ctx.exception))
        
        # Corrupt File record directly on filesystem
        file_path = self.file_adapter._get_file_path(record.project_id, record.checkpoint_id)
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        data["rows_processed"] = 999999
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f)
            
        with self.assertRaises(ValueError) as ctx:
            await self.file_mgr.load_progress(record.checkpoint_id)
        self.assertIn("CHECKPOINT CORRUPTION", str(ctx.exception))

    async def test_sqlite_initialization(self) -> None:
        """Verify sqlite database structure and table/index creation."""
        conn = self.sqlite_adapter._get_connection()
        try:
            cursor = conn.cursor()
            # Verify table columns
            cursor.execute("PRAGMA table_info(checkpoints)")
            cols = {row["name"]: row["type"] for row in cursor.fetchall()}
            self.assertIn("checkpoint_id", cols)
            self.assertIn("last_processed_primary_key", cols)
            self.assertIn("status", cols)
            
            # Verify indexes
            cursor.execute("SELECT name FROM sqlite_master WHERE type='index'")
            indexes = [row["name"] for row in cursor.fetchall()]
            self.assertTrue(any("idx_checkpoints_proj_mig" in idx for idx in indexes))
            self.assertTrue(any("idx_checkpoints_status" in idx for idx in indexes))
        finally:
            conn.close()

    async def test_file_backend(self) -> None:
        """Verify basic writing and loading behavior of FileCheckpointStorageAdapter."""
        record = self.sample_record
        record.checksum = record.calculate_checksum()
        
        # Write
        self.assertTrue(await self.file_adapter.write(record))
        
        # File must exist
        expected_path = self.file_adapter._get_file_path(record.project_id, record.checkpoint_id)
        self.assertTrue(os.path.exists(expected_path))
        
        # Read
        loaded = await self.file_adapter.read(record.checkpoint_id)
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded.checkpoint_id, record.checkpoint_id)
        self.assertEqual(loaded.last_processed_primary_key, record.last_processed_primary_key)
        self.assertEqual(loaded.status, CheckpointStatus.COMMITTED)

    def test_factory_creation(self) -> None:
        """Verify the CheckpointStorageFactory creates proper backends based on config type."""
        # 1. SQLite creation via dictionary config
        config_db = {"type": "sqlite", "db_path": self.db_path}
        adapter_db = CheckpointStorageFactory.create(config_db)
        self.assertIsInstance(adapter_db, SQLiteCheckpointStorageAdapter)
        
        # 2. File creation via dictionary config
        config_file = {"type": "file", "workspace_dir": self.test_dir}
        adapter_file = CheckpointStorageFactory.create(config_file)
        self.assertIsInstance(adapter_file, FileCheckpointStorageAdapter)
        
        # 3. Object-based config simulation (MigrationConfig style)
        class MockConfig:
            workspace_dir = self.test_dir
            checkpoint_storage_type = "sqlite"
        adapter_obj = CheckpointStorageFactory.create(MockConfig())
        self.assertIsInstance(adapter_obj, SQLiteCheckpointStorageAdapter)

    async def test_resume(self) -> None:
        """Verify resume retrieves correct table cursor checkpoints."""
        rec1 = CheckpointRecord(
            checkpoint_id="c-001", project_id="p-1", migration_id="m-1",
            workflow_state=WorkflowState.PRODUCTION_MIGRATION, table_name="users",
            batch_number=1, last_processed_primary_key={"id": 100}, status=CheckpointStatus.PENDING
        )
        rec1.checksum = rec1.calculate_checksum()
        
        rec2 = CheckpointRecord(
            checkpoint_id="c-002", project_id="p-1", migration_id="m-1",
            workflow_state=WorkflowState.PRODUCTION_MIGRATION, table_name="users",
            batch_number=2, last_processed_primary_key={"id": 200}, status=CheckpointStatus.PENDING
        )
        rec2.checksum = rec2.calculate_checksum()
        
        await self.sqlite_mgr.save_progress(rec1)
        # Add tiny delay to ensure timestamps increments
        await asyncio.sleep(0.01)
        await self.sqlite_mgr.save_progress(rec2)
        
        resumed = await self.sqlite_mgr.resume("p-1", "m-1", "users")
        self.assertIsNotNone(resumed)
        self.assertEqual(resumed.checkpoint_id, "c-002")
        self.assertEqual(resumed.last_processed_primary_key, {"id": 200})

    async def test_purge(self) -> None:
        """Verify purge safety rules and retention windows."""
        # Save checkpoints with different statuses
        records = [
            CheckpointRecord("chk-pending", "proj-p", "mig-m", WorkflowState.PRODUCTION_MIGRATION, "table1", 1, status=CheckpointStatus.PENDING),
            CheckpointRecord("chk-committed", "proj-p", "mig-m", WorkflowState.PRODUCTION_MIGRATION, "table1", 2, status=CheckpointStatus.COMMITTED),
            CheckpointRecord("chk-completed", "proj-p", "mig-m", WorkflowState.PRODUCTION_MIGRATION, "table1", 3, status=CheckpointStatus.COMPLETED),
            CheckpointRecord("chk-failed", "proj-p", "mig-m", WorkflowState.PRODUCTION_MIGRATION, "table1", 4, status=CheckpointStatus.FAILED),
        ]
        
        for r in records:
            r.checksum = r.calculate_checksum()
            await self.sqlite_mgr.save_progress(r)
            
        # Purge. Only FAILED and COMPLETED should be purged
        purged = await self.sqlite_mgr.purge("proj-p", "mig-m")
        self.assertEqual(purged, 2)
        
        # Verify COMMITTED checkpoints still exist (PENDING gets upgraded to COMMITTED on save)
        all_chks = await self.sqlite_mgr.list_checkpoints("proj-p", "mig-m")
        self.assertEqual(len(all_chks), 2)
        statuses = {c.status for c in all_chks}
        self.assertEqual(len(statuses), 1)
        self.assertIn(CheckpointStatus.COMMITTED, statuses)

    async def test_mark_completed_and_failed(self) -> None:
        """Verify mark_completed and mark_failed status updates."""
        # 1. Mark completed
        comp_rec = await self.sqlite_mgr.mark_completed("proj-abc", "mig-1", "users", "worker-1")
        self.assertEqual(comp_rec.status, CheckpointStatus.COMPLETED)
        self.assertEqual(comp_rec.batch_number, -1)
        
        loaded = await self.sqlite_mgr.load_progress(comp_rec.checkpoint_id)
        self.assertEqual(loaded.status, CheckpointStatus.COMPLETED)
        
        # 2. Mark failed
        fail_success = await self.sqlite_mgr.mark_failed(comp_rec.checkpoint_id, "Resource lock error")
        self.assertTrue(fail_success)
        
        loaded_failed = await self.sqlite_mgr.load_progress(comp_rec.checkpoint_id)
        self.assertEqual(loaded_failed.status, CheckpointStatus.FAILED)
        self.assertEqual(loaded_failed.metrics.get("error_details"), "Resource lock error")

    async def test_list_checkpoints(self) -> None:
        """Verify list_checkpoints retrieves chronological list."""
        rec1 = CheckpointRecord("c-01", "p-1", "m-1", WorkflowState.PRODUCTION_MIGRATION, "users", 1, status=CheckpointStatus.PENDING)
        rec2 = CheckpointRecord("c-02", "p-1", "m-1", WorkflowState.PRODUCTION_MIGRATION, "users", 2, status=CheckpointStatus.PENDING)
        
        rec1.checksum = rec1.calculate_checksum()
        rec2.checksum = rec2.calculate_checksum()
        
        await self.sqlite_mgr.save_progress(rec1)
        await asyncio.sleep(0.01)
        await self.sqlite_mgr.save_progress(rec2)
        
        res = await self.sqlite_mgr.list_checkpoints("p-1", "m-1")
        self.assertEqual(len(res), 2)
        self.assertEqual(res[0].checkpoint_id, "c-01")
        self.assertEqual(res[1].checkpoint_id, "c-02")

    async def test_concurrent_checkpoint_writes(self) -> None:
        """Verify that writing multiple checkpoints concurrently does not cause SQLite lockups."""
        tasks = []
        for i in range(50):
            rec = CheckpointRecord(
                checkpoint_id=f"chk-concurrent-{i}",
                project_id="proj-concurrent",
                migration_id="mig-concurrent",
                workflow_state=WorkflowState.PRODUCTION_MIGRATION,
                table_name="orders",
                batch_number=i,
                worker_id="thread-pool",
                status=CheckpointStatus.PENDING
            )
            rec.checksum = rec.calculate_checksum()
            tasks.append(self.sqlite_mgr.save_progress(rec))
            
        results = await asyncio.gather(*tasks)
        self.assertTrue(all(results))
        
        all_chks = await self.sqlite_mgr.list_checkpoints("proj-concurrent", "mig-concurrent")
        self.assertEqual(len(all_chks), 50)

    async def test_10000_checkpoint_insert_stress_test(self) -> None:
        """Verify performance and memory behavior when inserting 10,000 checkpoints."""
        # Using a single SQLite transaction manually for super-fast bulk insert verification
        conn = self.sqlite_adapter._get_connection()
        try:
            cursor = conn.cursor()
            # Insert 10,000 checkpoints
            import time
            start = time.monotonic()
            
            project_id = "proj-stress"
            migration_id = "mig-stress"
            
            # Prefab records
            records_data = []
            for i in range(10000):
                records_data.append((
                    f"stress-{i}", project_id, migration_id, WorkflowState.PRODUCTION_MIGRATION.value,
                    "orders", i, "worker-stress", None, i * 10, 0, 0, 0,
                    "{}", "{}", "dummychecksum", "2026-07-03T12:00:00Z", "2026-07-03T12:00:00Z", "COMMITTED"
                ))
                
            cursor.executemany("""
                INSERT INTO checkpoints (
                    checkpoint_id, project_id, migration_id, workflow_state,
                    table_name, batch_number, worker_id, last_processed_primary_key,
                    rows_processed, rows_failed, rows_skipped, retry_count,
                    adapter_state, metrics, checksum, created_at, updated_at, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, records_data)
            conn.commit()
            
            elapsed = time.monotonic() - start
            logger.info("Inserted 10,000 checkpoints in %.3fs", elapsed)
            # Ensure it completes within reasonable limit (< 1 second usually for bulk transactions)
            self.assertLess(elapsed, 3.0)
            
            # Read back count
            cursor.execute("SELECT COUNT(*) FROM checkpoints WHERE project_id = ?", (project_id,))
            self.assertEqual(cursor.fetchone()[0], 10000)
            
        finally:
            conn.close()

    async def test_recovery_after_interrupted_write(self) -> None:
        """Verify that system recovers from and handles transaction write interrupts."""
        # Simulate db crash during write by supplying corrupt/invalid connection parameters
        bad_adapter = SQLiteCheckpointStorageAdapter(os.path.join(self.test_dir, "nonexistent_dir", "db.db"))
        # We don't initialize it, writing to it will raise an operational error
        
        bad_mgr = CheckpointManager(bad_adapter)
        
        # Writing should return False (caught gracefully) rather than crashing the pipeline
        success = await bad_mgr.save_progress(self.sample_record)
        self.assertFalse(success)

    async def test_file_sqlite_parity(self) -> None:
        """Verify state and schema output parity between local File and SQLite storage backends."""
        record = self.sample_record
        record.checksum = record.calculate_checksum()
        
        # Write to both
        await self.sqlite_mgr.save_progress(record)
        await self.file_mgr.save_progress(record)
        
        # Load from both
        sqlite_loaded = await self.sqlite_mgr.load_progress(record.checkpoint_id)
        file_loaded = await self.file_mgr.load_progress(record.checkpoint_id)
        
        self.assertIsNotNone(sqlite_loaded)
        self.assertIsNotNone(file_loaded)
        
        # Verify parity
        self.assertEqual(sqlite_loaded.checkpoint_id, file_loaded.checkpoint_id)
        self.assertEqual(sqlite_loaded.project_id, file_loaded.project_id)
        self.assertEqual(sqlite_loaded.migration_id, file_loaded.migration_id)
        self.assertEqual(sqlite_loaded.table_name, file_loaded.table_name)
        self.assertEqual(sqlite_loaded.batch_number, file_loaded.batch_number)
        self.assertEqual(sqlite_loaded.last_processed_primary_key, file_loaded.last_processed_primary_key)
        self.assertEqual(sqlite_loaded.rows_processed, file_loaded.rows_processed)
        self.assertEqual(sqlite_loaded.checksum, file_loaded.checksum)
        self.assertEqual(sqlite_loaded.status, file_loaded.status)
