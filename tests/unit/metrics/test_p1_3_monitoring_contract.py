"""
AKAAL P1.3 Unit Test Suite — Canonical Monitoring Data Contract & Metric Exposure
===================================================================================
Comprehensive verification of get_monitoring_snapshot DTO schema versioning,
12 metric domains, multiprocess worker telemetry aggregation, secret redaction,
and null vs zero metric distinction.
"""

import unittest
import uuid
import datetime
from unittest.mock import MagicMock

from akaal.gateway.engine_gateway import EngineGateway
from akaal.core.state.state_store import CentralStateStore
from akaal.metrics.registry import MetricsRegistry
from akaal.replication.scheduling.parallel_scheduler import ParallelReplicationScheduler
from akaal.engine.spec import TransportPartition, PartitionStrategy


class TestP13MonitoringContract(unittest.TestCase):
    """P1.3 Comprehensive Test Suite for Canonical Live Monitoring Contract."""

    def setUp(self):
        self.gateway = EngineGateway()
        self.mig_id = f"mig-test-p13-{uuid.uuid4().hex[:6]}"

    def test_01_get_monitoring_snapshot_schema_and_version(self):
        """Verify get_monitoring_snapshot returns valid DTO with schema_version 1.0."""
        snap = self.gateway.get_monitoring_snapshot({"migration_id": self.mig_id})

        self.assertEqual(snap["schema_version"], "1.0")
        self.assertEqual(snap["migration_id"], self.mig_id)
        self.assertIn("captured_at", snap)
        self.assertIn("runtime", snap)
        self.assertIn("progress", snap)
        self.assertIn("throughput", snap)
        self.assertIn("workers", snap)
        self.assertIn("batching", snap)
        self.assertIn("connections", snap)
        self.assertIn("checkpoints", snap)
        self.assertIn("retries", snap)
        self.assertIn("backpressure", snap)
        self.assertIn("resources", snap)
        self.assertIn("partitions", snap)
        self.assertIn("lob", snap)
        self.assertIn("validation", snap)
        self.assertIn("cdc", snap)
        self.assertIn("errors", snap)

    def test_02_capability_registry_dispatch(self):
        """Verify get_monitoring_snapshot is registered and executable via EngineGateway.invoke."""
        result = self.gateway.invoke("get_monitoring_snapshot", {"migration_id": self.mig_id})
        self.assertEqual(result["schema_version"], "1.0")
        self.assertEqual(result["migration_id"], self.mig_id)

    def test_03_null_vs_zero_semantics(self):
        """Verify unmeasured metrics return null/None and do NOT fabricate false zeros."""
        snap = self.gateway.get_monitoring_snapshot({"migration_id": self.mig_id})

        # In initial state before execution, rows_transferred & rows_total are None
        self.assertIsNone(snap["progress"]["rows_transferred"])
        self.assertIsNone(snap["progress"]["rows_total"])
        self.assertIsNone(snap["throughput"]["rows_per_sec"])

        # Real zero count like retry_count is 0, not None
        self.assertEqual(snap["retries"]["retry_count"], 0)

    def test_04_secret_redaction_in_errors_and_logs(self):
        """Verify plaintext secrets in error messages are redacted automatically."""
        # Inject error message with password into CentralStateStore
        self.gateway.state_store.update_progress(self.mig_id, {
            "status": "FAILED",
            "error_message": "Connection to target DB failed with password=SecretPassword123!",
            "failed_stage": "transport",
        })

        snap = self.gateway.get_monitoring_snapshot({"migration_id": self.mig_id})
        err_msg = snap["errors"]["error_message"]

        self.assertIsNotNone(err_msg)
        self.assertNotIn("SecretPassword123", err_msg)
        self.assertEqual(err_msg, "[REDACTED]")

    def test_05_cdc_inactive_future_phase_classification(self):
        """Verify CDC domain correctly reports FUTURE_PHASE_INACTIVE and does NOT fabricate fake events."""
        snap = self.gateway.get_monitoring_snapshot({"migration_id": self.mig_id})

        self.assertEqual(snap["cdc"]["cdc_status"], "FUTURE_PHASE_INACTIVE")
        self.assertIsNone(snap["cdc"]["cdc_lag_ms"])
        self.assertIsNone(snap["cdc"]["cdc_events_processed"])

    def test_06_multiprocess_worker_metrics_parent_visibility(self):
        """Verify parallel worker process updates to CentralStateStore are visible in parent monitoring snapshot."""
        # Simulate worker updating CentralStateStore progress
        self.gateway.state_store.update_progress(self.mig_id, {
            "status": "RUNNING",
            "rows_migrated": 25000,
            "rows_total": 100000,
            "throughput_mbps": 45.2,
            "rows_per_sec": 12500,
            "active_workers": 4,
            "completed_tables": 2,
            "total_tables": 10,
        })

        snap = self.gateway.get_monitoring_snapshot({"migration_id": self.mig_id})

        self.assertEqual(snap["progress"]["rows_transferred"], 25000)
        self.assertEqual(snap["progress"]["rows_total"], 100000)
        self.assertEqual(snap["throughput"]["throughput_mbps"], 45.2)
        self.assertEqual(snap["throughput"]["rows_per_sec"], 12500)
        self.assertEqual(snap["workers"]["active_workers"], 4)

    def test_07_mission_control_compatibility(self):
        """Verify existing get_runtime_snapshot API remains 100% backward compatible for Mission Control."""
        runtime_snap = self.gateway.get_runtime_snapshot({"migration_id": self.mig_id})

        self.assertIn("health_status", runtime_snap)
        self.assertIn("approval_status", runtime_snap)
        self.assertIn("rows_transferred", runtime_snap)
        self.assertIn("rows_total", runtime_snap)
        self.assertIn("progress_percent", runtime_snap)
        self.assertIn("available_actions", runtime_snap)


if __name__ == "__main__":
    unittest.main()
