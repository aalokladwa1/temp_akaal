"""
AKAAL P1.3.2 Unit Test Suite — Historical Migration Monitoring & Restart Reconstruction
========================================================================================
Verification of daemon restart state reconstruction, COMPLETED / FAILED / TERMINATED
historical snapshot retrieval, multi-migration isolation, and live vs historical mode semantics.
"""

import unittest
import os
import uuid
import datetime
from unittest.mock import MagicMock

from akaal.gateway.engine_gateway import EngineGateway
from akaal.core.state.state_store import CentralStateStore


class TestP132HistoricalMonitoring(unittest.TestCase):
    """P1.3.2 Comprehensive Test Suite for Historical Monitoring & Daemon Restart."""

    def setUp(self):
        self.gateway = EngineGateway()
        self.mig_a = f"mig-hist-a-{uuid.uuid4().hex[:6]}"
        self.mig_b = f"mig-hist-b-{uuid.uuid4().hex[:6]}"

    def test_01_migration_specific_monitoring_isolation(self):
        """Verify monitoring snapshots for distinct migrations remain strictly isolated."""
        self.gateway.state_store.update_progress(self.mig_a, {
            "status": "RUNNING",
            "rows_migrated": 10000,
            "rows_total": 50000,
        })
        self.gateway.state_store.update_progress(self.mig_b, {
            "status": "COMPLETED",
            "rows_migrated": 50000,
            "rows_total": 50000,
        })

        snap_a = self.gateway.get_monitoring_snapshot({"migration_id": self.mig_a})
        snap_b = self.gateway.get_monitoring_snapshot({"migration_id": self.mig_b})

        self.assertEqual(snap_a["monitoring_mode"], "LIVE")
        self.assertEqual(snap_a["progress"]["rows_transferred"], 10000)

        self.assertEqual(snap_b["monitoring_mode"], "HISTORICAL")
        self.assertEqual(snap_b["progress"]["rows_transferred"], 50000)

    def test_02_completed_historical_snapshot_semantics(self):
        """Verify completed migration reports HISTORICAL mode and zeroes live-only metrics."""
        self.gateway.state_store.update_progress(self.mig_a, {
            "status": "COMPLETED",
            "rows_migrated": 200000,
            "rows_total": 200000,
            "completed_tables": 10,
            "total_tables": 10,
            "duration_seconds": 15.4,
            "average_rows_per_sec": 12987,
        })

        snap = self.gateway.get_monitoring_snapshot({"migration_id": self.mig_a})

        self.assertEqual(snap["monitoring_mode"], "HISTORICAL")
        self.assertEqual(snap["runtime"]["status"], "COMPLETED")
        self.assertEqual(snap["progress"]["rows_transferred"], 200000)
        self.assertEqual(snap["workers"]["active_workers"], 0)
        self.assertIsNone(snap["throughput"]["eta_seconds"])
        self.assertIsNone(snap["runtime"]["pid"])
        self.assertIsNone(snap["progress"]["current_table"])

    def test_03_failed_historical_snapshot_semantics(self):
        """Verify failed migration retains error information and failed stage truthfully."""
        self.gateway.state_store.update_progress(self.mig_a, {
            "status": "FAILED",
            "rows_migrated": 15000,
            "rows_total": 100000,
            "failed_stage": "data_migration",
            "failed_object": "ORDERS_TABLE",
            "error_message": "Network socket timeout to target database with pwd=SecretPwd999",
        })

        snap = self.gateway.get_monitoring_snapshot({"migration_id": self.mig_a})

        self.assertEqual(snap["monitoring_mode"], "HISTORICAL")
        self.assertEqual(snap["runtime"]["status"], "FAILED")
        self.assertEqual(snap["errors"]["failed_stage"], "data_migration")
        self.assertEqual(snap["errors"]["failed_object"], "ORDERS_TABLE")
        self.assertNotIn("SecretPwd999", snap["errors"]["error_message"])

    def test_04_daemon_restart_historical_reconstruction(self):
        """Verify durable state in SQLite WAL state.db reconstructs snapshot after daemon restart."""
        # 1. Update progress in initial gateway instance
        self.gateway.state_store.update_progress(self.mig_a, {
            "status": "COMPLETED",
            "rows_migrated": 88000,
            "rows_total": 88000,
            "completed_tables": 4,
            "total_tables": 4,
            "duration_seconds": 8.2,
        })

        # 2. Simulate daemon restart: create new EngineGateway and clear in-memory state dictionary
        new_gateway = EngineGateway()
        new_gateway.state_store._state["progress"].pop(self.mig_a, None)

        # 3. Query historical snapshot from new gateway instance
        snap = new_gateway.get_monitoring_snapshot({"migration_id": self.mig_a})

        self.assertEqual(snap["monitoring_mode"], "HISTORICAL")
        self.assertEqual(snap["runtime"]["status"], "COMPLETED")
        self.assertEqual(snap["progress"]["rows_transferred"], 88000)
        self.assertEqual(snap["progress"]["completed_tables"], 4)

    def test_05_terminated_migration_no_progress_after_termination(self):
        """Verify terminated migration sets active workers to 0 and stops progress."""
        self.gateway.state_store.update_progress(self.mig_a, {
            "status": "TERMINATED",
            "rows_migrated": 32000,
            "rows_total": 100000,
        })

        snap = self.gateway.get_monitoring_snapshot({"migration_id": self.mig_a})

        self.assertEqual(snap["monitoring_mode"], "HISTORICAL")
        self.assertEqual(snap["runtime"]["status"], "TERMINATED")
        self.assertEqual(snap["workers"]["active_workers"], 0)
        self.assertIsNone(snap["throughput"]["eta_seconds"])


if __name__ == "__main__":
    unittest.main()
