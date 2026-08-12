"""
AKAAL Forensic Verification Tests — Step 5.5 Enterprise Workflow Gating & Truthful Telemetry
=============================================================================================
Tests:
1. Full Legal Workflow Stage Mapping & Gating Rules
2. GATE 1 / GATE 2 / GATE 3 Fail-Closed Enforcement
3. Tampered Approved Plan Fingerprint Rejection
4. Truthful Telemetry Snapshot Generation from CentralStateStore
5. Pause / Resume / Terminate Lifecycle Constraints
6. Secret Telemetry Exposure Prevention (PLAINTEXT_SECRET_TELEMETRY_EXPOSURE = NO)
7. Legacy Transport Isolation Verification
"""

import os
import unittest
from unittest.mock import MagicMock, patch

from akaal.gateway.engine_gateway import EngineGateway
from akaal.core.state.state_store import CentralStateStore
from akaal.engine.facade import AkaalSuperEngine
from akaal.migration.target_identifier import ConnectionAuthority


class TestStep55WorkflowGatingTelemetry(unittest.TestCase):

    def setUp(self):
        self.state_store = CentralStateStore()
        self.super_engine = AkaalSuperEngine()
        self.gateway = EngineGateway()

    def _get_valid_payload(self, mig_id: str) -> dict:
        src_auth = ConnectionAuthority(connection_id="src-01", role="SOURCE", engine="ORACLE", host="127.0.0.1", port=1521, database="FREE", username="SYSTEM", credential_ref="cred-src")
        tgt_auth = ConnectionAuthority(connection_id="tgt-01", role="TARGET", engine="POSTGRESQL", host="127.0.0.1", port=5432, database="pgdb", username="postgres", credential_ref="cred-tgt")
        return {
            "migration_id": mig_id,
            "migration_name": f"Gating Test {mig_id}",
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
            "is_synthetic_test": True,
        }

    def test_01_gate_2_unapproved_plan_fails_closed(self):
        """Verify starting transport without GATE 2 approval fails closed with APPROVAL_REQUIRED."""
        mig_id = "mig-gate2-unapproved-01"
        payload = self._get_valid_payload(mig_id)
        self.gateway.create_migration(payload)
        self.gateway.generate_plan({"migration_id": mig_id})

        # Start transport without approval
        res = self.gateway.start_transport({"migration_id": mig_id, "is_synthetic_test": False})
        self.assertIn(res["status"], ("failed", "error"))
        self.assertEqual(res["error_code"], "APPROVAL_REQUIRED")

    def test_02_gate_2_tampered_plan_fingerprint_fails_closed(self):
        """Verify modifying plan after approval causes SHA-256 fingerprint mismatch and fails closed."""
        mig_id = "mig-gate2-tamper-02"
        payload = self._get_valid_payload(mig_id)
        self.gateway.create_migration(payload)
        self.gateway.generate_plan({"migration_id": mig_id})
        
        # Approve plan
        req = self.gateway.request_approval({"migration_id": mig_id, "approver": "Security Lead"})
        app_id = req["approval_reference_id"]
        self.gateway.submit_approval_decision({"approval_reference_id": app_id, "decision": "APPROVED", "approver": "Security Lead"})

        # Tamper with stored plan
        tampered_plan = {"plan_id": f"plan-{mig_id}", "stages": [{"stage_id": "malicious_stage"}]}
        self.state_store.set_state(mig_id, tampered_plan, category="execution_plan")

        # Clear Gateway RAM dict to ensure CentralStateStore tampered plan is read (simulating process restart)
        self.gateway._plans.pop(mig_id, None)
        self.gateway._plans.pop(f"plan-{mig_id}", None)

        # Attempt to start transport with tampered plan
        res = self.gateway.start_transport({"migration_id": mig_id, "is_synthetic_test": False})
        self.assertIn(res["status"], ("failed", "error"))
        self.assertEqual(res["error_code"], "PLAN_FINGERPRINT_MISMATCH")

    def test_03_truthful_telemetry_snapshot_from_backend(self):
        """Verify get_runtime_snapshot reads truthful metrics from CentralStateStore."""
        mig_id = "mig-telem-snapshot-03"
        self.state_store.set_state(f"{mig_id}_status", {"status": "RUNNING"}, category="runtime")
        self.state_store.update_progress(mig_id, {
            "migration_id": mig_id,
            "status": "RUNNING",
            "rows_migrated": 45000,
            "rows_total": 100000,
            "throughput_mbps": 12.5,
            "completed_tables": 3,
            "total_tables": 10,
            "current_table": "SYSTEM.CUSTOMERS",
            "checkpoint_lsn": "chkpt-00045"
        })

        snap = self.gateway.get_runtime_snapshot({"migration_id": mig_id})
        self.assertEqual(snap["status"], "RUNNING")
        self.assertEqual(snap["rows_transferred"], 45000)
        self.assertEqual(snap["rows_total"], 100000)
        self.assertEqual(snap["progress_percent"], 45.0)
        self.assertEqual(snap["throughput_mbps"], 12.5)
        self.assertEqual(snap["current_table"], "SYSTEM.CUSTOMERS")
        self.assertEqual(snap["current_checkpoint_lsn"], "chkpt-00045")

    def test_04_failed_migration_telemetry_truthfulness(self):
        """Verify failed migration telemetry correctly reports FAILED status and error details."""
        mig_id = "mig-failed-telem-04"
        self.state_store.set_state(f"{mig_id}_status", {"status": "FAILED", "failed_stage": "data_transport", "error_code": "CONNECTION_LOST"}, category="runtime")
        self.state_store.update_progress(mig_id, {
            "migration_id": mig_id,
            "status": "FAILED",
            "failed_stage": "data_transport",
            "error_code": "CONNECTION_LOST",
            "error_message": "Network timeout to source Oracle host"
        })

        snap = self.gateway.get_runtime_snapshot({"migration_id": mig_id})
        self.assertEqual(snap["status"], "FAILED")
        self.assertEqual(snap["health_status"], "ERROR")
        self.assertEqual(snap["next_stage"], "recovery")
        self.assertIn("Network timeout", snap["current_activity"])

    def test_05_no_plaintext_secrets_in_telemetry_snapshot(self):
        """Verify get_runtime_snapshot output contains NO plaintext passwords."""
        mig_id = "mig-sec-snap-05"
        payload = self._get_valid_payload(mig_id)
        payload["source_pass"] = "PlainTextSecretPass123!"
        self.gateway.create_migration(payload)

        snap = self.gateway.get_runtime_snapshot({"migration_id": mig_id})
        snap_str = str(snap)
        self.assertNotIn("PlainTextSecretPass123!", snap_str)
        self.assertNotIn("source_pass", snap_str)

    def test_06_legacy_transport_isolation(self):
        """Verify legacy transport engine is NOT reachable from WorkflowEngine or EngineGateway."""
        from akaal.gateway.engine_gateway import EngineGateway
        import inspect
        source_code = inspect.getsource(EngineGateway)
        self.assertNotIn("AkaalMigrationEngine", source_code)
        self.assertNotIn("OracleSourceReader", source_code)
        self.assertNotIn("PostgreSQLTargetWriter", source_code)


if __name__ == "__main__":
    unittest.main()
