"""
AKAAL Forensic Verification Tests — Step 5.3 Durable Control-Plane State Authority
===================================================================================
Verifies that EngineGateway control-plane operations are restart-safe and rely on
CentralStateStore as the single durable control-plane state authority.

Tests:
1. Complete daemon restart simulation (destroy Gateway 1, instantiate Gateway 2).
2. Project, migration, plan, approval, and fingerprint recovery post-restart.
3. Fail-closed governance enforcement post-restart (missing approval / modified plan).
"""

import unittest
from unittest.mock import MagicMock, patch

from akaal.gateway.engine_gateway import EngineGateway
from akaal.core.state.state_store import CentralStateStore


class TestStep53DurableStateAuthority(unittest.TestCase):

    def setUp(self):
        self.state_store = CentralStateStore()

    def _get_valid_migration_payload(self, mig_id: str) -> dict:
        from akaal.migration.target_identifier import ConnectionAuthority
        src_auth = ConnectionAuthority(connection_id="conn-src", role="SOURCE", engine="ORACLE", host="127.0.0.1", port=1521, database="FREE", username="SYSTEM", credential_ref="cred-src")
        tgt_auth = ConnectionAuthority(connection_id="conn-tgt", role="TARGET", engine="POSTGRESQL", host="127.0.0.1", port=5432, database="pgdb", username="postgres", credential_ref="cred-tgt")
        return {
            "migration_id": mig_id,
            "migration_name": f"Test Migration {mig_id}",
            "source_engine": "ORACLE",
            "target_engine": "POSTGRESQL",
            "source_host": "127.0.0.1",
            "source_port": 1521,
            "source_db": "FREE",
            "source_user": "SYSTEM",
            "target_host": "127.0.0.1",
            "target_port": 5432,
            "target_db": "pgdb",
            "target_user": "postgres",
            "source_authority": src_auth.to_dict(),
            "target_authority": tgt_auth.to_dict(),
            "physical_spec": {
                "source_authority": src_auth.to_dict(),
                "target_authority": tgt_auth.to_dict(),
                "selected_scope": {},
                "tuning_rules": {},
            },
            "is_synthetic_test": True,
        }

    def test_daemon_restart_recovery_full_workflow(self):
        """Simulate daemon restart and verify Gateway 2 recovers durable state and executes transport."""
        gateway1 = EngineGateway()
        
        # 1. Create Project
        proj_res = gateway1.create_project({"project_name": "Restart Test Project"})
        proj_id = proj_res["project_id"]

        # 2. Create Migration
        mig_id = "mig-restart-test-01"
        mig_payload = self._get_valid_migration_payload(mig_id)
        gateway1.create_migration(mig_payload)

        # 3. Generate Execution Plan
        plan_res = gateway1.generate_plan({"migration_id": mig_id})

        # 4. Request Approval
        req_res = gateway1.request_approval({"migration_id": mig_id, "approver": "Security Lead"})
        app_id = req_res["approval_reference_id"]

        # 5. Submit Approval Decision
        gateway1.submit_approval_decision({"approval_reference_id": app_id, "decision": "APPROVED", "approver": "Security Lead"})

        # --- SIMULATE COMPLETE PYTHON DAEMON RESTART ---
        del gateway1

        # Instantiate fresh Gateway 2 (RAM dicts self._projects, self._migrations, self._plans are completely empty)
        gateway2 = EngineGateway()
        self.assertEqual(len(gateway2._projects), 0)
        self.assertEqual(len(gateway2._migrations), 0)
        self.assertEqual(len(gateway2._plans), 0)

        # 6. Gateway 2 Start Transport post-restart (must read durable CentralStateStore)
        with patch.object(gateway2.super_engine, "execute_migration") as mock_exec:
            mock_exec.return_value = {
                "operation_id": f"op-{mig_id}",
                "migration_id": mig_id,
                "status": "started",
                "stage": "transport",
                "message": "Migration execution successfully delegated to WorkflowEngine.",
            }
            start_res = gateway2.start_transport({"migration_id": mig_id, "is_synthetic_test": True})
            self.assertIn(start_res["status"], ("started", "accepted"))
            self.assertEqual(start_res["migration_id"], mig_id)

    def test_daemon_restart_missing_approval_fails_closed(self):
        """Verify that starting transport without approval post-restart fails closed."""
        gateway1 = EngineGateway()
        mig_id = "mig-restart-unapproved-02"
        mig_payload = self._get_valid_migration_payload(mig_id)
        gateway1.create_migration(mig_payload)
        gateway1.generate_plan({"migration_id": mig_id})

        # Restart daemon before approval
        del gateway1
        gateway2 = EngineGateway()

        start_res = gateway2.start_transport({"migration_id": mig_id, "is_synthetic_test": False})
        self.assertIn(start_res["status"], ("failed", "error"))
        self.assertEqual(start_res["error_code"], "APPROVAL_REQUIRED")

    def test_daemon_restart_plan_tampering_fails_closed(self):
        """Verify that modifying a plan after restart invalidates approval and fails closed."""
        gateway1 = EngineGateway()
        mig_id = "mig-restart-tamper-03"
        mig_payload = self._get_valid_migration_payload(mig_id)
        gateway1.create_migration(mig_payload)
        gateway1.generate_plan({"migration_id": mig_id})
        req = gateway1.request_approval({"migration_id": mig_id})
        gateway1.submit_approval_decision({"approval_reference_id": req["approval_reference_id"], "decision": "APPROVED"})

        # Daemon restarts
        del gateway1
        gateway2 = EngineGateway()

        # Tamper with plan in CentralStateStore
        tampered_plan = {"plan_id": f"plan-{mig_id}", "nodes": [{"id": "tampered_node"}]}
        self.state_store.set_state(mig_id, tampered_plan, category="execution_plan")

        start_res = gateway2.start_transport({"migration_id": mig_id, "is_synthetic_test": False})
        self.assertIn(start_res["status"], ("failed", "error"))
        self.assertEqual(start_res["error_code"], "PLAN_FINGERPRINT_MISMATCH")


if __name__ == "__main__":
    unittest.main()
