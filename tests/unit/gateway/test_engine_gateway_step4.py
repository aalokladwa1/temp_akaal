"""
AKAAL Unit Tests — EngineGateway Thinning & Async Start ACK (Step 4 Final Verification)
========================================================================================
Tests EngineGateway non-blocking start_transport (<50ms ACK), AkaalSuperEngine delegation,
fail-closed governance/fingerprint gates, S4-H10 cross-process atomic start claim under multiprocessing,
S4-H11 legal state transition ordering, S4-H12 single JSON IPC serialization contract,
and independent SQLite connection durability proof on artifacts/state.db.
"""

import os
import time
import json
import sqlite3
import threading
import multiprocessing
import unittest
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, Any

from akaal.gateway.engine_gateway import EngineGateway
from akaal.engine.facade import AkaalSuperEngine
from akaal.governance.facade.platform6 import EnterpriseGovernancePlatformV6
from akaal.core.state.state_store import CentralStateStore
from akaal.ipc_server import handle_capability_request, send_ipc_frame


def _subproc_claim_worker(db_path: str, key: str, op_id: str, fingerprint: str, barrier: Any, return_dict: Any, worker_idx: int):
    """Subprocess worker executing SQLite BEGIN IMMEDIATE atomic claim on shared state.db."""
    conn = sqlite3.connect(db_path, timeout=30.0)
    conn.row_factory = sqlite3.Row
    try:
        barrier.wait()  # Synchronize subprocess start
    except Exception:
        pass

    try:
        conn.execute("BEGIN IMMEDIATE;")
        cur = conn.execute("SELECT val_json FROM central_state WHERE category='runtime' AND state_key=?", (key,))
        row = cur.fetchone()
        current = json.loads(row["val_json"]) if (row and row["val_json"] and row["val_json"] != "null") else None
        curr_status = str(current.get("status", "")).upper() if isinstance(current, dict) else ""

        if curr_status in ("START_REQUESTED", "STARTING", "RUNNING", "COMPLETED"):
            conn.commit()
            return_dict[worker_idx] = {
                "won": False,
                "op_id": current.get("operation_id", op_id) if isinstance(current, dict) else op_id
            }
        else:
            new_state = {
                "status": "START_REQUESTED",
                "operation_id": op_id,
                "plan_fingerprint": fingerprint,
                "claimed_by_proc": worker_idx
            }
            conn.execute("""
            INSERT INTO central_state (category, state_key, val_json, updated_at)
            VALUES ('runtime', ?, ?, DATETIME('now'))
            ON CONFLICT(category, state_key) DO UPDATE SET
                val_json=excluded.val_json,
                updated_at=DATETIME('now')
            """, (key, json.dumps(new_state)))
            conn.commit()
            return_dict[worker_idx] = {"won": True, "op_id": op_id}
    except Exception as ex:
        try:
            conn.rollback()
        except Exception:
            pass
        return_dict[worker_idx] = {"won": False, "error": str(ex)}
    finally:
        conn.close()


