import unittest
from akaal.gateway.engine_gateway import EngineGateway
from tests.conftest import require_oracle

class TestCleanSessionGovernanceAndLifecycle(unittest.TestCase):

    def setUp(self):
        self.gateway = EngineGateway()
        self.mig_id = "mig-clean-p08-test"
        self.proj_id = "proj-clean-p08-test"

    def test_clean_session_approval_queue_is_empty(self):
        # 1. Governance Centre immediately after startup: approvals = 0
        queue_res = self.gateway.invoke("get_approval_queue", {})
        self.assertEqual(queue_res.get("status"), "success")
        self.assertEqual(len(queue_res.get("approvals", [])), 0, "Clean startup must have 0 approvals")

    def test_canonical_lifecycle_and_fail_closed_governance(self):
        require_oracle("localhost", 1521)
        # 2. DISCOVER & PREFLIGHT

        preflight_res = self.gateway.invoke("run_preflight", {
            "source_engine": "Oracle 19c",
            "target_engine": "PostgreSQL 16",
            "source_db": "FREE",
            "source_user": "SYSTEM"
        })
        snap_id = preflight_res.get("discovery_snapshot_id")
        self.assertIsNotNone(snap_id)

        # Truthful estimated_duration when baseline throughput is unmeasured
        self.assertIsNone(preflight_res.get("estimated_duration"), "Unmeasured duration must return None, not fake 14m")

        # 3. PLAN (Single generate_plan execution)
        plan_res = self.gateway.invoke("generate_plan", {
            "migration_id": self.mig_id,
            "discovery_snapshot_id": snap_id,
            "parallelism": 8
        })
        plan_id = plan_res.get("execution_plan_id")
        self.assertIsNotNone(plan_id)

        # 4. REGISTER CANONICAL MIGRATION
        create_res = self.gateway.invoke("create_migration", {
            "project_id": self.proj_id,
            "migration_id": self.mig_id,
            "migration_name": "Clean P0.8 Verification Pipeline",
            "discovery_snapshot_id": snap_id,
            "execution_plan_id": plan_id
        })
        self.assertIn(create_res.get("status"), ["configured", "created"])

        # 5. REQUEST APPROVAL (Gate status becomes PENDING)
        app_res = self.gateway.invoke("request_approval", {
            "migration_id": self.mig_id,
            "discovery_snapshot_id": snap_id,
            "approver": "Aalok (Lead DBA)"
        })
        app_id = app_res.get("approval_reference_id")
        self.assertEqual(app_res.get("status"), "pending")

        # 6. Verify Runtime Snapshot state returns PENDING approval status
        snap_before = self.gateway.invoke("get_runtime_snapshot", {"migration_id": self.mig_id})
        self.assertEqual(snap_before.get("approval_status"), "PENDING")

        # 7. Premature start_transport MUST BE REJECTED
        premature = self.gateway.invoke("start_transport", {"migration_id": self.mig_id})
        self.assertIn(premature.get("status"), ["failed", "error"])
        self.assertEqual(premature.get("error_code"), "APPROVAL_REQUIRED")

        # 8. HUMAN OPERATOR EXPLICITLY APPROVES IN GOVERNANCE CENTRE
        decision = self.gateway.invoke("submit_approval_decision", {
            "approval_id": app_id,
            "migration_id": self.mig_id,
            "decision": "approved",
            "approver": "Aalok (Lead DBA)",
            "reason": "Topological DAG plan and custody validated."
        })
        self.assertEqual(decision.get("status"), "approved")

        # 9. Verify Runtime Snapshot state now returns APPROVED
        snap_after = self.gateway.invoke("get_runtime_snapshot", {"migration_id": self.mig_id})
        self.assertEqual(snap_after.get("approval_status"), "APPROVED")

        # 10. Authorized start_transport AFTER APPROVAL SUCCEEDS
        authorized = self.gateway.invoke("start_transport", {"migration_id": self.mig_id})
        self.assertIn(authorized.get("status"), ["success", "accepted", "transport_running"])

if __name__ == "__main__":
    unittest.main()
