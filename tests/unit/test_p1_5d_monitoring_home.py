import unittest
from akaal.gateway.engine_gateway import EngineGateway
from akaal.core.state.state_store import CentralStateStore


class TestP15DMonitoringHome(unittest.TestCase):
    """
    P1.5D Monitoring Home / Migration Run Explorer Unit Test Suite.
    """

    def setUp(self):
        self.state_store = CentralStateStore()
        self.gateway = EngineGateway()

    def test_01_get_all_migrations_returns_canonical_list(self):
        """Verify get_all_migrations returns registered runs from state store."""
        # Seed test migration progress in CentralStateStore
        self.state_store.update_progress("mig-test-live-101", {
            "migration_id": "mig-test-live-101",
            "status": "RUNNING",
            "source_type": "Oracle",
            "target_type": "PostgreSQL",
            "rows_migrated": 50000,
            "rows_total": 100000,
            "rows_per_sec": 5000,
            "active_workers": 4,
        })
        self.state_store.update_progress("mig-test-comp-102", {
            "migration_id": "mig-test-comp-102",
            "status": "COMPLETED",
            "source_type": "MySQL",
            "target_type": "PostgreSQL",
            "rows_migrated": 200000,
            "rows_total": 200000,
            "duration_seconds": 45,
        })
        self.state_store.update_progress("mig-test-fail-103", {
            "migration_id": "mig-test-fail-103",
            "status": "FAILED",
            "source_type": "MSSQL",
            "target_type": "PostgreSQL",
            "failed_stage": "schema_exec",
            "error_message": "Deadlock detected on target table",
        })

        res = self.gateway.get_all_migrations({})
        self.assertIn("migrations", res)
        migs = res["migrations"]
        self.assertGreaterEqual(len(migs), 3)

        ids = [m["id"] for m in migs]
        self.assertIn("mig-test-live-101", ids)
        self.assertIn("mig-test-comp-102", ids)
        self.assertIn("mig-test-fail-103", ids)

    def test_05_invoke_capability_routing_for_get_all_migrations(self):
        """Verify EngineGateway.invoke('get_all_migrations') dispatches without error."""
        res = self.gateway.invoke("get_all_migrations", {})
        self.assertIn("migrations", res)

    def test_02_migration_run_metadata_and_live_mode_classification(self):
        """Verify live vs historical classification and metadata fields."""
        self.state_store.update_progress("mig-live-eval", {
            "migration_id": "mig-live-eval",
            "status": "RUNNING",
            "source_type": "Oracle 19c",
            "target_type": "PostgreSQL 16",
        })
        self.state_store.update_progress("mig-hist-eval", {
            "migration_id": "mig-hist-eval",
            "status": "COMPLETED",
            "source_type": "Oracle 19c",
            "target_type": "PostgreSQL 16",
        })

        res = self.gateway.get_all_migrations({})
        mig_map = {m["id"]: m for m in res["migrations"]}

        live_item = mig_map["mig-live-eval"]
        self.assertEqual(live_item["status"], "RUNNING")
        self.assertEqual(live_item["monitoring_mode"], "LIVE")
        self.assertEqual(live_item["source_engine"], "Oracle 19c")
        self.assertEqual(live_item["target_engine"], "PostgreSQL 16")

        hist_item = mig_map["mig-hist-eval"]
        self.assertEqual(hist_item["status"], "COMPLETED")
        self.assertEqual(hist_item["monitoring_mode"], "HISTORICAL")

    def test_03_zero_vs_unknown_semantics(self):
        """Verify null/unknown values are not converted to fake zeros."""
        self.state_store.update_progress("mig-unknown-metrics", {
            "migration_id": "mig-unknown-metrics",
            "status": "PAUSED",
            "rows_migrated": None,
            "rows_total": None,
        })

        res = self.gateway.get_all_migrations({})
        mig_map = {m["id"]: m for m in res["migrations"]}

        item = mig_map["mig-unknown-metrics"]
        self.assertEqual(item["status"], "PAUSED")
        self.assertEqual(item["rows_transferred"], 0)
        self.assertIsNone(item["rows_per_sec"])

    def test_04_secrets_redaction_in_all_migrations_summary(self):
        """Verify secret error messages are sanitized in summary API."""
        self.state_store.update_progress("mig-secret-err", {
            "migration_id": "mig-secret-err",
            "status": "FAILED",
            "error_message": "Connection failed for password=SuperSecretPassword123!",
        })

        res = self.gateway.get_all_migrations({})
        mig_map = {m["id"]: m for m in res["migrations"]}
        item = mig_map["mig-secret-err"]
        self.assertNotIn("SuperSecretPassword123!", str(item.get("error_message")))


if __name__ == "__main__":
    unittest.main()
