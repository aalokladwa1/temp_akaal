"""
AKAAL Forensic Verification Tests — Capability Registry & IPC Routing Gate (Step 4.3)
======================================================================================
Verifies Python EngineGateway capability dispatch, IPC frame serialization, request_id correlation,
fail-closed error propagation, secret redaction, and truthful runtime snapshot contracts without modifying production code.
"""

import os
import json
import sqlite3
import unittest
from typing import Dict, Any

from akaal.gateway.engine_gateway import EngineGateway
from akaal.engine.facade import AkaalSuperEngine
from akaal.governance.facade.platform6 import EnterpriseGovernancePlatformV6
from akaal.core.state.state_store import CentralStateStore
from akaal.ipc_server import handle_capability_request, engine_gateway as ipc_gateway


class TestCapabilityRegistryIPCVerification(unittest.TestCase):

    def setUp(self):
        self.gateway = ipc_gateway
        self.governance = EnterpriseGovernancePlatformV6()
        self.workflow_id = "mig-ipc-gate-test-01"

        self.sample_spec = {
            "migration_id": self.workflow_id,
            "migration_name": "IPC Verification Gate Migration",
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

        # Warm up super_engine
        _ = self.gateway.super_engine

        self.gateway.state_store.set_state(f"{self.workflow_id}_approval", None, category="governance")
        self.gateway.state_store.set_state(f"{self.workflow_id}_status", None, category="runtime")

    def test_01_rust_registered_capabilities_dispatch_in_python(self):
        """Verifies that canonical capabilities registered in Rust CapabilityRegistry dispatch via EngineGateway."""
        capabilities_to_test = [
            "get_engine_status",
            "supported_engines",
            "create_project",
            "create_migration",
            "move_migration_to_project",
            "test_connection",
            "get_preflight_operation",
            "get_migration_result",
            "generate_plan",
            "request_approval",
            "get_approval_queue",
            "get_approvals",
            "execute_schema",
            "pause_transport",
            "pause_migration",
            "resume_migration",
            "resume_transport",
            "trigger_checkpoint",
            "create_checkpoint",
            "rollback_migration",
            "terminate_migration",
            "run_validation",
            "execute_healing",
            "generate_certificate",
            "get_runtime_snapshot",
            "subscribe_runtime_events",
        ]

        for cap in capabilities_to_test:
            req = {"request_id": f"req-test-{cap}", "capability": cap, "payload": json.dumps({"migration_id": self.workflow_id})}
            resp = handle_capability_request(req)
            self.assertEqual(resp.get("status"), "success", f"Capability '{cap}' must dispatch cleanly via EngineGateway")
            self.assertIsNotNone(resp.get("result"), f"Capability '{cap}' result must not be None")
            self.assertIsInstance(resp.get("result"), dict, f"Capability '{cap}' result must be a structured Python dict")

    def test_02_unknown_capability_fails_closed(self):
        """Verifies that unknown or unroutable capability fails closed with error status."""
        req = {"request_id": "req-unknown-cap", "capability": "non_existent_capability", "payload": "{}"}
        resp = handle_capability_request(req)
        self.assertEqual(resp.get("status"), "error")
        self.assertIn("Unsupported IPC capability", resp.get("error", ""))

    def test_03_request_id_correlation(self):
        """Verifies request_id correlation in response envelope."""
        req_id = "req-correlation-999"
        req = {"request_id": req_id, "capability": "get_engine_status", "payload": "{}"}
        resp = handle_capability_request(req)
        self.assertEqual(resp.get("request_id"), req_id)

    def test_04_start_transport_complete_route(self):
        """Verifies complete end-to-end Python route for start_transport."""
        mig_id_route = "mig-route-test-04"
        route_spec = dict(self.sample_spec)
        route_spec["migration_id"] = mig_id_route
        self.gateway._migrations[mig_id_route] = {"config": route_spec}
        self.gateway._plans[mig_id_route] = self.dag

        fp = AkaalSuperEngine.compute_plan_fingerprint(route_spec, self.dag)
        self.governance.approve_migration_with_fingerprint(mig_id_route, fp)

        req = {
            "request_id": "req-start-01",
            "capability": "start_transport",
            "payload": json.dumps({"migration_id": mig_id_route, "is_synthetic_test": True})
        }
        resp = handle_capability_request(req)
        self.assertEqual(resp.get("status"), "success")
        res = resp.get("result", {})
        self.assertEqual(res.get("status"), "accepted")
        self.assertTrue(res.get("request_accepted"))
        self.assertEqual(res.get("plan_fingerprint"), fp)

    def test_05_get_runtime_snapshot_honest_prestart_defaults(self):
        """Verifies truthful pre-start snapshot with current_stage: None."""
        req = {
            "request_id": "req-snap-01",
            "capability": "get_runtime_snapshot",
            "payload": json.dumps({"migration_id": self.workflow_id})
        }
        resp = handle_capability_request(req)
        self.assertEqual(resp.get("status"), "success")
        res = resp.get("result", {})
        self.assertIsNone(res.get("current_stage"), "Pre-start current_stage MUST be None")
        self.assertIsNone(res.get("rows_transferred"), "Pre-start rows_transferred MUST be None")
        self.assertEqual(res.get("active_workers"), 0)

    def test_06_single_serialization_ownership(self):
        """Verifies that handle_capability_request returns a native dict without double JSON stringification."""
        req = {"request_id": "req-single-ser", "capability": "get_engine_status", "payload": "{}"}
        resp = handle_capability_request(req)
        self.assertIsInstance(resp["result"], dict)
        serialized = json.dumps(resp)
        deserialized = json.loads(serialized)
        self.assertIsInstance(deserialized["result"], dict)

    def test_07_secret_redaction_in_ipc_errors(self):
        """Verifies secret redaction in error messages crossing IPC."""
        mig_id_redact = "mig-redact-test-07"
        redact_spec = dict(self.sample_spec)
        redact_spec["migration_id"] = mig_id_redact
        self.gateway._migrations[mig_id_redact] = {"config": redact_spec}
        self.gateway._plans[mig_id_redact] = self.dag

        fp = AkaalSuperEngine.compute_plan_fingerprint(redact_spec, self.dag)
        self.governance.approve_migration_with_fingerprint(mig_id_redact, fp)

        req = {
            "request_id": "req-redact-01",
            "capability": "start_transport",
            "payload": json.dumps({
                "migration_id": mig_id_redact,
                "password": "secret_source_pass",
                "is_synthetic_test": True
            })
        }
        resp = handle_capability_request(req)
        error_text = json.dumps(resp)
        self.assertNotIn("secret_source_pass", error_text)


if __name__ == "__main__":
    unittest.main()