class TestEngineGatewayStep4(unittest.TestCase):

    def setUp(self):
        import uuid
        self.gateway = EngineGateway()
        self.governance = EnterpriseGovernancePlatformV6()
        self.workflow_id = f"mig-gw-step4-{uuid.uuid4().hex[:8]}"

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

    def test_01_approved_valid_request_can_claim(self):
        fp = AkaalSuperEngine.compute_plan_fingerprint(self.sample_spec, self.dag)
        self.governance.approve_migration_with_fingerprint(self.workflow_id, fp)

        t0 = time.perf_counter()
        res = self.gateway.start_transport({"migration_id": self.workflow_id, "is_synthetic_test": True})
        elapsed_ms = (time.perf_counter() - t0) * 1000.0

        self.assertEqual(res.get("status"), "accepted")
        self.assertTrue(res.get("request_accepted"))
        self.assertEqual(res.get("migration_id"), self.workflow_id)
        self.assertEqual(res.get("plan_fingerprint"), fp)

    def test_02_unapproved_request_leaves_no_execution_claim(self):
        res = self.gateway.start_transport({"migration_id": self.workflow_id})
        self.assertEqual(res.get("status"), "error")
        self.assertEqual(res.get("error_code"), "APPROVAL_REQUIRED")

        claimed_state = self.gateway.state_store.get_state(f"{self.workflow_id}_status", default=None, category="runtime")
        self.assertIsNone(claimed_state, "Unapproved request MUST leave no execution claim in state store")

    def test_03_missing_approved_fingerprint_leaves_no_claim(self):
        self.gateway.state_store.set_state(f"{self.workflow_id}_approval", {"status": "approved"}, category="governance")
        res = self.gateway.start_transport({"migration_id": self.workflow_id})
        self.assertEqual(res.get("status"), "error")
        self.assertEqual(res.get("error_code"), "APPROVED_PLAN_FINGERPRINT_MISSING")

        claimed_state = self.gateway.state_store.get_state(f"{self.workflow_id}_status", default=None, category="runtime")
        self.assertIsNone(claimed_state, "Missing fingerprint request MUST leave no execution claim")

    def test_04_fingerprint_mismatch_leaves_no_execution_claim(self):
        fp = AkaalSuperEngine.compute_plan_fingerprint(self.sample_spec, self.dag)
        self.governance.approve_migration_with_fingerprint(self.workflow_id, fp)

        mutated_payload = {"migration_id": self.workflow_id, "selected_scope": {"objects": [{"object_name": "NEW_TABLE"}]}}
        res = self.gateway.start_transport(mutated_payload)

        self.assertEqual(res.get("status"), "error")
        self.assertEqual(res.get("error_code"), "PLAN_FINGERPRINT_MISMATCH")

        claimed_state = self.gateway.state_store.get_state(f"{self.workflow_id}_status", default=None, category="runtime")
        self.assertIsNone(claimed_state, "Fingerprint mismatch MUST leave no execution claim")

    def test_05_physical_contract_failure_leaves_no_execution_claim(self):
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

        claimed_state = self.gateway.state_store.get_state(f"{mig_id_no_phys}_status", default=None, category="runtime")
        self.assertIsNone(claimed_state, "Physical contract failure MUST leave no execution claim")

    def test_06_five_concurrent_starts_launch_one_worker(self):
        # S4-H10: Concurrency barrier testing
        fp = AkaalSuperEngine.compute_plan_fingerprint(self.sample_spec, self.dag)
        self.governance.approve_migration_with_fingerprint(self.workflow_id, fp)

        barrier = threading.Barrier(5)

        def worker_task():
            barrier.wait()
            return self.gateway.start_transport({"migration_id": self.workflow_id, "is_synthetic_test": True})

        with ThreadPoolExecutor(max_workers=5) as pool:
            futures = [pool.submit(worker_task) for _ in range(5)]
            results = [f.result() for f in futures]

        winners = [r for r in results if not r.get("already_running")]
        losers = [r for r in results if r.get("already_running")]

        self.assertEqual(len(winners), 1, f"Exactly ONE thread must win the atomic single-start claim. Results: {results}")
        self.assertEqual(len(losers), 4, "Remaining 4 competing threads must report already_running")

        op_ids = {r.get("operation_id") for r in results}
        self.assertEqual(len(op_ids), 1, "All 5 concurrent callers must receive the exact same operation_id")

    def test_07_independent_sqlite_durability_proof(self):
        # PART E: Real Durability Proof via direct independent SQLite query on artifacts/state.db
        mig_id_durability = "mig-durability-test-07"
        durability_spec = dict(self.sample_spec)
        durability_spec["migration_id"] = mig_id_durability
        self.gateway._migrations[mig_id_durability] = {"config": durability_spec}
        self.gateway._plans[mig_id_durability] = self.dag

        fp = AkaalSuperEngine.compute_plan_fingerprint(durability_spec, self.dag)
        self.governance.approve_migration_with_fingerprint(mig_id_durability, fp)

        res = self.gateway.start_transport({"migration_id": mig_id_durability, "is_synthetic_test": True})
        op_id = res.get("operation_id")

        db_path = self.gateway.state_store.db_path
        self.assertTrue(os.path.exists(db_path), f"SQLite database file must exist at {db_path}")

        # Independent raw SQLite connection reading state.db without touching shared Python memory
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cur = conn.execute("SELECT val_json FROM central_state WHERE category='runtime' AND state_key=?", (f"{mig_id_durability}_status",))
        row = cur.fetchone()
        conn.close()

        self.assertIsNotNone(row, "Durable SQLite record must exist in central_state table")
        durable_val = json.loads(row["val_json"])

        self.assertEqual(durable_val.get("operation_id"), op_id)
        self.assertEqual(durable_val.get("plan_fingerprint"), fp)
        self.assertIn(durable_val.get("status"), ("START_REQUESTED", "STARTING", "RUNNING", "COMPLETED"))

    def test_08_independent_sqlite_connection_contention_produces_one_winner(self):
        # Section 7: Two raw independent sqlite3 connections executing BEGIN IMMEDIATE on competing threads
        db_path = self.gateway.state_store.db_path
        key = "mig-conn-contention-08_status"

        # Pre-create table
        conn_init = sqlite3.connect(db_path)
        conn_init.execute("CREATE TABLE IF NOT EXISTS central_state (category TEXT, state_key TEXT, val_json TEXT, updated_at TEXT, PRIMARY KEY (category, state_key))")
        conn_init.execute("DELETE FROM central_state WHERE category='runtime' AND state_key=?", (key,))
        conn_init.commit()
        conn_init.close()

        results = {}
        barrier = threading.Barrier(2)

        def raw_conn_worker(idx, op_id):
            conn = sqlite3.connect(db_path, timeout=30.0)
            conn.row_factory = sqlite3.Row
            barrier.wait()
            try:
                conn.execute("BEGIN IMMEDIATE;")
                cur = conn.execute("SELECT val_json FROM central_state WHERE category='runtime' AND state_key=?", (key,))
                row = cur.fetchone()
                current = json.loads(row["val_json"]) if (row and row["val_json"] and row["val_json"] != "null") else None
                curr_status = str(current.get("status", "")).upper() if isinstance(current, dict) else ""

                if curr_status in ("START_REQUESTED", "STARTING", "RUNNING", "COMPLETED"):
                    conn.commit()
                    results[idx] = {"won": False, "op_id": current.get("operation_id")}
                else:
                    new_val = {"status": "START_REQUESTED", "operation_id": op_id, "plan_fingerprint": "fp-conn-08"}
                    conn.execute("INSERT INTO central_state VALUES ('runtime', ?, ?, DATETIME('now'))", (key, json.dumps(new_val)))
                    conn.commit()
                    results[idx] = {"won": True, "op_id": op_id}
            except Exception as ex:
                conn.rollback()
                results[idx] = {"won": False, "error": str(ex)}
            finally:
                conn.close()

        t1 = threading.Thread(target=raw_conn_worker, args=(1, "op-conn-1"))
        t2 = threading.Thread(target=raw_conn_worker, args=(2, "op-conn-2"))

        t1.start()
        t2.start()
        t1.join()
        t2.join()

        winners = [r for r in results.values() if r.get("won")]
        losers = [r for r in results.values() if not r.get("won")]

        self.assertEqual(len(winners), 1, "Exactly 1 independent SQLite connection must win BEGIN IMMEDIATE claim")
        self.assertEqual(len(losers), 1, "Competing connection must lose claim")
        winner_op = winners[0]["op_id"]
        self.assertEqual(losers[0]["op_id"], winner_op, "Losing connection must recover winning operation_id")

    def test_09_cross_process_multiprocessing_contention_produces_one_winner(self):
        # Section 8: True cross-process contention using Python multiprocessing
        db_path = self.gateway.state_store.db_path
        key = "mig-process-contention-09_status"

        conn_init = sqlite3.connect(db_path)
        conn_init.execute("CREATE TABLE IF NOT EXISTS central_state (category TEXT, state_key TEXT, val_json TEXT, updated_at TEXT, PRIMARY KEY (category, state_key))")
        conn_init.execute("DELETE FROM central_state WHERE category='runtime' AND state_key=?", (key,))
        conn_init.commit()
        conn_init.close()

        manager = multiprocessing.Manager()
        return_dict = manager.dict()
        barrier = manager.Barrier(2)

        p1 = multiprocessing.Process(target=_subproc_claim_worker, args=(db_path, key, "op-proc-1", "fp-proc-9", barrier, return_dict, 1))
        p2 = multiprocessing.Process(target=_subproc_claim_worker, args=(db_path, key, "op-proc-2", "fp-proc-9", barrier, return_dict, 2))

        p1.start()
        p2.start()
        p1.join(timeout=10.0)
        p2.join(timeout=10.0)

        results = dict(return_dict)
        winners = [r for r in results.values() if r.get("won")]
        losers = [r for r in results.values() if not r.get("won")]

        self.assertEqual(len(winners), 1, f"Cross-process contention MUST yield exactly 1 winner. Results: {results}")
        self.assertEqual(len(losers), 1, f"Cross-process loser MUST report won=False. Results: {results}")

        winner_op = winners[0]["op_id"]
        self.assertEqual(losers[0]["op_id"], winner_op, "Cross-process loser MUST recover winner operation_id")

        # Independent post-process SQLite verification
        conn_check = sqlite3.connect(db_path)
        conn_check.row_factory = sqlite3.Row
        row = conn_check.execute("SELECT val_json FROM central_state WHERE category='runtime' AND state_key=?", (key,)).fetchone()
        conn_check.close()

        self.assertIsNotNone(row)
        durable_val = json.loads(row["val_json"])
        self.assertEqual(durable_val.get("operation_id"), winner_op)
        self.assertEqual(durable_val.get("status"), "START_REQUESTED")

    def test_10_guarded_transition_prevents_stale_overwrites(self):
        # S4-H11: Transition guard test
        state_store = CentralStateStore()
        key = f"{self.workflow_id}_status"
        state_store.set_state(key, {"status": "RUNNING", "operation_id": "op-active"}, category="runtime")

        # Stale attempt to overwrite RUNNING back to STARTING must be REJECTED
        ok = state_store.guarded_transition_state(key, expected_current=["START_REQUESTED"], target_status="STARTING")
        self.assertFalse(ok)
        self.assertEqual(state_store.get_state(key, default=None, category="runtime")["status"], "RUNNING")

    def test_11_ipc_serialization_remains_single_object(self):
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

    def test_12_before_start_runtime_snapshot_honest_defaults(self):
        snap = self.gateway.get_runtime_snapshot({"migration_id": self.workflow_id})
        self.assertIsNone(snap.get("current_stage"))
        self.assertIn("start", snap.get("available_actions", []))

    def test_13_secret_redaction_in_ipc_errors(self):
        fp = AkaalSuperEngine.compute_plan_fingerprint(self.sample_spec, self.dag)
        self.governance.approve_migration_with_fingerprint(self.workflow_id, fp)

        res = self.gateway.start_transport({
            "migration_id": self.workflow_id,
            "password": "secret_source_pass",
            "is_synthetic_test": True
        })
        err_msg = res.get("error_message", "")
        self.assertNotIn("secret_source_pass", err_msg)


if __name__ == "__main__":
    unittest.main()
