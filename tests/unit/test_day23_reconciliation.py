import unittest
from akaal.gateway.engine_gateway import EngineGateway

class TestDay23ControlPlaneReconciliation(unittest.TestCase):

    def setUp(self):
        self.gateway = EngineGateway()
        self.mig_id = "mig-test-day23"
        self.proj_id = "proj-test-day23"

        # 1. Create Migration
        self.gateway.invoke("create_migration", {
            "project_id": self.proj_id,
            "migration_id": self.mig_id,
            "migration_name": "Day 23 Verification Pipeline",
            "source_host": "localhost",
            "source_port": 1521,
            "source_service": "instance2_pdb",
            "source_user": "SYSTEM",
            "source_pass": "ora_pass",
            "target_host": "localhost",
            "target_port": 5433,
            "target_db": "pg_analytics",
            "target_user": "p",
            "target_pass": "pg_pass",
        })

    def test_governance_fail_closed_and_start_transport_reconciliation(self):
        # 2. Request Approval (Gate status becomes PENDING)
        app_res = self.gateway.invoke("request_approval", {
            "migration_id": self.mig_id,
            "approver": "Aalok (Lead DBA)"
        })
        app_id = app_res["approval_reference_id"]
        self.assertEqual(app_res["status"], "pending")

        # 3. Premature start_transport MUST return status: failed / error with APPROVAL_REQUIRED
        premature_res = self.gateway.invoke("start_transport", {"migration_id": self.mig_id})
        self.assertIn(premature_res.get("status"), ["failed", "error"])
        self.assertEqual(premature_res.get("error_code"), "APPROVAL_REQUIRED")

        # 4. Submit Approval Decision (Approved)
        decision_res = self.gateway.invoke("submit_approval_decision", {
            "approval_id": app_id,
            "migration_id": self.mig_id,
            "decision": "approved",
            "approver": "Aalok (Lead DBA)",
            "reason": "Execution plan sha256 validated."
        })
        self.assertEqual(decision_res["status"], "approved")

        # 5. Authorized start_transport AFTER APPROVAL MUST succeed
        authorized_res = self.gateway.invoke("start_transport", {"migration_id": self.mig_id})
        self.assertIn(authorized_res.get("status"), ["success", "accepted", "transport_running"])

        # 6. Verify Runtime Snapshot state transitions to RUNNING / COMPLETED & exposes PID
        snapshot = self.gateway.invoke("get_runtime_snapshot", {"migration_id": self.mig_id})
        self.assertIn(snapshot.get("health_status"), ["READY", "HEALTHY"])
        self.assertIsNotNone(snapshot.get("pid"))

    def test_governance_queue_reconciliation_no_seeded_fake_data(self):
        # Verify get_approval_queue returns dynamic approvals from CentralStateStore
        queue_res = self.gateway.invoke("get_approval_queue", {})
        self.assertEqual(queue_res.get("status"), "success")
        self.assertIsInstance(queue_res.get("approvals"), list)

    def test_snapshot_returns_neutral_idle_telemetry_before_start(self):
        fresh_mig_id = "mig-fresh-idle"
        self.gateway.invoke("create_migration", {
            "project_id": self.proj_id,
            "migration_id": fresh_mig_id,
            "migration_name": "Fresh Pipeline",
            "source_host": "localhost",
            "source_port": 1521,
            "source_service": "instance2_pdb",
            "source_user": "SYSTEM",
            "source_pass": "ora_pass",
            "target_host": "localhost",
            "target_port": 5433,
            "target_db": "pg_analytics",
            "target_user": "p",
            "target_pass": "pg_pass",
        })
        snap = self.gateway.invoke("get_runtime_snapshot", {"migration_id": fresh_mig_id})
        self.assertEqual(snap.get("current_stage"), "ready")
        self.assertIsNone(snap.get("rows_transferred"))
        self.assertIsNone(snap.get("progress_percent"))
        self.assertEqual(snap.get("active_workers"), 0)

    def test_p0_7_telemetry_provenance_and_zero_synthetic_workers(self):
        mig_id = "mig-p07-telemetry"
        self.gateway.invoke("create_migration", {
            "project_id": self.proj_id,
            "migration_id": mig_id,
            "migration_name": "P0.7 Telemetry Test",
            "source_host": "localhost",
            "source_port": 1521,
            "source_service": "instance2_pdb",
            "source_user": "SYSTEM",
            "source_pass": "ora_pass",
            "target_host": "localhost",
            "target_port": 5433,
            "target_db": "pg_analytics",
            "target_user": "p",
            "target_pass": "pg_pass",
        })
        # Request & Approve
        app_res = self.gateway.invoke("request_approval", {"migration_id": mig_id, "approver": "DBA"})
        app_id = app_res["approval_reference_id"]
        self.gateway.invoke("submit_approval_decision", {
            "approval_id": app_id,
            "migration_id": mig_id,
            "decision": "approved",
            "approver": "DBA"
        })
        # Execute Transport
        start_res = self.gateway.invoke("start_transport", {"migration_id": mig_id})
        self.assertIn(start_res.get("status"), ["success", "accepted", "transport_running"])

        self.gateway.state_store.update_progress(mig_id, {
            "rows_migrated": 5,
            "percentage": 100.0,
            "status": "COMPLETED",
            "active_workers": 0,
            "rows_per_sec": 50.0,
            "throughput_mbps": 10.5
        })
        self.gateway.state_store.set_state(f"{mig_id}_status", {"status": "COMPLETED"}, category="runtime")

        # Snapshot after completion
        snap = self.gateway.invoke("get_runtime_snapshot", {"migration_id": mig_id})
        
        # A. active_workers must be 0 upon completion (No RUNNING=4 fallback left!)
        self.assertEqual(snap.get("active_workers"), 0)

        # B. rows_transferred equals actual target writes (5 rows)
        self.assertEqual(snap.get("rows_transferred"), 5)

        # C. progress_percent reaches 100 on completion
        self.assertEqual(snap.get("progress_percent"), 100.0)

        # D. rows_per_sec is calculated from actual elapsed time
        self.assertIsNotNone(snap.get("rows_per_sec"))
        self.assertGreater(snap.get("rows_per_sec"), 0)

        # E. throughput_mbps is calculated from byte payload
        self.assertIsNotNone(snap.get("throughput_mbps"))
        self.assertGreaterEqual(snap.get("throughput_mbps"), 0.0)

        # F. Unavailable metrics (bandwidth, ring_buffer) remain None/unexposed
        self.assertIsNone(snap.get("bandwidth"))
        self.assertIsNone(snap.get("ring_buffer"))

if __name__ == "__main__":
    unittest.main()
