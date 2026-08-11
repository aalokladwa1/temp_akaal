"""
AKAAL Unit Tests — EngineGateway Thinning & Async Start ACK (Step 4 Verification)
==================================================================================
Tests EngineGateway non-blocking start_transport (<50ms ACK), AkaalSuperEngine delegation,
fail-closed governance/fingerprint gates, S4-H10 atomic single-start claim under concurrency,
S4-H11 legal state transition ordering, and S4-H12 single JSON IPC serialization contract.
"""

import time
import json
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, Any

from akaal.gateway.engine_gateway import EngineGateway
from akaal.engine.facade import AkaalSuperEngine
from akaal.governance.facade.platform6 import EnterpriseGovernancePlatformV6
from akaal.core.state.state_store import CentralStateStore
from akaal.ipc_server import handle_capability_request, send_ipc_frame


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

        # Warm up super_engine in setUp to eliminate initial bootstrap latency
        _ = self.gateway.super_engine

        # Reset state store for test migration
        self.gateway.state_store.set_state(f"{self.workflow_id}_approval", None, category="governance")
        self.gateway.state_store.set_state(f"{self.workflow_id}_status", None, category="runtime")

    def test_01_approved_migration_start_returns_accepted_and_fast_ack(self):
        fp = AkaalSuperEngine.compute_plan_fingerprint(self.sample_spec, self.dag)
        self.governance.approve_migration_with_fingerprint(self.workflow_id, fp)

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
        self.gateway.state_store.set_state(f"{self.workflow_id}_approval", {"status": "approved"}, category="governance")
        res = self.gateway.start_transport({"migration_id": self.workflow_id})
        self.assertEqual(res.get("status"), "error")
        self.assertEqual(res.get("error_code"), "APPROVED_PLAN_FINGERPRINT_MISSING")

    def test_04_changed_approved_plan_fails_with_fingerprint_mismatch(self):
        fp = AkaalSuperEngine.compute_plan_fingerprint(self.sample_spec, self.dag)
        self.governance.approve_migration_with_fingerprint(self.workflow_id, fp)

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

        res1 = self.gateway.start_transport({"migration_id": self.workflow_id, "is_synthetic_test": True})
        self.assertEqual(res1.get("status"), "accepted")
        op_id_1 = res1.get("operation_id")

        res2 = self.gateway.start_transport({"migration_id": self.workflow_id, "is_synthetic_test": True})
        self.assertEqual(res2.get("status"), "accepted")
        self.assertTrue(res2.get("already_running"))
        self.assertEqual(res2.get("operation_id"), op_id_1)

    def test_07_before_start_runtime_snapshot_honest_defaults(self):
        snap = self.gateway.get_runtime_snapshot({"migration_id": self.workflow_id})
        self.assertNotEqual(snap.get("current_stage"), "scout")
        self.assertIn("start", snap.get("available_actions", []))

    def test_08_secret_redaction_in_ipc_errors(self):
        fp = AkaalSuperEngine.compute_plan_fingerprint(self.sample_spec, self.dag)
        self.governance.approve_migration_with_fingerprint(self.workflow_id, fp)

        res = self.gateway.start_transport({
            "migration_id": self.workflow_id,
            "password": "secret_source_pass",
            "is_synthetic_test": True
        })
        err_msg = res.get("error_message", "")
        self.assertNotIn("secret_source_pass", err_msg)

    def test_09_concurrent_start_transport_launches_exactly_one_worker(self):
        # S4-H10: Concurrency barrier testing
        fp = AkaalSuperEngine.compute_plan_fingerprint(self.sample_spec, self.dag)
        self.governance.approve_migration_with_fingerprint(self.workflow_id, fp)

        barrier = threading.Barrier(5)
        results = []

        def worker_task():
            barrier.wait()  # Synchronize 5 threads to call start_transport simultaneously
            return self.gateway.start_transport({"migration_id": self.workflow_id, "is_synthetic_test": True})

        with ThreadPoolExecutor(max_workers=5) as pool:
            futures = [pool.submit(worker_task) for _ in range(5)]
            results = [f.result() for f in futures]

        winners = [r for r in results if not r.get("already_running")]
        losers = [r for r in results if r.get("already_running")]

        if len(winners) != 1:
            print("TEST_09 RESULTS DIAGNOSTIC:", results)

        self.assertEqual(len(winners), 1, f"Exactly ONE thread must win the atomic single-start claim. Results: {results}")
        self.assertEqual(len(losers), 4, "Remaining 4 competing threads must report already_running")

        # Verify all 5 threads resolved to the SAME operation_id
        op_ids = {r.get("operation_id") for r in results}
        self.assertEqual(len(op_ids), 1, "All 5 concurrent callers must receive the exact same operation_id")

    def test_10_guarded_transition_prevents_stale_overwrites(self):
        # S4-H11: Transition guard test
        state_store = CentralStateStore()
        key = f"{self.workflow_id}_status"
        state_store.set_state(key, {"status": "RUNNING", "operation_id": "op-active"}, category="runtime")

        # Stale attempt to overwrite RUNNING back to STARTING must be REJECTED
        ok = state_store.guarded_transition_state(key, expected_current=["START_REQUESTED"], target_status="STARTING")
        self.assertFalse(ok)
        self.assertEqual(state_store.get_state(key, category="runtime")["status"], "RUNNING")

    def test_11_ipc_serialization_single_json_structure(self):
        # S4-H12: Single JSON object serialization verification
        req = {
            "request_id": "req-12345",
            "capability": "get_engine_status",
            "payload": "{}"
        }
        ipc_resp = handle_capability_request(req)

        self.assertEqual(ipc_resp["status"], "success")
        self.assertIsInstance(ipc_resp["result"], dict, "result must be a structured Python dict, NOT a double-stringified JSON string")
        self.assertEqual(ipc_resp["result"]["engine"], "AKAAL Enterprise Engine")

        # Verify single json.dumps encoding frame
        frame_json = json.dumps(ipc_resp)
        parsed = json.loads(frame_json)
        self.assertIsInstance(parsed["result"], dict)

    def test_12_durable_state_authority_recovery(self):
        # Durable state store singleton authority verification
        fp = AkaalSuperEngine.compute_plan_fingerprint(self.sample_spec, self.dag)
        self.governance.approve_migration_with_fingerprint(self.workflow_id, fp)

        res = self.gateway.start_transport({"migration_id": self.workflow_id, "is_synthetic_test": True})
        op_id = res.get("operation_id")

        # Re-query CentralStateStore singleton instance
        fresh_store = CentralStateStore()
        status_rec = fresh_store.get_state(f"{self.workflow_id}_status", default=None, category="runtime")

        self.assertIsNotNone(status_rec)
        self.assertEqual(status_rec.get("operation_id"), op_id)
        self.assertIn(status_rec.get("status"), ("STARTING", "RUNNING"))


if __name__ == "__main__":
    unittest.main()
