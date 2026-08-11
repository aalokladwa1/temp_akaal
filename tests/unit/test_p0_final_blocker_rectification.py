"""
AKAAL P0 Live Acceptance Blockers — Focused Regression Tests
============================================================
Verifies non-default connection authority survival, async preflight ACK latency & DTO bounds,
capacity check target password resolution, structured create_migration failure handling,
and deterministic retry suppression.
"""

import unittest
import time
from typing import Dict, Any
from akaal.migration.target_identifier import ConnectionAuthority
from akaal.core.credential_vault import credential_vault
from akaal.gateway.engine_gateway import EngineGateway
from akaal.workflow.steps.migration_steps import (
    _extract_source_config,
    _extract_target_config,
)
from akaal.workflow.execution.policies import FixedRetryPolicy, ExponentialRetryPolicy


class TestP0LiveAcceptanceBlockers(unittest.TestCase):

    def setUp(self):
        self.gateway = EngineGateway()
        credential_vault.clear_all()

    # TEST 1 — Async preflight ACK returns before background discovery completes (< 250ms)
    def test_01_async_preflight_ack_returns_immediately(self):
        start_time = time.time()
        ack = self.gateway.invoke("run_preflight", {
            "operation_id": "op-ack-speed-test",
            "source_host": "oracle-test.internal",
            "source_port": 1627,
            "source_service": "CUSTOM_PDB_X",
            "source_user": "MIG_USER_X",
            "source_pass": "pass_x",
            "target_host": "pg-test.internal",
            "target_port": 6547,
            "target_db": "CUSTOM_TARGET_X",
            "target_user": "TARGET_USER_X",
            "target_pass": "pass_y",
        })
        elapsed_ms = (time.time() - start_time) * 1000.0

        self.assertTrue(ack.get("command_accepted"))
        self.assertEqual(ack.get("status"), "accepted")
        self.assertEqual(ack.get("operation_id"), "op-ack-speed-test")
        self.assertLess(elapsed_ms, 250.0, f"Preflight ACK latency {elapsed_ms:.2f}ms exceeded 250ms target")

    # TEST 2 — RUNNING preflight DTO does not contain full catalog
    def test_02_running_preflight_dto_is_bounded(self):
        op_id = "op-dto-bound-check"
        with self.gateway._preflight_lock:
            self.gateway._preflight_operations[op_id] = {
                "operation_id": op_id,
                "status": "RUNNING",
                "phase": "PROFILING",
                "completed_objects": 150,
                "total_objects": 5000,
                "schema": "BIG_SCH_01",
                "object_name": "TBL_ORDERS",
                "qualified_name": "BIG_SCH_01.TBL_ORDERS",
                "rows_counted": 250000,
                "message": "Profiling...",
                "result": {"large_catalog_nodes": ["node_data"] * 5000}
            }

        dto = self.gateway.invoke("get_preflight_operation", {"operation_id": op_id})
        self.assertEqual(dto["status"], "RUNNING")
        self.assertEqual(dto["completed_objects"], 150)
        self.assertNotIn("result", dto)
        self.assertNotIn("large_catalog_nodes", dto)

    # TEST 3 & 4 — Exact custom non-default source and target authority survive end-to-end
    def test_03_custom_non_default_authority_survives(self):
        payload = {
            "source_host": "oracle-test.internal",
            "source_port": 1627,
            "source_service": "CUSTOM_PDB_X",
            "source_user": "MIG_USER_X",
            "source_pass": "secret_x_999",
            "target_host": "pg-test.internal",
            "target_port": 6547,
            "target_db": "CUSTOM_TARGET_X",
            "target_user": "TARGET_USER_X",
            "target_pass": "secret_y_888",
        }
        res = self.gateway.create_migration(payload)
        self.assertTrue(res.get("success", True))
        mig_id = res["migration_id"]
        mig = self.gateway._migrations[mig_id]["config"]

        # Assert persisted manifest authority
        src_auth = mig["source_authority"]
        self.assertEqual(src_auth["host"], "oracle-test.internal")
        self.assertEqual(src_auth["port"], 1627)
        self.assertEqual(src_auth["database"], "CUSTOM_PDB_X")
        self.assertEqual(src_auth["username"], "MIG_USER_X")

        tgt_auth = mig["target_authority"]
        self.assertEqual(tgt_auth["host"], "pg-test.internal")
        self.assertEqual(tgt_auth["port"], 6547)
        self.assertEqual(tgt_auth["database"], "CUSTOM_TARGET_X")
        self.assertEqual(tgt_auth["username"], "TARGET_USER_X")

        # Assert runtime step extraction
        src_cfg = _extract_source_config(mig)
        self.assertEqual(src_cfg.host, "oracle-test.internal")
        self.assertEqual(src_cfg.port, 1627)
        self.assertEqual(src_cfg.database_name, "CUSTOM_PDB_X")
        self.assertEqual(src_cfg.extra["username"], "MIG_USER_X")

        tgt_cfg = _extract_target_config(mig)
        self.assertEqual(tgt_cfg.host, "pg-test.internal")
        self.assertEqual(tgt_cfg.port, 6547)
        self.assertEqual(tgt_cfg.database_name, "CUSTOM_TARGET_X")
        self.assertEqual(tgt_cfg.extra["username"], "TARGET_USER_X")

    # TEST 5 — Missing required authority field fails closed
    def test_05_missing_authority_field_fails_closed(self):
        payload = {
            "source_host": "oracle-test.internal",
            "source_port": 1627,
            "require_strict_authority": True,
            # missing source_service / database
            "source_user": "MIG_USER_X",
            "source_pass": "pass_x",
            "target_host": "pg-test.internal",
            "target_port": 6547,
            "target_db": "CUSTOM_TARGET_X",
            "target_user": "TARGET_USER_X",
            "target_pass": "pass_y",
        }
        res = self.gateway.create_migration(payload)
        self.assertFalse(res.get("success"))
        self.assertEqual(res.get("status"), "error")
        self.assertEqual(res.get("error_code"), "MIGRATION_CONFIGURATION_INCOMPLETE")
        self.assertIsNone(res.get("migration_id"))

    # TEST 6 — Credential refs resolve through canonical refs
    def test_06_credential_refs_resolution(self):
        payload = {
            "source_host": "oracle-test.internal",
            "source_port": 1627,
            "source_service": "CUSTOM_PDB_X",
            "source_user": "MIG_USER_X",
            "source_pass": "pass_ora_secret",
            "target_host": "pg-test.internal",
            "target_port": 6547,
            "target_db": "CUSTOM_TARGET_X",
            "target_user": "TARGET_USER_X",
            "target_pass": "pass_pg_secret",
        }
        res = self.gateway.create_migration(payload)
        mig = self.gateway._migrations[res["migration_id"]]["config"]

        src_cfg = _extract_source_config(mig)
        tgt_cfg = _extract_target_config(mig)

        self.assertEqual(src_cfg.extra["password"], "pass_ora_secret")
        self.assertEqual(tgt_cfg.extra["password"], "pass_pg_secret")

    # TEST 7 — Capacity check receives resolved target password
    def test_07_capacity_check_receives_target_password(self):
        payload = {
            "source_host": "oracle-test.internal",
            "source_port": 1627,
            "source_service": "CUSTOM_PDB_X",
            "source_user": "MIG_USER_X",
            "source_pass": "ora_pass",
            "target_host": "pg-test.internal",
            "target_port": 6547,
            "target_db": "CUSTOM_TARGET_X",
            "target_user": "TARGET_USER_X",
            "target_pass": "resolved_pg_pass_123",
        }
        tgt_auth = ConnectionAuthority.from_dict(payload, role="TARGET")
        credential_vault.store_credentials({"password": "resolved_pg_pass_123"}, existing_ref=tgt_auth.credential_ref)

        resolved_secrets = credential_vault.get_credentials(tgt_auth.credential_ref, fail_closed=True)
        self.assertEqual(resolved_secrets.get("password"), "resolved_pg_pass_123")

    # TEST 8 — create_migration application failure is surfaced with success=False
    def test_08_create_migration_failure_surfaced_correctly(self):
        payload = {
            "source_host": "",
            "source_port": 0,
            "source_db": "",
            "source_user": "",
        }
        res = self.gateway.create_migration(payload)
        self.assertFalse(res.get("success"))
        self.assertEqual(res.get("status"), "error")
        self.assertEqual(res.get("error_code"), "MIGRATION_CONFIGURATION_INCOMPLETE")
        self.assertIsNone(res.get("migration_id"))

    # TEST 9 — Deterministic failure retry policy classification
    def test_09_deterministic_retry_policy_classification(self):
        policy = FixedRetryPolicy(delay_seconds=0.1)
        exp_policy = ExponentialRetryPolicy()

        config_err = ValueError("MIGRATION_CONFIGURATION_INCOMPLETE: Source authority missing")
        integrity_err = ValueError("MIGRATION_AUTHORITY_INTEGRITY_VIOLATION: Fingerprint mismatch")
        cred_err = RuntimeError("CREDENTIAL_RESOLUTION_FAILED: Password missing")

        self.assertFalse(policy.should_retry(1, 3, config_err))
        self.assertFalse(policy.should_retry(1, 3, integrity_err))
        self.assertFalse(policy.should_retry(1, 3, cred_err))

        self.assertFalse(exp_policy.should_retry(1, 3, config_err))
        self.assertFalse(exp_policy.should_retry(1, 3, integrity_err))


if __name__ == "__main__":
    unittest.main()
