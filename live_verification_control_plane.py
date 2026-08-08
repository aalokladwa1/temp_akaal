r"""
AKAAL Day 21 — Control Plane Real Lifecycle & Action Matrix Verification Test
"""
import os
import sys
import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("live_verification_control_plane")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from akaal.gateway.engine_gateway import EngineGateway

def test_control_plane_lifecycle():
    gateway = EngineGateway()
    mig_id = "mig-test-lifecycle-999"

    print("\n--- 1. Testing Unknown Migration ID Rejection ---")
    bad_start = gateway.invoke("start_transport", {"migration_id": "mig-unknown-xyz"})
    assert bad_start["status"] == "failed", f"Expected failure for unknown migration ID, got {bad_start}"
    assert bad_start["error_code"] == "UNKNOWN_MIGRATION_ID", f"Expected UNKNOWN_MIGRATION_ID error code, got {bad_start['error_code']}"
    print(f"[SUCCESS] Unknown Migration ID explicitly rejected: {bad_start}")

    print("\n--- 2. Testing Create Migration (Unstarted / Ready State) ---")
    mig_res = gateway.invoke("create_migration", {"migration_id": mig_id, "migration_name": "Core Production Cutover"})
    assert mig_res["migration_id"] == mig_id, "Migration ID mismatch"
    print(f"Registered Migration: {mig_res}")

    print("\n--- 3. Testing Initial Runtime Snapshot (Must be READY, zero fake rows) ---")
    init_snap = gateway.invoke("get_runtime_snapshot", {"migration_id": mig_id})
    assert init_snap["health_status"] == "READY", f"Expected READY status, got {init_snap['health_status']}"
    assert init_snap["rows_transferred"] is None, f"Expected None for unstarted rows_transferred, got {init_snap['rows_transferred']}"
    assert "start" in init_snap["available_actions"], "Expected 'start' in available_actions"
    assert "resume" not in init_snap["available_actions"], "CREATED state must NOT contain 'resume'"
    print(f"[SUCCESS] Initial Runtime Snapshot verified READY: {json.dumps(init_snap, indent=2)}")

    print("\n--- 4. Testing Start Transport (Operator Confirmation Lifecycle) ---")
    transport_res = gateway.invoke("start_transport", {"migration_id": mig_id})
    print(f"Start Transport Result: {transport_res}")
    assert transport_res["status"] in ("transport_running", "failed"), f"Unexpected transport status: {transport_res['status']}"

    print("\n--- 5. Testing Runtime Snapshot Post-Start (RUNNING state action matrix) ---")
    post_snap = gateway.invoke("get_runtime_snapshot", {"migration_id": mig_id})
    assert "pause" in post_snap["available_actions"], "RUNNING state must contain 'pause'"
    assert "resume" not in post_snap["available_actions"], "RUNNING state must NOT contain 'resume'"
    print(f"[SUCCESS] Post-Start Runtime Snapshot verified RUNNING (Resume absent): {json.dumps(post_snap, indent=2)}")

    print("\n--- 6. Testing Governance Approval Request & Queue ---")
    app_res = gateway.invoke("request_approval", {
        "migration_id": mig_id,
        "migration_name": "Core Production Cutover",
        "approver": "Aalok (Lead DBA)",
        "four_eyes_policy": True
    })
    app_id = app_res["approval_reference_id"]

    queue_res = gateway.invoke("get_approval_queue", {})
    assert queue_res["status"] == "success", "Failed to retrieve approval queue"
    found_pkt = any(p.get("id") == app_id for p in queue_res["approvals"])
    assert found_pkt, f"Approval packet {app_id} not found in queue"
    print(f"[SUCCESS] Approval queue retrieved: {len(queue_res['approvals'])} active packet(s).")

    print("\n--- 7. Testing Approval Decision Submission ---")
    dec_res = gateway.invoke("submit_approval_decision", {
        "approval_id": app_id,
        "decision": "approved",
        "approver": "Aalok (Lead DBA)",
        "reason": "Topological DAG and security posture sign-off verified."
    })
    assert dec_res["status"] == "approved", "Approval decision status mismatch"
    print(f"Decision Recorded: {dec_res}")

    print("\n--- 8. Testing Pause & Resume Runtime Commands Action Matrix ---")
    pause_res = gateway.invoke("pause_migration", {"migration_id": mig_id})
    print(f"Pause Migration: {pause_res}")

    paused_snap = gateway.invoke("get_runtime_snapshot", {"migration_id": mig_id})
    assert "resume" in paused_snap["available_actions"], "PAUSED state must contain 'resume'"
    assert "pause" not in paused_snap["available_actions"], "PAUSED state must NOT contain 'pause'"
    print(f"[SUCCESS] PAUSED state available actions verified: {paused_snap['available_actions']}")

    chkpt_res = gateway.invoke("trigger_checkpoint", {"migration_id": mig_id})
    print(f"Trigger Checkpoint: {chkpt_res}")

    resume_res = gateway.invoke("resume_migration", {"migration_id": mig_id})
    print(f"Resume Migration: {resume_res}")

    resumed_snap = gateway.invoke("get_runtime_snapshot", {"migration_id": mig_id})
    assert "pause" in resumed_snap["available_actions"], "RUNNING state post-resume must contain 'pause'"
    assert "resume" not in resumed_snap["available_actions"], "RUNNING state post-resume must NOT contain 'resume'"
    print(f"[SUCCESS] Resumed state available actions verified: {resumed_snap['available_actions']}")

    print("\n==========================================================================")
    print("ALL CONTROL PLANE LIFECYCLE & ACTION MATRIX TESTS PASSED 100%")
    print("==========================================================================")

if __name__ == "__main__":
    test_control_plane_lifecycle()
