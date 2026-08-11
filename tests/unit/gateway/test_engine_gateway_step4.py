"""
AKAAL Unit Tests — EngineGateway Thinning & Async Start ACK (Step 4 Verification)
==================================================================================
Tests EngineGateway non-blocking start_transport (<50ms ACK), AkaalSuperEngine delegation,
fail-closed governance/fingerprint gates, idempotent double-start protection,
error code mapping, and truthful before-start runtime snapshot authority.
"""

import time
import unittest
from typing import Dict, Any

from akaal.gateway.engine_gateway import EngineGateway
from akaal.engine.facade import AkaalSuperEngine
from akaal.governance.facade.platform6 import EnterpriseGovernancePlatformV6
from akaal.core.state.state_store import CentralStateStore


class TestEngineGatewayStep4(unittest.TestCase):

    def setUp(self):
        self.gateway = EngineGateway()
        self.governance = EnterpriseGovernancePlatformV6()
        self.workflow_id = "mig-gateway-step4-test-01"

        # Register migration in gateway
        self.sample_spec = {
            "migration_id": self.workflow_id,
            "migration_name": "Step 4 Test Migration",
            "source_host": "oracle-src.internal",
            "source_port": 1521,
            "source_database": "FREE",
            "source_username": "SYSTEM",
            "target_host": "pg-dst.internal",
            "target_port": 5432,
            "target_database": "analytics",
            "target_username": "postgres",
            "selected_scope": {"objects": [{"object_name": "CUSTOMERS"}]},
            "tuning_policy": {"parallelism": 2, "batch_size": 5000},
            "validation_policy": {"level": "CHECKSUM"},
            "source_authority": {
                "system_type": "ORACLE",
                "host": "oracle-src.internal",
                "port": 1521,
                "database": "FREE",
                "username": "SYSTEM",
                "credentials_ref": "vault:oracle/src",
                "password": "secret_source_pass",
            },
            "target_authority": {
                "system_type": "POSTGRESQL",
                "host": "pg-dst.internal",
                "port": 5432,
                "database": "analytics",
                "username": "postgres",
                "credentials_ref": "vault:pg/dst",
                "password": "secret_target_pass",
            },
            "physical_spec": {"selected_scope": {"objects": [{"object_name": "CUSTOMERS"}]}},
            "physical_validation_context": {"source_rows": [(1, "Alice")], "target_rows": [(1, "Alice")]},
        }
        self.dag = {"phases": [{"phase": "schema"}, {"phase": "transport"}]}

        self.gateway._migrations[self.workflow_id] = {"config": self.sample_spec}
        self.gateway._plans[self.workflow_id] = self.dag

        # Reset state store for test migration
        self.gateway.state_store.set_state(f"{self.workflow_id}_approval", None, category="governance")
        self.gateway.state_store.set_state(f"{self.workflow_id}_status", None, category="runtime")

    def test_01_approved_migration_start_returns_accepted_and_fast_ack(self):
        # 1. Compute fingerprint & Approve via Governance Platform V6
        fp = AkaalSuperEngine.compute_plan_fingerprint(self.sample_spec, self.dag)
        self.governance.approve_migration_with_fingerprint(self.workflow_id, fp)

        # 2. Invoke start_transport & verify timing < 50ms
        t0 = time.perf_counter()
        res = self.gateway.start_transport({"migration_id": self.workflow_id, "is_synthetic_test": True})
        elapsed_ms = (time.perf_counter() - t0) * 1000.0

        self.assertEqual(res.get("status"), "accepted")
        self.assertTrue(res.get("request_accepted"))
        self.assertEqual(res.get("migration_id"), self.workflow_id)
        self.assertEqual(res.get("plan_fingerprint"), fp)
        self.assertLess(elapsed_ms, 50.0, f"start_transport ACK took {elapsed_ms:.2f}ms (must be < 50ms)")

    def test_02_unapproved_migration_returns_approval_required(self):
        res = self.gateway.start_transport({"migration_id": self.workflow_id})
        self.assertEqual(res.get("status"), "error")
        self.assertEqual(res.get("error_code"), "APPROVAL_REQUIRED")

    def test_03_missing_approved_fingerprint_fails_closed(self):
        # Legacy approval without fingerprint
        self.gateway.state_store.set_state(f"{self.workflow_id}_approval", {"status": "approved"}, category="governance")
        res = self.gateway.start_transport({"migration_id": self.workflow_id})
        self.assertEqual(res.get("status"), "error")
        self.assertEqual(res.get("error_code"), "APPROVED_PLAN_FINGERPRINT_MISSING")

    def test_04_changed_approved_plan_fails_with_fingerprint_mismatch(self):
        fp = AkaalSuperEngine.compute_plan_fingerprint(self.sample_spec, self.dag)
        self.governance.approve_migration_with_fingerprint(self.workflow_id, fp)

        # Payload mutates selected_scope post-approval
        mutated_payload = {"migration_id": self.workflow_id, "selected_scope": {"objects": [{"object_name": "NEW_TABLE"}]}}
        res = self.gateway.start_transport(mutated_payload)

        self.assertEqual(res.get("status"), "error")
        self.assertEqual(res.get("error_code"), "PLAN_FINGERPRINT_MISMATCH")

    def test_05_physical_contract_failure_propagated(self):
        spec_no_physical = dict(self.sample_spec)
        del spec_no_physical["physical_spec"]

        mig_id_no_phys = "mig-no-phys-01"
        spec_no_physical["migration_id"] = mig_id_no_phys
        self.gateway._migrations[mig_id_no_phys] = {"config": spec_no_physical}
        self.gateway._plans[mig_id_no_phys] = self.dag
        fp = AkaalSuperEngine.compute_plan_fingerprint(spec_no_physical, self.dag)
        self.governance.approve_migration_with_fingerprint(mig_id_no_phys, fp)

        res = self.gateway.start_transport({"migration_id": mig_id_no_phys, "is_synthetic_test": False})
        self.assertEqual(res.get("status"), "error")
        self.assertEqual(res.get("error_code"), "PHYSICAL_EXECUTION_CONTRACT_INVALID")

    def test_06_idempotent_repeated_start_returns_existing_operation_ack(self):
        fp = AkaalSuperEngine.compute_plan_fingerprint(self.sample_spec, self.dag)
        self.governance.approve_migration_with_fingerprint(self.workflow_id, fp)

        # First start call
        res1 = self.gateway.start_transport({"migration_id": self.workflow_id, "is_synthetic_test": True})
        self.assertEqual(res1.get("status"), "accepted")
        op_id_1 = res1.get("operation_id")

        # Immediate second start call (simulating double click)
        res2 = self.gateway.start_transport({"migration_id": self.workflow_id, "is_synthetic_test": True})
        self.assertEqual(res2.get("status"), "accepted")
        self.assertTrue(res2.get("already_running"))
        self.assertEqual(res2.get("operation_id"), op_id_1)

    def test_07_before_start_runtime_snapshot_honest_defaults(self):
        # Migration created but unstarted
        snap = self.gateway.get_runtime_snapshot({"migration_id": self.workflow_id})
        self.assertNotEqual(snap.get("current_stage"), "scout")
        self.assertIn("start", snap.get("available_actions", []))

    def test_08_secret_redaction_in_ipc_errors(self):
        fp = AkaalSuperEngine.compute_plan_fingerprint(self.sample_spec, self.dag)
        self.governance.approve_migration_with_fingerprint(self.workflow_id, fp)

        # Force a generic error payload with raw password
        res = self.gateway.start_transport({
            "migration_id": self.workflow_id,
            "password": "secret_source_pass",
            "is_synthetic_test": True
        })
        err_msg = res.get("error_message", "")
        self.assertNotIn("secret_source_pass", err_msg)


if __name__ == "__main__":
    unittest.main()
